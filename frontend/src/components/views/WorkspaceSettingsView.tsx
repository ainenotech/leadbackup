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
  Users,
  Search,
  Check,
  X,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Sliders,
  Zap,
  Info,
} from "lucide-react";
import { api, AuthOrganization, SendingDomain, SenderAccount } from "@/lib/api";

interface WorkspaceSettingsViewProps {
  currentOrg: AuthOrganization | null;
  onSettingsUpdated?: (updatedOrg?: AuthOrganization, newSenderEmail?: string) => void;
}

export default function WorkspaceSettingsView({
  currentOrg,
  onSettingsUpdated,
}: WorkspaceSettingsViewProps) {
  const [activeTab, setActiveTab] = useState<
    "general" | "channels" | "domains" | "senders" | "compliance"
  >("general");

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
  const [newDomainDescription, setNewDomainDescription] = useState("");
  const [newDomainNotes, setNewDomainNotes] = useState("");
  const [showAddDomainModal, setShowAddDomainModal] = useState(false);
  const [domainSearch, setDomainSearch] = useState("");
  const [domainStatusFilter, setDomainStatusFilter] = useState("all");
  const [isAddingDomain, setIsAddingDomain] = useState(false);
  const [domainError, setDomainError] = useState<string | null>(null);
  const [domainSuccess, setDomainSuccess] = useState<string | null>(null);
  const [verifyingDomainId, setVerifyingDomainId] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Senders / Mail IDs State
  const [senders, setSenders] = useState<SenderAccount[]>([]);
  const [isLoadingSenders, setIsLoadingSenders] = useState(false);
  const [senderSearch, setSenderSearch] = useState("");
  const [senderDomainFilter, setSenderDomainFilter] = useState("");
  const [senderProviderFilter, setSenderProviderFilter] = useState("");
  const [senderStatusFilter, setSenderStatusFilter] = useState("");
  const [showAddSenderModal, setShowAddSenderModal] = useState(false);
  const [expandedSenderId, setExpandedSenderId] = useState<string | null>(null);
  const [refreshingSenderId, setRefreshingSenderId] = useState<string | null>(null);

  // Add Sender Form State
  const [newSenderEmail, setNewSenderEmail] = useState("");
  const [newSenderName, setNewSenderName] = useState("");
  const [newSenderDomainId, setNewSenderDomainId] = useState("");
  const [newSenderProvider, setNewSenderProvider] = useState("ses_only");
  const [newSenderHourlyLimit, setNewSenderHourlyLimit] = useState(50);
  const [newSenderDailyLimit, setNewSenderDailyLimit] = useState(200);
  const [newSenderWarmup, setNewSenderWarmup] = useState(false);
  const [newSenderNotes, setNewSenderNotes] = useState("");
  const [isAddingSender, setIsAddingSender] = useState(false);
  const [senderError, setSenderError] = useState<string | null>(null);
  const [senderSuccess, setSenderSuccess] = useState<string | null>(null);

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

  // Load sender accounts
  const fetchSenders = async () => {
    if (!orgId) return;
    try {
      setIsLoadingSenders(true);
      const res = await api.getSenders({
        domain_id: senderDomainFilter || undefined,
        provider: senderProviderFilter || undefined,
        status: senderStatusFilter || undefined,
        search: senderSearch || undefined,
      });
      setSenders(res);
    } catch (err: any) {
      console.warn("Failed to load senders:", err);
    } finally {
      setIsLoadingSenders(false);
    }
  };

  useEffect(() => {
    if (currentOrg) {
      setOrgName(currentOrg.name || "My Organization");
      const s = currentOrg.settings;
      if (s) {
        const sender = s.sender || s;
        if (sender.sender_name) setSenderName(sender.sender_name);
        if (sender.sender_email) setSenderEmail(sender.sender_email);
        if (sender.daily_limit) setDailyLimit(sender.daily_limit);
        if (sender.reply_to) setReplyTo(sender.reply_to);
      }
      fetchOrgDomains();
      fetchSenders();
    }
  }, [currentOrg]);

  useEffect(() => {
    if (activeTab === "senders") {
      fetchSenders();
      fetchOrgDomains();
    } else if (activeTab === "domains") {
      fetchOrgDomains();
    }
  }, [activeTab, senderDomainFilter, senderProviderFilter, senderStatusFilter]);

  useEffect(() => {
    if (showAddSenderModal) {
      fetchOrgDomains();
    }
  }, [showAddSenderModal]);

  useEffect(() => {
    const handleMsg = (e: MessageEvent) => {
      if (e.data?.type === "OAUTH_MAILBOX_CONNECTED") {
        fetchSenders();
        fetchOrgDomains();
      }
    };
    window.addEventListener("message", handleMsg);
    return () => window.removeEventListener("message", handleMsg);
  }, [orgId]);

  const handleSaveGeneral = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orgId) return;

    try {
      setIsSaving(true);
      setSaveSuccess(false);
      const res = await api.updateOrgSettings(orgId, {
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
      const updatedOrg = res?.organization || res?.data || res;
      if (onSettingsUpdated) onSettingsUpdated(updatedOrg, senderEmail);
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
    const cleanDomain = newDomainInput
      .trim()
      .toLowerCase()
      .replace("https://", "")
      .replace("http://", "")
      .split("/")[0];
    if (!cleanDomain || !cleanDomain.includes(".")) {
      setDomainError("Please enter a valid domain (e.g. acme.com or outreach.acme.com)");
      return;
    }

    try {
      setIsAddingDomain(true);
      await api.addEmailDomain(
        orgId,
        cleanDomain,
        newDomainDescription || undefined,
        newDomainNotes || undefined
      );
      setDomainSuccess(
        `Domain ${cleanDomain} registered in AWS SES! Add the DNS records below to complete verification.`
      );
      setNewDomainInput("");
      setNewDomainDescription("");
      setNewDomainNotes("");
      setShowAddDomainModal(false);
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
      if (res.can_send || res.verification_status === "verified" || res.status === "verified" || res.status === "ready") {
        setDomainSuccess(`Domain verified successfully! AWS SES high-deliverability sending is now ENABLED.`);
      } else {
        setDomainError("DNS records have not been detected yet. Please verify that the records were added correctly to your DNS provider and allow time for DNS propagation.");
      }
      await fetchOrgDomains();
      await fetchSenders();
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
      await fetchSenders();
    } catch (err: any) {
      alert("Failed to update sending state: " + err.message);
    }
  };

  const handleDeleteDomain = async (domainId: string, domainName: string) => {
    if (!orgId) return;
    if (
      !confirm(
        `Are you sure you want to remove ${domainName}? This will revoke AWS SES identity and affect any associated sender accounts.`
      )
    )
      return;
    try {
      await api.deleteEmailDomain(orgId, domainId);
      await fetchOrgDomains();
      await fetchSenders();
    } catch (err: any) {
      alert("Failed to delete domain: " + err.message);
    }
  };

  const handleCreateSender = async (e: React.FormEvent) => {
    e.preventDefault();
    setSenderError(null);
    setSenderSuccess(null);

    const email = newSenderEmail.trim().toLowerCase();
    if (!email || !email.includes("@")) {
      setSenderError("Please enter a valid sender email address.");
      return;
    }

    try {
      setIsAddingSender(true);
      await api.createSender({
        email,
        display_name: newSenderName || undefined,
        domain_id: newSenderDomainId || undefined,
        provider: newSenderProvider,
        hourly_limit: newSenderHourlyLimit,
        daily_limit: newSenderDailyLimit,
        warmup_enabled: newSenderWarmup,
        notes: newSenderNotes || undefined,
      });

      setSenderSuccess(`Sender account ${email} created successfully!`);
      setNewSenderEmail("");
      setNewSenderName("");
      setNewSenderDomainId("");
      setNewSenderNotes("");
      setShowAddSenderModal(false);
      await fetchSenders();
    } catch (err: any) {
      setSenderError(err.message || "Failed to create sender account");
    } finally {
      setIsAddingSender(false);
    }
  };

  const handleRefreshSender = async (senderId: string) => {
    try {
      setRefreshingSenderId(senderId);
      await api.refreshSenderReadiness(senderId);
      await fetchSenders();
    } catch (err: any) {
      alert("Failed to refresh sender readiness: " + err.message);
    } finally {
      setRefreshingSenderId(null);
    }
  };

  const handleToggleSenderEnabled = async (sender: SenderAccount) => {
    try {
      await api.updateSender(sender.id, { enabled: !sender.enabled });
      await fetchSenders();
    } catch (err: any) {
      alert("Failed to toggle sender: " + err.message);
    }
  };

  const handleDeleteSender = async (sender: SenderAccount) => {
    if (!confirm(`Are you sure you want to remove sender '${sender.email}'?`)) return;
    try {
      await api.deleteSender(sender.id);
      await fetchSenders();
    } catch (err: any) {
      alert("Failed to delete sender: " + err.message);
    }
  };

  const copyToClipboard = (text: string, key: string) => {
    if (navigator?.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    }
  };

  // Filtered domains
  const filteredDomains = domains.filter((d) => {
    const matchesSearch =
      !domainSearch ||
      d.domain.toLowerCase().includes(domainSearch.toLowerCase()) ||
      (d.description && d.description.toLowerCase().includes(domainSearch.toLowerCase()));
    const isVerified = d.status === "verified" || d.status === "ready" || d.verification_status === "verified";
    const isPaused = d.status === "paused" || d.can_send === false;

    if (domainStatusFilter === "verified") return matchesSearch && isVerified && !isPaused;
    if (domainStatusFilter === "pending") return matchesSearch && !isVerified;
    if (domainStatusFilter === "paused") return matchesSearch && isPaused;
    return matchesSearch;
  });

  // Calculate overview counts for senders
  const activeSendersCount = senders.filter((s) => s.overall_status === "active").length;
  const totalDailyCapacity = senders
    .filter((s) => s.overall_status === "active")
    .reduce((acc, s) => acc + (s.daily_limit || 0), 0);

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
              Configure outbound mailboxes, DNS authentication (SPF, DKIM, DMARC), AWS SES sending domains, and multi-sender capacity.
            </p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-1 shadow-xs max-w-2xl mt-6 overflow-x-auto">
          <button
            type="button"
            onClick={() => setActiveTab("general")}
            className={`flex-1 min-w-[110px] py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
              activeTab === "general"
                ? "bg-white text-[#0F172A] shadow-xs"
                : "text-[#64748B] hover:text-[#0F172A]"
            }`}
          >
            🏢 Profile
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("channels")}
            className={`flex-1 min-w-[120px] py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
              activeTab === "channels"
                ? "bg-white text-[#0F172A] shadow-xs"
                : "text-[#64748B] hover:text-[#0F172A]"
            }`}
          >
            📬 Channels
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("domains")}
            className={`flex-1 min-w-[130px] py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
              activeTab === "domains"
                ? "bg-white text-[#0F172A] shadow-xs"
                : "text-[#64748B] hover:text-[#0F172A]"
            }`}
          >
            🌐 Domains ({domains.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("senders")}
            className={`flex-1 min-w-[140px] py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
              activeTab === "senders"
                ? "bg-white text-[#0F172A] shadow-xs"
                : "text-[#64748B] hover:text-[#0F172A]"
            }`}
          >
            ✉️ Mail IDs ({senders.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("compliance")}
            className={`flex-1 min-w-[120px] py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
              activeTab === "compliance"
                ? "bg-white text-[#0F172A] shadow-xs"
                : "text-[#64748B] hover:text-[#0F172A]"
            }`}
          >
            ⚖️ Compliance
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
                    href={`http://localhost:8000/api/channels/oauth/microsoft/login?email=${encodeURIComponent(detectEmail)}&org_id=${encodeURIComponent(orgId)}`}
                    target="_blank"
                    rel="noopener noreferrer"
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
                    href={`http://localhost:8000/api/channels/oauth/google/login?email=${encodeURIComponent(detectEmail)}&org_id=${encodeURIComponent(orgId)}`}
                    target="_blank"
                    rel="noopener noreferrer"
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
                  Verify arbitrary domains with AWS SES Easy DKIM. Background daemon checks DNS propagation automatically every 5 minutes.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => fetchOrgDomains()}
                  className="py-2 px-3 bg-white border border-[#CBD5E1] hover:bg-[#F8FAFC] text-[#334155] text-[13px] font-bold rounded-xl flex items-center gap-1.5 shadow-xs transition-all"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoadingDomains ? "animate-spin text-[#2563EB]" : ""}`} />
                  <span>Refresh</span>
                </button>
                <button
                  onClick={() => setShowAddDomainModal(true)}
                  className="py-2 px-4 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13px] font-bold rounded-xl flex items-center gap-1.5 shadow-xs transition-all"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add Domain</span>
                </button>
              </div>
            </div>

            {/* Search & Filter Bar */}
            <div className="flex flex-col sm:flex-row gap-3 mb-6">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-[#94A3B8] absolute left-3.5 top-3" />
                <input
                  type="text"
                  placeholder="Search domains by name or description..."
                  value={domainSearch}
                  onChange={(e) => setDomainSearch(e.target.value)}
                  className="w-full pl-9 pr-3.5 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>
              <div className="flex gap-2">
                <select
                  value={domainStatusFilter}
                  onChange={(e) => setDomainStatusFilter(e.target.value)}
                  className="px-3 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                >
                  <option value="all">All Statuses</option>
                  <option value="verified">Verified Only</option>
                  <option value="pending">Pending Verification</option>
                  <option value="paused">Paused</option>
                </select>
              </div>
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
            <div className="mb-6 p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl space-y-3">
              <div className="flex items-start gap-3">
                <span className="text-xl">💡</span>
                <div className="text-[12px] text-[#475569] leading-relaxed">
                  <strong className="text-[#0F172A] block mb-0.5">Universal DNS Provider Support &amp; Best Practices:</strong>
                  Add the CNAME records provided below to your DNS hosting provider (Cloudflare, GoDaddy, Namecheap, Route 53, etc.).
                  Verification is automatically checked in the background.
                </div>
              </div>

              {/* Recommended SPF & DMARC Tip */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                <div className="p-2.5 bg-white border border-[#E2E8F0] rounded-lg text-[11.5px]">
                  <span className="font-bold text-[#0F172A] block mb-0.5">Recommended SPF TXT Record:</span>
                  <code className="text-[#2563EB] bg-[#EFF6FF] px-1.5 py-0.5 rounded font-mono block truncate select-all">
                    v=spf1 include:amazonses.com ~all
                  </code>
                </div>
                <div className="p-2.5 bg-white border border-[#E2E8F0] rounded-lg text-[11.5px]">
                  <span className="font-bold text-[#0F172A] block mb-0.5">Recommended DMARC TXT Record (_dmarc):</span>
                  <code className="text-[#2563EB] bg-[#EFF6FF] px-1.5 py-0.5 rounded font-mono block truncate select-all">
                    v=DMARC1; p=none; sp=none; pct=100;
                  </code>
                </div>
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
            {!isLoadingDomains && filteredDomains.length === 0 && (
              <div className="py-10 text-center border-2 border-dashed border-[#E2E8F0] rounded-xl">
                <Globe className="w-10 h-10 text-[#94A3B8] mx-auto mb-2 opacity-50" />
                <div className="text-[14px] font-bold text-[#0F172A]">
                  {domains.length === 0 ? "No Sending Domains Configured" : "No Matching Domains Found"}
                </div>
                <p className="text-[12.5px] text-[#64748B] max-w-md mx-auto mt-1 mb-4">
                  {domains.length === 0
                    ? "Add your corporate or campaign sending domain to generate AWS SES Easy DKIM verification records."
                    : "Try adjusting your search query or status filter."}
                </p>
                {domains.length === 0 && (
                  <button
                    onClick={() => setShowAddDomainModal(true)}
                    className="py-2 px-4 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13px] font-bold rounded-xl transition-all"
                  >
                    Add First Domain
                  </button>
                )}
              </div>
            )}

            {/* Domains List */}
            <div className="space-y-5">
              {filteredDomains.map((dom) => {
                const isVerified =
                  dom.status === "verified" ||
                  dom.status === "ready" ||
                  dom.verification_status === "verified";
                const canSend = dom.can_send ?? isVerified;
                const isChecking = verifyingDomainId === dom.id;

                return (
                  <div key={dom.id} className="border border-[#E2E8F0] rounded-xl p-5 bg-[#F8FAFC]">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold ${
                            isVerified ? "bg-[#ECFDF5] text-[#059669]" : "bg-[#FEF3C7] text-[#D97706]"
                          }`}
                        >
                          <Globe className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2.5">
                            <span className="text-[16px] font-extrabold text-[#0F172A] font-mono">
                              {dom.domain}
                            </span>
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
                          {dom.description && (
                            <p className="text-[12px] text-[#475569] mt-0.5">{dom.description}</p>
                          )}
                          <div className="flex items-center gap-3 text-[11.5px] mt-1 text-[#64748B]">
                            {dom.ses_identity_arn && (
                              <span className="truncate max-w-xs font-mono text-[10.5px]">
                                ARN: {dom.ses_identity_arn}
                              </span>
                            )}
                            {dom.daily_cap && (
                              <span>
                                Daily Cap: <strong className="text-[#0F172A]">{dom.daily_cap}</strong>
                              </span>
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
                          <RefreshCw
                            className={`w-3.5 h-3.5 ${
                              isChecking ? "animate-spin text-[#2563EB]" : ""
                            }`}
                          />
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
                              <div className="col-span-2 font-mono font-bold text-[#0F172A]">
                                {recType}
                              </div>
                              <div className="col-span-4 font-mono text-[#334155] flex items-center gap-1.5 pr-2">
                                <span className="truncate" title={recHost}>
                                  {recHost}
                                </span>
                                <button
                                  type="button"
                                  onClick={() => copyToClipboard(recHost, hostKey)}
                                  className="text-[10px] text-[#2563EB] hover:underline font-sans shrink-0 px-1 py-0.5 rounded bg-[#EFF6FF]"
                                >
                                  {copiedKey === hostKey ? "Copied!" : "Copy"}
                                </button>
                              </div>
                              <div className="col-span-4 font-mono text-[#334155] flex items-center gap-1.5 pr-2">
                                <span className="truncate" title={recVal}>
                                  {recVal}
                                </span>
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

      {/* TAB 4: SENDER ACCOUNTS (MAIL IDS) */}
      {activeTab === "senders" && (
        <div className="space-y-6">
          <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs">
            {/* Header + Stats */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
              <div>
                <h2 className="text-lg font-bold text-[#0F172A] flex items-center gap-2">
                  <span>✉️</span>
                  <span>Mail IDs &amp; Sender Account Management</span>
                </h2>
                <p className="text-[13px] text-[#64748B] mt-0.5">
                  Configure sender addresses associated with verified domains. Tracks SES identity readiness, mailbox connections, and hourly/daily rate caps.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => fetchSenders()}
                  className="py-2 px-3 bg-white border border-[#CBD5E1] hover:bg-[#F8FAFC] text-[#334155] text-[13px] font-bold rounded-xl flex items-center gap-1.5 shadow-xs transition-all"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoadingSenders ? "animate-spin text-[#2563EB]" : ""}`} />
                  <span>Refresh</span>
                </button>
                <button
                  onClick={() => setShowAddSenderModal(true)}
                  className="py-2 px-4 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13px] font-bold rounded-xl flex items-center gap-1.5 shadow-xs transition-all"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add Mail ID</span>
                </button>
              </div>
            </div>

            {/* Quick Metrics Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              <div className="p-3.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl">
                <span className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider block">
                  Total Mail IDs
                </span>
                <span className="text-xl font-extrabold text-[#0F172A] mt-1 block">
                  {senders.length}
                </span>
              </div>
              <div className="p-3.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl">
                <span className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider block">
                  Active &amp; Ready
                </span>
                <span className="text-xl font-extrabold text-[#059669] mt-1 block">
                  {activeSendersCount}
                </span>
              </div>
              <div className="p-3.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl">
                <span className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider block">
                  Active Daily Capacity
                </span>
                <span className="text-xl font-extrabold text-[#2563EB] mt-1 block">
                  {totalDailyCapacity.toLocaleString()} /day
                </span>
              </div>
              <div className="p-3.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl">
                <span className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider block">
                  Verified Domains
                </span>
                <span className="text-xl font-extrabold text-[#0F172A] mt-1 block">
                  {domains.filter((d) => d.status === "verified" || d.status === "ready").length}
                </span>
              </div>
            </div>

            {/* Search & Filter Bar */}
            <div className="flex flex-col sm:flex-row gap-3 mb-6">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-[#94A3B8] absolute left-3.5 top-3" />
                <input
                  type="text"
                  placeholder="Search senders by email or display name..."
                  value={senderSearch}
                  onChange={(e) => setSenderSearch(e.target.value)}
                  className="w-full pl-9 pr-3.5 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>

              <div className="flex flex-wrap gap-2">
                <select
                  value={senderDomainFilter}
                  onChange={(e) => setSenderDomainFilter(e.target.value)}
                  className="px-3 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                >
                  <option value="">All Domains</option>
                  {domains.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.domain}
                    </option>
                  ))}
                </select>

                <select
                  value={senderProviderFilter}
                  onChange={(e) => setSenderProviderFilter(e.target.value)}
                  className="px-3 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                >
                  <option value="">All Providers</option>
                  <option value="ses_only">SES Only</option>
                  <option value="microsoft_365">Microsoft 365</option>
                  <option value="google_workspace">Google Workspace</option>
                  <option value="smtp_imap">SMTP / IMAP</option>
                </select>

                <select
                  value={senderStatusFilter}
                  onChange={(e) => setSenderStatusFilter(e.target.value)}
                  className="px-3 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                >
                  <option value="">All Statuses</option>
                  <option value="active">Active (Ready)</option>
                  <option value="ses_pending">SES Pending</option>
                  <option value="mailbox_disconnected">Disconnected</option>
                  <option value="rate_limited">Rate Limited</option>
                  <option value="disabled">Disabled</option>
                </select>
              </div>
            </div>

            {/* Alerts */}
            {senderError && (
              <div className="mb-5 p-3.5 bg-[#FEF2F2] border border-[#FECACA] rounded-xl text-[12.5px] text-[#DC2626] font-medium flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-[#DC2626]" />
                  <span>{senderError}</span>
                </div>
                <button onClick={() => setSenderError(null)} className="text-[#DC2626] hover:underline font-bold text-[11.5px]">Dismiss</button>
              </div>
            )}

            {senderSuccess && (
              <div className="mb-5 p-3.5 bg-[#F0FDF4] border border-[#BBF7D0] rounded-xl text-[12.5px] text-[#15803D] font-medium flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-[#15803D]" />
                  <span>{senderSuccess}</span>
                </div>
                <button onClick={() => setSenderSuccess(null)} className="text-[#15803D] hover:underline font-bold text-[11.5px]">Dismiss</button>
              </div>
            )}

            {/* Senders List */}
            {isLoadingSenders && (
              <div className="py-8 text-center text-[#64748B] text-[13px] flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-[#2563EB]" />
                <span>Loading sender accounts...</span>
              </div>
            )}

            {!isLoadingSenders && senders.length === 0 && (
              <div className="py-10 text-center border-2 border-dashed border-[#E2E8F0] rounded-xl">
                <Mail className="w-10 h-10 text-[#94A3B8] mx-auto mb-2 opacity-50" />
                <div className="text-[14px] font-bold text-[#0F172A]">No Mail IDs Configured</div>
                <p className="text-[12.5px] text-[#64748B] max-w-md mx-auto mt-1 mb-4">
                  Add sender accounts associated with your verified sending domains to start routing multi-account outbound campaigns.
                </p>
                <button
                  onClick={() => setShowAddSenderModal(true)}
                  className="py-2 px-4 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13px] font-bold rounded-xl transition-all"
                >
                  Add First Mail ID
                </button>
              </div>
            )}

            <div className="space-y-4">
              {senders.map((sender) => {
                const isExpanded = expandedSenderId === sender.id;
                const isRefreshing = refreshingSenderId === sender.id;

                let statusColor = "bg-[#FEF3C7] text-[#D97706] border-[#FDE68A]";
                let statusLabel = sender.overall_status.toUpperCase().replace("_", " ");
                if (sender.overall_status === "active") {
                  statusColor = "bg-[#ECFDF5] text-[#059669] border-[#A7F3D0]";
                  statusLabel = "✓ ACTIVE / READY";
                } else if (sender.overall_status === "disabled") {
                  statusColor = "bg-[#F1F5F9] text-[#64748B] border-[#CBD5E1]";
                  statusLabel = "DISABLED";
                } else if (sender.overall_status === "mailbox_disconnected") {
                  statusColor = "bg-[#FEF2F2] text-[#DC2626] border-[#FECACA]";
                  statusLabel = "DISCONNECTED";
                }

                return (
                  <div
                    key={sender.id}
                    className="border border-[#E2E8F0] rounded-xl p-5 bg-[#F8FAFC] transition-all hover:border-[#CBD5E1]"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      {/* Left: Identity info */}
                      <div className="flex items-start gap-3">
                        <div
                          className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold shrink-0 mt-0.5 ${
                            sender.overall_status === "active"
                              ? "bg-[#ECFDF5] text-[#059669]"
                              : "bg-[#F1F5F9] text-[#64748B]"
                          }`}
                        >
                          <Mail className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[15px] font-bold text-[#0F172A] font-mono">
                              {sender.email}
                            </span>
                            <span
                              className={`px-2.5 py-0.5 rounded-full font-bold text-[10.5px] border ${statusColor}`}
                            >
                              {statusLabel}
                            </span>
                            <span className="px-2 py-0.5 rounded-md bg-[#EFF6FF] text-[#2563EB] text-[10.5px] font-bold uppercase font-mono">
                              {sender.provider.replace("_", " ")}
                            </span>
                          </div>

                          <div className="flex items-center gap-3 text-[12px] text-[#64748B] mt-1 flex-wrap">
                            {sender.display_name && (
                              <span>
                                Display: <strong className="text-[#0F172A]">{sender.display_name}</strong>
                              </span>
                            )}
                            <span>
                              Domain: <strong className="text-[#0F172A]">{sender.domain_name}</strong>
                            </span>
                            <span>
                              Hourly: <strong className="text-[#0F172A]">{sender.sends_this_hour}/{sender.hourly_limit || "∞"}</strong>
                            </span>
                            <span>
                              Daily: <strong className="text-[#0F172A]">{sender.sends_today}/{sender.daily_limit || "∞"}</strong>
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Right: Actions */}
                      <div className="flex items-center gap-2 shrink-0">
                        {sender.provider !== "ses_only" && sender.mailbox_connection_status !== "connected" && (
                          <a
                            href={`http://localhost:8000/api/channels/oauth/${
                              sender.provider === "microsoft_365" ? "microsoft" : "google"
                            }/login?email=${encodeURIComponent(sender.email)}&org_id=${encodeURIComponent(orgId)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="py-1.5 px-3 bg-[#0F172A] hover:bg-[#1E293B] text-white rounded-lg text-[11.5px] font-bold flex items-center gap-1 transition-all"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            <span>Connect Mailbox</span>
                          </a>
                        )}

                        <button
                          onClick={() => handleRefreshSender(sender.id)}
                          disabled={isRefreshing}
                          title="Refresh readiness"
                          className="p-2 bg-white border border-[#CBD5E1] hover:bg-[#F1F5F9] rounded-lg text-[#334155] transition-all disabled:opacity-50"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-[#2563EB]" : ""}`} />
                        </button>

                        <button
                          onClick={() => handleToggleSenderEnabled(sender)}
                          title={sender.enabled ? "Disable sender" : "Enable sender"}
                          className={`px-3 py-1.5 rounded-lg text-[11.5px] font-bold transition-all ${
                            sender.enabled
                              ? "bg-white border border-[#CBD5E1] text-[#334155] hover:bg-[#FEF2F2] hover:text-[#DC2626]"
                              : "bg-[#2563EB] text-white hover:bg-[#1D4ED8]"
                          }`}
                        >
                          {sender.enabled ? "Disable" : "Enable"}
                        </button>

                        <button
                          onClick={() => setExpandedSenderId(isExpanded ? null : sender.id)}
                          className="p-2 bg-white border border-[#CBD5E1] hover:bg-[#F1F5F9] rounded-lg text-[#334155] transition-all"
                          title="Readiness checklist"
                        >
                          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </button>

                        <button
                          onClick={() => handleDeleteSender(sender)}
                          title="Delete sender"
                          className="p-2 text-[#94A3B8] hover:text-[#DC2626] hover:bg-white rounded-lg transition-all"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Expandable Readiness Checklist */}
                    {isExpanded && (
                      <div className="mt-4 pt-4 border-t border-[#E2E8F0] space-y-3">
                        <div className="text-[12px] font-bold text-[#0F172A] flex items-center gap-1.5">
                          <ShieldCheck className="w-4 h-4 text-[#2563EB]" />
                          <span>Sender Readiness &amp; Prerequisites Checklist</span>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[12px]">
                          {sender.readiness_checklist.map((check, idx) => (
                            <div
                              key={idx}
                              className={`p-2.5 rounded-lg border flex items-start gap-2 ${
                                check.passed
                                  ? "bg-[#F0FDF4] border-[#BBF7D0] text-[#15803D]"
                                  : "bg-[#FEF2F2] border-[#FECACA] text-[#DC2626]"
                              }`}
                            >
                              {check.passed ? (
                                <CheckCircle2 className="w-4 h-4 shrink-0 text-[#15803D] mt-0.5" />
                              ) : (
                                <AlertTriangle className="w-4 h-4 shrink-0 text-[#DC2626] mt-0.5" />
                              )}
                              <div>
                                <span className="font-bold block">{check.label}</span>
                                <span className="text-[11px] opacity-80">{check.detail}</span>
                              </div>
                            </div>
                          ))}
                        </div>

                        {sender.notes && (
                          <div className="text-[11.5px] text-[#64748B] bg-white p-2.5 rounded-lg border border-[#E2E8F0]">
                            <strong>Notes:</strong> {sender.notes}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: COMPLIANCE & FOOTER */}
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

      {/* MODAL: ADD SENDING DOMAIN */}
      {showAddDomainModal && (
        <div className="fixed inset-0 bg-[#0F172A]/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 max-w-lg w-full shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-[#0F172A] flex items-center gap-2">
                <span>🌐</span>
                <span>Register New Sending Domain</span>
              </h3>
              <button
                onClick={() => setShowAddDomainModal(false)}
                className="text-[#94A3B8] hover:text-[#0F172A] p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-[13px] text-[#64748B]">
              Add any root domain or subdomain. AWS SES Easy DKIM tokens will be generated immediately for DNS configuration.
            </p>

            <form onSubmit={handleAddDomain} className="space-y-4">
              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                  Domain Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. outreach.acme.com or acme.com"
                  value={newDomainInput}
                  onChange={(e) => setNewDomainInput(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>

              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                  Description / Purpose (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Inbound Sales SDR Team"
                  value={newDomainDescription}
                  onChange={(e) => setNewDomainDescription(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>

              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                  Internal Notes (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. Registered with Cloudflare DNS, owned by marketing"
                  value={newDomainNotes}
                  onChange={(e) => setNewDomainNotes(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddDomainModal(false)}
                  className="py-2.5 px-4 bg-white border border-[#CBD5E1] hover:bg-[#F1F5F9] text-[#334155] text-[13px] font-bold rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isAddingDomain}
                  className="py-2.5 px-5 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13px] font-bold rounded-xl transition-all disabled:opacity-50"
                >
                  {isAddingDomain ? "Provisioning..." : "Provision Domain"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ADD SENDER ACCOUNT (MAIL ID) */}
      {showAddSenderModal && (
        <div className="fixed inset-0 bg-[#0F172A]/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 max-w-lg w-full shadow-xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-[#0F172A] flex items-center gap-2">
                <span>✉️</span>
                <span>Add Sender Account (Mail ID)</span>
              </h3>
              <button
                onClick={() => setShowAddSenderModal(false)}
                className="text-[#94A3B8] hover:text-[#0F172A] p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-[13px] text-[#64748B]">
              Configure an individual sender email address (Gmail, Microsoft 365 / Outlook, or custom domain).
            </p>

            <form onSubmit={handleCreateSender} className="space-y-4">
              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                  Sender Email Address *
                </label>
                <input
                  type="email"
                  required
                  placeholder="e.g. yourname@gmail.com or mohit@nenotechnology.us"
                  value={newSenderEmail}
                  onChange={(e) => {
                    const val = e.target.value;
                    setNewSenderEmail(val);
                    if (val.includes("@")) {
                      const domainPart = val.split("@")[1].toLowerCase();
                      if (domainPart.includes("gmail.com")) {
                        setNewSenderProvider("google_workspace");
                      } else if (
                        domainPart.includes("outlook.com") ||
                        domainPart.includes("hotmail.com") ||
                        domainPart.includes("live.com")
                      ) {
                        setNewSenderProvider("microsoft_365");
                      }
                      if (!newSenderDomainId) {
                        const match = domains.find((d) => d.domain.toLowerCase() === domainPart);
                        if (match) setNewSenderDomainId(match.id);
                      }
                    }
                  }}
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>

              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                  Display Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Mohit Patel"
                  value={newSenderName}
                  onChange={(e) => setNewSenderName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>

              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                  Associated Sending Domain (Optional)
                </label>
                <select
                  value={newSenderDomainId}
                  onChange={(e) => setNewSenderDomainId(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                >
                  <option value="">Direct Mailbox / Any Domain (Gmail, Outlook, OAuth)</option>
                  {domains.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.domain} ({d.status === "verified" || d.status === "ready" ? "Verified" : "Pending"})
                    </option>
                  ))}
                </select>
                {domains.length === 0 && newSenderProvider === "ses_only" && (
                  <p className="text-[11.5px] text-[#DC2626] mt-1">
                    No sending domains found. For SES outbound sending, please register a domain in the Domains tab first.
                  </p>
                )}
              </div>

              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                  Delivery Connection Provider
                </label>
                <select
                  value={newSenderProvider}
                  onChange={(e) => setNewSenderProvider(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                >
                  <option value="ses_only">AWS SES Only (Outbound campaigns via SES)</option>
                  <option value="microsoft_365">Microsoft 365 / Outlook (OAuth mailbox)</option>
                  <option value="google_workspace">Google Workspace / Gmail (OAuth mailbox)</option>
                  <option value="smtp_imap">Custom SMTP / IMAP</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                    Hourly Limit
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="1000"
                    value={newSenderHourlyLimit}
                    onChange={(e) => setNewSenderHourlyLimit(parseInt(e.target.value) || 50)}
                    className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                  />
                </div>
                <div>
                  <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                    Daily Limit
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="5000"
                    value={newSenderDailyLimit}
                    onChange={(e) => setNewSenderDailyLimit(parseInt(e.target.value) || 200)}
                    className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="warmup-toggle"
                  checked={newSenderWarmup}
                  onChange={(e) => setNewSenderWarmup(e.target.checked)}
                  className="rounded text-[#2563EB] focus:ring-[#2563EB]"
                />
                <label htmlFor="warmup-toggle" className="text-[13px] text-[#0F172A] font-medium cursor-pointer">
                  Enable Warm-up Mode (Gradually ramps from 10 sends/day)
                </label>
              </div>

              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                  Internal Notes (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. Lead SDR account for SaaS campaign"
                  value={newSenderNotes}
                  onChange={(e) => setNewSenderNotes(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddSenderModal(false)}
                  className="py-2.5 px-4 bg-white border border-[#CBD5E1] hover:bg-[#F1F5F9] text-[#334155] text-[13px] font-bold rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isAddingSender}
                  className="py-2.5 px-5 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13px] font-bold rounded-xl transition-all disabled:opacity-50"
                >
                  {isAddingSender ? "Adding..." : "Add Mail ID"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
