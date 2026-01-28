"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getTaskStatus, TaskStatusResponse } from "@/lib/api";
import { ProgressTracker } from "@/components/ProgressTracker";
import { ReportViewer } from "@/components/ReportViewer";
import { Loader2 } from "lucide-react";

export default function ResearchPage() {
    const params = useParams();
    const taskId = params?.taskId as string;

    const [status, setStatus] = useState<TaskStatusResponse | null>(null);
    const [loading, setLoading] = useState(true);

    // Initial fetch
    useEffect(() => {
        if (!taskId) return;

        const fetchStatus = async () => {
            try {
                const data = await getTaskStatus(taskId);
                setStatus(data);
            } catch (e) {
                console.error("Failed to fetch status", e);
            } finally {
                setLoading(false);
            }
        };

        fetchStatus();

        // Poll for status updates (in addition to WS in ProgressTracker) to get full object for ReportViewer
        const interval = setInterval(async () => {
            try {
                const data = await getTaskStatus(taskId);
                setStatus(data);
            } catch (e) {
                // ignore
            }
        }, 3000);

        return () => clearInterval(interval);
    }, [taskId]);

    if (!taskId) return null;

    if (loading && !status) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-black">
                <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
            </div>
        );
    }

    return (
        <main className="min-h-screen bg-black text-gray-200 p-4 md:p-8">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* Top Navigation / Header */}
                <div className="flex items-center justify-between border-b border-white/10 pb-4">
                    <a href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                        <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center font-bold text-white">
                            W
                        </div>
                        <span className="font-semibold text-xl tracking-tight text-white">Weaver</span>
                    </a>
                    <div className="text-sm text-gray-400 font-mono">
                        Task: {taskId.slice(0, 8)}...
                    </div>
                </div>

                {/* Progress Tracker (Always visible until done, then maybe condense?) */}
                {/* Actually, keep it visible so user can see logs */}
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                    <ProgressTracker taskId={taskId} initialStatus={status || undefined} />
                </div>

                {/* Status Message */}
                {status?.status === "failed" && (
                    <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-300 text-center animate-in fade-in">
                        Task failed. Check logs above for details.
                    </div>
                )}

                {/* Final Report */}
                {status?.result && (
                    <div className="pt-8 border-t border-white/10">
                        <ReportViewer report={status.result} />
                    </div>
                )}

            </div>
        </main>
    );
}
