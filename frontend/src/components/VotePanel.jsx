import React, { useState, useEffect } from 'react';
import { Vote, Clock, CheckCircle } from 'lucide-react';

export default function VotePanel({ activeVote, items = [], onCastVote, currentUserId, userRole }) {
  const [secondsLeft, setSecondsLeft] = useState(30);

  useEffect(() => {
    if (!activeVote?.closesAt) return;
    const interval = setInterval(() => {
      const remaining = Math.max(0, Math.round((activeVote.closesAt - Date.now()) / 1000));
      setSecondsLeft(remaining);
      if (remaining <= 0) clearInterval(interval);
    }, 1000);
    return () => clearInterval(interval);
  }, [activeVote]);

  if (!activeVote) return null;

  const candidateItems = items.filter(it => activeVote.itemIds?.includes(it.id));
  const myVote = activeVote.votes ? activeVote.votes[currentUserId] : null;

  return (
    <div style={{
      position: 'fixed',
      bottom: '100px',
      right: '340px',
      width: '380px',
      background: '#FFFFFF',
      border: '2px solid #F59E0B',
      borderRadius: '16px',
      padding: '16px',
      boxShadow: '0 10px 30px rgba(0,0,0,0.15)',
      zIndex: 90,
      animation: 'fadeIn 0.25s ease-out'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#B45309', fontWeight: 800, fontSize: '14px' }}>
          <Vote size={18} />
          <span>Contested Slot Vote</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '13px', fontWeight: 700, color: '#D97706' }}>
          <Clock size={15} />
          <span>{secondsLeft}s left</span>
        </div>
      </div>

      <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
        Two or more items contested this time slot. Cast your vote. Winner will be locked; others will be removed.
      </p>

      {/* Candidate Items Options */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '12px' }}>
        {candidateItems.map(item => {
          const isSelected = myVote === item.id;
          return (
            <div
              key={item.id}
              onClick={() => userRole !== 'viewer' && onCastVote(item.id)}
              style={{
                border: isSelected ? '2px solid #F59E0B' : '1px solid var(--border)',
                background: isSelected ? '#FEF3C7' : '#F9FAFB',
                padding: '10px 12px',
                borderRadius: '10px',
                cursor: userRole === 'viewer' ? 'default' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}
            >
              <div>
                <span style={{ fontWeight: 700, fontSize: '13px', display: 'block' }}>{item.venueName}</span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Day {item.dayIndex} ({item.startTime} - {item.endTime}) · €{item.pricePerPerson}
                </span>
              </div>
              {isSelected && <CheckCircle size={18} color="#D97706" />}
            </div>
          );
        })}
      </div>

      <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center' }}>
        Tie-breaker rule: Earliest pinned item, then Leader override choice.
      </div>
    </div>
  );
}
