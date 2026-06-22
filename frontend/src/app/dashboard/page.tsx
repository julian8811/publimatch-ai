"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import JournalCard from "@/components/JournalCard";
import { Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";

function DashboardContent() {
  const searchParams = useSearchParams();
  const id = searchParams.get("id");
  const [matches, setMatches] = useState<any[]>([]);
  const [manuscript, setManuscript] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingStep, setLoadingStep] = useState(0);

  // Animated loading messages
  useEffect(() => {
    if (!loading) return;
    const interval = setInterval(() => {
      setLoadingStep((prev) => (prev < 3 ? prev + 1 : prev));
    }, 2500);
    return () => clearInterval(interval);
  }, [loading]);

  useEffect(() => {
    if (!id) return;
    
    const fetchData = async () => {
      try {
        // Fetch manuscript details
        const manuRes = await fetch(`http://127.0.0.1:8003/api/manuscripts/${id}`);
        if (manuRes.ok) {
          const manuData = await manuRes.json();
          setManuscript(manuData);
        }

        // Fetch matches
        const matchesRes = await fetch(`http://127.0.0.1:8003/api/matches/${id}`);
        if (matchesRes.ok) {
          const matchesData = await matchesRes.json();
          setMatches(matchesData);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [id]);

  const loadingSteps = [
    "Reading manuscript document structure...",
    "Extracting abstract and keywords with Gemini...",
    "Running vector similarity search on OpenAlex...",
    "Performing double-pass AI journal compatibility analysis..."
  ];

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center py-24 relative overflow-hidden">
        {/* Dynamic Background Blurs */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-violet-600/10 blur-[120px] rounded-full pointer-events-none" />
        
        <div className="z-10 text-center max-w-md mx-auto px-6">
          <Loader2 className="w-16 h-16 text-violet-500 animate-spin mx-auto mb-6" />
          <h2 className="text-2xl font-bold mb-3 bg-clip-text text-transparent bg-gradient-to-r from-white to-zinc-400">
            Running Semantic Analysis
          </h2>
          <div className="h-6 overflow-hidden relative w-full mb-8">
            <p className="text-sm text-zinc-400 animate-pulse">
              {loadingSteps[loadingStep]}
            </p>
          </div>
          
          {/* Progress Bar */}
          <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all duration-1000 ease-out"
              style={{ width: `${((loadingStep + 1) / 4) * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-zinc-500 mt-2 font-mono">
            <span>Step {loadingStep + 1} of 4</span>
            <span>{Math.round(((loadingStep + 1) / 4) * 100)}%</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 md:p-12 max-w-7xl mx-auto w-full relative">
      {/* Background Blurs */}
      <div className="absolute top-10 left-10 w-[400px] h-[400px] bg-violet-500/5 blur-[100px] rounded-full pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[400px] h-[400px] bg-cyan-500/5 blur-[100px] rounded-full pointer-events-none" />

      <div className="z-10 relative">
        <Link href="/" className="inline-flex items-center text-sm text-zinc-400 hover:text-white transition-colors mb-8 group">
          <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" /> Back to Upload
        </Link>
        
        <div className="mb-14 text-center md:text-left relative">
          <div className="absolute -inset-4 bg-gradient-to-r from-violet-600/20 to-fuchsia-600/20 blur-3xl rounded-full -z-10"></div>
          <h1 className="text-4xl md:text-6xl font-extrabold mb-4 text-transparent bg-clip-text bg-gradient-to-r from-white via-zinc-100 to-zinc-400 drop-shadow-sm">
            Academic Recommendation Report
          </h1>
          <p className="text-lg text-zinc-400 font-medium max-w-3xl">
            Below is the semantic profile extracted from your manuscript and the corresponding best-matched scientific journals, ranked by relevance and acceptance probability.
          </p>
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          
          {/* Column 1: Manuscript Profile */}
          <div className="lg:col-span-1 space-y-6">
            <div className="glass rounded-[2rem] p-7 border border-white/10 relative overflow-hidden bg-gradient-to-br from-white/[0.04] to-transparent shadow-2xl">
              <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-violet-500 via-fuchsia-500 to-cyan-500 shadow-[0_0_20px_rgba(139,92,246,0.6)]" />
              
              <h2 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-zinc-300 mb-6 flex items-center tracking-wide">
                <span className="w-2.5 h-2.5 rounded-full bg-violet-400 mr-3 shadow-[0_0_10px_rgba(139,92,246,0.8)]" />
                Manuscript Profile
              </h2>
              
              {manuscript ? (
                <div className="space-y-5">
                  <div>
                    <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">Title</span>
                    <h3 className="text-sm font-semibold text-zinc-200 mt-1 leading-snug">
                      {manuscript.title}
                    </h3>
                  </div>
                  
                  {manuscript.article_type && (
                    <div>
                      <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">Article Type</span>
                      <div className="mt-1">
                        <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-medium bg-violet-500/10 text-violet-300 border border-violet-500/20">
                          {manuscript.article_type}
                        </span>
                      </div>
                    </div>
                  )}

                  {manuscript.keywords && manuscript.keywords.length > 0 && (
                    <div>
                      <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">Extracted Keywords</span>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {manuscript.keywords.map((kw: string) => (
                          <span key={kw} className="px-2 py-0.5 rounded bg-white/5 text-[11px] text-zinc-300 border border-white/5">
                            {kw}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {manuscript.abstract && (
                    <div>
                      <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">Abstract Summary</span>
                      <p className="text-xs text-zinc-400 leading-relaxed mt-1.5 whitespace-pre-line bg-black/20 p-3 rounded-lg border border-white/5 max-h-[220px] overflow-y-auto">
                        {manuscript.abstract}
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-zinc-500 italic">No manuscript details available.</p>
              )}
            </div>
          </div>

          {/* Column 2 & 3: Journal Matches */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white flex items-center">
                Recommended Journals
                <span className="ml-2 text-xs font-mono px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 border border-violet-500/30">
                  {matches.length} matches
                </span>
              </h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {matches.map((match) => (
                <JournalCard key={match.openalex_id} journal={match} />
              ))}
            </div>
            
            {matches.length === 0 && (
              <div className="text-center py-20 glass rounded-2xl border border-white/5">
                <p className="text-zinc-400">No matches found. Try uploading a different manuscript.</p>
              </div>
            )}
          </div>
          
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><Loader2 className="w-10 h-10 animate-spin text-violet-500" /></div>}>
      <DashboardContent />
    </Suspense>
  );
}
