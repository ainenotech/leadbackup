"use client";

import React, { useState, useEffect, useCallback, Suspense } from "react";
import Sidebar, { PageId } from "@/components/layout/Sidebar";
import AuthView from "@/components/views/AuthView";
import PipelineOverview from "@/components/views/PipelineOverview";
import AnalyticsView from "@/components/views/AnalyticsView";
import MasterDbView from "@/components/views/MasterDbView";
import TemplateHubView from "@/components/views/TemplateHubView";
import UploadDraftView from "@/components/views/UploadDraftView";
import LeadsDirectoryView from "@/components/views/LeadsDirectoryView";
import EmailReviewView from "@/components/views/EmailReviewView";
import RepliesBookingsView from "@/components/views/RepliesBookingsView";
import KnowledgeBaseView from "@/components/views/KnowledgeBaseView";
import WorkspaceSettingsView from "@/components/views/WorkspaceSettingsView";
import TeamMembersView from "@/components/views/TeamMembersView";
import SuperAdminView from "@/components/views/SuperAdminView";
import {
  api,
  OverviewStats,
  ActivityFeedEvent,
  CampaignLogItem,
  AuthUser,
  AuthOrganization,
  getStoredToken,
  clearStoredToken,
} from "@/lib/api";

function AppContent() {
  // Authentication State
  const [mounted, setMounted] = useState<boolean>(false);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isAuthChecking, setIsAuthChecking] = useState<boolean>(true);
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [currentOrg, setCurrentOrg] = useState<AuthOrganization | null>(null);
  const [organizations, setOrganizations] = useState<AuthOrganization[]>([]);
  const [activeSenderEmail, setActiveSenderEmail] = useState<string>("mohit@nenotechnology.us");

  // Navigation State
  const [activePage, setActivePage] = useState<PageId>("overview");
  const [syncInterval, setSyncInterval] = useState<number>(5000);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);

  // Overview Stats
  const [stats, setStats] = useState<OverviewStats>({
    total_leads: 0,
    drafted_leads: 0,
    sent_leads: 0,
    replied_leads: 0,
    forms_filled: 0,
    scheduled_leads: 0,
    draft_pct: 0,
    sent_pct: 0,
    reply_pct: 0,
    form_pct: 0,
    booked_pct: 0,
  });

  const [events, setEvents] = useState<ActivityFeedEvent[]>([]);
  const [recentLogs, setRecentLogs] = useState<CampaignLogItem[]>([]);

  // Check existing session on mount
  useEffect(() => {
    setMounted(true);
    const checkAuth = async () => {
      const token = getStoredToken();
      if (!token) {
        setIsAuthenticated(false);
        setIsAuthChecking(false);
        return;
      }

      try {
        const me = await api.getMe();
        if (me && me.user) {
          setCurrentUser(me.user);
          const org = me.active_organization || me.organization || me.organizations?.[0];
          setCurrentOrg(org || null);
          setOrganizations(me.organizations || (org ? [org] : []));
          setActiveSenderEmail(me.user.email || "mohit@nenotechnology.us");
          setIsAuthenticated(true);
        } else {
          setIsAuthenticated(false);
        }
      } catch (e) {
        console.warn("Session check failed:", e);
        setIsAuthenticated(false);
      } finally {
        setIsAuthChecking(false);
      }
    };

    checkAuth();
  }, []);

  // Sync data from FastAPI backend
  const fetchTelemetry = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      setIsSyncing(true);
      const [sRes, fRes, lRes] = await Promise.allSettled([
        api.getOverviewStats(),
        api.getRealtimeFeed(15),
        api.getLogs({ limit: 10 }),
      ]);

      if (sRes.status === "fulfilled") setStats(sRes.value);
      if (fRes.status === "fulfilled" && fRes.value.events) setEvents(fRes.value.events);
      if (lRes.status === "fulfilled" && lRes.value.logs) setRecentLogs(lRes.value.logs);
    } catch (e) {
      console.warn("Telemetry fetch error:", e);
    } finally {
      setIsSyncing(false);
    }
  }, [isAuthenticated]);

  // Initial load once authenticated
  useEffect(() => {
    if (isAuthenticated) {
      fetchTelemetry();
      if (typeof window !== "undefined") {
        const urlParams = new URLSearchParams(window.location.search);
        const pageParam = urlParams.get("page") as PageId;
        const validPages: PageId[] = [
          "overview",
          "master_db",
          "analytics",
          "templates",
          "upload",
          "leads",
          "email",
          "replies",
          "knowledge_base",
          "org_settings",
          "team",
          "super_admin",
        ];
        if (pageParam && validPages.includes(pageParam)) {
          setActivePage(pageParam);
        }
      }
    }
  }, [isAuthenticated, fetchTelemetry]);

  // Periodic Auto-Sync Timer
  useEffect(() => {
    if (!isAuthenticated || syncInterval <= 0) return;
    const timer = setInterval(() => {
      fetchTelemetry();
    }, syncInterval);
    return () => clearInterval(timer);
  }, [isAuthenticated, syncInterval, fetchTelemetry]);

  const handlePageChange = (page: PageId) => {
    setActivePage(page);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("page", page);
      window.history.pushState({}, "", url);
    }
  };

  const handleLoginSuccess = (
    user: AuthUser,
    org: AuthOrganization,
    orgs: AuthOrganization[]
  ) => {
    setCurrentUser(user);
    setCurrentOrg(org);
    setOrganizations(orgs);
    setActiveSenderEmail(user.email || "mohit@nenotechnology.us");
    setIsAuthenticated(true);
    fetchTelemetry();
  };

  const handleLogout = () => {
    clearStoredToken();
    setIsAuthenticated(false);
    setCurrentUser(null);
    setCurrentOrg(null);
    setOrganizations([]);
    setActivePage("overview");
  };

  const handleSwitchOrg = async (orgId: string) => {
    try {
      const res = await api.switchOrg(orgId);
      setCurrentOrg(res.organization);
      fetchTelemetry();
    } catch (err: any) {
      alert("Failed to switch workspace: " + err.message);
    }
  };

  // While verifying session
  if (!mounted || isAuthChecking) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-[#2563EB] border-t-transparent rounded-full animate-spin"></div>
          <span className="text-[13px] font-bold text-[#64748B]">Loading AINeotechnology...</span>
        </div>
      </div>
    );
  }

  // If not logged in, render the executive login screen with login side content
  if (!isAuthenticated) {
    return <AuthView onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="flex min-h-screen bg-[#F8FAFC]">
      {/* Complete Sidebar from Old Project */}
      <Sidebar
        activePage={activePage}
        onPageChange={handlePageChange}
        currentUser={currentUser}
        currentOrg={currentOrg}
        organizations={organizations}
        onSwitchOrg={handleSwitchOrg}
        activeSenderEmail={activeSenderEmail}
        onLogout={handleLogout}
        syncInterval={syncInterval}
        onSyncIntervalChange={setSyncInterval}
        onManualSync={fetchTelemetry}
        isSyncing={isSyncing}
      />

      {/* Main Content View Container */}
      <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full overflow-x-hidden">
        {activePage === "overview" && (
          <PipelineOverview
            stats={stats}
            events={events}
            recentLogs={recentLogs}
            syncChoiceText={
              syncInterval === 5000
                ? "⚡ Real-Time (5s)"
                : syncInterval === 15000
                ? "🚀 Fast (15s)"
                : syncInterval === 30000
                ? "⏱️ Standard (30s)"
                : syncInterval === 60000
                ? "🕐 1 Min"
                : "⏸️ Paused"
            }
            onNavigate={(p) => handlePageChange(p as PageId)}
          />
        )}

        {activePage === "master_db" && <MasterDbView />}

        {activePage === "analytics" && <AnalyticsView />}

        {activePage === "templates" && <TemplateHubView />}

        {activePage === "upload" && (
          <UploadDraftView
            onNavigate={(p) => handlePageChange(p as PageId)}
          />
        )}

        {activePage === "leads" && <LeadsDirectoryView />}

        {activePage === "email" && (
          <EmailReviewView
            onDraftsApproved={fetchTelemetry}
            onNavigateToUpload={() => handlePageChange("upload")}
          />
        )}

        {activePage === "replies" && <RepliesBookingsView />}

        {activePage === "knowledge_base" && <KnowledgeBaseView />}

        {activePage === "org_settings" && (
          <WorkspaceSettingsView currentOrg={currentOrg} onSettingsUpdated={fetchTelemetry} />
        )}

        {activePage === "team" && (
          <TeamMembersView
            currentOrg={currentOrg}
            currentUser={currentUser}
            onNavigateToSettings={() => handlePageChange("org_settings")}
          />
        )}

        {activePage === "super_admin" && <SuperAdminView currentUser={currentUser} />}
      </main>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center">
          <div className="text-[13px] font-bold text-[#64748B]">Loading outreach pipeline...</div>
        </div>
      }
    >
      <AppContent />
    </Suspense>
  );
}
