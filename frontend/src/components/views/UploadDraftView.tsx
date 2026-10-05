"use client";

import React, { useState } from "react";
import HeaderBanner from "@/components/layout/HeaderBanner";
import { api, TemplateItem } from "@/lib/api";
import { Upload, FileSpreadsheet, CheckCircle2, AlertCircle, RefreshCw, ArrowRight } from "lucide-react";
import { PageId } from "@/components/layout/Sidebar";

interface UploadDraftViewProps {
  onNavigate: (page: PageId) => void;
}

export default function UploadDraftView({ onNavigate }: UploadDraftViewProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | number>("");
  const [generating, setGenerating] = useState(false);
  const [generateResult, setGenerateResult] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"new" | "skipped_sent" | "skipped_drafted">("new");

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setUploading(true);
      setUploadResult(null);
      setGenerateResult(null);

      try {
        const [res, tplsRes] = await Promise.all([
          api.uploadLeadsFile(selectedFile),
          api.getTemplates(),
        ]);
        setUploadResult(res);
        setTemplates(tplsRes.templates || []);
        if (tplsRes.templates && tplsRes.templates.length > 0) {
          setSelectedTemplateId(tplsRes.templates[0].id);
        }
      } catch (err: any) {
        alert(err.message || "Failed to process lead sheet");
      } finally {
        setUploading(false);
      }
    }
  };

  const handleGenerateDrafts = async () => {
    if (!uploadResult?.new_leads || uploadResult.new_leads.length === 0) return;
    setGenerating(true);
    setGenerateResult(null);

    try {
      const res = await api.generateDrafts({
        leads: uploadResult.new_leads,
        template_id: String(selectedTemplateId),
      });
      setGenerateResult(res);
    } catch (err: any) {
      alert(err.message || "Draft generation failed");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <HeaderBanner
        title="Upload Leads &amp; Generate Drafts"
        subtitle="Import fresh lead spreadsheets, automatically skip already-contacted leads, and generate personalized drafts."
        badgeText="Smart Deduplication"
        badgeType="live"
      />

      {/* Drag & Drop Upload Card */}
      <div className="bg-white border-2 border-dashed border-[#CBD5E1] rounded-2xl p-8 text-center hover:border-[#2563EB] transition-colors shadow-[0_1px_3px_rgba(0,0,0,0.02)]">
        <input
          type="file"
          id="lead-file-input"
          accept=".csv, .xlsx"
          onChange={handleFileChange}
          className="hidden"
        />
        <label
          htmlFor="lead-file-input"
          className="cursor-pointer flex flex-col items-center justify-center space-y-3"
        >
          <div className="w-14 h-14 rounded-2xl bg-[#EFF6FF] text-[#2563EB] flex items-center justify-center text-2xl shadow-xs">
            <Upload className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-bold text-[#0F172A] text-base">
              {file ? file.name : "Drag and drop your CSV or Excel lead sheet here"}
            </h3>
            <p className="text-[12.5px] text-[#64748B] mt-1">
              Required column: <code className="text-[#2563EB] font-semibold">&apos;email&apos;</code>. Auto-detected: <code className="text-[#475569]">&apos;Full Name&apos; / &apos;name&apos;, &apos;Company Name&apos; / &apos;company&apos;, &apos;lead_id&apos;, &apos;last_activity_date&apos;</code>
            </p>
          </div>
          <span className="px-4 py-2 bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-semibold text-[13px] rounded-lg shadow-sm transition-colors">
            {uploading ? "Analyzing & Deduplicating..." : "Browse Files"}
          </span>
        </label>
      </div>

      {/* Upload Results & Metrics */}
      {uploadResult && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Summary Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
              <span className="text-[12px] font-semibold text-[#64748B]">Total in Uploaded Sheet</span>
              <div className="text-2xl font-bold text-[#0F172A] mt-1">{uploadResult.total_rows}</div>
            </div>
            <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
              <span className="text-[12px] font-semibold text-[#D97706]">Skipped (Already Sent)</span>
              <div className="text-2xl font-bold text-[#D97706] mt-1">{uploadResult.skipped_sent_count}</div>
            </div>
            <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
              <span className="text-[12px] font-semibold text-[#64748B]">Pending in Review</span>
              <div className="text-2xl font-bold text-[#0F172A] mt-1">{uploadResult.skipped_drafted_count}</div>
            </div>
            <div className="bg-white border border-[#BFDBFE] bg-[#EFF6FF] rounded-xl p-4 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
              <span className="text-[12px] font-bold text-[#1D4ED8]">New Leads Ready</span>
              <div className="text-2xl font-bold text-[#2563EB] mt-1">{uploadResult.new_leads_count}</div>
            </div>
          </div>

          {/* Tab Ribbon */}
          <div className="flex items-center gap-2 border-b border-[#E2E8F0] pb-2">
            <button
              onClick={() => setActiveTab("new")}
              className={`px-4 py-2 rounded-lg text-[13px] font-semibold transition-all ${
                activeTab === "new"
                  ? "bg-[#2563EB] text-white shadow-xs"
                  : "bg-white text-[#475569] border border-[#E2E8F0] hover:bg-[#F8FAFC]"
              }`}
            >
              ✨ New Leads Ready ({uploadResult.new_leads_count})
            </button>
            <button
              onClick={() => setActiveTab("skipped_sent")}
              className={`px-4 py-2 rounded-lg text-[13px] font-semibold transition-all ${
                activeTab === "skipped_sent"
                  ? "bg-[#2563EB] text-white shadow-xs"
                  : "bg-white text-[#475569] border border-[#E2E8F0] hover:bg-[#F8FAFC]"
              }`}
            >
              🛡️ Skipped / Already Emailed ({uploadResult.skipped_sent_count})
            </button>
            <button
              onClick={() => setActiveTab("skipped_drafted")}
              className={`px-4 py-2 rounded-lg text-[13px] font-semibold transition-all ${
                activeTab === "skipped_drafted"
                  ? "bg-[#2563EB] text-white shadow-xs"
                  : "bg-white text-[#475569] border border-[#E2E8F0] hover:bg-[#F8FAFC]"
              }`}
            >
              ⏳ Awaiting Approval ({uploadResult.skipped_drafted_count})
            </button>
          </div>

          {/* Tab 1: New Leads Ready */}
          {activeTab === "new" && (
            <div className="space-y-4">
              {uploadResult.new_leads_count > 0 ? (
                <>
                  {/* Template Picker */}
                  <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex items-center justify-between flex-wrap gap-4">
                    <div>
                      <h4 className="font-bold text-[#0F172A] text-[13.5px]">Select Email Template for this Cohort:</h4>
                      <p className="text-[12px] text-[#64748B]">Assigns this template to all {uploadResult.new_leads_count} leads for personalized AI generation</p>
                    </div>
                    <div className="w-full sm:w-80">
                      <select
                        value={selectedTemplateId}
                        onChange={(e) => setSelectedTemplateId(e.target.value)}
                        className="w-full text-[13px] bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg px-3 py-2 text-[#0F172A] font-medium focus:outline-none focus:border-[#2563EB]"
                      >
                        {templates.map((tpl) => (
                          <option key={tpl.id} value={tpl.id}>
                            {tpl.name} [{tpl.category || "Outreach"}]
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Generate Button */}
                  <div className="flex items-center justify-between p-4 bg-[#EFF6FF] border border-[#BFDBFE] rounded-xl">
                    <div>
                      <div className="text-[13px] font-bold text-[#1D4ED8]">Ready to generate personalized drafts</div>
                      <div className="text-[11.5px] text-[#3B82F6]">Safe human-in-the-loop review will be available before sending</div>
                    </div>
                    <button
                      onClick={handleGenerateDrafts}
                      disabled={generating}
                      className="px-5 py-2.5 bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-bold text-[13px] rounded-lg shadow-sm transition-colors flex items-center gap-2"
                    >
                      {generating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <span>🚀</span>}
                      <span>{generating ? "Generating AI Drafts..." : `Generate AI Drafts (${uploadResult.new_leads_count})`}</span>
                    </button>
                  </div>

                  {generateResult && (
                    <div className="p-4 bg-[#ECFDF5] border border-[#A7F3D0] rounded-xl flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <CheckCircle2 className="w-5 h-5 text-[#059669]" />
                        <span className="text-[13px] font-bold text-[#065F46]">
                          Successfully generated {generateResult.created_count} draft(s)! Ready for review.
                        </span>
                      </div>
                      <button
                        onClick={() => onNavigate("email")}
                        className="px-3.5 py-1.5 bg-[#059669] hover:bg-[#047857] text-white font-semibold text-[12px] rounded-lg shadow-xs transition-colors flex items-center gap-1.5"
                      >
                        <span>Open Email Review Studio</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}

                  {/* Leads Preview Table */}
                  <div className="bg-white border border-[#E2E8F0] rounded-xl overflow-hidden shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
                    <table className="w-full text-left text-[12.5px]">
                      <thead className="bg-[#F8FAFC] text-[#475569] border-b border-[#E2E8F0] text-[11px] uppercase font-semibold">
                        <tr>
                          <th className="py-2.5 px-3">Email Address</th>
                          <th className="py-2.5 px-3">Name</th>
                          <th className="py-2.5 px-3">Company</th>
                          <th className="py-2.5 px-3">Lead ID</th>
                          <th className="py-2.5 px-3">Last Activity</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#F1F5F9]">
                        {uploadResult.new_leads.slice(0, 50).map((l: any, idx: number) => (
                          <tr key={idx} className="hover:bg-[#F8FAFC]">
                            <td className="py-2.5 px-3 font-semibold text-[#0F172A]">{l.email}</td>
                            <td className="py-2.5 px-3 text-[#475569]">{l.name || l["Full Name"] || l["Contact Name"] || l["Name"] || "—"}</td>
                            <td className="py-2.5 px-3 text-[#475569]">{l.company || l["Company Name"] || l["Organization"] || l["Company"] || "—"}</td>
                            <td className="py-2.5 px-3 text-[#64748B] font-mono text-[11px]">{l.lead_id || "—"}</td>
                            <td className="py-2.5 px-3 text-[#64748B] text-[11px]">{l.last_activity_date || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <div className="bg-white border border-[#E2E8F0] rounded-xl p-8 text-center text-[#64748B]">
                  No new leads found in this spreadsheet. All contacts were either already emailed or are currently drafted.
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Skipped Sent */}
          {activeTab === "skipped_sent" && (
            <div className="bg-white border border-[#E2E8F0] rounded-xl overflow-hidden shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
              <table className="w-full text-left text-[12.5px]">
                <thead className="bg-[#F8FAFC] text-[#475569] border-b border-[#E2E8F0] text-[11px] uppercase font-semibold">
                  <tr>
                    <th className="py-2.5 px-3">Email Address</th>
                    <th className="py-2.5 px-3">Name</th>
                    <th className="py-2.5 px-3">Company</th>
                    <th className="py-2.5 px-3">Deduplication Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F1F5F9]">
                  {uploadResult.skipped_sent.map((l: any, idx: number) => (
                    <tr key={idx} className="hover:bg-[#F8FAFC]">
                      <td className="py-2.5 px-3 font-semibold text-[#0F172A]">{l.email}</td>
                      <td className="py-2.5 px-3 text-[#475569]">{l.name || l["Full Name"] || l["Contact Name"] || l["Name"] || "—"}</td>
                      <td className="py-2.5 px-3 text-[#475569]">{l.company || l["Company Name"] || l["Organization"] || l["Company"] || "—"}</td>
                      <td className="py-2.5 px-3">
                        <span className="badge badge-sent text-[10.5px]">Already Emailed (Protected)</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Tab 3: Skipped Drafted */}
          {activeTab === "skipped_drafted" && (
            <div className="bg-white border border-[#E2E8F0] rounded-xl overflow-hidden shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
              <table className="w-full text-left text-[12.5px]">
                <thead className="bg-[#F8FAFC] text-[#475569] border-b border-[#E2E8F0] text-[11px] uppercase font-semibold">
                  <tr>
                    <th className="py-2.5 px-3">Email Address</th>
                    <th className="py-2.5 px-3">Name</th>
                    <th className="py-2.5 px-3">Company</th>
                    <th className="py-2.5 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F1F5F9]">
                  {uploadResult.skipped_drafted.map((l: any, idx: number) => (
                    <tr key={idx} className="hover:bg-[#F8FAFC]">
                      <td className="py-2.5 px-3 font-semibold text-[#0F172A]">{l.email}</td>
                      <td className="py-2.5 px-3 text-[#475569]">{l.name || l["Full Name"] || l["Contact Name"] || l["Name"] || "—"}</td>
                      <td className="py-2.5 px-3 text-[#475569]">{l.company || l["Company Name"] || l["Organization"] || l["Company"] || "—"}</td>
                      <td className="py-2.5 px-3">
                        <span className="badge badge-drafted text-[10.5px]">Draft in Review</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
