import React from 'react';
import { Compass, Users, Wifi, WifiOff, LogOut, ArrowLeft, Shield, Copy, Check } from 'lucide-react';

export default function Header({ user, currentTrip, latencyMs, connected, activeParticipants, onBackToDashboard, onLogout, onOpenProfile }) {
  const [copied, setCopied] = React.useState(false);

  const copyInvite = () => {
    if (currentTrip?.invite_code) {
      navigator.clipboard.writeText(currentTrip.invite_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getLatencyColor = (ms) => {
    if (ms === null) return '#A0A0A0';
    if (ms < 80) return '#10B981'; // Green
    if (ms < 150) return '#F59E0B'; // Yellow
    return '#EF4444'; // Red
  };

  return (
    <header style={{
      background: '#FFFFFF',
      borderBottom: '1px solid var(--border)',
      padding: '12px 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      position: 'sticky',
      top: 0,
      zIndex: 50
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }} onClick={onBackToDashboard}>
          <div style={{ background: 'var(--primary)', color: '#FFF', padding: '6px 10px', borderRadius: '8px', display: 'flex', alignItems: 'center' }}>
            <Compass size={20} />
          </div>
          <div>
            <span style={{ fontWeight: 800, fontSize: '18px', color: 'var(--text-main)', letterSpacing: '-0.5px' }}>
              WarRoom
            </span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', fontWeight: 600 }}>
              Group Canvas & Logistics
            </span>
          </div>
        </div>

        {currentTrip && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginLeft: '12px', borderLeft: '1px solid var(--border)', paddingLeft: '16px' }}>
            <button
              onClick={onBackToDashboard}
              style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '13px', color: 'var(--text-muted)', padding: '4px 8px', borderRadius: '6px' }}
              title="Dashboard"
            >
              <ArrowLeft size={16} /> Trips
            </button>
            <span style={{ fontWeight: 700, fontSize: '15px' }}>{currentTrip.title}</span>
            <span style={{
              background: '#F0F2F5',
              padding: '2px 8px',
              borderRadius: '12px',
              fontSize: '12px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              <span>{currentTrip.destination}</span>
              {currentTrip.country && <span style={{ color: 'var(--text-muted)' }}>({currentTrip.country})</span>}
            </span>
            <span style={{
              background: '#E0F2FE',
              color: '#0369A1',
              padding: '2px 8px',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: 700
            }}>
              {currentTrip.currency || 'EUR'} ({currentTrip.currency_symbol || currentTrip.currencySymbol || '€'})
            </span>
            <button
              onClick={copyInvite}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                background: '#F7F7F9',
                border: '1px solid var(--border)',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600
              }}
              title="Click to copy invite code"
            >
              {copied ? <Check size={14} color="#10B981" /> : <Copy size={14} />}
              <code>{currentTrip.invite_code}</code>
            </button>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
        {/* Latency & Connectivity indicator */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          background: '#F7F7F9',
          padding: '4px 10px',
          borderRadius: '20px',
          fontSize: '12px',
          fontWeight: 600
        }}>
          {connected ? (
            <>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: getLatencyColor(latencyMs) }} />
              <Wifi size={14} color={getLatencyColor(latencyMs)} />
              <span>{latencyMs !== null ? `${latencyMs} ms` : 'Syncing'}</span>
            </>
          ) : (
            <>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#EF4444' }} />
              <WifiOff size={14} color="#EF4444" />
              <span>Reconnecting</span>
            </>
          )}
        </div>

        {/* Presence count */}
        {currentTrip && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: 600 }}>
            <Users size={16} color="var(--primary)" />
            <span>{activeParticipants?.length || 1} online</span>
          </div>
        )}

        {/* User Badge */}
        {user && (
          <div
            onClick={onOpenProfile}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              cursor: 'pointer',
              padding: '4px 8px',
              borderRadius: '8px',
              background: '#F8F9FA',
              border: '1px solid var(--border)',
              transition: 'all 0.15s ease'
            }}
            title="Click to view & edit your profile details"
          >
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              background: 'var(--primary)',
              color: '#FFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '13px'
            }}>
              {user.display_name?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div>
              <span style={{ fontSize: '13px', fontWeight: 700, display: 'block' }}>{user.display_name}</span>
              <span style={{
                fontSize: '10px',
                textTransform: 'uppercase',
                padding: '1px 6px',
                borderRadius: '4px',
                background: user.role === 'admin' ? '#EDE9FE' : (user.role === 'leader' ? '#FEF3C7' : '#E0F2FE'),
                color: user.role === 'admin' ? '#6D28D9' : (user.role === 'leader' ? '#B45309' : '#0369A1'),
                fontWeight: 700
              }}>
                {user.role} · Profile
              </span>
            </div>
          </div>
        )}

        <button
          onClick={onLogout}
          style={{ color: 'var(--text-muted)', padding: '6px', borderRadius: '6px' }}
          title="Sign out"
        >
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
}
