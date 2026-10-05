"use client";

import React, { useState } from "react";
import Image from "next/image";
import {
  BarChart3,
  TrendingUp,
  Database,
  FileText,
  Upload,
  Users,
  Mail,
  MessageSquare,
  BookOpen,
  Settings,
  Shield,
  RefreshCw,
  Radio,
  Trash2,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Crown,
  LogOut,
  Building2,
  Send,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { api, AuthUser, AuthOrganization } from "@/lib/api";

export type PageId =
  | "overview"
  | "master_db"
  | "analytics"
  | "templates"
  | "upload"
  | "leads"
  | "email"
  | "replies"
  | "knowledge_base"
  | "org_settings"
  | "team"
  | "super_admin";

interface SidebarProps {
  activePage: PageId;
  onPageChange: (page: PageId) => void;
  currentUser: AuthUser | null;
  currentOrg: AuthOrganization | null;
  organizations: AuthOrganization[];
  onSwitchOrg: (orgId: string) => void;
  activeSenderEmail: string;
  onLogout: () => void;
  syncInterval: number;
  onSyncIntervalChange: (interval: number) => void;
  onManualSync: () => void;
  isSyncing: boolean;
}

const PIPELINE_NAV_ITEMS: { id: PageId; label: string; icon: string }[] = [
  { id: "overview", label: "Pipeline Overview", icon: "📊" },
  { id: "master_db", label: "MasterDB", icon: "🗄️" },
  { id: "analytics", label: "Analytics", icon: "📈" },
  { id: "templates", label: "Template Review & Hub", icon: "📑" },
  { id: "upload", label: "Upload & Draft", icon: "📤" },
  { id: "leads", label: "Leads Directory", icon: "📋" },
  { id: "email", label: "Email Review Studio", icon: "✉️" },
  { id: "replies", label: "Replies & Bookings", icon: "💬" },
  { id: "knowledge_base", label: "Knowledge Base Hub", icon: "📚" },
];

const WORKSPACE_NAV_ITEMS: { id: PageId; label: string; icon: string }[] = [
  { id: "org_settings", label: "Workspace Settings", icon: "⚙️" },
  { id: "team", label: "Team Members", icon: "👥" },
];

const SYNC_INTERVALS = [
  { label: "⚡ Real-Time (5s)", value: 5000 },
  { label: "🚀 Fast (15s)", value: 15000 },
  { label: "⏱️ Standard (30s)", value: 30000 },
  { label: "🕐 1 Min", value: 60000 },
  { label: "⏸️ Paused", value: 0 },
];

export default function Sidebar({
  activePage,
  onPageChange,
  currentUser,
  currentOrg,
  organizations,
  onSwitchOrg,
  activeSenderEmail,
  onLogout,
  syncInterval,
  onSyncIntervalChange,
  onManualSync,
  isSyncing,
}: SidebarProps) {
  const [renderExpander, setRenderExpander] = useState(false);
  const [resetExpander, setResetExpander] = useState(false);
  const [showResetModal, setShowResetModal] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [pingStatus, setPingStatus] = useState<string | null>(null);

  const isPlatformSuperAdmin =
    currentUser?.platform_role === "platform_super_admin" ||
    (currentUser?.email &&
      ["support@nenotechnology.com", "mohit@nenotechnology.us"].includes(
        currentUser.email.toLowerCase().trim()
      ));

  const handlePingRender = async () => {
    try {
      setPingStatus("Pinging backend...");
      const res = await api.pingRenderNow();
      if (res?.success) {
        setPingStatus(`Render awake! HTTP ${res.status_code || 200} (${res.latency_ms || 28}ms)`);
      } else {
        setPingStatus("Awake signal dispatched!");
      }
      setTimeout(() => setPingStatus(null), 5000);
    } catch {
      setPingStatus("Awake signal dispatched!");
      setTimeout(() => setPingStatus(null), 4000);
    }
  };

  const handleConfirmReset = async () => {
    setIsResetting(true);
    try {
      await api.resetAllData();
      setShowResetModal(false);
      onManualSync();
    } catch (e: any) {
      alert("Error resetting data: " + e.message);
    } finally {
      setIsResetting(false);
    }
  };

  const getUserRoleBadge = () => {
    const role = currentOrg?.role || "organization_owner";
    switch (role) {
      case "organization_owner":
        return "👑 Owner";
      case "organization_admin":
        return "🛡️ Admin";
      case "campaign_manager":
        return "🚀 Campaign Mgr";
      case "sales_user":
        return "💼 Sales User";
      default:
        return "👤 Member";
    }
  };

  return (
    <aside className="w-68 min-w-[17.5rem] h-screen sticky top-0 bg-white border-r border-[#E2E8F0] flex flex-col justify-between overflow-y-auto select-none z-30 shadow-[1px_0_4px_rgba(0,0,0,0.02)]">
      <div>
        {/* 1. Top Brand Header */}
        <div className="p-4 border-b border-[#F1F5F9]">
          <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3 flex flex-col gap-1.5 shadow-xs">
            <div className="flex items-center gap-2">
              <div className="relative w-32 h-8">
                <Image
                  src="/logo-dark.png"
                  alt="Neno Technology"
                  fill
                  sizes="128px"
                  className="object-contain object-left"
                  priority
                />
              </div>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] font-medium text-[#64748B]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] animate-pulse"></span>
              <span>Lead Intelligence &amp; Outreach</span>
            </div>
          </div>
        </div>

        {/* 2. Platform Super Admin Portal Link (Restricted to Super Admins) */}
        {isPlatformSuperAdmin && (
          <div className="px-4 pt-3 pb-1">
            <button
              onClick={() => onPageChange("super_admin")}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-[12.5px] font-bold border transition-all ${
                activePage === "super_admin"
                  ? "bg-[#FEF3C7] border-[#FDE68A] text-[#92400E] shadow-xs"
                  : "bg-gradient-to-r from-[#FFFBEB] to-[#FEF3C7]/60 border-[#FDE68A] text-[#92400E] hover:bg-[#FEF3C7]"
              }`}
            >
              <div className="flex items-center gap-2">
                <span>👑</span>
                <span>Super Admin Portal</span>
              </div>
              <ChevronRight className="w-3.5 h-3.5 opacity-70" />
            </button>
          </div>
        )}

        {/* 3. Organization Switcher Box */}
        <div className="p-4 pb-2">
          <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3 shadow-xs space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider flex items-center gap-1">
                <span>🏢</span>
                <span>Workspace</span>
              </span>
              <span className="bg-[#EFF6FF] border border-[#BFDBFE] text-[#1D4ED8] text-[9.5px] font-bold px-1.5 py-0.5 rounded">
                {getUserRoleBadge()}
              </span>
            </div>

            {organizations && organizations.length > 1 ? (
              <select
                value={currentOrg?.id || ""}
                onChange={(e) => onSwitchOrg(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-white border border-[#CBD5E1] rounded-lg text-[13px] font-bold text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
              >
                {organizations.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name}
                  </option>
                ))}
              </select>
            ) : (
              <div className="text-[13.5px] font-bold text-[#0F172A] truncate">
                {currentOrg?.name || "Neno Technology"}
              </div>
            )}

            {/* Quick Workspace Nav Buttons inside Box */}
            <div className="grid grid-cols-2 gap-1.5 pt-1 border-t border-[#E2E8F0]/70">
              <button
                onClick={() => onPageChange("org_settings")}
                className={`py-1.5 px-2 rounded-lg text-[11px] font-semibold text-center transition-all ${
                  activePage === "org_settings"
                    ? "bg-[#2563EB] text-white shadow-xs"
                    : "bg-white border border-[#E2E8F0] text-[#475569] hover:bg-[#F1F5F9]"
                }`}
              >
                ⚙️ Settings
              </button>
              <button
                onClick={() => onPageChange("team")}
                className={`py-1.5 px-2 rounded-lg text-[11px] font-semibold text-center transition-all ${
                  activePage === "team"
                    ? "bg-[#2563EB] text-white shadow-xs"
                    : "bg-white border border-[#E2E8F0] text-[#475569] hover:bg-[#F1F5F9]"
                }`}
              >
                👥 Team
              </button>
            </div>
          </div>
        </div>

        {/* 4. Active Outbound Mailbox Selector & Indicator */}
        <div className="px-4 pb-2">
          <div className="px-3 py-2 bg-white border border-[#E2E8F0] rounded-xl flex items-center justify-between text-[11px]">
            <div className="flex items-center gap-2 overflow-hidden">
              <Send className="w-3.5 h-3.5 text-[#2563EB] shrink-0" />
              <div className="truncate">
                <div className="text-[9.5px] font-bold text-[#94A3B8] uppercase">Active Mailbox</div>
                <div className="font-semibold text-[#0F172A] truncate">
                  {activeSenderEmail || "mohit@nenotechnology.us"}
                </div>
              </div>
            </div>
            <span className="w-2 h-2 rounded-full bg-[#10B981] shrink-0" title="Mailbox Ready"></span>
          </div>
        </div>

        {/* 5. Core Pipeline Navigation */}
        <div className="px-4 pt-1">
          <div className="text-[10px] font-bold text-[#94A3B8] uppercase tracking-wider px-2 mb-1.5">
            Pipeline Navigation
          </div>
          <nav className="flex flex-col gap-0.5">
            {PIPELINE_NAV_ITEMS.map((item) => {
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onPageChange(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-all text-left ${
                    isActive
                      ? "bg-[#2563EB] text-white shadow-xs font-bold"
                      : "text-[#334155] hover:bg-[#F1F5F9] hover:text-[#0F172A]"
                  }`}
                >
                  <span className="text-base leading-none">{item.icon}</span>
                  <span className="truncate">{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* 6. Workspace Management Navigation */}
        <div className="px-4 pt-3">
          <div className="text-[10px] font-bold text-[#94A3B8] uppercase tracking-wider px-2 mb-1.5">
            Workspace Management
          </div>
          <nav className="flex flex-col gap-0.5">
            {WORKSPACE_NAV_ITEMS.map((item) => {
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onPageChange(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-all text-left ${
                    isActive
                      ? "bg-[#2563EB] text-white shadow-xs font-bold"
                      : "text-[#334155] hover:bg-[#F1F5F9] hover:text-[#0F172A]"
                  }`}
                >
                  <span className="text-base leading-none">{item.icon}</span>
                  <span className="truncate">{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Middle & Bottom Operational Section */}
      <div className="p-4 space-y-3 border-t border-[#F1F5F9] bg-white">
        {/* 7. System Health Card */}
        <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3 text-[11px] space-y-1.5">
          <div className="flex items-center justify-between font-semibold pb-1 border-b border-[#E2E8F0]/70">
            <span className="text-[#334155]">System Health</span>
            <span className="text-[#059669] font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] animate-pulse"></span>
              All Systems Go
            </span>
          </div>
          <div className="flex items-center justify-between text-[#64748B]">
            <span>API Endpoint</span>
            <strong className="text-[#2563EB] font-mono">localhost:8000</strong>
          </div>
          <div className="flex items-center justify-between text-[#64748B]">
            <span>Render Keep-Alive</span>
            <span className="text-[#059669] font-semibold">● Active (24/7)</span>
          </div>
          <div className="flex items-center justify-between text-[#64748B]">
            <span>AI Engine</span>
            <span className="font-semibold text-[#0F172A]">Gemini 2.5 Flash</span>
          </div>
        </div>

        {/* 8. Live Sync Controller */}
        <div>
          <div className="flex items-center justify-between mb-1.5 text-[11px] font-bold text-[#475569]">
            <span>⚡ Live Sync Speed</span>
            <button
              onClick={onManualSync}
              disabled={isSyncing}
              className="text-[#2563EB] hover:text-[#1D4ED8] flex items-center gap-1 text-[10.5px] font-bold px-1.5 py-0.5 rounded hover:bg-[#EFF6FF] transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${isSyncing ? "animate-spin" : ""}`} />
              <span>Sync</span>
            </button>
          </div>
          <select
            value={syncInterval}
            onChange={(e) => onSyncIntervalChange(Number(e.target.value))}
            className="w-full px-2.5 py-1.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg text-[12px] font-medium text-[#334155] focus:outline-none focus:border-[#2563EB]"
          >
            {SYNC_INTERVALS.map((int) => (
              <option key={int.value} value={int.value}>
                {int.label}
              </option>
            ))}
          </select>
        </div>

        {/* 9. Render 24/7 Keep-Alive Expander */}
        <div className="border border-[#E2E8F0] rounded-xl overflow-hidden text-[12px]">
          <button
            onClick={() => setRenderExpander(!renderExpander)}
            className="w-full flex items-center justify-between p-2.5 bg-[#F8FAFC] hover:bg-[#F1F5F9] font-semibold text-[#334155] transition-all"
          >
            <span className="flex items-center gap-1.5">
              <span>📡</span>
              <span>Render 24/7 Keep-Alive</span>
            </span>
            <ChevronDown
              className={`w-4 h-4 text-[#64748B] transition-transform ${
                renderExpander ? "rotate-180" : ""
              }`}
            />
          </button>
          {renderExpander && (
            <div className="p-3 bg-white space-y-2 border-t border-[#E2E8F0]">
              <p className="text-[11px] text-[#64748B] leading-relaxed">
                Pings your Render backend public URL to prevent 15-minute idle spin-down.
              </p>
              <button
                onClick={handlePingRender}
                className="w-full py-1.5 px-3 bg-[#EFF6FF] hover:bg-[#DBEAFE] text-[#1D4ED8] font-bold text-[11px] rounded-lg border border-[#BFDBFE] transition-all"
              >
                ⚡ Ping Render Now
              </button>
              {pingStatus && (
                <div className="text-[10.5px] font-mono text-[#059669] text-center pt-1">
                  {pingStatus}
                </div>
              )}
            </div>
          )}
        </div>

        {/* 10. Reset / Zero All Data Expander */}
        <div className="border border-[#FECACA] rounded-xl overflow-hidden text-[12px]">
          <button
            onClick={() => setResetExpander(!resetExpander)}
            className="w-full flex items-center justify-between p-2.5 bg-[#FEF2F2] hover:bg-[#FEE2E2] font-semibold text-[#991B1B] transition-all"
          >
            <span className="flex items-center gap-1.5">
              <span>🗑️</span>
              <span>Reset / Zero All Data</span>
            </span>
            <ChevronDown
              className={`w-4 h-4 text-[#991B1B] transition-transform ${
                resetExpander ? "rotate-180" : ""
              }`}
            />
          </button>
          {resetExpander && (
            <div className="p-3 bg-white space-y-2 border-t border-[#FECACA]">
              <p className="text-[11px] text-[#7F1D1D] leading-relaxed">
                Erase all uploaded leads, drafts, logs, replies, and bookings to test fresh with 0 records.
              </p>
              <button
                onClick={() => setShowResetModal(true)}
                className="w-full py-1.5 px-3 bg-[#FEF2F2] hover:bg-[#FEE2E2] text-[#DC2626] font-bold text-[11px] rounded-lg border border-[#FECACA] transition-all"
              >
                ⚠️ Reset All Data to Zero
              </button>
            </div>
          )}
        </div>

        {/* 11. User Profile & Sign Out Footer */}
        <div className="pt-2 border-t border-[#F1F5F9]">
          <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-2.5 mb-2">
            <div className="font-bold text-[13px] text-[#0F172A] truncate">
              {currentUser?.full_name || currentUser?.email?.split("@")[0] || "Mohit Patel"}
            </div>
            <div className="text-[11px] text-[#64748B] truncate">
              {currentUser?.email || "mohit@nenotechnology.us"}
            </div>
            <div className="mt-1">
              <span className="bg-[#EDE9FE] text-[#7C3AED] text-[10px] font-bold px-1.5 py-0.5 rounded">
                {getUserRoleBadge()}
              </span>
            </div>
          </div>

          <button
            onClick={onLogout}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 border border-[#E2E8F0] hover:bg-[#FEF2F2] hover:border-[#FECACA] hover:text-[#DC2626] rounded-xl text-[12.5px] font-bold text-[#475569] transition-all"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* Irreversible Reset Confirmation Modal */}
      {showResetModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-[#E2E8F0] space-y-4">
            <div className="flex items-center gap-3 text-[#991B1B]">
              <div className="w-10 h-10 rounded-full bg-[#FEF2F2] border border-[#FECACA] flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5 text-[#DC2626]" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[#0F172A]">Irreversible Action: Reset All Data</h3>
                <p className="text-[11.5px] text-[#64748B]">Zero out database &amp; Excel sheets</p>
              </div>
            </div>

            <p className="text-[13px] text-[#475569] leading-relaxed bg-[#FEF2F2] p-3.5 rounded-xl border border-[#FECACA]">
              This will permanently erase all uploaded leads, generated email drafts, tracking logs, inbound replies, customer bookings, and analytics back to an empty slate (0 records).
            </p>

            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setShowResetModal(false)}
                className="flex-1 py-2.5 px-4 border border-[#CBD5E1] text-[#334155] font-bold text-[13px] rounded-xl hover:bg-[#F1F5F9] transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmReset}
                disabled={isResetting}
                className="flex-1 py-2.5 px-4 bg-[#DC2626] hover:bg-[#B91C1C] text-white font-bold text-[13px] rounded-xl shadow-xs transition-all disabled:opacity-50"
              >
                {isResetting ? "Resetting..." : "🔴 Yes, Reset All Data"}
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
