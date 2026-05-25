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
    { label: "Claims Today", value: summary?.total_claims_today || 0, icon: Activity, color: "var(--primary)" },
    { label: "Denial Rate", value: `${summary?.denial_rate_pct || 0}%`, icon: AlertTriangle, color: "var(--danger)" },
    { label: "Avg Risk Score", value: summary?.avg_risk_score || 0, icon: FileCheck, color: "var(--warning)" },
    { label: "Pending Appeals", value: summary?.appeals_pending || 0, icon: Clock, color: "var(--info)" }
  ];

  return (
    <div className="flex-col gap-6 animate-fade-in">
      <div>
        <h1>Dashboard Overview</h1>
        <p style={{ color: 'var(--text-secondary)' }}>Real-time metrics and pipeline volume.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '24px' }}>
        {stats.map((stat, i) => (
          <div key={i} className="glass-card flex items-center gap-4">
            <div style={{ background: `${stat.color}20`, padding: '16px', borderRadius: '12px', color: stat.color }}>
              <stat.icon size={24} />
            </div>
            <div>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{stat.label}</div>
              <div style={{ fontSize: '1.75rem', fontWeight: 'bold' }}>{stat.value}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="glass-card" style={{ height: '400px', display: 'flex', flexDirection: 'column' }}>
        <h3 style={{ marginBottom: '24px' }}>Claim Volume (30 Days)</h3>
        <div style={{ flex: 1 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={volume} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="var(--primary)" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorDenied" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--danger)" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="var(--danger)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-glass)" vertical={false} />
              <XAxis dataKey="date" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} tickLine={false} axisLine={false} />
              <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} tickLine={false} axisLine={false} />
              <Tooltip 
                contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border-glass)', borderRadius: '8px', color: 'var(--text-primary)' }}
                itemStyle={{ color: 'var(--text-primary)' }}
              />
              <Area type="monotone" dataKey="total" stroke="var(--primary)" fillOpacity={1} fill="url(#colorTotal)" name="Total Claims" />
              <Area type="monotone" dataKey="denied" stroke="var(--danger)" fillOpacity={1} fill="url(#colorDenied)" name="Denied Claims" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
