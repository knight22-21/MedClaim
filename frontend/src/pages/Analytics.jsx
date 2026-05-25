import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { AlertCircle } from 'lucide-react';

export default function Analytics() {
  const [denials, setDenials] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await api.getDenialsByPayer();
        setDenials(res.data.data || []);
      } catch (err) {
        console.error("Failed to fetch analytics", err);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  return (
    <div className="flex-col gap-6 animate-fade-in">
      <div>
        <h1>Advanced Analytics</h1>
        <p style={{ color: 'var(--text-secondary)' }}>Deep dive into denial patterns and payer behavior.</p>
      </div>

      <div className="glass-card" style={{ height: '450px', display: 'flex', flexDirection: 'column' }}>
        <div className="flex items-center gap-2" style={{ marginBottom: '24px' }}>
          <AlertCircle size={20} color="var(--danger)" />
          <h3>Denial Volume by Payer</h3>
        </div>
        
        {loading ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading charts...</div>
        ) : denials.length === 0 ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>No denial data available.</div>
        ) : (
          <div style={{ flex: 1 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={denials} margin={{ top: 20, right: 30, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-glass)" vertical={false} />
                <XAxis dataKey="payer_name" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} tickLine={false} axisLine={false} />
                <Tooltip 
                  cursor={{ fill: 'var(--bg-surface-hover)' }}
                  contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border-glass)', borderRadius: '8px', color: 'var(--text-primary)' }}
                />
                <Bar dataKey="denied_claims" fill="var(--danger)" name="Denied Claims" radius={[4, 4, 0, 0]} barSize={40} />
                <Bar dataKey="total_claims" fill="var(--primary)" name="Total Claims" radius={[4, 4, 0, 0]} barSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
      
      <div className="glass-card">
        <h3>Denial Rate Leaderboard</h3>
        <table style={{ width: '100%', marginTop: '16px', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-glass)', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              <th style={{ padding: '12px 16px', fontWeight: 500 }}>Payer</th>
              <th style={{ padding: '12px 16px', fontWeight: 500 }}>Total Claims</th>
              <th style={{ padding: '12px 16px', fontWeight: 500 }}>Denied Claims</th>
              <th style={{ padding: '12px 16px', fontWeight: 500 }}>Denial Rate</th>
            </tr>
          </thead>
          <tbody>
            {denials.map(d => (
              <tr key={d.payer_name} style={{ borderBottom: '1px solid var(--border-glass)' }}>
                <td style={{ padding: '12px 16px', fontWeight: 500 }}>{d.payer_name}</td>
                <td style={{ padding: '12px 16px' }}>{d.total_claims}</td>
                <td style={{ padding: '12px 16px' }}>{d.denied_claims}</td>
                <td style={{ padding: '12px 16px' }}>
                  <span className="badge" style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)' }}>
                    {d.denial_rate_pct}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
