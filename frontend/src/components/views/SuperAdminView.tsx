"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldAlert,
  Building,
  Users,
  Database,
  Mail,
  BookOpen,
  Search,
  Plus,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import { api, AuthUser, AuthOrganization } from "@/lib/api";

interface SuperAdminViewProps {
  currentUser: AuthUser | null;
}

export default function SuperAdminView({ currentUser }: SuperAdminViewProps) {
  const [activeTab, setActiveTab] = useState<"orgs" | "provision">("orgs");
  const [metrics, setMetrics] = useState({
    total_organizations: 0,
    active_organizations: 0,
    total_users: 0,
    total_leads: 0,
    total_campaign_logs: 0,
    total_kb_docs: 0,
  });
  const [organizations, setOrganizations] = useState<AuthOrganization[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  // Provision form state
  const [provOrgName, setProvOrgName] = useState("");
  const [provAdminEmail, setProvAdminEmail] = useState("");
  const [provAdminName, setProvAdminName] = useState("");
  const [provPassword, setProvPassword] = useState("");
  const [isProvisioning, setIsProvisioning] = useState(false);
  const [provisionMessage, setProvisionMessage] = useState<string | null>(null);

  const loadAdminData = async () => {
    try {
      setIsLoading(true);
      const res = await api.getSuperAdminOverview();
      if (res.metrics) setMetrics(res.metrics);
      if (res.organizations) setOrganizations(res.organizations);
    } catch (e: any) {
      console.warn("Failed to load super admin data:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const handleToggleStatus = async (orgId: string, currentStatus: string) => {
    const newStatus = currentStatus === "active" ? "suspended" : "active";
    if (!confirm(`Are you sure you want to change status to "${newStatus}"?`)) return;

    try {
      await api.setOrgStatus(orgId, newStatus);
      await loadAdminData();
    } catch (err: any) {
      alert("Failed to update status: " + err.message);
    }
  };

  const handleProvision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!provOrgName || !provAdminEmail || !provPassword) return;

    try {
      setIsProvisioning(true);
      setProvisionMessage(null);
      await api.register({
        org_name: provOrgName.trim(),
        admin_email: provAdminEmail.trim().toLowerCase(),
        password: provPassword,
        full_name: provAdminName.trim() || undefined,
      });

      setProvisionMessage(`Organization "${provOrgName}" successfully provisioned!`);
      setProvOrgName("");
      setProvAdminEmail("");
      setProvAdminName("");
      setProvPassword("");
      await loadAdminData();
    } catch (err: any) {
      alert("Provisioning failed: " + err.message);
    } finally {
      setIsProvisioning(false);
    }
  };

  const filteredOrgs = organizations.filter((o) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (o.name || "").toLowerCase().includes(q) || (o.slug || "").toLowerCase().includes(q);
  });

  return (
    <div className="space-y-6">
      {/* Top Header Banner */}
      <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#FEF3C7] border border-[#FDE68A] text-[#92400E] text-[11px] font-bold uppercase tracking-wider mb-2">
              <span>👑</span>
              <span>Platform Super Admin</span>
            </div>
            <h1 className="text-2xl font-extrabold text-[#0F172A] tracking-tight">
              Global SaaS Operations Center
            </h1>
            <p className="text-[13.5px] text-[#64748B] max-w-2xl leading-relaxed mt-1">
              Platform-wide telemetry, cross-tenant auditing, and tenant workspace controls across all organizations.
            </p>
          </div>

          <button
            onClick={loadAdminData}
            disabled={isLoading}
            className="self-start sm:self-center inline-flex items-center gap-2 px-3.5 py-2 bg-[#F8FAFC] hover:bg-[#F1F5F9] border border-[#CBD5E1] text-[#334155] rounded-xl text-[13px] font-bold transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            <span>Refresh Telemetry</span>
          </button>
        </div>

        {/* Global KPIs */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-6">
          <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3.5">
            <div className="flex items-center justify-between text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
              <span>Organizations</span>
              <span>🏢</span>
            </div>
            <div className="text-2xl font-extrabold text-[#0F172A] font-mono mt-1">
              {metrics.total_organizations}
            </div>
          </div>

          <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3.5">
            <div className="flex items-center justify-between text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
              <span>Active Workspaces</span>
              <span>⚡</span>
            </div>
            <div className="text-2xl font-extrabold text-[#059669] font-mono mt-1">
              {metrics.active_organizations}
            </div>
          </div>

          <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3.5">
            <div className="flex items-center justify-between text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
              <span>Platform Users</span>
              <span>👥</span>
            </div>
            <div className="text-2xl font-extrabold text-[#2563EB] font-mono mt-1">
              {metrics.total_users}
            </div>
          </div>

          <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3.5">
            <div className="flex items-center justify-between text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
              <span>System Leads</span>
              <span>📋</span>
            </div>
            <div className="text-2xl font-extrabold text-[#0F172A] font-mono mt-1">
              {metrics.total_leads}
            </div>
          </div>

          <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3.5">
            <div className="flex items-center justify-between text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
              <span>Outreach Logs</span>
              <span>✉️</span>
            </div>
            <div className="text-2xl font-extrabold text-[#0F172A] font-mono mt-1">
              {metrics.total_campaign_logs}
            </div>
          </div>

          <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3.5">
            <div className="flex items-center justify-between text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
              <span>RAG Docs</span>
              <span>📚</span>
            </div>
            <div className="text-2xl font-extrabold text-[#7C3AED] font-mono mt-1">
              {metrics.total_kb_docs}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex bg-white border border-[#E2E8F0] rounded-xl p-1 shadow-xs max-w-md">
        <button
          type="button"
          onClick={() => setActiveTab("orgs")}
          className={`flex-1 py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
            activeTab === "orgs"
              ? "bg-[#2563EB] text-white shadow-xs"
              : "text-[#64748B] hover:text-[#0F172A]"
          }`}
        >
          🏢 All Organizations ({organizations.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("provision")}
          className={`flex-1 py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
            activeTab === "provision"
              ? "bg-[#2563EB] text-white shadow-xs"
              : "text-[#64748B] hover:text-[#0F172A]"
          }`}
        >
          ➕ Provision New Workspace
        </button>
      </div>

      {/* TAB 1: ALL ORGANIZATIONS */}
      {activeTab === "orgs" && (
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
            <h2 className="text-lg font-bold text-[#0F172A]">
              Registered Tenant Workspaces
            </h2>

            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 absolute left-3 top-3 text-[#94A3B8]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter by name or slug..."
                className="w-full pl-9 pr-3.5 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
              />
            </div>
          </div>

          <div className="space-y-3">
            {filteredOrgs.map((org) => {
              const isActive = org.status === "active";

              return (
                <div
                  key={org.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl gap-4 hover:border-[#CBD5E1] transition-all"
                >
                  <div className="flex items-center gap-3.5">
                    <div className="w-10 h-10 rounded-xl bg-[#EFF6FF] border border-[#BFDBFE] text-[#1D4ED8] flex items-center justify-center font-bold text-lg">
                      🏢
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[14.5px] font-bold text-[#0F172A]">{org.name}</span>
                        <span
                          className={`text-[10.5px] font-bold px-2 py-0.5 rounded ${
                            isActive
                              ? "bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]"
                              : "bg-[#FEF2F2] text-[#DC2626] border border-[#FECACA]"
                          }`}
                        >
                          ● {isActive ? "Active" : "Suspended"}
                        </span>
                      </div>
                      <div className="text-[12px] text-[#64748B] flex items-center gap-2 mt-0.5">
                        <span>Slug: <strong className="font-mono text-[#334155]">{org.slug}</strong></span>
                        <span>•</span>
                        <span className="font-mono text-[11px] text-[#94A3B8]">ID: {org.id.slice(0, 8)}...</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleToggleStatus(org.id, org.status)}
                      className={`px-3 py-1.5 rounded-lg text-[12px] font-bold transition-all border ${
                        isActive
                          ? "bg-white text-[#DC2626] border-[#FECACA] hover:bg-[#FEF2F2]"
                          : "bg-[#059669] text-white border-transparent hover:bg-[#047857]"
                      }`}
                    >
                      {isActive ? "Suspend Workspace" : "Activate Workspace"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 2: PROVISION NEW WORKSPACE */}
      {activeTab === "provision" && (
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs max-w-2xl">
          <h2 className="text-lg font-bold text-[#0F172A] mb-1">
            Provision New Tenant Workspace
          </h2>
          <p className="text-[13px] text-[#64748B] mb-5">
            Instantly set up an isolated tenant organization with dedicated AES-256 encrypted schema.
          </p>

          {provisionMessage && (
            <div className="mb-5 p-3.5 bg-[#F0FDF4] border border-[#BBF7D0] rounded-xl text-[13px] text-[#15803D] font-bold flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 shrink-0" />
              <span>{provisionMessage}</span>
            </div>
          )}

          <form onSubmit={handleProvision} className="space-y-4">
            <div>
              <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                Organization / Company Name *
              </label>
              <input
                type="text"
                required
                value={provOrgName}
                onChange={(e) => setProvOrgName(e.target.value)}
                placeholder="Acme Global Corporation"
                className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
              />
            </div>

            <div>
              <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                Primary Administrator Work Email *
              </label>
              <input
                type="email"
                required
                value={provAdminEmail}
                onChange={(e) => setProvAdminEmail(e.target.value)}
                placeholder="admin@acmeglobal.com"
                className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                  Administrator Name
                </label>
                <input
                  type="text"
                  value={provAdminName}
                  onChange={(e) => setProvAdminName(e.target.value)}
                  placeholder="Jane Doe"
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>

              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                  Initial Password *
                </label>
                <input
                  type="password"
                  required
                  value={provPassword}
                  onChange={(e) => setProvPassword(e.target.value)}
                  placeholder="Min 6 chars"
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isProvisioning}
                className="py-2.5 px-6 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13.5px] font-bold rounded-xl transition-all disabled:opacity-50"
              >
                {isProvisioning ? "Provisioning..." : "Provision Organization"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
