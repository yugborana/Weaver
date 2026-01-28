"use client";

import { useEffect, useState, useRef } from "react";
import { getWebSocketUrl, TaskStatusResponse } from "@/lib/api";
import { CheckCircle2, Circle, Loader2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/api";

interface ProgressTrackerProps {
    taskId: string;
    initialStatus?: TaskStatusResponse;
}

interface LogMessage {
    message: string;
    timestamp: string;
    agent: string;
}

const STAGES = [
    { id: "initializing", label: "Initializing" },
    { id: "planning_strategy", label: "Research Strategy" },
    { id: "gathering_data", label: "Gathering Data" },
    { id: "critiquing_draft", label: "Critique & Review" },
    { id: "revising_draft", label: "Revising Draft" },
    { id: "finished", label: "Final Report" }
];

export function ProgressTracker({ taskId, initialStatus }: ProgressTrackerProps) {
    const [logs, setLogs] = useState<LogMessage[]>([]);
    const [currentStage, setCurrentStage] = useState(initialStatus?.current_stage || "initializing");
    const [isConnected, setIsConnected] = useState(false);

    const scrollRef = useRef<HTMLDivElement>(null);

    // Scroll to bottom of logs
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    useEffect(() => {
        const wsUrl = getWebSocketUrl(taskId);
        let ws: WebSocket | null = null;
        let reconnectTimeout: NodeJS.Timeout;

        const connect = () => {
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                setIsConnected(true);
                console.log("WebSocket connected");
            };

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);

                    if (message.type === "log_message") {
                        setLogs(prev => [...prev, message.data]);
                    } else if (message.type === "status_update") {
                        // Map backend status to frontend stage if needed
                        // For now rely on log messages or polling for precise stage sync if status_update is generic
                        // Actually coordinator sends status enum value
                        const status = message.data.status; // e.g. "in_progress"

                        // Allow some mapping or just refetch status via polling
                        // For simplicity, let's just log it here 
                    }
                } catch (e) {
                    console.error("Error parsing WebSocket message", e);
                }
            };

            ws.onclose = () => {
                setIsConnected(false);
                // Try to reconnect
                reconnectTimeout = setTimeout(connect, 3000);
            };
        };

        connect();

        return () => {
            if (ws) ws.close();
            clearTimeout(reconnectTimeout);
        };
    }, [taskId]);

    // Polling for stage updates (backup to WebSocket)
    useEffect(() => {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`http://localhost:8000/research/${taskId}/status`);
                if (res.ok) {
                    const data = await res.json();
                    setCurrentStage(data.current_stage);
                }
            } catch (e) {
                // ignore errors
            }
        }, 2000);

        return () => clearInterval(interval);
    }, [taskId]);

    return (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-700">

            {/* Stages Timeline - The Circuit Board */}
            <div className="lg:col-span-1 glass-panel p-6 rounded-2xl h-fit">
                <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                    <span className="h-2 w-2 bg-blue-500 rounded-full animate-pulse" />
                    System Status
                </h3>

                <div className="space-y-0 relative">
                    {/* Connecting Line */}
                    <div className="absolute left-[19px] top-2 bottom-4 w-[2px] bg-white/5" />

                    {STAGES.map((stage, index) => {
                        const isActive = stage.id === currentStage;
                        const isCompleted = STAGES.findIndex(s => s.id === currentStage) > index || currentStage === "finished";

                        return (
                            <div key={stage.id} className="relative z-10 flex items-start group min-h-[60px]">
                                <div className={cn(
                                    "relative h-10 w-10 shrink-0 rounded-xl flex items-center justify-center border transition-all duration-500",
                                    isActive ? "bg-blue-500/20 border-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.5)] scale-110" :
                                        isCompleted ? "bg-emerald-500/10 border-emerald-500/50" :
                                            "bg-black border-white/10"
                                )}>
                                    {isCompleted ? (
                                        <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                                    ) : isActive ? (
                                        <Loader2 className="h-5 w-5 text-blue-400 animate-spin" />
                                    ) : (
                                        <Circle className="h-4 w-4 text-gray-600" />
                                    )}
                                </div>

                                <div className="ml-4 pt-2">
                                    <div className={cn(
                                        "text-sm font-medium transition-colors duration-300",
                                        isActive ? "text-white" : isCompleted ? "text-gray-300" : "text-gray-600"
                                    )}>
                                        {stage.label}
                                    </div>
                                    {isActive && (
                                        <div className="text-xs text-blue-400 mt-1 animate-pulse">
                                            Processing...
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div className="mt-8 pt-6 border-t border-white/5">
                    <div className="flex items-center justify-between text-xs text-gray-500 font-mono">
                        <span>CONNECTION</span>
                        <span className={cn(isConnected ? "text-emerald-400" : "text-red-400")}>
                            {isConnected ? "STABLE" : "OFFLINE"}
                        </span>
                    </div>
                </div>
            </div>

            {/* Live Logs - The Terminal */}
            <div className="lg:col-span-3 glass-panel rounded-2xl overflow-hidden flex flex-col h-[600px] border-l-4 border-l-blue-500/20">
                <div className="p-4 border-b border-white/5 bg-black/40 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="h-3 w-3 rounded-full bg-red-500/20 border border-red-500/50" />
                        <div className="h-3 w-3 rounded-full bg-yellow-500/20 border border-yellow-500/50" />
                        <div className="h-3 w-3 rounded-full bg-green-500/20 border border-green-500/50" />
                    </div>
                    <div className="text-xs font-mono text-gray-500">agent_terminal.exe</div>
                </div>

                <div
                    ref={scrollRef}
                    className="flex-1 overflow-y-auto p-6 font-mono text-sm space-y-2 bg-black/50"
                >
                    {logs.length === 0 && (
                        <div className="h-full flex flex-col items-center justify-center text-gray-600 gap-2 opacity-50">
                            <Loader2 className="h-8 w-8 animate-spin" />
                            <p>Initializing Neural Uplink...</p>
                        </div>
                    )}

                    {logs.map((log, i) => (
                        <div key={i} className="flex gap-4 animate-in fade-in slide-in-from-left-2 duration-300">
                            <span className="text-gray-600 shrink-0 select-none">
                                {new Date(log.timestamp).toLocaleTimeString([], { hour12: false })}
                            </span>
                            <div className="flex-1 break-words">
                                <span className={cn(
                                    "font-bold mr-3",
                                    log.agent === "researcher" ? "text-blue-400" :
                                        log.agent === "critic" ? "text-orange-400" :
                                            log.agent === "reviser" ? "text-purple-400" :
                                                "text-gray-400"
                                )}>
                                    {log.agent.toUpperCase()} &gt;
                                </span>
                                <span className="text-gray-300">
                                    {log.message}
                                </span>
                            </div>
                        </div>
                    ))}
                    <div className="h-4" /> {/* Spacer */}
                </div>
            </div>
        </div>
    );
}
