"""Master Database models — centralised lead management, import history,
chunking, outreach history, activity timeline, and audit logging.

All tables are additive; they do **not** modify existing campaign_log,
knowledge_documents, or processed_replies schemas.
"""

import uuid
from sqlalchemy import (
    Boolean, Column, Float, Integer, String, Text, Index,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.types import DateTime
from sqlalchemy.sql import func
from sqlalchemy import JSON

from .db import Base


# ─────────────────────────────────────────────────────────────
# 1. MASTER LEAD — single source of truth for every unique lead
# ─────────────────────────────────────────────────────────────

class MasterLead(Base):
    """One row per unique lead across the entire system.
    Identified primarily by normalised email address.
    """
    __tablename__ = "master_lead"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Contact info
    email = Column(String, nullable=False)
    email_normalized = Column(String, nullable=False, unique=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    company = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    website = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    location = Column(String, nullable=True)

    # Source & campaign
    lead_source = Column(String, nullable=True)

    # Scoring & status
    lead_score = Column(Float, default=0.0)
    current_status = Column(String, default="new")  # new | active | contacted | replied | booked | unsubscribed | bounced
    engagement_score = Column(Float, default=0.0)
    intent = Column(String, nullable=True)

    # Suppression flags
    unsubscribed = Column(Boolean, default=False)
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)
    bounced = Column(Boolean, default=False)
    bounce_reason = Column(Text, nullable=True)
    spam_reported = Column(Boolean, default=False)

    # Aggregate counters (denormalised for fast dashboard queries)
    total_emails_sent = Column(Integer, default=0)
    total_replies = Column(Integer, default=0)
    total_opens = Column(Integer, default=0)
    total_clicks = Column(Integer, default=0)
    total_followups = Column(Integer, default=0)

    # Timestamps
    last_contacted_at = Column(DateTime(timezone=True), nullable=True)
    last_reply_at = Column(DateTime(timezone=True), nullable=True)
    next_followup_at = Column(DateTime(timezone=True), nullable=True)
    booking_status = Column(String, nullable=True)

    # Extensibility
    custom_fields = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ─────────────────────────────────────────────────────────────
# 2. LEAD IMPORT — one record per uploaded file
# ─────────────────────────────────────────────────────────────

class LeadImport(Base):
    """Tracks every CSV/Excel file upload session."""
    __tablename__ = "lead_import"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    import_code = Column(String, nullable=True, index=True)  # e.g. IMP-2026-0925-001
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=True)  # csv | xlsx
    uploaded_by = Column(String, default="Admin")

    # Statistics
    total_records = Column(Integer, default=0)
    new_leads = Column(Integer, default=0)
    existing_leads = Column(Integer, default=0)
    duplicates = Column(Integer, default=0)
    invalid_records = Column(Integer, default=0)
    valid_emails = Column(Integer, default=0)
    invalid_emails = Column(Integer, default=0)
    new_template_assignments = Column(Integer, default=0)
    duplicate_template_sends = Column(Integer, default=0)

    # Chunking config
    chunk_size = Column(Integer, default=25)
    chunks_created = Column(Integer, default=0)

    # Status: preview | confirmed | processing | completed | failed
    status = Column(String, default="preview")
    error_message = Column(Text, nullable=True)

    config = Column(JSON, nullable=True)  # stores column mapping, options

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


# ─────────────────────────────────────────────────────────────
# 3. LEAD IMPORT RECORD — per-row outcome of an import
# ─────────────────────────────────────────────────────────────

class LeadImportRecord(Base):
    """One row per record in an uploaded file, recording what happened."""
    __tablename__ = "lead_import_record"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    import_id = Column(String, ForeignKey("lead_import.id"), nullable=False, index=True)
    master_lead_id = Column(String, ForeignKey("master_lead.id"), nullable=True, index=True)
    row_number = Column(Integer, nullable=True)

    # created | existing | duplicate_lead | duplicate_template | invalid_email | invalid_data
    action = Column(String, nullable=False)
    raw_data = Column(JSON, nullable=True)
    duplicate_of_id = Column(String, nullable=True)
    error_detail = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────────────────────────
# 4. LEAD CHUNK — batch of leads for template assignment
# ─────────────────────────────────────────────────────────────

CHUNK_STATUS_FLOW = [
    "IMPORTED",
    "DEDUPLICATED",
    "CHUNKED",
    "AWAITING_TEMPLATE",
    "TEMPLATE_ASSIGNED",
    "READY",
    "PROCESSING",
    "COMPLETED",
    "PARTIALLY_COMPLETED",
    "FAILED",
    "PAUSED",
    "CANCELLED",
]

# Valid transitions (from → set of allowed to)
CHUNK_STATUS_TRANSITIONS = {
    "IMPORTED": {"DEDUPLICATED", "CHUNKED", "AWAITING_TEMPLATE"},
    "DEDUPLICATED": {"CHUNKED", "AWAITING_TEMPLATE"},
    "CHUNKED": {"AWAITING_TEMPLATE"},
    "AWAITING_TEMPLATE": {"TEMPLATE_ASSIGNED", "CANCELLED"},
    "TEMPLATE_ASSIGNED": {"READY", "AWAITING_TEMPLATE", "CANCELLED"},
    "READY": {"PROCESSING", "PAUSED", "CANCELLED"},
    "PROCESSING": {"COMPLETED", "PARTIALLY_COMPLETED", "FAILED", "PAUSED"},
    "PAUSED": {"READY", "PROCESSING", "CANCELLED"},
    "PARTIALLY_COMPLETED": {"PROCESSING", "COMPLETED", "FAILED"},
    "COMPLETED": set(),
    "FAILED": {"READY", "PROCESSING"},
    "CANCELLED": set(),
}


class LeadChunk(Base):
    """A batch/chunk of leads grouped for template assignment and sending."""
    __tablename__ = "lead_chunk"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chunk_name = Column(String, nullable=False)  # e.g. CHUNK-001
    import_id = Column(String, ForeignKey("lead_import.id"), nullable=True, index=True)

    total_leads = Column(Integer, default=0)
    eligible_leads = Column(Integer, default=0)
    duplicate_template_leads = Column(Integer, default=0)

    # Template assignment (human-in-the-loop)
    template_id = Column(String, nullable=True)
    template_name = Column(String, nullable=True)
    template_assigned_at = Column(DateTime(timezone=True), nullable=True)
    assigned_by = Column(String, nullable=True)

    # Status tracking (state machine)
    processing_status = Column(String, default="AWAITING_TEMPLATE")
    email_sending_status = Column(String, nullable=True)

    # Counters
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    open_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    booking_count = Column(Integer, default=0)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────────────────────────
# 5. LEAD CHUNK MEMBER — links leads to chunks
# ─────────────────────────────────────────────────────────────

class LeadChunkMember(Base):
    """Associates a MasterLead with a LeadChunk."""
    __tablename__ = "lead_chunk_member"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chunk_id = Column(String, ForeignKey("lead_chunk.id"), nullable=False, index=True)
    master_lead_id = Column(String, ForeignKey("master_lead.id"), nullable=False, index=True)

    eligible = Column(Boolean, default=True)
    duplicate_template = Column(Boolean, default=False)
    override_approved = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("chunk_id", "master_lead_id", name="uq_chunk_member"),
    )


# ─────────────────────────────────────────────────────────────
# 6. OUTREACH HISTORY — which templates sent to which leads
# ─────────────────────────────────────────────────────────────

class OutreachHistory(Base):
    """Records every template sent (or attempted) to a lead.
    The UNIQUE constraint on (master_lead_id, template_id) prevents
    the same template being sent to the same lead twice, unless
    admin_override is set True on a new row.
    """
    __tablename__ = "outreach_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    master_lead_id = Column(String, ForeignKey("master_lead.id"), nullable=False, index=True)
    template_id = Column(String, nullable=True)
    template_name = Column(String, nullable=True)
    campaign_log_id = Column(String, ForeignKey("campaign_log.id"), nullable=True)
    chunk_id = Column(String, ForeignKey("lead_chunk.id"), nullable=True)

    # sent | failed | skipped_duplicate | pending | draft
    status = Column(String, default="pending")
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # Engagement snapshot
    opened = Column(Boolean, default=False)
    clicked = Column(Boolean, default=False)
    replied = Column(Boolean, default=False)
    booked = Column(Boolean, default=False)
    bounced = Column(Boolean, default=False)

    admin_override = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────────────────────────
# 7. LEAD ACTIVITY — chronological timeline for every lead
# ─────────────────────────────────────────────────────────────

class LeadActivity(Base):
    """Chronological event log for a lead's lifecycle."""
    __tablename__ = "lead_activity"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    master_lead_id = Column(String, ForeignKey("master_lead.id"), nullable=False, index=True)

    # lead_imported | assigned_to_chunk | template_assigned | email_sent |
    # email_opened | link_clicked | reply_received | followup_sent |
    # meeting_booked | status_changed | lead_updated | duplicate_detected
    activity_type = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    event_metadata = Column(JSON, nullable=True)
    campaign_log_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_lead_activity_lead_created", "master_lead_id", "created_at"),
    )


# ─────────────────────────────────────────────────────────────
# 8. AUDIT LOG — admin action tracking
# ─────────────────────────────────────────────────────────────

class AuditLog(Base):
    """Records every important admin/system action for traceability."""
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user = Column(String, default="Admin")
    action = Column(String, nullable=False)

    # lead | chunk | import | template_assignment | outreach | system
    entity_type = Column(String, nullable=True)
    entity_id = Column(String, nullable=True)

    previous_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_audit_log_entity", "entity_type", "created_at"),
    )
