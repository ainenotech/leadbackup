"""Retrieval-augmented generation (RAG) support for the reply agent.

Company knowledge (FAQs, pricing, policies, onboarding steps, etc.) is
chunked, embedded with Google's text-embedding model, and stored in the
Postgres `knowledge_documents` table (see Backend/models.py). When a
customer reply comes in, `retrieve_relevant_chunks` embeds their message
and returns the most similar stored chunks, which reply_worker.py passes
into Agent.reply_agent.process_incoming_reply so the AI's answer is
grounded in real company information instead of guessing.

No vector-database extension (e.g. pgvector) is required: embeddings are
stored as plain float arrays and compared with cosine similarity in
Python via numpy. This keeps the setup to "just Postgres", at the cost of
scanning every row per query — fine for a knowledge base of FAQs/policies
(tens to low thousands of chunks), not meant for millions of documents.
"""

import os
from typing import Any, List, Optional

import numpy as np
from sqlalchemy.orm import Session

from Backend.models import KnowledgeDocument

_embeddings = None

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
if "text-embedding-004" in EMBEDDING_MODEL:
    EMBEDDING_MODEL = "models/gemini-embedding-001"

CHUNK_SIZE = 800  # characters per chunk
CHUNK_OVERLAP = 120  # characters of overlap between consecutive chunks


def _get_embeddings():
    """Lazily builds the embeddings client. Always uses Gemini's embedding
    API (GEMINI_API_KEY / GOOGLE_API_KEY) regardless of LLM_PROVIDER —
    Anthropic does not offer a public embeddings endpoint, so RAG needs a
    Google API key even when replies are drafted with Claude."""
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) is required for RAG embeddings, "
            "even if LLM_PROVIDER=claude — Anthropic doesn't provide an "
            "embeddings API. Set it in .env."
        )

    _embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL, google_api_key=api_key)
    return _embeddings


def embed_text(text: str) -> List[float]:
    """Embeds a single query string."""
    return _get_embeddings().embed_query(text)


def embed_texts(texts: List[str], batch_size: int = 10) -> List[List[float]]:
    """Embeds document chunks in batches with automatic backoff and pacing to prevent rate limits."""
    client = _get_embeddings()
    all_vectors = []
    import time
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        for attempt in range(5):
            try:
                vectors = client.embed_documents(batch)
                all_vectors.extend(vectors)
                time.sleep(1.0)  # gentle 1s pacing between batches
                break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    print(f"[Notice] Rate limit reached. Backing off 6s before retry (attempt {attempt+1}/5)...")
                    time.sleep(6)
                elif attempt == 4:
                    raise e
                else:
                    time.sleep(2)
    return all_vectors


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Splits text into overlapping chunks on paragraph boundaries first,
    falling back to a hard character split for any paragraph longer than
    chunk_size on its own."""
    paragraphs = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para

        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)

        if len(para) <= chunk_size:
            current = para
        else:
            # Hard-split an overlong paragraph
            start = 0
            while start < len(para):
                end = start + chunk_size
                chunks.append(para[start:end])
                start = end - overlap if end - overlap > start else end
            current = ""

    if current:
        chunks.append(current)

    return chunks


def add_document(
    db: Session, title: str, content: str, category: Optional[str] = None, organization_id: Optional[str] = None
) -> int:
    """Chunks, embeds and stores `content` under `title`. Returns the
    number of chunks stored."""
    chunks = chunk_text(content)
    if not chunks:
        return 0

    vectors = embed_texts(chunks)

    for chunk, vector in zip(chunks, vectors):
        db.add(
            KnowledgeDocument(
                title=title,
                category=category,
                content=chunk,
                embedding=vector,
                organization_id=organization_id,
            )
        )
    db.commit()
    return len(chunks)


def list_documents(db: Session, organization_id: Optional[str] = None) -> List[dict]:
    """Returns one summary row per distinct source document (grouped by
    title), filtered by organization_id if provided."""
    from sqlalchemy import func
    q = db.query(
        KnowledgeDocument.title,
        KnowledgeDocument.category,
        func.count(KnowledgeDocument.id).label("chunks"),
        func.min(func.substr(KnowledgeDocument.content, 1, 200)).label("preview"),
    )
    if organization_id:
        q = q.filter(KnowledgeDocument.organization_id == organization_id)

    rows = (
        q.group_by(KnowledgeDocument.title, KnowledgeDocument.category)
        .order_by(KnowledgeDocument.title)
        .all()
    )
    return [
        {
            "title": r[0],
            "category": r[1] or "Documentation",
            "chunks": r[2],
            "preview": (r[3] or "")[:200],
        }
        for r in rows
    ]


def clear_all_knowledge_documents(db: Session, organization_id: Optional[str] = None) -> int:
    """Deletes document chunks stored in the knowledge base (scoped to org if provided)."""
    q = db.query(KnowledgeDocument)
    if organization_id:
        q = q.filter(KnowledgeDocument.organization_id == organization_id)
    deleted = q.delete()
    db.commit()
    return deleted


def extract_text_from_file(file_or_path, filename: str) -> str:
    """Extracts raw text content from a file path or file-like buffer.

    Supported formats:
    - PDF  (.pdf)           – page-by-page text via pypdf
    - Word (.docx)          – paragraphs + table cells via python-docx
    - Excel (.xlsx, .xls)   – sheet-by-sheet rows via pandas/openpyxl
    - CSV  (.csv)           – tabular rows via pandas
    - JSON (.json)          – pretty-printed key/value text
    - Markdown / Text       – raw UTF-8 text (.md, .txt, and everything else)
    """
    import io
    ext = os.path.splitext(filename)[1].lower()

    # ── PDF ──
    if ext == ".pdf":
        from pypdf import PdfReader
        if isinstance(file_or_path, (str, os.PathLike)):
            reader = PdfReader(file_or_path)
        elif hasattr(file_or_path, "read"):
            reader = PdfReader(file_or_path)
        elif isinstance(file_or_path, bytes):
            reader = PdfReader(io.BytesIO(file_or_path))
        else:
            raise ValueError(f"Unsupported file input type: {type(file_or_path)}")

        pages_text = []
        for p in reader.pages:
            t = p.extract_text()
            if t:
                pages_text.append(t.strip())
        return "\n\n".join(pages_text)

    # ── DOCX (Word) ──
    if ext == ".docx":
        try:
            from docx import Document as DocxDocument
        except ImportError:
            raise ImportError("python-docx is required for .docx files. Install it with: pip install python-docx")

        if isinstance(file_or_path, bytes):
            doc = DocxDocument(io.BytesIO(file_or_path))
        elif hasattr(file_or_path, "read"):
            doc = DocxDocument(file_or_path)
        else:
            doc = DocxDocument(file_or_path)

        parts = []
        # Extract paragraphs
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                parts.append(text)
        # Extract table data
        for table in doc.tables:
            table_rows = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                table_rows.append(" | ".join(cells))
            if table_rows:
                parts.append("\n".join(table_rows))
        return "\n\n".join(parts)

    # ── CSV ──
    if ext == ".csv":
        import pandas as pd
        if isinstance(file_or_path, bytes):
            df = pd.read_csv(io.BytesIO(file_or_path))
        elif hasattr(file_or_path, "read"):
            df = pd.read_csv(file_or_path)
        elif isinstance(file_or_path, (str, os.PathLike)):
            df = pd.read_csv(file_or_path)
        else:
            return str(file_or_path)
        return _dataframe_to_text(df, filename)

    # ── Excel (XLSX / XLS) ──
    if ext in (".xlsx", ".xls"):
        import pandas as pd
        if isinstance(file_or_path, bytes):
            xls = pd.ExcelFile(io.BytesIO(file_or_path))
        elif hasattr(file_or_path, "read"):
            xls = pd.ExcelFile(file_or_path)
        elif isinstance(file_or_path, (str, os.PathLike)):
            xls = pd.ExcelFile(file_or_path)
        else:
            return str(file_or_path)

        all_text = []
        for sheet_name in xls.sheet_names:
            df = xls.parse(sheet_name)
            all_text.append(f"--- Sheet: {sheet_name} ---")
            all_text.append(_dataframe_to_text(df, filename))
        return "\n\n".join(all_text)

    # ── JSON ──
    if ext == ".json":
        import json as _json
        raw = _read_raw_text(file_or_path)
        try:
            data = _json.loads(raw)
            return _json.dumps(data, indent=2, ensure_ascii=False)
        except Exception:
            return raw

    # ── Markdown / Plain Text / Fallback ──
    return _read_raw_text(file_or_path)


def _read_raw_text(file_or_path) -> str:
    """Helper to read raw UTF-8 text from a path, buffer, or bytes object."""
    if isinstance(file_or_path, (str, os.PathLike)) and os.path.exists(str(file_or_path)):
        with open(file_or_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    elif hasattr(file_or_path, "read"):
        data = file_or_path.read()
        if isinstance(data, bytes):
            return data.decode("utf-8", errors="replace")
        return str(data)
    elif isinstance(file_or_path, bytes):
        return file_or_path.decode("utf-8", errors="replace")
    elif isinstance(file_or_path, str):
        return file_or_path
    return ""


def _dataframe_to_text(df, filename: str = "") -> str:
    """Converts a pandas DataFrame into a readable text block suitable for
    chunking and embedding. Each row becomes a labeled line using its column
    headers so the retrieval engine can match on column names and values."""
    if df.empty:
        return ""
    lines = []
    headers = list(df.columns)
    lines.append("Columns: " + ", ".join(str(h) for h in headers))
    for idx, row in df.iterrows():
        parts = [f"{col}: {row[col]}" for col in headers if str(row[col]).strip() and str(row[col]).lower() != "nan"]
        if parts:
            lines.append(f"Row {idx + 1}: " + " | ".join(parts))
    return "\n".join(lines)


def ingest_file_content(
    db: Session,
    filename: str,
    file_bytes_or_content: Any,
    title: Optional[str] = None,
    category: Optional[str] = None,
) -> int:
    """Extracts text from a file (PDF/DOCX/CSV/XLSX/JSON/MD/TXT), chunks,
    embeds and saves to KnowledgeDocument.
    Replaces any existing document with the same title to avoid duplicate chunks.
    """
    text = extract_text_from_file(file_bytes_or_content, filename)
    if not text or not text.strip():
        return 0

    doc_title = title or os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf" and not doc_title.endswith("(PDF)"):
        doc_title = f"{doc_title} (PDF)"
    elif ext == ".docx" and not doc_title.endswith("(Word)"):
        doc_title = f"{doc_title} (Word)"

    # Remove existing chunks for this title to avoid duplicate accumulation
    delete_document(db, doc_title, organization_id=organization_id)

    # Auto-detect category from file extension if not specified
    if not category:
        ext_categories = {
            ".pdf": "PDF Knowledge Base",
            ".docx": "Word Document",
            ".csv": "Spreadsheet Data",
            ".xlsx": "Spreadsheet Data",
            ".xls": "Spreadsheet Data",
            ".json": "Structured Data",
        }
        category = ext_categories.get(ext, "Documentation")

    return add_document(db, title=doc_title, content=text, category=category, organization_id=organization_id)


def get_knowledge_base_summary(db: Session, organization_id: Optional[str] = None) -> dict:
    """Returns total chunk count, list of documents, and embedding configuration."""
    docs = list_documents(db, organization_id=organization_id)
    q = db.query(KnowledgeDocument)
    if organization_id:
        q = q.filter(KnowledgeDocument.organization_id == organization_id)
    total_chunks = q.count()
    return {
        "total_chunks": total_chunks,
        "total_documents": len(docs),
        "documents": docs,
        "embedding_model": EMBEDDING_MODEL,
    }


def delete_document(db: Session, title: str, organization_id: Optional[str] = None) -> int:
    """Deletes every chunk stored under `title`. Returns the number of
    chunks removed."""
    q = db.query(KnowledgeDocument).filter(KnowledgeDocument.title == title)
    if organization_id:
        q = q.filter(KnowledgeDocument.organization_id == organization_id)
    deleted = q.delete()
    db.commit()
    return deleted


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    va, vb = np.array(a, dtype=float), np.array(b, dtype=float)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def retrieve_relevant_chunks(
    db: Session, query: str, top_k: int = 4, min_score: float = 0.40, organization_id: Optional[str] = None
) -> List[dict]:
    """Embeds `query` and returns the top_k most similar stored chunks
    (each as {"title", "category", "content", "score"}), filtered to a
    minimum cosine-similarity so unrelated messages ("thanks, bye") don't
    drag in irrelevant knowledge. Returns [] if the knowledge base is
    empty or nothing clears min_score."""
    q = db.query(KnowledgeDocument)
    if organization_id:
        q = q.filter(KnowledgeDocument.organization_id == organization_id)
    rows = q.all()
    if not rows:
        return []

    query_vector = embed_text(query)

    scored = []
    for row in rows:
        if not row.embedding:
            continue
        score = _cosine_similarity(query_vector, row.embedding)
        scored.append((score, row))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    # Filter by min_score; fallback to top 2 if best match is between 0.35 and min_score
    filtered = [(score, row) for score, row in scored if score >= min_score]
    if not filtered and scored and scored[0][0] >= 0.35:
        filtered = scored[:2]

    return [
        {
            "title": row.title,
            "category": row.category,
            "content": row.content,
            "score": round(score, 4),
        }
        for score, row in filtered[:top_k]
    ]
