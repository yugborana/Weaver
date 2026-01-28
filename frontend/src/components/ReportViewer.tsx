"use client";

import { FileText, Link as LinkIcon, Download, ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/api";

interface ReportViewerProps {
    report: any;
}

export function ReportViewer({ report }: ReportViewerProps) {
    if (!report) return null;

    return (
        <div className="max-w-5xl mx-auto space-y-12 animate-in fade-in duration-700 pb-20">

            {/* Header Section */}
            <div className="text-center space-y-6 pt-8 pb-12 border-b border-white/10">
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-500/10 text-blue-400 rounded-full text-xs font-medium uppercase tracking-wider mb-4">
                    Generated Report
                </div>
                <h1 className="text-4xl md:text-6xl font-bold text-white tracking-tight leading-tight max-w-4xl mx-auto">
                    {report.title}
                </h1>
                <div className="max-w-3xl mx-auto text-lg text-gray-400 leading-relaxed font-light">
                    {report.abstract}
                </div>

                <div className="flex justify-center gap-4 pt-4">
                    <button
                        onClick={() => window.print()}
                        className="flex items-center gap-2 px-6 py-2.5 bg-white text-black hover:bg-gray-200 rounded-full text-sm font-medium transition-all"
                    >
                        <Download className="h-4 w-4" />
                        Download PDF
                    </button>
                </div>
            </div>

            {/* Main Content & Sidebar Layout */}
            <div className="flex flex-col lg:flex-row gap-12">

                {/* Main Content Column */}
                <div className="flex-1 space-y-12">
                    {report.sections.map((section: any, idx: number) => (
                        <div key={idx} className="group relative pl-8 border-l border-white/10 hover:border-blue-500/50 transition-colors duration-500">
                            <div className="absolute -left-[5px] top-0 h-2 w-2 rounded-full bg-blue-500/20 group-hover:bg-blue-500 transition-colors" />

                            <h2 className="text-2xl font-bold text-white mb-6 tracking-tight flex items-baseline gap-3">
                                <span className="text-sm font-mono text-gray-500 opacity-50">0{idx + 1}.</span>
                                {section.title}
                            </h2>

                            <div className="prose prose-invert prose-lg max-w-none text-gray-300 leading-8">
                                {section.content}
                            </div>

                            {section.source_ids?.length > 0 && (
                                <div className="mt-6 flex flex-wrap gap-2 opacity-50 group-hover:opacity-100 transition-opacity">
                                    {section.source_ids.map((sid: string) => (
                                        <span key={sid} className="text-xs font-mono text-blue-400 bg-blue-500/5 px-2 py-1 rounded">
                                            [{sid}]
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}

                    {/* Conclusion Box */}
                    <div className="glass-panel p-8 rounded-2xl border-l-4 border-l-purple-500 mt-12">
                        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                            <FileText className="h-5 w-5 text-purple-400" />
                            Key Takeaways
                        </h2>
                        <p className="text-gray-300 leading-relaxed">
                            {report.conclusion}
                        </p>
                    </div>
                </div>

                {/* Sidebar (Sources) */}
                <div className="lg:w-80 space-y-8">
                    <div className="sticky top-8">
                        <h3 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <LinkIcon className="h-4 w-4" />
                            References
                        </h3>

                        <div className="space-y-4 max-h-[calc(100vh-200px)] overflow-y-auto pr-2 custom-scrollbar">
                            {report.references.map((ref: any, idx: number) => (
                                <a
                                    key={idx}
                                    href={ref.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="block p-4 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/20 transition-all group"
                                >
                                    <div className="flex items-start justify-between gap-2 mb-2">
                                        <span className="text-xs font-mono text-blue-400">[{ref.id}]</span>
                                        <ArrowUpRight className="h-3 w-3 text-gray-600 group-hover:text-white transition-colors" />
                                    </div>
                                    <h4 className="text-sm font-medium text-gray-200 line-clamp-2 mb-1 group-hover:text-blue-200 transition-colors">
                                        {ref.title || "Untitled Source"}
                                    </h4>
                                    <div className="text-xs text-gray-500 truncate">
                                        {new URL(ref.url).hostname.replace('www.', '')}
                                    </div>
                                </a>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
