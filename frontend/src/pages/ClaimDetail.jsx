import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { ArrowLeft, CheckCircle, AlertTriangle, Play, FileText, User } from 'lucide-react';

export default function ClaimDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [claim, setClaim] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchClaim = async () => {
    try {
      const res = await api.getClaim(id);
      setClaim(res.data.data);
    } catch (err) {
      console.error("Failed to fetch claim details", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClaim();
  }, [id]);

  const handleRunPipeline = async () => {
    try {
      await api.startPipeline(id);
      alert("Pipeline started in background");
      fetchClaim(); // Refresh
    } catch (err) {
      alert("Error starting pipeline");
    }
  };

  if (loading) return <div style={{ padding: '24px' }}>Loading claim details...</div>;
  if (!claim) return <div style={{ padding: '24px' }}>Claim not found.</div>;

  return (
    <div className="flex-col gap-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/claims')} className="btn btn-glass" style={{ padding: '8px' }}>
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 style={{ marginBottom: 0 }}>Claim Details</h1>
          <p style={{ color: 'var(--text-secondary)' }}>ID: {claim.id}</p>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '12px' }}>
          <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.1)', color: 'var(--primary)' }}>
            {claim.status.replace(/_/g, ' ')}
          </span>
          {claim.status === 'RECEIVED' && (
            <button className="btn btn-primary" onClick={handleRunPipeline}>
              <Play size={16} /> Run Pipeline
            </button>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Left Column: Basic Info */}
        <div className="flex-col gap-6">
          <div className="glass-card">
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <User size={18} color="var(--primary)"/> Patient Information
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Name</div>
                <div style={{ fontWeight: 500 }}>{claim.patient_name}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>DOB</div>
                <div style={{ fontWeight: 500 }}>{claim.patient_dob}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Date of Service</div>
                <div style={{ fontWeight: 500 }}>{claim.date_of_service}</div>
              </div>
            </div>
          </div>

          <div className="glass-card">
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={18} color="var(--primary)"/> Billing Details
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div className="flex justify-between">
                <span style={{ color: 'var(--text-secondary)' }}>Payer</span>
                <span style={{ fontWeight: 500 }}>{claim.payer_name}</span>
              </div>
              <div className="flex justify-between">
                <span style={{ color: 'var(--text-secondary)' }}>Payer ID</span>
                <span style={{ fontWeight: 500 }}>{claim.payer_id}</span>
              </div>
              <div className="flex justify-between">
                <span style={{ color: 'var(--text-secondary)' }}>Facility Type</span>
                <span style={{ fontWeight: 500 }}>{claim.facility_type}</span>
              </div>
              <div className="flex justify-between" style={{ marginTop: '8px', paddingTop: '12px', borderTop: '1px dashed var(--border-glass)' }}>
                <span style={{ fontWeight: 600 }}>Total Billed</span>
                <span style={{ fontWeight: 600, color: 'var(--primary)' }}>${claim.billed_amount?.toFixed(2)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: AI Analysis */}
        <div className="flex-col gap-6">
          <div className="glass-card">
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle size={18} color="var(--success)"/> Code Audit Results
            </h3>
            {claim.audit_findings ? (
              <div className="flex-col gap-4">
                <div className="flex justify-between items-center">
                  <span>Confidence Score</span>
                  <span style={{ fontWeight: 600, color: claim.audit_confidence > 0.8 ? 'var(--success)' : 'var(--warning)' }}>
                    {(claim.audit_confidence * 100).toFixed(0)}%
                  </span>
                </div>
                {claim.audit_findings.length === 0 ? (
                  <div style={{ padding: '12px', background: 'rgba(16, 185, 129, 0.05)', borderRadius: '4px', border: '1px solid rgba(16, 185, 129, 0.2)', color: 'var(--success)' }}>
                    No coding issues detected. Clean claim.
                  </div>
                ) : (
                  claim.audit_findings.map((f, i) => (
                    <div key={i} style={{ padding: '12px', background: 'rgba(239, 68, 68, 0.05)', borderRadius: '4px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                      <div style={{ fontWeight: 600, color: 'var(--danger)' }}>{f.issue_type}: Code {f.code}</div>
                      <div style={{ fontSize: '0.875rem', marginTop: '4px' }}>{f.description}</div>
                      <div style={{ fontSize: '0.875rem', marginTop: '8px', fontStyle: 'italic' }}>Suggested: {f.suggested_correction}</div>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div style={{ color: 'var(--text-muted)' }}>Audit not yet performed.</div>
            )}
          </div>

          <div className="glass-card">
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={18} color={claim.denial_risk_score > 70 ? "var(--danger)" : "var(--warning)"}/> Denial Prediction
            </h3>
            {claim.denial_risk_score !== null ? (
              <div className="flex-col gap-4">
                <div className="flex justify-between items-center">
                  <span>Risk Score</span>
                  <span style={{ fontWeight: 600, color: claim.denial_risk_score > 70 ? 'var(--danger)' : 'var(--warning)' }}>
                    {claim.denial_risk_score}/100
                  </span>
                </div>
                {claim.risk_factors && claim.risk_factors.length > 0 ? (
                  claim.risk_factors.map((r, i) => (
                    <div key={i} style={{ fontSize: '0.875rem', padding: '8px 0', borderBottom: '1px dashed var(--border-glass)' }}>
                      <span style={{ fontWeight: 500 }}>{r.factor}</span>
                      <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>{r.description}</p>
                    </div>
                  ))
                ) : (
                  <div style={{ color: 'var(--text-secondary)' }}>No significant risk factors identified.</div>
                )}
              </div>
            ) : (
              <div style={{ color: 'var(--text-muted)' }}>Prediction not yet performed.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
