import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ResearchRequest {
    topic: string;
    subtopics?: string[];
    depth_level?: number;
    requirements?: string;
}

export interface ResearchResponse {
    task_id: string;
    status: string;
    message: string;
    monitoring_url: string;
}

export interface TaskStatusResponse {
    task_id: string;
    status: string;
    progress: {
        messages_logged: number;
        revisions: number;
        search_queries: number;
    };
    current_stage: string;
    result: any;
}

export async function startResearch(data: ResearchRequest): Promise<ResearchResponse> {
    const response = await fetch(`${API_BASE_URL}/research`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        throw new Error("Failed to start research");
    }

    return response.json();
}

export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
    const response = await fetch(`${API_BASE_URL}/research/${taskId}/status`);

    if (!response.ok) {
        throw new Error("Failed to fetch status");
    }

    return response.json();
}

export function getWebSocketUrl(taskId: string): string {
    const wsProtocol = API_BASE_URL.startsWith('https') ? 'wss' : 'ws';
    const wsHost = API_BASE_URL.replace(/^https?:\/\//, '');
    return `${wsProtocol}://${wsHost}/ws/${taskId}`;
}

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}
