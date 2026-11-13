import React, { useState } from 'react';
import { Compass, Key, Mail, User, DollarSign, ShieldAlert } from 'lucide-react';
import { api, authStorage } from '../api';

const DIETARY_OPTIONS = ['vegetarian', 'vegan', 'halal', 'gluten-free'];

export default function LoginModal({ onLoginSuccess }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('leader@warroom.local');
  const [password, setPassword] = useState('Password123!');
  const [displayName, setDisplayName] = useState('Trip Leader');
  const [role, setRole] = useState('leader');
  const [budgetCeiling, setBudgetCeiling] = useState(150);
  const [dietaryTags, setDietaryTags] = useState(['vegetarian']);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const toggleTag = (tag) => {
    setDietaryTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      let tokens;
      if (isRegister) {
        tokens = await api.register({
          email: email.trim(),
          password,
          display_name: displayName.trim(),
          role,
          budget_ceiling: Number(budgetCeiling),
          dietary_tags: dietaryTags
        });
      } else {
        tokens = await api.login(email.trim(), password);
      }

      authStorage.saveTokens(tokens.access_token, tokens.refresh_token);
      const user = await api.getMe();
      authStorage.saveTokens(tokens.access_token, tokens.refresh_token, user);
      onLoginSuccess(user);
    } catch (err) {
      const msg = typeof err === 'string'
        ? err
        : (err?.message && err.message !== '[object Object]' ? err.message : 'Authentication failed. Please verify your credentials.');
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #FFF1F2 0%, #F5F3FF 100%)',
      padding: '24px'
    }}>
      <div style={{
        background: '#FFFFFF',
        width: '440px',
        borderRadius: '20px',
        padding: '36px',
        boxShadow: '0 20px 40px rgba(0,0,0,0.08)',
        border: '1px solid var(--border)'
      }}>
        {/* Brand */}
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{
            background: 'var(--primary)',
            color: '#FFF',
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 12px'
          }}>
            <Compass size={28} />
          </div>
          <h1 style={{ fontSize: '22px', fontWeight: 800, letterSpacing: '-0.5px' }}>AI Trip War Room</h1>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Collaborative Group Itinerary & Real-Time Logistics Engine
          </p>
        </div>

        {/* Tab switch */}
        <div style={{ display: 'flex', background: '#F1F3F5', borderRadius: '10px', padding: '3px', marginBottom: '16px' }}>
          <button
            type="button"
            onClick={() => { setIsRegister(false); setError(null); }}
            style={{
              flex: 1,
              padding: '8px',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '13px',
              background: !isRegister ? '#FFFFFF' : 'transparent',
              color: !isRegister ? 'var(--text-main)' : 'var(--text-muted)',
              boxShadow: !isRegister ? '0 2px 4px rgba(0,0,0,0.05)' : 'none'
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setIsRegister(true); setError(null); }}
            style={{
              flex: 1,
              padding: '8px',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '13px',
              background: isRegister ? '#FFFFFF' : 'transparent',
              color: isRegister ? 'var(--text-main)' : 'var(--text-muted)',
              boxShadow: isRegister ? '0 2px 4px rgba(0,0,0,0.05)' : 'none'
            }}
          >
            Create Account
          </button>
        </div>

        {/* Quick Demo Switcher */}
        {!isRegister && (
          <div style={{
            background: '#F8F9FA',
            border: '1px solid var(--border)',
            borderRadius: '10px',
            padding: '10px 12px',
            marginBottom: '16px'
          }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: '6px' }}>
              One-Click Demo Accounts
            </span>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                type="button"
                onClick={() => {
                  setEmail('leader@warroom.local');
                  setPassword('Password123!');
                  setError(null);
                }}
                style={{
                  flex: 1,
                  padding: '6px 8px',
                  borderRadius: '6px',
                  fontSize: '11px',
                  fontWeight: 700,
                  background: email === 'leader@warroom.local' ? '#FFE4E6' : '#FFFFFF',
                  color: email === 'leader@warroom.local' ? 'var(--primary)' : 'var(--text-main)',
                  border: email === 'leader@warroom.local' ? '1px solid var(--primary)' : '1px solid var(--border)'
                }}
              >
                👑 Leader
              </button>
              <button
                type="button"
                onClick={() => {
                  setEmail('planner@warroom.local');
                  setPassword('Password123!');
                  setError(null);
                }}
                style={{
                  flex: 1,
                  padding: '6px 8px',
                  borderRadius: '6px',
                  fontSize: '11px',
                  fontWeight: 700,
                  background: email === 'planner@warroom.local' ? '#FFE4E6' : '#FFFFFF',
                  color: email === 'planner@warroom.local' ? 'var(--primary)' : 'var(--text-main)',
                  border: email === 'planner@warroom.local' ? '1px solid var(--primary)' : '1px solid var(--border)'
                }}
              >
                📝 Planner
              </button>
              <button
                type="button"
                onClick={() => {
                  setEmail('admin@warroom.local');
                  setPassword('Password123!');
                  setError(null);
                }}
                style={{
                  flex: 1,
                  padding: '6px 8px',
                  borderRadius: '6px',
                  fontSize: '11px',
                  fontWeight: 700,
                  background: email === 'admin@warroom.local' ? '#FFE4E6' : '#FFFFFF',
                  color: email === 'admin@warroom.local' ? 'var(--primary)' : 'var(--text-main)',
                  border: email === 'admin@warroom.local' ? '1px solid var(--primary)' : '1px solid var(--border)'
                }}
              >
                🛡️ Admin
              </button>
            </div>
          </div>
        )}

        {error && (
          <div style={{
            background: '#FEF2F2',
            border: '1px solid #FCA5A5',
            color: '#991B1B',
            padding: '10px 12px',
            borderRadius: '8px',
            fontSize: '12px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <ShieldAlert size={15} />
            <span>{typeof error === 'string' ? error : JSON.stringify(error)}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Email Address</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border)' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={8}
              style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border)' }}
            />
          </div>

          {isRegister && (
            <>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Display Name</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={e => setDisplayName(e.target.value)}
                  required
                  style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border)' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Role</label>
                  <select
                    value={role}
                    onChange={e => setRole(e.target.value)}
                    style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--border)', textTransform: 'capitalize' }}
                  >
                    <option value="planner">Planner</option>
                    <option value="leader">Leader</option>
                    <option value="viewer">Viewer</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Budget Ceiling (€)</label>
                  <input
                    type="number"
                    value={budgetCeiling}
                    onChange={e => setBudgetCeiling(e.target.value)}
                    min={20}
                    max={500}
                    style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--border)' }}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '6px' }}>Dietary Constraints</label>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {DIETARY_OPTIONS.map(tag => {
                    const active = dietaryTags.includes(tag);
                    return (
                      <button
                        type="button"
                        key={tag}
                        onClick={() => toggleTag(tag)}
                        style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          padding: '4px 8px',
                          borderRadius: '6px',
                          background: active ? '#DCFCE7' : '#F1F3F5',
                          color: active ? '#166534' : '#666',
                          border: active ? '1px solid #86EFAC' : '1px solid transparent',
                          textTransform: 'capitalize'
                        }}
                      >
                        {tag}
                      </button>
                    );
                  })}
                </div>
              </div>
            </>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              background: 'var(--primary)',
              color: '#FFFFFF',
              padding: '12px',
              borderRadius: '10px',
              fontWeight: 800,
              fontSize: '14px',
              marginTop: '8px',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? 'Authenticating...' : (isRegister ? 'Register & Enter' : 'Sign In')}
          </button>
        </form>
      </div>
    </div>
  );
}
