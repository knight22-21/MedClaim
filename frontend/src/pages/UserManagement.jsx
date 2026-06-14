import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Users, Plus, Mail, Shield, Edit, Trash2, Search, Filter } from 'lucide-react';

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  
  const [formData, setFormData] = useState({
    email: '',
    full_name: '',
    role: 'viewer',
    department: '',
    phone: '',
  });

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await api.getUsers(roleFilter, 100, 0);
      setUsers(res.data.data || []);
    } catch (err) {
      console.error('Failed to fetch users:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [roleFilter]);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await api.createUser(formData);
      setShowModal(false);
      setFormData({ email: '', full_name: '', role: 'viewer', department: '', phone: '' });
      fetchUsers();
    } catch (err) {
      console.error('Failed to create user:', err);
      alert('Failed to create user');
    }
  };

  const handleUpdateUser = async (e) => {
    e.preventDefault();
    try {
      await api.updateUser(editingUser.id, formData);
      setShowModal(false);
      setEditingUser(null);
      setFormData({ email: '', full_name: '', role: 'viewer', department: '', phone: '' });
      fetchUsers();
    } catch (err) {
      console.error('Failed to update user:', err);
      alert('Failed to update user');
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!confirm('Are you sure you want to delete this user?')) return;
    try {
      await api.deleteUser(userId);
      fetchUsers();
    } catch (err) {
      console.error('Failed to delete user:', err);
      alert('Failed to delete user');
    }
  };

  const handleInviteUser = async (email) => {
    try {
      await api.inviteUser({ email });
      alert('Invitation sent successfully');
    } catch (err) {
      console.error('Failed to invite user:', err);
      alert('Failed to send invitation');
    }
  };

  const openModal = (user = null) => {
    if (user) {
      setEditingUser(user);
      setFormData({
        email: user.email,
        full_name: user.full_name,
        role: user.role,
        department: user.department || '',
        phone: user.phone || '',
      });
    } else {
      setEditingUser(null);
      setFormData({ email: '', full_name: '', role: 'viewer', department: '', phone: '' });
    }
    setShowModal(true);
  };

  const filteredUsers = users.filter(user =>
    user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (user.full_name && user.full_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  if (loading) return <div style={{ padding: '24px' }}>Loading users...</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 700, color: '#0f172a', marginBottom: '8px' }}>User Management</h1>
          <p style={{ color: '#64748b', fontSize: '1rem' }}>Manage users and their roles</p>
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
          <Plus size={16} /> Add User
        </button>
      </div>

      {/* Filters */}
      <div style={{ padding: '16px', borderRadius: '12px', background: '#ffffff', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)', display: 'flex', gap: '16px', alignItems: 'center' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af' }} />
          <input
            type="text"
            placeholder="Search users..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 12px 10px 40px',
              borderRadius: '6px',
              border: '1px solid #d1d5db',
              background: '#ffffff',
              color: '#1f2937',
              fontSize: '0.875rem',
              boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
            }}
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Filter size={16} color="#64748b" />
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            style={{
              padding: '10px 12px',
              borderRadius: '6px',
              border: '1px solid #d1d5db',
              background: '#ffffff',
              color: '#1f2937',
              fontSize: '0.875rem',
              boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
            }}
          >
            <option value="">All Roles</option>
            <option value="admin">Admin</option>
            <option value="billing_specialist">Billing Specialist</option>
            <option value="viewer">Viewer</option>
          </select>
        </div>
      </div>

      {/* Users Table */}
      <div style={{ borderRadius: '12px', background: '#ffffff', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #e5e7eb', background: '#f8fafc' }}>
              <th style={{ padding: '16px', textAlign: 'left', color: '#64748b', fontSize: '0.875rem', fontWeight: 600 }}>User</th>
              <th style={{ padding: '16px', textAlign: 'left', color: '#64748b', fontSize: '0.875rem', fontWeight: 600 }}>Role</th>
              <th style={{ padding: '16px', textAlign: 'left', color: '#64748b', fontSize: '0.875rem', fontWeight: 600 }}>Department</th>
              <th style={{ padding: '16px', textAlign: 'left', color: '#64748b', fontSize: '0.875rem', fontWeight: 600 }}>Status</th>
              <th style={{ padding: '16px', textAlign: 'right', color: '#64748b', fontSize: '0.875rem', fontWeight: 600 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>
                  No users found
                </td>
              </tr>
            ) : (
              filteredUsers.map((user) => (
                <tr key={user.id} style={{ borderBottom: '1px solid #e5e7eb' }}>
                  <td style={{ padding: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{
                        width: '40px',
                        height: '40px',
                        borderRadius: '50%',
                        background: '#0284c7',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'white',
                        fontWeight: 600,
                      }}>
                        {(user.full_name || user.email || 'U').charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div style={{ fontWeight: 500, color: '#0f172a' }}>{user.full_name || 'Unknown'}</div>
                        <div style={{ fontSize: '0.875rem', color: '#64748b' }}>{user.email}</div>
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: '16px' }}>
                    <span style={{
                      padding: '4px 12px',
                      borderRadius: '4px',
                      background: user.role === 'admin' ? '#e0f2fe' :
                                user.role === 'billing_specialist' ? '#f0fdf4' :
                                '#f1f5f9',
                      color: user.role === 'admin' ? '#0284c7' :
                             user.role === 'billing_specialist' ? '#059669' :
                             '#64748b',
                      border: user.role === 'admin' ? '1px solid #bae6fd' :
                             user.role === 'billing_specialist' ? '1px solid #bbf7d0' :
                             '1px solid #e2e8f0',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      textTransform: 'capitalize'
                    }}>
                      {user.role.replace('_', ' ')}
                    </span>
                  </td>
                  <td style={{ padding: '16px', color: '#0f172a' }}>{user.department || '-'}</td>
                  <td style={{ padding: '16px' }}>
                    <span style={{ 
                      padding: '4px 12px',
                      borderRadius: '4px',
                      background: '#f0fdf4',
                      color: '#059669',
                      border: '1px solid #bbf7d0',
                      fontSize: '0.75rem',
                      fontWeight: 600
                    }}>
                      Active
                    </span>
                  </td>
                  <td style={{ padding: '16px', textAlign: 'right' }}>
                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                      <button
                        onClick={() => handleInviteUser(user.email)}
                        style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }}
                        title="Send invitation"
                      >
                        <Mail size={16} />
                      </button>
                      <button
                        onClick={() => openModal(user)}
                        style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }}
                        title="Edit user"
                      >
                        <Edit size={16} />
                      </button>
                      <button
                        onClick={() => handleDeleteUser(user.id)}
                        style={{ background: 'transparent', border: 'none', color: '#dc2626', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }}
                        title="Delete user"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
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
            <h2 style={{ marginBottom: '24px', fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>{editingUser ? 'Edit User' : 'Add User'}</h2>
            <form onSubmit={editingUser ? handleUpdateUser : handleCreateUser} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', fontWeight: 600, color: '#374151' }}>Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
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
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', fontWeight: 600, color: '#374151' }}>Full Name</label>
                <input
                  type="text"
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
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
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', fontWeight: 600, color: '#374151' }}>Role</label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
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
                >
                  <option value="viewer">Viewer</option>
                  <option value="billing_specialist">Billing Specialist</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', fontWeight: 600, color: '#374151' }}>Department</label>
                <input
                  type="text"
                  value={formData.department}
                  onChange={(e) => setFormData({ ...formData, department: e.target.value })}
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
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', fontWeight: 600, color: '#374151' }}>Phone</label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
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
                  {editingUser ? 'Update' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowModal(false); setEditingUser(null); }}
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
