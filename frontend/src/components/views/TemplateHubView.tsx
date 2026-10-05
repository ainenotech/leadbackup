"use client";

import React, { useState, useEffect, useMemo } from "react";
import HeaderBanner from "@/components/layout/HeaderBanner";
import { api, TemplateItem } from "@/lib/api";
import {
  RefreshCw,
  Check,
  Copy,
  ExternalLink,
  Code,
  Eye,
  FileText,
  Search,
  Sparkles,
  RotateCcw,
  Save,
  CheckCircle2,
  Trophy,
  TrendingUp,
  Layers,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

export default function TemplateHubView() {
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | number>("");
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"gallery" | "analytics" | "batch">("gallery");

  // Filter & Search states
  const [searchKw, setSearchKw] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All Categories");

  // Simulation variables
  const [simName, setSimName] = useState("Alex");
  const [simCompany, setSimCompany] = useState("Acme Health");
  const [simPain, setSimPain] = useState("manual operational overhead");

  // Preview view modes: rendered iframe, raw HTML, plain text
  const [viewMode, setViewMode] = useState<"rendered" | "html" | "text">("rendered");
  const [copiedSubject, setCopiedSubject] = useState(false);
  const [copiedHtml, setCopiedHtml] = useState(false);

  // Edit drawers
  const [editSubjectOpen, setEditSubjectOpen] = useState(false);
  const [editHtmlOpen, setEditHtmlOpen] = useState(false);
  const [customTitle, setCustomTitle] = useState("");
  const [customSubject, setCustomSubject] = useState("");
  const [customHtml, setCustomHtml] = useState("");
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const fetchTemplates = async () => {
    try {
      setLoading(true);
      const res = await api.getTemplates();
      const tpls = res.templates || [];
      setTemplates(tpls);
      if (tpls.length > 0 && !selectedId) {
        setSelectedId(tpls[0].id);
      }
    } catch (e: any) {
      console.error("Failed to load templates", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const currentTemplate = useMemo(() => {
    return templates.find((t) => String(t.id) === String(selectedId)) || templates[0];
  }, [templates, selectedId]);

  // Sync edit drawers when currentTemplate changes
  useEffect(() => {
    if (currentTemplate) {
      setCustomTitle(currentTemplate.name || "");
      setCustomSubject(currentTemplate.subject || "");
      setCustomHtml(currentTemplate.html_content || currentTemplate.body || "");
    }
  }, [currentTemplate]);

  // Categories list
  const categories = useMemo(() => {
    const cats = new Set(templates.map((t) => t.category || "General"));
    return ["All Categories", ...Array.from(cats).sort()];
  }, [templates]);

  // Filtered templates list
  const filteredTemplates = useMemo(() => {
    return templates.filter((t) => {
      const matchCat =
        selectedCategory === "All Categories" || (t.category || "General") === selectedCategory;
      const kw = searchKw.toLowerCase().trim();
      const matchKw =
        !kw ||
        t.name?.toLowerCase().includes(kw) ||
        t.subject?.toLowerCase().includes(kw) ||
        t.description?.toLowerCase().includes(kw) ||
        t.category?.toLowerCase().includes(kw);
      return matchCat && matchKw;
    });
  }, [templates, selectedCategory, searchKw]);

  // Client-side lead placeholder interpolation
  const interpolatePlaceholders = (text: string, first: string, comp: string, pain: string) => {
    if (!text) return "";
    return text
      .replace(/\{\{?\s*(?:first_?name|lead_?name|name|recipient_?name)\s*\}?\}/gi, first)
      .replace(/\{\{?\s*(?:company_?name|company|client|business)\s*\}?\}/gi, comp)
      .replace(/\{\{?\s*(?:pain_?point|pain|challenge)\s*\}?\}/gi, pain)
      .replace(/LOGO_URL/g, "https://res.cloudinary.com/dqreqsjas/image/upload/v1789542387/logo-dark.png")
      .replace(/BOOKING_LINK/g, "https://bookings.cloud.microsoft/book/Connect@nenotechnology.com/?ismsaljsauthenabled")
      .replace(/LINKEDIN_URL/g, "https://www.linkedin.com/in/tirthpatel-ai/")
      .replace(/UNSUBSCRIBE_LINK/g, "#unsubscribe");
  };

  // Live rendered subject and HTML body
  const renderedSubject = useMemo(() => {
    const rawSubj = customSubject || currentTemplate?.subject || "";
    return interpolatePlaceholders(rawSubj, simName, simCompany, simPain);
  }, [customSubject, currentTemplate, simName, simCompany, simPain]);

  const renderedHtml = useMemo(() => {
    const rawHtml = customHtml || currentTemplate?.html_content || currentTemplate?.body || "";
    return interpolatePlaceholders(rawHtml, simName, simCompany, simPain);
  }, [customHtml, currentTemplate, simName, simCompany, simPain]);

  // Copy helpers
  const handleCopySubject = () => {
    navigator.clipboard.writeText(renderedSubject);
    setCopiedSubject(true);
    setTimeout(() => setCopiedSubject(false), 2000);
  };

  const handleCopyHtml = () => {
    navigator.clipboard.writeText(renderedHtml);
    setCopiedHtml(true);
    setTimeout(() => setCopiedHtml(false), 2000);
  };

  // Convert HTML to simple plain text for the "text" tab
  const plainTextVersion = useMemo(() => {
    if (!renderedHtml) return "";
    let t = renderedHtml
      .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, "")
      .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, "")
      .replace(/<\/p>/gi, "\n\n")
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/div>/gi, "\n")
      .replace(/<\/li>/gi, "\n")
      .replace(/<[^>]+>/gi, "")
      .replace(/&nbsp;/g, " ")
      .replace(/&bull;/g, "•")
      .replace(/&middot;/g, "·")
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">");
    return t.trim();
  }, [renderedHtml]);

  // Trophy analytics metrics
  const trophyStats = useMemo(() => {
    if (!templates.length) return null;
    const sortedOpen = [...templates].sort((a, b) => (b.stats?.open_rate || 0) - (a.stats?.open_rate || 0));
    const sortedClick = [...templates].sort((a, b) => (b.stats?.clicked || 0) - (a.stats?.clicked || 0));
    const sortedReply = [...templates].sort((a, b) => (b.stats?.replied || 0) - (a.stats?.replied || 0));
    const sortedBook = [...templates].sort((a, b) => (b.stats?.booked || 0) - (a.stats?.booked || 0));

    return {
      topOpen: sortedOpen[0],
      topClick: sortedClick[0],
      topReply: sortedReply[0],
      topBook: sortedBook[0],
    };
  }, [templates]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-20 space-y-2">
        <RefreshCw className="w-6 h-6 animate-spin text-[#2563EB]" />
        <span className="text-[13px] text-[#64748B]">Loading Email Template Studio...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Top Executive Banner ── */}
      <HeaderBanner
        title="✉️ Email Template Studio"
        subtitle="Review and customize responsive executive HTML templates with real-time lead simulation, copy outreach copy, and pair batch outreach cohorts."
        badgeText={`${templates.length} Templates Ready`}
        badgeType="live"
        action={
          <div className="flex items-center gap-2">
            <span className="badge badge-sent text-[11px] px-2.5 py-1">
              ✓ Responsive HTML &bull; Tirth Patel Signatures
            </span>
          </div>
        }
      />

      {actionNotice && (
        <div className="p-3 bg-[#ECFDF5] border border-[#A7F3D0] rounded-xl text-[#065F46] font-semibold text-[13px]">
          {actionNotice}
        </div>
      )}

      {/* ── Tabs Navigation ── */}
      <div className="flex items-center gap-2 border-b border-[#E2E8F0] pb-2 flex-wrap">
        <button
          onClick={() => setActiveTab("gallery")}
          className={`px-4 py-2 rounded-lg text-[13px] font-bold transition-all ${
            activeTab === "gallery"
              ? "bg-[#2563EB] text-white shadow-xs"
              : "bg-white text-[#475569] border border-[#E2E8F0] hover:bg-[#F8FAFC]"
          }`}
        >
          🎨 Template Studio &amp; Live Preview ({templates.length})
        </button>
        <button
          onClick={() => setActiveTab("analytics")}
          className={`px-4 py-2 rounded-lg text-[13px] font-bold transition-all ${
            activeTab === "analytics"
              ? "bg-[#2563EB] text-white shadow-xs"
              : "bg-white text-[#475569] border border-[#E2E8F0] hover:bg-[#F8FAFC]"
          }`}
        >
          📈 Performance Analytics &amp; Daily Trends
        </button>
        <button
          onClick={() => setActiveTab("batch")}
          className={`px-4 py-2 rounded-lg text-[13px] font-bold transition-all ${
            activeTab === "batch"
              ? "bg-[#2563EB] text-white shadow-xs"
              : "bg-white text-[#475569] border border-[#E2E8F0] hover:bg-[#F8FAFC]"
          }`}
        >
          📤 Sheet-to-Template Batch Outreach (20–25 Leads)
        </button>
      </div>

      {/* ═══════════════════════════════════════════════════════════════
          TAB 1: TEMPLATE STUDIO & LIVE PREVIEW (38% Left / 62% Right)
         ═══════════════════════════════════════════════════════════════ */}
      {activeTab === "gallery" && currentTemplate && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* ── LEFT COLUMN: Template Directory (5 of 12 cols) ── */}
          <div className="lg:col-span-5 space-y-3">
            <div className="bg-white border border-[#E2E8F0] rounded-xl p-3.5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-2.5">
              <div className="flex justify-between items-center">
                <span className="font-bold text-[#0F172A] text-[13.5px]">📑 Template Directory</span>
                <span className="text-[11px] text-[#64748B]">Click template to preview</span>
              </div>

              {/* Search & Category Filter */}
              <div className="grid grid-cols-2 gap-2">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[#94A3B8]" />
                  <input
                    type="text"
                    value={searchKw}
                    onChange={(e) => setSearchKw(e.target.value)}
                    placeholder="Filter templates..."
                    className="w-full pl-8 pr-2 py-1.5 text-[12px] bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                  />
                </div>

                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="w-full py-1.5 px-2 text-[12px] bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg text-[#0F172A] font-medium focus:outline-none focus:border-[#2563EB]"
                >
                  {categories.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Template Cards List */}
            <div className="space-y-2.5 max-h-[820px] overflow-y-auto pr-1">
              {filteredTemplates.map((t) => {
                const isSelected = String(t.id) === String(selectedId);
                const accent = t.accent_color || "#2563EB";

                return (
                  <div
                    key={t.id}
                    onClick={() => setSelectedId(t.id)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? "bg-[#F8FAFC] border-[#2563EB] shadow-md ring-1 ring-[#2563EB]"
                        : "bg-white border-[#E2E8F0] hover:border-[#CBD5E1] hover:bg-[#F8FAFC]"
                    }`}
                    style={{
                      borderLeftWidth: isSelected ? "4px" : "3px",
                      borderLeftColor: isSelected ? accent : "#CBD5E1",
                    }}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <h4 className="font-bold text-[#0F172A] text-[13.5px] leading-snug">
                        {t.name}
                      </h4>
                      {isSelected ? (
                        <span
                          className="text-[9.5px] font-bold text-white px-2 py-0.5 rounded-full shrink-0 tracking-wider"
                          style={{ backgroundColor: accent }}
                        >
                          ● ACTIVE
                        </span>
                      ) : (
                        <span className="text-[10px] font-bold text-[#64748B] bg-[#F1F5F9] px-2 py-0.5 rounded shrink-0">
                          {t.category || "General"}
                        </span>
                      )}
                    </div>

                    <p className="text-[12px] text-[#475569] leading-relaxed mb-2 line-clamp-2">
                      {t.description}
                    </p>

                    <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-2 text-[11px] text-[#334155] font-mono break-all">
                      <span className="font-sans font-bold text-[#64748B] mr-1">Subject:</span>
                      <span>{t.subject}</span>
                    </div>

                    {t.stats && (t.stats.sent || 0) > 0 && (
                      <div className="mt-2 flex items-center gap-3 text-[11px] text-[#64748B] pt-1 border-t border-[#F1F5F9]">
                        <span>Sent: <strong className="text-[#0F172A]">{t.stats.sent}</strong></span>
                        <span>Open: <strong className="text-[#2563EB]">{t.stats.open_rate}%</strong></span>
                        <span>Clicks: <strong className="text-[#0D9488]">{t.stats.clicked || 0}</strong></span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* ── RIGHT COLUMN: Live Inspector & Email Preview (7 of 12 cols) ── */}
          <div className="lg:col-span-7 bg-white border border-[#E2E8F0] rounded-2xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
            {/* Live Prospect Simulation Bar */}
            <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3.5 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-[11.5px] font-bold text-[#64748B] uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-[#2563EB]" />
                  <span>Real-Time Lead Simulation Parameters:</span>
                </span>
                <span className="text-[11px] text-[#2563EB] font-semibold">Live Interpolating</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[12px]">
                <div>
                  <label className="block text-[10.5px] font-semibold text-[#64748B] mb-0.5">
                    Lead Name:
                  </label>
                  <input
                    type="text"
                    value={simName}
                    onChange={(e) => setSimName(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-white border border-[#CBD5E1] rounded-lg font-semibold text-[#0F172A]"
                  />
                </div>
                <div>
                  <label className="block text-[10.5px] font-semibold text-[#64748B] mb-0.5">
                    Target Company:
                  </label>
                  <input
                    type="text"
                    value={simCompany}
                    onChange={(e) => setSimCompany(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-white border border-[#CBD5E1] rounded-lg font-semibold text-[#0F172A]"
                  />
                </div>
                <div>
                  <label className="block text-[10.5px] font-semibold text-[#64748B] mb-0.5">
                    Operational Pain:
                  </label>
                  <input
                    type="text"
                    value={simPain}
                    onChange={(e) => setSimPain(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-white border border-[#CBD5E1] rounded-lg font-semibold text-[#0F172A]"
                  />
                </div>
              </div>
            </div>

            {/* Simulated macOS / Outlook Email Header */}
            <div className="border border-[#CBD5E1] rounded-xl overflow-hidden shadow-sm">
              {/* Window Chrome Header */}
              <div className="bg-[#F1F5F9] px-4 py-2.5 border-b border-[#CBD5E1] flex items-center justify-between text-[12px]">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#EF4444]"></span>
                  <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B]"></span>
                  <span className="w-2.5 h-2.5 rounded-full bg-[#10B981]"></span>
                  <span className="font-bold text-[#0F172A] ml-2 text-[13px]">
                    Live Preview: {currentTemplate.name}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="badge badge-neutral text-[10.5px]">
                    {currentTemplate.category || "Executive Outreach"}
                  </span>
                </div>
              </div>

              {/* Subject Line & Routing Meta Box */}
              <div className="bg-white p-4 border-b border-[#E2E8F0] space-y-2">
                <div className="flex justify-between items-center text-[11px] text-[#64748B]">
                  <span className="uppercase font-bold tracking-wider">Subject Line</span>
                  <span className="font-mono bg-[#F0F9FF] text-[#0284C7] px-2 py-0.5 rounded border border-[#BAE6FD]">
                    Pattern: {currentTemplate.subject}
                  </span>
                </div>
                <div className="font-bold text-[#0F172A] text-base leading-snug">
                  {renderedSubject}
                </div>
                <div className="flex flex-wrap gap-4 text-[12px] text-[#64748B] pt-1 border-t border-[#F8FAFC]">
                  <div>
                    <strong className="text-[#334155]">From:</strong> Tirth Patel &lt;support@nenotechnology.com&gt;
                  </div>
                  <div>
                    <strong className="text-[#334155]">To:</strong> {simName} &lt;contact@{simCompany.toLowerCase().replace(/\s+/g, "")}.com&gt;
                  </div>
                </div>
              </div>

              {/* View Mode Bar & Copy Actions */}
              <div className="bg-[#F8FAFC] px-4 py-2 border-b border-[#E2E8F0] flex items-center justify-between flex-wrap gap-2 text-[12px]">
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => setViewMode("rendered")}
                    className={`px-3 py-1 rounded-md font-semibold text-[11.5px] transition-colors flex items-center gap-1.5 ${
                      viewMode === "rendered"
                        ? "bg-[#2563EB] text-white shadow-2xs"
                        : "bg-white text-[#475569] border border-[#CBD5E1] hover:bg-[#F1F5F9]"
                    }`}
                  >
                    <Eye className="w-3.5 h-3.5" />
                    <span>Rendered Email (Client View)</span>
                  </button>
                  <button
                    onClick={() => setViewMode("html")}
                    className={`px-3 py-1 rounded-md font-semibold text-[11.5px] transition-colors flex items-center gap-1.5 ${
                      viewMode === "html"
                        ? "bg-[#2563EB] text-white shadow-2xs"
                        : "bg-white text-[#475569] border border-[#CBD5E1] hover:bg-[#F1F5F9]"
                    }`}
                  >
                    <Code className="w-3.5 h-3.5" />
                    <span>HTML Source</span>
                  </button>
                  <button
                    onClick={() => setViewMode("text")}
                    className={`px-3 py-1 rounded-md font-semibold text-[11.5px] transition-colors flex items-center gap-1.5 ${
                      viewMode === "text"
                        ? "bg-[#2563EB] text-white shadow-2xs"
                        : "bg-white text-[#475569] border border-[#CBD5E1] hover:bg-[#F1F5F9]"
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Plain Text</span>
                  </button>
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={handleCopySubject}
                    className="px-2.5 py-1 text-[11.5px] font-semibold bg-white hover:bg-[#F1F5F9] text-[#334155] border border-[#CBD5E1] rounded-md transition-colors flex items-center gap-1"
                  >
                    {copiedSubject ? <Check className="w-3 h-3 text-[#059669]" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedSubject ? "Copied Subj!" : "Copy Subject"}</span>
                  </button>

                  <button
                    onClick={handleCopyHtml}
                    className="px-2.5 py-1 text-[11.5px] font-semibold bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-md transition-colors flex items-center gap-1"
                  >
                    {copiedHtml ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedHtml ? "Copied HTML!" : "Copy HTML Code"}</span>
                  </button>
                </div>
              </div>

              {/* ── LIVE PREVIEW CONTENT (ISOLATED IFRAME FOR 100% FIDELITY) ── */}
              <div className="bg-[#F1F5F9] p-3">
                {viewMode === "rendered" && (
                  <iframe
                    title="Live Template Preview"
                    srcDoc={renderedHtml}
                    className="w-full bg-white rounded-xl shadow-xs border border-[#CBD5E1]"
                    style={{ height: "680px" }}
                    sandbox="allow-same-origin"
                  />
                )}

                {viewMode === "html" && (
                  <pre className="p-4 bg-[#0F172A] text-[#E2E8F0] font-mono text-[11.5px] rounded-xl overflow-x-auto max-h-[680px] leading-relaxed whitespace-pre-wrap">
                    {renderedHtml}
                  </pre>
                )}

                {viewMode === "text" && (
                  <div className="p-6 bg-white rounded-xl shadow-xs border border-[#CBD5E1] text-[13.5px] text-[#1E293B] leading-relaxed whitespace-pre-wrap font-sans max-h-[680px] overflow-y-auto">
                    {plainTextVersion}
                  </div>
                )}
              </div>
            </div>

            {/* Subject Line & Title Customization Accordion */}
            <div className="border border-[#E2E8F0] rounded-xl overflow-hidden">
              <button
                onClick={() => setEditSubjectOpen(!editSubjectOpen)}
                className="w-full px-4 py-3 bg-[#F8FAFC] flex justify-between items-center text-[12.5px] font-bold text-[#334155] hover:bg-[#F1F5F9] transition-colors"
              >
                <span>✏️ Edit Subject Line &amp; Template Title (Dynamic Placeholders)</span>
                {editSubjectOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {editSubjectOpen && (
                <div className="p-4 bg-white border-t border-[#E2E8F0] space-y-3 text-[12.5px]">
                  <p className="text-[#64748B] text-[12px]">
                    Customize the display title and subject line pattern. Tags like <code>{`{{Company}}`}</code> and <code>{`{{FirstName}}`}</code> carry over automatically.
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-bold text-[#64748B] uppercase mb-1">
                        Template Title
                      </label>
                      <input
                        type="text"
                        value={customTitle}
                        onChange={(e) => setCustomTitle(e.target.value)}
                        className="w-full px-3 py-2 border border-[#CBD5E1] rounded-lg text-[#0F172A] font-semibold"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-bold text-[#64748B] uppercase mb-1">
                        Subject Line Pattern
                      </label>
                      <input
                        type="text"
                        value={customSubject}
                        onChange={(e) => setCustomSubject(e.target.value)}
                        className="w-full px-3 py-2 border border-[#CBD5E1] rounded-lg text-[#0F172A] font-semibold"
                      />
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      onClick={() => {
                        setCustomTitle(currentTemplate.name);
                        setCustomSubject(currentTemplate.subject || "");
                        setActionNotice("↺ Reset to built-in template subject.");
                        setTimeout(() => setActionNotice(null), 3000);
                      }}
                      className="px-3 py-1.5 text-[11.5px] font-semibold bg-[#F1F5F9] hover:bg-[#E2E8F0] text-[#475569] rounded-lg transition-colors flex items-center gap-1"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Reset to Default</span>
                    </button>
                    <button
                      onClick={() => {
                        setActionNotice("✅ Subject line preferences updated for live simulation!");
                        setTimeout(() => setActionNotice(null), 3000);
                      }}
                      className="px-3.5 py-1.5 text-[11.5px] font-semibold bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-lg transition-colors flex items-center gap-1"
                    >
                      <Save className="w-3.5 h-3.5" />
                      <span>Apply Changes</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Inspect & Edit HTML Code Accordion */}
            <div className="border border-[#E2E8F0] rounded-xl overflow-hidden">
              <button
                onClick={() => setEditHtmlOpen(!editHtmlOpen)}
                className="w-full px-4 py-3 bg-[#F8FAFC] flex justify-between items-center text-[12.5px] font-bold text-[#334155] hover:bg-[#F1F5F9] transition-colors"
              >
                <span>🛠️ Inspect &amp; Customize HTML Source Code</span>
                {editHtmlOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {editHtmlOpen && (
                <div className="p-4 bg-white border-t border-[#E2E8F0] space-y-3 text-[12.5px]">
                  <p className="text-[#64748B] text-[12px]">
                    Directly modify responsive table styles, callout copy, or signature tags.
                  </p>
                  <textarea
                    rows={10}
                    value={customHtml}
                    onChange={(e) => setCustomHtml(e.target.value)}
                    className="w-full p-3 font-mono text-[11.5px] bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => {
                        setCustomHtml(currentTemplate.html_content || currentTemplate.body || "");
                        setActionNotice("↺ Reset template HTML to built-in code.");
                        setTimeout(() => setActionNotice(null), 3000);
                      }}
                      className="px-3 py-1.5 text-[11.5px] font-semibold bg-[#F1F5F9] hover:bg-[#E2E8F0] text-[#475569] rounded-lg transition-colors flex items-center gap-1"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Reset HTML</span>
                    </button>
                    <button
                      onClick={() => {
                        setActionNotice("✅ Template HTML updated in active session!");
                        setTimeout(() => setActionNotice(null), 3000);
                      }}
                      className="px-3.5 py-1.5 text-[11.5px] font-semibold bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-lg transition-colors flex items-center gap-1"
                    >
                      <Save className="w-3.5 h-3.5" />
                      <span>Save HTML</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════
          TAB 2: PERFORMANCE ANALYTICS & DAILY TRENDS
         ═══════════════════════════════════════════════════════════════ */}
      {activeTab === "analytics" && (
        <div className="space-y-6">
          {/* Trophy KPI Cards */}
          {trophyStats && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 relative overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.03)]">
                <div className="absolute top-0 left-0 right-0 h-1 bg-[#2563EB]"></div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-[12px] font-semibold text-[#64748B]">🏆 Top Open Rate</span>
                  <span className="text-base">👁️</span>
                </div>
                <div className="text-2xl font-bold text-[#0F172A]">
                  {trophyStats.topOpen?.stats?.open_rate || 0}%
                </div>
                <div className="mt-1 text-[11px] text-[#64748B] truncate">
                  {trophyStats.topOpen?.name?.split(":")[0] || "Template 1"}
                </div>
              </div>

              <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 relative overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.03)]">
                <div className="absolute top-0 left-0 right-0 h-1 bg-[#0D9488]"></div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-[12px] font-semibold text-[#0D9488]">🏆 Top Click Rate</span>
                  <span className="text-base">🖱️</span>
                </div>
                <div className="text-2xl font-bold text-[#0D9488]">
                  {trophyStats.topClick?.stats?.clicked || 0} Clicks
                </div>
                <div className="mt-1 text-[11px] text-[#64748B] truncate">
                  {trophyStats.topClick?.name?.split(":")[0] || "Template 1"}
                </div>
              </div>

              <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 relative overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.03)]">
                <div className="absolute top-0 left-0 right-0 h-1 bg-[#7C3AED]"></div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-[12px] font-semibold text-[#7C3AED]">🏆 Top Reply Rate</span>
                  <span className="text-base">💬</span>
                </div>
                <div className="text-2xl font-bold text-[#7C3AED]">
                  {trophyStats.topReply?.stats?.replied || 0} Replies
                </div>
                <div className="mt-1 text-[11px] text-[#64748B] truncate">
                  {trophyStats.topReply?.name?.split(":")[0] || "Template 1"}
                </div>
              </div>

              <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 relative overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.03)]">
                <div className="absolute top-0 left-0 right-0 h-1 bg-[#059669]"></div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-[12px] font-semibold text-[#059669]">🏆 Total Consultations</span>
                  <span className="text-base">📅</span>
                </div>
                <div className="text-2xl font-bold text-[#059669]">
                  {trophyStats.topBook?.stats?.booked || 0} Booked
                </div>
                <div className="mt-1 text-[11px] text-[#64748B] truncate">
                  Across all campaigns
                </div>
              </div>
            </div>
          )}

          {/* Matrix Table */}
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-3">
            <h3 className="font-bold text-[#0F172A] text-[15px]">Outreach Template Performance Matrix</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[13px] border-collapse">
                <thead className="bg-[#F8FAFC] text-[#475569] border-y border-[#E2E8F0] text-[11px] uppercase font-bold">
                  <tr>
                    <th className="py-3 px-3">Template Name</th>
                    <th className="py-3 px-3 text-center">Assigned Leads</th>
                    <th className="py-3 px-3 text-center">Opened</th>
                    <th className="py-3 px-3 text-center">Clicked</th>
                    <th className="py-3 px-3 text-center">Replied</th>
                    <th className="py-3 px-3 text-center">Open Rate</th>
                    <th className="py-3 px-3 text-center">Reply Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F1F5F9]">
                  {templates.map((t) => (
                    <tr key={t.id} className="hover:bg-[#F8FAFC]">
                      <td className="py-3 px-3 font-semibold text-[#0F172A]">
                        {t.name}
                        <div className="text-[11px] text-[#64748B] font-normal">{t.category}</div>
                      </td>
                      <td className="py-3 px-3 text-center font-bold">{t.stats?.sent || 0}</td>
                      <td className="py-3 px-3 text-center font-bold text-[#2563EB]">{t.stats?.opened || 0}</td>
                      <td className="py-3 px-3 text-center font-bold text-[#0D9488]">{t.stats?.clicked || 0}</td>
                      <td className="py-3 px-3 text-center font-bold text-[#7C3AED]">{t.stats?.replied || 0}</td>
                      <td className="py-3 px-3 text-center font-bold text-[#2563EB]">{t.stats?.open_rate || 0}%</td>
                      <td className="py-3 px-3 text-center font-bold text-[#7C3AED]">{t.stats?.reply_rate || 0}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════
          TAB 3: SHEET-TO-TEMPLATE BATCH OUTREACH (20–25 LEADS)
         ═══════════════════════════════════════════════════════════════ */}
      {activeTab === "batch" && (
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-6 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-5">
          <div>
            <h3 className="font-bold text-[#0F172A] text-lg">
              Sheet-to-Template Batch Outreach (20–25 Leads per Cohort)
            </h3>
            <p className="text-[13px] text-[#64748B] mt-1">
              Maximize deliverability and inbox placement by sending curated batches of 20 to 25 leads per template cohort with Microsoft Graph throttling.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl space-y-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#2563EB] bg-[#EFF6FF] px-2 py-0.5 rounded border border-[#BFDBFE]">
                Step 1
              </span>
              <h4 className="font-bold text-[#0F172A] text-sm">Upload Spreadsheet</h4>
              <p className="text-[12px] text-[#64748B]">
                Upload CSV or Excel files with prospect names, companies, and verified emails in &quot;Upload &amp; Draft&quot;.
              </p>
            </div>

            <div className="p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl space-y-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#2563EB] bg-[#EFF6FF] px-2 py-0.5 rounded border border-[#BFDBFE]">
                Step 2
              </span>
              <h4 className="font-bold text-[#0F172A] text-sm">Pair Outreach Template</h4>
              <p className="text-[12px] text-[#64748B]">
                Select any of the 7 responsive templates tailored to that specific industry or audience segment.
              </p>
            </div>

            <div className="p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl space-y-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#2563EB] bg-[#EFF6FF] px-2 py-0.5 rounded border border-[#BFDBFE]">
                Step 3
              </span>
              <h4 className="font-bold text-[#0F172A] text-sm">Review &amp; 1-Click Send</h4>
              <p className="text-[12px] text-[#64748B]">
                Inspect rendered drafts in &quot;Email Review&quot; and dispatch safely via Microsoft Graph API.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
