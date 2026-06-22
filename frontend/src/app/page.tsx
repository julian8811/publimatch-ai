import Dropzone from "@/components/Dropzone";
import { Search, Brain, BarChart3, ShieldCheck } from "lucide-react";

export default function Home() {
  return (
    <main className="flex-1 flex flex-col items-center justify-center py-16 px-6 relative overflow-hidden">
      {/* Dynamic Background Blurs */}
      <div className="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-violet-600/10 blur-[130px] rounded-full pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 translate-x-1/2 translate-y-1/2 w-[600px] h-[600px] bg-fuchsia-600/10 blur-[130px] rounded-full pointer-events-none" />
      
      <div className="z-10 text-center max-w-4xl mx-auto w-full flex-1 flex flex-col justify-center">
        <div className="inline-block mx-auto px-4 py-1.5 rounded-full border border-violet-500/30 bg-violet-500/10 text-violet-300 text-sm font-medium mb-8 shadow-[0_0_15px_rgba(139,92,246,0.2)]">
          ✨ AI-Powered Journal Matching
        </div>
        <h1 className="text-4xl md:text-6xl lg:text-7xl font-extrabold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-b from-white to-zinc-400">
          Find the Perfect Home <br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-violet-400 via-fuchsia-400 to-cyan-400 animate-pulse">
            for Your Research
          </span>
        </h1>
        <p className="text-base md:text-lg text-zinc-400 mb-12 max-w-2xl mx-auto leading-relaxed">
          Upload your manuscript and let our advanced semantic AI analyze your work to recommend the best scientific journals with the highest acceptance probability.
        </p>
        
        <Dropzone />
        
        {/* Features Highlights Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-24 max-w-5xl mx-auto text-left">
          <div className="glass rounded-2xl p-6 border border-white/5 hover:border-violet-500/20 transition-all group">
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 text-violet-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <Search className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-semibold mb-2 text-white">Semantic Search</h3>
            <p className="text-sm text-zinc-400 leading-relaxed">
              Leverages pgvector and database indexes to match your manuscript text against millions of publications from OpenAlex.
            </p>
          </div>
          
          <div className="glass rounded-2xl p-6 border border-white/5 hover:border-fuchsia-500/20 transition-all group">
            <div className="w-10 h-10 rounded-xl bg-fuchsia-500/10 text-fuchsia-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <Brain className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-semibold mb-2 text-white">Double-Pass Gemini AI</h3>
            <p className="text-sm text-zinc-400 leading-relaxed">
              Extracts metadata structure and reviews final matches to evaluate compatibility, submission strategy, and cover letters.
            </p>
          </div>
          
          <div className="glass rounded-2xl p-6 border border-white/5 hover:border-cyan-500/20 transition-all group">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-semibold mb-2 text-white">Predatory Journal Audit</h3>
            <p className="text-sm text-zinc-400 leading-relaxed">
              Analyzes publisher integrity, APC pricing anomalies, and broad scope claims to shield your work from predatory publishers.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
