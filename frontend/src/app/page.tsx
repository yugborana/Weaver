import { ResearchForm } from "@/components/ResearchForm";
import { Sparkles, ArrowRight, Activity, Globe } from "lucide-react";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col relative overflow-hidden">

      {/* Background Decor - cleaner, more subtle */}
      <div className="absolute top-0 left-0 w-full h-[500px] bg-gradient-to-b from-blue-900/10 to-transparent pointer-events-none z-0" />
      <div className="absolute top-[20%] left-[50%] -translate-x-1/2 w-[800px] h-[300px] bg-blue-500/5 rounded-[100%] blur-[120px] pointer-events-none z-0" />

      {/* Navbar Placeholder (for visual balance) */}
      <nav className="relative z-10 w-full max-w-7xl mx-auto p-6 flex justify-between items-center text-sm">
        <div className="flex items-center gap-2 font-semibold tracking-tight text-gray-200">
          <div className="h-6 w-6 bg-white rounded-full flex items-center justify-center text-black font-bold text-xs">W</div>
          Weaver
        </div>
        <div className="flex items-center gap-4">
          <a href="/evals" className="text-gray-400 hover:text-white transition-colors">Evaluations</a>
          <div className="text-gray-500">v1.0.0</div>
        </div>
      </nav>

      <div className="relative z-10 w-full max-w-5xl mx-auto flex-1 flex flex-col justify-center items-center p-4 text-center space-y-12">

        {/* Hero Text */}
        <div className="space-y-6 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-blue-200/80 backdrop-blur-sm animate-in fade-in slide-in-from-top-4 duration-1000">
            <Sparkles className="h-3 w-3" />
            <span>Autonomous Research Agent</span>
          </div>

          <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-tighter bg-clip-text text-transparent bg-gradient-to-b from-white via-white/90 to-white/50 animate-in fade-in zoom-in duration-1000 delay-100 pb-2">
            Knowledge, <br /> Weaved Instantly.
          </h1>

          <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto leading-relaxed animate-in fade-in slide-in-from-bottom-4 duration-1000 delay-200">
            Deep automated research that plans, searches, critiques, and writes
            comprehensive reports in minutes, not days.
          </p>
        </div>

        {/* Feature Grid (Decorative) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-3xl animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-300">
          <div className="glass-panel p-4 rounded-xl flex items-center gap-3 text-left">
            <Globe className="h-5 w-5 text-blue-400" />
            <div>
              <div className="text-sm font-semibold text-gray-200">Global Search</div>
              <div className="text-xs text-gray-500">Access to live web data</div>
            </div>
          </div>
          <div className="glass-panel p-4 rounded-xl flex items-center gap-3 text-left">
            <Activity className="h-5 w-5 text-purple-400" />
            <div>
              <div className="text-sm font-semibold text-gray-200">Self-Correction</div>
              <div className="text-xs text-gray-500">Iterative improvement loops</div>
            </div>
          </div>
          <div className="glass-panel p-4 rounded-xl flex items-center gap-3 text-left">
            <ArrowRight className="h-5 w-5 text-emerald-400" />
            <div>
              <div className="text-sm font-semibold text-gray-200">Structured Reports</div>
              <div className="text-xs text-gray-500">Ready-to-use citations</div>
            </div>
          </div>
        </div>

        {/* Action Area */}
        <div className="w-full max-w-2xl animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-500">
          <ResearchForm />
        </div>
      </div>

      <footer className="relative z-10 py-8 text-center text-xs text-gray-600 border-t border-white/5 mt-auto">
        <p>Powered by Groq & Supabase</p>
      </footer>
    </main>
  );
}
