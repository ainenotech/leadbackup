# Enterprise Lead Intelligence & Autonomous Outreach Platform

An enterprise-grade, privacy-first platform for automated lead re-engagement, dynamic email composition, autonomous RAG-grounded inquiry handling, telemetry tracking, and calendar appointment scheduling.

Powered by **FastAPI**, **Streamlit**, **LangGraph**, **Google Gemini**, and **Microsoft 365 (Microsoft Graph API)**.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Complete Project Flow](#-complete-project-flow)
- [Comprehensive Technology Stack](#-comprehensive-technology-stack)
- [Key Features & Capabilities](#-key-features--capabilities)
- [Project Directory & Module Structure](#-project-directory--module-structure)
- [Installation & Quickstart](#-installation--quickstart)
- [Environment Configuration](#-environment-configuration)
- [Microsoft Entra ID (Azure AD) Setup](#-microsoft-entra-id-azure-ad-setup)
- [Running the Platform](#-running-the-platform)
- [Background Autonomous Daemons](#-background-autonomous-daemons)
- [Docker Deployment](#-docker-deployment)
- [Security, Privacy & Best Practices](#-security-privacy--best-practices)
- [License](#-license)

---

## 🌟 Overview

The **Enterprise Lead Intelligence & Autonomous Outreach Platform** streamlines the entire lifecycle of B2B lead reactivation. It transforms raw lead spreadsheets into revenue pipeline by blending automated AI generation with human-in-the-loop review, multi-channel inbound response handling, vector retrieval, and appointment booking.

### Core Value Drivers:
- **Zero-Friction Ingestion & Deduplication**: Upload Excel/CSV files with automatic schema detection and multi-layer deduplication against prior campaign dispatches.
- **Human-in-the-Loop Email Studio**: Review AI-personalized drafts in sandboxed email client previews (Outlook & Apple Mail simulation) with 1-click template swapping.
- **Autonomous RAG Reply Agent**: Inbound lead replies to the shared mailbox are fetched automatically, categorized for intent, grounded against embedded organizational documents (PDF, Markdown, TXT), and answered with accurate facts.
- **Automated Scheduling Integration**: Direct coordination with Microsoft Bookings, Microsoft Calendar, and Microsoft Teams to suggest slots, prevent double-bookings, and confirm meetings.
- **Real-Time Telemetry & Analytics**: Built-in 14-engine telemetry system tracking email opens, link redirects, reply velocity, and sentiment, with one-click export to publication-ready PDF and Excel executive dossiers.

---

## 🏛️ System Architecture

The following diagram illustrates the end-to-end architecture and data exchange across frontend modules, backend services, external APIs, and persistent storage:

```mermaid
graph TD
    subgraph Data Ingestion
        A[Lead Dataset: CSV / XLSX] --> B[Upload & Schema Mapping Engine]
        B --> C[Multi-Tier Deduplication Guard]
    end

    subgraph Composition & Review
        C --> D[LangGraph AI Composer / Template Hub]
        D --> E[Human-in-the-Loop Email Review Studio]
    end

    subgraph Outbound Dispatch & Telemetry
        E -->|OAuth 2.0 / MSAL| F[Microsoft Graph API: Mail.Send]
        F --> G[Recipient Inbox]
        G -->|Pixel Trigger / Link Redirect| H[FastAPI Telemetry Service]
        H --> I[(PostgreSQL / SQLite Database)]
    end

    subgraph Inbound Processing & RAG
        G -->|Customer Replies| J[Shared Mailbox]
        K[Autonomous Reply Daemon] -->|Polls Mail.Read| J
        L[Knowledge Base: PDF / MD / TXT] -->|Gemini Dense Embeddings| M[(Vector Store in DB)]
        M -->|Cosine Similarity Retrieval| K
        K -->|Grounded AI Response| F
    end

    subgraph Calendar & Synchronization
        G -->|Consultation Link / Form| N[Booking Form / Microsoft Bookings]
        N --> O[Outlook Calendar / Teams Meeting Link]
        O --> P[Permanent Excel Audit Log: booked_leads.xlsx]
        P -->|Sync Engine| I
        J -->|Sync Engine| I
    end

    subgraph Reporting & Analytics
        I --> Q[Streamlit Executive Control Center]
        I --> R[PDF Dossiers & Multi-Sheet Excel Exports]
    end
```

---

## 🔄 Complete Project Flow

The platform guides every lead through a rigorous 7-stage lifecycle:

```
[1. Ingest & Deduplicate] ➔ [2. Compose & Personalize] ➔ [3. Review & Dispatch] ➔ [4. Track Telemetry]
                                                                                          │
[7. Confirm & Archive]   ⬅ [6. Ground & Auto-Reply]   ⬅ [5. Inbound Reply & Intent] ⬅────┘
```

### Stage 1: Ingestion & Validation
1. An operator uploads a lead sheet (`.xlsx` or `.csv`) through the **Upload & Draft** interface.
2. The engine normalizes column headers (`name`, `email`, `company`, `last_activity_date`, `deal_stage`).
3. Leads are cross-referenced in memory against historical database records and current campaign logs to filter out duplicate contacts.

### Stage 2: AI Composition & Personalization
1. Leads pass to the **LangGraph** orchestration graph.
2. The composer interpolates contextual variables (contact name, company name, previous deal history, and personalized tracking links) into selected high-converting HTML templates.
3. Alternately, the AI composer generates customized outreach messaging adhering to corporate tone and guidelines.

### Stage 3: Human-in-the-Loop Review & Outbound Dispatch
1. Operators inspect generated drafts inside the **Email Review Studio**.
2. Previews render within a sandboxed environment mimicking modern desktop and mobile email clients.
3. Operators can make ad-hoc edits, cycle templates, approve individual leads, or trigger bulk approval.
4. Emails are dispatched via **Microsoft Graph API** using an enterprise OAuth 2.0 app-only credential flow.

### Stage 4: Real-Time Telemetry Tracking
1. Outgoing emails include an invisible 1x1 tracking pixel and encoded redirection links generated with unique tokens.
2. The **FastAPI** telemetry service records open counts, timestamps, link clicks, device context, and unsubscribe requests directly into the database.

### Stage 5: Inbound Inbox Monitoring & Intent Classification
1. The **Autonomous Reply Daemon** (`reply_worker.py`) continuously polls the shared Outlook mailbox via Microsoft Graph API.
2. Quoted email history, email headers, and system signatures are stripped to isolate the customer's fresh message.
3. An LLM classifier evaluates the message intent into standardized categories:
   - `Interested`
   - `Question / Inquiry`
   - `Meeting Request`
   - `Reschedule`
   - `Not Interested / Opt-Out`

### Stage 6: Vector RAG Retrieval & Contextual Response
1. If the incoming reply is a question or inquiry, relevant chunks from the embedded Knowledge Base (company documentation, FAQs, pricing frameworks) are retrieved via **Cosine Similarity Vector Search**.
2. Grounded facts are injected into the prompt context with a zero-hallucination threshold.
3. The AI crafts an executive-level, factual response that either answers the inquiry directly or presents calendar booking slots.

### Stage 7: Appointment Scheduling & Permanent Archival
1. Once a lead selects a time slot or completes the booking flow, the event coordinates with **Outlook Calendar** and generates a **Microsoft Teams** meeting link.
2. The confirmed booking is atomically committed to the primary SQL database and mirrored to permanent offline Excel logs (`booked_leads.xlsx`, `customer_replies.xlsx`) for complete auditability.

---

## 🛠️ Comprehensive Technology Stack

The platform is constructed using modern, production-hardened libraries across every tier:

### 1. User Interface & Presentation
| Technology | Role & Purpose |
|---|---|
| **Streamlit** | Core interactive dashboard engine powering the 7 executive views with reactive state management. |
| **Custom Design System (CSS)** | Tailored dual-theme system (Dark & Light modes) with responsive cards, KPI badges, and typography (Outfit, Inter, JetBrains Mono). |
| **LRU Memory Style Cache** | Zero-latency CSS compilation caching to prevent UI flicker across rerenders. |
| **Sandboxed HTML Rendering** | Secure isolated iframe containers for rendering email previews without CSS bleeding. |

### 2. Backend, Webhooks & APIs
| Technology | Role & Purpose |
|---|---|
| **FastAPI** | High-performance asynchronous REST API handling telemetry webhooks, pixel tracking, and redirects. |
| **Uvicorn** | Production-ready ASGI server running the FastAPI backend service. |
| **Keepalive Daemon** | Self-healing background polling service preventing idle spin-downs on serverless/cloud hosting platforms. |

### 3. Artificial Intelligence & Agentic Orchestration
| Technology | Role & Purpose |
|---|---|
| **LangChain** | Foundation for LLM abstraction, prompt engineering, output sanitization, and structured parsing. |
| **LangGraph** | Stateful multi-node workflow orchestration graph for email composition pipelines. |
| **Google Gemini API** | Primary generative engine (`gemini-2.5-flash` / `gemini-3.6-flash`) for rapid, high-context email generation. |
| **Anthropic Claude API** | Optional alternative generative model provider (`claude-sonnet-4-6`). |
| **Google GenAI Embeddings** | Dense vector generation model (`text-embedding-004`) converting documents and inquiries into 768-dimensional vectors. |

### 4. Knowledge Base & Vector Retrieval (RAG)
| Technology | Role & Purpose |
|---|---|
| **Cosine Similarity Search** | Pure mathematical vector similarity scoring implemented via NumPy; requires no external vector database plugins. |
| **PyPDF** | Robust PDF document ingestion and text extraction engine. |
| **Semantic Document Chunking** | Dynamic text splitter preserving contextual integrity across technical documentation and FAQs. |

### 5. Database, ORM & Storage
| Technology | Role & Purpose |
|---|---|
| **PostgreSQL** | Primary production relational database storing campaign records, telemetry logs, and vector embeddings. |
| **psycopg2-binary** | High-performance PostgreSQL database adapter for Python. |
| **SQLite** | Out-of-the-box local database fallback for local testing and offline execution. |
| **SQLAlchemy** | Object Relational Mapper (ORM) with automated schema migrations, connection pooling, and batch execution. |

### 6. Email, Calendar & Microsoft 365
| Technology | Role & Purpose |
|---|---|
| **Microsoft Graph API** | Cloud communications backend for sending emails, polling inboxes, and inspecting calendars. |
| **MSAL (Microsoft Authentication Library)** | Secure enterprise OAuth 2.0 app-only client credentials authentication and automatic token caching. |
| **Outlook Calendar API** | Availability lookahead, conflict prevention, and appointment scheduling. |
| **Microsoft Bookings** | Direct integration with enterprise scheduling links. |

### 7. Spreadsheet Processing & Audit Logging
| Technology | Role & Purpose |
|---|---|
| **Pandas** | High-performance DataFrame operations, lead filtering, and dataset deduplication. |
| **OpenPyXL** | Native read/write operations for Excel workbooks (`.xlsx`) and audit ledger persistence. |
| **Google API Client & Google Auth** | Optional connector for synchronizing inbound responses from Google Sheets / Forms. |

### 8. Analytics & Report Generation
| Technology | Role & Purpose |
|---|---|
| **ReportLab** | Enterprise PDF document layout engine producing publication-ready executive dossiers. |
| **Matplotlib** | Static and interactive chart generation for open-rate velocity and engagement distributions. |
| **NumPy** | Vector math computations, statistical aggregations, and engagement scoring algorithms. |

### 9. DevOps & Infrastructure
| Technology | Role & Purpose |
|---|---|
| **Docker & Docker Compose** | Multi-container orchestration (FastAPI backend, Streamlit frontend, Nginx reverse proxy). |
| **Nginx** | Reverse proxy, static asset routing, and unified port forwarding. |

---

## 🎯 Key Features & Capabilities

### 1. Executive Dashboard Modules
1. **Pipeline Overview**: High-level funnel visualization tracking stage velocity from raw lead to confirmed booking, complemented by real-time KPI metrics and chronological activity streams.
2. **Analytics & Telemetry**: 14 analytical visualizers analyzing open rates, click-through rates, reply sentiment, bounce handling, and engagement scoring.
3. **Template Hub**: Curated responsive corporate HTML email templates with live client sandboxing, personalization tag references, and batch generation triggers.
4. **Upload & Ingestion**: Drag-and-drop file ingestion supporting Excel and CSV formats with smart column mapping and instant deduplication against historical records.
5. **Leads Directory**: Centralized directory with full-text search, campaign filtering, and status drill-down.
6. **Email Review Studio**: Granular human-in-the-loop review interface with live Outlook/Apple Mail previews, real-time token interpolation, and single or batch dispatching.
7. **Replies & Bookings**: Real-time shared mailbox synchronization, RAG knowledge ingestion interface, vector playground, and calendar appointment tracking.

### 2. Autonomous Background Workers
- **Continuous Reply Daemon**: Scans the support mailbox at configurable intervals, classifies lead messages, performs RAG context retrieval, and sends answers automatically.
- **Batch Campaign Runner**: Headless command-line utility for executing automated pipeline runs across scheduled intervals.
- **Production Keepalive Service**: Automated health-check prober ensuring uninterrupted availability on cloud hosts.

---

## 📁 Project Directory & Module Structure

```
.
├── Agent/                         # AI & Agentic Orchestration Layer
│   ├── agents/
│   │   └── composer.py            # AI email composition logic
│   ├── graph.py                   # LangGraph state machine definition
│   ├── llm.py                     # Provider factory (Gemini / Claude)
│   ├── reply_agent.py             # Inbound reply parser & intent classifier
│   └── state.py                   # State schema definitions for LangGraph
├── Backend/                       # Core API & Data Layer
│   ├── api.py                     # FastAPI server (telemetry, webhooks, health)
│   ├── crud.py                    # Batched database queries & sync logic
│   ├── db.py                      # SQLAlchemy connection manager & schema initialization
│   ├── keepalive.py               # Background keepalive worker implementation
│   └── models.py                  # Database schemas (CampaignLog, KnowledgeDocument)
├── Calendar/                      # Calendar & Meeting Scheduling Layer
│   ├── availability.py            # Working hour slot calculator & collision detector
│   ├── config.py                  # Scheduling parameters & office hour rules
│   └── outlook_calendar.py        # Microsoft Graph Calendar & Teams link generator
├── Email/                         # Email Delivery & Template Layer
│   ├── base.py                    # Abstract base mailer interface
│   ├── config.py                  # Email service configuration
│   ├── draft_options.py           # Responsive HTML templates with CDN styling
│   ├── outlook_mailer.py          # Microsoft Graph API email dispatcher
│   └── templates.py               # Transactional & confirmation email templates
├── services/                      # Business Logic & Analytical Engines
│   ├── analytics_export.py        # PDF (ReportLab) & Excel dossier generators
│   ├── analytics_service.py       # KPI computation & statistical engines
│   ├── excel_logger.py            # Permanent Excel audit ledger operations
│   ├── rag.py                     # Text chunking, Gemini embeddings & cosine search
│   └── template_service.py        # Template registry & placeholder interpolation
├── utils/                         # Utilities & Design Assets
│   ├── microsoft_auth.py          # MSAL OAuth 2.0 token acquisition wrapper
│   ├── theme.py                   # Modern dual-theme CSS design system
│   └── token.py                   # Unique token generator for telemetry tracking
├── knowledge_base/                # Raw documentation repository (.pdf, .md, .txt)
├── analytics_view.py              # Streamlit view: 14 telemetry & analytics visualizers
├── dashboard.py                   # Main Streamlit application entry point
├── docker-compose.yml             # Container orchestration specification
├── Dockerfile                     # Multi-stage container build file
├── keepalive_worker.py            # CLI runner for keepalive service
├── leads.py                       # Lead file loader & data sanitization utility
├── main_api.py                    # CLI runner for FastAPI service
├── nginx.conf                     # Nginx reverse proxy configuration
├── reply_worker.py                # CLI runner for autonomous reply daemon
├── requirements.txt               # Complete Python package dependency manifest
├── seed_knowledge_base.py         # Vector embedding ingestion tool
└── worker.py                      # Headless batch campaign runner
```

---

## 🚀 Installation & Quickstart

### 1. Prerequisites
- **Python**: Version 3.10 to 3.14
- **Database**: PostgreSQL (Supabase, Neon, AWS RDS, or local instance) or SQLite
- **Microsoft 365 Tenant**: Azure AD App Registration with application permissions
- **LLM API Key**: Google AI API key (Gemini) or Anthropic API key (Claude)

### 2. Clone & Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd lead

# Create and activate virtual environment
python -m venv .venv

# On Windows PowerShell:
.venv\Scripts\Activate.ps1

# On Linux / macOS:
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

---

## ⚙️ Environment Configuration

Create your `.env` configuration by copying the template:

```bash
cp .env.example .env
```

Populate `.env` with generic credentials matching your infrastructure:

```ini
# ==============================================================================
# LEAD DATASET CONFIGURATION
# ==============================================================================
LEADS_FILE=leads.xlsx
STALE_AFTER_DAYS=90
CAMPAIGN_NAME=lead_reengagement_q3

# ==============================================================================
# DATABASE CONFIGURATION
# PostgreSQL connection string (SQLite fallback is used if left blank)
# ==============================================================================
DATABASE_URL=postgresql+psycopg2://db_user:db_password@localhost:5432/lead_intelligence

# ==============================================================================
# TELEMETRY & API HOST CONFIGURATION
# Base URL where the FastAPI service is accessible for tracking pixels & redirects
# ==============================================================================
API_BASE_URL=http://localhost:8000
PORT=8000

# ==============================================================================
# LLM & VECTOR EMBEDDING PROVIDER (Google Gemini / Anthropic)
# ==============================================================================
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=models/text-embedding-004

# Optional: Anthropic Claude settings (if LLM_PROVIDER=claude)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CLAUDE_MODEL=claude-sonnet-4-6

# ==============================================================================
# MICROSOFT 365 / OUTLOOK / GRAPH API CREDENTIALS
# ==============================================================================
EMAIL_PROVIDER=outlook
MS_TENANT_ID=your_azure_tenant_id_here
MS_CLIENT_ID=your_azure_client_id_here
MS_CLIENT_SECRET=your_azure_client_secret_here

# Mailbox used for outbound dispatch, inbound replies, and calendar scheduling
MS_SENDER_EMAIL=outreach@example.com
CONTACT_EMAIL=support@example.com
CONTACT_PHONE=+1-555-0100

# ==============================================================================
# SCHEDULING & BOOKINGS INTEGRATION
# ==============================================================================
BOOKING_FORM_URL=https://bookings.cloud.microsoft/book/organization@example.com/consultation
FORM_BASE_URL=http://localhost:8000

# Working hours configuration (0=Monday, 4=Friday)
OFFICE_HOURS_TZ=UTC
OFFICE_HOURS_START=09:00
OFFICE_HOURS_END=18:00
OFFICE_HOURS_DAYS=0,1,2,3,4
MEETING_DURATION_MINUTES=30
AVAILABILITY_LOOKAHEAD_DAYS=14

# Scheduling fallback strategy ("auto_propose" or "manual_flag")
SCHEDULING_FALLBACK=auto_propose
AUTO_PROPOSE_LOOKAHEAD_DAYS=7
AUTO_PROPOSE_SLOT_COUNT=3
```

---

## 🔐 Microsoft Entra ID (Azure AD) Setup

To allow the platform to send emails, monitor inbound replies, and manage calendar events via the Microsoft Graph API:

1. **Register Application**:
   - Go to **Microsoft Entra ID** (Azure Portal) -> **App registrations** -> **New registration**.
   - Set a name and choose **Accounts in this organizational directory only (Single tenant)**.
2. **Generate Credentials**:
   - Under **Certificates & secrets**, generate a **New client secret**.
   - Copy the value immediately into `MS_CLIENT_SECRET`.
   - Copy the **Application (client) ID** into `MS_CLIENT_ID` and **Directory (tenant) ID** into `MS_TENANT_ID`.
3. **Configure API Permissions**:
   - Under **API permissions** -> **Add a permission** -> **Microsoft Graph** -> **Application permissions**, grant:
     - `Mail.Send` (to send outbound campaign emails and auto-replies)
     - `Mail.Read` (to monitor inbound customer responses)
     - `Calendars.ReadWrite` (to check schedule availability and book meetings)
4. **Grant Admin Consent**:
   - Click **Grant admin consent for [Your Organization]** to activate the permissions.

---

## 🖥️ Running the Platform

### Option A: Standard Two-Terminal Workflow

For interactive development and day-to-day operations:

**Terminal 1 — Telemetry & Webhook API:**
```powershell
python main_api.py
```
*The FastAPI server starts on `http://localhost:8000`, serving tracking pixels, redirects, and webhooks.*

**Terminal 2 — Executive Streamlit Dashboard:**
```powershell
streamlit run dashboard.py
```
*The dashboard opens in your browser at `http://localhost:8501`.*

---

## 🤖 Background Autonomous Daemons

The platform includes modular standalone daemons for background execution:

### 1. Inbound Reply Daemon (`reply_worker.py`)
Monitors the shared Outlook mailbox, classifies customer replies, queries the RAG vector store, and sends grounded responses.

```powershell
# Continuous monitoring (runs every 30 seconds):
python reply_worker.py --interval 30

# Single execution (processes unread messages and exits):
python reply_worker.py --once
```

### 2. Knowledge Base Indexer (`seed_knowledge_base.py`)
Parses `.pdf`, `.md`, and `.txt` files in `knowledge_base/`, computes dense vector embeddings using Google Gemini, and indexes them into the database:

```powershell
python seed_knowledge_base.py
```

### 3. Headless Campaign Outreach Runner (`worker.py`)
Iterates through stale leads in the dataset, checks deduplication flags, generates drafts, and sends them headlessly:

```powershell
python worker.py
```

### 4. Deployment Keepalive Worker (`keepalive_worker.py`)
Pings the primary application endpoint at set intervals to avoid cloud container sleep states:

```powershell
python keepalive_worker.py --interval 540
```

---

## 🐳 Docker Deployment

The application includes a production-grade multi-container `docker-compose.yml` configuration:

```bash
# Build and run the backend, frontend, and reverse proxy in the background
docker-compose up -d --build

# Inspect container status
docker-compose ps

# View unified application logs
docker-compose logs -f
```

### Service Map:
- **Nginx Reverse Proxy**: Accessible on port `80` (routes API traffic to `8000` and dashboard traffic to `8501`).
- **FastAPI Telemetry**: Port `8000`.
- **Streamlit Dashboard**: Port `8501`.

---

## 🔒 Security, Privacy & Best Practices

- **Strict Secret Isolation**: No API keys, credentials, or client secrets are committed to version control. The `.gitignore` file explicitly excludes `.env` and local cache directories.
- **Pre-Send Deduplication**: Multi-tier checks prevent repeat outreach to the same recipient across database records, current drafts, and historical flags.
- **Zero-Hallucination Vector Retrieval**: Vector retrieval enforces a minimum cosine similarity threshold (`0.35`) so queries that do not match knowledge base content trigger graceful escalation rather than fabricated answers.
- **Sandboxed Rendering**: Customer email previews and HTML templates are isolated within sandboxed iframes, blocking arbitrary script execution and stylesheet conflicts.
- **Stateless Token Telemetry**: Tracking pixels and click redirects utilize cryptographically unique UUIDs, avoiding exposure of internal database identifiers in outbound links.

---

## 📄 License

This project is distributed under the **MIT License**. Refer to the [LICENSE](LICENSE) file for complete details.
