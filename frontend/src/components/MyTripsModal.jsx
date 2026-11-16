import React, { useState, useEffect } from 'react';
import { X, MapPin, Users, Copy, Check, Plus, ArrowRight, Calendar, Sparkles } from 'lucide-react';
import { api } from '../api';

export default function MyTripsModal({ isOpen, onClose, currentTripId, onSelectTrip, onCreateNew }) {
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [copiedCode, setCopiedCode] = useState(null);

  useEffect(() => {
    if (isOpen) {
      loadTrips();
    }
  }, [isOpen]);

  const loadTrips = async () => {
    try {
      setLoading(true);
      const data = await api.getMyTrips();
      setTrips(data || []);
    } catch (err) {
      console.error('Failed to load trips:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyCode = (code, e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      backdropFilter: 'blur(4px)',
      padding: '20px'
    }}>
      <div style={{
        background: '#FFFFFF',
        borderRadius: '20px',
        width: '100%',
        maxWidth: '680px',
        maxHeight: '85vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <MapPin size={20} color="var(--primary)" />
              My Collaborative Trips
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
              Switch between your active trip war rooms or invite friends
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: '#F1F3F5',
              border: 'none',
              borderRadius: '50%',
              width: '32px',
              height: '32px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer'
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
              Loading your trips...
            </div>
          ) : trips.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 20px' }}>
              <div style={{ fontSize: '42px', marginBottom: '12px' }}>✈️</div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 8px' }}>No Trips Yet</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '20px' }}>
                You haven't created or joined any collaborative trip rooms yet.
              </p>
              <button
                onClick={() => { onClose(); onCreateNew(); }}
                style={{
                  background: 'var(--primary)',
                  color: '#FFF',
                  border: 'none',
                  borderRadius: '10px',
                  padding: '10px 20px',
                  fontWeight: 700,
                  fontSize: '14px',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <Plus size={16} /> Plan a New Trip
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {trips.map(t => {
                const isCurrent = t.id === currentTripId;
                return (
                  <div
                    key={t.id}
                    onClick={() => { onSelectTrip(t); onClose(); }}
                    style={{
                      border: isCurrent ? '2px solid var(--primary)' : '1px solid var(--border)',
                      borderRadius: '14px',
                      padding: '16px 20px',
                      background: isCurrent ? '#FFF5F5' : '#FFFFFF',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                        <span style={{ fontSize: '16px', fontWeight: 800, color: 'var(--text-main)' }}>
                          {t.title}
                        </span>
                        {isCurrent && (
                          <span style={{
                            background: 'var(--primary)',
                            color: '#FFF',
                            fontSize: '11px',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: '12px'
                          }}>
                            Active Room
                          </span>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '13px', color: 'var(--text-muted)' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <MapPin size={14} /> {t.destination}, {t.country || 'Global'}
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Users size={14} /> {t.members_count || 1} travelers
                        </span>
                        <span>
                          Currency: <strong>{t.currency || 'EUR'} ({t.currency_symbol || '€'})</strong>
                        </span>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <button
                        onClick={(e) => handleCopyCode(t.invite_code, e)}
                        title="Copy Invite Code"
                        style={{
                          background: copiedCode === t.invite_code ? '#DCFCE7' : '#F1F3F5',
                          color: copiedCode === t.invite_code ? '#166534' : 'var(--text-main)',
                          border: 'none',
                          borderRadius: '8px',
                          padding: '6px 12px',
                          fontSize: '12px',
                          fontWeight: 700,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        {copiedCode === t.invite_code ? <Check size={14} /> : <Copy size={14} />}
                        {t.invite_code}
                      </button>

                      <div style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: '50%',
                        background: isCurrent ? 'var(--primary)' : '#F1F3F5',
                        color: isCurrent ? '#FFF' : 'var(--text-main)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}>
                        <ArrowRight size={16} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid var(--border)',
          background: '#F8F9FA',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Total trips: {trips.length}
          </span>
          <button
            onClick={() => { onClose(); onCreateNew(); }}
            style={{
              background: 'var(--primary)',
              color: '#FFF',
              border: 'none',
              borderRadius: '8px',
              padding: '8px 16px',
              fontWeight: 700,
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Plus size={16} /> Create New Trip
          </button>
        </div>
      </div>
    </div>
  );
}
