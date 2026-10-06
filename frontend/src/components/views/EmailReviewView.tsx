"use client";

import React, { useState, useEffect, useMemo } from "react";
import HeaderBanner from "@/components/layout/HeaderBanner";
import { api, CampaignLogItem, TemplateItem } from "@/lib/api";
import {
  Mail,
  Send,
  XCircle,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Code,
  Eye,
  FileEdit,
  Save,
  Sparkles,
  Layers,
  Check,
} from "lucide-react";

interface EmailReviewViewProps {
  onDraftsApproved?: () => void;
  onNavigateToUpload?: () => void;
  activeSenderEmail?: string;
}

export default function EmailReviewView({
  onDraftsApproved,
  onNavigateToUpload,
  activeSenderEmail,
}: EmailReviewViewProps = {}) {
  const [drafts, setDrafts] = useState<CampaignLogItem[]>([]);
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("tpl_fde_velocity");

  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [viewMode, setViewMode] = useState<"preview" | "edit">("preview");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchInitialData = async () => {
    try {
      setLoading(true);
      const [draftsRes, tplsRes] = await Promise.all([
        api.getPendingDrafts(),
        api.getTemplates(),
      ]);
      const draftList = draftsRes.drafts || [];
      setDrafts(draftList);
      setTemplates(tplsRes.templates || []);

      if (draftList.length > 0) {
        const first = draftList[0];
        setSelectedId(first.id);
        setSubject(first.subject || "");
        setBody(first.body || "");
        if (first.template_id) {
          setSelectedTemplateId(first.template_id);
        }
      }
    } catch (e: any) {
      console.error("Failed to load drafts or templates", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInitialData();
  }, []);

  const currentDraft = useMemo(() => {
    return drafts.find((d) => d.id === selectedId) || drafts[0];
  }, [drafts, selectedId]);

  const handleSelectDraft = (id: string) => {
    setSelectedId(id);
    const selected = drafts.find((d) => d.id === id);
    if (selected) {
      setSubject(selected.subject || "");
      setBody(selected.body || "");
      if (selected.template_id) {
        setSelectedTemplateId(selected.template_id);
      }
    }
  };

  // Apply selected template to this single draft
  const handleApplyTemplate = async () => {
    if (!selectedId) return;
    setSaving(true);
    try {
      const res = await api.applyTemplateToDraft(selectedId, selectedTemplateId);
      if (res.draft) {
        setSubject(res.draft.subject || "");
        setBody(res.draft.body || "");
        setDrafts((prev) =>
          prev.map((d) => (d.id === selectedId ? { ...d, ...res.draft } : d))
        );
      }
      setActionMessage("⭐ Template successfully applied with prospect placeholders!");
      setTimeout(() => setActionMessage(null), 3500);
    } catch (e: any) {
      alert("Failed to apply template: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  // Apply selected template to all pending drafts
  const handleApplyTemplateAll = async () => {
    if (drafts.length === 0) return;
    const tName = templates.find((t) => t.id === selectedTemplateId)?.name || selectedTemplateId;
    if (!confirm(`Apply "${tName}" to all ${drafts.length} pending drafts?`)) return;

    setSaving(true);
    try {
      const res = await api.applyTemplateAll(selectedTemplateId);
      setActionMessage(`⭐ Successfully formatted all ${res.updated_count} drafts with ${tName}!`);
      // Re-fetch to sync
      const freshDrafts = await api.getPendingDrafts();
      setDrafts(freshDrafts.drafts || []);
      if (selectedId) {
        const updated = (freshDrafts.drafts || []).find((d) => d.id === selectedId);
        if (updated) {
          setSubject(updated.subject || "");
          setBody(updated.body || "");
        }
      }
      setTimeout(() => setActionMessage(null), 4000);
    } catch (e: any) {
      alert("Failed to apply template in bulk: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  // Save edits to subject/body
  const handleSaveDraft = async () => {
    if (!selectedId) return;
    setSaving(true);
    try {
      await api.updateDraft(selectedId, { subject, body });
      setDrafts((prev) =>
        prev.map((d) => (d.id === selectedId ? { ...d, subject, body } : d))
      );
      setActionMessage("💾 Draft changes saved successfully!");
      setTimeout(() => setActionMessage(null), 3000);
    } catch (e: any) {
      alert("Failed to save draft: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  // Approve & 1-Click Send via Microsoft Graph
  const handleApproveAndSend = async () => {
    if (!selectedId) return;
    setSaving(true);
    try {
      await api.approveAndSendDraft(selectedId);
      setActionMessage(`🚀 Email successfully dispatched to ${currentDraft?.email} via Microsoft Graph!`);
      const nextDrafts = drafts.filter((d) => d.id !== selectedId);
      setDrafts(nextDrafts);
      if (nextDrafts.length > 0) {
        handleSelectDraft(nextDrafts[0].id);
      }
      if (onDraftsApproved) onDraftsApproved();
      setTimeout(() => setActionMessage(null), 4500);
    } catch (e: any) {
      alert("Failed to dispatch email: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  // Reject single draft
  const handleReject = async () => {
    if (!selectedId) return;
    setSaving(true);
    try {
      await api.rejectDraft(selectedId);
      setActionMessage("✕ Draft rejected and archived.");
      const nextDrafts = drafts.filter((d) => d.id !== selectedId);
      setDrafts(nextDrafts);
      if (nextDrafts.length > 0) {
        handleSelectDraft(nextDrafts[0].id);
      }
      setTimeout(() => setActionMessage(null), 3000);
    } catch (e: any) {
      alert("Failed to reject draft: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  // Bulk Approve & Send All
  const handleSendAll = async () => {
    if (drafts.length === 0) return;
    if (!confirm(`Are you sure you want to approve and dispatch all ${drafts.length} pending drafts via Microsoft Graph?`)) return;

    setSaving(true);
    try {
      const res = await api.sendAllDrafts();
      setActionMessage(`✅ Bulk dispatch complete: ${res.sent_count} sent, ${res.failed_count} failed.`);
      const freshDrafts = await api.getPendingDrafts();
      setDrafts(freshDrafts.drafts || []);
      if (freshDrafts.drafts && freshDrafts.drafts.length > 0) {
        handleSelectDraft(freshDrafts.drafts[0].id);
      }
      if (onDraftsApproved) onDraftsApproved();
      setTimeout(() => setActionMessage(null), 5000);
    } catch (e: any) {
      alert("Batch dispatch error: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  // Bulk Reject All
  const handleRejectAll = async () => {
    if (drafts.length === 0) return;
    if (!confirm(`Are you sure you want to reject all ${drafts.length} pending drafts without sending?`)) return;

    setSaving(true);
    try {
      const res = await api.rejectAllDrafts();
      setActionMessage(`✕ Successfully rejected all ${res.rejected_count} drafts.`);
      setDrafts([]);
      setTimeout(() => setActionMessage(null), 4000);
    } catch (e: any) {
      alert("Reject all error: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-20 space-y-2">
        <RefreshCw className="w-6 h-6 animate-spin text-[#2563EB]" />
        <span className="text-[13px] text-[#64748B]">Loading pending email drafts...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Top Header Banner ── */}
      <HeaderBanner
        title="Email Review Studio"
        subtitle="Inspect AI-generated drafts, customize messaging, review live previews, and dispatch via Microsoft Graph."
        badgeText="Quality Control"
        badgeType="live"
        action={
          drafts.length > 0 ? (
            <button
              onClick={handleSendAll}
              disabled={saving}
              className="px-4 py-2 bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-bold text-[12.5px] rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
            >
              <span>⚡ Bulk Approve &amp; Send All ({drafts.length})</span>
            </button>
          ) : null
        }
      />

      {actionMessage && (
        <div className="p-3.5 bg-[#ECFDF5] border border-[#A7F3D0] rounded-xl text-[#065F46] font-semibold text-[13px] animate-in fade-in duration-150">
          {actionMessage}
        </div>
      )}

      {/* ── Empty State: Zero Drafts Awaiting Review ── */}
      {drafts.length === 0 ? (
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-16 text-center text-[#64748B] space-y-4 shadow-[0_1px_3px_rgba(0,0,0,0.03)]">
          <div className="w-16 h-16 rounded-2xl bg-[#EFF6FF] text-[#2563EB] flex items-center justify-center text-3xl mx-auto border border-[#BFDBFE]">
            📬
          </div>
          <div className="space-y-1">
            <h3 className="font-bold text-[#0F172A] text-lg">No Pending Drafts Awaiting Review</h3>
            <p className="text-[13.5px] max-w-md mx-auto text-[#64748B]">
              All draft queues are clear. Upload a lead sheet in &quot;Upload &amp; Draft&quot; to generate new personalized outreach sequences.
            </p>
          </div>
          {onNavigateToUpload && (
            <button
              onClick={onNavigateToUpload}
              className="px-5 py-2.5 bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-bold text-[13px] rounded-xl shadow-sm transition-colors"
            >
              Upload Spreadsheet &amp; Generate Drafts &rarr;
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-5">
          {/* Human-in-the-Loop Alert Banner */}
          <div className="bg-[#FFFBEB] border border-[#FDE68A] rounded-xl p-3.5 flex items-center justify-between flex-wrap gap-2 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
            <div className="flex items-center gap-2 font-bold text-[#92400E] text-[13.5px]">
              <span>📬</span>
              <span><strong>{drafts.length}</strong> draft email(s) awaiting your executive approval</span>
            </div>
            <span className="badge badge-drafted text-[11px]">Human-in-the-Loop</span>
          </div>

          {/* ── Draft Selector & Template Switcher Ribbon ── */}
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.02)] space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
              {/* Draft Selector (7 cols) */}
              <div className="md:col-span-7 space-y-1">
                <label className="block text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
                  Select Draft to Review ({drafts.length} in queue):
                </label>
                <select
                  value={selectedId}
                  onChange={(e) => handleSelectDraft(e.target.value)}
                  className="w-full text-[13px] bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg px-3 py-2 text-[#0F172A] font-semibold focus:outline-none focus:border-[#2563EB]"
                >
                  {drafts.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name ? `${d.name} (${d.email})` : d.email} — {d.company || "Enterprise"}
                    </option>
                  ))}
                </select>
              </div>

              {/* Template Switcher (5 cols) */}
              <div className="md:col-span-5 space-y-1">
                <label className="block text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
                  Apply Outreach Template:
                </label>
                <div className="flex items-center gap-2">
                  <select
                    value={selectedTemplateId}
                    onChange={(e) => setSelectedTemplateId(e.target.value)}
                    className="w-full text-[12.5px] bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg px-3 py-2 text-[#0F172A] font-semibold focus:outline-none focus:border-[#2563EB]"
                  >
                    {templates.map((t) => (
                      <option key={t.id} value={String(t.id)}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={handleApplyTemplate}
                    disabled={saving}
                    className="px-3 py-2 bg-[#F1F5F9] hover:bg-[#E2E8F0] text-[#1E293B] font-bold text-[12px] rounded-lg border border-[#CBD5E1] whitespace-nowrap transition-colors"
                    title="Apply chosen template to this draft"
                  >
                    ⭐ Apply
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* ── Lead Profile & Outreach Target Cards ── */}
          {currentDraft && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Lead Profile Card */}
              <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.02)] space-y-1.5 text-[13px]">
                <div className="flex justify-between items-center pb-2 border-b border-[#F1F5F9]">
                  <span className="font-bold text-[#0F172A] text-[13.5px]">Lead Profile</span>
                  <span className="badge badge-pending text-[10.5px]">Verified Contact</span>
                </div>
                <div className="text-[#334155]">
                  <strong className="text-[#0F172A]">Full Name:</strong> {currentDraft.name || "N/A"}
                </div>
                <div className="text-[#334155]">
                  <strong className="text-[#0F172A]">Company:</strong> {currentDraft.company || "N/A"}
                </div>
                <div className="text-[11.5px] text-[#64748B]">
                  Lead Identifier: <code className="text-[#2563EB] font-mono">{currentDraft.lead_id || currentDraft.id}</code>
                </div>
              </div>

              {/* Outreach Target Card */}
              <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.02)] space-y-1.5 text-[13px]">
                <div className="flex justify-between items-center pb-2 border-b border-[#F1F5F9]">
                  <span className="font-bold text-[#0F172A] text-[13.5px]">Outreach Target</span>
                  <span className="badge badge-drafted text-[10.5px]">DRAFTED</span>
                </div>
                <div className="text-[#334155]">
                  <strong className="text-[#0F172A]">Recipient:</strong>{" "}
                  <code className="font-mono font-semibold text-[#2563EB]">{currentDraft.email}</code>
                </div>
                <div className="text-[#334155] flex items-center gap-1.5">
                  <strong className="text-[#0F172A]">Booking CTA:</strong>
                  <a
                    href="https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled"
                    target="_blank"
                    rel="noreferrer"
                    className="text-[#2563EB] font-semibold underline inline-flex items-center gap-1"
                  >
                    <span>Microsoft Bookings (Cloud)</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <div className="text-[11.5px] text-[#64748B]">
                  Active Template: <strong className="text-[#0F172A]">{currentDraft.template_name || "Template 1"}</strong>
                </div>
              </div>
            </div>
          )}

          {/* ── Subject Line Editor ── */}
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.02)] space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-[11.5px] font-bold text-[#64748B] uppercase tracking-wider">
                Subject Line:
              </label>
              <button
                onClick={handleSaveDraft}
                disabled={saving}
                className="text-[12px] font-bold text-[#2563EB] hover:underline flex items-center gap-1"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save Subject &amp; Body</span>
              </button>
            </div>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full text-[14px] font-semibold text-[#0F172A] bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg px-3.5 py-2.5 focus:outline-none focus:border-[#2563EB]"
            />
          </div>

          {/* ── Email Body Editor & Live Outlook Preview ── */}
          <div className="bg-white border border-[#CBD5E1] rounded-2xl overflow-hidden shadow-sm">
            {/* Outlook / Webmail Client View Header */}
            <div className="bg-[#F8FAFC] px-4 py-2.5 border-b border-[#CBD5E1] flex items-center justify-between flex-wrap gap-2 text-[12px]">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#EF4444]"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B]"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-[#10B981]"></span>
                <span className="font-semibold text-[#334155] ml-2">
                  Outlook / Webmail Client View
                </span>
              </div>

              {/* View Toggle */}
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setViewMode("preview")}
                  className={`px-3 py-1 rounded-md text-[11.5px] font-semibold transition-colors flex items-center gap-1.5 ${
                    viewMode === "preview"
                      ? "bg-[#2563EB] text-white shadow-2xs"
                      : "bg-white text-[#475569] border border-[#CBD5E1] hover:bg-[#F1F5F9]"
                  }`}
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>Live Email Preview</span>
                </button>
                <button
                  onClick={() => setViewMode("edit")}
                  className={`px-3 py-1 rounded-md text-[11.5px] font-semibold transition-colors flex items-center gap-1.5 ${
                    viewMode === "edit"
                      ? "bg-[#2563EB] text-white shadow-2xs"
                      : "bg-white text-[#475569] border border-[#CBD5E1] hover:bg-[#F1F5F9]"
                  }`}
                >
                  <FileEdit className="w-3.5 h-3.5" />
                  <span>Edit Body / HTML</span>
                </button>
              </div>
            </div>

            {/* Recipient Routing Subheader */}
            <div className="px-4 py-2 bg-white border-b border-[#F1F5F9] text-[12px] text-[#475569] flex flex-wrap gap-4">
              <div>
                <strong className="text-[#1E293B]">From:</strong> Neno Technology Outreach &lt;{activeSenderEmail || "mohit@nenotechnology.us"}&gt;
              </div>
              <div>
                <strong className="text-[#1E293B]">To:</strong> {currentDraft?.name || "Lead"} &lt;{currentDraft?.email}&gt;
              </div>
            </div>

            {/* Preview or Code Area */}
            <div className="p-3 bg-[#F1F5F9]">
              {viewMode === "preview" ? (
                <iframe
                  title="Draft Live Preview"
                  srcDoc={body}
                  className="w-full bg-white rounded-xl shadow-xs border border-[#CBD5E1]"
                  style={{ height: "650px" }}
                  sandbox="allow-same-origin"
                />
              ) : (
                <textarea
                  rows={20}
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className="w-full p-4 font-mono text-[12px] bg-white border border-[#CBD5E1] rounded-xl text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              )}
            </div>
          </div>

          {/* ── Single Draft Action Bar ── */}
          <div className="flex items-center justify-between flex-wrap gap-3 pt-2">
            <div className="flex items-center gap-2">
              <button
                onClick={handleReject}
                disabled={saving}
                className="px-4 py-2 bg-[#FEF2F2] hover:bg-[#FEE2E2] text-[#DC2626] font-bold text-[12.5px] rounded-lg border border-[#FECACA] transition-colors flex items-center gap-1.5"
              >
                <XCircle className="w-4 h-4" />
                <span>Reject Draft</span>
              </button>

              <button
                onClick={handleSaveDraft}
                disabled={saving}
                className="px-4 py-2 bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#334155] font-bold text-[12.5px] rounded-lg border border-[#CBD5E1] transition-colors flex items-center gap-1.5"
              >
                <Save className="w-4 h-4" />
                <span>Save Changes</span>
              </button>
            </div>

            <button
              onClick={handleApproveAndSend}
              disabled={saving}
              className="px-5 py-2.5 bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-bold text-[13px] rounded-xl shadow-md transition-colors flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              <span>Approve &amp; Send Now (1-Click)</span>
            </button>
          </div>

          {/* ── BATCH OPERATIONS & BULK DISPATCH CENTER (Exact Streamlit Match) ── */}
          <hr className="border-0 border-t border-[#E2E8F0] my-6" />

          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
            <div className="flex justify-between items-center flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="text-lg">⚡</span>
                <span className="font-bold text-[#0F172A] text-[15px]">
                  Bulk Operations &amp; Dispatch Center ({drafts.length} Leads)
                </span>
              </div>
              <span className="badge badge-drafted text-[11px] font-semibold">
                {drafts.length} Leads Ready
              </span>
            </div>

            <p className="text-[12.5px] text-[#64748B]">
              Approve and send all remaining drafts formatted with your chosen executive template, or reject remaining drafts without dispatching emails.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                onClick={handleApplyTemplateAll}
                disabled={saving}
                className="px-4 py-2.5 bg-[#EFF6FF] hover:bg-[#DBEAFE] text-[#1D4ED8] font-bold text-[12.5px] rounded-xl border border-[#BFDBFE] transition-colors flex items-center justify-center gap-1.5"
              >
                <span>⭐ Apply Template to All ({drafts.length})</span>
              </button>

              <button
                onClick={handleSendAll}
                disabled={saving}
                className="px-4 py-2.5 bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-bold text-[12.5px] rounded-xl shadow-sm transition-colors flex items-center justify-center gap-1.5 sm:col-span-1"
              >
                <span>🚀 Bulk Approve &amp; Send Remaining ({drafts.length})</span>
              </button>

              <button
                onClick={handleRejectAll}
                disabled={saving}
                className="px-4 py-2.5 bg-[#FEF2F2] hover:bg-[#FEE2E2] text-[#DC2626] font-bold text-[12.5px] rounded-xl border border-[#FECACA] transition-colors flex items-center justify-center gap-1.5"
              >
                <XCircle className="w-4 h-4" />
                <span>Reject All Drafts ({drafts.length})</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
