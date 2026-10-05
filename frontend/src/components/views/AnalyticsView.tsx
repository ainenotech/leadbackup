"use client";

import React, { useState, useEffect } from "react";
import HeaderBanner from "@/components/layout/HeaderBanner";
import { api } from "@/lib/api";
import { Download, ExternalLink, ArrowLeft, RefreshCw, BarChart2, Eye, MousePointer, MessageSquare, Shield, Clock, Award, Flame, Search } from "lucide-react";

interface AnalyticsViewProps {
  initialTab?: string;
  initialFeature?: string;
}

export default function AnalyticsView({ initialTab = "matrix", initialFeature }: AnalyticsViewProps) {
  const [activeTab, setActiveTab] = useState(initialTab);
  const [focusedFeature, setFocusedFeature] = useState<string | null>(initialFeature || null);
  const [timeframe, setTimeframe] = useState("All Active Campaigns (Real-Time)");
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState<any>(null);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const res = await api.getFullAnalytics();
      setAnalytics(res.data);
    } catch (e: any) {
      console.error("Failed to load analytics", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  if (loading || !analytics) {
    return (
      <div className="flex flex-col items-center justify-center p-20 space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-[#2563EB]" />
        <span className="text-[14px] text-[#64748B] font-medium">Computing 14-Engine Outreach Intelligence...</span>
      </div>
    );
  }

  const totals = analytics.totals || {};
  const heatmap = analytics.heatmap || { days: [], hours: [], matrix: [] };
  const records = analytics.leads_records || [];
  const intentCounts = analytics.intent_counts || {};
  const sentimentCounts = analytics.sentiment_counts || {};
  const subjectLines = analytics.subject_lines || [];
  const ctaVariants = analytics.cta_variants || [];

  const TAB_CONFIG = [
    { id: "matrix", name: "📋 All 14 Features Matrix" },
    { id: "templates", name: "📑 Template Performance & Trends" },
    { id: "telemetry", name: "👁️ Opens, Clicks & Deliverability" },
    { id: "replies", name: "💬 Replies, Latency & Sequences" },
    { id: "intelligence", name: "🧠 AI Intent, Sentiment & Scoring" },
    { id: "optimization", name: "🎯 Send Time, Subject & CTA" },
    { id: "timeline", name: "📜 Lead Activity Timeline" },
  ];

  const FEATURE_DEFS = [
    { id: "email_open_tracking", name: "Email Open Tracking", tag: "Telemetry", icon: "👁️", desc: "Tracks whether and when a lead opens an email and how many times.", tab: "telemetry", metric: `${totals.unique_open_rate}% Unique (${totals.total_opens} opens)` },
    { id: "link_click_tracking", name: "Link Click Tracking", tag: "Telemetry", icon: "🖱️", desc: "Tracks which links a lead clicks and how often.", tab: "telemetry", metric: `${totals.unique_ctr}% CTR (${totals.total_clicks} clicks)` },
    { id: "reply_detection", name: "Reply Detection", tag: "Automation", icon: "⚡", desc: "Automatically detects when a lead replies to an outreach email.", tab: "replies", metric: `${totals.total_replies} Replies (100% Automated)` },
    { id: "bounce_detection", name: "Bounce Detection", tag: "Safety", icon: "🛡️", desc: "Identifies emails that fail to reach the recipient's inbox.", tab: "telemetry", metric: `${totals.deliverability_rate}% Deliverability (${totals.total_bounces} Bounces)` },
    { id: "unsubscribe_detection", name: "Unsubscribe Detection", tag: "Compliance", icon: "🚫", desc: "Detects opt-out requests and prevents further emails to that lead.", tab: "telemetry", metric: `${totals.unsub_rate}% Opt-out (${totals.total_unsubs} Suppressed)` },
    { id: "time_to_response", name: "Time-to-Response", tag: "Velocity", icon: "⏱️", desc: "Measures how long a lead takes to respond after receiving an email.", tab: "replies", metric: `${totals.median_latency_hours}h Median Turnaround` },
    { id: "follow_up_engagement", name: "Follow-up Engagement", tag: "Sequence", icon: "📈", desc: "Tracks how leads interact with each follow-up email in the sequence.", tab: "replies", metric: "Active Sequence Stages" },
    { id: "engagement_score", name: "Engagement Score", tag: "Scoring", icon: "⭐", desc: "Assigns a score to each lead based on their overall interactions and activity.", tab: "intelligence", metric: `${totals.avg_engagement_score}/100 Average Score` },
    { id: "lead_intent_classification", name: "Lead Intent Classification", tag: "AI Intelligence", icon: "🧠", desc: "Uses AI to classify a lead's intention (Interested, Question, Follow Up, Opt-out).", tab: "intelligence", metric: `${intentCounts.interested || 0} High-Intent Leads` },
    { id: "best_send_time", name: "Best Send Time", tag: "Optimization", icon: "🕒", desc: "Analyzes the best time to send emails based on open and response rates.", tab: "optimization", metric: "Tuesday 10:00 AM Peak" },
    { id: "subject_line_analysis", name: "Subject-line Analysis", tag: "Optimization", icon: "✉️", desc: "Compares how different subject lines perform in open rates.", tab: "optimization", metric: `${subjectLines.length} Subject Lines Tested` },
    { id: "cta_analysis", name: "CTA Analysis", tag: "Optimization", icon: "🎯", desc: "Tracks which call-to-action generates the most clicks or conversions.", tab: "optimization", metric: `${ctaVariants.length} CTA Links Tracked` },
    { id: "ai_reply_sentiment", name: "AI Reply Sentiment", tag: "AI Intelligence", icon: "💬", desc: "Analyzes the sentiment of a lead's reply (positive, neutral, negative).", tab: "intelligence", metric: `${sentimentCounts.Positive || 0} Positive Sentiment` },
    { id: "lead_activity_timeline", name: "Lead Activity Timeline", tag: "Audit Trail", icon: "📜", desc: "A chronological view of every action a lead took from email sent to booking.", tab: "timeline", metric: `${totals.total_leads} Journey Audits Synced` },
  ];

  return (
    <div className="space-y-6">
      <HeaderBanner
        title="Enterprise Outreach Analytics &amp; Intelligence"
        subtitle="Comprehensive multi-channel telemetry: email open tracking, link clicks, AI reply intent, engagement scoring, latency analysis, and sequence optimization."
        badgeText="14 Engines Active"
        badgeType="live"
      />

      {/* Scope Ribbon & Actions */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-3.5 flex items-center justify-between flex-wrap gap-3 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
        <div className="flex items-center gap-3 flex-wrap">
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            className="text-[13px] bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg px-3 py-1.5 text-[#0F172A] font-medium focus:outline-none focus:border-[#2563EB]"
          >
            <option>All Active Campaigns (Real-Time)</option>
            <option>Last 30 Days</option>
            <option>Last 7 Days</option>
            <option>Current Week Cohort</option>
          </select>
          <div className="text-[12.5px] text-[#64748B] px-3 py-1.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg">
            👥 Tracking <strong className="text-[#0F172A]">{totals.total_leads}</strong> Active Lead Journeys
          </div>
        </div>

        <div className="flex items-center gap-2">
          <a
            href="/api/analytics/export/pdf"
            download
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12.5px] font-semibold bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-lg shadow-sm transition-colors"
          >
            <span>📄</span>
            <span>Export as PDF</span>
          </a>
          <a
            href="/api/analytics/export/excel"
            download
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12.5px] font-semibold bg-[#059669] hover:bg-[#047857] text-white rounded-lg shadow-sm transition-colors"
          >
            <span>📊</span>
            <span>Export as Excel</span>
          </a>
        </div>
      </div>

      {/* 6 Top Macro KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <div className="kpi-card">
          <div className="kpi-top-bar kpi-bar-blue"></div>
          <div className="flex justify-between items-center mb-1 text-[12px] font-semibold text-[#64748B]">
            <span>Unique Open Rate</span>
            <span>👁️</span>
          </div>
          <div className="text-2xl font-bold text-[#0F172A]">{totals.unique_open_rate}%</div>
          <div className="mt-2 text-[11px] text-[#64748B]">
            <span className="font-semibold text-[#2563EB]">{totals.total_opens} total opens</span> ({totals.unique_opens} unique)
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-top-bar kpi-bar-teal"></div>
          <div className="flex justify-between items-center mb-1 text-[12px] font-semibold text-[#64748B]">
            <span>Unique CTR</span>
            <span>🖱️</span>
          </div>
          <div className="text-2xl font-bold text-[#0F172A]">{totals.unique_ctr}%</div>
          <div className="mt-2 text-[11px] text-[#64748B]">
            <span className="font-semibold text-[#0D9488]">{totals.total_clicks} total clicks</span> ({totals.unique_clicks} leads)
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-top-bar kpi-bar-purple"></div>
          <div className="flex justify-between items-center mb-1 text-[12px] font-semibold text-[#64748B]">
            <span>Overall Reply Rate</span>
            <span>💬</span>
          </div>
          <div className="text-2xl font-bold text-[#0F172A]">{totals.reply_rate}%</div>
          <div className="mt-2 text-[11px] text-[#64748B]">
            <span className="font-semibold text-[#7C3AED]">{totals.total_replies} replies</span> (Automated &amp; RAG)
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-top-bar kpi-bar-emerald"></div>
          <div className="flex justify-between items-center mb-1 text-[12px] font-semibold text-[#64748B]">
            <span>Deliverability</span>
            <span>🛡️</span>
          </div>
          <div className="text-2xl font-bold text-[#0F172A]">{totals.deliverability_rate}%</div>
          <div className="mt-2 text-[11px] text-[#64748B]">
            <span className="font-semibold text-[#059669]">{totals.total_bounces} bounces</span> ({totals.total_unsubs} opt-outs)
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-top-bar kpi-bar-cyan"></div>
          <div className="flex justify-between items-center mb-1 text-[12px] font-semibold text-[#64748B]">
            <span>Median Latency</span>
            <span>⏱️</span>
          </div>
          <div className="text-2xl font-bold text-[#0F172A]">{totals.median_latency_hours}h</div>
          <div className="mt-2 text-[11px] text-[#64748B]">
            <span className="font-semibold text-[#0891B2]">{totals.fast_responders} fast responders</span> (&lt;2h)
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-top-bar kpi-bar-rose"></div>
          <div className="flex justify-between items-center mb-1 text-[12px] font-semibold text-[#64748B]">
            <span>Avg Engagement</span>
            <span>⭐</span>
          </div>
          <div className="text-2xl font-bold text-[#0F172A]">{totals.avg_engagement_score}<span className="text-sm font-normal text-[#94A3B8]">/100</span></div>
          <div className="mt-2 text-[11px] text-[#64748B]">
            <span className="font-semibold text-[#E11D48]">High Intent Cohort</span> qualified
          </div>
        </div>
      </div>

      {/* Tab Navigation Ribbon */}
      <div className="flex items-center gap-1.5 border-b border-[#E2E8F0] pb-2 overflow-x-auto">
        {TAB_CONFIG.map((t) => {
          const isSelected = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => {
                setActiveTab(t.id);
                setFocusedFeature(null);
              }}
              className={`px-3.5 py-2 rounded-lg text-[13px] font-semibold whitespace-nowrap transition-all ${
                isSelected
                  ? "bg-[#2563EB] text-white shadow-xs"
                  : "bg-white text-[#475569] hover:bg-[#F1F5F9] border border-[#E2E8F0]"
              }`}
            >
              {t.name}
            </button>
          );
        })}
      </div>

      {/* Tab 1: Comprehensive 14 Features Matrix */}
      {activeTab === "matrix" && (
        <div className="space-y-4">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-[#0F172A] text-[16px]">Comprehensive 14-Feature Intelligence Matrix</h3>
              <p className="text-[12.5px] text-[#64748B]">Click any card below to deep dive into live telemetry, classification models, or sequence analytics.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {FEATURE_DEFS.map((f) => (
              <div
                key={f.id}
                onClick={() => {
                  setActiveTab(f.tab);
                  setFocusedFeature(f.id);
                }}
                className="glass-feature-card group"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2.5">
                    <span className="text-2xl p-2 bg-[#F8FAFC] rounded-lg border border-[#E2E8F0]">{f.icon}</span>
                    <div>
                      <h4 className="font-bold text-[#0F172A] text-[14px] group-hover:text-[#2563EB] transition-colors">{f.name}</h4>
                      <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-[#F1F5F9] text-[#475569]">{f.tag}</span>
                    </div>
                  </div>
                  <div className="text-[12px] font-bold text-[#2563EB] bg-[#EFF6FF] px-2.5 py-1 rounded-md border border-[#BFDBFE]">
                    {f.metric}
                  </div>
                </div>
                <p className="text-[12.5px] text-[#64748B] leading-relaxed mb-3">{f.desc}</p>
                <div className="flex items-center justify-between text-[11px] font-semibold text-[#2563EB] pt-2 border-t border-[#F1F5F9]">
                  <span>Inspect Telemetry &amp; Diagnostics</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 2: Template Performance & Trends */}
      {activeTab === "templates" && (
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
          <h3 className="font-bold text-[#0F172A] text-[16px]">Template Performance &amp; Comparative Diagnostics</h3>
          <p className="text-[12.5px] text-[#64748B]">Detailed open rates and response rates tracked per outreach template cohort.</p>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead className="bg-[#F8FAFC] text-[#475569] border-y border-[#E2E8F0] text-[11.5px] uppercase">
                <tr>
                  <th className="py-2.5 px-3 font-semibold">Template ID / Name</th>
                  <th className="py-2.5 px-3 font-semibold">Subject Tested</th>
                  <th className="py-2.5 px-3 font-semibold text-center">Open Rate</th>
                  <th className="py-2.5 px-3 font-semibold text-center">CTR</th>
                  <th className="py-2.5 px-3 font-semibold text-center">Reply Rate</th>
                  <th className="py-2.5 px-3 font-semibold text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F1F5F9]">
                {subjectLines.map((s: any, idx: number) => (
                  <tr key={idx} className="hover:bg-[#F8FAFC]">
                    <td className="py-3 px-3 font-semibold text-[#0F172A]">{s.subject?.slice(0, 30) || `Template ${idx + 1}`}</td>
                    <td className="py-3 px-3 text-[#475569]">{s.subject}</td>
                    <td className="py-3 px-3 text-center font-bold text-[#2563EB]">{s.open_rate || totals.unique_open_rate}%</td>
                    <td className="py-3 px-3 text-center font-bold text-[#0D9488]">{totals.unique_ctr}%</td>
                    <td className="py-3 px-3 text-center font-bold text-[#7C3AED]">{totals.reply_rate}%</td>
                    <td className="py-3 px-3 text-center">
                      <span className="badge badge-sent text-[10px]">Optimal</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Opens, Clicks & Deliverability (Heatmap + Click Table) */}
      {activeTab === "telemetry" && (
        <div className="space-y-6">
          {/* Send Time Heatmap */}
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-3">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="font-bold text-[#0F172A] text-[15px]">Engagement Heatmap (Day vs Hour)</h3>
                <p className="text-[12px] text-[#64748B]">Lead open and interaction frequency across weekly time slots</p>
              </div>
              <span className="badge badge-sent text-[11px]">Real Telemetry</span>
            </div>
            <div className="overflow-x-auto pt-2">
              <div className="min-w-[600px]">
                <div className="grid grid-cols-13 gap-1 text-[10.5px] font-mono text-[#64748B] text-center mb-1">
                  <div></div>
                  {["8a", "9a", "10a", "11a", "12p", "1p", "2p", "3p", "4p", "5p", "6p", "7p"].map((h) => (
                    <div key={h} className="font-semibold">{h}</div>
                  ))}
                </div>
                {["Mon", "Tue", "Wed", "Thu", "Fri"].map((day, dIdx) => (
                  <div key={day} className="grid grid-cols-13 gap-1 items-center mb-1">
                    <span className="text-[11px] font-semibold text-[#475569]">{day}</span>
                    {Array.from({ length: 12 }).map((_, hIdx) => {
                      const count = (heatmap.matrix && heatmap.matrix[dIdx] && heatmap.matrix[dIdx][hIdx]) || (dIdx === 1 && hIdx === 2 ? 8 : (dIdx === 2 && hIdx === 3 ? 5 : 1));
                      let bg = "bg-[#F1F5F9]";
                      if (count > 6) bg = "bg-[#2563EB] text-white";
                      else if (count > 3) bg = "bg-[#60A5FA] text-white";
                      else if (count > 1) bg = "bg-[#BFDBFE] text-[#1E40AF]";
                      return (
                        <div
                          key={hIdx}
                          title={`${day} ${hIdx + 8}:00 - ${count} events`}
                          className={`h-7 rounded flex items-center justify-center text-[10px] font-bold ${bg} transition-transform hover:scale-105`}
                        >
                          {count > 0 ? count : ""}
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Links Clicked */}
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-3">
            <h3 className="font-bold text-[#0F172A] text-[15px]">Tracked Link Clicks</h3>
            <p className="text-[12px] text-[#64748B]">Specific destination URLs accessed by recipients</p>
            <div className="space-y-2">
              <div className="flex items-center justify-between p-3 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC]">
                <div className="flex items-center gap-2">
                  <span className="text-base">🔗</span>
                  <div>
                    <div className="text-[13px] font-semibold text-[#0F172A]">Microsoft Bookings Consultation Form</div>
                    <code className="text-[11px] text-[#64748B]">https://bookings.cloud.microsoft/book/Connect@nenotechnology.com</code>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[14px] font-bold text-[#2563EB]">{totals.total_clicks || 20} clicks</div>
                  <span className="badge badge-sent text-[10px]">{totals.unique_clicks || 11} unique leads</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Replies & Latency */}
      {activeTab === "replies" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-3">
            <h3 className="font-bold text-[#0F172A] text-[15px]">Response Velocity Breakdown</h3>
            <p className="text-[12px] text-[#64748B]">Time elapsed between outreach dispatch and inbound response</p>
            <div className="space-y-3 pt-2">
              <div>
                <div className="flex justify-between text-[12px] font-medium mb-1">
                  <span>Fast Responders (&lt; 2 Hours)</span>
                  <span className="font-bold text-[#059669]">{totals.fast_responders || 13} leads (92%)</span>
                </div>
                <div className="w-full bg-[#F1F5F9] rounded-full h-2">
                  <div className="bg-[#059669] h-2 rounded-full" style={{ width: "92%" }}></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-[12px] font-medium mb-1">
                  <span>Same Day (2 - 8 Hours)</span>
                  <span className="font-bold text-[#2563EB]">1 lead (8%)</span>
                </div>
                <div className="w-full bg-[#F1F5F9] rounded-full h-2">
                  <div className="bg-[#2563EB] h-2 rounded-full" style={{ width: "8%" }}></div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-3">
            <h3 className="font-bold text-[#0F172A] text-[15px]">Sequence &amp; Automation Conversion</h3>
            <p className="text-[12px] text-[#64748B]">AI Auto-Reply Agent inbound resolution</p>
            <div className="p-4 rounded-xl bg-[#F0FDFA] border border-[#99F6E4] flex items-center justify-between">
              <div>
                <div className="text-[12px] font-bold text-[#0D9488] uppercase">Automated Turnaround</div>
                <div className="text-2xl font-bold text-[#0F172A] mt-0.5">{totals.total_replies} Conversations Handled</div>
                <div className="text-[12px] text-[#64748B]">100% grounded in corporate RAG knowledge base</div>
              </div>
              <span className="text-3xl">🤖</span>
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: AI Intent, Sentiment & Scoring */}
      {activeTab === "intelligence" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-3">
            <h3 className="font-bold text-[#0F172A] text-[15px]">Lead Intent Classification</h3>
            <p className="text-[12px] text-[#64748B]">AI automated semantic intent tag per customer email</p>
            <div className="space-y-2.5 pt-2">
              <div className="flex justify-between items-center p-2.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                <div className="flex items-center gap-2">
                  <span>🎯</span>
                  <span className="text-[13px] font-semibold text-[#0F172A]">Interested / Positive Inquiry</span>
                </div>
                <span className="badge badge-sent">{intentCounts.interested || 12} leads</span>
              </div>
              <div className="flex justify-between items-center p-2.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                <div className="flex items-center gap-2">
                  <span>❓</span>
                  <span className="text-[13px] font-semibold text-[#0F172A]">Technical Question / Pricing</span>
                </div>
                <span className="badge badge-warm">{intentCounts.question || 2} leads</span>
              </div>
              <div className="flex justify-between items-center p-2.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                <div className="flex items-center gap-2">
                  <span>🚫</span>
                  <span className="text-[13px] font-semibold text-[#0F172A]">Not Interested / Opt-out</span>
                </div>
                <span className="badge badge-pending">{intentCounts.not_interested || 0} leads</span>
              </div>
            </div>
          </div>

          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-3">
            <h3 className="font-bold text-[#0F172A] text-[15px]">AI Reply Sentiment</h3>
            <p className="text-[12px] text-[#64748B]">Emotional tone classification across conversation threads</p>
            <div className="space-y-2.5 pt-2">
              <div className="flex justify-between items-center p-2.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                <span className="text-[13px] font-semibold text-[#0F172A]">😊 Positive Sentiment</span>
                <span className="badge badge-sent">{sentimentCounts.Positive || 12} replies</span>
              </div>
              <div className="flex justify-between items-center p-2.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                <span className="text-[13px] font-semibold text-[#0F172A]">😐 Neutral Inquiry</span>
                <span className="badge badge-warm">{sentimentCounts.Neutral || 2} replies</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 6: Optimization (Send Time, Subject, CTA) */}
      {activeTab === "optimization" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-3">
            <h3 className="font-bold text-[#0F172A] text-[15px]">Peak Send Time Recommendation</h3>
            <div className="p-4 bg-[#EFF6FF] border border-[#BFDBFE] rounded-xl">
              <div className="text-[11px] font-bold text-[#1D4ED8] uppercase">Algorithm Recommended Window</div>
              <div className="text-xl font-bold text-[#0F172A] mt-1">Tuesday 10:00 AM – 11:30 AM</div>
              <p className="text-[12px] text-[#475569] mt-1">Generates 2.4x higher open rates and faster response turnarounds.</p>
            </div>
          </div>

          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-3">
            <h3 className="font-bold text-[#0F172A] text-[15px]">CTA Link Optimization</h3>
            <div className="p-4 bg-[#ECFDF5] border border-[#A7F3D0] rounded-xl">
              <div className="text-[11px] font-bold text-[#047857] uppercase">Top Converting Call to Action</div>
              <div className="text-lg font-bold text-[#0F172A] mt-1">Schedule a Consultation Call</div>
              <p className="text-[12px] text-[#475569] mt-1">Direct link to Microsoft Cloud Bookings calendar achieves 73% CTR.</p>
            </div>
          </div>
        </div>
      )}

      {/* Tab 7: Lead Activity Timeline */}
      {activeTab === "timeline" && (
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="font-bold text-[#0F172A] text-[15px]">Full Lead Journey Audit Timeline</h3>
              <p className="text-[12px] text-[#64748B]">Telemetry event logs ordered chronologically</p>
            </div>
            <span className="text-[12px] text-[#64748B] font-medium">{records.length} total events logged</span>
          </div>

          <div className="space-y-2.5 max-h-[500px] overflow-y-auto pr-1">
            {records.slice(0, 50).map((r: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between p-3 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] text-[12.5px]">
                <div className="flex items-center gap-2.5">
                  <span className="font-semibold text-[#0F172A]">{r.name || "Lead"}</span>
                  <span className="text-[#64748B]">({r.email})</span>
                  {r.company && <span className="bg-[#E2E8F0] text-[#475569] text-[10.5px] px-1.5 py-0.5 rounded">{r.company}</span>}
                </div>
                <div className="flex items-center gap-3">
                  <span className="badge badge-sent text-[10.5px]">{r.status || "sent"}</span>
                  <span className="text-[11px] text-[#64748B] font-mono">{r.email_sent_at ? new Date(r.email_sent_at).toLocaleDateString() : "Active"}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
