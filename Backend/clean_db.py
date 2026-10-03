import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import bcrypt
from Backend.db import SessionLocal
from Backend.auth_models import Organization, User, OrganizationMember, Session as UserSession
from Backend.channels_models import OrgMailConnection
from Backend.domain_models import OrgSendingDomain
from sqlalchemy import text

def clean_orgs_and_users():
    db = SessionLocal()
    try:
        # Check orgs to delete
        neno_org = db.query(Organization).filter(Organization.slug == "nenotechnology").first()
        if not neno_org:
            print("Error: neno_org not found!")
            return

        print(f"Keeping Neno Org: {neno_org.id} ({neno_org.name})")

        # Set Neno Org brand_name and settings
        neno_org.name = "Neno Technology"
        neno_org.brand_name = "AINeotechnology"
        neno_org.email = "mohit@nenotechnology.us"
        if not neno_org.settings:
            neno_org.settings = {}
        neno_org.settings["sender_email"] = "mohit@nenotechnology.us"

        # Find other orgs
        other_orgs = db.query(Organization).filter(Organization.id != neno_org.id).all()
        other_org_ids = [o.id for o in other_orgs]
        print(f"Other orgs to delete: {[o.name for o in other_orgs]}")

        # Delete related records for other orgs
        for org_id in other_org_ids:
            db.execute(text("DELETE FROM organization_members WHERE organization_id = :oid"), {"oid": org_id})
            db.execute(text("DELETE FROM org_mail_connections WHERE organization_id = :oid"), {"oid": org_id})
            db.execute(text("DELETE FROM org_sending_domains WHERE organization_id = :oid"), {"oid": org_id})
            db.execute(text("DELETE FROM organizations WHERE id = :oid"), {"oid": org_id})

        # Remove users: man@nenotechnology.com, admin_b1b5dc@testsas.io
        emails_to_remove = ["man@nenotechnology.com", "admin_b1b5dc@testsas.io"]
        for email in emails_to_remove:
            user = db.query(User).filter(User.email == email).first()
            if user:
                print(f"Deleting user: {user.email}")
                db.execute(text("DELETE FROM organization_members WHERE user_id = :uid"), {"uid": user.id})
                db.execute(text("DELETE FROM sessions WHERE user_id = :uid"), {"uid": user.id})
                db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user.id})

        # Remove any other members from Neno Org except Mohit
        mohit_user = db.query(User).filter(User.email == "mohit@nenotechnology.us").first()
        if mohit_user:
            # Set a standard known password for Mohit (e.g. Mohit@123 or Admin@12345)
            # We will set a password hash for Admin@12345 so Mohit can sign in with Admin@12345 or anything he wants!
            salt = bcrypt.gensalt(rounds=12)
            mohit_user.password_hash = bcrypt.hashpw(b"Admin@12345", salt).decode("utf-8")
            mohit_user.full_name = "Mohit Patel"
            mohit_user.platform_role = "platform_super_admin"
            mohit_user.status = "active"

            # Ensure Mohit is default organization_owner in Neno Org
            db.execute(text("DELETE FROM organization_members WHERE organization_id = :oid AND user_id != :uid"), {"oid": neno_org.id, "uid": mohit_user.id})
            m = db.query(OrganizationMember).filter(OrganizationMember.organization_id == neno_org.id, OrganizationMember.user_id == mohit_user.id).first()
            if not m:
                import uuid
                m = OrganizationMember(
                    id=str(uuid.uuid4()),
                    organization_id=neno_org.id,
                    user_id=mohit_user.id,
                    role="organization_owner",
                    is_default=True,
                    status="active",
                )
                db.add(m)
            else:
                m.role = "organization_owner"
                m.is_default = True
                m.status = "active"

        # Also remove support@nenotechnology.com if present as member
        support_user = db.query(User).filter(User.email == "support@nenotechnology.com").first()
        if support_user:
            db.execute(text("DELETE FROM organization_members WHERE user_id = :uid"), {"uid": support_user.id})
            # We can delete support user as well or keep password synced
            db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": support_user.id})

        db.commit()
        print("Clean up completed successfully!")

        # Verify
        print("\n--- FINAL ORGS ---")
        for o in db.query(Organization).all():
            print(f"ID: {o.id}, Name: {o.name}, Slug: {o.slug}")

        print("\n--- FINAL USERS ---")
        for u in db.query(User).all():
            print(f"ID: {u.id}, Email: {u.email}, Name: {u.full_name}")

        print("\n--- FINAL MEMBERSHIPS ---")
        for m in db.query(OrganizationMember).all():
            print(f"OrgID: {m.organization_id}, UserID: {m.user_id}, Role: {m.role}")

    except Exception as e:
        db.rollback()
        print("Error during clean:", e)
    finally:
        db.close()

if __name__ == "__main__":
    clean_orgs_and_users()
