-- ============================================================================
-- MedClaim — Pipeline Jobs Table
-- 
-- Tracks background LangGraph pipeline execution jobs.
-- Created for Subphase 4.1 (Background Task Processing).
--
-- Run this in the Supabase SQL Editor:
-- https://supabase.com/dashboard/project/<project_id>/sql
-- ============================================================================

CREATE TABLE IF NOT EXISTS pipeline_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id        UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'QUEUED'
                    CHECK (status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED')),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    result          JSONB,          -- Final state summary (status, tokens, risk score, etc.)
    error           TEXT,           -- Error message if FAILED
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fast lookups by claim_id (list all jobs for a claim)
CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_claim_id ON pipeline_jobs(claim_id);

-- Index for polling active jobs
CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_status ON pipeline_jobs(status)
    WHERE status IN ('QUEUED', 'RUNNING');

-- Enable Row Level Security (match other tables)
ALTER TABLE pipeline_jobs ENABLE ROW LEVEL SECURITY;

-- Allow all operations for authenticated service role
CREATE POLICY "service_role_all" ON pipeline_jobs
    FOR ALL
    USING (true)
    WITH CHECK (true);
