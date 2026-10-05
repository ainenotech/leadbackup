import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, Set

import pandas as pd
from dotenv import load_dotenv


load_dotenv()

DEFAULT_LEADS_FILE = os.getenv(
    "LEADS_FILE", os.path.join(os.path.dirname(__file__), "leads.xlsx")
)
REQUIRED_COLUMNS = {"lead_id", "email", "name", "company", "last_activity_date"}

# Normalized column names that may indicate email delivery/contact status
STATUS_COLUMN_NAMES = {
    "status",
    "email_status",
    "mail_status",
    "sent",
    "email_sent",
    "mail_sent",
    "already_sent",
    "sent_mail",
    "contacted",
    "is_sent",
    "sent_status",
}

SENT_INDICATOR_VALUES = {
    "sent",
    "yes",
    "true",
    "1",
    "already sent",
    "delivered",
    "contacted",
    "emailed",
    "done",
    "completed",
}

SENT_DATE_COLUMNS = {
    "email_sent_at",
    "sent_at",
    "sent_date",
    "mail_sent_at",
    "date_sent",
}


@dataclass
class Lead:
    lead_id: str
    email: str
    name: Optional[str]
    company: Optional[str]
    last_activity_date: Optional[str]
    last_deal_stage: Optional[str] = None


# Smart Column Alias Mapping
EMAIL_COLUMN_ALIASES = [
    "email", "email_address", "email address", "company email", "work email",
    "business email", "contact email", "e-mail", "mail", "to"
]

NAME_COLUMN_ALIASES = [
    "full_name", "fullname", "full name", "contact_name", "contact name",
    "name", "lead_name", "lead name", "client name", "person"
]

FIRST_NAME_COLUMN_ALIASES = [
    "first_name", "firstname", "first name", "given name", "first"
]

LAST_NAME_COLUMN_ALIASES = [
    "last_name", "lastname", "last name", "surname", "family name", "last"
]

COMPANY_COLUMN_ALIASES = [
    "company", "company_name", "company name", "organization", "organisation",
    "org_name", "org name", "org", "account_name", "account name", "account",
    "business_name", "business name", "business", "firm", "agency"
]

LEAD_ID_COLUMN_ALIASES = [
    "lead_id", "lead id", "id", "contact id", "contact_id", "record id", "record_id"
]

LAST_ACTIVITY_COLUMN_ALIASES = [
    "last_activity_date", "last activity date", "last_activity", "last activity",
    "activity date", "activity_date", "date"
]

COMMON_WEBMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "aol.com", "zoho.com", "protonmail.com", "mail.com", "gmx.com", "live.com"
}


def _find_col_by_alias(columns, aliases) -> Optional[str]:
    lower_map = {str(c).strip().lower(): c for c in columns}
    for a in aliases:
        if a in lower_map:
            return lower_map[a]
    for a in aliases:
        a_clean = a.replace(" ", "").replace("_", "")
        for c_low, original in lower_map.items():
            if a_clean == c_low.replace(" ", "").replace("_", ""):
                return original
    return None


def infer_name_from_email(email: str) -> str:
    import re
    if "@" not in email:
        return ""
    user = email.split("@")[0]
    parts = [p for p in re.split(r"[._\-+0-9]+", user) if p]
    if parts:
        return " ".join(parts).title()
    return ""


def infer_company_from_email(email: str) -> str:
    if "@" not in email:
        return ""
    domain = email.split("@")[1].lower()
    if domain in COMMON_WEBMAIL_DOMAINS:
        return ""
    root = domain.split(".")[0]
    if root and len(root) > 1:
        return root.title()
    return ""


def detect_lead_status_in_dataframe(
    df: pd.DataFrame,
    sent_emails: Optional[Set[str]] = None,
    drafted_emails: Optional[Set[str]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Inspects an uploaded lead DataFrame.
    Splits rows into:
      1. new_leads_df: New leads ready for outreach drafting
      2. skipped_sent_df: Leads that have already received an email (with skip_reason)
      3. skipped_drafted_df: Leads that already have a draft in review (with skip_reason)
    """
    sent_emails = {e.lower().strip() for e in (sent_emails or set()) if e}
    drafted_emails = {e.lower().strip() for e in (drafted_emails or set()) if e}

    clean_df = df.copy()

    # Find the email column with aliases
    email_col = _find_col_by_alias(clean_df.columns, EMAIL_COLUMN_ALIASES)
    if not email_col:
        for col in clean_df.columns:
            non_null = clean_df[col].dropna()
            if not non_null.empty and "@" in str(non_null.iloc[0]):
                email_col = col
                break

    if not email_col:
        raise ValueError("Could not find an 'email' column in the uploaded sheet.")

    # Find name, company, lead_id, last_activity columns
    name_col = _find_col_by_alias(clean_df.columns, NAME_COLUMN_ALIASES)
    first_name_col = _find_col_by_alias(clean_df.columns, FIRST_NAME_COLUMN_ALIASES)
    last_name_col = _find_col_by_alias(clean_df.columns, LAST_NAME_COLUMN_ALIASES)
    company_col = _find_col_by_alias(clean_df.columns, COMPANY_COLUMN_ALIASES)
    lead_id_col = _find_col_by_alias(clean_df.columns, LEAD_ID_COLUMN_ALIASES)
    last_activity_date_col = _find_col_by_alias(clean_df.columns, LAST_ACTIVITY_COLUMN_ALIASES)

    # Find status or sent date columns if present in the sheet
    status_col = None
    sent_date_col = None
    for col in clean_df.columns:
        col_lower = str(col).strip().lower()
        if col_lower in STATUS_COLUMN_NAMES and status_col is None:
            status_col = col
        if col_lower in SENT_DATE_COLUMNS and sent_date_col is None:
            sent_date_col = col

    new_rows = []
    skipped_sent_rows = []
    skipped_drafted_rows = []

    seen_in_this_file = set()

    for idx, row in clean_df.iterrows():
        raw_email = row.get(email_col)
        if pd.isna(raw_email) or not str(raw_email).strip():
            continue

        email = str(raw_email).strip().lower()

        # Resolve lead name
        raw_name = ""
        if name_col and pd.notna(row.get(name_col)):
            raw_name = str(row.get(name_col)).strip()
        elif first_name_col and pd.notna(row.get(first_name_col)):
            first = str(row.get(first_name_col)).strip()
            last = str(row.get(last_name_col)).strip() if last_name_col and pd.notna(row.get(last_name_col)) else ""
            raw_name = f"{first} {last}".strip()
        if not raw_name or raw_name.lower() in ("nan", "none", "-", "—"):
            raw_name = infer_name_from_email(email)

        # Resolve company
        raw_company = ""
        if company_col and pd.notna(row.get(company_col)):
            raw_company = str(row.get(company_col)).strip()
        if not raw_company or raw_company.lower() in ("nan", "none", "-", "—"):
            raw_company = infer_company_from_email(email)

        # Resolve lead_id
        raw_lead_id = ""
        if lead_id_col and pd.notna(row.get(lead_id_col)):
            raw_lead_id = str(row.get(lead_id_col)).strip()
        if not raw_lead_id or raw_lead_id.lower() in ("nan", "none"):
            raw_lead_id = f"lead_{email.split('@')[0]}"

        # Resolve last activity date
        raw_activity = ""
        if last_activity_date_col and pd.notna(row.get(last_activity_date_col)):
            raw_activity = str(row.get(last_activity_date_col)).strip()
        if not raw_activity or raw_activity.lower() in ("nan", "none"):
            raw_activity = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Check duplicate within this uploaded file itself
        if email in seen_in_this_file:
            row_dict = row.to_dict()
            row_dict["email"] = email
            row_dict["name"] = raw_name
            row_dict["company"] = raw_company
            row_dict["lead_id"] = raw_lead_id
            row_dict["last_activity_date"] = raw_activity
            row_dict["skip_reason"] = "Duplicate row in uploaded file"
            skipped_sent_rows.append(row_dict)
            continue

        seen_in_this_file.add(email)
        row_dict = row.to_dict()
        row_dict["email"] = email
        row_dict["name"] = raw_name
        row_dict["company"] = raw_company
        row_dict["lead_id"] = raw_lead_id
        row_dict["last_activity_date"] = raw_activity

        # 1. Check if marked as sent in the sheet's status column
        sheet_sent_reason = None
        if status_col and pd.notna(row.get(status_col)):
            val = str(row.get(status_col)).strip().lower()
            if val in SENT_INDICATOR_VALUES:
                sheet_sent_reason = f"Marked '{val}' in sheet column '{status_col}'"

        # 2. Check if sheet has a sent date column populated
        if not sheet_sent_reason and sent_date_col and pd.notna(row.get(sent_date_col)):
            val = str(row.get(sent_date_col)).strip()
            if val and val.lower() not in ["none", "nan", "nat", ""]:
                sheet_sent_reason = f"Sent timestamp in sheet column '{sent_date_col}': {val}"

        # 3. Check if email already sent in database history
        if email in sent_emails:
            row_dict["skip_reason"] = "Already sent in database records"
            skipped_sent_rows.append(row_dict)
        elif sheet_sent_reason:
            row_dict["skip_reason"] = sheet_sent_reason
            skipped_sent_rows.append(row_dict)
        elif email in drafted_emails:
            row_dict["skip_reason"] = "Draft already generated & pending review"
            skipped_drafted_rows.append(row_dict)
        else:
            row_dict["status"] = "new"
            new_rows.append(row_dict)

    new_leads_df = pd.DataFrame(new_rows) if new_rows else pd.DataFrame(columns=clean_df.columns)
    skipped_sent_df = pd.DataFrame(skipped_sent_rows) if skipped_sent_rows else pd.DataFrame()
    skipped_drafted_df = pd.DataFrame(skipped_drafted_rows) if skipped_drafted_rows else pd.DataFrame()

    return new_leads_df, skipped_sent_df, skipped_drafted_df



def update_lead_sheet_status(
    email: str,
    status: str,
    sent_at: Optional[str] = None,
    file_path: str = DEFAULT_LEADS_FILE,
) -> bool:
    """Updates the status and timestamp for an email in leads.xlsx."""
    if not os.path.exists(file_path):
        return False

    try:
        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        if "email" not in df.columns:
            return False

        if "status" not in df.columns:
            df["status"] = "new"
        if "email_sent_at" not in df.columns:
            df["email_sent_at"] = ""

        mask = df["email"].astype(str).str.strip().str.lower() == email.strip().lower()
        if not mask.any():
            return False

        df.loc[mask, "status"] = status
        if sent_at:
            df.loc[mask, "email_sent_at"] = sent_at

        if file_path.lower().endswith(".csv"):
            df.to_csv(file_path, index=False)
        else:
            df.to_excel(file_path, index=False)
        return True
    except Exception as e:
        print(f"Error updating lead sheet status: {e}")
        return False


def append_or_update_leads_dataset(
    incoming_df: pd.DataFrame,
    file_path: str = DEFAULT_LEADS_FILE,
    default_status: str = "new",
) -> pd.DataFrame:
    """Merges newly uploaded leads into DEFAULT_LEADS_FILE without corrupting existing statuses."""
    clean_incoming = incoming_df.copy()

    # Ensure required columns exist
    if "lead_id" not in clean_incoming.columns:
        clean_incoming["lead_id"] = [f"lead_{uuid.uuid4().hex[:6]}" for _ in range(len(clean_incoming))]
    if "last_activity_date" not in clean_incoming.columns:
        clean_incoming["last_activity_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if "name" not in clean_incoming.columns:
        clean_incoming["name"] = ""
    if "company" not in clean_incoming.columns:
        clean_incoming["company"] = ""
    if "status" not in clean_incoming.columns:
        clean_incoming["status"] = default_status

    if os.path.exists(file_path):
        try:
            if file_path.lower().endswith(".csv"):
                existing_df = pd.read_csv(file_path)
            else:
                existing_df = pd.read_excel(file_path)
        except Exception:
            existing_df = pd.DataFrame()
    else:
        existing_df = pd.DataFrame()

    if not existing_df.empty and "email" in existing_df.columns:
        existing_emails = set(existing_df["email"].astype(str).str.strip().str.lower())
        new_only = clean_incoming[
            ~clean_incoming["email"].astype(str).str.strip().str.lower().isin(existing_emails)
        ]
        combined = pd.concat([existing_df, new_only], ignore_index=True)
    else:
        combined = clean_incoming

    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    if file_path.lower().endswith(".csv"):
        combined.to_csv(file_path, index=False)
    else:
        combined.to_excel(file_path, index=False)

    return combined


def load_stale_leads(stale_after_days: int, file_path: str = DEFAULT_LEADS_FILE) -> List[Lead]:
    """Load stale lead dataset from an Excel workbook (.xlsx) or CSV file.
    Replaces legacy CRM integrations for Step 1 lead dataset ingestion.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Lead dataset file not found: {file_path}")

    if file_path.lower().endswith(".csv"):
        leads_df = pd.read_csv(file_path)
    else:
        leads_df = pd.read_excel(file_path)
    missing_columns = REQUIRED_COLUMNS - set(leads_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Lead workbook is missing required columns: {missing}")

    cutoff = datetime.now(timezone.utc) - timedelta(days=stale_after_days)
    leads = []
    for _, row in leads_df.iterrows():
        if pd.isna(row["email"]) or pd.isna(row["last_activity_date"]):
            continue

        activity = pd.to_datetime(row["last_activity_date"], utc=True, errors="coerce")
        if pd.isna(activity) or activity.to_pydatetime() > cutoff:
            continue

        leads.append(
            Lead(
                lead_id=str(row["lead_id"]),
                email=str(row["email"]),
                name=None if pd.isna(row["name"]) else str(row["name"]),
                company=None if pd.isna(row["company"]) else str(row["company"]),
                last_activity_date=activity.isoformat(),
                last_deal_stage=(
                    None if pd.isna(row.get("last_deal_stage")) else str(row["last_deal_stage"])
                ),
            )
        )

    return leads
