import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, FileText, BarChart3, Mic, Settings } from 'lucide-react';

import DashboardHome from './pages/DashboardHome';
import ClaimsList from './pages/ClaimsList';
import Analytics from './pages/Analytics';
import VoiceQuery from './pages/VoiceQuery';

const Sidebar = () => {
  const location = useLocation();
  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/claims', label: 'Claims', icon: FileText },
    { path: '/analytics', label: 'Analytics', icon: BarChart3 },
    { path: '/voice', label: 'Voice AI', icon: Mic },
  ];

  return (
    <div style={{ width: '250px', background: 'var(--bg-surface)', borderRight: '1px solid var(--border-glass)', padding: '24px' }}>
      <div style={{ marginBottom: '40px', fontWeight: 'bold', fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{ width: '24px', height: '24px', background: 'var(--primary)', borderRadius: '6px' }}></div>
        MedClaim AI
      </div>
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '12px 16px',
              borderRadius: '8px',
              color: location.pathname === item.path ? 'white' : 'var(--text-secondary)',
              background: location.pathname === item.path ? 'var(--primary)' : 'transparent',
              transition: 'all 0.2s'
            }}
          >
            <item.icon size={20} />
            <span style={{ fontWeight: 500 }}>{item.label}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
};

const Header = () => {
  return (
    <header style={{ height: '70px', borderBottom: '1px solid var(--border-glass)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', padding: '0 24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div className="badge" style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--success)' }}>
          System Operational
        </div>
        <button style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}>
          <Settings size={20} />
        </button>
      </div>
    </header>
  );
};

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <Sidebar />
        <div className="main-content">
          <Header />
          <main style={{ padding: '32px' }}>
            <Routes>
              <Route path="/" element={<DashboardHome />} />
              <Route path="/claims" element={<ClaimsList />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/voice" element={<VoiceQuery />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
