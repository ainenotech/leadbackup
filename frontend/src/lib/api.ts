export interface OverviewStats {
  total_leads: number;
  drafted_leads: number;
  sent_leads: number;
  replied_leads: number;
  forms_filled: number;
  scheduled_leads: number;
  draft_pct: number;
  sent_pct: number;
  reply_pct: number;
  form_pct: number;
  booked_pct: number;
}

export interface CampaignLogItem {
  id: string;
  campaign: string;
  lead_id: string;
  email: string;
  name: string;
  company: string;
  phone: string;
  status: string;
  subject: string;
  body: string;
  email_sent_at: string | null;
  send_error: string;
  opened: boolean;
  open_count: number;
  first_open_at: string | null;
  last_open_at: string | null;
  clicked_link: boolean;
  click_count: number;
  first_click_at: string | null;
  last_click_at: string | null;
  clicked_urls: string;
  unsubscribed: boolean;
  unsubscribed_at: string | null;
  bounced: boolean;
  bounce_reason: string;
  engagement_score: number;
  form_filled_at: string | null;
  submitted_availability: string;
  note: string;
  reply_body: string;
  reply_intent: string;
  reply_received_at: string | null;
  ai_reply_sent: string;
  ai_reply_sent_at: string | null;
  proposed_slot: string;
  confirmed_slot: string;
  meet_link: string;
  booking_status: string;
  token: string;
  tracking_link: string;
  template_id: string;
  template_name: string;
  created_at: string | null;
}

export interface ActivityFeedEvent {
  id: string;
  lead_id: string;
  name: string;
  email: string;
  company: string;
  event_type: string;
  badge: string;
  badge_color: string;
  timestamp: string;
  relative_time: string;
  details: string;
}

export interface MasterDbLead {
  id: string;
  email: string;
  name: string;
  company: string;
  phone: string;
  status: string;
  template_id: string;
  template_name: string;
  opened: boolean;
  open_count: number;
  clicked_link: boolean;
  click_count: number;
  reply_body: string;
  reply_intent: string;
  reply_received_at: string | null;
  booking_status: string;
  confirmed_slot: string;
  meet_link: string;
  form_filled_at: string | null;
  email_sent_at: string | null;
  created_at: string | null;
  job_title: string;
  last_activity_date: string;
  location: string;
  tier: "HOT" | "WARM" | "COLD";
  score?: number;
  activity_summary?: string;
  tier_display?: string;
}

export interface TemplateItem {
  id: number | string;
  name: string;
  category: string;
  description: string;
  subject?: string;
  body?: string;
  system_instructions?: string;
  tone?: string;
  created_at?: string;
  is_active?: boolean;
  total_sent?: number;
  total_opened?: number;
  total_replied?: number;
  open_rate?: number;
  reply_rate?: number;
  html_content?: string;
  accent_color?: string;
  badge?: string;
  stats?: {
    total_leads?: number;
    sent?: number;
    opened?: number;
    replied?: number;
    open_rate?: number;
    reply_rate?: number;
    booked?: number;
    clicked?: number;
  };
}

export interface ReplyItem {
  id: string;
  lead_id: string;
  name: string;
  email: string;
  company: string;
  reply_intent: string;
  reply_body: string;
  reply_received_at: string | null;
  ai_reply_sent: string;
  ai_reply_sent_at: string | null;
  booking_status: string;
  confirmed_slot: string;
  meet_link: string;
  note: string;
  customer_reply?: string;
  ai_response_sent?: string;
}

export interface BookingItem {
  id: string;
  lead_id: string;
  name: string;
  email: string;
  company: string;
  booking_status: string;
  confirmed_slot: string;
  service: string;
  note: string;
}

// ── Multi-Tenant SaaS & Auth Interfaces ──
export interface AuthUser {
  id: string;
  email: string;
  full_name: string | null;
  platform_role: string;
  status: string;
  is_verified?: boolean;
}

export interface AuthOrganization {
  id: string;
  name: string;
  slug: string;
  status: string;
  role?: string;
  is_default?: boolean;
  settings?: Record<string, any>;
  plan_tier?: string;
  created_at?: string;
}

export interface TeamMember {
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  status: string;
  is_default: boolean;
  joined_at: string;
}

export interface SendingDomain {
  id: string;
  domain: string;
  status: "verified" | "pending" | "failed" | "paused";
  reputation_score?: number;
  created_at?: string;
  records?: Array<{
    type: string;
    name: string;
    value: string;
    status: string;
  }>;
}

export interface SuperAdminMetrics {
  total_organizations: number;
  active_organizations: number;
  total_users: number;
  total_leads: number;
  total_campaign_logs: number;
  total_kb_docs: number;
}

// ── Auth Token Helpers ──
const TOKEN_KEY = "ain_session_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
  document.cookie = `session_token=${token}; path=/; max-age=2592000; SameSite=Lax`;
}

export function clearStoredToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
  document.cookie = "session_token=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 UTC;";
}

function getAuthHeaders(): Record<string, string> {
  const token = getStoredToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export const api = {
  // ── Authentication & Multi-Tenancy ──
  async login(payload: { email: string; password: string }): Promise<{
    access_token: string;
    token_type: string;
    user: AuthUser;
    organization: AuthOrganization;
    organizations: AuthOrganization[];
  }> {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail || "Invalid email or password");
    }
    const data = await res.json();
    if (data.access_token) {
      setStoredToken(data.access_token);
    }
    return data;
  },

  async register(payload: {
    org_name: string;
    admin_email: string;
    password: string;
    full_name?: string;
  }): Promise<{
    access_token: string;
    user: AuthUser;
    organization: AuthOrganization;
    organizations: AuthOrganization[];
  }> {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Registration failed" }));
      throw new Error(err.detail || "Registration failed");
    }
    const data = await res.json();
    if (data.access_token) {
      setStoredToken(data.access_token);
    }
    return data;
  },

  async getMe(): Promise<{
    user: AuthUser;
    organization: AuthOrganization;
    active_organization?: AuthOrganization;
    organizations: AuthOrganization[];
  }> {
    const res = await fetch("/api/auth/me", {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Unauthorized");
    const json = await res.json();
    return json.data || json;
  },

  async switchOrg(organization_id: string): Promise<{
    access_token: string;
    organization: AuthOrganization;
  }> {
    const res = await fetch("/api/auth/switch-org", {
      method: "POST",
      headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ organization_id }),
    });
    if (!res.ok) throw new Error("Failed to switch workspace");
    const json = await res.json();
    const data = json.data || json;
    if (data.access_token) {
      setStoredToken(data.access_token);
    }
    return data;
  },

  // ── Team Members ──
  async getOrgMembers(orgId: string): Promise<TeamMember[]> {
    const res = await fetch(`/api/org/${orgId}/members`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to load team members");
    const json = await res.json();
    return json.members || [];
  },

  async inviteOrgMember(
    orgId: string,
    payload: { email: string; role: string; full_name?: string; temporary_password?: string }
  ): Promise<any> {
    const res = await fetch(`/api/org/${orgId}/members`, {
      method: "POST",
      headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Invite failed" }));
      throw new Error(err.detail || "Invite failed");
    }
    return res.json();
  },

  async updateMemberRole(orgId: string, userId: string, role: string): Promise<any> {
    const res = await fetch(`/api/org/${orgId}/members/${userId}/role`, {
      method: "PUT",
      headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    });
    if (!res.ok) throw new Error("Failed to update member role");
    return res.json();
  },

  async removeOrgMember(orgId: string, userId: string): Promise<any> {
    const res = await fetch(`/api/org/${orgId}/members/${userId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to remove member");
    return res.json();
  },

  // ── Workspace Settings ──
  async getOrgSettings(orgId: string): Promise<any> {
    const res = await fetch(`/api/org/${orgId}/settings`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to load settings");
    return res.json();
  },

  async updateOrgSettings(orgId: string, settings: any): Promise<any> {
    const res = await fetch(`/api/org/${orgId}/settings`, {
      method: "PUT",
      headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    if (!res.ok) throw new Error("Failed to save settings");
    return res.json();
  },

  // ── Super Admin Portal ──
  async getSuperAdminOverview(): Promise<{
    metrics: SuperAdminMetrics;
    organizations: AuthOrganization[];
  }> {
    const res = await fetch("/api/admin/overview", {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Super Admin access required");
    const json = await res.json();
    return json.data || json;
  },

  async setOrgStatus(orgId: string, status: "active" | "suspended"): Promise<any> {
    const res = await fetch(`/api/admin/org/${orgId}/status`, {
      method: "PUT",
      headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) throw new Error("Failed to update status");
    return res.json();
  },

  // ── Sending Domains & DNS ──
  async getDomains(orgId: string): Promise<SendingDomain[]> {
    const res = await fetch(`/api/domains/${orgId}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) return [];
    const json = await res.json();
    return json.domains || [];
  },

  async registerDomain(orgId: string, domain: string): Promise<any> {
    const res = await fetch(`/api/domains/${orgId}`, {
      method: "POST",
      headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ domain }),
    });
    if (!res.ok) throw new Error("Failed to register domain");
    return res.json();
  },

  async verifyDomain(orgId: string, domainId: string): Promise<any> {
    const res = await fetch(`/api/domains/${orgId}/${domainId}/verify`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Verification failed");
    return res.json();
  },

  async deleteDomain(orgId: string, domainId: string): Promise<any> {
    const res = await fetch(`/api/domains/${orgId}/${domainId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to remove domain");
    return res.json();
  },

  // ── Pipeline & Telemetry Endpoints ──
  async getOverviewStats(): Promise<OverviewStats> {
    const res = await fetch("/api/realtime/summary");
    if (!res.ok) throw new Error("Failed to load overview stats");
    const json = await res.json();
    const m = json.metrics || json;
    const total = m.total_leads || 0;
    const sent = m.sent ?? m.sent_leads ?? 0;
    const replied = m.replied ?? m.replied_leads ?? 0;
    const booked = m.booked ?? m.scheduled_leads ?? 0;
    const drafted = m.drafted ?? m.drafted_leads ?? Math.max(0, total - sent);
    const formFilled = m.forms_filled ?? m.booked ?? 0;

    return {
      total_leads: total,
      drafted_leads: drafted,
      sent_leads: sent,
      replied_leads: replied,
      forms_filled: formFilled,
      scheduled_leads: booked,
      draft_pct: total > 0 ? Math.round((drafted / total) * 100) : 0,
      sent_pct: total > 0 ? Math.round((sent / total) * 100) : 0,
      reply_pct: sent > 0 ? Math.round((replied / sent) * 100) : 0,
      form_pct: sent > 0 ? Math.round((formFilled / sent) * 100) : 0,
      booked_pct: sent > 0 ? Math.round((booked / sent) * 100) : 0,
    };
  },

  async getLogs(params?: {
    status?: string;
    campaign?: string;
    search?: string;
    limit?: number;
  }): Promise<{ total: number; logs: CampaignLogItem[] }> {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.campaign) qs.set("campaign", params.campaign);
    if (params?.search) qs.set("search", params.search);
    if (params?.limit) qs.set("limit", params.limit.toString());
    const res = await fetch(`/api/logs?${qs.toString()}`);
    if (!res.ok) throw new Error("Failed to load logs");
    return res.json();
  },

  async getRealtimeFeed(limit = 25): Promise<{ status: string; total_events: number; events: ActivityFeedEvent[] }> {
    const res = await fetch(`/api/realtime/feed?limit=${limit}`);
    if (!res.ok) throw new Error("Failed to load realtime feed");
    return res.json();
  },

  async getFullAnalytics(): Promise<{ status: string; features: any[]; data: any }> {
    const res = await fetch("/api/analytics/full");
    if (!res.ok) throw new Error("Failed to load analytics");
    return res.json();
  },

  async getMasterDb(): Promise<{ total: number; leads: MasterDbLead[]; counts: { hot: number; warm: number; cold: number } }> {
    const res = await fetch("/api/master-db");
    if (!res.ok) throw new Error("Failed to load master db");
    return res.json();
  },

  async getTemplates(): Promise<{ templates: TemplateItem[]; total: number }> {
    const res = await fetch("/api/templates");
    if (!res.ok) throw new Error("Failed to load templates");
    return res.json();
  },

  async getTemplateDetail(id: string): Promise<{ template: TemplateItem; sample_preview: { subject: string; body: string } }> {
    const res = await fetch(`/api/templates/${encodeURIComponent(id)}`);
    if (!res.ok) throw new Error("Failed to load template");
    return res.json();
  },

  async uploadLeadsFile(file: File): Promise<any> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch("/api/leads/upload", {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Upload failed");
    }
    return res.json();
  },

  async generateDrafts(payload: { leads: any[]; template_id?: string; campaign_name?: string }): Promise<any> {
    const res = await fetch("/api/drafts/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Draft generation failed" }));
      throw new Error(err.detail || "Draft generation failed");
    }
    return res.json();
  },

  async getPendingDrafts(): Promise<{ total: number; drafts: CampaignLogItem[] }> {
    const res = await fetch("/api/drafts");
    if (!res.ok) throw new Error("Failed to load pending drafts");
    return res.json();
  },

  async updateDraft(id: string, payload: { subject: string; body: string }): Promise<any> {
    const res = await fetch(`/api/drafts/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to update draft");
    return res.json();
  },

  async approveAndSendDraft(id: string): Promise<any> {
    const res = await fetch(`/api/drafts/${id}/approve`, {
      method: "POST",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Approval failed" }));
      throw new Error(err.detail || "Approval failed");
    }
    return res.json();
  },

  async rejectDraft(id: string): Promise<any> {
    const res = await fetch(`/api/drafts/${id}/reject`, {
      method: "POST",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to reject draft" }));
      throw new Error(err.detail || "Failed to reject draft");
    }
    return res.json();
  },

  async applyTemplateToDraft(id: string, template_id: string): Promise<any> {
    const res = await fetch(`/api/drafts/${id}/apply-template`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ template_id }),
    });
    if (!res.ok) throw new Error("Failed to apply template to draft");
    return res.json();
  },

  async applyTemplateAll(template_id: string): Promise<{ success: boolean; updated_count: number }> {
    const res = await fetch("/api/drafts/apply-template-all", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ template_id }),
    });
    if (!res.ok) throw new Error("Failed to apply template to all drafts");
    return res.json();
  },

  async rejectAllDrafts(): Promise<{ success: boolean; rejected_count: number }> {
    const res = await fetch("/api/drafts/reject-all", {
      method: "POST",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to reject all drafts" }));
      throw new Error(err.detail || "Failed to reject all drafts");
    }
    return res.json();
  },

  async renderTemplate(payload: {
    template_id?: string | number;
    lead_name?: string;
    company?: string;
    pain_point?: string;
  }): Promise<{ subject: string; body: string }> {
    const res = await fetch("/api/templates/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to render template preview");
    return res.json();
  },

  async sendAllDrafts(): Promise<{ sent_count: number; failed_count: number; errors: string[] }> {
    const res = await fetch("/api/drafts/send-all", {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to dispatch drafts in batch");
    return res.json();
  },

  async getReplies(): Promise<{ total: number; replies: ReplyItem[] }> {
    const res = await fetch("/api/replies");
    if (!res.ok) throw new Error("Failed to load replies");
    return res.json();
  },

  async getBookings(): Promise<{ total: number; bookings: BookingItem[] }> {
    const res = await fetch("/api/bookings");
    if (!res.ok) throw new Error("Failed to load bookings");
    return res.json();
  },

  async checkInboxNow(): Promise<any> {
    const res = await fetch("/api/replies/check-inbox", {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to check inbox");
    return res.json();
  },

  async getDaemonStatus(): Promise<{ running: boolean; last_run: string | null }> {
    const res = await fetch("/api/daemon/status");
    if (!res.ok) throw new Error("Failed to get daemon status");
    return res.json();
  },

  async startDaemon(): Promise<any> {
    const res = await fetch("/api/daemon/start", { method: "POST" });
    if (!res.ok) throw new Error("Failed to start daemon");
    return res.json();
  },

  async stopDaemon(): Promise<any> {
    const res = await fetch("/api/daemon/stop", { method: "POST" });
    if (!res.ok) throw new Error("Failed to stop daemon");
    return res.json();
  },

  // ── Knowledge Base Endpoints ──
  async getKbSummary(): Promise<{
    total_chunks: number;
    total_documents: number;
    documents: Array<{ title: string; category?: string; chunk_count?: number; chunks?: number }>;
    embedding_model: string;
  }> {
    const res = await fetch("/api/kb/summary");
    if (!res.ok) throw new Error("Failed to load KB summary");
    return res.json();
  },

  async getKbDocuments(): Promise<{ documents: Array<{ title: string; category?: string; chunk_count?: number; chunks?: number }> }> {
    const res = await fetch("/api/kb/documents");
    if (!res.ok) return { documents: [] };
    return res.json();
  },

  async uploadKbFile(file: File, category?: string): Promise<any> {
    const formData = new FormData();
    formData.append("file", file);
    if (category) formData.append("category", category);
    const res = await fetch("/api/kb/upload", {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Failed to upload KB document");
    return res.json();
  },

  async deleteKbDocument(title: string): Promise<any> {
    const res = await fetch(`/api/kb/documents?title=${encodeURIComponent(title)}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete document");
    return res.json();
  },

  async searchKb(query: string, top_k = 4): Promise<{ query: string; chunks: any[] }> {
    const res = await fetch("/api/kb/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k }),
    });
    if (!res.ok) throw new Error("Search failed");
    return res.json();
  },

  async clearKb(): Promise<any> {
    const res = await fetch("/api/kb/clear", { method: "POST" });
    if (!res.ok) throw new Error("Failed to clear KB");
    return res.json();
  },

  // ── System Operations ──
  async pingRenderNow(): Promise<any> {
    const res = await fetch("/api/keepalive/ping");
    if (!res.ok) throw new Error("Failed to ping Render");
    return res.json();
  },

  async syncSystemData(): Promise<any> {
    const res = await fetch("/api/system/sync", { method: "POST" });
    if (!res.ok) throw new Error("Failed to sync data");
    return res.json();
  },

  async resetAllData(): Promise<any> {
    const res = await fetch("/api/system/reset-all", { method: "POST" });
    if (!res.ok) throw new Error("Failed to reset system data");
    return res.json();
  },
};
