import os
from dotenv import load_dotenv

load_dotenv()

# Which provider to send through: "outlook" (default, via Microsoft Graph)
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "outlook").lower()

# --- Microsoft Graph / Azure AD app registration (shared with Calendar) ---
MS_TENANT_ID = os.getenv("MS_TENANT_ID", "")
MS_CLIENT_ID = os.getenv("MS_CLIENT_ID", "")
MS_CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET", "")

# The shared company support mailbox emails are sent from / read from
MS_SENDER_EMAIL = os.getenv("MS_SENDER_EMAIL", "support@nenotechnology.com")

GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]



# --- Amazon SES ---
AWS_PROFILE = os.getenv("AWS_PROFILE", "")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SES_CONFIGURATION_SET = os.getenv(
    "SES_CONFIGURATION_SET", "neno-campaigns"
)
SES_FROM_EMAIL = os.getenv(
    "SES_FROM_EMAIL", "support@nenotechnology.com"
)
SES_REPLY_TO = os.getenv(
    "SES_REPLY_TO", MS_SENDER_EMAIL
)

