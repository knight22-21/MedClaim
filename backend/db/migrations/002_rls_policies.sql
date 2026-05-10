-- =============================================================================
-- MedClaim — Row Level Security Policies
-- Migration 002: RLS for multi-tenant access control
-- Run in: Supabase SQL Editor (after 001_initial_schema.sql)
-- =============================================================================
-- 
-- Access model:
--   - Authenticated users: read/write only claims assigned to their user ID
--   - Service role (FastAPI backend): full read/write on all rows
--   - Anon role: no access
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE denial_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE appeal_letters ENABLE ROW LEVEL SECURITY;
ALTER TABLE claim_outcomes ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- SERVICE ROLE POLICIES (FastAPI backend — full access)
-- The service_role key bypasses RLS by default in Supabase,
-- but we define explicit policies for clarity and documentation.
-- =============================================================================

-- Claims: service role full access
CREATE POLICY "Service role full access on claims"
    ON claims
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Audit results: service role full access
CREATE POLICY "Service role full access on audit_results"
    ON audit_results
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Denial predictions: service role full access
CREATE POLICY "Service role full access on denial_predictions"
    ON denial_predictions
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Appeal letters: service role full access
CREATE POLICY "Service role full access on appeal_letters"
    ON appeal_letters
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Claim outcomes: service role full access
CREATE POLICY "Service role full access on claim_outcomes"
    ON claim_outcomes
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- =============================================================================
-- AUTHENTICATED USER POLICIES (Dashboard users — scoped to assigned claims)
-- =============================================================================

-- Claims: users can read their assigned claims
CREATE POLICY "Users can view own claims"
    ON claims
    FOR SELECT
    USING (
        auth.role() = 'authenticated'
        AND assigned_user_id = auth.uid()
    );

-- Claims: users can update their assigned claims (e.g., approve corrections)
CREATE POLICY "Users can update own claims"
    ON claims
    FOR UPDATE
    USING (
        auth.role() = 'authenticated'
        AND assigned_user_id = auth.uid()
    )
    WITH CHECK (
        auth.role() = 'authenticated'
        AND assigned_user_id = auth.uid()
    );

-- Claims: users can insert new claims (assigned to themselves)
CREATE POLICY "Users can insert claims"
    ON claims
    FOR INSERT
    WITH CHECK (
        auth.role() = 'authenticated'
        AND assigned_user_id = auth.uid()
    );

-- Audit results: users can read audits for their claims
CREATE POLICY "Users can view audits for own claims"
    ON audit_results
    FOR SELECT
    USING (
        auth.role() = 'authenticated'
        AND claim_id IN (
            SELECT id FROM claims WHERE assigned_user_id = auth.uid()
        )
    );

-- Denial predictions: users can read predictions for their claims
CREATE POLICY "Users can view predictions for own claims"
    ON denial_predictions
    FOR SELECT
    USING (
        auth.role() = 'authenticated'
        AND claim_id IN (
            SELECT id FROM claims WHERE assigned_user_id = auth.uid()
        )
    );

-- Appeal letters: users can read and update appeal letters for their claims
CREATE POLICY "Users can view appeals for own claims"
    ON appeal_letters
    FOR SELECT
    USING (
        auth.role() = 'authenticated'
        AND claim_id IN (
            SELECT id FROM claims WHERE assigned_user_id = auth.uid()
        )
    );

CREATE POLICY "Users can approve appeals for own claims"
    ON appeal_letters
    FOR UPDATE
    USING (
        auth.role() = 'authenticated'
        AND claim_id IN (
            SELECT id FROM claims WHERE assigned_user_id = auth.uid()
        )
    )
    WITH CHECK (
        auth.role() = 'authenticated'
        AND claim_id IN (
            SELECT id FROM claims WHERE assigned_user_id = auth.uid()
        )
    );

-- Claim outcomes: users can read outcomes for their claims
CREATE POLICY "Users can view outcomes for own claims"
    ON claim_outcomes
    FOR SELECT
    USING (
        auth.role() = 'authenticated'
        AND claim_id IN (
            SELECT id FROM claims WHERE assigned_user_id = auth.uid()
        )
    );
