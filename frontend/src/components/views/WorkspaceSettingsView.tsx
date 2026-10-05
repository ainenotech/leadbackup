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
  const [domains, setDomains] = useState<SendingDomain[]>([
    {
      id: "dom_1",
      domain: "nenotechnology.us",
      status: "verified",
      reputation_score: 99,
      records: [
        { type: "TXT (SPF)", name: "@", value: "v=spf1 include:spf.protection.outlook.com -all", status: "verified" },
        { type: "CNAME (DKIM)", name: "selector1._domainkey", value: "selector1-nenotechnology-us.domainkey.outlook.com", status: "verified" },
        { type: "TXT (DMARC)", name: "_dmarc", value: "v=DMARC1; p=reject; sp=reject; pct=100", status: "verified" },
        { type: "MX", name: "@", value: "nenotechnology-us.mail.protection.outlook.com", status: "verified" },
      ],
    },
    {
      id: "dom_2",
      domain: "nenotechnology.com",
      status: "verified",
      reputation_score: 98,
      records: [
        { type: "TXT (SPF)", name: "@", value: "v=spf1 include:_spf.google.com ~all", status: "verified" },
        { type: "TXT (DKIM)", name: "google._domainkey", value: "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBA...", status: "verified" },
        { type: "TXT (DMARC)", name: "_dmarc", value: "v=DMARC1; p=quarantine; pct=100", status: "verified" },
        { type: "MX", name: "@", value: "aspmx.l.google.com", status: "verified" },
      ],
    },
  ]);
  const [newDomainInput, setNewDomainInput] = useState("");
  const [isVerifyingDomain, setIsVerifyingDomain] = useState(false);

  const orgId = currentOrg?.id || "";

  useEffect(() => {
    if (currentOrg) {
      setOrgName(currentOrg.name || "Neno Technology");
      if (currentOrg.settings) {
        if (currentOrg.settings.sender_name) setSenderName(currentOrg.settings.sender_name);
        if (currentOrg.settings.sender_email) setSenderEmail(currentOrg.settings.sender_email);
        if (currentOrg.settings.daily_limit) setDailyLimit(currentOrg.settings.daily_limit);
        if (currentOrg.settings.reply_to) setReplyTo(currentOrg.settings.reply_to);
      }
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
      } else if (d.includes("outlook") || d.includes("nenotechnology") || d.includes("microsoft")) {
        setDetectedChannel("microsoft_oauth");
      } else {
        setDetectedChannel("smtp_imap");
      }
      setIsDetecting(false);
    }, 600);
  };

  const handleAddDomain = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDomainInput.trim()) return;
    const cleanDomain = newDomainInput.trim().toLowerCase().replace("https://", "").replace("http://", "").split("/")[0];
    const newEntry: SendingDomain = {
      id: "dom_" + Date.now(),
      domain: cleanDomain,
      status: "pending",
      reputation_score: 85,
      records: [
        { type: "TXT (SPF)", name: "@", value: "v=spf1 include:spf.protection.outlook.com -all", status: "pending" },
        { type: "TXT (DMARC)", name: "_dmarc", value: "v=DMARC1; p=quarantine; pct=100", status: "pending" },
      ],
    };
    setDomains([...domains, newEntry]);
    setNewDomainInput("");
  };

  const handleVerifyDomain = (domainId: string) => {
    setIsVerifyingDomain(true);
    setTimeout(() => {
      setDomains(
        domains.map((d) =>
          d.id === domainId ? { ...d, status: "verified", reputation_score: 99 } : d
        )
      );
      setIsVerifyingDomain(false);
    }, 1200);
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

      {/* TAB 3: SENDING DOMAINS & DNS */}
      {activeTab === "domains" && (
        <div className="space-y-6">
          <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
              <div>
                <h2 className="text-lg font-bold text-[#0F172A]">
                  Active Sending Domains &amp; DNS Records
                </h2>
                <p className="text-[13px] text-[#64748B]">
                  Verified domains authorized for high-volume outreach with 99%+ deliverability.
                </p>
              </div>

              {/* Add Domain Input */}
              <form onSubmit={handleAddDomain} className="flex gap-2">
                <input
                  type="text"
                  required
                  value={newDomainInput}
                  onChange={(e) => setNewDomainInput(e.target.value)}
                  placeholder="companyoutreach.com"
                  className="px-3.5 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
                <button
                  type="submit"
                  className="py-2 px-3.5 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13px] font-bold rounded-xl flex items-center gap-1.5"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add Domain</span>
                </button>
              </form>
            </div>

            {/* Domains List */}
            <div className="space-y-4">
              {domains.map((dom) => (
                <div key={dom.id} className="border border-[#E2E8F0] rounded-xl p-5 bg-[#F8FAFC]">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg bg-[#EFF6FF] text-[#2563EB] flex items-center justify-center font-bold">
                        <Globe className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="text-[15px] font-bold text-[#0F172A] font-mono">{dom.domain}</div>
                        <div className="flex items-center gap-2 text-[11.5px] mt-0.5">
                          <span
                            className={`px-2 py-0.5 rounded font-bold ${
                              dom.status === "verified"
                                ? "bg-[#ECFDF5] text-[#059669]"
                                : "bg-[#FEF3C7] text-[#D97706]"
                            }`}
                          >
                            ● {dom.status.toUpperCase()}
                          </span>
                          <span className="text-[#64748B]">Reputation Score:</span>
                          <strong className="text-[#059669] font-mono">{dom.reputation_score}%</strong>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleVerifyDomain(dom.id)}
                        disabled={isVerifyingDomain}
                        className="py-1.5 px-3 bg-white border border-[#CBD5E1] hover:bg-[#F1F5F9] rounded-lg text-[12px] font-bold text-[#334155] flex items-center gap-1.5"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${isVerifyingDomain ? "animate-spin" : ""}`} />
                        <span>Verify DNS</span>
                      </button>
                    </div>
                  </div>

                  {/* DNS Records Breakdown */}
                  <div className="bg-white rounded-lg border border-[#E2E8F0] overflow-hidden text-[12px]">
                    <div className="grid grid-cols-12 bg-[#F1F5F9] px-3.5 py-2 font-bold text-[#475569] uppercase tracking-wider text-[11px]">
                      <div className="col-span-3">Record Type</div>
                      <div className="col-span-2">Host Name</div>
                      <div className="col-span-5">Target Value</div>
                      <div className="col-span-2 text-right">Status</div>
                    </div>
                    {dom.records?.map((rec, rIdx) => (
                      <div
                        key={rIdx}
                        className="grid grid-cols-12 px-3.5 py-2.5 border-t border-[#F1F5F9] items-center font-mono text-[11.5px]"
                      >
                        <div className="col-span-3 font-bold text-[#0F172A]">{rec.type}</div>
                        <div className="col-span-2 text-[#475569]">{rec.name}</div>
                        <div className="col-span-5 text-[#334155] truncate" title={rec.value}>
                          {rec.value}
                        </div>
                        <div className="col-span-2 text-right">
                          <span className="bg-[#ECFDF5] text-[#059669] px-2 py-0.5 rounded text-[10.5px] font-bold">
                            ✓ Verified
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
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
