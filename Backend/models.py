import uuid

from sqlalchemy import Boolean, Column, Float, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from .db import Base


class CampaignLog(Base):
    """One row per (lead, campaign). Columns support lead journey:
    drafting, approval, sending, email replies, form responses, telemetry, and calendar bookings.
    """

    __tablename__ = "campaign_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_name = Column(String, nullable=False)

    lead_id = Column(String, nullable=False)
    email = Column(String, nullable=False)
    name = Column(String, nullable=True)
    company = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    token = Column(String, unique=True, nullable=False)
    tracking_link = Column(String, nullable=True)

    subject = Column(Text, nullable=True)
    body = Column(Text, nullable=True)

    # Statuses: drafted | approved | sent | rejected | failed
    status = Column(String, default="pending")
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    send_error = Column(Text, nullable=True)

    # Live Telemetry Fields (Real-time tracking)
    opened = Column(Boolean, default=False)
    open_count = Column(Integer, default=0)
    first_open_at = Column(DateTime(timezone=True), nullable=True)
    last_open_at = Column(DateTime(timezone=True), nullable=True)
    clicked_link = Column(Boolean, default=False)
    click_count = Column(Integer, default=0)
    first_click_at = Column(DateTime(timezone=True), nullable=True)
    last_click_at = Column(DateTime(timezone=True), nullable=True)
    clicked_urls = Column(Text, nullable=True)  # JSON or comma-separated list of clicked links
    unsubscribed = Column(Boolean, default=False)
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)
    bounced = Column(Boolean, default=False)
    bounce_reason = Column(Text, nullable=True)
    engagement_score = Column(Float, default=0.0)

    # Form submission fields
    form_filled_at = Column(DateTime(timezone=True), nullable=True)
    submitted_availability = Column(Text, nullable=True)  # JSON list of ISO datetimes
    note = Column(Text, nullable=True)

    # Reply Agent fields (customer replies & AI responses)
    reply_body = Column(Text, nullable=True)
    reply_intent = Column(String, nullable=True)  # interested | question | reschedule | not_interested
    reply_received_at = Column(DateTime(timezone=True), nullable=True)
    ai_reply_sent = Column(Text, nullable=True)
    ai_reply_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Scheduler & Microsoft Teams meeting fields
    proposed_slot = Column(Text, nullable=True)  # JSON list of ISO datetimes
    confirmed_slot = Column(String, nullable=True)  # ISO datetime string
    meet_link = Column(String, nullable=True)  # Microsoft Teams join URL
    # booking_status: awaiting_scheduling | scheduled | alternates_proposed | needs_manual_scheduling
    booking_status = Column(String, nullable=True)
    scheduling_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class KnowledgeDocument(Base):
    """A chunk of company knowledge (FAQ, policy, pricing, product info)
    used to ground the reply agent's answers via retrieval-augmented
    generation (RAG). One source document is split into several rows
    sharing the same `title`; each row holds one chunk's text plus its
    embedding vector. Embeddings are stored as plain float arrays and
    compared with cosine similarity in Python (services/rag.py) — no
    pgvector extension required, just a standard Postgres database.
    """

    __tablename__ = "knowledge_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)  # source doc/FAQ name, shared across its chunks
    category = Column(String, nullable=True)  # e.g. "pricing", "support", "onboarding"
    content = Column(Text, nullable=False)  # this chunk's text
    embedding = Column(ARRAY(Float).with_variant(JSON, "sqlite"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProcessedReply(Base):
    """Tracks processed or suppressed Microsoft Outlook/Bookings message IDs to
    prevent duplicate responses and avoid re-ingestion of historical notifications.
    """

    __tablename__ = "processed_replies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String, unique=True, index=True, nullable=False)
    sender_email = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    status = Column(String, default="processed")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


