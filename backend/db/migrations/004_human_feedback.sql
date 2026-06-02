-- ============================================================================
-- MedClaim — Human Feedback Table
-- 
-- Stores specialist overrides and corrections for LangGraph few-shot learning.
-- Created for Subphase 4.2 (Human-in-the-Loop Feedback Workflows).
-- ============================================================================

CREATE TABLE IF NOT EXISTS human_feedback (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id        UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    specialist_id   TEXT NOT NULL,
    action          TEXT NOT NULL CHECK (action IN ('APPROVED_OVERRIDE', 'REJECTED')),
    notes           TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for RAG retrieval queries
CREATE INDEX IF NOT EXISTS idx_human_feedback_action ON human_feedback(action);

-- Enable Row Level Security
ALTER TABLE human_feedback ENABLE ROW LEVEL SECURITY;

-- Allow all operations for authenticated service role
CREATE POLICY "service_role_all" ON human_feedback
    FOR ALL
    USING (true)
    WITH CHECK (true);
