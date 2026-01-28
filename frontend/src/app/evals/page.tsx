'use client';

import React, { useState } from 'react';
import { EvalPanel } from '@/components/evals/EvalPanel';
import type { EvalResult, EvalSummary } from '@/lib/types';
// import Header from '@/components/Header'; // Assuming you have a header component, adjust import as needed

export default function EvalsPage() {
    const [results, setResults] = useState<EvalResult[]>([]);
    const [summary, setSummary] = useState<EvalSummary | null>(null);
    const [isRunning, setIsRunning] = useState(false);
    const [progress, setProgress] = useState<{ current: number; total: number; percentage: number } | null>(null);

    const handleRunEval = async (dataset: string, grader: string) => {
        setIsRunning(true);
        setResults([]);
        setSummary(null);
        setProgress({ current: 0, total: 10, percentage: 0 }); // Mock initial progress

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/eval/run`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dataset, grader })
            });

            if (!response.ok) {
                throw new Error('Failed to start evaluation');
            }

            // In a real implementation, you might use WebSockets or SSE for real-time updates.
            // For now, we'll simulate it or simple polling could be added.
            // This part depends on how the backend streams results.

            // Assuming the backend returns everything at once for this basic integration
            const data = await response.json();
            if (data.results) {
                setResults(data.results);
                setSummary(data);
                setProgress({ current: data.results.length, total: data.results.length, percentage: 100 });
            }
        } catch (error) {
            console.error('Eval error:', error);
            // Handle error state
        } finally {
            setIsRunning(false);
        }
    };

    const handleStopEval = () => {
        setIsRunning(false);
        // Add API call to stop eval if supported
    };

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col">
            {/* <Header /> */}
            <main className="flex-1">
                <EvalPanel
                    results={results}
                    summary={summary}
                    onRunEval={handleRunEval}
                    onStopEval={handleStopEval}
                    isRunning={isRunning}
                    progress={progress}
                />
            </main>
        </div>
    );
}
