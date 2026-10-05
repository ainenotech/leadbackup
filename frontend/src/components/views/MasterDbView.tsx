"use client";

import React, { useState, useEffect, useMemo } from "react";
import HeaderBanner from "@/components/layout/HeaderBanner";
import { api, MasterDbLead, TemplateItem } from "@/lib/api";
import {
  Search,
  Download,
  RefreshCw,
  Flame,
  Zap,
  Snowflake,
  ExternalLink,
  X,
  Mail,
  Building,
  User,
  Briefcase,
  Calendar,
  CheckCircle2,
  Clock,
  Eye,
  MousePointer,
  MessageSquare,
} from "lucide-react";

export default function MasterDbView() {
  const [leads, setLeads] = useState<MasterDbLead[]>([]);
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("__all__");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [minScore, setMinScore] = useState<number>(0);
  const [activeTab, setActiveTab] = useState<"HOT" | "WARM" | "COLD" | "ALL">("HOT");
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedLead, setSelectedLead] = useState<MasterDbLead | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [dbRes, tplRes] = await Promise.all([
        api.getMasterDb(),
        api.getTemplates(),
      ]);
      setLeads(dbRes.leads || []);
      setTemplates(tplRes.templates || []);
    } catch (e: any) {
      console.error("Failed to load master db", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Calculate dynamic counts per template across all leads in DB
  const templateCounts = useMemo(() => {
    const countsMap: Record<string, number> = { __all__: leads.length };
    templates.forEach((tpl) => {
      const tId = String(tpl.id);
      const tName = tpl.name || tId;
      const numMatch = tName.match(/Template\s*(\d+)/i) || tId.match(/(\d+)/);
      const tNum = numMatch ? numMatch[1] : "";

      const matchCount = leads.filter((l) => {
        if (l.template_id === tId) return true;
        if (l.template_name && l.template_name === tName) return true;
        if (l.template_name && l.template_name.toLowerCase().includes(tId.toLowerCase())) return true;
        if (tNum && l.template_name && l.template_name.toLowerCase().includes(`template ${tNum}`)) return true;
        return false;
      }).length;

      countsMap[tId] = matchCount;
    });
    return countsMap;
  }, [leads, templates]);

  // Filter leads based on template, search query, and min score
  const filteredLeads = useMemo(() => {
    return leads.filter((lead) => {
      // 1. Template filter
      if (selectedTemplate !== "__all__") {
        const tObj = templates.find((t) => String(t.id) === selectedTemplate);
        const tName = tObj?.name || selectedTemplate;
        const numMatch = selectedTemplate.match(/(\d+)/) || tName.match(/Template\s*(\d+)/i);
        const tNum = numMatch ? numMatch[1] : "";

        const matchTpl =
          lead.template_id === selectedTemplate ||
          lead.template_name === tName ||
          (lead.template_name && lead.template_name.toLowerCase().includes(selectedTemplate.toLowerCase())) ||
          (tNum && lead.template_name && lead.template_name.toLowerCase().includes(`template ${tNum}`));
        if (!matchTpl) return false;
      }

      // 2. Min Score filter
      if (minScore > 0 && (lead.score || 0) < minScore) {
        return false;
      }

      // 3. Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const match =
          (lead.name && lead.name.toLowerCase().includes(q)) ||
          (lead.company && lead.company.toLowerCase().includes(q)) ||
          (lead.email && lead.email.toLowerCase().includes(q)) ||
          (lead.job_title && lead.job_title.toLowerCase().includes(q)) ||
          (lead.activity_summary && lead.activity_summary.toLowerCase().includes(q)) ||
          (lead.reply_body && lead.reply_body.toLowerCase().includes(q));
        if (!match) return false;
      }

      return true;
    });
  }, [leads, selectedTemplate, minScore, searchQuery, templates]);

  // Segment leads into cohorts
  const hotLeads = useMemo(() => filteredLeads.filter((l) => l.tier === "HOT"), [filteredLeads]);
  const warmLeads = useMemo(() => filteredLeads.filter((l) => l.tier === "WARM"), [filteredLeads]);
  const coldLeads = useMemo(() => filteredLeads.filter((l) => l.tier === "COLD"), [filteredLeads]);

  // Aggregate metrics
  const totalLeads = filteredLeads.length;
  const hotCount = hotLeads.length;
  const warmCount = warmLeads.length;
  const coldCount = coldLeads.length;
  const hotPct = totalLeads ? (hotCount / totalLeads) * 100 : 0;
  const warmPct = totalLeads ? (warmCount / totalLeads) * 100 : 0;
  const coldPct = totalLeads ? (coldCount / totalLeads) * 100 : 0;

  const openedCount = useMemo(() => {
    return filteredLeads.reduce((acc, l) => acc + (l.open_count || (l.opened ? 1 : 0)), 0);
  }, [filteredLeads]);

  const clickedCount = useMemo(() => {
    return filteredLeads.reduce((acc, l) => acc + (l.click_count || (l.clicked_link ? 1 : 0)), 0);
  }, [filteredLeads]);

  const repliedCount = useMemo(() => {
    return filteredLeads.filter(
      (l) => l.reply_body && l.reply_body.trim() && !["none", "nan", "—", "-"].includes(l.reply_body.toLowerCase())
    ).length;
  }, [filteredLeads]);

  // Get active leads list based on tab
  const displayedLeads = useMemo(() => {
    switch (activeTab) {
      case "HOT":
        return [...hotLeads].sort((a, b) => (b.score || 0) - (a.score || 0) || (b.open_count || 0) - (a.open_count || 0));
      case "WARM":
        return [...warmLeads].sort((a, b) => (b.score || 0) - (a.score || 0) || (b.open_count || 0) - (a.open_count || 0));
      case "COLD":
        return coldLeads;
      case "ALL":
      default:
        return filteredLeads;
    }
  }, [activeTab, hotLeads, warmLeads, coldLeads, filteredLeads]);

  // Export CSV generator matching Streamlit column structure
  const exportCSV = (cohortName: string, dataToExport: MasterDbLead[]) => {
    const headers = [
      "Tier",
      "Lead Score",
      "Company",
      "Contact Name",
      "Role / Title",
      "Email Address",
      "Template",
      "Opens",
      "Clicks",
      "Engagement Signals",
      "Customer Reply Preview",
      "Status",
      "Last Sent",
    ];

    const rows = dataToExport.map((l) => [
      `"${l.tier_display || l.tier}"`,
      l.score || 0,
      `"${(l.company || "Unknown Company").replace(/"/g, '""')}"`,
      `"${(l.name || "Lead Contact").replace(/"/g, '""')}"`,
      `"${(l.job_title || "—").replace(/"/g, '""')}"`,
      `"${l.email}"`,
      `"${(l.template_name || "—").replace(/"/g, '""')}"`,
      l.open_count || (l.opened ? 1 : 0),
      l.click_count || (l.clicked_link ? 1 : 0),
      `"${(l.activity_summary || "—").replace(/"/g, '""')}"`,
      `"${(l.reply_body ? l.reply_body.slice(0, 100) : "—").replace(/"/g, '""')}"`,
      `"${(l.status || "Sent").toUpperCase()}"`,
      `"${l.email_sent_at ? l.email_sent_at.slice(0, 16).replace("T", " ") : "—"}"`,
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute(
      "download",
      `${cohortName.toLowerCase().replace(/\s+/g, "_")}_leads_${new Date().toISOString().slice(0, 10)}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getScoreColor = (score: number) => {
    if (score >= 70) return "bg-[#EF4444]";
    if (score >= 25) return "bg-[#D97706]";
    return "bg-[#3B82F6]";
  };

  return (
    <div className="space-y-6">
      {/* ── Top Header Banner ── */}
      <HeaderBanner
        title="🗄️ Master DB"
        subtitle="Live database segmentation with verified Hot, Warm, and Cold lead telemetry."
        badgeText="Real Database Verified"
        badgeType="live"
        action={
          <button
            onClick={() => exportCSV("all_filtered", filteredLeads)}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-[12.5px] font-semibold bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-lg shadow-sm transition-colors"
          >
            <Download className="w-4 h-4" />
            <span>Export Filtered CSV ({filteredLeads.length})</span>
          </button>
        }
      />

      {/* ── Template Filter, Search & Score Slider Ribbon ── */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end">
          {/* Template Filter Select (5 cols) */}
          <div className="md:col-span-5 space-y-1">
            <label className="block text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
              Filter Outreach Template:
            </label>
            <select
              value={selectedTemplate}
              onChange={(e) => setSelectedTemplate(e.target.value)}
              className="w-full text-[13px] bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg px-3 py-2 text-[#0F172A] font-semibold focus:outline-none focus:border-[#2563EB]"
            >
              <option value="__all__">🌐 All Templates ({templateCounts.__all__ || leads.length} leads)</option>
              {templates.map((t) => {
                const count = templateCounts[String(t.id)] || 0;
                return (
                  <option key={t.id} value={String(t.id)}>
                    {t.name} ({count} leads)
                  </option>
                );
              })}
            </select>
          </div>

          {/* Search Box (4 cols) */}
          <div className="md:col-span-4 space-y-1">
            <label className="block text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
              Search Real Database:
            </label>
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-[#94A3B8]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search company, contact name, or email..."
                className="w-full pl-9 pr-3 py-2 text-[13px] bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
              />
            </div>
          </div>

          {/* Min Score Slider (3 cols) */}
          <div className="md:col-span-3 space-y-1">
            <div className="flex justify-between items-center text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
              <span>Min Lead Score:</span>
              <span className="text-[#2563EB] font-mono text-[12px] bg-[#EFF6FF] px-2 py-0.5 rounded border border-[#BFDBFE]">
                {minScore}/100
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-full h-2 bg-[#E2E8F0] rounded-lg appearance-none cursor-pointer accent-[#2563EB]"
            />
          </div>
        </div>
      </div>

      {/* ── 5 Sleek Executive KPI Cards (Exact Streamlit Match) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {/* Total Leads */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-3.5 relative overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.03)]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-[#2563EB]"></div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-[12px] font-semibold text-[#64748B]">Total Leads</span>
            <span className="text-base">👥</span>
          </div>
          <div className="text-2xl font-bold text-[#0F172A] tracking-tight">{totalLeads}</div>
          <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-[#64748B]">
            <span className="px-1.5 py-0.2 rounded bg-[#EFF6FF] text-[#2563EB] font-bold">Active</span>
            <span className="truncate">In current view</span>
          </div>
        </div>

        {/* Hot Leads */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-3.5 relative overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.03)]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#EF4444] to-[#F87171]"></div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-[12px] font-bold text-[#EF4444]">🔥 Hot Leads</span>
            <span className="text-base">🔥</span>
          </div>
          <div className="text-2xl font-bold text-[#EF4444] tracking-tight">{hotCount}</div>
          <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-[#64748B]">
            <span className="px-1.5 py-0.2 rounded bg-[#FEF2F2] text-[#EF4444] font-bold border border-[#FECACA]">
              {hotPct.toFixed(1)}%
            </span>
            <span className="truncate">High intent / replies</span>
          </div>
        </div>

        {/* Warm Leads */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-3.5 relative overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.03)]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-[#D97706]"></div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-[12px] font-bold text-[#D97706]">⚡ Warm Leads</span>
            <span className="text-base">⚡</span>
          </div>
          <div className="text-2xl font-bold text-[#D97706] tracking-tight">{warmCount}</div>
          <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-[#64748B]">
            <span className="px-1.5 py-0.2 rounded bg-[#FFFBEB] text-[#D97706] font-bold border border-[#FDE68A]">
              {warmPct.toFixed(1)}%
            </span>
            <span className="truncate">Opened / Engaged</span>
          </div>
        </div>

        {/* Cold Leads */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-3.5 relative overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.03)]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-[#06B6D4]"></div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-[12px] font-semibold text-[#0E7490]">❄️ Cold Leads</span>
            <span className="text-base">❄️</span>
          </div>
          <div className="text-2xl font-bold text-[#0E7490] tracking-tight">{coldCount}</div>
          <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-[#64748B]">
            <span className="px-1.5 py-0.2 rounded bg-[#ECFEFF] text-[#0891B2] font-bold border border-[#A5F3FC]">
              {coldPct.toFixed(1)}%
            </span>
            <span className="truncate">Unopened</span>
          </div>
        </div>

        {/* Responses & Telemetry */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-3.5 relative overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.03)]">
          <div className="absolute top-0 left-0 right-0 h-1 bg-[#0D9488]"></div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-[12px] font-bold text-[#0D9488]">💬 Responses</span>
            <span className="text-base">💬</span>
          </div>
          <div className="text-2xl font-bold text-[#0D9488] tracking-tight">{repliedCount}</div>
          <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-[#64748B]">
            <span className="px-1.5 py-0.2 rounded bg-[#F0FDFA] text-[#0D9488] font-bold border border-[#99F6E4]">
              {clickedCount} Clicks
            </span>
            <span className="truncate">{openedCount} Opens</span>
          </div>
        </div>
      </div>

      {/* ── 4 Segment Tabs Matching Streamlit Exactly ── */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 border-b border-[#E2E8F0] pb-2 flex-wrap">
          <button
            onClick={() => setActiveTab("HOT")}
            className={`px-4 py-2 rounded-lg text-[13px] font-bold transition-all flex items-center gap-2 ${
              activeTab === "HOT"
                ? "bg-[#EF4444] text-white shadow-xs"
                : "bg-white text-[#475569] border border-[#E2E8F0] hover:bg-[#FEF2F2] hover:text-[#EF4444]"
            }`}
          >
            <span>🔥 Hot Leads ({hotCount})</span>
          </button>

          <button
            onClick={() => setActiveTab("WARM")}
            className={`px-4 py-2 rounded-lg text-[13px] font-bold transition-all flex items-center gap-2 ${
              activeTab === "WARM"
                ? "bg-[#D97706] text-white shadow-xs"
                : "bg-white text-[#475569] border border-[#E2E8F0] hover:bg-[#FFFBEB] hover:text-[#D97706]"
            }`}
          >
            <span>⚡ Warm Leads ({warmCount})</span>
          </button>

          <button
            onClick={() => setActiveTab("COLD")}
            className={`px-4 py-2 rounded-lg text-[13px] font-bold transition-all flex items-center gap-2 ${
              activeTab === "COLD"
                ? "bg-[#0891B2] text-white shadow-xs"
                : "bg-white text-[#475569] border border-[#E2E8F0] hover:bg-[#ECFEFF] hover:text-[#0891B2]"
            }`}
          >
            <span>❄️ Cold Leads ({coldCount})</span>
          </button>

          <button
            onClick={() => setActiveTab("ALL")}
            className={`px-4 py-2 rounded-lg text-[13px] font-bold transition-all flex items-center gap-2 ${
              activeTab === "ALL"
                ? "bg-[#0F172A] text-white shadow-xs"
                : "bg-white text-[#475569] border border-[#E2E8F0] hover:bg-[#F8FAFC]"
            }`}
          >
            <span>📋 All Leads ({totalLeads})</span>
          </button>
        </div>

        {/* Tab Caption & Cohort CSV Export Button */}
        <div className="flex justify-between items-center flex-wrap gap-2 px-1">
          <div className="text-[13px] text-[#475569]">
            {activeTab === "HOT" && (
              <span>
                Showing <strong>{hotCount}</strong> high-intent leads who replied to emails or clicked engagement links:
              </span>
            )}
            {activeTab === "WARM" && (
              <span>
                Showing <strong>{warmCount}</strong> active consideration leads who opened emails or clicked once:
              </span>
            )}
            {activeTab === "COLD" && (
              <span>
                Showing <strong>{coldCount}</strong> leads awaiting first open or response:
              </span>
            )}
            {activeTab === "ALL" && (
              <span>
                Showing all <strong>{totalLeads}</strong> real database records:
              </span>
            )}
          </div>

          <button
            onClick={() => {
              if (activeTab === "HOT") exportCSV("hot", hotLeads);
              else if (activeTab === "WARM") exportCSV("warm", warmLeads);
              else if (activeTab === "COLD") exportCSV("cold", coldLeads);
              else exportCSV("all", filteredLeads);
            }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#1E293B] border border-[#CBD5E1] rounded-lg transition-colors shadow-2xs"
          >
            <Download className="w-3.5 h-3.5 text-[#2563EB]" />
            <span>
              ⬇️ Export {activeTab === "ALL" ? "All" : activeTab === "HOT" ? "Hot" : activeTab === "WARM" ? "Warm" : "Cold"} Leads (CSV)
            </span>
          </button>
        </div>

        {/* ── Main Data Table (100% Streamlit Parity) ── */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.03)]">
          {loading ? (
            <div className="flex flex-col items-center justify-center p-16 space-y-2">
              <RefreshCw className="w-6 h-6 animate-spin text-[#2563EB]" />
              <span className="text-[13px] text-[#64748B]">Querying Master Database...</span>
            </div>
          ) : displayedLeads.length === 0 ? (
            <div className="text-center p-12 text-[#64748B] text-[13.5px] space-y-1">
              <div className="text-2xl mb-1">🔍</div>
              <p className="font-semibold text-[#0F172A]">No leads found under current filters.</p>
              <p className="text-[12px]">Try clearing your search query or selecting &quot;All Templates&quot;.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[12.5px] border-collapse">
                <thead className="bg-[#F8FAFC] text-[#475569] border-b border-[#E2E8F0] text-[11px] uppercase tracking-wider font-bold">
                  <tr>
                    <th className="py-3 px-3.5 whitespace-nowrap">Tier</th>
                    <th className="py-3 px-3.5 whitespace-nowrap">Lead Score</th>
                    <th className="py-3 px-3.5 whitespace-nowrap">Company</th>
                    <th className="py-3 px-3.5 whitespace-nowrap">Contact Name</th>
                    <th className="py-3 px-3.5 whitespace-nowrap">Role / Title</th>
                    <th className="py-3 px-3.5 whitespace-nowrap">Email Address</th>
                    <th className="py-3 px-3.5 whitespace-nowrap">Template</th>
                    <th className="py-3 px-3.5 text-center whitespace-nowrap">Opens</th>
                    <th className="py-3 px-3.5 text-center whitespace-nowrap">Clicks</th>
                    <th className="py-3 px-3.5 whitespace-nowrap">Engagement Signals</th>
                    <th className="py-3 px-3.5 whitespace-nowrap">Customer Reply Preview</th>
                    <th className="py-3 px-3.5 whitespace-nowrap">Status</th>
                    <th className="py-3 px-3.5 whitespace-nowrap">Last Sent</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F1F5F9]">
                  {displayedLeads.slice(0, 150).map((lead) => {
                    const score = lead.score || 0;
                    const opens = lead.open_count || (lead.opened ? 1 : 0);
                    const clicks = lead.click_count || (lead.clicked_link ? 1 : 0);
                    const hasReply = Boolean(
                      lead.reply_body &&
                        lead.reply_body.trim() &&
                        !["none", "nan", "—", "-"].includes(lead.reply_body.toLowerCase())
                    );
                    const replyPreview = hasReply
                      ? lead.reply_body.length > 85
                        ? lead.reply_body.slice(0, 85) + "..."
                        : lead.reply_body
                      : "—";

                    let tierBadge = "badge-cold";
                    if (lead.tier === "HOT") tierBadge = "badge-hot";
                    else if (lead.tier === "WARM") tierBadge = "badge-warm";

                    return (
                      <tr
                        key={lead.id}
                        onClick={() => setSelectedLead(lead)}
                        className="hover:bg-[#F8FAFC] transition-colors cursor-pointer group"
                      >
                        {/* 1. Tier */}
                        <td className="py-3 px-3.5 whitespace-nowrap">
                          <span className={`badge ${tierBadge} text-[11px]`}>
                            {lead.tier_display || (lead.tier === "HOT" ? "🔥 Hot" : lead.tier === "WARM" ? "⚡ Warm" : "❄️ Cold")}
                          </span>
                        </td>

                        {/* 2. Score with Progress Bar */}
                        <td className="py-3 px-3.5 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <div className="w-14 h-2 bg-[#E2E8F0] rounded-full overflow-hidden">
                              <div
                                className={`h-full ${getScoreColor(score)} rounded-full`}
                                style={{ width: `${Math.min(100, Math.max(5, score))}%` }}
                              />
                            </div>
                            <span className="font-mono font-bold text-[#0F172A] text-[11.5px]">{score}</span>
                          </div>
                        </td>

                        {/* 3. Company */}
                        <td className="py-3 px-3.5 whitespace-nowrap font-semibold text-[#0F172A]">
                          {lead.company || "Unknown Company"}
                        </td>

                        {/* 4. Contact Name */}
                        <td className="py-3 px-3.5 whitespace-nowrap text-[#334155] font-medium">
                          {lead.name || "Lead Contact"}
                        </td>

                        {/* 5. Role / Title */}
                        <td className="py-3 px-3.5 whitespace-nowrap text-[#64748B]">
                          {lead.job_title && lead.job_title !== "—" ? lead.job_title : "—"}
                        </td>

                        {/* 6. Email */}
                        <td className="py-3 px-3.5 whitespace-nowrap font-mono text-[11px] text-[#2563EB]">
                          {lead.email}
                        </td>

                        {/* 7. Template */}
                        <td className="py-3 px-3.5 whitespace-nowrap text-[#475569]">
                          {lead.template_name
                            ? lead.template_name.split(":")[0]
                            : lead.template_id || "Template 1"}
                        </td>

                        {/* 8. Opens */}
                        <td className="py-3 px-3.5 text-center whitespace-nowrap font-semibold text-[#0F172A]">
                          {opens > 0 ? (
                            <span className="inline-flex items-center gap-1 text-[#2563EB]">
                              <Eye className="w-3 h-3" />
                              <span>{opens}</span>
                            </span>
                          ) : (
                            <span className="text-[#94A3B8]">0</span>
                          )}
                        </td>

                        {/* 9. Clicks */}
                        <td className="py-3 px-3.5 text-center whitespace-nowrap font-semibold text-[#0F172A]">
                          {clicks > 0 ? (
                            <span className="inline-flex items-center gap-1 text-[#0D9488]">
                              <MousePointer className="w-3 h-3" />
                              <span>{clicks}</span>
                            </span>
                          ) : (
                            <span className="text-[#94A3B8]">0</span>
                          )}
                        </td>

                        {/* 10. Engagement Signals */}
                        <td className="py-3 px-3.5 whitespace-nowrap">
                          <span className="text-[11.5px] font-medium text-[#475569]">
                            {lead.activity_summary || "Delivered • Unopened"}
                          </span>
                        </td>

                        {/* 11. Customer Reply Preview */}
                        <td className="py-3 px-3.5 max-w-xs truncate text-[11.5px] text-[#334155]">
                          {hasReply ? (
                            <span className="text-[#065F46] font-medium bg-[#ECFDF5] px-2 py-0.5 rounded border border-[#A7F3D0]">
                              &ldquo;{replyPreview}&rdquo;
                            </span>
                          ) : (
                            <span className="text-[#94A3B8]">—</span>
                          )}
                        </td>

                        {/* 12. Status */}
                        <td className="py-3 px-3.5 whitespace-nowrap">
                          <span
                            className={`badge ${
                              lead.status === "replied"
                                ? "badge-sent"
                                : lead.status === "scheduled" || lead.status === "booked"
                                ? "badge-pending"
                                : "badge-neutral"
                            } text-[10.5px] uppercase`}
                          >
                            {lead.status || "Sent"}
                          </span>
                        </td>

                        {/* 13. Last Sent */}
                        <td className="py-3 px-3.5 whitespace-nowrap text-[#64748B] font-mono text-[11px]">
                          {lead.email_sent_at
                            ? lead.email_sent_at.slice(0, 16).replace("T", " ")
                            : lead.created_at
                            ? lead.created_at.slice(0, 16).replace("T", " ")
                            : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* ── Comprehensive Lead Details Modal ── */}
      {selectedLead && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full border border-[#CBD5E1] shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="bg-[#F8FAFC] px-6 py-4 border-b border-[#E2E8F0] flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span
                  className={`badge ${
                    selectedLead.tier === "HOT"
                      ? "badge-hot"
                      : selectedLead.tier === "WARM"
                      ? "badge-warm"
                      : "badge-cold"
                  } text-[11px]`}
                >
                  {selectedLead.tier_display || selectedLead.tier}
                </span>
                <h3 className="font-bold text-[#0F172A] text-base">
                  {selectedLead.name || "Lead Profile"} &bull; {selectedLead.company || "Enterprise"}
                </h3>
              </div>
              <button
                onClick={() => setSelectedLead(null)}
                className="w-7 h-7 rounded-lg text-[#64748B] hover:text-[#0F172A] hover:bg-[#E2E8F0] flex items-center justify-center transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto text-[13px]">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <span className="text-[11px] uppercase font-bold text-[#64748B]">Email Address</span>
                  <div className="font-mono text-[#0F172A] font-semibold">{selectedLead.email}</div>
                </div>
                <div className="space-y-1">
                  <span className="text-[11px] uppercase font-bold text-[#64748B]">Role / Title</span>
                  <div className="text-[#0F172A] font-medium">{selectedLead.job_title || "Executive Contact"}</div>
                </div>
                <div className="space-y-1">
                  <span className="text-[11px] uppercase font-bold text-[#64748B]">Lead Score</span>
                  <div className="font-bold text-[#2563EB] font-mono text-[14px]">
                    {selectedLead.score}/100
                  </div>
                </div>
                <div className="space-y-1">
                  <span className="text-[11px] uppercase font-bold text-[#64748B]">Template Used</span>
                  <div className="text-[#0F172A]">{selectedLead.template_name || selectedLead.template_id || "Template 1"}</div>
                </div>
              </div>

              {/* Engagement Signals */}
              <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3.5 space-y-1.5">
                <span className="text-[11px] uppercase font-bold text-[#64748B]">Real-Time Telemetry Signals</span>
                <p className="text-[#334155] font-semibold">{selectedLead.activity_summary || "Delivered"}</p>
                <div className="flex gap-4 text-[12px] text-[#64748B] pt-1">
                  <span>Opens: <strong className="text-[#0F172A]">{selectedLead.open_count || (selectedLead.opened ? 1 : 0)}</strong></span>
                  <span>Clicks: <strong className="text-[#0F172A]">{selectedLead.click_count || (selectedLead.clicked_link ? 1 : 0)}</strong></span>
                  <span>Status: <strong className="text-[#0F172A] uppercase">{selectedLead.status}</strong></span>
                </div>
              </div>

              {/* Customer Reply Section */}
              {selectedLead.reply_body && (
                <div className="bg-[#F0FDF4] border border-[#BBF7D0] rounded-xl p-4 space-y-1.5">
                  <div className="flex justify-between items-center">
                    <span className="text-[11.5px] font-bold text-[#166534] uppercase flex items-center gap-1.5">
                      <MessageSquare className="w-3.5 h-3.5" />
                      <span>Inbound Customer Reply</span>
                    </span>
                    {selectedLead.reply_intent && (
                      <span className="badge badge-sent text-[10.5px]">
                        Intent: {selectedLead.reply_intent}
                      </span>
                    )}
                  </div>
                  <p className="text-[#14532D] text-[13.5px] leading-relaxed whitespace-pre-wrap italic">
                    &ldquo;{selectedLead.reply_body}&rdquo;
                  </p>
                  {selectedLead.reply_received_at && (
                    <div className="text-[11px] text-[#15803D] pt-1">
                      Received at: {selectedLead.reply_received_at.slice(0, 16).replace("T", " ")}
                    </div>
                  )}
                </div>
              )}

              {/* Booking & Consultation Details */}
              {(selectedLead.confirmed_slot || selectedLead.meet_link || selectedLead.booking_status) && (
                <div className="bg-[#EFF6FF] border border-[#BFDBFE] rounded-xl p-4 space-y-1.5">
                  <span className="text-[11.5px] font-bold text-[#1D4ED8] uppercase flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Meeting &amp; Consultation Booking</span>
                  </span>
                  <div className="text-[#1E3A8A] text-[13px] space-y-1">
                    {selectedLead.confirmed_slot && (
                      <div><strong>Confirmed Slot:</strong> {selectedLead.confirmed_slot}</div>
                    )}
                    {selectedLead.meet_link && (
                      <div>
                        <strong>Meeting Link:</strong>{" "}
                        <a
                          href={selectedLead.meet_link}
                          target="_blank"
                          rel="noreferrer"
                          className="underline text-[#2563EB]"
                        >
                          Join Consultation ↗
                        </a>
                      </div>
                    )}
                    {selectedLead.booking_status && (
                      <div><strong>Booking Status:</strong> {selectedLead.booking_status}</div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="bg-[#F8FAFC] px-6 py-3 border-t border-[#E2E8F0] flex justify-end">
              <button
                onClick={() => setSelectedLead(null)}
                className="px-4 py-2 bg-[#0F172A] hover:bg-[#1E293B] text-white font-semibold text-[12px] rounded-lg transition-colors"
              >
                Close Profile
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
