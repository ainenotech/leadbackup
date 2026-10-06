"use client";

import React, { useState, useEffect } from "react";
import {
  Settings,
  Globe,
  Mail,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Plus,
  Trash2,
  Save,
  Server,
  Key,
} from "lucide-react";
import { api, AuthOrganization, SendingDomain } from "@/lib/api";

interface WorkspaceSettingsViewProps {
  currentOrg: AuthOrganization | null;
  onSettingsUpdated?: () => void;
}

export default function WorkspaceSettingsView({
  currentOrg,
  onSettingsUpdated,
}: WorkspaceSettingsViewProps) {
  const [activeTab, setActiveTab] = useState<"general" | "channels" | "domains" | "compliance">("general");

  // General Settings State
  const [orgName, setOrgName] = useState(currentOrg?.name || "Neno Technology");
  const [senderName, setSenderName] = useState(
    currentOrg?.settings?.sender_name || "Mohit Patel"
  );
  const [senderEmail, setSenderEmail] = useState(
    currentOrg?.settings?.sender_email || "mohit@nenotechnology.us"
  );
  const [dailyLimit, setDailyLimit] = useState(
    currentOrg?.settings?.daily_limit || 250
  );
  const [replyTo, setReplyTo] = useState(
    currentOrg?.settings?.reply_to || "mohit@nenotechnology.us"
  );
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Channels / Detection State
  const [detectEmail, setDetectEmail] = useState(senderEmail);
  const [detectedChannel, setDetectedChannel] = useState<string | null>("microsoft_oauth");
  const [isDetecting, setIsDetecting] = useState(false);

  // Domains State
  const [domains, setDomains] = useState<SendingDomain[]>([]);
  const [isLoadingDomains, setIsLoadingDomains] = useState(false);
  const [newDomainInput, setNewDomainInput] = useState("");
  const [isAddingDomain, setIsAddingDomain] = useState(false);
  const [domainError, setDomainError] = useState<string | null>(null);
  const [domainSuccess, setDomainSuccess] = useState<string | null>(null);
  const [verifyingDomainId, setVerifyingDomainId] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const orgId = currentOrg?.id || "";

  // Load real domains for the active organization
  const fetchOrgDomains = async () => {
    if (!orgId) return;
    try {
      setIsLoadingDomains(true);
      const res = await api.getEmailDomains(orgId);
      setDomains(res);
    } catch (err: any) {
      console.warn("Failed to load domains:", err);
    } finally {
      setIsLoadingDomains(false);
    }
  };

  useEffect(() => {
    if (currentOrg) {
      setOrgName(currentOrg.name || "My Organization");
      if (currentOrg.settings) {
        if (currentOrg.settings.sender_name) setSenderName(currentOrg.settings.sender_name);
        if (currentOrg.settings.sender_email) setSenderEmail(currentOrg.settings.sender_email);
        if (currentOrg.settings.daily_limit) setDailyLimit(currentOrg.settings.daily_limit);
        if (currentOrg.settings.reply_to) setReplyTo(currentOrg.settings.reply_to);
      }
      fetchOrgDomains();
    }
  }, [currentOrg]);

  const handleSaveGeneral = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orgId) return;

    try {
      setIsSaving(true);
      setSaveSuccess(false);
      await api.updateOrgSettings(orgId, {
        name: orgName,
        sender_config: {
          sender_name: senderName,
          sender_email: senderEmail,
          daily_limit: dailyLimit,
          reply_to: replyTo,
        },
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 4000);
      if (onSettingsUpdated) onSettingsUpdated();
    } catch (err: any) {
      alert("Failed to save settings: " + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDetectChannel = () => {
    if (!detectEmail || !detectEmail.includes("@")) return;
    setIsDetecting(true);
    setTimeout(() => {
      const d = detectEmail.split("@")[1].toLowerCase();
      if (d.includes("gmail") || d.includes("google")) {
        setDetectedChannel("google_oauth");
      } else if (d.includes("outlook") || d.includes("microsoft")) {
        setDetectedChannel("microsoft_oauth");
      } else {
        setDetectedChannel("ses_aws");
      }
      setIsDetecting(false);
    }, 600);
  };

  const handleAddDomain = async (e: React.FormEvent) => {
    e.preventDefault();
    setDomainError(null);
    setDomainSuccess(null);
    if (!orgId) {
      setDomainError("No active organization found.");
      return;
    }
    const cleanDomain = newDomainInput.trim().toLowerCase().replace("https://", "").replace("http://", "").split("/")[0];
    if (!cleanDomain || !cleanDomain.includes(".")) {
      setDomainError("Please enter a valid domain (e.g. acme.com or outreach.acme.com)");
      return;
    }

    try {
      setIsAddingDomain(true);
      await api.addEmailDomain(orgId, cleanDomain);
      setDomainSuccess(`Domain ${cleanDomain} registered in AWS SES! Add the DNS records below to complete verification.`);
      setNewDomainInput("");
      await fetchOrgDomains();
    } catch (err: any) {
      setDomainError(err.message || "Failed to add domain to AWS SES");
    } finally {
      setIsAddingDomain(false);
    }
  };

  const handleVerifyDomain = async (domainId: string) => {
    setDomainError(null);
    setDomainSuccess(null);
    if (!orgId) return;

    try {
      setVerifyingDomainId(domainId);
      const res = await api.verifyEmailDomain(orgId, domainId);
      if (res.can_send || res.verification_status === "verified" || res.status === "verified") {
        setDomainSuccess(`Domain verified successfully! AWS SES high-deliverability sending is now ENABLED.`);
      } else {
        setDomainError("DNS records have not been detected yet. Please verify that the records were added correctly to your DNS provider and allow time for DNS propagation.");
      }
      await fetchOrgDomains();
    } catch (err: any) {
      setDomainError(err.message || "Verification check failed");
    } finally {
      setVerifyingDomainId(null);
    }
  };

  const handleToggleSending = async (domainId: string, currentCanSend: boolean) => {
    if (!orgId) return;
    try {
      await api.toggleDomainSending(orgId, domainId, !currentCanSend);
      await fetchOrgDomains();
    } catch (err: any) {
      alert("Failed to update sending state: " + err.message);
    }
  };

  const handleDeleteDomain = async (domainId: string, domainName: string) => {
    if (!orgId) return;
    if (!confirm(`Are you sure you want to remove ${domainName}? This will revoke AWS SES identity and stop outbound campaigns.`)) return;
    try {
      await api.deleteEmailDomain(orgId, domainId);
      await fetchOrgDomains();
    } catch (err: any) {
      alert("Failed to delete domain: " + err.message);
    }
  };

  const copyToClipboard = (text: string, key: string) => {
    if (navigator?.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header Banner */}
      <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5">
              <span className="text-2xl">⚙️</span>
              <h1 className="text-2xl font-extrabold text-[#0F172A] tracking-tight">
                Workspace &amp; Infrastructure Settings
              </h1>
            </div>
            <p className="text-[13.5px] text-[#64748B] max-w-2xl leading-relaxed">
              Configure outbound mailboxes, DNS authentication (SPF, DKIM, DMARC), email delivery gateways, and organization identity.
            </p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-1 shadow-xs max-w-xl mt-6">
          <button
            type="button"
            onClick={() => setActiveTab("general")}
            className={`flex-1 py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
              activeTab === "general"
                ? "bg-white text-[#0F172A] shadow-xs"
                : "text-[#64748B] hover:text-[#0F172A]"
            }`}
          >
            🏢 General Profile
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("channels")}
            className={`flex-1 py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
              activeTab === "channels"
                ? "bg-white text-[#0F172A] shadow-xs"
                : "text-[#64748B] hover:text-[#0F172A]"
            }`}
          >
            📬 Email Channels
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("domains")}
            className={`flex-1 py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
              activeTab === "domains"
                ? "bg-white text-[#0F172A] shadow-xs"
                : "text-[#64748B] hover:text-[#0F172A]"
            }`}
          >
            🌐 Sending Domains
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("compliance")}
            className={`flex-1 py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
              activeTab === "compliance"
                ? "bg-white text-[#0F172A] shadow-xs"
                : "text-[#64748B] hover:text-[#0F172A]"
            }`}
          >
            ⚖️ Compliance &amp; Footer
          </button>
        </div>
      </div>

      {/* TAB 1: GENERAL PROFILE */}
      {activeTab === "general" && (
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs max-w-3xl">
          <h2 className="text-lg font-bold text-[#0F172A] mb-1">
            Workspace Configuration
          </h2>
          <p className="text-[13px] text-[#64748B] mb-5">
            Default identity attached to outbound campaigns and team notifications.
          </p>

          {saveSuccess && (
            <div className="mb-5 p-3.5 bg-[#F0FDF4] border border-[#BBF7D0] rounded-xl text-[13px] text-[#15803D] font-bold flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 shrink-0" />
              <span>Workspace settings updated successfully!</span>
            </div>
          )}

          <form onSubmit={handleSaveGeneral} className="space-y-4">
            <div>
              <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                Company / Organization Name
              </label>
              <input
                type="text"
                required
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                  Default Sender Display Name
                </label>
                <input
                  type="text"
                  required
                  value={senderName}
                  onChange={(e) => setSenderName(e.target.value)}
                  placeholder="Mohit Patel"
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>

              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                  Active Outbound Mailbox Email
                </label>
                <input
                  type="email"
                  required
                  value={senderEmail}
                  onChange={(e) => setSenderEmail(e.target.value)}
                  placeholder="mohit@nenotechnology.us"
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                  Daily Outbound Send Cap
                </label>
                <input
                  type="number"
                  min="1"
                  max="5000"
                  value={dailyLimit}
                  onChange={(e) => setDailyLimit(parseInt(e.target.value) || 250)}
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>

              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                  Reply-To Email Address
                </label>
                <input
                  type="email"
                  value={replyTo}
                  onChange={(e) => setReplyTo(e.target.value)}
                  placeholder="mohit@nenotechnology.us"
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isSaving}
                className="py-2.5 px-6 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13.5px] font-bold rounded-xl shadow-xs transition-all flex items-center gap-2"
              >
                {isSaving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                <span>Save Workspace Settings</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* TAB 2: EMAIL DELIVERY CHANNELS */}
      {activeTab === "channels" && (
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs max-w-3xl space-y-6">
          <div>
            <h2 className="text-lg font-bold text-[#0F172A] mb-1">
              Outbound Email Channel Detection
            </h2>
            <p className="text-[13px] text-[#64748B]">
              Detect the optimal connection protocol (OAuth vs SMTP) based on your corporate email domain.
            </p>
          </div>

          <div className="flex gap-3">
            <input
              type="email"
              value={detectEmail}
              onChange={(e) => setDetectEmail(e.target.value)}
              placeholder="e.g. mohit@nenotechnology.us"
              className="flex-1 px-4 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
            />
            <button
              onClick={handleDetectChannel}
              disabled={isDetecting}
              className="py-2.5 px-5 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13px] font-bold rounded-xl transition-all disabled:opacity-50"
            >
              {isDetecting ? "Detecting DNS..." : "Detect Channel"}
            </button>
          </div>

          {detectedChannel && (
            <div className="p-4 bg-[#F8FAFC] border border-[#BFDBFE] rounded-xl space-y-4">
              <div className="flex items-center justify-between">
                <div className="text-[13px] font-bold text-[#0F172A]">
                  Recommended Connection:{" "}
                  <span className="text-[#2563EB] uppercase font-mono">{detectedChannel}</span>
                </div>
                <span className="bg-[#ECFDF5] text-[#059669] text-[11px] font-bold px-2 py-0.5 rounded">
                  ● Highest Deliverability
                </span>
              </div>

              {detectedChannel === "microsoft_oauth" && (
                <div className="space-y-3">
                  <div className="text-[12.5px] text-[#475569] leading-relaxed">
                    Connect your Microsoft 365 / Outlook mailbox securely using OAuth 2.0 without sharing raw passwords.
                  </div>
                  <a
                    href="http://localhost:8000/api/auth/oauth/microsoft/login"
                    className="inline-flex items-center gap-2 py-2.5 px-4 bg-[#0F172A] hover:bg-[#1E293B] text-white text-[13px] font-bold rounded-xl transition-all"
                  >
                    <span>🪟 Connect Microsoft 365 Mailbox</span>
                  </a>
                </div>
              )}

              {detectedChannel === "google_oauth" && (
                <div className="space-y-3">
                  <div className="text-[12.5px] text-[#475569] leading-relaxed">
                    Connect your Google Workspace mailbox securely using OAuth 2.0 with send &amp; reply sync.
                  </div>
                  <a
                    href="http://localhost:8000/api/auth/oauth/google/login"
                    className="inline-flex items-center gap-2 py-2.5 px-4 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13px] font-bold rounded-xl transition-all"
                  >
                    <span>🌐 Connect Google Workspace Mailbox</span>
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: SENDING DOMAINS & AWS SES DNS */}
      {activeTab === "domains" && (
        <div className="space-y-6">
          <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
              <div>
                <h2 className="text-lg font-bold text-[#0F172A] flex items-center gap-2">
                  <span>🌐</span>
                  <span>AWS SES Sending Domains &amp; DNS Verification</span>
                </h2>
                <p className="text-[13px] text-[#64748B] mt-0.5">
                  Verify arbitrary customer domains with AWS SES Easy DKIM. Works seamlessly with any DNS provider (Cloudflare, GoDaddy, Namecheap, Route53, etc.).
                </p>
              </div>

              {/* Add Domain Input */}
              <form onSubmit={handleAddDomain} className="flex gap-2">
                <input
                  type="text"
                  required
                  value={newDomainInput}
                  onChange={(e) => setNewDomainInput(e.target.value)}
                  placeholder="e.g. acme.com or mail.acme.com"
                  className="px-3.5 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB] min-w-[240px]"
                />
                <button
                  type="submit"
                  disabled={isAddingDomain}
                  className="py-2 px-4 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13px] font-bold rounded-xl flex items-center gap-1.5 transition-all disabled:opacity-50"
                >
                  <Plus className="w-4 h-4" />
                  <span>{isAddingDomain ? "Provisioning SES..." : "Add Domain"}</span>
                </button>
              </form>
            </div>

            {/* Error & Success Alerts */}
            {domainError && (
              <div className="mb-5 p-3.5 bg-[#FEF2F2] border border-[#FECACA] rounded-xl text-[12.5px] text-[#DC2626] font-medium flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-[#DC2626]" />
                  <span>{domainError}</span>
                </div>
                <button onClick={() => setDomainError(null)} className="text-[#DC2626] hover:underline font-bold text-[11.5px]">Dismiss</button>
              </div>
            )}

            {domainSuccess && (
              <div className="mb-5 p-3.5 bg-[#F0FDF4] border border-[#BBF7D0] rounded-xl text-[12.5px] text-[#15803D] font-medium flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-[#15803D]" />
                  <span>{domainSuccess}</span>
                </div>
                <button onClick={() => setDomainSuccess(null)} className="text-[#15803D] hover:underline font-bold text-[11.5px]">Dismiss</button>
              </div>
            )}

            {/* Universal DNS Provider Instructions Banner */}
            <div className="mb-6 p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl flex items-start gap-3">
              <span className="text-xl">💡</span>
              <div className="text-[12px] text-[#475569] leading-relaxed">
                <strong className="text-[#0F172A] block mb-0.5">Universal DNS Provider Support:</strong>
                Log in to your domain registrar or DNS hosting provider (<strong>GoDaddy, Cloudflare, Namecheap, Route 53, Hostinger, Squarespace, Bluehost</strong>, etc.), add the CNAME &amp; TXT records shown below, and click <strong>Verify DNS</strong>. Verification propagates worldwide within minutes.
              </div>
            </div>

            {/* Loading state */}
            {isLoadingDomains && (
              <div className="py-8 text-center text-[#64748B] text-[13px] flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-[#2563EB]" />
                <span>Loading sending domains...</span>
              </div>
            )}

            {/* Empty state */}
            {!isLoadingDomains && domains.length === 0 && (
              <div className="py-10 text-center border-2 border-dashed border-[#E2E8F0] rounded-xl">
                <Globe className="w-10 h-10 text-[#94A3B8] mx-auto mb-2 opacity-50" />
                <div className="text-[14px] font-bold text-[#0F172A]">No Sending Domains Configured</div>
                <p className="text-[12.5px] text-[#64748B] max-w-md mx-auto mt-1 mb-4">
                  Add your corporate or campaign sending domain above to generate AWS SES Easy DKIM verification records.
                </p>
              </div>
            )}

            {/* Domains List */}
            <div className="space-y-5">
              {domains.map((dom) => {
                const isVerified = dom.status === "verified" || dom.verification_status === "verified";
                const canSend = dom.can_send ?? isVerified;
                const isChecking = verifyingDomainId === dom.id;

                return (
                  <div key={dom.id} className="border border-[#E2E8F0] rounded-xl p-5 bg-[#F8FAFC]">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold ${
                          isVerified ? "bg-[#ECFDF5] text-[#059669]" : "bg-[#FEF3C7] text-[#D97706]"
                        }`}>
                          <Globe className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2.5">
                            <span className="text-[16px] font-extrabold text-[#0F172A] font-mono">{dom.domain}</span>
                            <span
                              className={`px-2.5 py-0.5 rounded-full font-bold text-[11px] ${
                                isVerified
                                  ? "bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]"
                                  : "bg-[#FEF3C7] text-[#D97706] border border-[#FDE68A]"
                              }`}
                            >
                              {isVerified ? "✓ VERIFIED" : "⏳ VERIFICATION PENDING"}
                            </span>
                            {isVerified && (
                              <span
                                className={`px-2.5 py-0.5 rounded-full font-bold text-[10.5px] cursor-pointer ${
                                  canSend
                                    ? "bg-[#EFF6FF] text-[#1D4ED8] border border-[#BFDBFE]"
                                    : "bg-[#F1F5F9] text-[#64748B] border border-[#CBD5E1]"
                                }`}
                                onClick={() => handleToggleSending(dom.id, canSend)}
                                title="Click to toggle sending"
                              >
                                {canSend ? "⚡ SES SENDING ENABLED" : "⏸️ SENDING PAUSED"}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-3 text-[11.5px] mt-1 text-[#64748B]">
                            {dom.ses_identity_arn && (
                              <span className="truncate max-w-xs font-mono text-[10.5px]">ARN: {dom.ses_identity_arn}</span>
                            )}
                            {dom.reputation_score !== undefined && (
                              <span>Reputation: <strong className="text-[#059669] font-mono">{dom.reputation_score}%</strong></span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleVerifyDomain(dom.id)}
                          disabled={isChecking}
                          className="py-1.5 px-3.5 bg-white border border-[#CBD5E1] hover:bg-[#F1F5F9] rounded-lg text-[12px] font-bold text-[#334155] flex items-center gap-1.5 shadow-xs transition-all disabled:opacity-50"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${isChecking ? "animate-spin text-[#2563EB]" : ""}`} />
                          <span>{isChecking ? "Checking SES..." : "Check Verification"}</span>
                        </button>

                        <button
                          onClick={() => handleDeleteDomain(dom.id, dom.domain)}
                          title="Delete Domain"
                          className="p-1.5 text-[#94A3B8] hover:text-[#DC2626] hover:bg-white rounded-lg transition-all"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* DNS Records Table */}
                    <div className="bg-white rounded-xl border border-[#E2E8F0] overflow-hidden text-[12px] shadow-xs">
                      <div className="grid grid-cols-12 bg-[#F1F5F9] px-4 py-2 font-bold text-[#475569] uppercase tracking-wider text-[10.5px]">
                        <div className="col-span-2">Record Type</div>
                        <div className="col-span-4">Host / Name</div>
                        <div className="col-span-4">Value / Target</div>
                        <div className="col-span-2 text-right">Status</div>
                      </div>

                      {dom.records && dom.records.length > 0 ? (
                        dom.records.map((rec, rIdx) => {
                          const hostKey = `${dom.id}_host_${rIdx}`;
                          const valKey = `${dom.id}_val_${rIdx}`;
                          const recType = rec.record_type || rec.type || "CNAME";
                          const recHost = rec.host || rec.name || "@";
                          const recVal = rec.value || "";

                          return (
                            <div
                              key={rIdx}
                              className="grid grid-cols-12 px-4 py-3 border-t border-[#F1F5F9] items-center text-[12px] hover:bg-[#F8FAFC]"
                            >
                              <div className="col-span-2 font-mono font-bold text-[#0F172A]">{recType}</div>
                              <div className="col-span-4 font-mono text-[#334155] flex items-center gap-1.5 pr-2">
                                <span className="truncate" title={recHost}>{recHost}</span>
                                <button
                                  type="button"
                                  onClick={() => copyToClipboard(recHost, hostKey)}
                                  className="text-[10px] text-[#2563EB] hover:underline font-sans shrink-0 px-1 py-0.5 rounded bg-[#EFF6FF]"
                                >
                                  {copiedKey === hostKey ? "Copied!" : "Copy"}
                                </button>
                              </div>
                              <div className="col-span-4 font-mono text-[#334155] flex items-center gap-1.5 pr-2">
                                <span className="truncate" title={recVal}>{recVal}</span>
                                <button
                                  type="button"
                                  onClick={() => copyToClipboard(recVal, valKey)}
                                  className="text-[10px] text-[#2563EB] hover:underline font-sans shrink-0 px-1 py-0.5 rounded bg-[#EFF6FF]"
                                >
                                  {copiedKey === valKey ? "Copied!" : "Copy"}
                                </button>
                              </div>
                              <div className="col-span-2 text-right">
                                <span
                                  className={`px-2 py-0.5 rounded text-[10.5px] font-bold ${
                                    rec.status === "verified" || isVerified
                                      ? "bg-[#ECFDF5] text-[#059669]"
                                      : "bg-[#FEF3C7] text-[#D97706]"
                                  }`}
                                >
                                  {rec.status === "verified" || isVerified ? "✓ Verified" : "Pending"}
                                </span>
                              </div>
                            </div>
                          );
                        })
                      ) : (
                        <div className="p-4 text-center text-[#64748B] text-[12px]">
                          Generating DKIM &amp; MAIL FROM tokens from AWS SES... Click Check Verification in a few moments.
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: COMPLIANCE & FOOTER */}
      {activeTab === "compliance" && (
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs max-w-3xl">
          <h2 className="text-lg font-bold text-[#0F172A] mb-1">
            CAN-SPAM &amp; GDPR Compliance Footer
          </h2>
          <p className="text-[13px] text-[#64748B] mb-5">
            Automatically appended to every dispatched email draft to maintain pristine sender reputation.
          </p>

          <div className="space-y-4">
            <div>
              <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                Unsubscribe Instructions Text
              </label>
              <textarea
                rows={3}
                defaultValue="If you prefer not to receive future communications, please reply with 'Unsubscribe' or click the opt-out link below."
                className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
              />
            </div>

            <div>
              <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                Company Physical Mailing Address
              </label>
              <input
                type="text"
                defaultValue="Neno Technology LLC · 100 Enterprise Blvd, Suite 400"
                className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
              />
            </div>

            <div className="pt-2">
              <button
                type="button"
                onClick={() => alert("Compliance footer saved.")}
                className="py-2.5 px-6 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13.5px] font-bold rounded-xl transition-all"
              >
                Save Compliance Settings
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
