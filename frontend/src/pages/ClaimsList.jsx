import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, pollJobUntilDone } from '../api/client';
import { Search, Filter, ChevronRight, Play, Plus, Loader } from 'lucide-react';

export default function ClaimsList() {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processingClaims, setProcessingClaims] = useState({}); // { claimId: "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" }
  const navigate = useNavigate();

  const fetchClaims = async () => {
    try {
      const res = await api.getClaims();
      setClaims(res.data.data?.claims || []);
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
      const res = await api.startPipeline(id);
      const jobId = res.data.data.job_id;

      // Track processing status inline
      setProcessingClaims(prev => ({ ...prev, [id]: "QUEUED" }));

      // Poll in background
      pollJobUntilDone(jobId, (job) => {
        setProcessingClaims(prev => ({ ...prev, [id]: job.status }));
      }).then(() => {
        // Pipeline finished — refresh the claims list
        fetchClaims();
        // Clear the processing state after a brief delay so user sees COMPLETED
        setTimeout(() => {
          setProcessingClaims(prev => {
            const next = { ...prev };
            delete next[id];
            return next;
          });
        }, 2000);
      }).catch(() => {
        setProcessingClaims(prev => ({ ...prev, [id]: "FAILED" }));
      });

    } catch (err) {
      alert("Error starting pipeline");
    }
  };

  const handleNewDummyClaim = async () => {
    const dummyClaim = {
      patient_name: "Jane Doe",
      patient_dob: "1988-05-12",
      payer_name: "Medicare",
      payer_id: "MCR-001",
      date_of_service: new Date().toISOString().split('T')[0],
      facility_type: "physician_office",
      diagnosis_codes: [{ code: "J18.9", description: "Pneumonia" }],
      procedure_codes: [{ code: "99213", description: "Office visit" }, { code: "99214", description: "Upcoded visit" }],
      billed_amount: 350.00,
      market: "US"
    };

    try {
      await api.ingestClaim(dummyClaim);
      fetchClaims();
    } catch (err) {
      alert("Failed to create dummy claim.");
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'RECEIVED': return { bg: '#f1f5f9', text: '#64748b', border: '#e2e8f0' };
      case 'APPROVED':
      case 'READY_FOR_SUBMISSION': return { bg: '#f0fdf4', text: '#059669', border: '#bbf7d0' };
      case 'DENIED':
      case 'FINAL_DENIED': return { bg: '#fef2f2', text: '#dc2626', border: '#fecaca' };
      case 'HUMAN_REVIEW_REQUIRED': return { bg: '#fef3c7', text: '#d97706', border: '#fde68a' };
      default: return { bg: '#e0f2fe', text: '#0284c7', border: '#bae6fd' };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 700, color: '#0f172a', marginBottom: '8px' }}>Claims Management</h1>
          <p style={{ color: '#64748b', fontSize: '1rem' }}>View and manage all ingested medical claims.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button 
            onClick={handleNewDummyClaim}
            style={{
              padding: '10px 20px',
              borderRadius: '6px',
              background: '#0284c7',
              color: 'white',
              border: 'none',
              fontWeight: 600,
              cursor: 'pointer',
              fontSize: '0.875rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 4px 6px rgba(2, 132, 199, 0.2)'
            }}
          >
            <Plus size={16}/> New Claim
          </button>
          <button style={{
            padding: '10px 20px',
            borderRadius: '6px',
            background: '#ffffff',
            color: '#64748b',
            border: '1px solid #e5e7eb',
            fontWeight: 500,
            cursor: 'pointer',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <Filter size={16}/> Filter
          </button>
          <div style={{ 
            padding: '8px 16px', 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px', 
            borderRadius: '6px',
            background: '#ffffff',
            border: '1px solid #e5e7eb',
            boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
          }}>
            <Search size={16} color="#9ca3af" />
            <input 
              type="text" 
              placeholder="Search claims..." 
              style={{ background: 'transparent', border: 'none', color: '#1f2937', outline: 'none', fontSize: '0.875rem' }} 
            />
          </div>
        </div>
      </div>

      <div style={{ 
        padding: 0, 
        overflow: 'hidden',
        borderRadius: '12px',
        background: '#ffffff',
        border: '1px solid #e5e7eb',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)'
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #e5e7eb', color: '#64748b', fontSize: '0.875rem', background: '#f8fafc' }}>
              <th style={{ padding: '16px 24px', fontWeight: 600 }}>Claim ID</th>
              <th style={{ padding: '16px 24px', fontWeight: 600 }}>Patient</th>
              <th style={{ padding: '16px 24px', fontWeight: 600 }}>Date of Service</th>
              <th style={{ padding: '16px 24px', fontWeight: 600 }}>Payer</th>
              <th style={{ padding: '16px 24px', fontWeight: 600 }}>Billed</th>
              <th style={{ padding: '16px 24px', fontWeight: 600 }}>Status</th>
              <th style={{ padding: '16px 24px', fontWeight: 600 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan="7" style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>Loading claims...</td></tr>
            ) : claims.length === 0 ? (
              <tr><td colSpan="7" style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>No claims found.</td></tr>
            ) : (
              claims.map(claim => {
                const statusColors = getStatusColor(claim.status);
                return (
                  <tr 
                    key={claim.id} 
                    onClick={() => navigate(`/claims/${claim.id}`)}
                    style={{ borderBottom: '1px solid #e5e7eb', cursor: 'pointer', transition: 'background 0.2s' }} 
                    onMouseOver={(e) => e.currentTarget.style.background = '#f8fafc'}
                    onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '16px 24px', fontFamily: 'monospace', color: '#64748b' }}>{claim.id.substring(0,8)}...</td>
                    <td style={{ padding: '16px 24px', fontWeight: 500, color: '#0f172a' }}>{claim.patient_name}</td>
                    <td style={{ padding: '16px 24px', color: '#64748b' }}>{claim.date_of_service}</td>
                    <td style={{ padding: '16px 24px', color: '#0f172a' }}>{claim.payer_name}</td>
                    <td style={{ padding: '16px 24px', fontWeight: 500, color: '#0f172a' }}>${claim.billed_amount?.toFixed(2)}</td>
                    <td style={{ padding: '16px 24px' }}>
                      <span style={{ 
                        padding: '4px 12px', 
                        borderRadius: '4px', 
                        background: statusColors.bg, 
                        color: statusColors.text,
                        border: `1px solid ${statusColors.border}`,
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        textTransform: 'capitalize'
                      }}>
                        {claim.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td style={{ padding: '16px 24px' }}>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        {processingClaims[claim.id] ? (
                          <span style={{ 
                            padding: '4px 12px',
                            borderRadius: '4px',
                            background: processingClaims[claim.id] === 'FAILED' ? '#fef2f2' : '#e0f2fe', 
                            color: processingClaims[claim.id] === 'FAILED' ? '#dc2626' : '#0284c7',
                            border: processingClaims[claim.id] === 'FAILED' ? '1px solid #fecaca' : '1px solid #bae6fd',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px'
                          }}>
                            {processingClaims[claim.id] !== 'COMPLETED' && processingClaims[claim.id] !== 'FAILED' && (
                              <Loader size={12} style={{ animation: 'spin 1s linear infinite' }} />
                            )}
                            {processingClaims[claim.id]}
                          </span>
                        ) : claim.status === 'RECEIVED' ? (
                          <button 
                            onClick={(e) => handleRunPipeline(claim.id, e)}
                            style={{
                              padding: '6px 12px',
                              borderRadius: '6px',
                              background: '#0284c7',
                              color: 'white',
                              border: 'none',
                              fontWeight: 600,
                              cursor: 'pointer',
                              fontSize: '0.75rem',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px',
                              boxShadow: '0 2px 4px rgba(2, 132, 199, 0.2)'
                            }}
                          >
                            <Play size={14} /> Run
                          </button>
                        ) : null}
                        <button style={{
                          padding: '6px',
                          borderRadius: '6px',
                          background: '#ffffff',
                          color: '#64748b',
                          border: '1px solid #e5e7eb',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center'
                        }}>
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
