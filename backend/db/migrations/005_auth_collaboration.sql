-- =============================================================================
-- MedClaim — Authentication & Collaboration Schema
-- Migration 005: User profiles, approval workflows, comments, blog, leads
-- Run in: Supabase SQL Editor
-- =============================================================================

-- =============================================================================
-- 1. USER_PROFILES TABLE
-- Extends Supabase auth.users with additional profile information
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    role TEXT NOT NULL CHECK (role IN ('admin', 'billing_specialist', 'viewer')),
    department TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_profiles_email ON user_profiles(email);
CREATE INDEX idx_user_profiles_role ON user_profiles(role);

-- Auto-update updated_at on row modification
CREATE TRIGGER trigger_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 2. APPROVAL_WORKFLOWS TABLE
-- Configurable approval workflow definitions
-- =============================================================================
CREATE TABLE IF NOT EXISTS approval_workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_by UUID REFERENCES user_profiles(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_approval_workflows_active ON approval_workflows(is_active);

CREATE TRIGGER trigger_approval_workflows_updated_at
    BEFORE UPDATE ON approval_workflows
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 3. APPROVAL_CHAIN_STEPS TABLE
-- Individual steps within an approval workflow
-- =============================================================================
CREATE TABLE IF NOT EXISTS approval_chain_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID NOT NULL REFERENCES approval_workflows(id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL,
    required_role TEXT NOT NULL CHECK (required_role IN ('admin', 'billing_specialist')),
    timeout_hours INTEGER NOT NULL DEFAULT 24,
    escalation_to_role TEXT CHECK (escalation_to_role IN ('admin', 'billing_specialist')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chain_steps_workflow ON approval_chain_steps(workflow_id);
CREATE INDEX idx_chain_steps_order ON approval_chain_steps(workflow_id, step_order);

-- =============================================================================
-- 4. CLAIM_APPROVALS TABLE
-- Tracks approval status for individual claims
-- =============================================================================
CREATE TABLE IF NOT EXISTS claim_approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    workflow_id UUID NOT NULL REFERENCES approval_workflows(id),
    current_step INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'approved', 'rejected', 'escalated', 'expired'
    )),
    assigned_to UUID REFERENCES user_profiles(id),
    timeout_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_claim_approvals_claim ON claim_approvals(claim_id);
CREATE INDEX idx_claim_approvals_assigned ON claim_approvals(assigned_to);
CREATE INDEX idx_claim_approvals_status ON claim_approvals(status);
CREATE UNIQUE INDEX idx_claim_approvals_unique ON claim_approvals(claim_id);

CREATE TRIGGER trigger_claim_approvals_updated_at
    BEFORE UPDATE ON claim_approvals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 5. APPROVAL_HISTORY TABLE
-- Audit trail for all approval actions
-- =============================================================================
CREATE TABLE IF NOT EXISTS approval_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_approval_id UUID NOT NULL REFERENCES claim_approvals(id) ON DELETE CASCADE,
    step INTEGER NOT NULL,
    approver_id UUID REFERENCES user_profiles(id),
    action TEXT NOT NULL CHECK (action IN ('approved', 'rejected', 'escalated', 'timeout')),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_approval_history_claim ON approval_history(claim_approval_id);
CREATE INDEX idx_approval_history_approver ON approval_history(approver_id);

-- =============================================================================
-- 6. COMMENTS TABLE
-- Threaded comments on claims
-- =============================================================================
CREATE TABLE IF NOT EXISTS comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES user_profiles(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX idx_comments_claim ON comments(claim_id);
CREATE INDEX idx_comments_parent ON comments(parent_id);
CREATE INDEX idx_comments_user ON comments(user_id);
CREATE INDEX idx_comments_created ON comments(created_at DESC);

CREATE TRIGGER trigger_comments_updated_at
    BEFORE UPDATE ON comments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 7. LEAD_CAPTURES TABLE
-- Lead capture from public website
-- =============================================================================
CREATE TABLE IF NOT EXISTS lead_captures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type TEXT NOT NULL CHECK (type IN ('demo_request', 'contact')),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT,
    phone TEXT,
    message TEXT,
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'contacted', 'qualified', 'closed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_lead_captures_type ON lead_captures(type);
CREATE INDEX idx_lead_captures_status ON lead_captures(status);
CREATE INDEX idx_lead_captures_created ON lead_captures(created_at DESC);

-- =============================================================================
-- 8. BLOG_POSTS TABLE
-- Blog posts for public website
-- =============================================================================
CREATE TABLE IF NOT EXISTS blog_posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    excerpt TEXT,
    content TEXT NOT NULL,
    author_id UUID REFERENCES user_profiles(id),
    category TEXT,
    tags JSONB DEFAULT '[]'::jsonb,
    published BOOLEAN NOT NULL DEFAULT false,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_blog_posts_slug ON blog_posts(slug);
CREATE INDEX idx_blog_posts_published ON blog_posts(published);
CREATE INDEX idx_blog_posts_category ON blog_posts(category);

CREATE TRIGGER trigger_blog_posts_updated_at
    BEFORE UPDATE ON blog_posts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 9. AUDIT_LOGS TABLE
-- Comprehensive audit trail for all system actions
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES user_profiles(id),
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);

-- =============================================================================
-- 10. NOTIFICATIONS TABLE
-- In-app notifications for users
-- =============================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_profiles(id),
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT,
    link TEXT,
    read BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(user_id, read);

-- =============================================================================
-- 11. MODIFY CLAIMS TABLE
-- Add approval workflow columns
-- =============================================================================
ALTER TABLE claims ADD COLUMN IF NOT EXISTS approval_workflow_id UUID REFERENCES approval_workflows(id);
ALTER TABLE claims ADD COLUMN IF NOT EXISTS current_approval_step INTEGER DEFAULT 1;

-- =============================================================================
-- 12. INSERT DEFAULT APPROVAL WORKFLOW
-- Create a default 2-step approval workflow
-- =============================================================================
INSERT INTO approval_workflows (name, description, is_active, created_by)
VALUES (
    'Default Approval Workflow',
    'Standard 2-step approval: Specialist review followed by Admin escalation if needed',
    true,
    NULL
) ON CONFLICT DO NOTHING;

-- Get the default workflow ID (assuming it's the first one)
-- This will be used to add steps
DO $$
DECLARE
    default_workflow_id UUID;
BEGIN
    SELECT id INTO default_workflow_id 
    FROM approval_workflows 
    WHERE name = 'Default Approval Workflow' 
    LIMIT 1;
    
    IF default_workflow_id IS NOT NULL THEN
        -- Step 1: Billing Specialist (24h timeout)
        INSERT INTO approval_chain_steps (workflow_id, step_order, required_role, timeout_hours, escalation_to_role)
        VALUES (default_workflow_id, 1, 'billing_specialist', 24, 'admin')
        ON CONFLICT DO NOTHING;
        
        -- Step 2: Admin (48h timeout)
        INSERT INTO approval_chain_steps (workflow_id, step_order, required_role, timeout_hours)
        VALUES (default_workflow_id, 2, 'admin', 48)
        ON CONFLICT DO NOTHING;
    END IF;
END $$;
