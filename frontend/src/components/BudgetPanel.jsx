import React from 'react';
import { DollarSign, AlertCircle, PieChart, CheckCircle2 } from 'lucide-react';

export default function BudgetPanel({
  budgetTotals = {},
  members = [],
  conflicts = [],
  currencySymbol = '€',
  currency = 'EUR'
}) {
  const formatCurrency = (cents) => {
    const val = Number(cents || 0) / 100;
    if (currencySymbol === '¥' || currencySymbol === '₩') {
      return `${currencySymbol}${Math.round(val).toLocaleString()}`;
    }
    return `${currencySymbol}${val.toFixed(2)}`;
  };

  const budgetBreaches = conflicts.filter(c => c.type === 'budgetBreach');
  const totalCentsSum = Object.values(budgetTotals).reduce((a, b) => a + Number(b), 0);

  return (
    <div style={{
      background: '#FFFFFF',
      borderTop: '1px solid var(--border)',
      padding: '16px 24px',
      boxShadow: '0 -2px 10px rgba(0,0,0,0.02)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ background: '#DCFCE7', color: '#166534', padding: '6px', borderRadius: '8px' }}>
            <DollarSign size={18} />
          </div>
          <div>
            <span style={{ fontWeight: 800, fontSize: '15px' }}>Live Group Logistics & Budget Engine</span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block' }}>
              Hamilton-Hare Largest Remainder split (guarantees exact sum with zero cent drift).
            </span>
          </div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
            Trip Total
          </span>
          <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-main)' }}>
            {formatCurrency(totalCentsSum)}
          </div>
        </div>
      </div>

      {/* Budget Breach Warning */}
      {budgetBreaches.length > 0 && (
        <div style={{
          background: '#FEF2F2',
          border: '1px solid #FCA5A5',
          borderRadius: '8px',
          padding: '8px 12px',
          marginBottom: '12px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: '#991B1B',
          fontSize: '12px',
          fontWeight: 600
        }}>
          <AlertCircle size={16} />
          <span>
            Budget ceiling exceeded for {budgetBreaches.length} participant(s)! Consider adjusting expensive venues.
          </span>
        </div>
      )}

      {/* Participants Budget Rail */}
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.max(1, members.length)}, minmax(180px, 1fr))`, gap: '14px', overflowX: 'auto' }}>
        {members.map(m => {
          const totalCents = Number(budgetTotals[m.userId] || 0);
          const ceilingCents = Number(m.budgetCeiling || 150) * 100;
          const percent = Math.min(100, Math.round((totalCents / ceilingCents) * 100));
          const isOver = totalCents > ceilingCents;

          return (
            <div
              key={m.userId}
              style={{
                background: isOver ? '#FFF5F5' : '#F9FAFB',
                border: isOver ? '1px solid #F87171' : '1px solid var(--border)',
                borderRadius: '10px',
                padding: '10px 12px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontWeight: 700, fontSize: '13px' }}>{m.displayName}</span>
                <span style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  color: isOver ? '#DC2626' : '#166534'
                }}>
                  {formatCurrency(totalCents)}
                </span>
              </div>

              {/* Progress bar */}
              <div style={{ height: '6px', background: '#E5E7EB', borderRadius: '3px', overflow: 'hidden', marginBottom: '6px' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${percent}%`,
                    background: isOver ? '#EF4444' : (percent > 80 ? '#F59E0B' : '#10B981'),
                    transition: 'width 0.3s ease'
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-muted)' }}>
                <span>Ceiling: €{m.budgetCeiling}</span>
                <span>{percent}%</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
