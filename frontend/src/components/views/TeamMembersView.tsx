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
  Eye,
  Smartphone,
  Monitor,
  Key,
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

  // Invite Form State
  const [invEmail, setInvEmail] = useState("");
  const [invName, setInvName] = useState("");
  const [invRole, setInvRole] = useState("regular_user");
  const [invPassword, setInvPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Resend State
  const [resendingUserId, setResendingUserId] = useState<string | null>(null);

  // Template Preview Modal State
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewDevice, setPreviewDevice] = useState<"desktop" | "mobile">("desktop");
  const [previewData, setPreviewData] = useState<{
    subject: string;
    html: string;
    text: string;
    org_name?: string;
    inviter_name?: string;
  } | null>(null);

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
      const res = await api.inviteOrgMember(orgId, {
        email: invEmail.trim(),
        full_name: invName.trim() || undefined,
        role: invRole,
        temporary_password: invPassword || undefined,
      });

      const emailSent = res?.data?.email_sent;
      setFeedback({
        type: "success",
        text: emailSent
          ? `🎉 Successfully invited ${invEmail.trim()} as ${invRole}! An invitation email has been sent to their inbox.`
          : `🎉 Successfully invited ${invEmail.trim()} as ${invRole}! Invitation email has been triggered.`,
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

  const handleResendInvite = async (userId: string, email: string) => {
    if (!orgId) return;
    try {
      setResendingUserId(userId);
      setFeedback(null);
      const res = await api.resendOrgMemberInvite(orgId, userId);
      setFeedback({
        type: "success",
        text: `✉️ Invitation email resent to ${email}!`,
      });
    } catch (err: any) {
      setFeedback({
        type: "error",
        text: err.message || `Failed to resend invitation email to ${email}.`,
      });
    } finally {
      setResendingUserId(null);
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

  const openPreview = async (email?: string, name?: string, role?: string) => {
    if (!orgId) return;
    try {
      setShowPreviewModal(true);
      setPreviewLoading(true);
      const data = await api.getInvitationPreview(orgId, {
        email: email || invEmail || "colleague@company.com",
        name: name || invName || "Alex Rivera",
        role: role || invRole || "regular_user",
      });
      setPreviewData(data);
    } catch (err: any) {
      console.warn("Failed to load invitation preview:", err);
    } finally {
      setPreviewLoading(false);
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

          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => openPreview()}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-[#EFF6FF] hover:bg-[#DBEAFE] border border-[#BFDBFE] text-[#1D4ED8] rounded-xl text-[13px] font-bold transition-all"
              title="Preview the exact email template that invitees receive"
            >
              <Eye className="w-4 h-4" />
              <span>Preview Email Template</span>
            </button>

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
            <strong className="text-[#0F172A]">{currentOrg?.name || "Nenotechnology"}</strong>
          </div>
          <div>
            <span className="text-[#64748B]">Total Members: </span>
            <strong className="text-[#2563EB] font-mono">{members.length}</strong>
          </div>
          <div className="text-[12px] text-[#059669] flex items-center gap-1.5 font-medium ml-auto">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Automatic Invitation Delivery Active</span>
          </div>
        </div>
      </div>

      {feedback && (
        <div
          className={`p-4 rounded-xl border text-[13px] font-medium flex items-center justify-between gap-2.5 ${
            feedback.type === "success"
              ? "bg-[#F0FDF4] border-[#BBF7D0] text-[#15803D]"
              : "bg-[#FEF2F2] border-[#FECACA] text-[#DC2626]"
          }`}
        >
          <div className="flex items-center gap-2.5">
            {feedback.type === "success" ? <CheckCircle2 className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
            <span>{feedback.text}</span>
          </div>
          <button onClick={() => setFeedback(null)} className="text-[12px] opacity-70 hover:opacity-100 font-bold">
            ✕
          </button>
        </div>
      )}

      {/* Invite Member Drawer / Form */}
      {showInviteModal && (
        <div className="bg-white border border-[#2563EB]/40 rounded-2xl p-6 shadow-md transition-all">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#EFF6FF] border border-[#BFDBFE] flex items-center justify-center text-[#2563EB]">
                <UserPlus className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-base font-bold text-[#0F172A]">Invite New Team Member</h2>
                <p className="text-[12px] text-[#64748B]">
                  An onboarding invitation email with access credentials will be delivered immediately.
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowInviteModal(false)}
              className="text-[#94A3B8] hover:text-[#0F172A] text-[13px] font-bold p-1"
            >
              ✕ Close
            </button>
          </div>

          <form onSubmit={handleInvite} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>

              <div>
                <label className="block text-[12.5px] font-bold text-[#0F172A] mb-1">
                  Full Name (Optional)
                </label>
                <input
                  type="text"
                  value={invName}
                  onChange={(e) => setInvName(e.target.value)}
                  placeholder="Alex Rivera"
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>

              <div>
                <label className="block text-[12.5px] font-bold text-[#0F172A] mb-1">
                  Workspace Role *
                </label>
                <select
                  value={invRole}
                  onChange={(e) => setInvRole(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                >
                  {ROLES.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
              <div>
                <label className="block text-[12.5px] font-bold text-[#0F172A] mb-1">
                  Temporary Password (Optional)
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={invPassword}
                    onChange={(e) => setInvPassword(e.target.value)}
                    placeholder="Defaults to Welcome@2026!"
                    className="w-full pl-9 pr-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] font-mono focus:outline-none focus:border-[#2563EB]"
                  />
                  <Key className="w-4 h-4 text-[#94A3B8] absolute left-3 top-3" />
                </div>
                <span className="text-[11px] text-[#64748B] mt-1 block">
                  Included securely in the invitation email for first-time login.
                </span>
              </div>

              <div className="sm:col-span-2 flex items-end justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => openPreview(invEmail, invName, invRole)}
                  className="py-2.5 px-4 bg-[#EFF6FF] hover:bg-[#DBEAFE] text-[#1D4ED8] border border-[#BFDBFE] text-[13px] font-bold rounded-xl transition-all inline-flex items-center gap-1.5"
                >
                  <Eye className="w-4 h-4" />
                  <span>Preview Email Template</span>
                </button>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="py-2.5 px-6 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13px] font-bold rounded-xl shadow-xs transition-all disabled:opacity-50 inline-flex items-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Sending Invitation Email...</span>
                    </>
                  ) : (
                    <>
                      <Mail className="w-4 h-4" />
                      <span>Send Workspace Invitation</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>
        </div>
      )}

      {/* Members Table */}
      <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-[#0F172A]">
            Current Workspace Roster
          </h2>
          <span className="text-[12px] text-[#64748B]">
            Showing all active members and invitees
          </span>
        </div>

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
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleResendInvite(m.user_id, m.email)}
                          disabled={resendingUserId === m.user_id}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-bold text-[#2563EB] bg-[#EFF6FF] hover:bg-[#DBEAFE] border border-[#BFDBFE] rounded-lg transition-all disabled:opacity-50"
                          title="Resend invitation email"
                        >
                          {resendingUserId === m.user_id ? (
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Mail className="w-3.5 h-3.5" />
                          )}
                          <span>Resend Invite</span>
                        </button>

                        <button
                          onClick={() => handleRemove(m.user_id, m.email)}
                          className="p-1.5 text-[#EF4444] hover:bg-[#FEF2F2] rounded-lg transition-all"
                          title="Remove member"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Live Email Template Preview Modal */}
      {showPreviewModal && (
        <div className="fixed inset-0 z-50 bg-[#0F172A]/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[92vh] flex flex-col overflow-hidden border border-[#CBD5E1] animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-[#E2E8F0] flex items-center justify-between bg-[#F8FAFC]">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-[#EFF6FF] border border-[#BFDBFE] flex items-center justify-center text-[#2563EB]">
                  <Mail className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-extrabold text-[#0F172A]">
                    Workspace Invitation Email Template
                  </h3>
                  <p className="text-[12px] text-[#64748B]">
                    Live preview of the responsive HTML email template dispatched to invitees.
                  </p>
                </div>
              </div>

              {/* Device Viewport Toggle & Close */}
              <div className="flex items-center gap-3">
                <div className="flex items-center bg-[#E2E8F0] p-0.5 rounded-lg text-[12px] font-bold">
                  <button
                    onClick={() => setPreviewDevice("desktop")}
                    className={`px-3 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                      previewDevice === "desktop"
                        ? "bg-white text-[#0F172A] shadow-xs"
                        : "text-[#64748B] hover:text-[#0F172A]"
                    }`}
                  >
                    <Monitor className="w-3.5 h-3.5" />
                    <span>Desktop</span>
                  </button>
                  <button
                    onClick={() => setPreviewDevice("mobile")}
                    className={`px-3 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                      previewDevice === "mobile"
                        ? "bg-white text-[#0F172A] shadow-xs"
                        : "text-[#64748B] hover:text-[#0F172A]"
                    }`}
                  >
                    <Smartphone className="w-3.5 h-3.5" />
                    <span>Mobile</span>
                  </button>
                </div>

                <button
                  onClick={() => setShowPreviewModal(false)}
                  className="w-8 h-8 rounded-lg hover:bg-[#E2E8F0] text-[#64748B] hover:text-[#0F172A] flex items-center justify-center font-bold text-sm"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Subject Line & Meta Bar */}
            {previewData && (
              <div className="px-6 py-3 bg-[#EFF6FF]/70 border-b border-[#BFDBFE]/70 text-[12.5px] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2 truncate">
                  <span className="font-bold text-[#1E40AF]">Subject:</span>
                  <span className="text-[#1E293B] font-semibold truncate">{previewData.subject}</span>
                </div>
                <div className="flex items-center gap-2 text-[11.5px] text-[#475569] shrink-0">
                  <span className="bg-white border border-[#CBD5E1] px-2.5 py-0.5 rounded-md font-mono">
                    Sender: Microsoft Graph (mohit@nenotechnology.us)
                  </span>
                </div>
              </div>
            )}

            {/* Email Iframe Canvas */}
            <div className="flex-1 overflow-auto bg-[#E2E8F0]/50 p-4 sm:p-6 flex justify-center items-start">
              {previewLoading ? (
                <div className="flex flex-col items-center justify-center py-24 text-[#64748B] gap-3">
                  <RefreshCw className="w-8 h-8 animate-spin text-[#2563EB]" />
                  <span className="text-sm font-semibold">Generating invitation template preview...</span>
                </div>
              ) : previewData ? (
                <div
                  className={`transition-all bg-white rounded-xl shadow-lg border border-[#CBD5E1] overflow-hidden ${
                    previewDevice === "desktop" ? "w-[620px] max-w-full" : "w-[390px] max-w-full"
                  }`}
                  style={{ height: "580px" }}
                >
                  <iframe
                    srcDoc={previewData.html}
                    title="Invitation Preview"
                    className="w-full h-full border-0"
                    sandbox="allow-same-origin allow-popups"
                  />
                </div>
              ) : (
                <div className="text-center py-14 text-sm text-[#64748B]">Unable to load email template</div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3.5 border-t border-[#E2E8F0] bg-white flex items-center justify-between">
              <div className="text-[12px] text-[#64748B] flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#10B981]"></span>
                <span>Optimized for Microsoft Outlook, Gmail, Apple Mail, and mobile inboxes.</span>
              </div>
              <button
                onClick={() => setShowPreviewModal(false)}
                className="px-4 py-2 bg-[#F1F5F9] hover:bg-[#E2E8F0] text-[#0F172A] rounded-xl text-[13px] font-bold transition-all"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
