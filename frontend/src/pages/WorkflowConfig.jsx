import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Workflow, Plus, Edit, Trash2, Layers, Clock, CheckCircle, XCircle } from 'lucide-react';

export default function WorkflowConfig() {
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingWorkflow, setEditingWorkflow] = useState(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [loadingWorkflow, setLoadingWorkflow] = useState(false);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    is_active: true,
  });

  const [stepForm, setStepForm] = useState({
    role: 'billing_specialist',
    step_order: 1,
    timeout_hours: 24,
  });

  const fetchWorkflows = async () => {
    setLoading(true);
    try {
      const res = await api.getWorkflows(true);
      setWorkflows(res.data.data || []);
    } catch (err) {
      console.error('Failed to fetch workflows:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const handleCreateWorkflow = async (e) => {
    e.preventDefault();
    try {
      await api.createWorkflow(formData);
      setShowModal(false);
      setFormData({ name: '', description: '', is_active: true });
      fetchWorkflows();
    } catch (err) {
      console.error('Failed to create workflow:', err);
      alert('Failed to create workflow');
    }
  };

  const handleUpdateWorkflow = async (e) => {
    e.preventDefault();
    try {
      await api.updateWorkflow(editingWorkflow.id, formData);
      setShowModal(false);
      setEditingWorkflow(null);
      setFormData({ name: '', description: '', is_active: true });
      fetchWorkflows();
    } catch (err) {
      console.error('Failed to update workflow:', err);
      alert('Failed to update workflow');
    }
  };

  const handleDeleteWorkflow = async (workflowId) => {
    if (!confirm('Are you sure you want to delete this workflow?')) return;
    try {
      await api.deleteWorkflow(workflowId);
      fetchWorkflows();
    } catch (err) {
      console.error('Failed to delete workflow:', err);
      alert('Failed to delete workflow');
    }
  };

  const handleAddStep = async (e) => {
    e.preventDefault();
    if (!selectedWorkflow) return;
    try {
      await api.addWorkflowStep(selectedWorkflow.id, stepForm);
      setStepForm({ role: 'billing_specialist', step_order: 1, timeout_hours: 24 });
      await fetchWorkflows();
      const updated = await api.getWorkflow(selectedWorkflow.id);
      setSelectedWorkflow(updated.data.data);
    } catch (err) {
      console.error('Failed to add step:', err);
      alert('Failed to add step');
    }
  };

  const handleDeleteStep = async (stepId) => {
    if (!confirm('Are you sure you want to delete this step?')) return;
    try {
      await api.deleteWorkflowStep(stepId);
      await fetchWorkflows();
      const updated = await api.getWorkflow(selectedWorkflow.id);
      setSelectedWorkflow(updated.data.data);
    } catch (err) {
      console.error('Failed to delete step:', err);
      alert('Failed to delete step');
    }
  };

  const openModal = (workflow = null) => {
    if (workflow) {
      setEditingWorkflow(workflow);
      setFormData({
        name: workflow.name,
        description: workflow.description || '',
        is_active: workflow.is_active,
      });
    } else {
      setEditingWorkflow(null);
      setFormData({ name: '', description: '', is_active: true });
    }
    setShowModal(true);
  };

  const handleSelectWorkflow = async (workflow) => {
    setLoadingWorkflow(true);
    setSelectedWorkflow(workflow);
    try {
      const updated = await api.getWorkflow(workflow.id);
      setSelectedWorkflow(updated.data.data);
    } catch (err) {
      console.error('Failed to fetch workflow details:', err);
    } finally {
      setLoadingWorkflow(false);
    }
  };

  if (loading) return <div style={{ padding: '24px' }}>Loading workflows...</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 700, color: '#0f172a', marginBottom: '8px' }}>Approval Workflows</h1>
          <p style={{ color: '#64748b', fontSize: '1rem' }}>Configure approval workflows for claims</p>
        </div>
        <button 
          onClick={() => openModal()}
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
          <Plus size={16} /> Create Workflow
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selectedWorkflow ? '1fr 1fr' : '1fr', gap: '24px' }}>
        {/* Workflows List */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
          {workflows.map((workflow) => (
            <div
              key={workflow.id}
              style={{ 
                cursor: 'pointer',
                padding: '24px',
                borderRadius: '12px',
                background: '#ffffff',
                border: selectedWorkflow?.id === workflow.id ? '2px solid #0284c7' : '1px solid #e5e7eb',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
                transition: 'box-shadow 0.2s'
              }}
              onClick={() => handleSelectWorkflow(workflow)}
            >
              <div style={{ display: 'flex', alignItems: 'start', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: '#0284c7', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Workflow size={20} color="white" />
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, color: '#0f172a' }}>{workflow.name}</div>
                    <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
                      {workflow.steps?.length || 0} steps
                    </div>
                  </div>
                </div>
                <span style={{ 
                  padding: '4px 12px',
                  borderRadius: '4px',
                  background: workflow.is_active ? '#f0fdf4' : '#f1f5f9',
                  color: workflow.is_active ? '#059669' : '#64748b',
                  border: workflow.is_active ? '1px solid #bbf7d0' : '1px solid #e2e8f0',
                  fontSize: '0.75rem',
                  fontWeight: 600
                }}>
                  {workflow.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              {workflow.description && (
                <p style={{ fontSize: '0.875rem', color: '#64748b', marginBottom: '16px', lineHeight: 1.5 }}>
                  {workflow.description}
                </p>
              )}
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={(e) => { e.stopPropagation(); openModal(workflow); }}
                  style={{ flex: 1, padding: '8px', borderRadius: '6px', border: '1px solid #e5e7eb', background: '#ffffff', cursor: 'pointer', color: '#64748b', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                >
                  <Edit size={14} />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteWorkflow(workflow.id); }}
                  style={{ flex: 1, padding: '8px', borderRadius: '6px', border: '1px solid #e5e7eb', background: '#ffffff', cursor: 'pointer', color: '#dc2626', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Workflow Details */}
        {selectedWorkflow && (
          <div style={{ padding: '24px', borderRadius: '12px', background: '#ffffff', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)' }}>
            {loadingWorkflow ? (
              <div style={{ textAlign: 'center', padding: '48px', color: '#64748b' }}>
                Loading workflow details...
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
                  <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.25rem', fontWeight: 600, color: '#0f172a' }}>
                    <Layers size={20} color="#0284c7" />
                    {selectedWorkflow.name}
                  </h2>
                  <span style={{ 
                    padding: '4px 12px',
                    borderRadius: '4px',
                    background: selectedWorkflow.is_active ? '#f0fdf4' : '#f1f5f9',
                    color: selectedWorkflow.is_active ? '#059669' : '#64748b',
                    border: selectedWorkflow.is_active ? '1px solid #bbf7d0' : '1px solid #e2e8f0',
                    fontSize: '0.75rem',
                    fontWeight: 600
                  }}>
                    {selectedWorkflow.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>

                {selectedWorkflow.description && (
                  <p style={{ color: '#64748b', marginBottom: '24px', lineHeight: 1.6 }}>
                    {selectedWorkflow.description}
                  </p>
                )}

                <h3 style={{ marginBottom: '16px', fontSize: '1rem', fontWeight: 600, color: '#0f172a' }}>Approval Steps</h3>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
                  {!selectedWorkflow.steps || selectedWorkflow.steps.length === 0 ? (
                    <div style={{ color: '#64748b', fontStyle: 'italic', padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                      No steps configured yet
                    </div>
                  ) : (
                    selectedWorkflow.steps
                      .sort((a, b) => a.step_order - b.step_order)
                      .map((step) => (
                        <div key={step.id} style={{ 
                          padding: '16px', 
                          background: '#f8fafc', 
                          borderRadius: '8px',
                          border: '1px solid #e5e7eb',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px'
                        }}>
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
                            {step.step_order}
                          </div>
                          <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: 500, color: '#0f172a' }}>{step.required_role.replace('_', ' ')}</div>
                            <div style={{ fontSize: '0.875rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                              <Clock size={12} />
                              {step.timeout_hours}h timeout
                            </div>
                          </div>
                          <button
                            onClick={() => handleDeleteStep(step.id)}
                            style={{ padding: '8px', borderRadius: '6px', border: '1px solid #e5e7eb', background: '#ffffff', cursor: 'pointer', color: '#dc2626', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      ))
                  )}
                </div>

                <div style={{ padding: '16px', borderRadius: '8px', background: '#f8fafc', border: '1px solid #e5e7eb' }}>
                  <h4 style={{ marginBottom: '12px', fontSize: '0.875rem', fontWeight: 600, color: '#0f172a' }}>Add New Step</h4>
                  <form onSubmit={handleAddStep} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                      <div>
                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.75rem', color: '#64748b', fontWeight: 500 }}>Step Order</label>
                        <input
                          type="number"
                          value={stepForm.step_order}
                          onChange={(e) => setStepForm({ ...stepForm, step_order: parseInt(e.target.value) })}
                          min="1"
                          style={{
                            width: '100%',
                            padding: '8px 12px',
                            borderRadius: '6px',
                            border: '1px solid #d1d5db',
                            background: '#ffffff',
                            color: '#1f2937',
                            fontSize: '0.875rem',
                            boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
                          }}
                        />
                      </div>
                      <div>
                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.75rem', color: '#64748b', fontWeight: 500 }}>Role</label>
                        <select
                          value={stepForm.role}
                          onChange={(e) => setStepForm({ ...stepForm, role: e.target.value })}
                          style={{
                            width: '100%',
                            padding: '8px 12px',
                            borderRadius: '6px',
                            border: '1px solid #d1d5db',
                            background: '#ffffff',
                            color: '#1f2937',
                            fontSize: '0.875rem',
                            boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
                          }}
                        >
                          <option value="billing_specialist">Billing Specialist</option>
                          <option value="admin">Admin</option>
                          <option value="manager">Manager</option>
                        </select>
                      </div>
                      <div>
                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.75rem', color: '#64748b', fontWeight: 500 }}>Timeout (hours)</label>
                        <input
                          type="number"
                          value={stepForm.timeout_hours}
                          onChange={(e) => setStepForm({ ...stepForm, timeout_hours: parseInt(e.target.value) })}
                          min="1"
                          style={{
                            width: '100%',
                            padding: '8px 12px',
                            borderRadius: '6px',
                            border: '1px solid #d1d5db',
                            background: '#ffffff',
                            color: '#1f2937',
                            fontSize: '0.875rem',
                            boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
                          }}
                        />
                      </div>
                    </div>
                    <button 
                      type="submit"
                      style={{
                        padding: '8px 16px',
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
                        boxShadow: '0 2px 4px rgba(2, 132, 199, 0.2)'
                      }}
                    >
                      <Plus size={14} /> Add Step
                    </button>
                  </form>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{ width: '100%', maxWidth: '500px', padding: '32px', borderRadius: '12px', background: '#ffffff', border: '1px solid #e5e7eb', boxShadow: '0 20px 25px rgba(0, 0, 0, 0.1)' }}>
            <h2 style={{ marginBottom: '24px', fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>{editingWorkflow ? 'Edit Workflow' : 'Create Workflow'}</h2>
            <form onSubmit={editingWorkflow ? handleUpdateWorkflow : handleCreateWorkflow} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', fontWeight: 600, color: '#374151' }}>Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    borderRadius: '6px',
                    border: '1px solid #d1d5db',
                    background: '#ffffff',
                    color: '#1f2937',
                    fontSize: '0.875rem',
                    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', fontWeight: 600, color: '#374151' }}>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={3}
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    borderRadius: '6px',
                    border: '1px solid #d1d5db',
                    background: '#ffffff',
                    color: '#1f2937',
                    fontSize: '0.875rem',
                    resize: 'vertical',
                    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
                  }}
                />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  id="isActive"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  style={{ width: '16px', height: '16px' }}
                />
                <label htmlFor="isActive" style={{ fontSize: '0.875rem', color: '#374151' }}>Active</label>
              </div>
              <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                <button 
                  type="submit"
                  style={{
                    flex: 1,
                    padding: '12px 16px',
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
                  {editingWorkflow ? 'Update' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowModal(false); setEditingWorkflow(null); }}
                  style={{
                    flex: 1,
                    padding: '12px 16px',
                    borderRadius: '6px',
                    background: '#ffffff',
                    color: '#64748b',
                    border: '1px solid #e5e7eb',
                    fontWeight: 600,
                    cursor: 'pointer',
                    fontSize: '0.875rem'
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
