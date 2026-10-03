import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import bcrypt
from Backend.db import SessionLocal
from Backend.auth_models import Organization, User, OrganizationMember
from sqlalchemy import text

def inspect_and_clean():
    db = SessionLocal()
    try:
        print("--- CURRENT ORGS ---")
        orgs = db.query(Organization).all()
        for o in orgs:
            print(f"ID: {o.id}, Name: {o.name}, Slug: {o.slug}")

        print("\n--- CURRENT USERS ---")
        users = db.query(User).all()
        for u in users:
            print(f"ID: {u.id}, Email: {u.email}, Name: {u.full_name}, Role: {u.platform_role}")

        print("\n--- CURRENT MEMBERSHIPS ---")
        members = db.query(OrganizationMember).all()
        for m in members:
            print(f"OrgID: {m.organization_id}, UserID: {m.user_id}, Role: {m.role}")

    finally:
        db.close()

if __name__ == "__main__":
    inspect_and_clean()
