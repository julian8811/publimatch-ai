"use client";

import { useState, useRef } from "react";
import { UploadCloud, File as FileIcon, X, Loader2, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { config } from "@/lib/config";
import { authHeaders, clearToken } from "@/lib/auth";

export default function Dropzone() {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setIsDragging(true);
    else if (e.type === "dragleave") setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    setError(null);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    // Validate file size (max 50MB)
    if (file.size > 50 * 1024 * 1024) {
      setError("File is too large. Maximum size is 50 MB.");
      return;
    }

    // Validate file type
    const allowedTypes = [".pdf", ".docx"];
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!allowedTypes.includes(ext)) {
      setError("Invalid file type. Only PDF and DOCX files are supported.");
      return;
    }

    setIsUploading(true);
    setError(null);
    const headers = authHeaders();
    
    try {
      const projRes = await fetch(`${config.apiUrl}/projects/`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ name: "AI Match Project", description: "Uploaded via UI" })
      });

      if (projRes.status === 401) {
        clearToken();
        setError("Your session has expired. Please log in again.");
        setIsUploading(false);
        return;
      }

      if (!projRes.ok) {
        const errBody = await projRes.json().catch(() => ({}));
        setError(errBody.detail || `Project creation failed (${projRes.status})`);
        setIsUploading(false);
        return;
      }

      const projData = await projRes.json();
      
      const formData = new FormData();
      formData.append("file", file);
      formData.append("project_id", projData.id);
      
      const uploadRes = await fetch(`${config.apiUrl}/manuscripts/upload`, {
        method: "POST",
        headers,
        body: formData
      });

      if (uploadRes.status === 401) {
        clearToken();
        setError("Your session has expired. Please log in again.");
        setIsUploading(false);
        return;
      }

      if (!uploadRes.ok) {
        const errBody = await uploadRes.json().catch(() => ({}));
        setError(errBody.detail || `Upload failed (${uploadRes.status})`);
        setIsUploading(false);
        return;
      }

      const manuscript = await uploadRes.json();
      router.push(`/dashboard?id=${manuscript.id}`);
    } catch (e) {
      if (e instanceof TypeError && e.message === "Failed to fetch") {
        setError("Network error: Unable to reach the server. Make sure the backend is running.");
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
      console.error("Upload error:", e);
      setIsUploading(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto mt-12 relative z-10">
      {/* Background Glow */}
      <div className="absolute -inset-1 bg-gradient-to-r from-violet-600 to-fuchsia-600 rounded-[3rem] blur opacity-20 group-hover:opacity-40 transition duration-1000 group-hover:duration-200"></div>
      
      <div
        className={`relative group rounded-[2.5rem] p-12 text-center transition-all duration-500 ease-out border overflow-hidden
          ${isDragging 
            ? "border-violet-400 bg-violet-900/20 scale-[1.02] shadow-[0_0_40px_rgba(139,92,246,0.3)]" 
            : "border-white/10 glass hover:border-violet-500/50 hover:bg-white/5 shadow-2xl"}
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        {/* Animated background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-violet-500/5 via-transparent to-fuchsia-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,.docx"
          onChange={handleFileSelect}
        />
        
        <AnimatePresence mode="wait">
          {!file ? (
            <motion.div 
              key="empty" 
              initial={{ opacity: 0, y: 10 }} 
              animate={{ opacity: 1, y: 0 }} 
              exit={{ opacity: 0, scale: 0.95 }} 
              transition={{ duration: 0.3 }}
              className="flex flex-col items-center cursor-pointer relative z-10"
            >
              <motion.div 
                animate={{ y: [0, -8, 0] }} 
                transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
                className="relative p-6 rounded-full bg-gradient-to-b from-white/5 to-white/0 border border-white/10 mb-8 group-hover:border-violet-500/30 group-hover:shadow-[0_0_30px_rgba(139,92,246,0.2)] transition-all duration-300"
              >
                <div className="absolute inset-0 bg-violet-500/20 rounded-full blur-xl group-hover:bg-violet-500/30 transition-colors"></div>
                <UploadCloud className="w-12 h-12 text-violet-300 relative z-10" />
              </motion.div>
              
              <h3 className="text-2xl font-bold tracking-tight mb-3 text-transparent bg-clip-text bg-gradient-to-r from-white to-zinc-300">
                Drop your manuscript here
              </h3>
              <p className="text-zinc-400 text-sm md:text-base font-medium">
                Supports <span className="text-violet-300">PDF</span> or <span className="text-fuchsia-300">DOCX</span> files
              </p>
              
              <div className="mt-8 px-6 py-2.5 rounded-full border border-white/10 bg-white/5 text-sm font-semibold text-zinc-300 group-hover:bg-violet-500/20 group-hover:text-white group-hover:border-violet-500/30 transition-all duration-300">
                Browse Files
              </div>
            </motion.div>
          ) : (
            <motion.div 
              key="file" 
              initial={{ scale: 0.95, opacity: 0 }} 
              animate={{ scale: 1, opacity: 1 }} 
              className="flex flex-col items-center relative z-10"
            >
              <div className="w-full flex items-center space-x-5 bg-black/40 backdrop-blur-xl p-5 rounded-2xl border border-white/10 shadow-inner">
                <div className="p-4 bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20 rounded-xl text-violet-300 border border-violet-500/20 shadow-[0_0_15px_rgba(139,92,246,0.15)]">
                  <FileIcon className="w-8 h-8" />
                </div>
                <div className="text-left flex-1 min-w-0">
                  <p className="text-base font-semibold text-zinc-100 truncate">{file.name}</p>
                  <p className="text-xs text-zinc-400 font-mono mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
                <button 
                  onClick={(e) => { e.stopPropagation(); setFile(null); }} 
                  className="p-2 hover:bg-rose-500/20 hover:text-rose-400 rounded-full transition-colors border border-transparent hover:border-rose-500/30"
                >
                  <X className="w-5 h-5 text-zinc-500 transition-colors" />
                </button>
              </div>
              
              <button
                onClick={(e) => { e.stopPropagation(); handleUpload(); }}
                disabled={isUploading}
                className="mt-10 px-10 py-4 bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white rounded-full font-bold tracking-wide transition-all duration-300 shadow-[0_0_30px_rgba(139,92,246,0.4)] hover:shadow-[0_0_40px_rgba(217,70,239,0.6)] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-[0_0_30px_rgba(139,92,246,0.4)] flex items-center space-x-3 hover:scale-105 active:scale-95"
              >
                {isUploading ? (
                  <><Loader2 className="w-5 h-5 animate-spin" /><span>Analyzing Semantic Profile...</span></>
                ) : (
                  <span>Discover Matching Journals</span>
                )}
              </button>

              {error && (
                <motion.div
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 flex items-start gap-2 bg-rose-500/10 border border-rose-500/30 rounded-xl p-3 text-sm text-rose-200 w-full"
                >
                  <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <p>{error}</p>
                    <button
                      onClick={(e) => { e.stopPropagation(); setError(null); }}
                      className="mt-1 text-xs text-rose-300/70 hover:text-rose-200 underline underline-offset-2"
                    >
                      Dismiss
                    </button>
                  </div>
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
