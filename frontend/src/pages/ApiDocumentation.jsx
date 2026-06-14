import React from 'react';
import { Book, Code, Database, Users, Workflow, MessageSquare, Shield, Zap, FileText, ArrowRight } from 'lucide-react';

export default function ApiDocumentation() {
  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc' }}>
      {/* Header */}
      <header style={{ background: '#ffffff', borderBottom: '1px solid #e5e7eb', padding: '24px 48px' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <h1 style={{ fontSize: '2rem', fontWeight: 700, color: '#0f172a', marginBottom: '8px' }}>API Documentation</h1>
          <p style={{ color: '#64748b', fontSize: '1rem' }}>Complete reference for MedClaim REST API endpoints</p>
        </div>
      </header>

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '48px' }}>
        {/* Overview */}
        <section style={{ marginBottom: '48px' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f172a', marginBottom: '16px' }}>Overview</h2>
          <div style={{ background: '#ffffff', padding: '24px', borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)' }}>
            <p style={{ color: '#64748b', lineHeight: 1.6, marginBottom: '16px' }}>
              The MedClaim API provides endpoints for managing insurance claims, running AI-powered claim processing, 
              approvals, user management, and more. All endpoints return JSON responses and use standard HTTP status codes.
            </p>
            <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#10b981' }}></div>
                <span style={{ fontSize: '0.875rem', color: '#64748b' }}>Base URL: <code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem' }}>https://your-backend.onrender.com</code></span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#3b82f6' }}></div>
                <span style={{ fontSize: '0.875rem', color: '#64748b' }}>Authentication: Bearer Token</span>
              </div>
            </div>
          </div>
        </section>

        {/* Authentication */}
        <section style={{ marginBottom: '48px' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f172a', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Shield size={24} color="#0284c7" /> Authentication
          </h2>
          <div style={{ background: '#ffffff', padding: '24px', borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)' }}>
            <p style={{ color: '#64748b', lineHeight: 1.6, marginBottom: '16px' }}>
              Most endpoints require authentication using a Bearer token. Include the token in the Authorization header.
            </p>
            <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', fontFamily: 'monospace', fontSize: '0.875rem', color: '#e2e8f0', overflowX: 'auto' }}>
              Authorization: Bearer &lt;your_access_token&gt;
            </div>
          </div>
        </section>

        {/* Endpoints */}
        <section>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f172a', marginBottom: '24px' }}>API Endpoints</h2>

          {/* Authentication */}
          <div style={{ marginBottom: '32px' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#0f172a', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Shield size={20} color="#0284c7" /> Authentication
            </h3>
            <div style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)', overflow: 'hidden' }}>
              <EndpointCard
                method="POST"
                path="/auth/login"
                description="Authenticate user and receive access token"
                body={{ email: "string", password: "string" }}
              />
              <EndpointCard
                method="POST"
                path="/auth/logout"
                description="Logout current user"
                auth={true}
              />
              <EndpointCard
                method="GET"
                path="/auth/me"
                description="Get current user profile"
                auth={true}
              />
              <EndpointCard
                method="POST"
                path="/auth/refresh"
                description="Refresh access token using refresh token"
                body={{ refresh_token: "string" }}
              />
            </div>
          </div>

          {/* Claims */}
          <div style={{ marginBottom: '32px' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#0f172a', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={20} color="#0284c7" /> Claims
            </h3>
            <div style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)', overflow: 'hidden' }}>
              <EndpointCard
                method="GET"
                path="/claims"
                description="Get all claims"
                auth={true}
              />
              <EndpointCard
                method="GET"
                path="/claims/{id}"
                description="Get claim details by ID"
                auth={true}
              />
              <EndpointCard
                method="POST"
                path="/claims"
                description="Ingest a new claim"
                auth={true}
                body={{ patient_name: "string", patient_dob: "string", date_of_service: "string", payer_name: "string", payer_id: "string", facility_type: "string", billed_amount: "number" }}
              />
              <EndpointCard
                method="POST"
                path="/claims/{id}/approve"
                description="Approve a claim (HITL override)"
                auth={true}
                body={{ human_approved: true, approved_by: "string", notes: "string" }}
              />
              <EndpointCard
                method="POST"
                path="/claims/{id}/reject"
                description="Reject a claim (HITL override)"
                auth={true}
                body={{ human_approved: true, approved_by: "string", notes: "string" }}
              />
            </div>
          </div>

          {/* Agents Pipeline */}
          <div style={{ marginBottom: '32px' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#0f172a', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Zap size={20} color="#0284c7" /> AI Pipeline
            </h3>
            <div style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)', overflow: 'hidden' }}>
              <EndpointCard
                method="POST"
                path="/agents/process/{id}"
                description="Start AI processing pipeline for a claim"
                auth={true}
              />
              <EndpointCard
                method="GET"
                path="/agents/status/{job_id}"
                description="Get status of a pipeline job"
                auth={true}
              />
              <EndpointCard
                method="GET"
                path="/agents/jobs/{claim_id}"
                description="Get all jobs for a claim"
                auth={true}
              />
            </div>
          </div>

          {/* Analytics */}
          <div style={{ marginBottom: '32px' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#0f172a', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Database size={20} color="#0284c7" /> Analytics
            </h3>
            <div style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)', overflow: 'hidden' }}>
              <EndpointCard
                method="GET"
                path="/analytics/summary"
                description="Get dashboard summary statistics"
                auth={true}
              />
              <EndpointCard
                method="GET"
                path="/analytics/denials"
                description="Get denial volume by payer"
                auth={true}
              />
              <EndpointCard
                method="GET"
                path="/analytics/volume"
                description="Get claim volume over time"
                auth={true}
              />
            </div>
          </div>

          {/* Workflows */}
          <div style={{ marginBottom: '32px' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#0f172a', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Workflow size={20} color="#0284c7" /> Approval Workflows
            </h3>
            <div style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)', overflow: 'hidden' }}>
              <EndpointCard
                method="GET"
                path="/workflows"
                description="Get all approval workflows"
                auth={true}
                query="is_active (optional)"
              />
              <EndpointCard
                method="GET"
                path="/workflows/{id}"
                description="Get workflow details"
                auth={true}
              />
              <EndpointCard
                method="POST"
                path="/workflows"
                description="Create new approval workflow"
                auth={true}
                body={{ name: "string", description: "string", is_active: true }}
              />
              <EndpointCard
                method="PUT"
                path="/workflows/{id}"
                description="Update workflow"
                auth={true}
                body={{ name: "string", description: "string", is_active: true }}
              />
              <EndpointCard
                method="DELETE"
                path="/workflows/{id}"
                description="Delete workflow"
                auth={true}
              />
              <EndpointCard
                method="POST"
                path="/workflows/{id}/steps"
                description="Add step to workflow"
                auth={true}
                body={{ role: "string", step_order: "number", timeout_hours: "number" }}
              />
              <EndpointCard
                method="POST"
                path="/workflows/claims/{claim_id}/initiate"
                description="Initiate approval workflow for claim"
                auth={true}
                body={{ workflow_id: "string" }}
              />
              <EndpointCard
                method="POST"
                path="/workflows/claims/{claim_id}/approve"
                description="Process claim approval action"
                auth={true}
                body={{ action: "approve|reject|escalate", notes: "string" }}
              />
            </div>
          </div>

          {/* Comments */}
          <div style={{ marginBottom: '32px' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#0f172a', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <MessageSquare size={20} color="#0284c7" /> Comments
            </h3>
            <div style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)', overflow: 'hidden' }}>
              <EndpointCard
                method="GET"
                path="/comments/claims/{claim_id}"
                description="Get comments for a claim"
                auth={true}
              />
              <EndpointCard
                method="POST"
                path="/comments"
                description="Create comment on claim"
                auth={true}
                body={{ claim_id: "string", user_id: "string", content: "string" }}
              />
              <EndpointCard
                method="PUT"
                path="/comments/{id}"
                description="Update comment"
                auth={true}
                body={{ content: "string" }}
              />
              <EndpointCard
                method="DELETE"
                path="/comments/{id}"
                description="Delete comment"
                auth={true}
              />
            </div>
          </div>

          {/* User Management */}
          <div style={{ marginBottom: '32px' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#0f172a', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Users size={20} color="#0284c7" /> User Management (Admin)
            </h3>
            <div style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)', overflow: 'hidden' }}>
              <EndpointCard
                method="GET"
                path="/admin/users"
                description="Get all users"
                auth={true}
                query="role, limit, offset"
              />
              <EndpointCard
                method="GET"
                path="/admin/users/{id}"
                description="Get user details"
                auth={true}
              />
              <EndpointCard
                method="POST"
                path="/admin/users"
                description="Create new user"
                auth={true}
                body={{ email: "string", full_name: "string", role: "string", department: "string", phone: "string" }}
              />
              <EndpointCard
                method="PUT"
                path="/admin/users/{id}"
                description="Update user"
                auth={true}
                body={{ email: "string", full_name: "string", role: "string", department: "string", phone: "string" }}
              />
              <EndpointCard
                method="DELETE"
                path="/admin/users/{id}"
                description="Delete user"
                auth={true}
              />
              <EndpointCard
                method="POST"
                path="/admin/users/invite"
                description="Invite user to platform"
                auth={true}
                body={{ email: "string" }}
              />
            </div>
          </div>

          {/* Voice AI */}
          <div style={{ marginBottom: '32px' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#0f172a', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Zap size={20} color="#0284c7" /> Voice AI
            </h3>
            <div style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)', overflow: 'hidden' }}>
              <EndpointCard
                method="POST"
                path="/voice/query"
                description="Submit voice query (multipart/form-data)"
                auth={true}
                body="audio file"
              />
              <EndpointCard
                method="POST"
                path="/voice/text-query"
                description="Submit text query"
                auth={true}
                body={{ query: "string" }}
              />
            </div>
          </div>

          {/* Public Endpoints */}
          <div style={{ marginBottom: '32px' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#0f172a', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Book size={20} color="#0284c7" /> Public Endpoints (No Auth)
            </h3>
            <div style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)', overflow: 'hidden' }}>
              <EndpointCard
                method="GET"
                path="/public/blog"
                description="Get blog posts"
                query="category, limit, offset"
              />
              <EndpointCard
                method="GET"
                path="/public/blog/{slug}"
                description="Get blog post by slug"
              />
              <EndpointCard
                method="POST"
                path="/public/lead/demo"
                description="Submit demo request"
                body={{ name: "string", email: "string", company: "string", message: "string" }}
              />
              <EndpointCard
                method="POST"
                path="/public/lead/contact"
                description="Submit contact form"
                body={{ name: "string", email: "string", subject: "string", message: "string" }}
              />
            </div>
          </div>
        </section>

        {/* Status Codes */}
        <section style={{ marginBottom: '48px' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f172a', marginBottom: '24px' }}>HTTP Status Codes</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            <StatusCodeCard code="200" description="OK - Request successful" color="#10b981" />
            <StatusCodeCard code="201" description="Created - Resource created" color="#10b981" />
            <StatusCodeCard code="400" description="Bad Request - Invalid input" color="#f59e0b" />
            <StatusCodeCard code="401" description="Unauthorized - Missing/invalid token" color="#ef4444" />
            <StatusCodeCard code="403" description="Forbidden - Insufficient permissions" color="#ef4444" />
            <StatusCodeCard code="404" description="Not Found - Resource not found" color="#f59e0b" />
            <StatusCodeCard code="500" description="Server Error - Internal error" color="#ef4444" />
          </div>
        </section>
      </div>
    </div>
  );
}

function EndpointCard({ method, path, description, auth, body, query }) {
  const methodColors = {
    GET: { bg: '#dbeafe', text: '#1e40af', border: '#3b82f6' },
    POST: { bg: '#dcfce7', text: '#166534', border: '#22c55e' },
    PUT: { bg: '#fef3c7', text: '#92400e', border: '#f59e0b' },
    DELETE: { bg: '#fee2e2', text: '#991b1b', border: '#ef4444' },
  };

  const colors = methodColors[method] || methodColors.GET;

  return (
    <div style={{ padding: '20px', borderBottom: '1px solid #e5e7eb', '&:last-child': { borderBottom: 'none' } }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
        <span style={{
          padding: '4px 12px',
          borderRadius: '4px',
          background: colors.bg,
          color: colors.text,
          border: `1px solid ${colors.border}`,
          fontSize: '0.75rem',
          fontWeight: 700,
          minWidth: '60px',
          textAlign: 'center'
        }}>
          {method}
        </span>
        <code style={{ 
          background: '#f1f5f9', 
          padding: '6px 12px', 
          borderRadius: '4px', 
          fontSize: '0.875rem', 
          color: '#0f172a',
          fontFamily: 'monospace',
          flex: 1
        }}>
          {path}
        </code>
        {auth && (
          <span style={{ 
            padding: '4px 8px', 
            borderRadius: '4px', 
            background: '#fef3c7', 
            color: '#92400e', 
            fontSize: '0.75rem', 
            fontWeight: 600,
            border: '1px solid #fcd34d'
          }}>
            🔒 Auth Required
          </span>
        )}
      </div>
      <p style={{ color: '#64748b', fontSize: '0.875rem', marginBottom: '12px' }}>{description}</p>
      {body && (
        <div style={{ marginBottom: '8px' }}>
          <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600, marginRight: '8px' }}>Body:</span>
          <code style={{ background: '#f1f5f9', padding: '4px 8px', borderRadius: '4px', fontSize: '0.75rem', color: '#0f172a', fontFamily: 'monospace' }}>
            {typeof body === 'string' ? body : JSON.stringify(body)}
          </code>
        </div>
      )}
      {query && (
        <div>
          <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600, marginRight: '8px' }}>Query:</span>
          <code style={{ background: '#f1f5f9', padding: '4px 8px', borderRadius: '4px', fontSize: '0.75rem', color: '#0f172a', fontFamily: 'monospace' }}>
            {query}
          </code>
        </div>
      )}
    </div>
  );
}

function StatusCodeCard({ code, description, color }) {
  return (
    <div style={{ 
      padding: '16px', 
      borderRadius: '8px', 
      background: '#ffffff', 
      border: '1px solid #e5e7eb',
      boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
    }}>
      <div style={{ 
        fontSize: '1.5rem', 
        fontWeight: 700, 
        color: color, 
        marginBottom: '8px' 
      }}>
        {code}
      </div>
      <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
        {description}
      </div>
    </div>
  );
}
