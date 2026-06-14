import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, pollJobUntilDone } from '../api/client';
import { ArrowLeft, CheckCircle, AlertTriangle, Play, FileText, User, Loader, ShieldAlert, MessageSquare, Send, Trash2 } from 'lucide-react';

export default function ClaimDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [claim, setClaim] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pipelineStatus, setPipelineStatus] = useState(null); // null | "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED"
  const [hitlNotes, setHitlNotes] = useState("");
  const [hitlSubmitting, setHitlSubmitting] = useState(false);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState("");
  const [commentSubmitting, setCommentSubmitting] = useState(false);

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

  const fetchComments = async () => {
    try {
      const res = await api.getClaimComments(id);
      setComments(res.data.data || []);
    } catch (err) {
      console.error("Failed to fetch comments", err);
    }
  };

  useEffect(() => {
    fetchClaim();
    fetchComments();
  }, [id]);

  const handleRunPipeline = async () => {
    try {
      const res = await api.startPipeline(id);
      const jobId = res.data.data.job_id;
      setPipelineStatus("QUEUED");

      const finalJob = await pollJobUntilDone(jobId, (job) => {
        setPipelineStatus(job.status);
      });

      await fetchClaim();
      setTimeout(() => setPipelineStatus(null), 3000);
    } catch (err) {
      setPipelineStatus("FAILED");
    }
  };

  const handleHitlAction = async (action) => {
    if (!hitlNotes.trim() && action === 'reject') {
      alert("Please provide notes for rejecting the claim.");
      return;
    }

    setHitlSubmitting(true);
    try {
      const payload = {
        human_approved: true, // true just signals human processed it
        approved_by: "specialist_user",
        notes: hitlNotes
      };

      if (action === 'approve') {
        await api.approveClaim(id, payload);
      } else {
        await api.rejectClaim(id, payload);
      }
      
      setHitlNotes("");
      await fetchClaim();
    } catch (err) {
      console.error(err);
      alert("Failed to submit HITL decision.");
    } finally {
      setHitlSubmitting(false);
    }
  };

  const handleSubmitComment = async () => {
    if (!newComment.trim()) return;

    setCommentSubmitting(true);
    try {
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      await api.createComment({
        claim_id: id,
        user_id: user.id,
        content: newComment
      });
      setNewComment("");
      await fetchComments();
    } catch (err) {
      console.error("Failed to submit comment", err);
      alert("Failed to submit comment.");
    } finally {
      setCommentSubmitting(false);
    }
  };

  const handleDeleteComment = async (commentId) => {
    if (!confirm("Are you sure you want to delete this comment?")) return;

    try {
      await api.deleteComment(commentId);
      await fetchComments();
    } catch (err) {
      console.error("Failed to delete comment", err);
      alert("Failed to delete comment.");
    }
  };

  if (loading) return <div style={{ padding: '24px' }}>Loading claim details...</div>;
  if (!claim) return <div style={{ padding: '24px' }}>Claim not found.</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <button 
          onClick={() => navigate('/claims')} 
          style={{ 
            padding: '8px 12px', 
            borderRadius: '6px', 
            background: '#ffffff', 
            border: '1px solid #e5e7eb', 
            color: '#64748b', 
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center'
          }}
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>Claim Details</h1>
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>ID: {claim.id}</p>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '12px', alignItems: 'center' }}>
          <span style={{ 
            padding: '4px 12px',
            borderRadius: '4px',
            background: claim.status === 'HUMAN_REVIEW_REQUIRED' ? '#fef3c7' : '#e0f2fe', 
            color: claim.status === 'HUMAN_REVIEW_REQUIRED' ? '#d97706' : '#0284c7',
            border: claim.status === 'HUMAN_REVIEW_REQUIRED' ? '1px solid #fde68a' : '1px solid #bae6fd',
            fontSize: '0.75rem',
            fontWeight: 600,
            textTransform: 'capitalize'
          }}>
            {claim.status.replace(/_/g, ' ')}
          </span>
          {pipelineStatus ? (
            <span style={{
              padding: '4px 12px',
              borderRadius: '4px',
              background: pipelineStatus === 'FAILED' ? '#fef2f2' : 
                          pipelineStatus === 'COMPLETED' ? '#f0fdf4' : '#e0f2fe',
              color: pipelineStatus === 'FAILED' ? '#dc2626' : 
                     pipelineStatus === 'COMPLETED' ? '#059669' : '#0284c7',
              border: pipelineStatus === 'FAILED' ? '1px solid #fecaca' : 
                     pipelineStatus === 'COMPLETED' ? '1px solid #bbf7d0' : '1px solid #bae6fd',
              fontSize: '0.75rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}>
              {pipelineStatus !== 'COMPLETED' && pipelineStatus !== 'FAILED' && (
                <Loader size={12} style={{ animation: 'spin 1s linear infinite' }} />
              )}
              Pipeline: {pipelineStatus}
            </span>
          ) : claim.status === 'RECEIVED' ? (
            <button 
              onClick={handleRunPipeline}
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
              <Play size={16} /> Run Pipeline
            </button>
          ) : null}
        </div>
      </div>

      {/* HITL Override Panel */}
      {claim.status === 'HUMAN_REVIEW_REQUIRED' && (
        <div style={{ padding: '24px', borderRadius: '12px', background: '#ffffff', border: '1px solid #e5e7eb', borderLeft: '4px solid #d97706', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'start', gap: '16px' }}>
            <ShieldAlert size={24} color="#d97706" style={{ marginTop: '4px' }} />
            <div style={{ flex: 1 }}>
              <h3 style={{ color: '#0f172a', marginBottom: '8px', fontSize: '1.125rem', fontWeight: 600 }}>Human Review Required</h3>
              <p style={{ color: '#64748b', marginBottom: '16px', lineHeight: 1.6 }}>
                Reason: {claim.human_review_reason || "The AI pipeline flagged this claim for specialist override."}
              </p>
              <textarea 
                value={hitlNotes}
                onChange={(e) => setHitlNotes(e.target.value)}
                placeholder="Enter specialist notes, justification, or correction instructions..."
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  borderRadius: '6px',
                  border: '1px solid #d1d5db',
                  background: '#ffffff',
                  color: '#1f2937',
                  marginBottom: '16px',
                  minHeight: '80px',
                  fontFamily: 'system-ui, -apple-system, sans-serif',
                  fontSize: '0.875rem',
                  boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
                }}
                disabled={hitlSubmitting}
              />
              <div style={{ display: 'flex', gap: '12px' }}>
                <button 
                  onClick={() => handleHitlAction('approve')}
                  disabled={hitlSubmitting}
                  style={{
                    padding: '10px 20px',
                    borderRadius: '6px',
                    background: '#059669',
                    color: 'white',
                    border: 'none',
                    fontWeight: 600,
                    cursor: 'pointer',
                    fontSize: '0.875rem',
                    boxShadow: '0 4px 6px rgba(5, 150, 105, 0.2)'
                  }}
                >
                  Approve as Correct
                </button>
                <button 
                  onClick={() => handleHitlAction('reject')}
                  disabled={hitlSubmitting}
                  style={{
                    padding: '10px 20px',
                    borderRadius: '6px',
                    background: '#dc2626',
                    color: 'white',
                    border: 'none',
                    fontWeight: 600,
                    cursor: 'pointer',
                    fontSize: '0.875rem',
                    boxShadow: '0 4px 6px rgba(220, 38, 38, 0.2)'
                  }}
                >
                  Reject & Deny
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Left Column: Basic Info */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div style={{ padding: '24px', borderRadius: '12px', background: '#ffffff', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)' }}>
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.125rem', fontWeight: 600, color: '#0f172a' }}>
              <User size={18} color="#0284c7"/> Patient Information
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '0.875rem', color: '#64748b', marginBottom: '4px' }}>Name</div>
                <div style={{ fontWeight: 500, color: '#0f172a' }}>{claim.patient_name}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.875rem', color: '#64748b', marginBottom: '4px' }}>DOB</div>
                <div style={{ fontWeight: 500, color: '#0f172a' }}>{claim.patient_dob}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.875rem', color: '#64748b', marginBottom: '4px' }}>Date of Service</div>
                <div style={{ fontWeight: 500, color: '#0f172a' }}>{claim.date_of_service}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '24px', borderRadius: '12px', background: '#ffffff', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)' }}>
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.125rem', fontWeight: 600, color: '#0f172a' }}>
              <FileText size={18} color="#0284c7"/> Billing Details
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#64748b' }}>Payer</span>
                <span style={{ fontWeight: 500, color: '#0f172a' }}>{claim.payer_name}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#64748b' }}>Payer ID</span>
                <span style={{ fontWeight: 500, color: '#0f172a' }}>{claim.payer_id}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#64748b' }}>Facility Type</span>
                <span style={{ fontWeight: 500, color: '#0f172a' }}>{claim.facility_type}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', paddingTop: '12px', borderTop: '1px dashed #e5e7eb' }}>
                <span style={{ fontWeight: 600, color: '#0f172a' }}>Total Billed</span>
                <span style={{ fontWeight: 600, color: '#0284c7' }}>${claim.billed_amount?.toFixed(2)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: AI Analysis */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div style={{ padding: '24px', borderRadius: '12px', background: '#ffffff', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)' }}>
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.125rem', fontWeight: 600, color: '#0f172a' }}>
              <CheckCircle size={18} color="#059669"/> Code Audit Results
            </h3>
            {claim.audit_findings ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: '#64748b' }}>Confidence Score</span>
                  <span style={{ fontWeight: 600, color: claim.audit_confidence > 0.8 ? '#059669' : '#d97706' }}>
                    {(claim.audit_confidence * 100).toFixed(0)}%
                  </span>
                </div>
                {claim.audit_findings.length === 0 ? (
                  <div style={{ padding: '12px', background: '#f0fdf4', borderRadius: '6px', border: '1px solid #bbf7d0', color: '#059669' }}>
                    No coding issues detected. Clean claim.
                  </div>
                ) : (
                  claim.audit_findings.map((f, i) => (
                    <div key={i} style={{ padding: '12px', background: '#fef2f2', borderRadius: '6px', border: '1px solid #fecaca' }}>
                      <div style={{ fontWeight: 600, color: '#dc2626' }}>{f.issue_type}: Code {f.code}</div>
                      <div style={{ fontSize: '0.875rem', marginTop: '4px', color: '#0f172a' }}>{f.description}</div>
                      <div style={{ fontSize: '0.875rem', marginTop: '8px', fontStyle: 'italic', color: '#64748b' }}>Suggested: {f.suggested_correction}</div>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div style={{ color: '#9ca3af' }}>Audit not yet performed.</div>
            )}
          </div>

          <div style={{ padding: '24px', borderRadius: '12px', background: '#ffffff', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)' }}>
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.125rem', fontWeight: 600, color: '#0f172a' }}>
              <AlertTriangle size={18} color={claim.denial_risk_score > 70 ? "#dc2626" : "#d97706"}/> Denial Prediction
            </h3>
            {claim.denial_risk_score !== null ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: '#64748b' }}>Risk Score</span>
                  <span style={{ fontWeight: 600, color: claim.denial_risk_score > 70 ? '#dc2626' : '#d97706' }}>
                    {claim.denial_risk_score}/100
                  </span>
                </div>
                {claim.risk_factors && claim.risk_factors.length > 0 ? (
                  claim.risk_factors.map((r, i) => (
                    <div key={i} style={{ fontSize: '0.875rem', padding: '8px 0', borderBottom: '1px dashed #e5e7eb' }}>
                      <span style={{ fontWeight: 500, color: '#0f172a' }}>{r.factor}</span>
                      <p style={{ color: '#64748b', marginTop: '4px' }}>{r.description}</p>
                    </div>
                  ))
                ) : (
                  <div style={{ color: '#64748b' }}>No significant risk factors identified.</div>
                )}
              </div>
            ) : (
              <div style={{ color: '#9ca3af' }}>Prediction not yet performed.</div>
            )}
          </div>
        </div>
      </div>

      {/* Comments Section */}
      <div style={{ padding: '24px', borderRadius: '12px', background: '#ffffff', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)' }}>
        <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.125rem', fontWeight: 600, color: '#0f172a' }}>
          <MessageSquare size={18} color="#0284c7" />
          Comments ({comments.length})
        </h3>

        {/* Add Comment */}
        <div style={{ marginBottom: '24px', display: 'flex', gap: '12px' }}>
          <textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Add a comment..."
            style={{
              flex: 1,
              padding: '12px 16px',
              borderRadius: '6px',
              border: '1px solid #d1d5db',
              background: '#ffffff',
              color: '#1f2937',
              minHeight: '60px',
              resize: 'vertical',
              fontSize: '0.875rem',
              boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
            }}
            disabled={commentSubmitting}
          />
          <button
            onClick={handleSubmitComment}
            disabled={commentSubmitting || !newComment.trim()}
            style={{
              padding: '0 20px',
              borderRadius: '6px',
              background: '#0284c7',
              color: 'white',
              border: 'none',
              fontWeight: 600,
              cursor: 'pointer',
              fontSize: '0.875rem',
              boxShadow: '0 4px 6px rgba(2, 132, 199, 0.2)'
            }}
          >
            {commentSubmitting ? '...' : <Send size={16} />}
          </button>
        </div>

        {/* Comments List */}
        {comments.length === 0 ? (
          <div style={{ color: '#64748b', fontStyle: 'italic' }}>
            No comments yet. Be the first to comment!
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {comments.map((comment) => (
              <div key={comment.id} style={{ 
                padding: '16px', 
                background: '#f8fafc', 
                borderRadius: '8px',
                border: '1px solid #e5e7eb'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ 
                      width: '32px', 
                      height: '32px', 
                      borderRadius: '50%', 
                      background: '#0284c7', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      color: 'white',
                      fontWeight: 600,
                      fontSize: '0.875rem'
                    }}>
                      {(comment.user_full_name || comment.user_email || 'U').charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div style={{ fontWeight: 500, fontSize: '0.875rem', color: '#0f172a' }}>
                        {comment.user_full_name || comment.user_email || 'Unknown User'}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                        {new Date(comment.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteComment(comment.id)}
                    style={{ 
                      background: 'transparent', 
                      border: 'none', 
                      color: '#64748b', 
                      cursor: 'pointer',
                      padding: '4px',
                      display: 'flex',
                      alignItems: 'center'
                    }}
                    title="Delete comment"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                <div style={{ color: '#0f172a', lineHeight: '1.5' }}>
                  {comment.content}
                </div>
                
                {/* Replies */}
                {comment.replies && comment.replies.length > 0 && (
                  <div style={{ marginTop: '12px', marginLeft: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {comment.replies.map((reply) => (
                      <div key={reply.id} style={{ 
                        padding: '12px', 
                        background: '#ffffff', 
                        borderRadius: '6px',
                        border: '1px solid #e5e7eb'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <div style={{ 
                              width: '24px', 
                              height: '24px', 
                              borderRadius: '50%', 
                              background: '#0284c7', 
                              display: 'flex', 
                              alignItems: 'center', 
                              justifyContent: 'center',
                              color: 'white',
                              fontWeight: 600,
                              fontSize: '0.75rem'
                            }}>
                              {(reply.user_full_name || reply.user_email || 'U').charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <div style={{ fontWeight: 500, fontSize: '0.8rem', color: '#0f172a' }}>
                                {reply.user_full_name || reply.user_email || 'Unknown User'}
                              </div>
                              <div style={{ fontSize: '0.7rem', color: '#64748b' }}>
                                {new Date(reply.created_at).toLocaleString()}
                              </div>
                            </div>
                          </div>
                          <button
                            onClick={() => handleDeleteComment(reply.id)}
                            style={{ 
                              background: 'transparent', 
                              border: 'none', 
                              color: '#64748b', 
                              cursor: 'pointer',
                              padding: '2px',
                              display: 'flex',
                              alignItems: 'center'
                            }}
                            title="Delete reply"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                        <div style={{ color: '#0f172a', fontSize: '0.875rem', lineHeight: '1.5' }}>
                          {reply.content}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
