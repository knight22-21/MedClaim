-- =============================================================================
-- MedClaim — Realtime Subscriptions & Feedback Loop Trigger
-- Migration 003: Enable realtime on claims + outcome webhook trigger
-- Run in: Supabase SQL Editor (after 002_rls_policies.sql)
-- =============================================================================

-- =============================================================================
-- REALTIME: Enable on claims table for live dashboard updates
-- When claims.status changes, Supabase broadcasts via WebSocket
-- =============================================================================

-- Add claims table to Supabase Realtime publication
-- Note: In Supabase dashboard, you can also enable this via
-- Database → Replication → Toggle "claims" table
ALTER PUBLICATION supabase_realtime ADD TABLE claims;

-- =============================================================================
-- FEEDBACK LOOP TRIGGER: On claim_outcomes insert → call webhook
-- When a claim outcome is recorded, notify the FastAPI backend to
-- embed the outcome and upsert it into the denial_patterns Qdrant collection
-- =============================================================================

-- Function that sends an HTTP POST to the feedback loop endpoint
-- Uses Supabase's pg_net extension for async HTTP calls
CREATE OR REPLACE FUNCTION notify_claim_outcome()
RETURNS TRIGGER AS $$
DECLARE
    payload JSONB;
    backend_url TEXT;
BEGIN
    -- Build the webhook payload with claim outcome data
    payload := jsonb_build_object(
        'claim_id', NEW.claim_id,
        'outcome_id', NEW.id,
        'outcome', NEW.outcome,
        'resolution_date', NEW.resolution_date,
        'amount_recovered', NEW.amount_recovered,
        'notes', NEW.notes,
        'event_type', 'CLAIM_OUTCOME_RECORDED',
        'triggered_at', NOW()
    );

    -- Log the event (visible in Supabase Logs)
    RAISE LOG 'MedClaim feedback loop triggered for claim_id: %, outcome: %',
        NEW.claim_id, NEW.outcome;

    -- Update the parent claim's status based on outcome
    UPDATE claims
    SET status = NEW.outcome,
        updated_at = NOW()
    WHERE id = NEW.claim_id;

    -- NOTE: The HTTP webhook call to FastAPI (/feedback/claim-outcome)
    -- is handled via a Supabase Edge Function rather than pg_net
    -- to keep the trigger lightweight and avoid network dependencies
    -- in the database layer. See: supabase/functions/claim-outcome-webhook/

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Attach trigger to claim_outcomes table
CREATE TRIGGER trigger_claim_outcome_feedback
    AFTER INSERT ON claim_outcomes
    FOR EACH ROW
    EXECUTE FUNCTION notify_claim_outcome();

-- Also trigger on UPDATE (in case outcome is corrected)
CREATE TRIGGER trigger_claim_outcome_feedback_update
    AFTER UPDATE ON claim_outcomes
    FOR EACH ROW
    EXECUTE FUNCTION notify_claim_outcome();

-- =============================================================================
-- HELPER VIEWS: Useful aggregations for the analytics dashboard
-- =============================================================================

-- Denial rate by payer
CREATE OR REPLACE VIEW v_denial_rate_by_payer AS
SELECT
    c.payer_name,
    COUNT(*) AS total_claims,
    COUNT(CASE WHEN co.outcome IN ('DENIED', 'FINAL_DENIED') THEN 1 END) AS denied_claims,
    ROUND(
        COUNT(CASE WHEN co.outcome IN ('DENIED', 'FINAL_DENIED') THEN 1 END)::NUMERIC
        / NULLIF(COUNT(*), 0) * 100,
        2
    ) AS denial_rate_pct
FROM claims c
LEFT JOIN claim_outcomes co ON c.id = co.claim_id
GROUP BY c.payer_name
ORDER BY denial_rate_pct DESC;

-- Average risk score by facility type
CREATE OR REPLACE VIEW v_avg_risk_by_facility AS
SELECT
    c.facility_type,
    ROUND(AVG(dp.risk_score), 1) AS avg_risk_score,
    COUNT(*) AS total_predictions
FROM claims c
JOIN denial_predictions dp ON c.id = dp.claim_id
GROUP BY c.facility_type
ORDER BY avg_risk_score DESC;

-- Appeal success rate
CREATE OR REPLACE VIEW v_appeal_success_rate AS
SELECT
    COUNT(*) AS total_appeals,
    COUNT(CASE WHEN co.outcome = 'APPROVED_ON_APPEAL' THEN 1 END) AS successful_appeals,
    ROUND(
        COUNT(CASE WHEN co.outcome = 'APPROVED_ON_APPEAL' THEN 1 END)::NUMERIC
        / NULLIF(COUNT(*), 0) * 100,
        2
    ) AS success_rate_pct
FROM appeal_letters al
JOIN claim_outcomes co ON al.claim_id = co.claim_id
WHERE al.status = 'SUBMITTED';

-- Daily claim volume
CREATE OR REPLACE VIEW v_daily_claim_volume AS
SELECT
    DATE(created_at) AS claim_date,
    COUNT(*) AS claims_received,
    COUNT(CASE WHEN status = 'APPROVED' THEN 1 END) AS approved,
    COUNT(CASE WHEN status IN ('DENIED', 'FINAL_DENIED') THEN 1 END) AS denied
FROM claims
GROUP BY DATE(created_at)
ORDER BY claim_date DESC;
