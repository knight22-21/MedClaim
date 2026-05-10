-- =============================================================================
-- MedClaim — Initial Database Schema
-- Migration 001: Core tables for claim lifecycle management
-- Run in: Supabase SQL Editor
-- =============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- 1. CLAIMS TABLE
-- Central table — one row per insurance claim
-- =============================================================================
CREATE TABLE IF NOT EXISTS claims (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_name    TEXT NOT NULL,
    patient_dob     DATE NOT NULL,
    payer_name      TEXT NOT NULL,
    payer_id        TEXT NOT NULL,
    date_of_service DATE NOT NULL,
    facility_type   TEXT NOT NULL CHECK (facility_type IN (
                        'inpatient_hospital',
                        'outpatient_hospital',
                        'physician_office',
                        'ambulatory_surgery_center',
                        'skilled_nursing_facility'
                    )),
    diagnosis_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    procedure_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    billed_amount   NUMERIC(12, 2) NOT NULL CHECK (billed_amount >= 0),
    status          TEXT NOT NULL DEFAULT 'RECEIVED' CHECK (status IN (
                        'RECEIVED',
                        'ELIGIBILITY_FAILED',
                        'ELIGIBILITY_VERIFIED',
                        'AUDIT_COMPLETE',
                        'HUMAN_REVIEW_REQUIRED',
                        'CORRECTION_PENDING',
                        'READY_FOR_SUBMISSION',
                        'SUBMITTED',
                        'DENIED',
                        'APPEAL_DRAFT_READY',
                        'APPEAL_PENDING_APPROVAL',
                        'APPEAL_SUBMITTED',
                        'APPROVED',
                        'APPROVED_ON_APPEAL',
                        'FINAL_DENIED'
                    )),
    market          TEXT NOT NULL DEFAULT 'US' CHECK (market IN ('US', 'INDIA')),
    assigned_user_id UUID,
    human_review_flag BOOLEAN NOT NULL DEFAULT false,
    human_review_reason TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX idx_claims_status ON claims (status);
CREATE INDEX idx_claims_payer_name ON claims (payer_name);
CREATE INDEX idx_claims_created_at ON claims (created_at DESC);
CREATE INDEX idx_claims_assigned_user ON claims (assigned_user_id);
CREATE INDEX idx_claims_market ON claims (market);

-- Auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_claims_updated_at
    BEFORE UPDATE ON claims
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 2. AUDIT_RESULTS TABLE
-- One row per completed code audit (linked to a claim)
-- Stores LLM call metadata for LLMOps cost/performance tracking
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_results (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id            UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    findings            JSONB NOT NULL DEFAULT '[]'::jsonb,
    overall_confidence  NUMERIC(4, 3) NOT NULL CHECK (overall_confidence BETWEEN 0 AND 1),
    audit_summary       TEXT,
    llm_model_used      TEXT NOT NULL,
    prompt_tokens       INTEGER NOT NULL DEFAULT 0,
    completion_tokens   INTEGER NOT NULL DEFAULT 0,
    latency_ms          INTEGER NOT NULL DEFAULT 0,
    rag_documents_used  INTEGER NOT NULL DEFAULT 0,
    top_rag_similarity  NUMERIC(4, 3),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_results_claim_id ON audit_results (claim_id);
CREATE INDEX idx_audit_results_created_at ON audit_results (created_at DESC);

-- =============================================================================
-- 3. DENIAL_PREDICTIONS TABLE
-- Risk score and factors for each claim's denial likelihood
-- =============================================================================
CREATE TABLE IF NOT EXISTS denial_predictions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id            UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    risk_score          INTEGER NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    risk_factors        JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommended_action  TEXT NOT NULL CHECK (recommended_action IN (
                            'SUBMIT_AS_IS',
                            'CORRECT_AND_RESUBMIT',
                            'ESCALATE_TO_HUMAN'
                        )),
    confidence          NUMERIC(4, 3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    llm_model_used      TEXT NOT NULL,
    prompt_tokens       INTEGER NOT NULL DEFAULT 0,
    completion_tokens   INTEGER NOT NULL DEFAULT 0,
    latency_ms          INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_denial_predictions_claim_id ON denial_predictions (claim_id);
CREATE INDEX idx_denial_predictions_risk_score ON denial_predictions (risk_score DESC);

-- =============================================================================
-- 4. APPEAL_LETTERS TABLE
-- Generated appeal letter drafts and their approval status
-- =============================================================================
CREATE TABLE IF NOT EXISTS appeal_letters (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id              UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    denial_reason_code    TEXT NOT NULL,
    denial_reason_desc    TEXT,
    payer_policy_excerpt  TEXT,
    guideline_excerpt     TEXT,
    letter_content        TEXT NOT NULL,
    supporting_documents  JSONB NOT NULL DEFAULT '[]'::jsonb,
    status                TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN (
                              'DRAFT',
                              'APPROVED',
                              'SUBMITTED'
                          )),
    approved_by           UUID,
    approved_at           TIMESTAMPTZ,
    llm_model_used        TEXT NOT NULL,
    prompt_tokens         INTEGER NOT NULL DEFAULT 0,
    completion_tokens     INTEGER NOT NULL DEFAULT 0,
    latency_ms            INTEGER NOT NULL DEFAULT 0,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_appeal_letters_claim_id ON appeal_letters (claim_id);
CREATE INDEX idx_appeal_letters_status ON appeal_letters (status);

-- =============================================================================
-- 5. CLAIM_OUTCOMES TABLE
-- Final resolution records — triggers feedback loop into Qdrant
-- =============================================================================
CREATE TABLE IF NOT EXISTS claim_outcomes (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id          UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    outcome           TEXT NOT NULL CHECK (outcome IN (
                          'APPROVED',
                          'DENIED',
                          'APPROVED_ON_APPEAL',
                          'FINAL_DENIED'
                      )),
    resolution_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    amount_recovered  NUMERIC(12, 2) DEFAULT 0,
    notes             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_claim_outcomes_claim_id ON claim_outcomes (claim_id);
CREATE INDEX idx_claim_outcomes_outcome ON claim_outcomes (outcome);
CREATE INDEX idx_claim_outcomes_resolution_date ON claim_outcomes (resolution_date DESC);

-- Unique constraint: one outcome per claim (upsert-friendly)
CREATE UNIQUE INDEX idx_claim_outcomes_unique_claim ON claim_outcomes (claim_id);
