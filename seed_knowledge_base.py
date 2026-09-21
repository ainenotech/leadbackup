"""One-off / re-runnable script to (re)load knowledge_base/*.md and *.txt
files into Postgres as embedded chunks for the reply agent's RAG retrieval
(see services/rag.py and Agent/reply_agent.py).

Every run clears all existing knowledge_documents rows and reloads from
scratch, so there's no duplicate-chunk drift as you edit files — just edit
the .md/.txt files in knowledge_base/ (or add new ones) and re-run.

Usage:
    python seed_knowledge_base.py
"""

import glob
import os

from dotenv import load_dotenv

load_dotenv()

from Backend.db import Base, SessionLocal, engine
from Backend.models import KnowledgeDocument
from services.rag import add_document

Base.metadata.create_all(bind=engine)

KB_DIR = os.path.join(os.path.dirname(__file__), "knowledge_base")


def extract_file_content(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(path)
        pages_text = []
        for p in reader.pages:
            t = p.extract_text()
            if t:
                pages_text.append(t.strip())
        return "\n\n".join(pages_text)
    else:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()


def main():
    db = SessionLocal()
    try:
        existing = db.query(KnowledgeDocument).count()
        if existing:
            print(f"Clearing {existing} existing knowledge chunk(s)...")
            db.query(KnowledgeDocument).delete()
            db.commit()

        pdf_files = sorted(glob.glob(os.path.join(KB_DIR, "*.pdf")))
        other_files = sorted(
            glob.glob(os.path.join(KB_DIR, "*.md")) + glob.glob(os.path.join(KB_DIR, "*.txt"))
        )
        files = pdf_files + other_files
        if not files:
            print(f"No .pdf/.md/.txt files found in {KB_DIR}/ — add some and re-run.")
            return

        total_chunks = 0
        seen_titles = set()
        for path in files:
            ext = os.path.splitext(path)[1].lower()
            base_name = os.path.splitext(os.path.basename(path))[0].replace("_", " ").replace("-", " ").title()
            title = f"{base_name} (PDF)" if ext == ".pdf" else base_name

            # Avoid double-indexing identical md if pdf is present
            if ext == ".md" and f"{base_name} (PDF)" in seen_titles:
                continue

            content = extract_file_content(path)
            if not content:
                continue

            n = add_document(db, title=title, content=content, category=None)
            seen_titles.add(title)
            print(f"  {os.path.basename(path)} -> '{title}' ({n} chunk(s))")
            total_chunks += n

        print(f"\nDone. Loaded {total_chunks} chunk(s) from {len(seen_titles)} source(s) into the knowledge base.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
