import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Activity, AlertTriangle, FileCheck, Clock } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function DashboardHome() {
  const [summary, setSummary] = useState(null);
  const [volume, setVolume] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [sumRes, volRes] = await Promise.all([
          api.getSummary(),
          api.getVolume()
        ]);
        setSummary(sumRes.data.data);
        // Reverse volume to chronological order for charts
        setVolume((volRes.data.data || []).reverse());
      } catch (err) {
        console.error("Failed to fetch dashboard data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div style={{ padding: '24px' }}>Loading dashboard...</div>;

  const stats = [
    { label: "Claims Today", value: summary?.total_claims_today || 0, icon: Activity, color: "#0284c7", bg: "#e0f2fe" },
    { label: "Denial Rate", value: `${summary?.denial_rate_pct || 0}%`, icon: AlertTriangle, color: "#dc2626", bg: "#fef2f2" },
    { label: "Avg Risk Score", value: summary?.avg_risk_score || 0, icon: FileCheck, color: "#d97706", bg: "#fef3c7" },
    { label: "Pending Appeals", value: summary?.appeals_pending || 0, icon: Clock, color: "#0891b2", bg: "#e0f2fe" }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div>
        <h1 style={{ fontSize: '1.875rem', fontWeight: 700, color: '#0f172a', marginBottom: '8px' }}>Dashboard Overview</h1>
        <p style={{ color: '#64748b', fontSize: '1rem' }}>Real-time metrics and pipeline volume.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '24px' }}>
        {stats.map((stat, i) => (
          <div key={i} style={{ 
            padding: '24px', 
            borderRadius: '12px', 
            background: '#ffffff', 
            border: '1px solid #e5e7eb',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
            display: 'flex',
            alignItems: 'center',
            gap: '16px'
          }}>
            <div style={{ background: stat.bg, padding: '16px', borderRadius: '12px', color: stat.color }}>
              <stat.icon size={24} />
            </div>
            <div>
              <div style={{ fontSize: '0.875rem', color: '#64748b', fontWeight: 500 }}>{stat.label}</div>
              <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#0f172a' }}>{stat.value}</div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ 
        padding: '24px', 
        borderRadius: '12px', 
        background: '#ffffff', 
        border: '1px solid #e5e7eb',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        height: '400px', 
        display: 'flex', 
        flexDirection: 'column' 
      }}>
        <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#0f172a', marginBottom: '24px' }}>Claim Volume (30 Days)</h3>
        <div style={{ flex: 1 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={volume} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0284c7" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#0284c7" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorDenied" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#dc2626" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#dc2626" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
              <XAxis dataKey="date" stroke="#64748b" tick={{ fill: '#64748b', fontSize: 12 }} tickLine={false} axisLine={false} />
              <YAxis stroke="#64748b" tick={{ fill: '#64748b', fontSize: 12 }} tickLine={false} axisLine={false} />
              <Tooltip 
                contentStyle={{ background: '#ffffff', border: '1px solid #e5e7eb', borderRadius: '8px', color: '#0f172a', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' }}
                itemStyle={{ color: '#0f172a' }}
              />
              <Area type="monotone" dataKey="total" stroke="#0284c7" fillOpacity={1} fill="url(#colorTotal)" name="Total Claims" />
              <Area type="monotone" dataKey="denied" stroke="#dc2626" fillOpacity={1} fill="url(#colorDenied)" name="Denied Claims" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
