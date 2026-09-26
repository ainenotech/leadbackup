import os
from dotenv import load_dotenv

load_dotenv()

# Which provider to send through: "outlook" (default, via Microsoft Graph)
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "outlook").lower()

# --- Microsoft Graph / Azure AD app registration (shared with Calendar) ---
MS_TENANT_ID = os.getenv("MS_TENANT_ID", "")
MS_CLIENT_ID = os.getenv("MS_CLIENT_ID", "")
MS_CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET", "")

# The mailbox emails are sent from / read from
MS_SENDER_EMAIL = os.getenv("MS_SENDER_EMAIL", "mohit@nenotechnology.us")

GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]
