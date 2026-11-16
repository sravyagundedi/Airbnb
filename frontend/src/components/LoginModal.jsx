import React, { useState } from 'react';
import { Compass, Key, Mail, User, DollarSign, ShieldAlert, Eye, EyeOff, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { api, authStorage } from '../api';

const DIETARY_OPTIONS = ['vegetarian', 'vegan', 'halal', 'gluten-free'];

export default function LoginModal({ onLoginSuccess }) {
  // mode: 'signin' | 'register' | 'forgot'
  const [mode, setMode] = useState('signin');
  const [email, setEmail] = useState('leader@warroom.local');
  const [password, setPassword] = useState('Password123!');
  const [showPassword, setShowPassword] = useState(false);
  const [displayName, setDisplayName] = useState('Trip Leader');
  const [role, setRole] = useState('leader');
  const [budgetCeiling, setBudgetCeiling] = useState(150);
  const [dietaryTags, setDietaryTags] = useState(['vegetarian']);

  // Forgot password state
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [codeSent, setCodeSent] = useState(false);
  const [successMsg, setSuccessMsg] = useState(null);

  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const toggleTag = (tag) => {
    setDietaryTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]);
  };

  const handleSwitchMode = (newMode) => {
    setMode(newMode);
    setError(null);
    setSuccessMsg(null);
    setCodeSent(false);

    if (newMode === 'register') {
      if (email.endsWith('@warroom.local')) {
        setEmail('');
        setPassword('');
        setDisplayName('');
        setRole('planner');
      }
    } else if (newMode === 'signin') {
      if (!email) {
        setEmail('leader@warroom.local');
        setPassword('Password123!');
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      if (mode === 'register') {
        const tokens = await api.register({
          email: email.trim(),
          password,
          display_name: displayName.trim(),
          role,
          budget_ceiling: Number(budgetCeiling),
          dietary_tags: dietaryTags
        });
        authStorage.saveTokens(tokens.access_token, tokens.refresh_token);
        const user = await api.getMe();
        authStorage.saveTokens(tokens.access_token, tokens.refresh_token, user);
        onLoginSuccess(user);
      } else if (mode === 'signin') {
        const tokens = await api.login(email.trim(), password);
        authStorage.saveTokens(tokens.access_token, tokens.refresh_token);
        const user = await api.getMe();
        authStorage.saveTokens(tokens.access_token, tokens.refresh_token, user);
        onLoginSuccess(user);
      } else if (mode === 'forgot') {
        if (!codeSent) {
          // Step 1: Request reset code
          const res = await api.forgotPassword(email.trim());
          setCodeSent(true);
          setResetCode(res.reset_code || '');
          setSuccessMsg(`Reset code generated: ${res.reset_code}. Please enter your new password.`);
        } else {
          // Step 2: Reset password
          const res = await api.resetPassword(email.trim(), resetCode.trim(), newPassword);
          setSuccessMsg('Password successfully reset! You can now sign in.');
          setMode('signin');
          setPassword(newPassword);
        }
      }
    } catch (err) {
      const msg = typeof err === 'string'
        ? err
        : (err?.message && err.message !== '[object Object]' ? err.message : 'Operation failed. Please check your details.');
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
        width: '460px',
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

        {/* Tab switch (only if not in forgot password mode) */}
        {mode !== 'forgot' ? (
          <div style={{ display: 'flex', background: '#F1F3F5', borderRadius: '10px', padding: '3px', marginBottom: '16px' }}>
            <button
              type="button"
              onClick={() => handleSwitchMode('signin')}
              style={{
                flex: 1,
                padding: '8px',
                borderRadius: '8px',
                fontWeight: 700,
                fontSize: '13px',
                background: mode === 'signin' ? '#FFFFFF' : 'transparent',
                color: mode === 'signin' ? 'var(--text-main)' : 'var(--text-muted)',
                boxShadow: mode === 'signin' ? '0 2px 4px rgba(0,0,0,0.05)' : 'none'
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => handleSwitchMode('register')}
              style={{
                flex: 1,
                padding: '8px',
                borderRadius: '8px',
                fontWeight: 700,
                fontSize: '13px',
                background: mode === 'register' ? '#FFFFFF' : 'transparent',
                color: mode === 'register' ? 'var(--text-main)' : 'var(--text-muted)',
                boxShadow: mode === 'register' ? '0 2px 4px rgba(0,0,0,0.05)' : 'none'
              }}
            >
              Create Account
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <button
              type="button"
              onClick={() => handleSwitchMode('signin')}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                color: 'var(--text-muted)',
                fontSize: '13px',
                fontWeight: 600,
                padding: '4px 0'
              }}
            >
              <ArrowLeft size={16} /> Back to Sign In
            </button>
          </div>
        )}

        {/* Quick Demo Switcher */}
        {mode === 'signin' && (
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

        {successMsg && (
          <div style={{
            background: '#F0FDF4',
            border: '1px solid #86EFAC',
            color: '#166534',
            padding: '10px 12px',
            borderRadius: '8px',
            fontSize: '12px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <CheckCircle2 size={16} />
            <span>{successMsg}</span>
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
          {mode === 'register' && (
            <div>
              <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Your Full Name</label>
              <input
                type="text"
                placeholder="e.g. Alex Morgan"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '14px' }}
              />
            </div>
          )}

          <div>
            <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Email Address</label>
            <input
              type="text"
              placeholder={mode === 'register' ? 'yourname@example.com' : 'user@domain.com or leader@warroom.local'}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={mode === 'forgot' && codeSent}
              style={{
                width: '100%',
                padding: '10px 12px',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                fontSize: '14px',
                background: (mode === 'forgot' && codeSent) ? '#F3F4F6' : '#FFFFFF'
              }}
            />
          </div>

          {mode === 'signin' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 700 }}>Password</label>
                <button
                  type="button"
                  onClick={() => handleSwitchMode('forgot')}
                  style={{ background: 'none', border: 'none', color: 'var(--primary)', fontSize: '12px', fontWeight: 600, cursor: 'pointer' }}
                >
                  Forgot password?
                </button>
              </div>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter your account password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  style={{ width: '100%', padding: '10px 38px 10px 12px', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '14px' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '10px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center'
                  }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
          )}

          {mode === 'register' && (
            <>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Choose Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Min. 8 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                    style={{ width: '100%', padding: '10px 38px 10px 12px', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '14px' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center'
                    }}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Your Travel Role</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '14px' }}
                >
                  <option value="planner">📝 Planner (Can edit, pin & suggest)</option>
                  <option value="leader">👑 Leader (Trip organizer with full rights)</option>
                  <option value="viewer">👁️ Viewer (Read-only observer)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Daily Budget Ceiling</label>
                <input
                  type="number"
                  min="0"
                  value={budgetCeiling}
                  onChange={(e) => setBudgetCeiling(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '14px' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '6px' }}>Dietary Preferences</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {DIETARY_OPTIONS.map(tag => {
                    const active = dietaryTags.includes(tag);
                    return (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => toggleTag(tag)}
                        style={{
                          padding: '4px 10px',
                          borderRadius: '16px',
                          fontSize: '12px',
                          fontWeight: 600,
                          background: active ? 'var(--primary)' : '#F1F3F5',
                          color: active ? '#FFF' : 'var(--text-main)',
                          border: 'none',
                          cursor: 'pointer'
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

          {mode === 'forgot' && codeSent && (
            <>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>6-Digit Reset Code</label>
                <input
                  type="text"
                  placeholder="Enter 6-digit code"
                  value={resetCode}
                  onChange={(e) => setResetCode(e.target.value)}
                  required
                  style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '14px' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>New Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Min. 8 characters"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    minLength={8}
                    style={{ width: '100%', padding: '10px 38px 10px 12px', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '14px' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center'
                    }}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
            </>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: '8px',
              padding: '12px',
              borderRadius: '10px',
              border: 'none',
              background: 'var(--primary)',
              color: '#FFFFFF',
              fontWeight: 700,
              fontSize: '15px',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? 'Please wait...' : (
              mode === 'signin' ? 'Sign In' :
              mode === 'register' ? 'Create Account & Enter' :
              (!codeSent ? 'Generate Reset Code' : 'Save New Password & Sign In')
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
