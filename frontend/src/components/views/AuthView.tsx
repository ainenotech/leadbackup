"use client";

import React, { useState } from "react";
import Image from "next/image";
import {
  Lock,
  Mail,
  Building,
  User,
  ShieldCheck,
  Zap,
  Sparkles,
  Server,
  ArrowRight,
  Database,
  BarChart3,
  CheckCircle2,
  FileCheck2,
} from "lucide-react";
import { api, AuthUser, AuthOrganization } from "@/lib/api";

interface AuthViewProps {
  onLoginSuccess: (user: AuthUser, org: AuthOrganization, orgs: AuthOrganization[]) => void;
}

export default function AuthView({ onLoginSuccess }: AuthViewProps) {
  const [tab, setTab] = useState<"signin" | "register">("signin");

  // Sign In Form State
  const [signInEmail, setSignInEmail] = useState("");
  const [signInPassword, setSignInPassword] = useState("");
  const [signInLoading, setSignInLoading] = useState(false);
  const [signInError, setSignInError] = useState<string | null>(null);

  // Register Form State
  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regOrgName, setRegOrgName] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regConfirmPassword, setRegConfirmPassword] = useState("");
  const [regLoading, setRegLoading] = useState(false);
  const [regError, setRegError] = useState<string | null>(null);

  const handleSignIn = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSignInError(null);
    if (!signInEmail || !signInPassword) {
      setSignInError("Please enter both work email and password.");
      return;
    }

    try {
      setSignInLoading(true);
      const res = await api.login({
        email: signInEmail.trim(),
        password: signInPassword,
      });

      onLoginSuccess(res.user, res.organization, res.organizations || [res.organization]);
    } catch (err: any) {
      setSignInError(err.message || "Sign in failed. Please check your credentials.");
    } finally {
      setSignInLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegError(null);

    if (!regName || !regEmail || !regOrgName || !regPassword) {
      setRegError("Please fill in all required fields marked with *.");
      return;
    }
    if (regPassword.length < 6) {
      setRegError("Password must be at least 6 characters long.");
      return;
    }
    if (regPassword !== regConfirmPassword) {
      setRegError("Passwords do not match. Please re-check.");
      return;
    }

    try {
      setRegLoading(true);
      const res = await api.register({
        org_name: regOrgName.trim(),
        admin_email: regEmail.trim().toLowerCase(),
        password: regPassword,
        full_name: regName.trim(),
      });

      onLoginSuccess(res.user, res.organization, res.organizations || [res.organization]);
    } catch (err: any) {
      setRegError(err.message || "Registration failed. Try a different work email.");
    } finally {
      setRegLoading(false);
    }
  };

  const fillDemoCredentials = () => {
    setSignInEmail("mohit@nenotechnology.us");
    setSignInPassword("Admin@12345");
  };

  return (
    <div className="min-h-screen w-full bg-[#F8FAFC] flex items-center justify-center p-4 sm:p-6 lg:p-8">
      {/* Container Box */}
      <div className="w-full max-w-5xl bg-white border border-[#E2E8F0] rounded-2xl shadow-[0_20px_40px_-15px_rgba(15,23,42,0.08)] overflow-hidden grid grid-cols-1 lg:grid-cols-12">
        {/* Left Side: Brand Showcase & Features (Login Side Content) */}
        <div className="lg:col-span-5 bg-gradient-to-br from-[#F8FAFC] via-[#EFF6FF]/40 to-[#EEF2FF] border-b lg:border-b-0 lg:border-r border-[#E2E8F0] p-8 flex flex-col justify-between">
          <div>
            {/* Top Logo & Badge */}
            <div className="flex items-center gap-3 mb-6">
              <div className="relative w-36 h-9">
                <Image
                  src="/logo-dark.png"
                  alt="AINeotechnology"
                  fill
                  sizes="144px"
                  className="object-contain object-left"
                  priority
                />
              </div>
            </div>

            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#EFF6FF] border border-[#BFDBFE] text-[#1D4ED8] text-[11px] font-bold uppercase tracking-wider mb-4">
              <Zap className="w-3.5 h-3.5 text-[#2563EB]" />
              Autonomous Lead Intelligence
            </div>

            <h1 className="text-2xl font-extrabold text-[#0F172A] tracking-tight leading-snug mb-3">
              Executive Outreach &amp; Deliverability Platform
            </h1>
            <p className="text-[13.5px] text-[#64748B] leading-relaxed mb-6">
              Production-grade AI email generation, real-time engagement telemetry, and verified multi-tenant deliverability infrastructure.
            </p>

            {/* Feature Capability Highlights */}
            <div className="space-y-3.5">
              <div className="flex items-start gap-3 p-3 bg-white/80 rounded-xl border border-[#E2E8F0]/80 shadow-xs">
                <div className="w-8 h-8 rounded-lg bg-[#EFF6FF] text-[#2563EB] flex items-center justify-center shrink-0 mt-0.5">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-[13px] font-bold text-[#0F172A]">Gemini 2.5 Flash AI Engine</div>
                  <div className="text-[11.5px] text-[#64748B]">Autonomous email drafting and dynamic lead contextualization.</div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-white/80 rounded-xl border border-[#E2E8F0]/80 shadow-xs">
                <div className="w-8 h-8 rounded-lg bg-[#F0FDF4] text-[#059669] flex items-center justify-center shrink-0 mt-0.5">
                  <Database className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-[13px] font-bold text-[#0F172A]">RAG Vector Knowledge Base</div>
                  <div className="text-[11.5px] text-[#64748B]">Ground AI replies with PDFs, Docs, and company SLAs.</div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-white/80 rounded-xl border border-[#E2E8F0]/80 shadow-xs">
                <div className="w-8 h-8 rounded-lg bg-[#FAF5FF] text-[#7C3AED] flex items-center justify-center shrink-0 mt-0.5">
                  <BarChart3 className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-[13px] font-bold text-[#0F172A]">Sub-Second Live Telemetry</div>
                  <div className="text-[11.5px] text-[#64748B]">Track opens, clicks, replies, and booked appointments 24/7.</div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-white/80 rounded-xl border border-[#E2E8F0]/80 shadow-xs">
                <div className="w-8 h-8 rounded-lg bg-[#FEF3C7] text-[#D97706] flex items-center justify-center shrink-0 mt-0.5">
                  <Server className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-[13px] font-bold text-[#0F172A]">Render 24/7 Keep-Alive</div>
                  <div className="text-[11.5px] text-[#64748B]">Zero idle spin-down with autonomous background heartbeats.</div>
                </div>
              </div>
            </div>
          </div>

          {/* Infrastructure Health Footer */}
          <div className="mt-8 pt-4 border-t border-[#E2E8F0] flex items-center justify-between text-[11px] text-[#64748B]">
            <div className="flex items-center gap-1.5 font-medium">
              <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse"></span>
              <span>All Systems Operational</span>
            </div>
            <div className="font-mono text-[10.5px] font-semibold text-[#2563EB]">v2.6.4 Production</div>
          </div>
        </div>

        {/* Right Side: Interactive Login / Register Form */}
        <div className="lg:col-span-7 p-8 sm:p-10 flex flex-col justify-between">
          <div>
            {/* Header Titles */}
            <div className="mb-6">
              <h2 className="text-2xl font-extrabold text-[#0F172A] tracking-tight">
                Welcome to <span className="text-[#2563EB]">AINeo</span>
              </h2>
              <p className="text-[13.5px] text-[#64748B] mt-1">
                Autonomous lead intelligence and high-deliverability outreach suite.
              </p>
            </div>

            {/* Segmented Pill Tabs */}
            <div className="flex bg-[#F1F5F9] p-1 rounded-xl border border-[#E2E8F0] mb-6">
              <button
                type="button"
                onClick={() => setTab("signin")}
                className={`flex-1 py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
                  tab === "signin"
                    ? "bg-white text-[#0F172A] shadow-xs"
                    : "text-[#64748B] hover:text-[#0F172A]"
                }`}
              >
                🔑 Sign In
              </button>
              <button
                type="button"
                onClick={() => setTab("register")}
                className={`flex-1 py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
                  tab === "register"
                    ? "bg-white text-[#0F172A] shadow-xs"
                    : "text-[#64748B] hover:text-[#0F172A]"
                }`}
              >
                🚀 Register Workspace
              </button>
            </div>

            {/* TAB 1: SIGN IN */}
            {tab === "signin" && (
              <div>
                {signInError && (
                  <div className="mb-4 p-3 bg-[#FEF2F2] border border-[#FECACA] rounded-xl text-[12.5px] text-[#DC2626] font-medium flex items-center gap-2">
                    <span>⚠️</span>
                    <span>{signInError}</span>
                  </div>
                )}

                <form onSubmit={handleSignIn} className="space-y-4">
                  <div>
                    <label className="block text-[13px] font-bold text-[#0F172A] mb-1.5">
                      Work Email Address
                    </label>
                    <div className="relative">
                      <Mail className="w-4 h-4 absolute left-3.5 top-3 text-[#94A3B8]" />
                      <input
                        type="email"
                        required
                        value={signInEmail}
                        onChange={(e) => setSignInEmail(e.target.value)}
                        placeholder="name@company.com"
                        className="w-full pl-10 pr-3.5 py-2.5 bg-white border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] font-medium placeholder-[#94A3B8] focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/20 transition-all"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[13px] font-bold text-[#0F172A] mb-1.5">
                      Password
                    </label>
                    <div className="relative">
                      <Lock className="w-4 h-4 absolute left-3.5 top-3 text-[#94A3B8]" />
                      <input
                        type="password"
                        required
                        value={signInPassword}
                        onChange={(e) => setSignInPassword(e.target.value)}
                        placeholder="••••••••••••"
                        className="w-full pl-10 pr-3.5 py-2.5 bg-white border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] font-medium placeholder-[#94A3B8] focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/20 transition-all"
                      />
                    </div>
                  </div>

                  <div className="pt-1 flex items-center gap-2">
                    <button
                      type="submit"
                      disabled={signInLoading}
                      className="flex-1 py-3 px-4 bg-gradient-to-r from-[#2563EB] to-[#1D4ED8] hover:from-[#1D4ED8] hover:to-[#1E40AF] text-white font-bold text-[14px] rounded-xl shadow-[0_4px_14px_rgba(37,99,235,0.25)] flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                    >
                      {signInLoading ? (
                        <span>Authenticating...</span>
                      ) : (
                        <>
                          <span>Sign In to Workspace</span>
                          <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      onClick={fillDemoCredentials}
                      title="Quick fill demo credentials"
                      className="px-3.5 py-3 border border-[#E2E8F0] hover:bg-[#F8FAFC] text-[#475569] text-[12px] font-bold rounded-xl transition-all"
                    >
                      ⚡ Demo
                    </button>
                  </div>
                </form>

                {/* SSO Divider & Buttons */}
                <div className="relative my-6 text-center">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-[#E2E8F0]"></div>
                  </div>
                  <div className="relative inline-block px-3 bg-white text-[11px] font-bold text-[#94A3B8] uppercase tracking-wider">
                    or continue with SSO
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <a
                    href="http://localhost:8000/api/auth/oauth/microsoft/login"
                    className="flex items-center justify-center gap-2 py-2.5 px-3 border border-[#E2E8F0] hover:bg-[#F8FAFC] hover:border-[#CBD5E1] rounded-xl text-[12.5px] font-bold text-[#334155] shadow-xs transition-all"
                  >
                    <span>🪟</span>
                    <span>Microsoft 365</span>
                  </a>
                  <a
                    href="http://localhost:8000/api/auth/oauth/google/login"
                    className="flex items-center justify-center gap-2 py-2.5 px-3 border border-[#E2E8F0] hover:bg-[#F8FAFC] hover:border-[#CBD5E1] rounded-xl text-[12.5px] font-bold text-[#334155] shadow-xs transition-all"
                  >
                    <span>🌐</span>
                    <span>Google Workspace</span>
                  </a>
                </div>
              </div>
            )}

            {/* TAB 2: REGISTER WORKSPACE */}
            {tab === "register" && (
              <div>
                {regError && (
                  <div className="mb-4 p-3 bg-[#FEF2F2] border border-[#FECACA] rounded-xl text-[12.5px] text-[#DC2626] font-medium flex items-center gap-2">
                    <span>⚠️</span>
                    <span>{regError}</span>
                  </div>
                )}

                <form onSubmit={handleRegister} className="space-y-3.5">
                  <div>
                    <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                      Your Full Name *
                    </label>
                    <div className="relative">
                      <User className="w-4 h-4 absolute left-3.5 top-3 text-[#94A3B8]" />
                      <input
                        type="text"
                        required
                        value={regName}
                        onChange={(e) => setRegName(e.target.value)}
                        placeholder="Mohit Patel"
                        className="w-full pl-10 pr-3.5 py-2.5 bg-white border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] font-medium placeholder-[#94A3B8] focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/20 transition-all"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                      Work Email Address *
                    </label>
                    <div className="relative">
                      <Mail className="w-4 h-4 absolute left-3.5 top-3 text-[#94A3B8]" />
                      <input
                        type="email"
                        required
                        value={regEmail}
                        onChange={(e) => setRegEmail(e.target.value)}
                        placeholder="mohit@nenotechnology.us"
                        className="w-full pl-10 pr-3.5 py-2.5 bg-white border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] font-medium placeholder-[#94A3B8] focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/20 transition-all"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                      Company or Organization Name *
                    </label>
                    <div className="relative">
                      <Building className="w-4 h-4 absolute left-3.5 top-3 text-[#94A3B8]" />
                      <input
                        type="text"
                        required
                        value={regOrgName}
                        onChange={(e) => setRegOrgName(e.target.value)}
                        placeholder="Neno Technology"
                        className="w-full pl-10 pr-3.5 py-2.5 bg-white border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] font-medium placeholder-[#94A3B8] focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/20 transition-all"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                        Password *
                      </label>
                      <input
                        type="password"
                        required
                        value={regPassword}
                        onChange={(e) => setRegPassword(e.target.value)}
                        placeholder="Min 6 chars"
                        className="w-full px-3.5 py-2.5 bg-white border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] font-medium placeholder-[#94A3B8] focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/20 transition-all"
                      />
                    </div>
                    <div>
                      <label className="block text-[13px] font-bold text-[#0F172A] mb-1">
                        Confirm Password *
                      </label>
                      <input
                        type="password"
                        required
                        value={regConfirmPassword}
                        onChange={(e) => setRegConfirmPassword(e.target.value)}
                        placeholder="Re-enter"
                        className="w-full px-3.5 py-2.5 bg-white border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] font-medium placeholder-[#94A3B8] focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/20 transition-all"
                      />
                    </div>
                  </div>

                  <div className="pt-2">
                    <button
                      type="submit"
                      disabled={regLoading}
                      className="w-full py-3 px-4 bg-gradient-to-r from-[#2563EB] to-[#1D4ED8] hover:from-[#1D4ED8] hover:to-[#1E40AF] text-white font-bold text-[14px] rounded-xl shadow-[0_4px_14px_rgba(37,99,235,0.25)] flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                    >
                      {regLoading ? (
                        <span>Provisioning Workspace...</span>
                      ) : (
                        <>
                          <span>Create Account &amp; Launch Workspace</span>
                          <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>

          {/* Enterprise Security Guarantee from Old Project */}
          <div className="mt-8 pt-5 border-t border-[#F1F5F9] text-center text-[11.5px] text-[#94A3B8] leading-relaxed">
            <div className="flex items-center justify-center gap-1.5 font-bold text-[#64748B] mb-0.5">
              <ShieldCheck className="w-4 h-4 text-[#2563EB]" />
              <span>Enterprise Multi-Tenant Security · AES-256 Workspace Isolation</span>
            </div>
            <div>Protected by AINeotechnology Autonomous Infrastructure</div>
          </div>
        </div>
      </div>
    </div>
  );
}
