'use client';

import React, { useState, useEffect } from 'react';
import type { EvalResult, EvalSummary, DatasetInfo, GraderInfo, GraderType, GraderBreakdown } from '@/lib/types';
import { ArrowLeft, Play, Square, CheckCircle2, XCircle, Clock, DollarSign, BarChart3, ChevronDown, ChevronUp, Wrench, Link2, Zap } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ModelConfig {
    agent_model: string;
    judge_model: string;
}

interface EvalPanelProps {
    results: EvalResult[];
    summary: EvalSummary | null;
    onRunEval: (dataset: string, grader: string) => void;
    onStopEval: () => void;
    isRunning: boolean;
    progress: { current: number; total: number; percentage: number } | null;
}

function ProgressBar({ passed, total }: { passed: number; total: number }) {
    const percentage = total > 0 ? (passed / total) * 100 : 0;
    const isComplete = total > 0 && passed === total;

    return (
        <div className="eval-progress w-full mb-6">
            <div className="flex justify-between text-sm mb-2">
                <span className="font-medium text-gray-300">Pass Rate</span>
                <span className="text-gray-400">
                    {percentage.toFixed(0)}% <span className="text-gray-500">({passed}/{total})</span>
                </span>
            </div>
            <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden backdrop-blur-sm border border-white/5">
                <div
                    className={`h-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-500 ease-out shadow-[0_0_10px_rgba(16,185,129,0.3)]`}
                    style={{ width: `${percentage}%` }}
                />
            </div>
        </div>
    );
}

function GraderBadge({ type }: { type: string }) {
    const labels: Record<string, string> = {
        contains: 'Contains',
        llm_judge: 'LLM Judge',
        task_completion: 'Task Completion',
        exact_match: 'Exact Match',
        step_diagnostics: 'Diagnostics',
        tool_usage: 'Tool Usage',
        source_citation: 'Source Citation',
        factual_accuracy: 'Factual Accuracy',
        composite: 'Composite',
        reasoning_coherence: 'Reasoning',
        unified: 'Unified',
    };

    // Aesthetic colors for badges
    const colors: Record<string, string> = {
        contains: 'bg-blue-500/10 text-blue-300 border-blue-500/20',
        llm_judge: 'bg-purple-500/10 text-purple-300 border-purple-500/20',
        task_completion: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20',
        exact_match: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
        step_diagnostics: 'bg-pink-500/10 text-pink-300 border-pink-500/20',
        tool_usage: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/20',
        source_citation: 'bg-orange-500/10 text-orange-300 border-orange-500/20',
        factual_accuracy: 'bg-lime-500/10 text-lime-300 border-lime-500/20',
        composite: 'bg-gradient-to-r from-purple-500/10 to-blue-500/10 text-white border-purple-500/20',
        reasoning_coherence: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/20',
        unified: 'bg-gradient-to-r from-emerald-500/10 via-blue-500/10 to-purple-500/10 text-white border-emerald-500/20',
    };

    if (!type) return null;

    return (
        <span className={`px-2.5 py-1 rounded-md text-xs font-medium border ${colors[type] || 'bg-gray-500/10 text-gray-300 border-gray-500/20'}`}>
            {labels[type] || type.replace(/_/g, ' ')}
        </span>
    );
}

interface EvalConfigInfoProps {
    model: string;
    judgeModel: string;
    graderTypes: string[];
    caseCount: number;
    selectedDataset: string;
    selectedGrader: string;
}

function EvalConfigInfo({ model, judgeModel, graderTypes, caseCount, selectedDataset, selectedGrader }: EvalConfigInfoProps) {
    return (
        <div className="relative overflow-hidden bg-white/5 backdrop-blur-md p-6 rounded-2xl border border-white/10 mb-8 shadow-xl">
            <div className="absolute top-0 right-0 p-3 opacity-20 transform translate-x-1/3 -translate-y-1/3 pointer-events-none">
                <div className="w-64 h-64 bg-blue-500/30 rounded-full blur-3xl"></div>
            </div>

            <div className="relative z-10">
                <div className="mb-4 border-b border-white/10 pb-2">
                    <span className="text-lg font-semibold text-white flex items-center gap-2">
                        <BarChart3 className="w-5 h-5 text-blue-400" />
                        Evaluation Setup
                    </span>
                </div>

                <div className="grid grid-cols-2 gap-6 text-sm">
                    <div>
                        <span className="text-gray-400 block mb-1 text-xs uppercase tracking-wider">Agent Model</span>
                        <span className="font-mono text-blue-200 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/10">{model}</span>
                    </div>

                    <div>
                        <span className="text-gray-400 block mb-1 text-xs uppercase tracking-wider">LLM Judge</span>
                        <span className="font-mono text-purple-200 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/10">{judgeModel}</span>
                    </div>

                    <div>
                        <span className="text-gray-400 block mb-1 text-xs uppercase tracking-wider">Dataset</span>
                        <span className="text-gray-200 font-medium">{selectedDataset}</span>
                    </div>

                    <div>
                        <span className="text-gray-400 block mb-1 text-xs uppercase tracking-wider">Grader Logic</span>
                        <span className="text-gray-200 font-medium">{selectedGrader}</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

function ScoreIndicator({ score }: { score: number }) {
    const getScoreClass = () => {
        if (score >= 0.8) return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';
        if (score >= 0.5) return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
        return 'text-rose-400 border-rose-500/30 bg-rose-500/10';
    };

    return (
        <span className={`px-2.5 py-0.5 rounded border font-mono text-sm font-semibold ${getScoreClass()}`}>
            {score.toFixed(2)}
        </span>
    );
}

function EvalResultCard({ result }: { result: EvalResult }) {
    const [isExpanded, setIsExpanded] = useState(false);
    const isLLMJudge = result.grader_type === 'llm_judge';
    const isComposite = result.grader_type === 'composite';
    const hasToolsUsed = result.tools_used && result.tools_used.length > 0;
    const hasSourcesCited = result.sources_cited && result.sources_cited.length > 0;
    const hasBreakdown = result.grader_breakdown && Object.keys(result.grader_breakdown).length > 0;

    const formatValue = (val: unknown): string => {
        if (typeof val === 'object' && val !== null) {
            return JSON.stringify(val, null, 2);
        }
        return String(val ?? '');
    };

    return (
        <div
            className={`group mb-3 border rounded-xl overflow-hidden transition-all duration-300 ${isExpanded ? 'shadow-lg bg-white/10 border-white/20' : 'hover:bg-white/5 border-white/5 bg-white/5'
                }`}
        >
            <div
                className="flex items-center p-4 gap-4 cursor-pointer"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <span className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold shadow-inner ${result.passed
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                    }`}>
                    {result.passed ? <CheckCircle2 className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                </span>

                <div className="flex-1 min-w-0">
                    <h3 className="text-gray-200 font-medium truncate text-sm sm:text-base">{result.name || 'Untitled Case'}</h3>
                    <div className="text-xs text-gray-500 truncate mt-0.5 font-mono opacity-60">{result.input.substring(0, 60)}...</div>
                </div>

                <div className="flex items-center gap-3">
                    {/* Quick indicators */}
                    {hasToolsUsed && <span title="Tools used"><Wrench className="w-4 h-4 text-cyan-400" /></span>}
                    {hasSourcesCited && <span title="Sources cited"><Link2 className="w-4 h-4 text-orange-400" /></span>}
                    {isComposite && <span title="Composite grader"><Zap className="w-4 h-4 text-purple-400" /></span>}

                    <div className="hidden sm:block">
                        <GraderBadge type={result.grader_type} />
                    </div>
                    <ScoreIndicator score={result.score} />
                    <span className="text-xs text-gray-500 font-mono w-14 text-right hidden sm:block">
                        {result.latency_ms?.toFixed(0) ?? 0}ms
                    </span>
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
                </div>
            </div>

            {isExpanded && (
                <div className="p-4 bg-black/20 border-t border-white/5 text-sm space-y-4 animate-in slide-in-from-top-2 duration-200">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-1">
                            <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider">Input</span>
                            <div className="bg-black/30 p-3 rounded-lg border border-white/5 font-mono text-gray-300 text-xs overflow-auto max-h-40">
                                {result.input}
                            </div>
                        </div>
                        <div className="space-y-1">
                            <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider">Expected Output</span>
                            <div className="bg-black/30 p-3 rounded-lg border border-white/5 font-mono text-gray-300 text-xs overflow-auto max-h-40">
                                {formatValue(result.expected)}
                            </div>
                        </div>
                    </div>

                    {result.output && (
                        <div className="space-y-1">
                            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Actual Output</span>
                            <div className="bg-black/30 p-3 rounded-lg border border-white/5 font-mono text-gray-300 text-xs overflow-auto max-h-60 whitespace-pre-wrap">
                                {result.output}
                            </div>
                        </div>
                    )}

                    {/* Composite Grader Breakdown */}
                    {hasBreakdown && (
                        <div className="space-y-2">
                            <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider flex items-center gap-2">
                                <Zap className="w-3 h-3" /> Grader Breakdown
                            </span>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                                {Object.entries(result.grader_breakdown!).map(([graderName, breakdown]) => (
                                    <div
                                        key={graderName}
                                        className={`p-3 rounded-lg border ${breakdown.passed ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-rose-500/5 border-rose-500/20'}`}
                                    >
                                        <div className="flex items-center justify-between mb-1">
                                            <span className="text-xs font-medium text-gray-300">{graderName.replace(/Grader$/, '')}</span>
                                            <span className={`text-xs font-bold ${breakdown.passed ? 'text-emerald-400' : 'text-rose-400'}`}>
                                                {(breakdown.score * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        {breakdown.weight && (
                                            <div className="text-[10px] text-gray-500">Weight: {(breakdown.weight * 100).toFixed(0)}%</div>
                                        )}
                                        <div className="text-[10px] text-gray-400 mt-1 line-clamp-2">{breakdown.reason}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Tools Used */}
                    {hasToolsUsed && (
                        <div className="space-y-1">
                            <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
                                <Wrench className="w-3 h-3" /> Tools Used
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                                {result.tools_used!.map((tool, idx) => (
                                    <span key={idx} className="px-2 py-0.5 bg-cyan-500/10 text-cyan-300 rounded text-xs border border-cyan-500/20">
                                        {tool}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Sources Cited */}
                    {hasSourcesCited && (
                        <div className="space-y-1">
                            <span className="text-xs font-semibold text-orange-400 uppercase tracking-wider flex items-center gap-2">
                                <Link2 className="w-3 h-3" /> Sources Cited
                            </span>
                            <div className="bg-orange-500/5 p-2 rounded-lg border border-orange-500/10 max-h-32 overflow-auto">
                                {result.sources_cited!.map((source, idx) => (
                                    <div key={idx} className="text-xs text-orange-200/80 font-mono truncate py-0.5">
                                        {source.startsWith('http') ? (
                                            <a href={source} target="_blank" rel="noopener noreferrer" className="hover:text-orange-300 underline">
                                                {source}
                                            </a>
                                        ) : source}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className={`space-y-1 ${isLLMJudge ? 'border-l-2 border-purple-500/30 pl-3' : ''}`}>
                        <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-2">
                            {isLLMJudge && '🤖'} {isLLMJudge ? 'LLM Judge Reasoning' : 'Reason / Feedback'}
                        </span>
                        <div className="bg-amber-500/5 p-3 rounded-lg border border-amber-500/10 text-gray-300 leading-relaxed theme-prose">
                            {result.reason}
                        </div>
                    </div>

                    {result.error && (
                        <div className="bg-rose-500/10 p-3 rounded-lg border border-rose-500/20">
                            <span className="text-xs font-bold text-rose-400 uppercase tracking-wider block mb-1">Error Trace</span>
                            <p className="text-rose-300 font-mono text-xs">{result.error}</p>
                        </div>
                    )}

                    {/* Cost/Token info if available */}
                    {(result.tokens_used || result.cost_usd) && (
                        <div className="flex gap-4 pt-2 border-t border-white/5 text-xs text-gray-500">
                            {result.tokens_used && <span>Tokens: {result.tokens_used.toLocaleString()}</span>}
                            {result.cost_usd && <span>Cost: ${result.cost_usd.toFixed(4)}</span>}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export function EvalPanel({ results, summary, onRunEval, onStopEval, isRunning, progress }: EvalPanelProps) {
    const [graderFilter, setGraderFilter] = useState<GraderType>('all');
    const [modelConfig, setModelConfig] = useState<ModelConfig>({
        agent_model: 'Loading...',
        judge_model: 'Loading...',
    });

    const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
    const [graders, setGraders] = useState<GraderInfo[]>([]);
    const [selectedDataset, setSelectedDataset] = useState<string>('eval_cases.json');
    const [selectedGrader, setSelectedGrader] = useState<string>('auto');

    useEffect(() => {
        fetch(`${API_URL}/config`)
            .then(res => res.json())
            .then(data => setModelConfig(data))
            .catch(err => console.error('Failed to fetch config:', err));

        fetch(`${API_URL}/eval/datasets`)
            .then(res => res.json())
            .then(data => {
                setDatasets(data.datasets || []);
                if (data.datasets?.length > 0) setSelectedDataset(data.datasets[0].file);
            })
            .catch(err => console.error('Failed to fetch datasets:', err));

        fetch(`${API_URL}/eval/graders`)
            .then(res => res.json())
            .then(data => setGraders(data.graders || []))
            .catch(err => console.error('Failed to fetch graders:', err));
    }, []);

    const selectedDatasetInfo = datasets.find(d => d.file === selectedDataset);
    const caseCount = selectedDatasetInfo?.count || 0;

    const filteredResults = graderFilter === 'all'
        ? results
        : results.filter(r => r.grader_type === graderFilter);

    const passedCount = results.filter(r => r.passed).length;
    const handleRunEval = () => onRunEval(selectedDataset, selectedGrader);

    // Only show relevant filter tabs - simplified for unified grader
    const allowedGraderTypes: GraderType[] = ['all', 'unified'];

    // Calculate total cost from results
    const totalCost = results.reduce((sum, r) => sum + (r.cost_usd || 0), 0);
    const estimatedCost = results.length > 0 ? (results.length * 0.002) : 0; // Fallback estimate: ~$0.002 per eval

    return (
        <div className="min-h-screen bg-[#0A0A0B] text-gray-100 p-6 sm:p-8 font-sans selection:bg-blue-500/30">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-6">
                    <div>
                        <a href="/" className="inline-flex items-center text-sm text-gray-500 hover:text-blue-400 transition-colors mb-2 gap-1">
                            <ArrowLeft className="w-4 h-4" /> Back to Generator
                        </a>
                        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                            Evaluation Dashboard
                        </h1>
                        <p className="text-gray-500 mt-1"> Analyze performance of the Research Agent</p>
                    </div>
                </div>

                {/* Controls Area */}
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">

                    {/* Left: Input Selection */}
                    <div className="lg:col-span-3 space-y-6">
                        <div className="bg-white/5 backdrop-blur-sm border border-white/5 rounded-xl p-5 flex flex-col sm:flex-row gap-4 items-end sm:items-center shadow-lg">
                            <div className="flex-1 w-full space-y-1.5">
                                <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider ml-1">Test Dataset</label>
                                <select
                                    className="w-full bg-black/40 border border-white/10 text-gray-200 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none transition-all appearance-none cursor-pointer hover:bg-black/60"
                                    value={selectedDataset}
                                    onChange={(e) => setSelectedDataset(e.target.value)}
                                    disabled={isRunning}
                                >
                                    {datasets.map(ds => (
                                        <option key={ds.file} value={ds.file}>{ds.name} ({ds.count} cases)</option>
                                    ))}
                                </select>
                            </div>

                            <div className="flex-1 w-full space-y-1.5">
                                <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider ml-1">Grader</label>
                                <div className="w-full bg-gradient-to-r from-emerald-500/10 via-blue-500/10 to-purple-500/10 border border-emerald-500/20 text-gray-200 rounded-lg px-4 py-2.5 flex items-center gap-2">
                                    <span className="text-emerald-400">✓</span>
                                    <span>Unified (All-in-One)</span>
                                </div>
                            </div>

                            <div className="w-full sm:w-auto pb-0.5">
                                {isRunning ? (
                                    <button
                                        className="w-full sm:w-auto px-6 py-2.5 bg-rose-600/20 text-rose-400 border border-rose-600/50 hover:bg-rose-600/30 rounded-lg font-medium transition-all flex items-center justify-center gap-2 animate-pulse"
                                        onClick={onStopEval}
                                    >
                                        <Square className="w-4 h-4 fill-current" /> Stop
                                    </button>
                                ) : (
                                    <button
                                        className="w-full sm:w-auto px-8 py-2.5 bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-900/40 rounded-lg font-medium transition-all flex items-center justify-center gap-2 transform hover:scale-[1.02] active:scale-[0.98]"
                                        onClick={handleRunEval}
                                    >
                                        <Play className="w-4 h-4 fill-current" /> Run Eval
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Running State */}
                        {isRunning && progress && (
                            <div className="bg-blue-500/5 border border-blue-500/10 rounded-xl p-6 animate-fade-in">
                                <div className="flex justify-between items-center mb-2">
                                    <span className="text-blue-300 font-medium flex items-center gap-2">
                                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-ping" />
                                        Running Evaluation...
                                    </span>
                                    <span className="text-blue-300 font-mono text-sm">{progress.current}/{progress.total}</span>
                                </div>
                                <div className="w-full h-1.5 bg-blue-900/30 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.6)] transition-all duration-300 ease-linear"
                                        style={{ width: `${progress.percentage}%` }}
                                    />
                                </div>
                            </div>
                        )}

                        {/* Results Section */}
                        {!isRunning && results.length > 0 && (
                            <div className="space-y-6">
                                <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6 border border-white/5">
                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                                        <h2 className="text-lg font-semibold text-white">Results Analysis</h2>

                                        {/* Filter Tabs */}
                                        <div className="flex p-1 bg-black/40 rounded-lg border border-white/5">
                                            {allowedGraderTypes.map(type => (
                                                <button
                                                    key={type}
                                                    onClick={() => setGraderFilter(type)}
                                                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${graderFilter === type
                                                        ? 'bg-blue-600 text-white shadow-lg'
                                                        : 'text-gray-400 hover:text-white hover:bg-white/5'
                                                        }`}
                                                >
                                                    {type === 'all' ? 'All' : type === 'llm_judge' ? 'Judge' : type.replace(/_/g, ' ')}
                                                    {type !== 'all' && (
                                                        <span className="ml-1.5 opacity-60 text-[10px] bg-white/20 px-1 rounded-full">
                                                            {results.filter(r => r.grader_type === type).length}
                                                        </span>
                                                    )}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    <ProgressBar passed={passedCount} total={results.length} />

                                    {/* List */}
                                    <div className="space-y-2">
                                        {filteredResults.length === 0 ? (
                                            <div className="text-center py-12 rounded-lg border border-dashed border-white/10">
                                                <p className="text-gray-500">No results found for this filter.</p>
                                            </div>
                                        ) : (
                                            filteredResults.map((result, idx) => (
                                                <EvalResultCard key={`${result.name}-${idx}`} result={result} />
                                            ))
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Empty State / Config Info */}
                        {!isRunning && results.length === 0 && (
                            <EvalConfigInfo
                                model={modelConfig.agent_model}
                                judgeModel={modelConfig.judge_model}
                                graderTypes={['LLM Judge', 'Contains', 'Task Completion', 'Diagnostics']}
                                caseCount={caseCount}
                                selectedDataset={selectedDatasetInfo?.name || 'None'}
                                selectedGrader={graders.find(g => g.id === selectedGrader)?.name || 'Auto'}
                            />
                        )}

                    </div>

                    {/* Right: Metrics Panel */}
                    <div className="lg:col-span-1 space-y-6">
                        <div className="bg-gradient-to-br from-white/5 to-white/0 backdrop-blur-md rounded-xl p-6 border border-white/10 sticky top-6">
                            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 border-b border-white/5 pb-2">
                                Session Metrics
                            </h3>

                            <div className="space-y-6">
                                <div>
                                    <div className="flex items-center gap-2 text-gray-400 mb-1">
                                        <Clock className="w-4 h-4" />
                                        <span className="text-xs">Avg. Latency</span>
                                    </div>
                                    <div className="text-2xl font-mono text-white">
                                        {summary ? (summary.avg_latency_ms / 1000).toFixed(2) : '0.00'}
                                        <span className="text-sm text-gray-500 ml-1">s</span>
                                    </div>
                                </div>

                                <div>
                                    <div className="flex items-center gap-2 text-gray-400 mb-1">
                                        <DollarSign className="w-4 h-4" />
                                        <span className="text-xs">Total Cost</span>
                                    </div>
                                    <div className="text-2xl font-mono text-emerald-400">
                                        ${totalCost > 0 ? totalCost.toFixed(4) : estimatedCost.toFixed(4)}
                                    </div>
                                    {totalCost === 0 && estimatedCost > 0 && (
                                        <div className="text-[10px] text-gray-500">estimated</div>
                                    )}
                                </div>

                                <div className="pt-4 border-t border-white/5">
                                    <div className="grid grid-cols-2 gap-4 text-center">
                                        <div className="bg-green-500/10 rounded-lg p-2 border border-green-500/20">
                                            <div className="text-lg font-bold text-green-400">{summary?.passed || 0}</div>
                                            <div className="text-[10px] text-green-300/60 uppercase">Passed</div>
                                        </div>
                                        <div className="bg-red-500/10 rounded-lg p-2 border border-red-500/20">
                                            <div className="text-lg font-bold text-red-400">{summary?.failed || 0}</div>
                                            <div className="text-[10px] text-red-300/60 uppercase">Failed</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
