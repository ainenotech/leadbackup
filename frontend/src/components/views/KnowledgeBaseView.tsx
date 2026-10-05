"use client";

import React, { useState, useEffect } from "react";
import {
  BookOpen,
  Upload,
  Database,
  Search,
  Trash2,
  Cpu,
  Layers,
  Sparkles,
  FileText,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import { api } from "@/lib/api";

const CATEGORIES = [
  "Auto-Detect",
  "Company Overview",
  "Pricing & Packages",
  "SLAs & Security",
  "Engineering Capabilities",
  "Case Studies",
  "FAQs",
  "Onboarding",
  "Documentation",
  "Custom",
];

export default function KnowledgeBaseView() {
  const [activeTab, setActiveTab] = useState<"upload" | "docs" | "search" | "settings">("upload");
  const [summary, setSummary] = useState<{
    total_chunks: number;
    total_documents: number;
    documents: any[];
    embedding_model: string;
  }>({
    total_chunks: 0,
    total_documents: 0,
    documents: [],
    embedding_model: "models/gemini-embedding-001",
  });
  const [isLoading, setIsLoading] = useState(true);

  // Upload Tab State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [category, setCategory] = useState("Auto-Detect");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Search Sandbox State
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Filter docs
  const [docFilter, setDocFilter] = useState("");

  const loadKbData = async () => {
    try {
      setIsLoading(true);
      const res = await api.getKbSummary();
      setSummary(res);
    } catch (e: any) {
      console.warn("Failed to load KB summary:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadKbData();
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    try {
      setIsUploading(true);
      setUploadMessage(null);
      await api.uploadKbFile(selectedFile, category !== "Auto-Detect" ? category : undefined);
      setUploadMessage({
        type: "success",
        text: `Successfully ingested "${selectedFile.name}" into vector memory!`,
      });
      setSelectedFile(null);
      await loadKbData();
    } catch (err: any) {
      setUploadMessage({
        type: "error",
        text: err.message || "Failed to ingest document.",
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (title: string) => {
    if (!confirm(`Are you sure you want to delete all vector chunks for "${title}"?`)) return;
    try {
      await api.deleteKbDocument(title);
      await loadKbData();
    } catch (err: any) {
      alert("Error deleting document: " + err.message);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    try {
      setIsSearching(true);
      const res = await api.searchKb(searchQuery.trim(), 4);
      setSearchResults(res.chunks || []);
    } catch (err: any) {
      alert("Search failed: " + err.message);
    } finally {
      setIsSearching(false);
    }
  };

  const handleClearAll = async () => {
    if (!confirm("⚠️ Irreversible Action: Delete ALL documents and vector chunks from knowledge base?")) return;
    try {
      await api.clearKb();
      await loadKbData();
      alert("Knowledge base cleared.");
    } catch (err: any) {
      alert("Error clearing KB: " + err.message);
    }
  };

  const filteredDocs = (summary.documents || []).filter((d) =>
    docFilter ? (d.title || "").toLowerCase().includes(docFilter.toLowerCase()) : true
  );

  return (
    <div className="space-y-6">
      {/* Top Header Banner */}
      <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5">
              <span className="text-2xl">📚</span>
              <h1 className="text-2xl font-extrabold text-[#0F172A] tracking-tight">
                Knowledge Base Hub
              </h1>
              <span className="bg-gradient-to-r from-[#0D9488] to-[#0EA5E9] text-white text-[11px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                RAG-Powered
              </span>
            </div>
            <p className="text-[13.5px] text-[#64748B] max-w-3xl leading-relaxed">
              Upload documents (PDF, DOCX, CSV, XLSX, JSON, Markdown, TXT) to automatically chunk, embed, and store in vector memory.
              When leads reply via email, our AI reply engine retrieves verified company facts to draft grounded, high-converting answers.
            </p>
          </div>

          <button
            onClick={loadKbData}
            disabled={isLoading}
            className="self-start sm:self-center inline-flex items-center gap-2 px-3.5 py-2 bg-[#F8FAFC] hover:bg-[#F1F5F9] border border-[#CBD5E1] text-[#334155] rounded-xl text-[13px] font-bold transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* KPI Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <div className="bg-[#F8FAFC] border border-[#E2E8F0] border-l-4 border-l-[#0D9488] rounded-xl p-4">
            <div className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider">Active Chunks</div>
            <div className="text-2xl font-extrabold text-[#0F172A] font-mono mt-1">
              {summary.total_chunks}
            </div>
            <div className="text-[11.5px] font-semibold text-[#0D9488] mt-1">Indexed in Vector Memory</div>
          </div>

          <div className="bg-[#F8FAFC] border border-[#E2E8F0] border-l-4 border-l-[#2563EB] rounded-xl p-4">
            <div className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider">Source Documents</div>
            <div className="text-2xl font-extrabold text-[#0F172A] font-mono mt-1">
              {summary.total_documents}
            </div>
            <div className="text-[11.5px] font-semibold text-[#2563EB] mt-1">Uploaded &amp; Processed</div>
          </div>

          <div className="bg-[#F8FAFC] border border-[#E2E8F0] border-l-4 border-l-[#7C3AED] rounded-xl p-4">
            <div className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider">Vector Dimension</div>
            <div className="text-2xl font-extrabold text-[#0F172A] font-mono mt-1">768-D</div>
            <div className="text-[11.5px] font-semibold text-[#7C3AED] mt-1">Float Vector Embeddings</div>
          </div>

          <div className="bg-[#F8FAFC] border border-[#E2E8F0] border-l-4 border-l-[#D97706] rounded-xl p-4">
            <div className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider">Embedding Engine</div>
            <div className="text-base font-extrabold text-[#0F172A] font-mono mt-2 truncate" title={summary.embedding_model}>
              {summary.embedding_model.replace("models/", "")}
            </div>
            <div className="text-[11.5px] font-semibold text-[#D97706] mt-1">Cosine Similarity Scan</div>
          </div>
        </div>
      </div>

      {/* Segmented Navigation Tabs */}
      <div className="flex bg-white border border-[#E2E8F0] rounded-xl p-1 shadow-xs max-w-xl">
        <button
          type="button"
          onClick={() => setActiveTab("upload")}
          className={`flex-1 py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
            activeTab === "upload"
              ? "bg-[#2563EB] text-white shadow-xs"
              : "text-[#64748B] hover:text-[#0F172A]"
          }`}
        >
          📥 Upload &amp; Ingest
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("docs")}
          className={`flex-1 py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
            activeTab === "docs"
              ? "bg-[#2563EB] text-white shadow-xs"
              : "text-[#64748B] hover:text-[#0F172A]"
          }`}
        >
          📁 Documents ({summary.total_documents})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("search")}
          className={`flex-1 py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
            activeTab === "search"
              ? "bg-[#2563EB] text-white shadow-xs"
              : "text-[#64748B] hover:text-[#0F172A]"
          }`}
        >
          🔍 Vector Sandbox
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("settings")}
          className={`flex-1 py-2 text-center text-[13px] font-bold rounded-lg transition-all ${
            activeTab === "settings"
              ? "bg-[#2563EB] text-white shadow-xs"
              : "text-[#64748B] hover:text-[#0F172A]"
          }`}
        >
          ⚙️ Settings
        </button>
      </div>

      {/* TAB 1: UPLOAD & INGEST */}
      {activeTab === "upload" && (
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs max-w-3xl">
          <h2 className="text-lg font-bold text-[#0F172A] mb-1">
            Ingest Knowledge Document
          </h2>
          <p className="text-[13px] text-[#64748B] mb-5">
            Supported formats: PDF, DOCX, CSV, XLSX, JSON, Markdown, and TXT files.
          </p>

          {uploadMessage && (
            <div
              className={`p-4 rounded-xl border text-[13px] font-medium mb-5 flex items-center gap-2.5 ${
                uploadMessage.type === "success"
                  ? "bg-[#F0FDF4] border-[#BBF7D0] text-[#15803D]"
                  : "bg-[#FEF2F2] border-[#FECACA] text-[#DC2626]"
              }`}
            >
              {uploadMessage.type === "success" ? (
                <CheckCircle2 className="w-5 h-5 shrink-0" />
              ) : (
                <AlertCircle className="w-5 h-5 shrink-0" />
              )}
              <span>{uploadMessage.text}</span>
            </div>
          )}

          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label className="block text-[13px] font-bold text-[#0F172A] mb-2">
                Select File to Upload
              </label>
              <div className="border-2 border-dashed border-[#CBD5E1] hover:border-[#2563EB] rounded-2xl p-6 text-center cursor-pointer transition-all bg-[#F8FAFC]">
                <input
                  type="file"
                  required
                  accept=".pdf,.docx,.csv,.xlsx,.xls,.json,.md,.txt"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="hidden"
                  id="kb-file-input"
                />
                <label htmlFor="kb-file-input" className="cursor-pointer">
                  <div className="w-12 h-12 rounded-xl bg-[#EFF6FF] text-[#2563EB] flex items-center justify-center mx-auto mb-3">
                    <Upload className="w-6 h-6" />
                  </div>
                  {selectedFile ? (
                    <div>
                      <div className="text-[14px] font-bold text-[#0F172A]">{selectedFile.name}</div>
                      <div className="text-[12px] text-[#64748B] mt-0.5">
                        {(selectedFile.size / 1024).toFixed(1)} KB · Ready to ingest
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="text-[14px] font-bold text-[#0F172A]">Click to select a document</div>
                      <div className="text-[12px] text-[#64748B] mt-0.5">
                        Drag &amp; drop or click to browse files
                      </div>
                    </div>
                  )}
                </label>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1.5">
                  Knowledge Category
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-white border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] font-medium focus:outline-none focus:border-[#2563EB]"
                >
                  {CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[13px] font-bold text-[#0F172A] mb-1.5">
                  Chunk Overlap Ratio
                </label>
                <input
                  type="text"
                  disabled
                  value="800 chars / 120 overlap"
                  className="w-full px-3.5 py-2.5 bg-[#F1F5F9] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#64748B] font-mono cursor-not-allowed"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={!selectedFile || isUploading}
                className="py-3 px-6 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[14px] font-bold rounded-xl shadow-xs transition-all disabled:opacity-50 flex items-center gap-2"
              >
                {isUploading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Chunking &amp; Embedding...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Ingest &amp; Generate Vector Embeddings</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* TAB 2: DOCUMENTS LIST */}
      {activeTab === "docs" && (
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
            <div>
              <h2 className="text-lg font-bold text-[#0F172A]">
                Indexed Source Documents
              </h2>
              <p className="text-[13px] text-[#64748B]">
                Documents stored and active in RAG vector memory for autonomous reply generation.
              </p>
            </div>

            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 absolute left-3 top-3 text-[#94A3B8]" />
              <input
                type="text"
                value={docFilter}
                onChange={(e) => setDocFilter(e.target.value)}
                placeholder="Filter by title..."
                className="w-full pl-9 pr-3.5 py-2 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13px] text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
              />
            </div>
          </div>

          {filteredDocs.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-[#CBD5E1] rounded-xl">
              <BookOpen className="w-10 h-10 text-[#94A3B8] mx-auto mb-2" />
              <div className="text-[14px] font-bold text-[#334155]">No documents found</div>
              <div className="text-[12.5px] text-[#64748B] mt-1">
                Upload your first PDF or document in the &ldquo;Upload &amp; Ingest&rdquo; tab.
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredDocs.map((doc, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl hover:border-[#CBD5E1] transition-all"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-[#EFF6FF] text-[#2563EB] flex items-center justify-center shrink-0">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="text-[13.5px] font-bold text-[#0F172A]">{doc.title}</div>
                      <div className="flex items-center gap-2 text-[11.5px] text-[#64748B] mt-0.5">
                        <span className="bg-[#E2E8F0] px-2 py-0.5 rounded text-[#334155] font-medium">
                          {doc.category || "Documentation"}
                        </span>
                        <span>•</span>
                        <span className="font-mono text-[#2563EB] font-bold">
                          {doc.chunk_count || doc.chunks || 1} vector chunks
                        </span>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDelete(doc.title)}
                    className="p-2 text-[#EF4444] hover:bg-[#FEF2F2] rounded-lg transition-all"
                    title="Delete document and chunks"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: VECTOR SEARCH SANDBOX */}
      {activeTab === "search" && (
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs max-w-4xl">
          <h2 className="text-lg font-bold text-[#0F172A] mb-1">
            Vector Similarity Sandbox
          </h2>
          <p className="text-[13px] text-[#64748B] mb-5">
            Test how the AI reply agent matches incoming customer questions to your ingested knowledge chunks in real-time.
          </p>

          <form onSubmit={handleSearch} className="flex gap-3 mb-6">
            <input
              type="text"
              required
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="e.g. What is your pricing model, or what SLA do you guarantee?"
              className="flex-1 px-4 py-2.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl text-[13.5px] text-[#0F172A] font-medium focus:outline-none focus:border-[#2563EB]"
            />
            <button
              type="submit"
              disabled={isSearching}
              className="py-2.5 px-5 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13px] font-bold rounded-xl shadow-xs transition-all disabled:opacity-50 flex items-center gap-2"
            >
              {isSearching ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              <span>Test Query</span>
            </button>
          </form>

          {searchResults.length > 0 && (
            <div className="space-y-4">
              <div className="text-[12.5px] font-bold text-[#64748B] uppercase tracking-wider">
                Top {searchResults.length} Retrieved Knowledge Chunks:
              </div>

              {searchResults.map((chunk, idx) => (
                <div key={idx} className="p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl space-y-2">
                  <div className="flex items-center justify-between text-[12px]">
                    <div className="font-bold text-[#0F172A] flex items-center gap-2">
                      <span>📄 {chunk.title}</span>
                      <span className="bg-[#E2E8F0] px-2 py-0.5 rounded text-[10.5px] text-[#475569]">
                        {chunk.category || "FAQ"}
                      </span>
                    </div>
                    <span className="bg-[#EFF6FF] border border-[#BFDBFE] text-[#1D4ED8] font-mono font-bold px-2 py-0.5 rounded">
                      Similarity: {chunk.score ? (chunk.score * 100).toFixed(1) + "%" : "Match"}
                    </span>
                  </div>
                  <p className="text-[13px] text-[#334155] leading-relaxed whitespace-pre-wrap font-sans bg-white p-3 rounded-lg border border-[#E2E8F0]">
                    {chunk.content}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: SETTINGS */}
      {activeTab === "settings" && (
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-xs max-w-2xl">
          <h2 className="text-lg font-bold text-[#0F172A] mb-1">
            Knowledge Base Maintenance
          </h2>
          <p className="text-[13px] text-[#64748B] mb-5">
            Manage vector memory retention and clear obsolete documents.
          </p>

          <div className="border border-[#FECACA] bg-[#FEF2F2] rounded-xl p-5">
            <h3 className="text-[14px] font-bold text-[#991B1B] mb-1 flex items-center gap-2">
              <Trash2 className="w-4 h-4" />
              <span>Danger Zone: Clear Vector Memory</span>
            </h3>
            <p className="text-[12.5px] text-[#7F1D1D] mb-4 leading-relaxed">
              This will erase all documents and chunks currently stored in PostgreSQL. You can re-upload your documents at any time.
            </p>
            <button
              onClick={handleClearAll}
              className="py-2.5 px-4 bg-[#DC2626] hover:bg-[#B91C1C] text-white text-[13px] font-bold rounded-xl transition-all shadow-xs"
            >
              Clear All Knowledge Documents
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
