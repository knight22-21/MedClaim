import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, FileText, BarChart3, Mic, Settings, LogOut, Users, Workflow } from 'lucide-react';

import DashboardHome from './pages/DashboardHome';
import ClaimsList from './pages/ClaimsList';
import Analytics from './pages/Analytics';
import VoiceQuery from './pages/VoiceQuery';
import ClaimDetail from './pages/ClaimDetail';
import Login from './pages/Login';
import Landing from './pages/Landing';
import UserManagement from './pages/UserManagement';
import WorkflowConfig from './pages/WorkflowConfig';
import ApiDocumentation from './pages/ApiDocumentation';
import ProtectedRoute from './components/ProtectedRoute';
import { api } from './api/client';

const Sidebar = () => {
  const location = useLocation();
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/claims', label: 'Claims', icon: FileText },
    { path: '/analytics', label: 'Analytics', icon: BarChart3 },
    { path: '/voice', label: 'Voice AI', icon: Mic },
  ];

  if (user.role === 'admin') {
    navItems.push({ path: '/admin/users', label: 'Users', icon: Users });
    navItems.push({ path: '/admin/workflows', label: 'Workflows', icon: Workflow });
  }

  return (
    <div style={{ width: '250px', background: '#ffffff', borderRight: '1px solid #e5e7eb', padding: '24px', boxShadow: '1px 0 3px rgba(0, 0, 0, 0.05)' }}>
      <div style={{ marginBottom: '40px', fontWeight: 'bold', fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '12px', color: '#0f172a' }}>
        <div style={{ width: '32px', height: '32px', background: '#0284c7', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 700, fontSize: '1rem' }}>
          M
        </div>
        MedClaim
      </div>
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '12px 16px',
              borderRadius: '6px',
              color: location.pathname === item.path ? '#0284c7' : '#64748b',
              background: location.pathname === item.path ? '#e0f2fe' : 'transparent',
              textDecoration: 'none',
              transition: 'all 0.2s',
              fontWeight: location.pathname === item.path ? 600 : 500
            }}
          >
            <item.icon size={20} />
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
};

const Header = () => {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await api.logout();
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      navigate('/login');
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  return (
    <header style={{ height: '70px', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', padding: '0 24px', background: '#ffffff', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ padding: '6px 12px', borderRadius: '6px', background: '#f0fdf4', color: '#059669', fontSize: '0.75rem', fontWeight: 600, border: '1px solid #bbf7d0' }}>
          System Operational
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: '#64748b', fontSize: '0.875rem' }}>
          <span style={{ fontWeight: 500, color: '#0f172a' }}>{user.full_name || user.email}</span>
          <span style={{ padding: '4px 10px', borderRadius: '4px', background: '#e0f2fe', color: '#0284c7', fontSize: '0.75rem', fontWeight: 600, border: '1px solid #bae6fd', textTransform: 'capitalize' }}>
            {user.role}
          </span>
        </div>
        <button 
          onClick={handleLogout}
          style={{ background: 'transparent', border: '1px solid #e5e7eb', color: '#64748b', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', borderRadius: '6px', fontSize: '0.875rem', fontWeight: 500, transition: 'all 0.2s' }}
          title="Logout"
          onMouseOver={(e) => e.target.style.background = '#f8fafc'}
          onMouseOut={(e) => e.target.style.background = 'transparent'}
        >
          <LogOut size={16} />
          Logout
        </button>
      </div>
    </header>
  );
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        
        {/* Protected Routes */}
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <div className="app-container">
              <Sidebar />
              <div className="main-content">
                <Header />
                <main style={{ padding: '32px' }}>
                  <DashboardHome />
                </main>
              </div>
            </div>
          </ProtectedRoute>
        } />
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <div className="app-container">
              <Sidebar />
              <div className="main-content">
                <Header />
                <main style={{ padding: '32px' }}>
                  <DashboardHome />
                </main>
              </div>
            </div>
          </ProtectedRoute>
        } />
        <Route path="/claims" element={
          <ProtectedRoute>
            <div className="app-container">
              <Sidebar />
              <div className="main-content">
                <Header />
                <main style={{ padding: '32px' }}>
                  <ClaimsList />
                </main>
              </div>
            </div>
          </ProtectedRoute>
        } />
        <Route path="/claims/:id" element={
          <ProtectedRoute>
            <div className="app-container">
              <Sidebar />
              <div className="main-content">
                <Header />
                <main style={{ padding: '32px' }}>
                  <ClaimDetail />
                </main>
              </div>
            </div>
          </ProtectedRoute>
        } />
        <Route path="/analytics" element={
          <ProtectedRoute>
            <div className="app-container">
              <Sidebar />
              <div className="main-content">
                <Header />
                <main style={{ padding: '32px' }}>
                  <Analytics />
                </main>
              </div>
            </div>
          </ProtectedRoute>
        } />
        <Route path="/voice" element={
          <ProtectedRoute>
            <div className="app-container">
              <Sidebar />
              <div className="main-content">
                <Header />
                <main style={{ padding: '32px' }}>
                  <VoiceQuery />
                </main>
              </div>
            </div>
          </ProtectedRoute>
        } />
        <Route path="/admin/users" element={
          <ProtectedRoute>
            <div className="app-container">
              <Sidebar />
              <div className="main-content">
                <Header />
                <main style={{ padding: '32px' }}>
                  <UserManagement />
                </main>
              </div>
            </div>
          </ProtectedRoute>
        } />
        <Route path="/admin/workflows" element={
          <ProtectedRoute>
            <div className="app-container">
              <Sidebar />
              <div className="main-content">
                <Header />
                <main style={{ padding: '32px' }}>
                  <WorkflowConfig />
                </main>
              </div>
            </div>
          </ProtectedRoute>
        } />
        <Route path="/api-docs" element={<ApiDocumentation />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
