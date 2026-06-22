import ScoreRing from "./ScoreRing";
import { ExternalLink, LockOpen, Lock, BookOpen, Lightbulb, ChevronDown } from "lucide-react";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const SCORE_LABELS: Record<string, { label: string; color: string }> = {
  semantic_score: { label: "Semantic", color: "bg-violet-500" },
  impact_score: { label: "Impact", color: "bg-blue-500" },
  oa_score: { label: "Open Access", color: "bg-emerald-500" },
  indexation_score: { label: "Indexation", color: "bg-cyan-500" },
  language_score: { label: "Language", color: "bg-amber-500" },
  apc_score: { label: "APC Cost", color: "bg-rose-500" },
  review_speed_score: { label: "Review Speed", color: "bg-teal-500" },
};

const RISK_COLORS: Record<string, { badge: string; dot: string; label: string }> = {
  low: { badge: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30", dot: "bg-emerald-400", label: "Low Risk" },
  medium: { badge: "bg-amber-500/20 text-amber-300 border-amber-500/30", dot: "bg-amber-400", label: "Medium Risk" },
  moderate: { badge: "bg-amber-500/20 text-amber-300 border-amber-500/30", dot: "bg-amber-400", label: "Moderate Risk" },
  high: { badge: "bg-rose-500/20 text-rose-300 border-rose-500/30", dot: "bg-rose-400", label: "High Risk" },
};

function ScoreBar({ label, score, color }: { label: string; score: number; color: string }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-20 text-zinc-400 font-medium flex-shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
      <span className="w-7 text-right font-bold text-zinc-300 tabular-nums">
        {Math.round(score)}
      </span>
    </div>
  );
}

export default function JournalCard({ journal }: { journal: any }) {
  const [expanded, setExpanded] = useState(false);
  const ai = journal.ai_analysis;
  const scores = journal.scores || {};

  return (
    <motion.div 
      whileHover={{ y: -5 }}
      transition={{ duration: 0.3 }}
      className="glass rounded-[2rem] p-7 transition-all duration-500 hover:shadow-[0_0_40px_rgba(139,92,246,0.2)] flex flex-col border border-white/10 hover:border-violet-500/30 relative overflow-hidden h-fit group bg-gradient-to-br from-white/[0.03] to-transparent"
    >
      {/* Animated Gradient Border Effect */}
      <div className="absolute inset-0 bg-gradient-to-r from-violet-600/0 via-violet-600/10 to-fuchsia-600/0 opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />

      {ai && (
        <div className="absolute top-0 right-0 bg-gradient-to-r from-violet-600 to-fuchsia-600 text-[10px] uppercase font-bold px-4 py-1.5 rounded-bl-[1.5rem] tracking-widest text-white shadow-lg">
          AI Analyzed
        </div>
      )}
      
      <div className="flex justify-between items-start mb-6 relative z-10">
        <div className="flex-1 pr-6 mt-2">
          <h3 className="text-xl font-bold leading-snug mb-3 text-transparent bg-clip-text bg-gradient-to-r from-white to-zinc-300 group-hover:to-white transition-colors">
            {journal.name}
          </h3>
          <p className="text-sm text-zinc-400 flex items-center font-medium">
            <BookOpen className="w-4 h-4 mr-2 text-violet-400 flex-shrink-0" />
            {journal.publisher}
          </p>
        </div>
        <div className="flex-shrink-0 mt-2 transform group-hover:scale-110 transition-transform duration-500">
          <ScoreRing score={scores.final_score || 0} />
        </div>
      </div>
      
      {/* Score breakdown bars */}
      <div className="space-y-1.5 mb-5 relative z-10">
        {Object.entries(SCORE_LABELS).map(([key, cfg]) => {
          const val = scores[key];
          if (val === undefined || val === null) return null;
          return (
            <ScoreBar
              key={key}
              label={cfg.label}
              score={val}
              color={cfg.color}
            />
          );
        })}
      </div>

      {/* Risk Assessment Badge */}
      {journal.risk_assessment && (
        <div className="mb-4 relative z-10">
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold ${
            RISK_COLORS[journal.risk_assessment.risk_level]?.badge || RISK_COLORS.low.badge
          }`}>
            <span className={`w-2 h-2 rounded-full ${
              RISK_COLORS[journal.risk_assessment.risk_level]?.dot || RISK_COLORS.low.dot
            }`} />
            <span>{RISK_COLORS[journal.risk_assessment.risk_level]?.label || "Unknown"} · Score {journal.risk_assessment.risk_score}</span>
          </div>
          {journal.risk_assessment.signals && journal.risk_assessment.signals.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {journal.risk_assessment.signals.map((signal: string) => (
                <span key={signal} className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-zinc-400 border border-white/5">
                  {signal.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="space-y-5 pt-5 border-t border-white/10 mt-auto relative z-10">
        <div className="flex items-center justify-between text-sm bg-black/20 p-3 rounded-xl border border-white/5">
          <span className="flex items-center font-medium">
            {journal.open_access ? (
              <><LockOpen className="w-4 h-4 mr-2 text-emerald-400" /> <span className="text-emerald-100/80">Open Access</span></>
            ) : (
              <><Lock className="w-4 h-4 mr-2 text-rose-400" /> <span className="text-rose-100/80">Closed Access</span></>
            )}
          </span>
          <span className="font-bold text-violet-300 tracking-wide">
            {journal.apc_usd > 0 ? `$${journal.apc_usd.toLocaleString()} APC` : "No APC"}
          </span>
        </div>
        
        {ai && (
          <button 
            onClick={() => setExpanded(!expanded)}
            className="flex items-center justify-between w-full text-sm font-semibold text-zinc-400 hover:text-white transition-colors py-2 px-1 group/btn"
          >
            <span className="flex items-center">
              <Lightbulb className="w-4 h-4 mr-2 text-amber-400/80 group-hover/btn:text-amber-400 transition-colors" />
              View AI Insights
            </span>
            <div className={`p-1 rounded-full bg-white/5 border border-white/10 transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`}>
              <ChevronDown className="w-4 h-4" />
            </div>
          </button>
        )}
        
        <AnimatePresence>
          {expanded && ai && (
            <motion.div 
              initial={{ height: 0, opacity: 0, marginTop: 0 }}
              animate={{ height: "auto", opacity: 1, marginTop: 12 }}
              exit={{ height: 0, opacity: 0, marginTop: 0 }}
              className="overflow-hidden"
            >
              <div className="space-y-5 pt-4 pb-5 text-sm text-zinc-300 bg-black/40 px-5 rounded-2xl border border-white/10 shadow-inner">
                <div>
                  <h4 className="font-bold text-violet-300 flex items-center mb-2 text-xs uppercase tracking-wider">
                    <div className="w-1.5 h-1.5 rounded-full bg-violet-400 mr-2" /> Compatibility
                  </h4>
                  <p className="text-sm leading-relaxed text-zinc-400 pl-3.5 border-l-2 border-violet-500/20">{ai.compatibility_reason}</p>
                </div>
                
                <div>
                  <h4 className="font-bold text-rose-300 flex items-center mb-2 text-xs uppercase tracking-wider">
                    <div className="w-1.5 h-1.5 rounded-full bg-rose-400 mr-2" /> Risk Assessment
                  </h4>
                  <p className="text-sm leading-relaxed text-zinc-400 pl-3.5 border-l-2 border-rose-500/20">{ai.predatory_risk}</p>
                </div>
                
                <div>
                  <h4 className="font-bold text-cyan-300 flex items-center mb-2 text-xs uppercase tracking-wider">
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 mr-2" /> Submission Strategy
                  </h4>
                  <p className="text-sm leading-relaxed text-zinc-400 pl-3.5 border-l-2 border-cyan-500/20">{ai.submission_strategy}</p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <a 
          href={journal.homepage_url || "#"} 
          target="_blank" 
          rel="noopener noreferrer"
          className="flex items-center justify-center w-full py-3.5 bg-white/5 hover:bg-violet-600 rounded-xl transition-all duration-300 text-sm font-bold text-white mt-6 border border-white/10 hover:border-violet-500 hover:shadow-[0_0_20px_rgba(139,92,246,0.4)] group/link"
        >
          Visit Journal Website 
          <ExternalLink className="w-4 h-4 ml-2 opacity-70 group-hover/link:opacity-100 group-hover/link:-translate-y-0.5 group-hover/link:translate-x-0.5 transition-all" />
        </a>
      </div>
    </motion.div>
  );
}
