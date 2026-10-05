"use client";

import React from "react";
import HeaderBanner from "@/components/layout/HeaderBanner";
import ActivityStream from "@/components/layout/ActivityStream";
import { OverviewStats, ActivityFeedEvent, CampaignLogItem } from "@/lib/api";
import { Users, FileEdit, Send, MessageSquare, ClipboardCheck, CalendarCheck, ArrowRight } from "lucide-react";
import { PageId } from "@/components/layout/Sidebar";

interface PipelineOverviewProps {
  stats: OverviewStats;
  events: ActivityFeedEvent[];
  recentLogs: CampaignLogItem[];
  syncChoiceText: string;
  onNavigate: (page: PageId) => void;
}

export default function PipelineOverview({
  stats,
  events,
  recentLogs,
  syncChoiceText,
  onNavigate,
}: PipelineOverviewProps) {
  return (
    <div className="space-y-6">
      <HeaderBanner
        title="Executive Pipeline Overview"
        subtitle="Real-time visibility into lead outreach, email performance, customer replies, and consultation bookings."
        badgeText="Live Campaign"
        badgeType="live"
      />

      {/* 6 Custom Rich KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {/* Total Leads */}
        <div className="kpi-card">
          <div className="kpi-top-bar kpi-bar-blue"></div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[12px] font-semibold text-[#64748B]">Total Leads</span>
            <div className="w-8 h-8 rounded-lg bg-[#EFF6FF] text-[#2563EB] flex items-center justify-center text-sm">
              👥
            </div>
          </div>
          <div className="text-2xl font-bold text-[#0F172A] tracking-tight">
            {(stats?.total_leads ?? 0).toLocaleString()}
          </div>
          <div className="mt-2 text-[11px] text-[#64748B] flex items-center gap-1.5">
            <span className="px-1.5 py-0.5 rounded bg-[#EFF6FF] text-[#2563EB] font-bold">100% active</span>
            <span className="truncate">in campaign</span>
          </div>
        </div>

        {/* Drafts In Review */}
        <div className="kpi-card cursor-pointer" onClick={() => onNavigate("email")}>
          <div className="kpi-top-bar kpi-bar-amber"></div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[12px] font-semibold text-[#64748B]">Drafts (Review)</span>
            <div className="w-8 h-8 rounded-lg bg-[#FFFBEB] text-[#D97706] flex items-center justify-center text-sm">
              ✍️
            </div>
          </div>
          <div className="text-2xl font-bold text-[#0F172A] tracking-tight">
            {(stats?.drafted_leads ?? 0).toLocaleString()}
          </div>
          <div className="mt-2 text-[11px] text-[#64748B] flex items-center gap-1.5">
            <span className="px-1.5 py-0.5 rounded bg-[#FFFBEB] text-[#D97706] font-bold">
              {stats?.draft_pct ?? 0}% queued
            </span>
            <span className="truncate">approval</span>
          </div>
        </div>

        {/* Outreach Sent */}
        <div className="kpi-card">
          <div className="kpi-top-bar kpi-bar-teal"></div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[12px] font-semibold text-[#64748B]">Outreach Sent</span>
            <div className="w-8 h-8 rounded-lg bg-[#F0FDFA] text-[#0D9488] flex items-center justify-center text-sm">
              📤
            </div>
          </div>
          <div className="text-2xl font-bold text-[#0F172A] tracking-tight">
            {(stats?.sent_leads ?? 0).toLocaleString()}
          </div>
          <div className="mt-2 text-[11px] text-[#64748B] flex items-center gap-1.5">
            <span className="px-1.5 py-0.5 rounded bg-[#F0FDFA] text-[#0D9488] font-bold">
              {stats?.sent_pct ?? 0}% sent
            </span>
            <span className="truncate">delivered</span>
          </div>
        </div>

        {/* Customer Replies */}
        <div className="kpi-card cursor-pointer" onClick={() => onNavigate("replies")}>
          <div className="kpi-top-bar kpi-bar-purple"></div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[12px] font-semibold text-[#64748B]">Replies</span>
            <div className="w-8 h-8 rounded-lg bg-[#F5F3FF] text-[#7C3AED] flex items-center justify-center text-sm">
              💬
            </div>
          </div>
          <div className="text-2xl font-bold text-[#0F172A] tracking-tight">
            {(stats?.replied_leads ?? 0).toLocaleString()}
          </div>
          <div className="mt-2 text-[11px] text-[#64748B] flex items-center gap-1.5">
            <span className="px-1.5 py-0.5 rounded bg-[#F5F3FF] text-[#7C3AED] font-bold">
              {stats?.reply_pct ?? 0}% reply
            </span>
            <span className="truncate">high intent</span>
          </div>
        </div>

        {/* Forms Completed */}
        <div className="kpi-card cursor-pointer" onClick={() => onNavigate("replies")}>
          <div className="kpi-top-bar kpi-bar-rose"></div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[12px] font-semibold text-[#64748B]">Forms Filled</span>
            <div className="w-8 h-8 rounded-lg bg-[#FFF1F2] text-[#E11D48] flex items-center justify-center text-sm">
              📋
            </div>
          </div>
          <div className="text-2xl font-bold text-[#0F172A] tracking-tight">
            {(stats?.forms_filled ?? 0).toLocaleString()}
          </div>
          <div className="mt-2 text-[11px] text-[#64748B] flex items-center gap-1.5">
            <span className="px-1.5 py-0.5 rounded bg-[#FFF1F2] text-[#E11D48] font-bold">
              {stats?.form_pct ?? 0}% form
            </span>
            <span className="truncate">consultation</span>
          </div>
        </div>

        {/* Bookings Confirmed */}
        <div className="kpi-card cursor-pointer" onClick={() => onNavigate("replies")}>
          <div className="kpi-top-bar kpi-bar-emerald"></div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[12px] font-semibold text-[#64748B]">Bookings</span>
            <div className="w-8 h-8 rounded-lg bg-[#ECFDF5] text-[#059669] flex items-center justify-center text-sm">
              🗓️
            </div>
          </div>
          <div className="text-2xl font-bold text-[#0F172A] tracking-tight">
            {(stats?.scheduled_leads ?? 0).toLocaleString()}
          </div>
          <div className="mt-2 text-[11px] text-[#64748B] flex items-center gap-1.5">
            <span className="px-1.5 py-0.5 rounded bg-[#ECFDF5] text-[#059669] font-bold">
              {stats?.booked_pct ?? 0}% booked
            </span>
            <span className="truncate">confirmed</span>
          </div>
        </div>
      </div>

      {/* Real-Time Live Activity Stream */}
      <ActivityStream events={events} syncChoiceText={syncChoiceText} />

      {/* Conversion Funnel & Quick Action Hub */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Funnel Progress */}
        <div className="lg:col-span-2 bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#F1F5F9]">
            <div>
              <h3 className="font-bold text-[#0F172A] text-[15px]">Outreach &amp; Conversion Pipeline</h3>
              <p className="text-[12px] text-[#64748B]">Stage-by-stage progression across all campaign cohorts</p>
            </div>
            <span className="badge badge-sent text-[11px]">Real-Time Sync</span>
          </div>

          <div className="space-y-3.5 pt-1">
            {/* Total Leads Stage */}
            <div>
              <div className="flex justify-between text-[12.5px] font-medium mb-1">
                <span className="text-[#334155] flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#2563EB]"></span>
                  <span>1. Audience Loaded</span>
                </span>
                <span className="font-bold text-[#0F172A]">{stats?.total_leads ?? 0} leads (100%)</span>
              </div>
              <div className="w-full bg-[#F1F5F9] rounded-full h-2 overflow-hidden">
                <div className="bg-[#2563EB] h-2 rounded-full" style={{ width: "100%" }}></div>
              </div>
            </div>

            {/* Sent Stage */}
            <div>
              <div className="flex justify-between text-[12.5px] font-medium mb-1">
                <span className="text-[#334155] flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#0D9488]"></span>
                  <span>2. Successfully Dispatched</span>
                </span>
                <span className="font-bold text-[#0F172A]">
                  {stats?.sent_leads ?? 0} ({stats?.sent_pct ?? 0}%)
                </span>
              </div>
              <div className="w-full bg-[#F1F5F9] rounded-full h-2 overflow-hidden">
                <div className="bg-[#0D9488] h-2 rounded-full" style={{ width: `${Math.min(100, stats?.sent_pct ?? 0)}%` }}></div>
              </div>
            </div>

            {/* Replies Stage */}
            <div>
              <div className="flex justify-between text-[12.5px] font-medium mb-1">
                <span className="text-[#334155] flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#7C3AED]"></span>
                  <span>3. Inbound Inquiries &amp; Replies</span>
                </span>
                <span className="font-bold text-[#0F172A]">
                  {stats?.replied_leads ?? 0} ({stats?.reply_pct ?? 0}%)
                </span>
              </div>
              <div className="w-full bg-[#F1F5F9] rounded-full h-2 overflow-hidden">
                <div className="bg-[#7C3AED] h-2 rounded-full" style={{ width: `${Math.min(100, (stats?.reply_pct ?? 0) * 5)}%` }}></div>
              </div>
            </div>

            {/* Bookings Stage */}
            <div>
              <div className="flex justify-between text-[12.5px] font-medium mb-1">
                <span className="text-[#334155] flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#059669]"></span>
                  <span>4. Consultation Meetings Scheduled</span>
                </span>
                <span className="font-bold text-[#0F172A]">{stats?.scheduled_leads ?? 0} booked</span>
              </div>
              <div className="w-full bg-[#F1F5F9] rounded-full h-2 overflow-hidden">
                <div className="bg-[#059669] h-2 rounded-full" style={{ width: `${(stats?.scheduled_leads ?? 0) > 0 ? 100 : 0}%` }}></div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Col: Quick Access Actions */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-[#0F172A] text-[15px] mb-1">Operational Actions</h3>
            <p className="text-[12px] text-[#64748B] mb-4">Direct shortcuts to campaign management workflows</p>

            <div className="space-y-2">
              <button
                onClick={() => onNavigate("upload")}
                className="w-full flex items-center justify-between p-3 rounded-lg border border-[#E2E8F0] hover:border-[#2563EB] hover:bg-[#F8FAFC] transition-all text-left text-[13px] font-medium group"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-lg">📤</span>
                  <div>
                    <div className="text-[#0F172A] font-semibold">Upload Leads &amp; Generate Drafts</div>
                    <div className="text-[11px] text-[#64748B]">Import CSV or Excel and AI draft emails</div>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-[#94A3B8] group-hover:text-[#2563EB] group-hover:translate-x-0.5 transition-all" />
              </button>

              <button
                onClick={() => onNavigate("email")}
                className="w-full flex items-center justify-between p-3 rounded-lg border border-[#E2E8F0] hover:border-[#2563EB] hover:bg-[#F8FAFC] transition-all text-left text-[13px] font-medium group"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-lg">✉️</span>
                  <div>
                    <div className="text-[#0F172A] font-semibold">Email Review Studio</div>
                    <div className="text-[11px] text-[#64748B]">
                      {stats.drafted_leads} draft(s) awaiting approval
                    </div>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-[#94A3B8] group-hover:text-[#2563EB] group-hover:translate-x-0.5 transition-all" />
              </button>

              <button
                onClick={() => onNavigate("master_db")}
                className="w-full flex items-center justify-between p-3 rounded-lg border border-[#E2E8F0] hover:border-[#2563EB] hover:bg-[#F8FAFC] transition-all text-left text-[13px] font-medium group"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-lg">🗄️</span>
                  <div>
                    <div className="text-[#0F172A] font-semibold">Master DB Segmentation</div>
                    <div className="text-[11px] text-[#64748B]">Hot, Warm &amp; Cold qualified leads</div>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-[#94A3B8] group-hover:text-[#2563EB] group-hover:translate-x-0.5 transition-all" />
              </button>

              <button
                onClick={() => onNavigate("analytics")}
                className="w-full flex items-center justify-between p-3 rounded-lg border border-[#E2E8F0] hover:border-[#2563EB] hover:bg-[#F8FAFC] transition-all text-left text-[13px] font-medium group"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-lg">📈</span>
                  <div>
                    <div className="text-[#0F172A] font-semibold">Analytics &amp; PDF/Excel Reports</div>
                    <div className="text-[11px] text-[#64748B]">14 intelligence engines telemetry</div>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-[#94A3B8] group-hover:text-[#2563EB] group-hover:translate-x-0.5 transition-all" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
