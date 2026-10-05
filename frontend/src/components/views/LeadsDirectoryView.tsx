"use client";

import React, { useState, useEffect } from "react";
import HeaderBanner from "@/components/layout/HeaderBanner";
import { api, CampaignLogItem } from "@/lib/api";
import { Search, RefreshCw, Filter, Mail, CheckCircle2 } from "lucide-react";

export default function LeadsDirectoryView() {
  const [logs, setLogs] = useState<CampaignLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [campaignFilter, setCampaignFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const res = await api.getLogs({ limit: 2000 });
      setLogs(res.logs || []);
    } catch (e: any) {
      console.error("Failed to load leads directory", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const campaigns = ["All", ...Array.from(new Set(logs.map((l) => l.campaign).filter(Boolean)))];
  const statuses = ["All", ...Array.from(new Set(logs.map((l) => l.status).filter(Boolean)))];

  const filteredLogs = logs.filter((l) => {
    if (campaignFilter !== "All" && l.campaign !== campaignFilter) return false;
    if (statusFilter !== "All" && l.status !== statusFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const match =
        l.email?.toLowerCase().includes(q) ||
        l.name?.toLowerCase().includes(q) ||
        l.company?.toLowerCase().includes(q) ||
        l.lead_id?.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <HeaderBanner
        title="Campaign Leads Directory"
        subtitle="Browse, filter, and inspect leads recorded in your database."
        badgeText="Master Directory"
        badgeType="live"
      />

      {/* Filter Ribbon */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.03)] grid grid-cols-1 md:grid-cols-3 gap-3">
        <div>
          <label className="block text-[11px] font-semibold text-[#64748B] uppercase mb-1">
            Filter by Campaign
          </label>
          <select
            value={campaignFilter}
            onChange={(e) => setCampaignFilter(e.target.value)}
            className="w-full text-[13px] bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg px-3 py-2 text-[#0F172A] font-medium focus:outline-none focus:border-[#2563EB]"
          >
            {campaigns.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-[#64748B] uppercase mb-1">
            Filter by Status
          </label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full text-[13px] bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg px-3 py-2 text-[#0F172A] font-medium focus:outline-none focus:border-[#2563EB]"
          >
            {statuses.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-[#64748B] uppercase mb-1">
            Search by Name, Email or Company
          </label>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-3 text-[#94A3B8]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Type to search..."
              className="w-full pl-9 pr-3 py-2 text-[13px] bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
            />
          </div>
        </div>
      </div>

      <div className="text-[13px] text-[#64748B] font-medium">
        Displaying <strong className="text-[#0F172A]">{filteredLogs.length}</strong> matching lead(s)
      </div>

      {/* Leads Table */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.03)]">
        {loading ? (
          <div className="flex flex-col items-center justify-center p-16 space-y-2">
            <RefreshCw className="w-6 h-6 animate-spin text-[#2563EB]" />
            <span className="text-[13px] text-[#64748B]">Loading leads directory...</span>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="text-center p-12 text-[#64748B] text-[13.5px]">
            No leads found matching current filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[12.5px]">
              <thead className="bg-[#F8FAFC] text-[#475569] border-b border-[#E2E8F0] text-[11px] uppercase tracking-wider font-semibold">
                <tr>
                  <th className="py-3 px-3.5">Lead ID</th>
                  <th className="py-3 px-3.5">Email Address</th>
                  <th className="py-3 px-3.5">Full Name</th>
                  <th className="py-3 px-3.5">Company</th>
                  <th className="py-3 px-3.5">Outreach Status</th>
                  <th className="py-3 px-3.5">Email Subject</th>
                  <th className="py-3 px-3.5">Booking Status</th>
                  <th className="py-3 px-3.5">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F1F5F9]">
                {filteredLogs.slice(0, 100).map((l) => (
                  <tr key={l.id} className="hover:bg-[#F8FAFC] transition-colors">
                    <td className="py-2.5 px-3.5 font-mono text-[11px] text-[#64748B]">{l.lead_id || "—"}</td>
                    <td className="py-2.5 px-3.5 font-semibold text-[#0F172A]">{l.email}</td>
                    <td className="py-2.5 px-3.5 text-[#334155]">{l.name || "—"}</td>
                    <td className="py-2.5 px-3.5 text-[#334155]">{l.company || "—"}</td>
                    <td className="py-2.5 px-3.5">
                      <span className="badge badge-sent text-[10.5px]">
                        {l.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3.5 max-w-xs truncate text-[#64748B]">{l.subject || "—"}</td>
                    <td className="py-2.5 px-3.5">
                      {l.booking_status ? (
                        <span className="badge badge-scheduled text-[10.5px]">{l.booking_status}</span>
                      ) : (
                        <span className="text-[#94A3B8]">—</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3.5 text-[#64748B] font-mono text-[11px]">
                      {l.created_at ? new Date(l.created_at).toLocaleDateString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
