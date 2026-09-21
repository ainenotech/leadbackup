# Lead Re-Engagement Agent — Excel & Microsoft 365 Ecosystem Edition

Implements the end-to-end automated lead re-engagement workflow:

1. **Excel Lead Dataset → Email Composer → Outlook (Microsoft Graph)**: Reads stale lead data directly from an Excel workbook (`leads.xlsx`), uses a LangGraph composer to draft personalized re-engagement emails, and sends them via the **Microsoft Graph `/sendMail` API** from the shared support mailbox (`support@nenotechnology.com`).
2. **Contact Form / Google Form → Webhook → Persistence**: Each email includes a unique trackable pick-a-time form link (`/form?token=...`); a customer can also be pointed at an external **Google Form**. Either path's submission is saved to the campaign database and appended to `booked_leads.xlsx`.
3. **Reply Agent (Outlook inbox + RAG)**: Polls the support mailbox's Outlook inbox via Microsoft Graph for unread replies from campaign leads. For each reply, it retrieves the most relevant chunks from a **Postgres-backed knowledge base** (FAQs, pricing, policies — embedded with Gemini, matched by cosine similarity) and uses them to ground an AI-drafted response, which is classified for intent and sent back automatically.
4. **Outlook Calendar Availability Checker + Scheduler + Microsoft Teams**: Cross-references the lead's submitted slots with the support mailbox's **Outlook Calendar** free/busy status (via Graph's `getSchedule`) and office-hours window; automatically books the meeting with an attached **Microsoft Teams** link and emails a confirmation, or triggers an auto-propose fallback when no overlap exists.
5. **Streamlit Dashboard**: Provides full visibility into outreach campaign metrics (sent, failed, form filled) and scheduling outcomes (scheduled with Teams link, alternates proposed, flagged for human follow-up).

---

## Architecture Overview

| Module | Description |
|---|---|
| `leads.py` | **Step 1 Lead Dataset Loader** — Loads stale leads from `leads.xlsx` (or `.csv`) based on `STALE_AFTER_DAYS`. |
| `Backend/db.py` | Postgres connection (`DATABASE_URL`) and SQLAlchemy session, shared by the campaign log and the RAG knowledge base. |
| `Backend/models.py` | `CampaignLog` (per-lead journey) and `KnowledgeDocument` (RAG chunks + embeddings) tables. |
| `services/rag.py` | Chunks, embeds (Gemini `text-embedding-004`) and stores knowledge documents in Postgres; retrieves the top-matching chunks for an incoming customer message via cosine similarity — no pgvector extension required. |
| `seed_knowledge_base.py` | Loads every `.md`/`.txt` file in `knowledge_base/` into Postgres (clears and reloads each run, so editing a file and re-running keeps things in sync). |
| `utils/microsoft_auth.py` | **Shared Microsoft Graph credentials** — App-only (client credentials) MSAL auth used by both the Outlook mailer and the Outlook calendar client. |
| `Email/` | `outlook_mailer.py` sends email via Microsoft Graph's `/sendMail`; `templates.py` holds deterministic confirmation & alternate-time email templates. |
| `Calendar/` | `outlook_calendar.py` queries the support mailbox's Outlook calendar via Graph `getSchedule` and creates events with an attached **Microsoft Teams** meeting; `availability.py` runs slot-matching logic against office hours. |
| `Agent/` | `graph.py` (email composer graph), `reply_agent.py` (inbound reply classifier + RAG-grounded response drafter) and `scheduler_graph.py` (scheduling state machine). |
| `worker.py` | Processes stale leads from Excel and dispatches outreach emails. |
| `reply_worker.py` | Polls the Outlook inbox for unread lead replies, retrieves relevant knowledge base chunks for each one, and sends an AI-drafted, knowledge-grounded response. |
| `scheduler_worker.py` | Processes form submissions, checks the Outlook calendar, and books confirmed slots with a Teams link. |
| `services/excel_logger.py` | Appends form submissions and confirmed bookings (incl. Teams link) to `booked_leads.xlsx`. |
| `dashboard.py` | Streamlit control center for monitoring campaign performance, booking details, and managing the RAG knowledge base. |

---

## Setup & Prerequisites

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   ```
   Fill in your LLM key (`GEMINI_API_KEY`), your Postgres connection (`DATABASE_URL`), and Microsoft Graph credentials:
   - `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET`
   - `MS_SENDER_EMAIL=support@nenotechnology.com`

3. **Set up Postgres**:
   - Create a database, e.g.:
     ```bash
     createdb lead_reengagement
     ```
   - Point `DATABASE_URL` at it, e.g. `postgresql+psycopg2://postgres:postgres@localhost:5432/lead_reengagement`.
   - No manual schema step needed — every entrypoint (`main_api.py`, `dashboard.py`, `worker.py`, `reply_worker.py`, `scheduler_worker.py`) calls `Base.metadata.create_all(bind=engine)` on startup, which creates the `campaign_log` and `knowledge_documents` tables automatically. No pgvector or other extension is required — embeddings are stored as plain float arrays and compared with cosine similarity in Python.
   - If you have existing data in an old `campaign.db` (SQLite, from before this project used Postgres), run `python migrate_sqlite_to_postgres.py` once to copy it over.

4. **Azure AD App Registration (Microsoft Graph)**:
   - In the [Azure Portal](https://portal.azure.com) go to **App registrations → New registration**. Note the **Application (client) ID** and **Directory (tenant) ID**.
   - Under **Certificates & secrets**, create a new client secret — this is `MS_CLIENT_SECRET`.
   - Under **API permissions → Add a permission → Microsoft Graph → Application permissions**, add:
     - `Mail.Send` (send as the support mailbox)
     - `Mail.Read` (poll the inbox for lead replies)
     - `Calendars.ReadWrite` (check free/busy and create events with a Teams link)
   - Click **Grant admin consent** for your organization — application permissions only work after admin consent.
   - No interactive sign-in or browser OAuth step is needed at runtime; the agent authenticates as the app itself (client-credentials flow) and acts on `MS_SENDER_EMAIL`'s mailbox and calendar, which must exist as a licensed Microsoft 365 mailbox with Teams enabled.

5. **Prepare Lead Data**:
   - Update `leads.xlsx` with your leads. Required columns: `lead_id`, `email`, `name`, `company`, `last_activity_date` (optional: `last_deal_stage`).

6. **Load the RAG knowledge base**:
   - Edit `knowledge_base/company_faqs.md` (or add more `.md`/`.txt` files in that folder) with your real FAQs, pricing, and policies. Keep one topic per paragraph — each blank-line-separated paragraph becomes its own retrievable chunk.
   - Run:
     ```bash
     python seed_knowledge_base.py
     ```
   - You can also add, browse, and delete knowledge documents from the dashboard's **Knowledge Base** page instead of (or in addition to) editing files.

7. **(Optional) Google Form for consultation intake**:
   - If you'd rather collect availability/details on a Google Form instead of the app's own hosted `/form` page, set `GOOGLE_FORM_URL` in `.env` and follow the **Google Forms Automated Sync (Webhook Guide)** panel in the dashboard's Replies & Bookings page to wire up the `/google-form-response` webhook. Submissions are recorded in the campaign database and appended to `booked_leads.xlsx` either way.

---

## Execution Flow

### UI workflow (recommended)

Start the API and dashboard in two PowerShell terminals:

```powershell
python main_api.py
streamlit run dashboard.py
```

Then use the dashboard in this order:

1. Open **Upload Leads** and upload a CSV or Excel sheet. The dashboard reads the lead details and excludes rows already sent or awaiting review.
2. Click **Generate Drafts** for the new leads.
3. Open **Email Review**, edit drafts if needed, then click **Approve & Send** for one lead or **Approve All**.
4. Open **Replies & Bookings** and click **Check Outlook Inbox** to process replies.
5. Click **Process Bookings** to check submitted availability, create Outlook/Teams meetings, and send confirmations or alternate-time messages.

The API process must remain running while leads use the consultation links. The dashboard replaces the manual worker commands for normal operation.

### Command-line worker workflow

```bash
# 1. Start the contact form web server (and the Google Form webhook endpoint)
python main_api.py

# 2. Run the outreach worker (reads stale leads from Excel and sends re-engagement emails via Outlook)
python worker.py

# 3. Poll the Outlook inbox for lead replies and send AI-drafted, RAG-grounded responses
python reply_worker.py

# 4. Run the scheduler worker (processes form submissions and books Outlook calendar slots with Teams links)
python scheduler_worker.py

# 5. Launch the monitoring dashboard (also manages the knowledge base)
streamlit run dashboard.py
```

---

## How the reply agent uses RAG

1. `reply_worker.py` polls the Outlook inbox and finds an unread message from a known lead.
2. It calls `services.rag.retrieve_relevant_chunks(db, message_text)`, which embeds the customer's message and returns the most similar chunks from `knowledge_documents` in Postgres (cosine similarity, filtered by a minimum score so unrelated replies don't drag in random chunks).
3. Those chunks are passed into `Agent.reply_agent.process_incoming_reply(..., context_chunks=...)`, which includes them in the LLM prompt and instructs it to answer from that knowledge rather than guessing at specifics like pricing or policy.
4. If the knowledge base is empty, or nothing scores above the relevance threshold, the agent still replies — just without company-specific grounding, same as before RAG was added.

---

## Scheduling Fallback Options

Configured via `SCHEDULING_FALLBACK` in `.env`:
- `auto_propose` (default): Automatically selects the next open office-hours slots on the Outlook calendar and sends the lead a fresh pick-a-time link.
- `manual_flag`: Flags the lead for human review on the dashboard under "Needs manual scheduling".
