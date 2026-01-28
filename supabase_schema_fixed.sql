-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. MAIN TASK TABLE (The "Brain")
-- This table matches your Python 'ResearchTask' model exactly.
CREATE TABLE IF NOT EXISTS research_tasks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    
    -- Request Data
    query JSONB NOT NULL,                 -- { topic, subtopics, depth... }
    
    -- State Management
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, planning, in_progress...
    revision_count INTEGER DEFAULT 0,
    max_revisions INTEGER DEFAULT 3,
    
    -- THE BRAIN (Consolidated JSONB Fields)
    -- We store these objects directly here so loading a task gets EVERYTHING needed for the next step.
    plan JSONB,                           -- ResearchPlan object
    current_report JSONB,                 -- ResearchReport object
    feedback_history JSONB DEFAULT '[]',  -- List[CritiqueFeedback]
    raw_search_results JSONB DEFAULT '[]', -- List[ResearchSource] (Context for Reviser)
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 2. LOGS TABLE (The "Audit Trail")
-- Kept separate so we don't load 10MB of logs every time we check status.
CREATE TABLE IF NOT EXISTS task_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    task_id UUID REFERENCES research_tasks(id) ON DELETE CASCADE,
    
    agent_type VARCHAR(50) NOT NULL,      -- 'researcher', 'critic', 'planner'
    message TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',          -- Token usage, latency, tool_used
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. INDEXES
-- Optimize for the most common query: "Get Task by ID" and "Poll Status"
CREATE INDEX IF NOT EXISTS idx_research_tasks_status ON research_tasks(status);
CREATE INDEX IF NOT EXISTS idx_logs_task_id_created ON task_logs(task_id, created_at DESC);

-- 4. AUTOMATIC UPDATED_AT TRIGGER
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_research_tasks_modtime
    BEFORE UPDATE ON research_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 5. RLS POLICIES (Backend Service Mode)
ALTER TABLE research_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_logs ENABLE ROW LEVEL SECURITY;

-- If you are using the SERVICE_ROLE key in your FastAPI backend,
-- these policies technically aren't needed (Service Role bypasses RLS).
-- However, these allow "Anon" access if you want to test from a frontend directly.
CREATE POLICY "Enable all access" ON research_tasks FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all access" ON task_logs FOR ALL USING (true) WITH CHECK (true);