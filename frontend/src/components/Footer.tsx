import Link from "next/link";

export default function Footer() {
  return (
    <footer className="w-full glass border-t border-white/10 py-8 px-6 mt-auto">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-zinc-400">
        <div className="flex flex-col items-center md:items-start gap-1">
          <p className="font-semibold text-zinc-300">
            PubliMatch <span className="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">AI</span>
          </p>
          <p className="text-xs">
            Advanced academic journal recommendations powered by OpenAlex & Gemini 2.5.
          </p>
        </div>
        
        <div className="flex gap-6 text-xs font-medium">
          <Link href="/" className="hover:text-white transition-colors">
            Upload
          </Link>
          <a
            href="https://openalex.org/"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white transition-colors"
          >
            OpenAlex
          </a>
          <a
            href="https://deepmind.google/technologies/gemini/"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white transition-colors"
          >
            Gemini AI
          </a>
        </div>
        
        <div className="text-xs text-zinc-500">
          © {new Date().getFullYear()} PubliMatch AI. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
