/* Types for the Elenchus Eval UI */

export type EventType =
    | 'llm' | 'tool' | 'message' | 'eval_result'
    | 'metrics' | 'error' | 'connected' | 'ack'
    | 'llm_judge' | 'eval_start' | 'eval_complete'
    | 'eval_progress' | 'eval_cancelled';

export interface Event {
    type: EventType;
    data: Record<string, unknown>;
    timestamp: string;
    run_id?: string;
    step?: number;
}

export interface Message {
    role: 'user' | 'assistant' | 'system' | 'tool';
    content: string;
    timestamp?: string;
}

export interface Metrics {
    totalTokens: number;
    latencyMs: number;
    costUsd: number;
}

export interface EvalCase {
    input: string;
    expected: string;
    name?: string;
}

export type GraderType =
    | 'contains' | 'llm_judge' | 'task_completion' | 'exact_match'
    | 'code_execution' | 'coding_agent_judge' | 'step_diagnostics'
    | 'tool_usage' | 'source_citation' | 'factual_accuracy' | 'composite'
    | 'reasoning_coherence' | 'unified' | 'all';

export interface GraderBreakdown {
    passed: boolean;
    score: number;
    reason: string;
    weight?: number;
}

export interface EvalResult {
    name: string;
    input: string;
    expected: string | Record<string, unknown>;
    output?: string;
    passed: boolean;
    score: number;
    reason: string;
    latency_ms: number;
    grader_type: GraderType;
    error?: string;
    // Enhanced fields
    grader_breakdown?: Record<string, GraderBreakdown>;
    tokens_used?: number;
    cost_usd?: number;
    tools_used?: string[];
    sources_cited?: string[];
}

export interface EvalSummary {
    name: string;
    total: number;
    passed: number;
    failed: number;
    pass_rate: number;
    avg_latency_ms: number;
    avg_score: number;
    total_cost_usd: number;
    results: EvalResult[];
}

export interface DatasetInfo {
    name: string;
    file: string;
    count: number;
    path: string;
}

export interface GraderInfo {
    id: string;
    name: string;
    description: string;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

export type TabType = 'chat' | 'eval';

// Chat Eval Playground types
export interface TaskType {
    id: string;
    name: string;
    metrics: string[];
}

export interface MetricInfo {
    name: string;
    description: string;
}

export interface ChatEvalResult {
    passed: boolean;
    score: number;
    reason: string;
    metric: string;
    expected: string;
    latency_ms: number;
}
