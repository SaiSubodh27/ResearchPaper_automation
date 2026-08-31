import { useEffect, useMemo, useState } from "react";
import {
  ArrowUpRight,
  Award,
  Bot,
  ChevronDown,
  ChevronRight,
  Download,
  ExternalLink,
  FileText,
  Loader2,
  RefreshCw,
  Search,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import { askToPath, topathUrl, type ToPathResponse } from "@/lib/topath";

// Local static backup import so papers display 100% instantly even before pushing to GitHub
import localBackupFeed from "../data/daily_material_papers.json";

// --- Configuration: GitHub Raw Feed & Local API URLs ---
const GITHUB_USERNAME = "SaiSubodh27";
const GITHUB_REPO = "Researchpaperautomation";
const RAW_GITHUB_FEED_URL = `https://raw.githubusercontent.com/${GITHUB_USERNAME}/${GITHUB_REPO}/main/data/daily_material_papers.json`;
const LOCAL_API_URL = "http://localhost:8000/api/material-science/daily";

// --- Types ---
export interface JournalInfo {
  journal_name: string;
  is_peer_reviewed?: boolean;
  citation_score?: number;
  h_index?: number;
  quartile: "Q1" | "Q2" | "Q3" | "Q4" | "Preprint (Unranked)" | string;
  quality_tier?: string;
  publisher?: string;
}

export interface MetricResult {
  metric: string;
  value: string;
  comparison?: string;
  unit?: string;
  note?: string;
}

export interface ResearchPaper {
  id: string;
  title: string;
  authors: string[];
  publishedAt: string;
  year?: number;
  journal?: JournalInfo;
  journal_name?: string;
  quartile?: string;
  abstract?: string;
  aim?: string;
  whyItMatters?: string;
  simpleConclusion?: string;
  results?: MetricResult[];
  citation_count?: number;
  doi?: string;
  pdf_url?: string;
  sourceUrl?: string;
  identifier?: string;
  dataset?: { name?: string; url?: string };
  limitations?: string[];
  keywords?: string[];
  topics?: string[];
  subfield?: string;
  ai_summary?: string;
}

const QUARTILE_STYLES: Record<string, { badge: string; border: string; text: string }> = {
  Q1: {
    badge: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800",
    border: "border-emerald-500",
    text: "Top-Tier (Q1)",
  },
  Q2: {
    badge: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800",
    border: "border-blue-500",
    text: "High Quality (Q2)",
  },
  Q3: {
    badge: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800",
    border: "border-amber-500",
    text: "Moderate (Q3)",
  },
  Q4: {
    badge: "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-950/60 dark:text-orange-300 dark:border-orange-800",
    border: "border-orange-500",
    text: "Indexed (Q4)",
  },
  "Preprint (Unranked)": {
    badge: "bg-gray-100 text-gray-700 border-gray-200 dark:bg-neutral-800 dark:text-neutral-300 dark:border-neutral-700",
    border: "border-gray-400",
    text: "Preprint",
  },
};

function getQuartileStyle(quartile = "Q2") {
  return QUARTILE_STYLES[quartile] || QUARTILE_STYLES["Q2"];
}

function formatDate(dateStr?: string) {
  if (!dateStr) return "2026";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return dateStr;
  }
}

// --- Detail View Component ---
function DetailPanel({
  paper,
  onAsk,
  onBack,
}: {
  paper: ResearchPaper;
  onAsk: () => void;
  onBack: () => void;
}) {
  const journal = paper.journal || {
    journal_name: paper.journal_name || "Academic Journal",
    quartile: paper.quartile || "Q2",
    quality_tier: paper.quartile ? `${paper.quartile} Journal` : "Peer-Reviewed",
  };

  const style = getQuartileStyle(journal.quartile);
  const pdfLink = paper.pdf_url;
  const doiLink = paper.doi || paper.sourceUrl;

  return (
    <main className="min-w-0 bg-white text-gray-900 dark:bg-neutral-950 dark:text-neutral-100 min-h-screen">
      <div className="mx-auto w-full max-w-6xl px-5 py-7 md:px-8 lg:px-12 lg:py-10">
        
        {/* Navigation */}
        <div className="mb-8 flex items-center justify-between gap-4 border-b border-gray-200 pb-5 dark:border-neutral-800">
          <button
            onClick={onBack}
            className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-gray-500 transition-colors hover:text-orange-500 dark:text-neutral-400"
          >
            ← Back to papers library
          </button>

          <div className="flex items-center gap-3">
            {pdfLink && (
              <a
                href={pdfLink}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 border border-emerald-200 bg-emerald-50 px-3.5 py-2 text-xs font-semibold text-emerald-700 transition-colors hover:bg-emerald-100 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300"
              >
                <Download size={14} /> Download PDF
              </a>
            )}
            <button
              onClick={onAsk}
              className="inline-flex items-center gap-2 border border-orange-500 bg-orange-500 px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-orange-600 shadow-sm"
            >
              <Bot size={14} /> Ask AI Copilot
            </button>
          </div>
        </div>

        {/* Paper Header */}
        <article>
          <div className={`max-w-4xl border-l-4 pl-5 md:pl-7 ${style.border}`}>
            
            <div className="mb-4 flex flex-wrap items-center gap-2.5 text-xs font-semibold">
              <span className={`inline-flex items-center gap-1.5 px-3 py-1 border rounded-full ${style.badge}`}>
                <Award size={13} />
                {journal.journal_name} ({journal.quartile})
              </span>

              {paper.citation_count !== undefined && (
                <span className="border border-gray-200 bg-gray-50 px-2.5 py-1 rounded-full text-gray-600 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-400">
                  📊 {paper.citation_count} Citations
                </span>
              )}
            </div>

            <h1 className="font-display text-3xl leading-[1.1] tracking-[-0.03em] text-gray-900 dark:text-white md:text-5xl font-bold">
              {paper.title}
            </h1>

            <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-gray-600 dark:text-neutral-400">
              <span className="font-medium">{paper.authors?.join(" · ") || "Unknown Authors"}</span>
              <span className="text-gray-300 dark:text-neutral-700">|</span>
              <span>{formatDate(paper.publishedAt)}</span>
              {doiLink && (
                <a
                  href={doiLink}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 font-medium text-orange-600 hover:underline dark:text-orange-400"
                >
                  DOI Link <ExternalLink size={13} />
                </a>
              )}
            </div>
          </div>

          {/* Abstract / AI Executive Summary */}
          <div className="mt-10 max-w-4xl space-y-10">
            <section className="border border-gray-200 bg-gray-50/50 p-6 dark:border-neutral-800 dark:bg-neutral-900/40 rounded-lg">
              <h2 className="mb-3 text-xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-2">
                <FileText size={18} className="text-orange-500" /> Abstract & Overview
              </h2>
              <p className="text-[16px] leading-8 text-gray-700 dark:text-neutral-300">
                {paper.ai_summary || paper.abstract || paper.aim || "No abstract is available for this paper."}
              </p>
            </section>
          </div>
        </article>
      </div>
    </main>
  );
}

// --- Main Page Component ---
export default function AICopilot() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [topic, setTopic] = useState("All Topics");
  const [papers, setPapers] = useState<ResearchPaper[]>([]);
  const [loading, setLoading] = useState(true);

  function mapRawPaperToSchema(p: any, idx: number): ResearchPaper {
    const jInfo = p.journal || {
      journal_name: p.journal_name || "Academic Journal",
      quartile: p.quartile || "Q2",
      quality_tier: p.quartile ? `${p.quartile} Journal` : "Peer-Reviewed"
    };

    return {
      id: p.id || `paper-${idx}`,
      title: p.title || "Untitled Research Paper",
      authors: Array.isArray(p.authors) ? p.authors : (p.authors ? [p.authors] : ["Unknown Author"]),
      publishedAt: p.publishedAt || p.date_published || (p.year ? `${p.year}` : "2026"),
      year: p.year || 2026,
      journal: jInfo,
      journal_name: jInfo.journal_name,
      quartile: jInfo.quartile,
      abstract: p.abstract || p.ai_summary || "No abstract available for this paper.",
      aim: p.abstract || p.ai_summary || "No aim information available.",
      ai_summary: p.ai_summary,
      citation_count: p.citation_count || 0,
      doi: p.doi || "",
      pdf_url: p.pdf_url || "",
      sourceUrl: p.doi || p.pdf_url || "",
      keywords: [p.subfield || "Material Science", jInfo.quartile || "Q2"],
      topics: [p.subfield || "Material Science", "All Topics"]
    };
  }

  async function loadDailyAutomationFeed() {
    setLoading(true);
    let fetchedData = null;

    try {
      // 1. Try local API
      const resApi = await fetch(LOCAL_API_URL);
      if (resApi.ok) {
        fetchedData = await resApi.json();
      }
    } catch {
      fetchedData = null;
    }

    if (!fetchedData || !fetchedData.papers || fetchedData.papers.length === 0) {
      try {
        // 2. Try raw GitHub feed
        const resGit = await fetch(RAW_GITHUB_FEED_URL);
        if (resGit.ok) {
          fetchedData = await resGit.json();
        }
      } catch {
        fetchedData = null;
      }
    }

    // 3. Fallback to local import backup file so papers ALWAYS display
    if (!fetchedData || !fetchedData.papers || fetchedData.papers.length === 0) {
      fetchedData = localBackupFeed;
    }

    if (fetchedData && fetchedData.papers) {
      const mapped = fetchedData.papers.map((p: any, idx: number) => mapRawPaperToSchema(p, idx));
      setPapers(mapped);
    }
    setLoading(false);
  }

  useEffect(() => {
    loadDailyAutomationFeed();
  }, []);

  const paper = papers.find((item) => item.id === selectedId) ?? null;

  const filteredPapers = useMemo(() => {
    return papers.filter((item) => {
      const titleText = (item.title + " " + item.authors.join(" ") + " " + (item.journal?.journal_name || "")).toLowerCase();
      const matchesQuery = titleText.includes(query.toLowerCase());
      const matchesTopic = topic === "All Topics" || (item.keywords && item.keywords.includes(topic)) || item.quartile === topic;
      return matchesQuery && matchesTopic;
    });
  }, [papers, query, topic]);

  return (
    <div className="min-h-screen bg-white text-gray-900 dark:bg-neutral-950 dark:text-neutral-100 font-sans">
      {!paper ? (
        <main className="mx-auto w-full max-w-[1500px] px-5 py-7 md:px-8 lg:px-10 lg:py-10">
          
          {/* Header */}
          <div className="mb-8 flex flex-col gap-4 border-b border-gray-200 pb-6 dark:border-neutral-800 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="mb-1 font-mono text-xs font-bold uppercase tracking-widest text-orange-600 dark:text-orange-400 flex items-center gap-1.5">
                <Sparkles size={14} /> Automated Daily Research Feed
              </p>
              <h1 className="font-display text-3xl font-bold tracking-tight text-gray-900 dark:text-white md:text-5xl">
                Material Science Daily Papers
              </h1>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={loadDailyAutomationFeed}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold border border-gray-200 rounded-lg hover:border-orange-500 dark:border-neutral-800 dark:hover:border-orange-500"
              >
                <RefreshCw size={13} className={loading ? "animate-spin text-orange-500" : ""} />
                Sync Daily Feed
              </button>
              <span className="px-3 py-1 text-xs font-bold bg-orange-50 text-orange-700 border border-orange-200 rounded-full dark:bg-orange-950/60 dark:text-orange-300 dark:border-orange-800">
                {filteredPapers.length} Papers Listed
              </span>
            </div>
          </div>

          {/* Search & Topic Filters */}
          <div className="mb-6 flex flex-col gap-3 border border-gray-200 bg-gray-50/60 p-3 dark:border-neutral-800 dark:bg-neutral-900/60 rounded-lg md:flex-row">
            <div className="relative min-w-0 flex-1">
              <Search size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search papers by title, author, or journal..."
                className="w-full bg-transparent py-2.5 pl-10 pr-3 text-sm text-gray-900 outline-none placeholder:text-gray-400 dark:text-white dark:placeholder:text-neutral-500"
              />
            </div>
            <div className="relative border-l border-gray-200 pl-3 dark:border-neutral-800 md:w-60">
              <select
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                className="h-full w-full cursor-pointer appearance-none bg-transparent pr-7 text-xs font-semibold text-gray-700 outline-none dark:text-neutral-300"
              >
                <option value="All Topics">All Subfields</option>
                <option value="Material Science">Material Science</option>
                <option value="Q1">Q1 (Top-Tier Only)</option>
                <option value="Q2">Q2 (High Quality)</option>
                <option value="Q3">Q3 (Moderate Quality)</option>
                <option value="Q4">Q4 (Indexed)</option>
              </select>
              <ChevronDown size={14} className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-gray-400" />
            </div>
          </div>

          {/* Enhanced Paper List Table */}
          <div className="overflow-hidden border border-gray-200 dark:border-neutral-800 rounded-lg shadow-sm">
            <div className="grid grid-cols-[minmax(0,1fr)_180px_130px_40px] gap-4 border-b border-gray-200 bg-gray-100 px-5 py-3.5 text-xs font-bold uppercase tracking-wider text-gray-600 dark:bg-neutral-900 dark:border-neutral-800">
              <span>Paper & Journal Details</span>
              <span>Journal Quality</span>
              <span>Date</span>
              <span />
            </div>

            <div className="divide-y divide-gray-200 dark:divide-neutral-800">
              {loading ? (
                <div className="px-5 py-12 text-center text-sm text-gray-500 flex items-center justify-center gap-2">
                  <Loader2 size={16} className="animate-spin text-orange-500" />
                  Fetching automated daily Material Science papers...
                </div>
              ) : filteredPapers.length === 0 ? (
                <div className="px-5 py-12 text-center text-sm text-gray-500">No papers match your search filter.</div>
              ) : (
                filteredPapers.map((item) => {
                  const j = item.journal || { journal_name: item.journal_name || "Academic Journal", quartile: item.quartile || "Q2" };
                  const quartileStyle = getQuartileStyle(j.quartile);

                  return (
                    <button
                      key={item.id}
                      onClick={() => setSelectedId(item.id)}
                      className="group grid w-full grid-cols-[minmax(0,1fr)_180px_130px_40px] items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-gray-50 dark:hover:bg-neutral-900/60"
                    >
                      {/* Paper Title & Authors & Journal Name */}
                      <div className="min-w-0 pr-4">
                        <span className="block truncate font-bold text-base text-gray-900 dark:text-white group-hover:text-orange-600 dark:group-hover:text-orange-400">
                          {item.title}
                        </span>
                        <div className="mt-1 flex items-center gap-2 text-xs text-gray-500 dark:text-neutral-400">
                          <span className="font-semibold text-gray-700 dark:text-neutral-300">🏛️ {j.journal_name}</span>
                          <span>•</span>
                          <span>👥 {item.authors.slice(0, 2).join(", ")}{item.authors.length > 2 ? " et al." : ""}</span>
                        </div>
                      </div>

                      {/* Journal Quality Badge */}
                      <div>
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-bold rounded-full border ${quartileStyle.badge}`}>
                          <Award size={12} /> {j.quartile}
                        </span>
                      </div>

                      {/* Date */}
                      <div className="text-xs text-gray-500 dark:text-neutral-400 font-mono">
                        {formatDate(item.publishedAt)}
                      </div>

                      {/* Chevron Arrow */}
                      <ChevronRight size={18} className="text-gray-400 group-hover:translate-x-1 group-hover:text-orange-500 transition-transform" />
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </main>
      ) : (
        <DetailPanel paper={paper} onBack={backToPapers} onAsk={() => setAssistantOpen(true)} />
      )}
    </div>
  );
}
