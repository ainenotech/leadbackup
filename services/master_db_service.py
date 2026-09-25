"""Master Database service — business logic for lead ingestion, deduplication,
chunking, template assignment, outreach history, activity timeline, and audit logging.

All functions accept a SQLAlchemy Session and return plain dicts or model instances.
"""

import math
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session

from Backend.master_db_models import (
    MasterLead, LeadImport, LeadImportRecord,
    LeadChunk, LeadChunkMember, OutreachHistory,
    LeadActivity, AuditLog,
    CHUNK_STATUS_TRANSITIONS,
)


# ─────────────────────────────────────────────────────────────
# EMAIL NORMALISATION
# ─────────────────────────────────────────────────────────────

def normalize_email(email: str) -> str:
    """Normalize an email address for deduplication:
    lowercase, strip whitespace, remove accidental formatting.
    """
    if not email:
        return ""
    cleaned = email.strip().lower()
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned


def is_valid_email(email: str) -> bool:
    """Basic email format validation."""
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


# ─────────────────────────────────────────────────────────────
# AUDIT LOGGING
# ─────────────────────────────────────────────────────────────

def log_audit(
    db: Session,
    action: str,
    entity_type: str = None,
    entity_id: str = None,
    user: str = "Admin",
    previous_value: Any = None,
    new_value: Any = None,
) -> AuditLog:
    """Creates an audit log entry."""
    entry = AuditLog(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_value=previous_value,
        new_value=new_value,
    )
    db.add(entry)
    return entry


# ─────────────────────────────────────────────────────────────
# LEAD ACTIVITY LOGGING
# ─────────────────────────────────────────────────────────────

def log_activity(
    db: Session,
    master_lead_id: str,
    activity_type: str,
    description: str = None,
    event_metadata: Dict = None,
    campaign_log_id: str = None,
) -> LeadActivity:
    """Creates a timeline event for a lead."""
    entry = LeadActivity(
        master_lead_id=master_lead_id,
        activity_type=activity_type,
        description=description,
        event_metadata=event_metadata,
        campaign_log_id=campaign_log_id,
    )
    db.add(entry)
    return entry


# ─────────────────────────────────────────────────────────────
# LEAD LOOKUP / CREATION
# ─────────────────────────────────────────────────────────────

def find_lead_by_email(db: Session, email: str) -> Optional[MasterLead]:
    """Find an existing MasterLead by normalised email."""
    norm = normalize_email(email)
    if not norm:
        return None
    return db.query(MasterLead).filter(MasterLead.email_normalized == norm).first()


def create_or_update_lead(
    db: Session,
    email: str,
    first_name: str = None,
    last_name: str = None,
    full_name: str = None,
    company: str = None,
    phone: str = None,
    job_title: str = None,
    website: str = None,
    linkedin_url: str = None,
    industry: str = None,
    location: str = None,
    lead_source: str = None,
    custom_fields: Dict = None,
) -> Tuple[MasterLead, bool]:
    """Find or create a MasterLead. Returns (lead, is_new)."""
    norm = normalize_email(email)
    existing = db.query(MasterLead).filter(MasterLead.email_normalized == norm).first()

    if existing:
        # Update fields only if they were previously empty
        if first_name and not existing.first_name:
            existing.first_name = first_name
        if last_name and not existing.last_name:
            existing.last_name = last_name
        if full_name and not existing.full_name:
            existing.full_name = full_name
        if company and not existing.company:
            existing.company = company
        if phone and not existing.phone:
            existing.phone = phone
        if job_title and not existing.job_title:
            existing.job_title = job_title
        if website and not existing.website:
            existing.website = website
        if linkedin_url and not existing.linkedin_url:
            existing.linkedin_url = linkedin_url
        if industry and not existing.industry:
            existing.industry = industry
        if location and not existing.location:
            existing.location = location
        if lead_source and not existing.lead_source:
            existing.lead_source = lead_source
        return existing, False

    # Derive first/last from full_name if not provided
    if full_name and not first_name:
        parts = full_name.strip().split()
        first_name = parts[0] if parts else None
        last_name = " ".join(parts[1:]) if len(parts) > 1 else None

    lead = MasterLead(
        email=email.strip(),
        email_normalized=norm,
        first_name=first_name,
        last_name=last_name,
        full_name=full_name or (f"{first_name or ''} {last_name or ''}".strip() or None),
        company=company,
        phone=phone,
        job_title=job_title,
        website=website,
        linkedin_url=linkedin_url,
        industry=industry,
        location=location,
        lead_source=lead_source,
        custom_fields=custom_fields,
        current_status="new",
    )
    db.add(lead)
    db.flush()  # get ID without commit
    return lead, True


# ─────────────────────────────────────────────────────────────
# TEMPLATE DUPLICATE CHECK
# ─────────────────────────────────────────────────────────────

def has_template_been_sent(db: Session, master_lead_id: str, template_id: str) -> bool:
    """Check if this template has already been sent to this lead."""
    if not template_id:
        return False
    existing = db.query(OutreachHistory).filter(
        OutreachHistory.master_lead_id == master_lead_id,
        OutreachHistory.template_id == template_id,
        OutreachHistory.status.in_(["sent", "pending", "draft"]),
        OutreachHistory.admin_override == False,
    ).first()
    return existing is not None


def get_templates_sent_to_lead(db: Session, master_lead_id: str) -> List[Dict]:
    """Returns list of templates sent to a lead with statuses."""
    rows = db.query(OutreachHistory).filter(
        OutreachHistory.master_lead_id == master_lead_id,
    ).order_by(OutreachHistory.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "template_id": r.template_id,
            "template_name": r.template_name,
            "status": r.status,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            "opened": r.opened,
            "clicked": r.clicked,
            "replied": r.replied,
            "booked": r.booked,
            "admin_override": r.admin_override,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ─────────────────────────────────────────────────────────────
# IMPORT PREVIEW
# ─────────────────────────────────────────────────────────────

def _find_column(columns: List[str], target: str) -> Optional[str]:
    """Find best matching column name using fuzzy matching (reuses leads.py logic)."""
    lower_map = {str(c).strip().lower(): c for c in columns}
    mappings = {
        "email": ["email", "email_address", "email address", "e-mail", "mail", "contact_email", "work_email", "to"],
        "name": ["full_name", "fullname", "full name", "contact_name", "contact name", "name", "lead_name", "first_name", "firstname", "first name", "person", "contact"],
        "first_name": ["first_name", "firstname", "first name", "given_name"],
        "last_name": ["last_name", "lastname", "last name", "surname", "family_name"],
        "company": ["company", "company_name", "company name", "organization", "org_name", "account_name", "account", "business_name", "business"],
        "phone": ["phone", "phone_number", "phone number", "mobile", "telephone", "tel", "contact_number"],
        "job_title": ["job_title", "title", "position", "role", "designation"],
        "website": ["website", "url", "web", "site", "homepage"],
        "linkedin_url": ["linkedin", "linkedin_url", "linkedin url", "linkedin_profile"],
        "industry": ["industry", "sector", "vertical"],
        "location": ["location", "city", "state", "country", "address", "region"],
        "lead_source": ["source", "lead_source", "lead source", "origin", "channel"],
    }
    candidates = mappings.get(target, [target])
    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]
    # Fallback: partial match
    for c in columns:
        c_low = str(c).strip().lower()
        if target.replace("_", "") in c_low.replace("_", ""):
            return c
    return None


def generate_import_preview(
    db: Session,
    df: pd.DataFrame,
    template_id: str = None,
    filename: str = "upload",
) -> Dict:
    """Analyses a DataFrame without inserting anything.
    Returns preview statistics for the admin to review.
    """
    columns = list(df.columns)
    email_col = _find_column(columns, "email")
    if not email_col:
        return {"error": "No email column found in uploaded file.", "columns": columns}

    name_col = _find_column(columns, "name")
    first_name_col = _find_column(columns, "first_name")
    last_name_col = _find_column(columns, "last_name")
    company_col = _find_column(columns, "company")
    phone_col = _find_column(columns, "phone")
    job_title_col = _find_column(columns, "job_title")

    total = len(df)
    new_leads = 0
    existing_leads = 0
    duplicate_leads = 0
    valid_emails = 0
    invalid_emails = 0
    new_template_assignments = 0
    duplicate_template_sends = 0

    seen_in_file: Set[str] = set()
    preview_rows = []

    for idx, row in df.iterrows():
        raw_email = row.get(email_col)
        if pd.isna(raw_email) or not str(raw_email).strip():
            invalid_emails += 1
            preview_rows.append({"row": idx + 1, "email": "", "action": "invalid_data", "reason": "Empty email"})
            continue

        email = str(raw_email).strip()
        norm = normalize_email(email)

        if not is_valid_email(email):
            invalid_emails += 1
            preview_rows.append({"row": idx + 1, "email": email, "action": "invalid_email", "reason": "Invalid format"})
            continue

        valid_emails += 1

        # Duplicate within the file itself
        if norm in seen_in_file:
            duplicate_leads += 1
            preview_rows.append({"row": idx + 1, "email": email, "action": "duplicate_lead", "reason": "Duplicate in file"})
            continue
        seen_in_file.add(norm)

        # Check against Master DB
        existing_lead = db.query(MasterLead).filter(MasterLead.email_normalized == norm).first()
        if existing_lead:
            existing_leads += 1
            # Check template-specific duplicate
            if template_id and has_template_been_sent(db, existing_lead.id, template_id):
                duplicate_template_sends += 1
                preview_rows.append({"row": idx + 1, "email": email, "action": "duplicate_template", "reason": f"Template already sent"})
            else:
                if template_id:
                    new_template_assignments += 1
                preview_rows.append({"row": idx + 1, "email": email, "action": "existing", "reason": "Lead exists, new assignment"})
        else:
            new_leads += 1
            if template_id:
                new_template_assignments += 1
            preview_rows.append({"row": idx + 1, "email": email, "action": "new", "reason": "New lead"})

    return {
        "filename": filename,
        "total_records": total,
        "new_leads": new_leads,
        "existing_leads": existing_leads,
        "duplicate_leads": duplicate_leads,
        "valid_emails": valid_emails,
        "invalid_emails": invalid_emails,
        "new_template_assignments": new_template_assignments,
        "duplicate_template_sends": duplicate_template_sends,
        "column_mapping": {
            "email": email_col,
            "name": name_col,
            "first_name": first_name_col,
            "last_name": last_name_col,
            "company": company_col,
            "phone": phone_col,
            "job_title": job_title_col,
        },
        "preview_rows": preview_rows[:100],  # show first 100 for preview
    }


# ─────────────────────────────────────────────────────────────
# IMPORT CONFIRMATION (Ingestion Pipeline)
# ─────────────────────────────────────────────────────────────

def confirm_import(
    db: Session,
    df: pd.DataFrame,
    filename: str,
    file_type: str,
    chunk_size: int = 25,
    template_id: str = None,
    template_name: str = None,
    uploaded_by: str = "Admin",
    column_mapping: Dict = None,
) -> Dict:
    """
    Full ingestion pipeline:
    1. Create import record
    2. Iterate rows → create/match leads
    3. Create import records per row
    4. Chunk leads
    5. Return summary
    """
    now = datetime.now(timezone.utc)
    import_code = f"IMP-{now.strftime('%Y-%m%d')}-{str(uuid.uuid4())[:6].upper()}"

    # Create import record
    imp = LeadImport(
        import_code=import_code,
        filename=filename,
        file_type=file_type,
        uploaded_by=uploaded_by,
        total_records=len(df),
        chunk_size=chunk_size,
        status="processing",
    )
    db.add(imp)
    db.flush()

    log_audit(db, "import_started", "import", imp.id, uploaded_by,
              new_value={"filename": filename, "total_records": len(df)})

    # Column mapping
    cm = column_mapping or {}
    email_col = cm.get("email") or _find_column(list(df.columns), "email")
    name_col = cm.get("name") or _find_column(list(df.columns), "name")
    first_name_col = cm.get("first_name") or _find_column(list(df.columns), "first_name")
    last_name_col = cm.get("last_name") or _find_column(list(df.columns), "last_name")
    company_col = cm.get("company") or _find_column(list(df.columns), "company")
    phone_col = cm.get("phone") or _find_column(list(df.columns), "phone")
    job_title_col = cm.get("job_title") or _find_column(list(df.columns), "job_title")
    website_col = _find_column(list(df.columns), "website")
    linkedin_col = _find_column(list(df.columns), "linkedin_url")
    industry_col = _find_column(list(df.columns), "industry")
    location_col = _find_column(list(df.columns), "location")
    source_col = _find_column(list(df.columns), "lead_source")

    if not email_col:
        imp.status = "failed"
        imp.error_message = "No email column found"
        db.commit()
        return {"error": "No email column found", "import_id": imp.id}

    # Process each row
    new_count = 0
    existing_count = 0
    dup_count = 0
    invalid_count = 0
    valid_email_count = 0
    invalid_email_count = 0
    new_tpl_count = 0
    dup_tpl_count = 0

    eligible_leads: List[str] = []  # master_lead_ids for chunking
    seen_in_file: Set[str] = set()

    def _get_val(row, col):
        if not col or col not in row.index:
            return None
        v = row.get(col)
        if pd.isna(v):
            return None
        s = str(v).strip()
        return s if s and s.lower() not in ("nan", "none", "") else None

    for idx, row in df.iterrows():
        raw_email = _get_val(row, email_col)
        if not raw_email:
            invalid_count += 1
            db.add(LeadImportRecord(
                import_id=imp.id, row_number=idx + 1,
                action="invalid_data", error_detail="Empty email",
                raw_data={"email": ""},
            ))
            continue

        norm = normalize_email(raw_email)
        if not is_valid_email(raw_email):
            invalid_email_count += 1
            invalid_count += 1
            db.add(LeadImportRecord(
                import_id=imp.id, row_number=idx + 1,
                action="invalid_email", error_detail="Invalid email format",
                raw_data={"email": raw_email},
            ))
            continue

        valid_email_count += 1

        if norm in seen_in_file:
            dup_count += 1
            db.add(LeadImportRecord(
                import_id=imp.id, row_number=idx + 1,
                action="duplicate_lead", error_detail="Duplicate within file",
                raw_data={"email": raw_email},
            ))
            continue
        seen_in_file.add(norm)

        # Extract lead fields
        first_name = _get_val(row, first_name_col)
        last_name = _get_val(row, last_name_col)
        full_name = _get_val(row, name_col)
        company = _get_val(row, company_col)
        phone = _get_val(row, phone_col)
        job_title = _get_val(row, job_title_col)
        website = _get_val(row, website_col)
        linkedin = _get_val(row, linkedin_col)
        industry = _get_val(row, industry_col)
        location = _get_val(row, location_col)
        source = _get_val(row, source_col) or filename

        lead, is_new = create_or_update_lead(
            db, raw_email,
            first_name=first_name, last_name=last_name, full_name=full_name,
            company=company, phone=phone, job_title=job_title,
            website=website, linkedin_url=linkedin,
            industry=industry, location=location, lead_source=source,
        )

        if is_new:
            new_count += 1
            action = "created"
            log_activity(db, lead.id, "lead_imported",
                         f"Lead imported from {filename}")
        else:
            existing_count += 1
            action = "existing"

        # Template-specific duplicate check
        if template_id:
            if has_template_been_sent(db, lead.id, template_id):
                dup_tpl_count += 1
                db.add(LeadImportRecord(
                    import_id=imp.id, row_number=idx + 1,
                    master_lead_id=lead.id, action="duplicate_template",
                    raw_data={"email": raw_email},
                    error_detail=f"Template {template_id} already sent",
                ))
                continue
            else:
                new_tpl_count += 1

        db.add(LeadImportRecord(
            import_id=imp.id, row_number=idx + 1,
            master_lead_id=lead.id, action=action,
            raw_data={"email": raw_email, "name": full_name or first_name, "company": company},
        ))
        eligible_leads.append(lead.id)

    # Chunk the eligible leads
    chunks_created = 0
    if eligible_leads and chunk_size > 0:
        total_chunks = math.ceil(len(eligible_leads) / chunk_size)
        for i in range(total_chunks):
            chunk_leads = eligible_leads[i * chunk_size : (i + 1) * chunk_size]
            chunks_created += 1
            chunk_name = f"CHUNK-{chunks_created:03d}"

            chunk = LeadChunk(
                chunk_name=chunk_name,
                import_id=imp.id,
                total_leads=len(chunk_leads),
                processing_status="AWAITING_TEMPLATE",
            )
            db.add(chunk)
            db.flush()

            for lead_id in chunk_leads:
                db.add(LeadChunkMember(
                    chunk_id=chunk.id,
                    master_lead_id=lead_id,
                ))
                log_activity(db, lead_id, "assigned_to_chunk",
                             f"Assigned to {chunk_name}")

            log_audit(db, "chunk_created", "chunk", chunk.id, uploaded_by,
                      new_value={"chunk_name": chunk_name, "total_leads": len(chunk_leads)})

    # Finalise import record
    imp.new_leads = new_count
    imp.existing_leads = existing_count
    imp.duplicates = dup_count
    imp.invalid_records = invalid_count
    imp.valid_emails = valid_email_count
    imp.invalid_emails = invalid_email_count
    imp.new_template_assignments = new_tpl_count
    imp.duplicate_template_sends = dup_tpl_count
    imp.chunks_created = chunks_created
    imp.status = "completed"
    imp.completed_at = datetime.now(timezone.utc)

    log_audit(db, "import_completed", "import", imp.id, uploaded_by,
              new_value={
                  "new_leads": new_count, "existing": existing_count,
                  "duplicates": dup_count, "chunks": chunks_created,
              })

    db.commit()

    return {
        "import_id": imp.id,
        "import_code": imp.import_code,
        "status": "completed",
        "total_records": len(df),
        "new_leads": new_count,
        "existing_leads": existing_count,
        "duplicates": dup_count,
        "invalid_records": invalid_count,
        "valid_emails": valid_email_count,
        "invalid_emails": invalid_email_count,
        "new_template_assignments": new_tpl_count,
        "duplicate_template_sends": dup_tpl_count,
        "chunks_created": chunks_created,
        "chunk_size": chunk_size,
    }


# ─────────────────────────────────────────────────────────────
# CHUNK MANAGEMENT
# ─────────────────────────────────────────────────────────────

def get_all_chunks(db: Session) -> List[Dict]:
    """Returns all chunks with summary stats."""
    chunks = db.query(LeadChunk).order_by(LeadChunk.created_at.desc()).all()
    return [_chunk_to_dict(c) for c in chunks]


def _chunk_to_dict(c: LeadChunk) -> Dict:
    return {
        "id": c.id,
        "chunk_name": c.chunk_name,
        "import_id": c.import_id,
        "total_leads": c.total_leads,
        "eligible_leads": c.eligible_leads,
        "duplicate_template_leads": c.duplicate_template_leads,
        "template_id": c.template_id,
        "template_name": c.template_name,
        "template_assigned_at": c.template_assigned_at.isoformat() if c.template_assigned_at else None,
        "assigned_by": c.assigned_by,
        "processing_status": c.processing_status,
        "sent_count": c.sent_count,
        "failed_count": c.failed_count,
        "reply_count": c.reply_count,
        "open_count": c.open_count,
        "click_count": c.click_count,
        "booking_count": c.booking_count,
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "completed_at": c.completed_at.isoformat() if c.completed_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def get_chunk_leads(db: Session, chunk_id: str) -> List[Dict]:
    """Returns all leads in a chunk with their eligibility status."""
    members = db.query(LeadChunkMember).filter(LeadChunkMember.chunk_id == chunk_id).all()
    result = []
    for m in members:
        lead = db.query(MasterLead).filter(MasterLead.id == m.master_lead_id).first()
        if lead:
            result.append({
                "member_id": m.id,
                "lead_id": lead.id,
                "email": lead.email,
                "full_name": lead.full_name,
                "company": lead.company,
                "industry": lead.industry,
                "current_status": lead.current_status,
                "eligible": m.eligible,
                "duplicate_template": m.duplicate_template,
                "override_approved": m.override_approved,
            })
    return result


def transition_chunk_status(
    db: Session, chunk_id: str, new_status: str, user: str = "Admin"
) -> Dict:
    """Validates and applies a chunk status transition."""
    chunk = db.query(LeadChunk).filter(LeadChunk.id == chunk_id).first()
    if not chunk:
        return {"error": "Chunk not found"}

    current = chunk.processing_status
    allowed = CHUNK_STATUS_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        return {"error": f"Invalid transition: {current} → {new_status}. Allowed: {allowed}"}

    old_status = chunk.processing_status
    chunk.processing_status = new_status

    if new_status == "PROCESSING" and not chunk.started_at:
        chunk.started_at = datetime.now(timezone.utc)
    elif new_status in ("COMPLETED", "PARTIALLY_COMPLETED"):
        chunk.completed_at = datetime.now(timezone.utc)

    log_audit(db, "chunk_status_changed", "chunk", chunk.id, user,
              previous_value={"status": old_status},
              new_value={"status": new_status})
    db.commit()

    return {"success": True, "chunk_id": chunk.id, "old_status": old_status, "new_status": new_status}


# ─────────────────────────────────────────────────────────────
# TEMPLATE ASSIGNMENT (Human-in-the-Loop)
# ─────────────────────────────────────────────────────────────

def assign_template_to_chunk(
    db: Session,
    chunk_id: str,
    template_id: str,
    template_name: str,
    assigned_by: str = "Admin",
    exclude_duplicates: bool = True,
) -> Dict:
    """
    Assigns a template to a chunk, running template-specific duplicate checks
    on every lead in the chunk.
    """
    chunk = db.query(LeadChunk).filter(LeadChunk.id == chunk_id).first()
    if not chunk:
        return {"error": "Chunk not found"}

    if chunk.processing_status not in ("AWAITING_TEMPLATE", "TEMPLATE_ASSIGNED"):
        return {"error": f"Cannot assign template in status: {chunk.processing_status}"}

    # Check each lead for template duplicates
    members = db.query(LeadChunkMember).filter(LeadChunkMember.chunk_id == chunk_id).all()
    eligible = 0
    dup_count = 0

    for member in members:
        is_dup = has_template_been_sent(db, member.master_lead_id, template_id)
        member.duplicate_template = is_dup
        if is_dup and exclude_duplicates:
            member.eligible = False
            dup_count += 1
        else:
            member.eligible = True
            eligible += 1
            # Create outreach history record
            existing_oh = db.query(OutreachHistory).filter(
                OutreachHistory.master_lead_id == member.master_lead_id,
                OutreachHistory.template_id == template_id,
                OutreachHistory.chunk_id == chunk_id,
            ).first()
            if not existing_oh:
                db.add(OutreachHistory(
                    master_lead_id=member.master_lead_id,
                    template_id=template_id,
                    template_name=template_name,
                    chunk_id=chunk_id,
                    status="pending",
                ))
            log_activity(db, member.master_lead_id, "template_assigned",
                         f"Template '{template_name}' assigned via {chunk.chunk_name}")

    old_template = chunk.template_name
    chunk.template_id = template_id
    chunk.template_name = template_name
    chunk.template_assigned_at = datetime.now(timezone.utc)
    chunk.assigned_by = assigned_by
    chunk.eligible_leads = eligible
    chunk.duplicate_template_leads = dup_count
    chunk.processing_status = "TEMPLATE_ASSIGNED"

    log_audit(db, "template_assigned", "chunk", chunk.id, assigned_by,
              previous_value={"template": old_template},
              new_value={"template_id": template_id, "template_name": template_name,
                         "eligible": eligible, "duplicates": dup_count})
    db.commit()

    return {
        "success": True,
        "chunk_id": chunk.id,
        "chunk_name": chunk.chunk_name,
        "template_id": template_id,
        "template_name": template_name,
        "total_leads": len(members),
        "eligible_leads": eligible,
        "duplicate_template_leads": dup_count,
    }


# ─────────────────────────────────────────────────────────────
# DASHBOARD METRICS
# ─────────────────────────────────────────────────────────────

def get_dashboard_metrics(db: Session) -> Dict:
    """Aggregated overview metrics for the CEO dashboard."""
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    total = db.query(func.count(MasterLead.id)).scalar() or 0
    new_this_week = db.query(func.count(MasterLead.id)).filter(
        MasterLead.created_at >= week_ago
    ).scalar() or 0

    status_counts = {}
    for status_val in ["new", "active", "contacted", "replied", "booked", "unsubscribed", "bounced"]:
        cnt = db.query(func.count(MasterLead.id)).filter(
            MasterLead.current_status == status_val
        ).scalar() or 0
        status_counts[status_val] = cnt

    # Import stats
    total_imports = db.query(func.count(LeadImport.id)).scalar() or 0
    total_dup_records = db.query(func.coalesce(func.sum(LeadImport.duplicates), 0)).scalar() or 0

    # Chunk pipeline
    chunk_statuses = {}
    for s in ["AWAITING_TEMPLATE", "TEMPLATE_ASSIGNED", "READY", "PROCESSING", "COMPLETED",
              "PARTIALLY_COMPLETED", "FAILED", "PAUSED", "CANCELLED"]:
        cnt = db.query(func.count(LeadChunk.id)).filter(LeadChunk.processing_status == s).scalar() or 0
        chunk_statuses[s] = cnt

    # Outreach stats
    total_sent = db.query(func.coalesce(func.sum(MasterLead.total_emails_sent), 0)).scalar() or 0
    total_replies = db.query(func.count(MasterLead.id)).filter(MasterLead.total_replies > 0).scalar() or 0
    total_booked = db.query(func.count(MasterLead.id)).filter(
        MasterLead.booking_status.in_(["scheduled", "confirmed", "meeting_scheduled", "booked"])
    ).scalar() or 0

    return {
        "total_leads": total,
        "new_this_week": new_this_week,
        "duplicate_records": total_dup_records,
        "status_counts": status_counts,
        "total_imports": total_imports,
        "chunk_pipeline": chunk_statuses,
        "active_outreach": chunk_statuses.get("PROCESSING", 0) + chunk_statuses.get("READY", 0),
        "total_emails_sent": total_sent,
        "total_replies": total_replies,
        "total_booked": total_booked,
    }


# ─────────────────────────────────────────────────────────────
# LEAD QUERIES (Paginated, Searchable, Filterable)
# ─────────────────────────────────────────────────────────────

def get_leads_paginated(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    search: str = None,
    status_filter: str = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> Dict:
    """Returns paginated, filtered, searchable lead list."""
    query = db.query(MasterLead)

    if search:
        search_term = f"%{search.strip().lower()}%"
        query = query.filter(or_(
            func.lower(MasterLead.email).like(search_term),
            func.lower(MasterLead.full_name).like(search_term),
            func.lower(MasterLead.company).like(search_term),
            func.lower(MasterLead.first_name).like(search_term),
            func.lower(MasterLead.last_name).like(search_term),
        ))

    if status_filter and status_filter != "all":
        query = query.filter(MasterLead.current_status == status_filter)

    total = query.count()

    # Sorting
    sort_col = getattr(MasterLead, sort_by, MasterLead.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    offset = (page - 1) * page_size
    leads = query.offset(offset).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total > 0 else 1,
        "leads": [_lead_to_dict(l) for l in leads],
    }


def _lead_to_dict(l: MasterLead) -> Dict:
    return {
        "id": l.id,
        "email": l.email,
        "first_name": l.first_name,
        "last_name": l.last_name,
        "full_name": l.full_name,
        "phone": l.phone,
        "company": l.company,
        "job_title": l.job_title,
        "website": l.website,
        "linkedin_url": l.linkedin_url,
        "industry": l.industry,
        "location": l.location,
        "lead_source": l.lead_source,
        "lead_score": l.lead_score,
        "current_status": l.current_status,
        "engagement_score": l.engagement_score,
        "intent": l.intent,
        "total_emails_sent": l.total_emails_sent,
        "total_replies": l.total_replies,
        "total_opens": l.total_opens,
        "total_clicks": l.total_clicks,
        "booking_status": l.booking_status,
        "unsubscribed": l.unsubscribed,
        "bounced": l.bounced,
        "last_contacted_at": l.last_contacted_at.isoformat() if l.last_contacted_at else None,
        "last_reply_at": l.last_reply_at.isoformat() if l.last_reply_at else None,
        "created_at": l.created_at.isoformat() if l.created_at else None,
        "updated_at": l.updated_at.isoformat() if l.updated_at else None,
    }


def get_lead_detail(db: Session, lead_id: str) -> Optional[Dict]:
    """Full lead detail with outreach history and timeline."""
    lead = db.query(MasterLead).filter(MasterLead.id == lead_id).first()
    if not lead:
        return None

    detail = _lead_to_dict(lead)

    # Outreach history
    detail["outreach_history"] = get_templates_sent_to_lead(db, lead.id)

    # Activity timeline
    activities = db.query(LeadActivity).filter(
        LeadActivity.master_lead_id == lead.id
    ).order_by(LeadActivity.created_at.desc()).limit(100).all()
    detail["timeline"] = [
        {
            "id": a.id,
            "type": a.activity_type,
            "description": a.description,
            "metadata": a.metadata,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in activities
    ]

    # Chunk memberships
    memberships = db.query(LeadChunkMember).filter(
        LeadChunkMember.master_lead_id == lead.id
    ).all()
    chunks_info = []
    for m in memberships:
        chunk = db.query(LeadChunk).filter(LeadChunk.id == m.chunk_id).first()
        if chunk:
            chunks_info.append({
                "chunk_id": chunk.id,
                "chunk_name": chunk.chunk_name,
                "template_name": chunk.template_name,
                "status": chunk.processing_status,
                "eligible": m.eligible,
            })
    detail["chunks"] = chunks_info

    return detail


# ─────────────────────────────────────────────────────────────
# IMPORT HISTORY
# ─────────────────────────────────────────────────────────────

def get_all_imports(db: Session) -> List[Dict]:
    """Returns all import records."""
    imports = db.query(LeadImport).order_by(LeadImport.created_at.desc()).all()
    return [
        {
            "id": i.id,
            "import_code": i.import_code,
            "filename": i.filename,
            "file_type": i.file_type,
            "uploaded_by": i.uploaded_by,
            "total_records": i.total_records,
            "new_leads": i.new_leads,
            "existing_leads": i.existing_leads,
            "duplicates": i.duplicates,
            "invalid_records": i.invalid_records,
            "valid_emails": i.valid_emails,
            "invalid_emails": i.invalid_emails,
            "chunks_created": i.chunks_created,
            "chunk_size": i.chunk_size,
            "status": i.status,
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "completed_at": i.completed_at.isoformat() if i.completed_at else None,
        }
        for i in imports
    ]


def get_import_detail(db: Session, import_id: str) -> Optional[Dict]:
    """Returns import detail with per-record breakdown."""
    imp = db.query(LeadImport).filter(LeadImport.id == import_id).first()
    if not imp:
        return None

    records = db.query(LeadImportRecord).filter(
        LeadImportRecord.import_id == import_id
    ).order_by(LeadImportRecord.row_number).all()

    return {
        "id": imp.id,
        "import_code": imp.import_code,
        "filename": imp.filename,
        "uploaded_by": imp.uploaded_by,
        "total_records": imp.total_records,
        "new_leads": imp.new_leads,
        "existing_leads": imp.existing_leads,
        "duplicates": imp.duplicates,
        "invalid_records": imp.invalid_records,
        "chunks_created": imp.chunks_created,
        "status": imp.status,
        "created_at": imp.created_at.isoformat() if imp.created_at else None,
        "records": [
            {
                "row": r.row_number,
                "action": r.action,
                "email": r.raw_data.get("email", "") if r.raw_data else "",
                "error": r.error_detail,
            }
            for r in records
        ],
    }


# ─────────────────────────────────────────────────────────────
# AUDIT LOG QUERIES
# ─────────────────────────────────────────────────────────────

def get_audit_log(db: Session, limit: int = 200, entity_type: str = None) -> List[Dict]:
    """Returns recent audit log entries."""
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    entries = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "user": e.user,
            "action": e.action,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "previous_value": e.previous_value,
            "new_value": e.new_value,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


# ─────────────────────────────────────────────────────────────
# BACKFILL: Populate MasterLead from existing campaign_log
# ─────────────────────────────────────────────────────────────

def backfill_from_campaign_log(db: Session) -> Dict:
    """Full synchronization: syncs MasterLead, LeadImport, LeadChunk, OutreachHistory,
    and LeadActivity from existing campaign_log rows and leads.xlsx using fast in-memory batching.
    """
    from Backend.models import CampaignLog

    camp_logs = db.query(CampaignLog).all()
    if not camp_logs:
        return {"created": 0, "updated": 0, "linked": 0}

    # Load rich metadata from leads.xlsx if present
    leads_meta = {}
    try:
        if os.path.exists("leads.xlsx"):
            df_leads = pd.read_excel("leads.xlsx")
            for _, r in df_leads.iterrows():
                em = str(r.get("email", "")).strip().lower()
                if em and "@" in em:
                    leads_meta[em] = {
                        "job_title": None if pd.isna(r.get("job_title")) else str(r.get("job_title")),
                        "location": None if pd.isna(r.get("location")) else str(r.get("location")),
                        "linkedin_url": None if pd.isna(r.get("links")) else str(r.get("links")),
                        "phone": None if pd.isna(r.get("phone_numbers") or r.get("Mobile No")) else str(r.get("phone_numbers") or r.get("Mobile No")),
                        "industry": None if pd.isna(r.get("company_industries")) else str(r.get("company_industries")),
                    }
    except Exception as ex:
        print("[backfill notice] leads.xlsx metadata note:", ex)

    # Preload existing MasterLeads into memory
    all_leads = db.query(MasterLead).all()
    leads_by_email = {l.email_normalized: l for l in all_leads if l.email_normalized}

    # Preload existing OutreachHistory into a lookup map
    all_oh = db.query(OutreachHistory).all()
    oh_set = {(oh.master_lead_id, oh.campaign_log_id): oh for oh in all_oh}

    # Ensure baseline LeadImport exists so Batch History tab displays the batch
    imp = db.query(LeadImport).first()
    if not imp:
        imp = LeadImport(
            import_code="IMP-INIT-MASTER-001",
            filename="leads.xlsx",
            file_type="xlsx",
            uploaded_by="System Initial Sync",
            total_records=len(camp_logs),
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        db.add(imp)
        db.flush()
    import_id = imp.id

    created_count = 0
    updated_count = 0

    for r in camp_logs:
        if not r.email:
            continue
        em = r.email.strip().lower()
        lead = leads_by_email.get(em)
        meta = leads_meta.get(em, {})

        if not lead:
            parts = (r.name or "").strip().split()
            fname = parts[0] if parts else None
            lname = " ".join(parts[1:]) if len(parts) > 1 else None
            lead = MasterLead(
                email=r.email.strip(),
                email_normalized=em,
                first_name=fname,
                last_name=lname,
                full_name=r.name,
                company=r.company,
                phone=getattr(r, "phone", None) or meta.get("phone"),
                job_title=meta.get("job_title"),
                location=meta.get("location"),
                linkedin_url=meta.get("linkedin_url"),
                industry=meta.get("industry"),
                lead_source="leads.xlsx",
                current_status="new",
                total_emails_sent=0,
                total_replies=0,
                total_opens=0,
                total_clicks=0,
            )
            db.add(lead)
            db.flush()
            leads_by_email[em] = lead
            created_count += 1
        else:
            updated_count += 1
            if not lead.job_title and meta.get("job_title"):
                lead.job_title = meta["job_title"]
            if not lead.location and meta.get("location"):
                lead.location = meta["location"]
            if not lead.linkedin_url and meta.get("linkedin_url"):
                lead.linkedin_url = meta["linkedin_url"]
            if not lead.phone and meta.get("phone"):
                lead.phone = meta["phone"]

        r.master_lead_id = lead.id

        # Update metrics accurately for both new and existing leads
        if r.status in ("sent", "delivered"):
            lead.total_emails_sent = (lead.total_emails_sent or 0) + 1
            lead.last_contacted_at = r.email_sent_at or getattr(r, "contacted_at", None) or lead.last_contacted_at
            if lead.current_status in ("new", "active"):
                lead.current_status = "contacted"

        if r.opened:
            lead.total_opens = (lead.total_opens or 0) + (r.open_count or 1)

        if r.clicked_link:
            lead.total_clicks = (lead.total_clicks or 0) + (r.click_count or 1)

        if r.reply_received_at or r.status == "replied":
            lead.total_replies = (lead.total_replies or 0) + 1
            lead.current_status = "replied"
            lead.last_reply_at = r.reply_received_at or lead.last_reply_at

        if r.booking_status in ("scheduled", "meeting_scheduled", "confirmed", "booked"):
            lead.current_status = "booked"
            lead.booking_status = r.booking_status

        if r.unsubscribed or r.status == "opted_out":
            lead.current_status = "unsubscribed"
            lead.unsubscribed = True
            lead.unsubscribed_at = r.unsubscribed_at

        if r.bounced:
            lead.current_status = "bounced"
            lead.bounced = True
            lead.bounce_reason = r.bounce_reason

        if r.engagement_score and (r.engagement_score > (lead.engagement_score or 0)):
            lead.engagement_score = float(r.engagement_score)

        # Outreach history tracking
        key = (lead.id, r.id)
        if key not in oh_set:
            oh = OutreachHistory(
                master_lead_id=lead.id,
                template_id=r.template_id,
                template_name=r.template_name,
                campaign_log_id=r.id,
                status=r.status or "sent",
                sent_at=r.email_sent_at or getattr(r, "contacted_at", None),
                opened=r.opened or False,
                clicked=r.clicked_link or False,
                replied=bool(r.reply_received_at or r.status == "replied"),
                booked=bool(r.booking_status in ("scheduled", "meeting_scheduled", "confirmed", "booked")),
                bounced=r.bounced or False,
            )
            db.add(oh)
            oh_set[key] = oh

    # Intelligent Chunks creation if none exist
    chunk_count = db.query(LeadChunk).count()
    if chunk_count == 0:
        tpl_groups = {}
        for r in camp_logs:
            t_id = r.template_id or "tpl_general"
            t_name = r.template_name or "General Outreach Template"
            if (t_id, t_name) not in tpl_groups:
                tpl_groups[(t_id, t_name)] = []
            if r.master_lead_id:
                tpl_groups[(t_id, t_name)].append(r)

        chunk_idx = 1
        for (t_id, t_name), logs_in_tpl in tpl_groups.items():
            chunk_obj = LeadChunk(
                chunk_name=f"CHUNK-{chunk_idx:03d} ({t_name[:24]})",
                import_id=import_id,
                template_id=t_id,
                template_name=t_name,
                assigned_by="System Sync",
                template_assigned_at=datetime.now(timezone.utc),
                total_leads=len(logs_in_tpl),
                eligible_leads=len(logs_in_tpl),
                duplicate_template_leads=0,
                processing_status="COMPLETED",
                sent_count=sum(1 for x in logs_in_tpl if x.status in ("sent", "delivered", "replied", "opted_out")),
                reply_count=sum(1 for x in logs_in_tpl if x.reply_received_at or x.status == "replied"),
                open_count=sum(x.open_count or (1 if x.opened else 0) for x in logs_in_tpl),
                click_count=sum(x.click_count or (1 if x.clicked_link else 0) for x in logs_in_tpl),
                booking_count=sum(1 for x in logs_in_tpl if x.booking_status in ("scheduled", "meeting_scheduled", "confirmed", "booked")),
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            db.add(chunk_obj)
            db.flush()

            for x in logs_in_tpl:
                db.add(LeadChunkMember(
                    chunk_id=chunk_obj.id,
                    master_lead_id=x.master_lead_id,
                    eligible=True,
                ))
                oh = oh_set.get((x.master_lead_id, x.id))
                if oh:
                    oh.chunk_id = chunk_obj.id

            chunk_idx += 1

    # LeadActivity event stream population if none exist
    act_count = db.query(LeadActivity).count()
    if act_count == 0:
        for l_id, lead in list(leads_by_email.items())[:50]:
            db.add(LeadActivity(
                master_lead_id=lead.id,
                activity_type="lead_imported",
                description=f"Lead record imported from {lead.lead_source or 'leads.xlsx'}",
                created_at=lead.created_at or datetime.now(timezone.utc),
            ))
            if lead.total_emails_sent and lead.total_emails_sent > 0:
                db.add(LeadActivity(
                    master_lead_id=lead.id,
                    activity_type="outreach_sent",
                    description=f"Outreach email dispatched to {lead.email}",
                    created_at=lead.last_contacted_at or datetime.now(timezone.utc),
                ))

    # AuditLog entry if none exist
    audit_count = db.query(AuditLog).count()
    if audit_count == 0:
        db.add(AuditLog(
            action="system_sync_completed",
            entity_type="system",
            entity_id=str(import_id),
            user="System Migration",
            new_value={
                "total_campaign_logs": len(camp_logs),
                "total_master_leads": len(leads_by_email),
                "status": "synchronized"
            }
        ))

    db.commit()
    return {"created": created_count, "updated": updated_count, "linked": len(camp_logs)}


def sync_campaign_entry_to_master_db(db: Session, entry) -> Optional[MasterLead]:
    """Live synchronization helper: called whenever an email is sent or updated via CampaignLog."""
    if not entry or not entry.email:
        return None
    try:
        norm = normalize_email(entry.email)
        lead = db.query(MasterLead).filter(MasterLead.email_normalized == norm).first()
        if not lead:
            parts = (entry.name or "").strip().split()
            lead = MasterLead(
                email=entry.email.strip(),
                email_normalized=norm,
                first_name=parts[0] if parts else None,
                last_name=" ".join(parts[1:]) if len(parts) > 1 else None,
                full_name=entry.name,
                company=entry.company,
                current_status="new",
                total_emails_sent=0,
                total_replies=0,
            )
            db.add(lead)
            db.flush()

        entry.master_lead_id = lead.id

        if entry.status in ("sent", "delivered"):
            lead.total_emails_sent = (lead.total_emails_sent or 0) + 1
            lead.current_status = "contacted"
            lead.last_contacted_at = entry.email_sent_at or datetime.now(timezone.utc)
            log_activity(db, lead.id, "email_sent", f"Email dispatched: {entry.subject or ''}")

        if entry.reply_received_at or entry.status == "replied":
            lead.total_replies = (lead.total_replies or 0) + 1
            lead.current_status = "replied"
            lead.last_reply_at = entry.reply_received_at or datetime.now(timezone.utc)
            log_activity(db, lead.id, "reply_received", f"Inbound reply received from {lead.email}")

        if entry.booking_status in ("scheduled", "meeting_scheduled", "confirmed", "booked"):
            lead.current_status = "booked"
            lead.booking_status = entry.booking_status
            log_activity(db, lead.id, "meeting_booked", f"Meeting scheduled: {entry.booking_status}")

        # Update or add OutreachHistory
        if entry.template_id or entry.template_name:
            oh = db.query(OutreachHistory).filter(
                OutreachHistory.master_lead_id == lead.id,
                OutreachHistory.campaign_log_id == entry.id,
            ).first()
            if not oh:
                db.add(OutreachHistory(
                    master_lead_id=lead.id,
                    template_id=entry.template_id,
                    template_name=entry.template_name,
                    campaign_log_id=entry.id,
                    status=entry.status or "sent",
                    sent_at=entry.email_sent_at,
                    opened=bool(entry.opened),
                    clicked=bool(entry.clicked_link),
                    replied=bool(entry.reply_received_at),
                    booked=bool(entry.booking_status in ("scheduled", "meeting_scheduled", "confirmed", "booked")),
                ))

        db.commit()
        return lead
    except Exception as e:
        print(f"[sync_campaign_entry_to_master_db notice] {e}")
        return None
