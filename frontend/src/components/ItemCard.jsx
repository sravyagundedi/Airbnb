import React, { useState } from 'react';
import { Lock, Unlock, Vote, Trash2, Clock, DollarSign, Star, MoveRight } from 'lucide-react';

export default function ItemCard({
  item,
  userRole,
  isLeader,
  onMove,
  onLock,
  onUnlock,
  onRemove,
  onOpenVote,
  hasConflict,
  currencySymbol = '€'
}) {
  const [editingTime, setEditingTime] = useState(false);
  const [startT, setStartT] = useState(item.startTime || '12:00');
  const [endT, setEndT] = useState(item.endTime || '13:30');

  const handleTimeSubmit = (e) => {
    e.preventDefault();
    setEditingTime(false);
    onMove(item.id, item.positionVersion, item.dayIndex, startT, endT);
  };

  const handleDayShift = (newDay) => {
    onMove(item.id, item.positionVersion, newDay, item.startTime, item.endTime);
  };

  const stageColors = {
    drafting: { bg: 'var(--badge-drafting)', text: 'var(--badge-drafting-txt)' },
    voting: { bg: 'var(--badge-voting)', text: 'var(--badge-voting-txt)' },
    locked: { bg: 'var(--badge-locked)', text: 'var(--badge-locked-txt)' }
  };

  const badgeStyle = stageColors[item.lifecycleStage] || stageColors.drafting;

  return (
    <div style={{
      background: '#FFFFFF',
      border: hasConflict ? '2px solid #EF4444' : '1px solid var(--border)',
      borderRadius: '12px',
      padding: '14px',
      marginBottom: '12px',
      boxShadow: '0 2px 6px rgba(0,0,0,0.04)',
      position: 'relative',
      transition: 'transform 0.15s ease, box-shadow 0.15s ease'
    }}>
      {/* Top row: Badges and version */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{
            background: badgeStyle.bg,
            color: badgeStyle.text,
            fontSize: '11px',
            fontWeight: 700,
            padding: '2px 8px',
            borderRadius: '6px',
            textTransform: 'uppercase',
            letterSpacing: '0.4px',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            {item.lifecycleStage === 'locked' && <Lock size={12} />}
            {item.lifecycleStage}
          </span>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
            v{item.positionVersion}
          </span>
        </div>

        <span style={{
          fontSize: '11px',
          fontWeight: 600,
          background: '#F0F2F5',
          color: 'var(--text-muted)',
          padding: '2px 6px',
          borderRadius: '4px',
          textTransform: 'capitalize'
        }}>
          {item.category}
        </span>
      </div>

      {/* Venue Name */}
      <div style={{ fontWeight: 700, fontSize: '15px', color: 'var(--text-main)', marginBottom: '4px' }}>
        {item.venueName || `Venue ${item.venueId}`}
      </div>

      {/* Time & Price bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-muted)', margin: '8px 0' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Clock size={14} />
          <span>{item.startTime} - {item.endTime}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '2px', fontWeight: 700, color: '#10B981' }}>
          <span>
            {currencySymbol}
            {currencySymbol === '¥' || currencySymbol === '₩'
              ? Math.round(Number(item.pricePerPerson || 0)).toLocaleString()
              : Number(item.pricePerPerson || 0).toFixed(2)}
          </span>
          <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 400 }}>/person</span>
        </div>
      </div>

      {/* Edit times form */}
      {editingTime && (
        <form onSubmit={handleTimeSubmit} style={{ background: '#F8F9FA', padding: '8px', borderRadius: '8px', margin: '8px 0' }}>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '6px' }}>
            <input
              type="time"
              value={startT}
              onChange={(e) => setStartT(e.target.value)}
              style={{ padding: '4px', border: '1px solid #CCC', borderRadius: '4px', flex: 1 }}
              required
            />
            <input
              type="time"
              value={endT}
              onChange={(e) => setEndT(e.target.value)}
              style={{ padding: '4px', border: '1px solid #CCC', borderRadius: '4px', flex: 1 }}
              required
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
            <button
              type="button"
              onClick={() => setEditingTime(false)}
              style={{ fontSize: '11px', padding: '3px 8px', color: 'var(--text-muted)' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              style={{ fontSize: '11px', padding: '3px 8px', background: 'var(--primary)', color: '#FFF', borderRadius: '4px', fontWeight: 600 }}
            >
              Apply Move
            </button>
          </div>
        </form>
      )}

      {/* Control Actions footer */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border)', paddingTop: '8px', marginTop: '6px' }}>
        {/* Day switch */}
        <div style={{ display: 'flex', gap: '4px' }}>
          {[1, 2, 3].map(d => (
            <button
              key={d}
              onClick={() => handleDayShift(d)}
              disabled={item.dayIndex === d || item.lifecycleStage === 'locked' && !isLeader}
              style={{
                fontSize: '11px',
                padding: '2px 6px',
                borderRadius: '4px',
                background: item.dayIndex === d ? '#222' : '#F0F2F5',
                color: item.dayIndex === d ? '#FFF' : '#666',
                fontWeight: 600,
                opacity: (item.lifecycleStage === 'locked' && !isLeader) ? 0.5 : 1
              }}
              title={`Move to Day ${d}`}
            >
              D{d}
            </button>
          ))}
        </div>

        {/* Action icons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {item.lifecycleStage !== 'locked' && (
            <button
              onClick={() => setEditingTime(!editingTime)}
              style={{ padding: '4px', color: '#666' }}
              title="Change Time Slot"
            >
              <Clock size={14} />
            </button>
          )}

          {/* Lock / Unlock */}
          {item.lifecycleStage === 'locked' ? (
            isLeader && (
              <button
                onClick={() => onUnlock(item.id)}
                style={{ padding: '4px', color: '#B45309' }}
                title="Leader Override: Unlock Item"
              >
                <Unlock size={14} />
              </button>
            )
          ) : (
            isLeader && (
              <button
                onClick={() => onLock(item.id)}
                style={{ padding: '4px', color: '#10B981' }}
                title="Lock Slot (Leader)"
              >
                <Lock size={14} />
              </button>
            )
          )}

          {/* Remove */}
          {(userRole !== 'viewer' && (item.lifecycleStage !== 'locked' || isLeader)) && (
            <button
              onClick={() => onRemove(item.id)}
              style={{ padding: '4px', color: '#EF4444' }}
              title="Remove Item"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
