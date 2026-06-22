import Link from "next/link";
import Image from "next/image";

export default function Header() {
  return (
    <header className="sticky top-0 z-50 w-full glass border-b border-white/10 backdrop-blur-md px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <Link href="/" className="flex items-center space-x-3 group">
          <div className="relative w-10 h-10 rounded-xl overflow-hidden border border-violet-500/30 group-hover:border-violet-500/60 transition-colors shadow-[0_0_15px_rgba(139,92,246,0.2)]">
            <Image
              src="/logo.png"
              alt="PubliMatch AI Logo"
              fill
              sizes="40px"
              className="object-cover group-hover:scale-110 transition-transform duration-300"
            />
          </div>
          <div className="flex flex-col">
            <span className="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-white to-violet-300 group-hover:to-violet-400 transition-all duration-300">
              PubliMatch <span className="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">AI</span>
            </span>
            <span className="text-[10px] text-zinc-400 tracking-wider uppercase font-semibold -mt-1">
              Academic Journal Matcher
            </span>
          </div>
        </Link>
        
        <nav className="hidden md:flex items-center space-x-8 text-sm font-medium">
          <Link href="/" className="text-zinc-300 hover:text-white transition-colors">
            Upload Manuscript
          </Link>
          <a
            href="https://openalex.org/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-zinc-400 hover:text-white transition-colors flex items-center space-x-1"
          >
            <span>OpenAlex API</span>
          </a>
        </nav>
        
        <div>
          <Link
            href="/"
            className="px-5 py-2 text-xs font-semibold text-white bg-violet-600/80 hover:bg-violet-600 rounded-full border border-violet-500/30 transition-all shadow-[0_0_15px_rgba(139,92,246,0.2)]"
          >
            New Analysis
          </Link>
        </div>
      </div>
    </header>
  );
}
