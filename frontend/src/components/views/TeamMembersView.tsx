"use client";

import React, { useState, useEffect } from "react";
import {
  Users,
  UserPlus,
  Shield,
  Trash2,
  Mail,
  CheckCircle2,
  AlertCircle,
  Settings,
  RefreshCw,
} from "lucide-react";
import { api, TeamMember, AuthUser, AuthOrganization } from "@/lib/api";

interface TeamMembersViewProps {
  currentOrg: AuthOrganization | null;
  currentUser: AuthUser | null;
  onNavigateToSettings: () => void;
}

const ROLES = [
  { id: "organization_owner", label: "👑 Organization Owner", desc: "Full administrative and billing access" },
  { id: "organization_admin", label: "🛡️ Organization Admin", desc: "Manage members, channels, and campaigns" },
  { id: "campaign_manager", label: "🚀 Campaign Manager", desc: "Create, review, and approve email outreach" },
  { id: "sales_user", label: "💼 Sales User", desc: "View leads, replies, and book consultations" },
  { id: "regular_user", label: "👤 Regular Member", desc: "Standard workspace pipeline access" },
  { id: "viewer", label: "👁️ Viewer (Read Only)", desc: "Read-only access across telemetry and analytics" },
];

export default function TeamMembersView({
  currentOrg,
  currentUser,
  onNavigateToSettings,
}: TeamMembersViewProps) {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showInviteModal, setShowInviteModal] = useState(false);

  // Invite Form
  const [invEmail, setInvEmail] = useState("");
  const [invName, setInvName] = useState("");
  const [invRole, setInvRole] = useState("regular_user");
  const [invPassword, setInvPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const orgId = currentOrg?.id || "";

  const loadMembers = async () => {
    if (!orgId) return;
    try {
      setIsLoading(true);
      const data = await api.getOrgMembers(orgId);
      setMembers(data);
    } catch (e: any) {
      console.warn("Failed to load members:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMembers();
  }, [orgId]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!invEmail || !orgId) return;

    try {
      setIsSubmitting(true);
      setFeedback(null);
      await api.inviteOrgMember(orgId, {
        email: invEmail.trim(),
        full_name: invName.trim() || undefined,
        role: invRole,
        temporary_password: invPassword || undefined,
      });

      setFeedback({
        type: "success",
        text: `Successfully invited ${invEmail} as ${invRole}!`,
      });
      setInvEmail("");
      setInvName("");
      setInvPassword("");
      setShowInviteModal(false);
      await loadMembers();
    } catch (err: any) {
      setFeedback({
        type: "error",
        text: err.message || "Failed to invite colleague.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    if (!orgId) return;
    try {
      await api.updateMemberRole(orgId, userId, newRole);
      await loadMembers();
    } catch (err: any) {
      alert("Failed to update role: " + err.message);
    }
  };

  const handleRemove = async (userId: string, email: string) => {
    if (!orgId) return;
    if (!confirm(`Are you sure you want to remove ${email} from this workspace?`)) return;
    try {
      await api.removeOrgMember(orgId, userId);
      await loadMembers();
    } catch (err: any) {
      alert("Failed to remove member: " + err.message);
    }
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case "organization_owner":
        return <span className="bg-[#EFF6FF] text-[#1D4ED8] border border-[#BFDBFE] text-[11px] font-bold px-2 py-0.5 rounded">👑 Owner</span>;
      case "organization_admin":
        return <span className="bg-[#F5F3FF] text-[#7C3AED] border border-[#DDD6FE] text-[11px] font-bold px-2 py-0.5 rounded">🛡️ Admin</span>;
      case "campaign_manager":
        return <span className="bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0] text-[11px] font-bold px-2 py-0.5 rounded">🚀 Manager</span>;
      case "sales_user":
        return <span className="bg-[#FEF3C7] text-[#D97706] border border-[#FDE68A] text-[11px] font-bold px-2 py-0.5 rounded">💼 Sales</span>;
      default:
        return <span className="bg-[#F1F5F9] text-[#475569] border border-[#CBD5E1] text-[11px] font-bold px-2 py-0.5 rounded">👤 Member</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header Banner */}
      <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5">
              <span className="text-2xl">👥</span>
              <h1 className="text-2xl font-extrabold text-[#0F172A] tracking-tight">
                Team Members &amp; Access Controls
              </h1>
            </div>
            <p className="text-[13.5px] text-[#64748B] max-w-2xl leading-relaxed">
              Manage workspace permissions, assign role-based access control (RBAC), and collaborate with team members across campaigns and leads.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onNavigateToSettings}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-[#F8FAFC] hover:bg-[#F1F5F9] border border-[#CBD5E1] text-[#334155] rounded-xl text-[13px] font-bold transition-all"
            >
              <Settings className="w-4 h-4" />
              <span>Workspace Settings</span>
            </button>

            <button
              onClick={() => setShowInviteModal(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-xl text-[13px] font-bold shadow-xs transition-all"
            >
              <UserPlus className="w-4 h-4" />
              <span>Invite Colleague</span>
            </button>
          </div>
        </div>

        {/* Quick Stats Strip */}
        <div className="flex items-center gap-6 mt-6 pt-5 border-t border-[#F1F5F9] text-[13px]">
          <div>
            <span className="text-[#64748B]">Active Workspace: </span>
            <strong className="text-[#0F172A]">{currentOrg?.name || "Neno Technology"}</strong>
          </div>
          <div>
            <span className="text-[#64748B]">Total Members: </span>
            <strong className="text-[#2563EB] font-mono">{members.length}</strong>
          </div>
        </div>
      </div>

      {feedback && (
        <div
          className={`p-4 rounded-xl border text-[13px] font-medium flex items-center gap-2.5 ${
            feedback.type === "success"
              ? "bg-[#F0FDF4] border-[#BBF7D0] text-[#15803D]"
              : "bg-[#FEF2F2] border-[#FECACA] text-[#DC2626]"
          }`}
        >
          {feedback.type === "success" ? <CheckCircle2 className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
          <span>{feedback.text}</span>
        </div>
      )}

      {/* Invite Member Drawer / Form */}
      {showInviteModal && (
        <div className="bg-white border border-[#2563EB]/30 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-[#0F172A] flex items-center gap-2">
              <UserPlus className="w-5 h-5 text-[#2563EB]" />
              <span>Invite New Team Member</span>
            </h2>
            <button
              onClick={() => setShowInviteModal(false)}
              className="text-[#94A3B8] hover:text-[#0F172A] text-[13px] font-bold"
            >
              ✕ Close
            </button>
          </div>

          <form onSubmit={handleInvite} className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div>
              <label className="block text-[12.5px] font-bold text-[#0F172A] mb-1">
                Colleague Work Email *
              </label>
              <input
                type="email"
                required
                value={invEmail}
                onChange={(e) => setInvEmail(e.target.value)}
                placeholder="alex@company.com"
                className="w-full px-3.5 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
              />
            </div>

            <div>
              <label className="block text-[12.5px] font-bold text-[#0F172A] mb-1">
                Full Name
              </label>
              <input
                type="text"
                value={invName}
                onChange={(e) => setInvName(e.target.value)}
                placeholder="Alex Rivera"
                className="w-full px-3.5 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
              />
            </div>

            <div>
              <label className="block text-[12.5px] font-bold text-[#0F172A] mb-1">
                Workspace Role *
              </label>
              <select
                value={invRole}
                onChange={(e) => setInvRole(e.target.value)}
                className="w-full px-3.5 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
              >
                {ROLES.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-end">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2 px-4 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13px] font-bold rounded-xl shadow-xs transition-all disabled:opacity-50"
              >
                {isSubmitting ? "Inviting..." : "Send Invitation"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Members Table */}
      <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs">
        <h2 className="text-lg font-bold text-[#0F172A] mb-4">
          Current Workspace Roster
        </h2>

        {isLoading ? (
          <div className="text-center py-10 text-[13px] text-[#64748B]">Loading members...</div>
        ) : members.length === 0 ? (
          <div className="text-center py-10 border border-dashed border-[#CBD5E1] rounded-xl">
            <Users className="w-8 h-8 text-[#94A3B8] mx-auto mb-2" />
            <div className="text-[14px] font-bold text-[#334155]">No members found</div>
          </div>
        ) : (
          <div className="divide-y divide-[#F1F5F9]">
            {members.map((m) => {
              const initials = (m.full_name || m.email || "U")
                .split(" ")
                .map((n) => n[0])
                .slice(0, 2)
                .join("")
                .toUpperCase();

              const isSelf = currentUser?.id === m.user_id;

              return (
                <div key={m.user_id} className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3.5">
                    <div className="w-10 h-10 rounded-full bg-[#EFF6FF] border border-[#BFDBFE] text-[#1D4ED8] font-bold text-[13px] flex items-center justify-center shrink-0">
                      {initials}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[14px] font-bold text-[#0F172A]">
                          {m.full_name || m.email.split("@")[0]}
                        </span>
                        {isSelf && (
                          <span className="bg-[#F1F5F9] text-[#64748B] text-[10px] font-bold px-1.5 py-0.5 rounded">
                            You
                          </span>
                        )}
                        {m.is_default && (
                          <span className="bg-[#EFF6FF] text-[#2563EB] text-[10px] font-bold px-1.5 py-0.5 rounded">
                            Primary
                          </span>
                        )}
                      </div>
                      <div className="text-[12px] text-[#64748B]">{m.email}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {/* Role Dropdown */}
                    <div className="flex items-center gap-2">
                      {getRoleBadge(m.role)}
                      <select
                        value={m.role}
                        onChange={(e) => handleRoleChange(m.user_id, e.target.value)}
                        className="text-[12px] bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg px-2 py-1 text-[#334155] focus:outline-none focus:border-[#2563EB]"
                      >
                        {ROLES.map((r) => (
                          <option key={r.id} value={r.id}>
                            {r.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    {!isSelf && (
                      <button
                        onClick={() => handleRemove(m.user_id, m.email)}
                        className="p-1.5 text-[#EF4444] hover:bg-[#FEF2F2] rounded-lg transition-all"
                        title="Remove member"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
