"""Knowledge Base Hub — Dedicated sidebar page for managing RAG documents.

Provides a full-featured UI to upload, ingest, browse, search, and delete
knowledge base documents of any supported format (PDF, DOCX, CSV, XLSX,
JSON, Markdown, TXT). Ingested documents are automatically chunked, embedded,
and stored in PostgreSQL for retrieval-augmented generation (RAG) when the
AI reply agent handles inbound customer emails.
"""

from typing import Any, Dict, List, Optional
import html
import os
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from Backend.db import SessionLocal
from services.rag import (
    clear_all_knowledge_documents,
    delete_document,
    get_knowledge_base_summary,
    ingest_file_content,
    list_documents,
    retrieve_relevant_chunks,
)
from Agent.reply_agent import process_incoming_reply


# ─────────────────────────────────────────────────────────────
# SUPPORTED FILE TYPES
# ─────────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = ["pdf", "docx", "csv", "xlsx", "xls", "json", "md", "txt"]
SUPPORTED_LABEL = "PDF, DOCX, CSV, XLSX, JSON, Markdown, TXT"

CATEGORY_OPTIONS = [
    "Auto-Detect",
    "Company Overview",
    "Pricing & Packages",
    "SLAs & Security",
    "Engineering Capabilities",
    "Case Studies",
    "FAQs",
    "Onboarding",
    "Documentation",
    "Custom",
]


def _clean_html(text: str) -> str:
    """Strips leading/trailing indentation from each line to prevent
    markdown parsers from mistaking 4-space indentation as a code block."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    return "".join(lines)


def _clean_text_preview(text: str, max_chars: int = 200) -> str:
    """Collapses whitespace and newlines to prevent markdown parsing breaks."""
    if not text:
        return ""
    collapsed = " ".join(str(text).split())
    if len(collapsed) > max_chars:
        return collapsed[:max_chars].rstrip() + "..."
    return collapsed


# ─────────────────────────────────────────────────────────────
# MAIN VIEW FUNCTION
# ─────────────────────────────────────────────────────────────
def render_knowledge_base_hub(organization_id: Optional[str] = None, *args, **kwargs):
    """Renders the full Knowledge Base Hub page."""
    if organization_id is None:
        organization_id = kwargs.get("organization_id") or st.session_state.get("current_org_id")

    # ── Fetch current KB state ──
    db = SessionLocal()
    try:
        kb_summary = get_knowledge_base_summary(db, organization_id=organization_id)
    except Exception:
        kb_summary = {"total_chunks": 0, "total_documents": 0, "documents": [], "embedding_model": "N/A"}
    finally:
        db.close()

    kb_chunks = kb_summary.get("total_chunks", 0)
    kb_docs_count = kb_summary.get("total_documents", 0)
    embedding_model = kb_summary.get("embedding_model", "models/gemini-embedding-001")
    docs_list = kb_summary.get("documents", [])

    # ═══════════════════════════════════════════════════════════
    # HEADER BANNER
    # ═══════════════════════════════════════════════════════════
    st.markdown(
        _clean_html("""
        <div style="margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 22px; font-weight: 700; display: flex; align-items: center; gap: 10px;">
                <span>📚</span> Knowledge Base Hub
                <span style="font-size: 12px; background: linear-gradient(135deg, #0D9488 0%, #0EA5E9 100%); color: #FFF; padding: 3px 10px; border-radius: 20px; font-weight: 600;">RAG-Powered</span>
            </h2>
            <p style="margin: 4px 0 0 0; font-size: 13.5px; color: var(--text-muted); line-height: 1.5;">
                Upload any document — PDFs, Word files, spreadsheets, CSVs, or JSON — and they are automatically chunked, embedded, and stored in your database.
                When a lead replies via email, the AI agent retrieves verified facts from these documents to compose accurate, grounded responses.
            </p>
        </div>
        """),
        unsafe_allow_html=True,
    )

    # ═══════════════════════════════════════════════════════════
    # KPI METRICS GRID
    # ═══════════════════════════════════════════════════════════
    kpi_html = f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 24px;">
        <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 18px; border-left: 4px solid #0D9488; box-shadow: var(--shadow-sm);">
            <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Active Chunks</div>
            <div style="font-size: 28px; font-weight: 800; color: var(--text-primary); margin: 4px 0; font-family: 'JetBrains Mono', monospace;">{kb_chunks}</div>
            <div style="font-size: 12px; color: #0D9488; font-weight: 600;">Indexed in Vector Memory</div>
        </div>
        <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 18px; border-left: 4px solid var(--brand-primary, #2563EB); box-shadow: var(--shadow-sm);">
            <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Source Documents</div>
            <div style="font-size: 28px; font-weight: 800; color: var(--text-primary); margin: 4px 0; font-family: 'JetBrains Mono', monospace;">{kb_docs_count}</div>
            <div style="font-size: 12px; color: var(--brand-primary, #2563EB); font-weight: 600;">Attached Files</div>
        </div>
        <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 18px; border-left: 4px solid #8B5CF6; box-shadow: var(--shadow-sm);">
            <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Embedding Engine</div>
            <div style="font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 8px 0 4px 0;">Gemini Embeddings</div>
            <div style="font-size: 12px; color: var(--text-muted);">Dense Vector Search</div>
        </div>
        <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 18px; border-left: 4px solid #F59E0B; box-shadow: var(--shadow-sm);">
            <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Supported Formats</div>
            <div style="font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 8px 0 4px 0;">7 File Types</div>
            <div style="font-size: 12px; color: var(--text-muted);">PDF · DOCX · CSV · XLSX · JSON · MD · TXT</div>
        </div>
    </div>
    """
    st.markdown(_clean_html(kpi_html), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════
    # UPLOAD & INGEST SECTION
    # ═══════════════════════════════════════════════════════════
    st.markdown(
        _clean_html("""
        <div style="margin-bottom: 8px;">
            <h4 style="margin: 0; font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                <span>📤</span> Upload & Ingest Document
            </h4>
            <p style="margin: 2px 0 0 0; font-size: 12.5px; color: var(--text-muted);">
                Drag and drop or browse to upload. The document will be parsed, split into semantic chunks, embedded using Gemini, and stored in PostgreSQL for RAG retrieval.
            </p>
        </div>
        """),
        unsafe_allow_html=True,
    )

    upload_col1, upload_col2 = st.columns([2.5, 1.5])

    with upload_col1:
        uploaded_file = st.file_uploader(
            f"Upload Document ({SUPPORTED_LABEL})",
            type=SUPPORTED_EXTENSIONS,
            key="kb_hub_file_uploader",
            help=f"Supported: {SUPPORTED_LABEL}. Max recommended size: 20MB.",
        )

    with upload_col2:
        custom_title = st.text_input(
            "Document Title (Optional)",
            placeholder="e.g. Neno Capabilities 2026",
            key="kb_hub_custom_title",
        )
        selected_category = st.selectbox(
            "Category",
            options=CATEGORY_OPTIONS,
            index=0,
            key="kb_hub_category_select",
        )

    # Custom category text input if "Custom" is selected
    custom_category_text = None
    if selected_category == "Custom":
        custom_category_text = st.text_input(
            "Enter Custom Category Name",
            placeholder="e.g. Partnership Agreements",
            key="kb_hub_custom_category_text",
        )

    ingest_btn = st.button(
        "⚡ Ingest & Embed into Database",
        type="primary",
        use_container_width=True,
        disabled=(uploaded_file is None),
        key="kb_hub_ingest_btn",
    )

    if ingest_btn and uploaded_file is not None:
        # Determine category
        if selected_category == "Auto-Detect":
            cat = None  # Let ingest_file_content auto-detect
        elif selected_category == "Custom":
            cat = custom_category_text.strip() if custom_category_text else None
        else:
            cat = selected_category

        with st.spinner(f"Extracting text, chunking & computing embeddings for '{uploaded_file.name}'..."):
            # Save file to knowledge_base/ directory
            kb_save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base")
            os.makedirs(kb_save_dir, exist_ok=True)
            saved_path = os.path.join(kb_save_dir, uploaded_file.name)
            file_bytes = uploaded_file.getvalue()
            with open(saved_path, "wb") as f_out:
                f_out.write(file_bytes)

            db_ingest = SessionLocal()
            try:
                num_chunks = ingest_file_content(
                    db=db_ingest,
                    filename=uploaded_file.name,
                    file_bytes_or_content=file_bytes,
                    title=custom_title.strip() if custom_title else None,
                    category=cat,
                    organization_id=organization_id,
                )
            except Exception as e:
                st.error(f"❌ Failed to ingest document: {e}")
                num_chunks = 0
            finally:
                db_ingest.close()

        if num_chunks > 0:
            st.success(f"✅ Successfully ingested **{uploaded_file.name}** into the Knowledge Base! ({num_chunks} vector chunks created)")
            st.cache_data.clear()
            st.rerun()
        elif num_chunks == 0:
            st.warning("⚠️ No text content could be extracted from the file. Please verify the document is not empty or encrypted.")

    # ═══════════════════════════════════════════════════════════
    # DIVIDER
    # ═══════════════════════════════════════════════════════════
    st.markdown("<hr style='margin: 24px 0; border: none; border-top: 1px solid var(--border-subtle);'>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════
    # ACTIVE DOCUMENTS INVENTORY
    # ═══════════════════════════════════════════════════════════
    st.markdown(
        _clean_html("""
        <h4 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
            <span>📑</span> Active Knowledge Documents
        </h4>
        """),
        unsafe_allow_html=True,
    )

    if not docs_list:
        st.info("💡 **No documents indexed yet.** Upload your first document above to start building the Knowledge Base. The AI reply agent will automatically use these documents to answer lead inquiries.")
    else:
        for doc in docs_list:
            d_title = doc.get("title", "Untitled")
            d_chunks = doc.get("chunks", 0)
            d_preview = doc.get("preview", "")
            d_cat = doc.get("category") or "Documentation"

            # Category badge color
            cat_colors = {
                "PDF Knowledge Base": "#DC2626",
                "Word Document": "#2563EB",
                "Spreadsheet Data": "#16A34A",
                "Structured Data": "#9333EA",
                "Documentation": "#0D9488",
                "Company Overview": "#0EA5E9",
                "Pricing & Packages": "#F59E0B",
                "SLAs & Security": "#EF4444",
                "Engineering Capabilities": "#6366F1",
                "Case Studies": "#EC4899",
                "FAQs": "#14B8A6",
                "Onboarding": "#8B5CF6",
            }
            badge_color = cat_colors.get(d_cat, "#64748B")

            doc_col1, doc_col2 = st.columns([5, 1])
            with doc_col1:
                clean_preview = _clean_text_preview(d_preview, 220)
                card_html = (
                    f'<div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 14px 18px; margin-bottom: 8px; box-shadow: var(--shadow-sm);">'
                    f'<div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">'
                    f'<span style="font-size: 15px; font-weight: 700; color: var(--text-primary);">📄 {html.escape(d_title)}</span>'
                    f'<span style="font-size: 10.5px; background: {badge_color}; color: #FFF; padding: 2px 8px; border-radius: 12px; font-weight: 600;">{html.escape(d_cat)}</span>'
                    f'<span style="font-size: 10.5px; background: #0D9488; color: #FFF; padding: 2px 8px; border-radius: 12px; font-weight: 600;">{d_chunks} Chunks</span>'
                    f'</div>'
                    f'<div style="font-size: 12px; color: var(--text-muted); margin-top: 6px; max-width: 750px; line-height: 1.45;">'
                    f'{html.escape(clean_preview)}'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)

            with doc_col2:
                if st.button("🗑️ Remove", key=f"kb_hub_del_{d_title}", use_container_width=True, type="secondary"):
                    db_del = SessionLocal()
                    try:
                        delete_document(db_del, d_title, organization_id=organization_id)
                    finally:
                        db_del.close()
                    st.toast(f"Removed '{d_title}' from Knowledge Base.", icon="🗑️")
                    st.cache_data.clear()
                    st.rerun()

        # Purge All button
        st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
        purge_col1, purge_col2 = st.columns([3, 1.2])
        with purge_col1:
            st.caption(f"Knowledge base has **{kb_chunks}** active chunks across **{kb_docs_count}** document(s).")
        with purge_col2:
            if st.button("🗑️ Purge All Documents", key="kb_hub_purge_all_btn", use_container_width=True, type="secondary"):
                db_purge = SessionLocal()
                try:
                    clear_all_knowledge_documents(db_purge, organization_id=organization_id)
                finally:
                    db_purge.close()
                st.cache_data.clear()
                st.toast("✅ All knowledge documents purged to 0 chunks!", icon="🗑️")
                st.rerun()

    # ═══════════════════════════════════════════════════════════
    # DIVIDER
    # ═══════════════════════════════════════════════════════════
    st.markdown("<hr style='margin: 24px 0; border: none; border-top: 1px solid var(--border-subtle);'>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════
    # INTERACTIVE RAG QUERY TESTER
    # ═══════════════════════════════════════════════════════════
    st.markdown(
        _clean_html("""
        <h4 style="margin: 0 0 4px 0; font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
            <span>🧪</span> RAG Query Playground
        </h4>
        <p style="margin: 0 0 12px 0; font-size: 12.5px; color: var(--text-muted);">
            Simulate a customer inquiry to see which knowledge chunks are retrieved, their cosine similarity scores, and how the AI agent drafts a grounded response.
        </p>
        """),
        unsafe_allow_html=True,
    )

    query_col1, query_col2 = st.columns([3.5, 1.2])
    with query_col1:
        test_query = st.text_input(
            "Simulate Customer Question",
            value="What are your core services and how do we get started?",
            key="kb_hub_test_query",
        )
    with query_col2:
        test_btn = st.button(
            "🔍 Test RAG Retrieval",
            type="primary",
            use_container_width=True,
            key="kb_hub_test_btn",
            disabled=(kb_chunks == 0),
        )

    if test_btn and test_query and kb_chunks > 0:
        with st.spinner("Embedding query and searching vector memory..."):
            db_test = SessionLocal()
            try:
                retrieved = retrieve_relevant_chunks(db_test, query=test_query, top_k=4, min_score=0.35, organization_id=organization_id)
                test_agent_res = process_incoming_reply(
                    db=db_test,
                    from_email="inquiry@client.com",
                    from_name="Prospective Client",
                    company="Client Enterprise",
                    subject="Inquiry",
                    raw_body=test_query,
                )
            finally:
                db_test.close()

        result_col1, result_col2 = st.columns([1.2, 1.8])

        with result_col1:
            st.markdown(f"**Retrieved Chunks ({len(retrieved)}):**")
            if not retrieved:
                st.warning("No chunks cleared the relevance threshold (0.35). The agent will use fallback capabilities context.")
            else:
                for idx, c in enumerate(retrieved, 1):
                    score = c.get("score", 0)
                    score_pct = int(score * 100)
                    bar_color = "#16A34A" if score >= 0.55 else ("#F59E0B" if score >= 0.40 else "#EF4444")
                    clean_chunk_content = _clean_text_preview(c.get('content', ''), 180)
                    chunk_html = (
                        f'<div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; font-size: 12px;">'
                        f'<div style="display: flex; justify-content: space-between; margin-bottom: 6px;">'
                        f'<span style="font-weight: 700; color: var(--text-primary);">Chunk #{idx} · {html.escape(c.get("title", "KB"))}</span>'
                        f'<span style="font-size: 10px; background: {bar_color}; color: #FFF; padding: 2px 8px; border-radius: 12px; font-weight: 600;">{score_pct}% Match</span>'
                        f'</div>'
                        f'<div style="color: var(--text-muted); font-size: 11.5px; line-height: 1.4;">{html.escape(clean_chunk_content)}</div>'
                        f'<div style="margin-top: 6px; background: var(--border-subtle); border-radius: 3px; height: 4px; overflow: hidden;">'
                        f'<div style="background: {bar_color}; width: {score_pct}%; height: 100%; border-radius: 3px;"></div>'
                        f'</div>'
                        f'</div>'
                    )
                    st.markdown(chunk_html, unsafe_allow_html=True)

        with result_col2:
            st.markdown(f"**AI Draft Response (Intent: `{test_agent_res.get('intent', 'question')}`):**")
            draft = test_agent_res.get("response_text", "")
            safe_draft = html.escape(draft).replace("\n", "<br/>")
            draft_html = (
                f'<div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 16px; font-size: 13px; color: var(--text-primary); line-height: 1.6; max-height: 420px; overflow-y: auto;">'
                f'{safe_draft}'
                f'</div>'
            )
            st.markdown(draft_html, unsafe_allow_html=True)
    elif test_btn and kb_chunks == 0:
        st.info("Upload at least one document first to test the RAG retrieval pipeline.")
