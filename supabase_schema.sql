-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. ENUMS (Matches python app.models.research.ResearchStatus)
CREATE TYPE research_status AS ENUM (
    'pending', 
    'planning', 
    'in_progress', 
    'reviewing', 
    'revising', 
    'completed', 
    'failed'
);

-- 2. MAIN TASK TABLE (The "Brain" State)
-- This table maps 1:1 to the ResearchTask Pydantic model.
CREATE TABLE IF NOT EXISTS research_tasks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    
    -- User Ownership (Optional: Enable if you have auth)
    -- user_id UUID REFERENCES auth.users(id),
    
    -- Inputs
    query JSONB NOT NULL,                 -- { topic, subtopics, depth... }
    
    -- State / Memory
    status research_status DEFAULT 'pending',
    plan JSONB,                           -- The ResearchPlan object
    raw_search_results JSONB DEFAULT '[]', -- List of ResearchSource objects (The gathered knowledge)
    current_report JSONB,                 -- The ResearchReport object (The latest draft)
    
    -- Loop Control
    feedback_history JSONB DEFAULT '[]',  -- List of CritiqueFeedback objects
    revision_count INTEGER DEFAULT 0,     -- Counts loops between Critic <-> Reviser
    max_revisions INTEGER DEFAULT 3,      -- Safety limit
    
    -- Meta
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 3. LOGS TABLE (The "Audit Trail")
-- Kept separate to keep the main task row lightweight.
CREATE TABLE IF NOT EXISTS task_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    task_id UUID REFERENCES research_tasks(id) ON DELETE CASCADE,
    
    agent_type VARCHAR(50) NOT NULL,      -- 'researcher', 'critic', 'planner'
    message TEXT NOT NULL,                -- The thought process
    metadata JSONB DEFAULT '{}',          -- Extra debug info (token usage, latency)
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. INDEXES (Performance)
CREATE INDEX idx_tasks_status ON research_tasks(status);
CREATE INDEX idx_logs_task_id ON task_logs(task_id);
-- Fast ordering for UI "Recent Logs" view
CREATE INDEX idx_logs_created_at ON task_logs(created_at DESC); 

-- 5. AUTOMATIC TIMESTAMP UPDATER
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

-- 6. RLS POLICIES (Security)
ALTER TABLE research_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_logs ENABLE ROW LEVEL SECURITY;

-- Development Policy (Allow everything - CHANGE FOR PRODUCTION)
CREATE POLICY "Enable access to all users" ON research_tasks FOR ALL USING (true);
CREATE POLICY "Enable access to all users" ON task_logs FOR ALL USING (true);