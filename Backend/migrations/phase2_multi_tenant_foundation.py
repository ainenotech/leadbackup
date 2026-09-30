"""Phase 2 Migration — Multi-Tenant Foundation

This script performs the following SAFE, NON-DESTRUCTIVE steps:

1. Creates new multi-tenant tables (organizations, users, organization_members,
   identity_accounts, sessions, otp_codes)
2. Adds `organization_id` column (nullable) to all existing tables
3. Creates the initial "seed" organization from existing company data
4. Creates the initial admin user
5. Backfills organization_id on ALL existing records
6. Adds performance indexes for organization-scoped queries
7. Verifies the migration

SAFETY: All new columns are added as NULLABLE first, backfilled, then
we verify. We do NOT set NOT NULL constraints in this migration to avoid
breaking running application instances. That will be done in a follow-up
migration once the application code is updated.

Run: python -m Backend.migrations.phase2_multi_tenant_foundation
"""

import os
import sys
import uuid
from datetime import datetime, timezone

# Ensure project root is on path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))

from sqlalchemy import inspect, text
from Backend.db import engine, Base, SessionLocal


def log(msg: str):
    """Timestamped migration log output."""
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def step_1_create_foundation_tables():
    """Create the new multi-tenant foundation tables."""
    log("STEP 1: Creating foundation tables...")
    
    # Import all models so they are registered on Base.metadata
    import Backend.models
    import Backend.master_db_models
    import Backend.auth_models
    
    # create_all is safe: it only creates tables that don't exist yet
    Base.metadata.create_all(bind=engine)
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    expected_new = ["organizations", "users", "organization_members",
                    "identity_accounts", "sessions", "otp_codes"]
    created = [t for t in expected_new if t in tables]
    missing = [t for t in expected_new if t not in tables]
    
    log(f"  Created/verified tables: {created}")
    if missing:
        log(f"  WARNING: Missing tables: {missing}")
        return False
    
    log("  STEP 1 COMPLETE: All foundation tables exist.")
    return True


def step_2_add_organization_id_columns():
    """Add organization_id column to all existing tables that need it."""
    log("STEP 2: Adding organization_id to existing tables...")
    
    inspector = inspect(engine)
    
    # Tables that need organization_id added
    tables_needing_org_id = [
        "master_lead",
        "campaign_log",       # Already has it (nullable), but let's verify
        "knowledge_documents",
        "lead_import",
        "lead_import_record",
        "lead_chunk",
        "lead_chunk_member",
        "outreach_history",
        "lead_activity",
        "audit_log",
        "processed_replies",
    ]
    
    added = []
    skipped = []
    
    with engine.connect() as conn:
        for tbl in tables_needing_org_id:
            if tbl not in inspector.get_table_names():
                log(f"  SKIP: Table '{tbl}' does not exist")
                skipped.append(tbl)
                continue
                
            existing_cols = {c["name"] for c in inspector.get_columns(tbl)}
            
            if "organization_id" in existing_cols:
                log(f"  SKIP: '{tbl}' already has organization_id")
                skipped.append(tbl)
                continue
            
            try:
                conn.execute(text(
                    f'ALTER TABLE "{tbl}" ADD COLUMN organization_id VARCHAR NULL'
                ))
                conn.commit()
                added.append(tbl)
                log(f"  ADDED: organization_id to '{tbl}'")
            except Exception as e:
                conn.rollback()
                log(f"  ERROR adding to '{tbl}': {e}")
                skipped.append(tbl)
    
    log(f"  STEP 2 COMPLETE: Added to {len(added)} tables, skipped {len(skipped)}")
    return True


def step_3_create_initial_organization():
    """Create the initial organization from existing company data."""
    log("STEP 3: Creating initial organization...")
    
    db = SessionLocal()
    try:
        from Backend.auth_models import Organization
        
        # Check if initial org already exists
        existing = db.query(Organization).filter(
            Organization.slug == "nenotechnology"
        ).first()
        
        if existing:
            log(f"  SKIP: Initial organization already exists (id={existing.id})")
            return existing.id
        
        org_id = str(uuid.uuid4())
        org = Organization(
            id=org_id,
            name="Neno Technology",
            slug="nenotechnology",
            legal_name="Aineno Innovation Pvt. Ltd.",
            industry="Technology / AI & Software",
            company_size="11-50",
            description="Agentic AI engineering company building production-grade autonomous AI systems, custom AI solutions, and forward-deployed engineering squads.",
            email="sales@nenotechnology.com",
            support_email="support@nenotechnology.com",
            phone=os.getenv("CONTACT_PHONE", "+91 7863852024"),
            address_line1="Ahmedabad",
            state="Gujarat",
            country="India",
            timezone="Asia/Kolkata",
            website="https://www.nenotechnology.com",
            social_links={
                "linkedin": "https://www.linkedin.com/company/nenotechnology/",
                "twitter": "https://x.com/nenotechnology",
                "instagram": "https://www.instagram.com/nenotechnology",
                "facebook": "https://www.facebook.com/nenotechnology",
            },
            brand_name="Nenotechnology",
            status="active",
            is_platform_org=True,  # This is the founding organization
            onboarding_completed=True,
            settings={
                "booking_url": os.getenv(
                    "BOOKING_FORM_URL",
                    "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled"
                ),
                "sender_email": os.getenv("MS_SENDER_EMAIL", ""),
                "campaign_name": os.getenv("CAMPAIGN_NAME", "q3_stale_lead_reengagement"),
                "office_hours_tz": os.getenv("OFFICE_HOURS_TZ", "Asia/Kolkata"),
                "office_hours_start": os.getenv("OFFICE_HOURS_START", "09:00"),
                "office_hours_end": os.getenv("OFFICE_HOURS_END", "18:00"),
            },
        )
        db.add(org)
        db.commit()
        log(f"  CREATED: Organization '{org.name}' (id={org_id})")
        return org_id
    except Exception as e:
        db.rollback()
        log(f"  ERROR creating organization: {e}")
        raise
    finally:
        db.close()


def step_4_create_initial_admin_user(org_id: str):
    """Create the initial admin user and link to the organization."""
    log("STEP 4: Creating initial admin user...")
    
    db = SessionLocal()
    try:
        from Backend.auth_models import User, OrganizationMember
        
        admin_email = os.getenv("MS_SENDER_EMAIL", "admin@nenotechnology.com").strip()
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == admin_email).first()
        if existing_user:
            log(f"  SKIP: Admin user already exists (id={existing_user.id})")
            user_id = existing_user.id
        else:
            user_id = str(uuid.uuid4())
            
            # Hash a temporary password — this will be changed at first login
            import bcrypt
            temp_password = "changeme_at_first_login_" + uuid.uuid4().hex[:8]
            password_hash = bcrypt.hashpw(
                temp_password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
            
            user = User(
                id=user_id,
                email=admin_email,
                email_verified=True,
                password_hash=password_hash,
                full_name="Admin",
                platform_role="platform_super_admin",
                status="active",
            )
            db.add(user)
            db.flush()
            log(f"  CREATED: Admin user '{admin_email}' (id={user_id})")
        
        # Check if membership already exists
        existing_member = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        ).first()
        
        if existing_member:
            log(f"  SKIP: Membership already exists")
        else:
            member = OrganizationMember(
                organization_id=org_id,
                user_id=user_id,
                role="organization_owner",
                is_default=True,
                status="active",
            )
            db.add(member)
            log(f"  CREATED: Membership (owner) for user in org")
        
        db.commit()
        return user_id
    except Exception as e:
        db.rollback()
        log(f"  ERROR creating admin user: {e}")
        raise
    finally:
        db.close()


def step_5_backfill_organization_id(org_id: str):
    """Backfill organization_id on ALL existing records."""
    log("STEP 5: Backfilling organization_id on existing data...")
    
    tables = [
        "master_lead",
        "campaign_log",
        "knowledge_documents",
        "lead_import",
        "lead_import_record",
        "lead_chunk",
        "lead_chunk_member",
        "outreach_history",
        "lead_activity",
        "audit_log",
        "processed_replies",
    ]
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    total_updated = 0
    with engine.connect() as conn:
        for tbl in tables:
            if tbl not in existing_tables:
                continue
            
            # Check if organization_id column exists
            cols = {c["name"] for c in inspector.get_columns(tbl)}
            if "organization_id" not in cols:
                log(f"  SKIP: '{tbl}' has no organization_id column")
                continue
            
            try:
                result = conn.execute(text(
                    f'UPDATE "{tbl}" SET organization_id = :org_id WHERE organization_id IS NULL'
                ), {"org_id": org_id})
                count = result.rowcount
                conn.commit()
                total_updated += count
                log(f"  BACKFILLED: '{tbl}' — {count} rows updated")
            except Exception as e:
                conn.rollback()
                log(f"  ERROR backfilling '{tbl}': {e}")
    
    log(f"  STEP 5 COMPLETE: {total_updated} total rows backfilled")
    return True


def step_6_add_indexes():
    """Add performance indexes for organization-scoped queries."""
    log("STEP 6: Adding organization_id indexes...")
    
    indexes = [
        ("ix_master_lead_org_id", "master_lead", "organization_id"),
        ("ix_master_lead_org_email", "master_lead", "organization_id, email_normalized"),
        ("ix_master_lead_org_status", "master_lead", "organization_id, current_status"),
        ("ix_campaign_log_org_id", "campaign_log", "organization_id"),
        ("ix_campaign_log_org_status", "campaign_log", "organization_id, status"),
        ("ix_campaign_log_org_created", "campaign_log", "organization_id, created_at"),
        ("ix_knowledge_docs_org_id", "knowledge_documents", "organization_id"),
        ("ix_lead_import_org_id", "lead_import", "organization_id"),
        ("ix_lead_chunk_org_id", "lead_chunk", "organization_id"),
        ("ix_outreach_history_org_id", "outreach_history", "organization_id"),
        ("ix_lead_activity_org_id", "lead_activity", "organization_id"),
        ("ix_audit_log_org_id", "audit_log", "organization_id"),
        ("ix_processed_replies_org_id", "processed_replies", "organization_id"),
    ]
    
    created = 0
    skipped = 0
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    with engine.connect() as conn:
        for ix_name, tbl, columns in indexes:
            if tbl not in existing_tables:
                skipped += 1
                continue
            
            # Check if index already exists
            existing_indexes = {ix["name"] for ix in inspector.get_indexes(tbl)}
            if ix_name in existing_indexes:
                skipped += 1
                continue
            
            try:
                conn.execute(text(
                    f'CREATE INDEX IF NOT EXISTS "{ix_name}" ON "{tbl}" ({columns})'
                ))
                conn.commit()
                created += 1
                log(f"  CREATED: Index {ix_name} on {tbl}({columns})")
            except Exception as e:
                conn.rollback()
                log(f"  ERROR creating index {ix_name}: {e}")
                skipped += 1
    
    log(f"  STEP 6 COMPLETE: {created} indexes created, {skipped} skipped")
    return True


def step_7_verify():
    """Verify the migration was successful."""
    log("STEP 7: Verification...")
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    # Verify new tables exist
    required_new = ["organizations", "users", "organization_members",
                    "identity_accounts", "sessions", "otp_codes"]
    for t in required_new:
        status = "OK" if t in tables else "MISSING"
        log(f"  Table '{t}': {status}")
    
    # Verify organization_id exists on existing tables
    target_tables = [
        "master_lead", "campaign_log", "knowledge_documents",
        "lead_import", "lead_chunk", "outreach_history",
        "lead_activity", "audit_log", "processed_replies",
    ]
    for t in target_tables:
        if t in tables:
            cols = {c["name"] for c in inspector.get_columns(t)}
            has_org_id = "organization_id" in cols
            status = "OK" if has_org_id else "MISSING org_id"
            log(f"  Table '{t}' organization_id: {status}")
    
    # Verify no NULL organization_ids remain
    db = SessionLocal()
    try:
        from Backend.auth_models import Organization, User, OrganizationMember
        
        org_count = db.query(Organization).count()
        user_count = db.query(User).count()
        member_count = db.query(OrganizationMember).count()
        
        log(f"  Organizations: {org_count}")
        log(f"  Users: {user_count}")
        log(f"  Organization members: {member_count}")
        
        # Check for NULL org_ids in critical tables
        with engine.connect() as conn:
            for t in ["master_lead", "campaign_log", "knowledge_documents"]:
                if t in tables:
                    null_count = conn.execute(text(
                        f'SELECT COUNT(*) FROM "{t}" WHERE organization_id IS NULL'
                    )).scalar()
                    status = "OK" if null_count == 0 else f"WARNING: {null_count} rows with NULL org_id"
                    log(f"  Table '{t}' NULL org_ids: {status}")
    finally:
        db.close()
    
    log("  STEP 7 COMPLETE: Verification done.")
    return True


def run_migration():
    """Execute the full Phase 2 migration."""
    log("=" * 60)
    log("PHASE 2 MIGRATION: Multi-Tenant Foundation")
    log("=" * 60)
    log(f"Database: {engine.url}")
    log("")
    
    # Step 1: Create new tables
    if not step_1_create_foundation_tables():
        log("MIGRATION ABORTED: Failed to create foundation tables")
        return False
    log("")
    
    # Step 2: Add organization_id columns
    if not step_2_add_organization_id_columns():
        log("MIGRATION ABORTED: Failed to add organization_id columns")
        return False
    log("")
    
    # Step 3: Create initial organization
    org_id = step_3_create_initial_organization()
    if not org_id:
        log("MIGRATION ABORTED: Failed to create initial organization")
        return False
    log("")
    
    # Step 4: Create initial admin user
    user_id = step_4_create_initial_admin_user(org_id)
    log("")
    
    # Step 5: Backfill organization_id
    if not step_5_backfill_organization_id(org_id):
        log("MIGRATION ABORTED: Failed to backfill organization_id")
        return False
    log("")
    
    # Step 6: Add indexes
    if not step_6_add_indexes():
        log("WARNING: Some indexes may not have been created")
    log("")
    
    # Step 7: Verify
    step_7_verify()
    
    log("")
    log("=" * 60)
    log("PHASE 2 MIGRATION COMPLETE")
    log("=" * 60)
    log("")
    log("Next steps:")
    log("  1. Verify the application still works (start API + dashboard)")
    log("  2. Check that existing leads/campaigns load correctly")
    log("  3. Proceed to Phase 3 (Authentication) after approval")
    
    return True


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
