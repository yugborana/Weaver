"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { startResearch } from "@/lib/api";
import { Loader2, Search } from "lucide-react";
import { cn } from "@/lib/api";

export function ResearchForm() {
    const router = useRouter();
    const [topic, setTopic] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!topic.trim()) return;

        setIsLoading(true);
        setError(null);

        try {
            const response = await startResearch({ topic });
            router.push(`/research/${response.task_id}`);
        } catch (err) {
            setError("Failed to start research. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="w-full relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200" />

            <div className="relative glass-panel rounded-2xl p-1">
                <form onSubmit={handleSubmit} className="relative flex items-center p-2">
                    <Search className="absolute left-6 h-5 w-5 text-gray-400 group-focus-within:text-blue-400 transition-colors" />
                    <input
                        id="topic"
                        type="text"
                        value={topic}
                        onChange={(e) => setTopic(e.target.value)}
                        placeholder="What do you want to research today?"
                        className="w-full bg-transparent border-none text-white placeholder-gray-500 focus:ring-0 pl-12 pr-4 py-4 text-lg"
                        disabled={isLoading}
                        autoComplete="off"
                    />
                    <button
                        type="submit"
                        disabled={isLoading || !topic.trim()}
                        className={cn(
                            "ml-2 px-6 py-3 bg-white text-black font-semibold rounded-xl hover:bg-gray-200 transition-all shadow-lg flex items-center gap-2 whitespace-nowrap",
                            (isLoading || !topic.trim()) && "opacity-50 cursor-not-allowed bg-white/10 text-white"
                        )}
                    >
                        {isLoading ? (
                            <Loader2 className="h-5 w-5 animate-spin" />
                        ) : (
                            "Start"
                        )}
                    </button>
                </form>
            </div>

            {/* Helper tags */}
            <div className="mt-6 flex flex-wrap justify-center gap-2 opacity-60">
                {["Quantum Computing", "Future of AI", "Renewable Energy", "Space Exploration"].map((tag) => (
                    <button
                        key={tag}
                        type="button"
                        onClick={() => setTopic(tag)}
                        className="text-xs px-3 py-1 rounded-full border border-white/10 hover:bg-white/5 transition-colors text-gray-400 hover:text-white"
                    >
                        {tag}
                    </button>
                ))}
            </div>
        </div>
    );
}
