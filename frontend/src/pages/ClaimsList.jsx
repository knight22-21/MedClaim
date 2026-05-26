import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Search, Filter, ChevronRight, Play } from 'lucide-react';

export default function ClaimsList() {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchClaims = async () => {
    try {
      const res = await api.getClaims();
      setClaims(res.data.data || []);
    } catch (err) {
      console.error("Failed to fetch claims", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClaims();
  }, []);

  const handleRunPipeline = async (id, e) => {
    e.stopPropagation();
    try {
      await api.startPipeline(id);
      alert("Pipeline started in background");
      fetchClaims();
    } catch (err) {
      alert("Error starting pipeline");
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'RECEIVED': return { bg: 'rgba(107, 114, 128, 0.1)', text: 'var(--text-secondary)' };
      case 'APPROVED':
      case 'READY_FOR_SUBMISSION': return { bg: 'rgba(16, 185, 129, 0.1)', text: 'var(--success)' };
      case 'DENIED':
      case 'FINAL_DENIED': return { bg: 'rgba(239, 68, 68, 0.1)', text: 'var(--danger)' };
      case 'HUMAN_REVIEW_REQUIRED': return { bg: 'rgba(245, 158, 11, 0.1)', text: 'var(--warning)' };
      default: return { bg: 'rgba(59, 130, 246, 0.1)', text: 'var(--primary)' };
    }
  };

  return (
    <div className="flex-col gap-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1>Claims Management</h1>
          <p style={{ color: 'var(--text-secondary)' }}>View and manage all ingested medical claims.</p>
        </div>
        <div className="flex gap-4">
          <button className="btn btn-glass"><Filter size={16}/> Filter</button>
          <div className="glass-panel" style={{ padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '8px', borderRadius: '8px' }}>
            <Search size={16} color="var(--text-muted)" />
            <input type="text" placeholder="Search claims..." style={{ background: 'transparent', border: 'none', color: 'var(--text-primary)', outline: 'none' }} />
          </div>
        </div>
      </div>

      <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-glass)', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              <th style={{ padding: '16px 24px', fontWeight: 500 }}>Claim ID</th>
              <th style={{ padding: '16px 24px', fontWeight: 500 }}>Patient</th>
              <th style={{ padding: '16px 24px', fontWeight: 500 }}>Date of Service</th>
              <th style={{ padding: '16px 24px', fontWeight: 500 }}>Payer</th>
              <th style={{ padding: '16px 24px', fontWeight: 500 }}>Billed</th>
              <th style={{ padding: '16px 24px', fontWeight: 500 }}>Status</th>
              <th style={{ padding: '16px 24px', fontWeight: 500 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan="7" style={{ padding: '24px', textAlign: 'center' }}>Loading claims...</td></tr>
            ) : claims.length === 0 ? (
              <tr><td colSpan="7" style={{ padding: '24px', textAlign: 'center' }}>No claims found.</td></tr>
            ) : (
              claims.map(claim => {
                const statusColors = getStatusColor(claim.status);
                return (
                  <tr key={claim.id} style={{ borderBottom: '1px solid var(--border-glass)', cursor: 'pointer', transition: 'background 0.2s' }} className="hover:bg-white/5">
                    <td style={{ padding: '16px 24px', fontFamily: 'monospace' }}>{claim.id.substring(0,8)}...</td>
                    <td style={{ padding: '16px 24px', fontWeight: 500 }}>{claim.patient_name}</td>
                    <td style={{ padding: '16px 24px', color: 'var(--text-secondary)' }}>{claim.date_of_service}</td>
                    <td style={{ padding: '16px 24px' }}>{claim.payer_name}</td>
                    <td style={{ padding: '16px 24px', fontWeight: 500 }}>${claim.billed_amount?.toFixed(2)}</td>
                    <td style={{ padding: '16px 24px' }}>
                      <span className="badge" style={{ background: statusColors.bg, color: statusColors.text }}>
                        {claim.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td style={{ padding: '16px 24px' }}>
                      <div className="flex gap-2">
                        {claim.status === 'RECEIVED' && (
                          <button className="btn btn-primary" onClick={(e) => handleRunPipeline(claim.id, e)} style={{ padding: '4px 8px' }}>
                            <Play size={14} /> Run
                          </button>
                        )}
                        <button className="btn btn-glass" style={{ padding: '4px 8px' }}>
                          <ChevronRight size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
