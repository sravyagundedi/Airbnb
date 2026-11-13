import React, { useState } from 'react';
import { User, Mail, DollarSign, Shield, Key, Check, AlertCircle, X, Sparkles } from 'lucide-react';
import { api, authStorage } from '../api';

const DIETARY_OPTIONS = ['vegetarian', 'vegan', 'halal', 'gluten-free'];

export default function ProfileModal({ user, onClose, onUpdateUser }) {
  const [displayName, setDisplayName] = useState(user.display_name || '');
  const [budgetCeiling, setBudgetCeiling] = useState(user.budget_ceiling || 150);
  const [dietaryTags, setDietaryTags] = useState(user.dietary_tags || []);
  
  // Password change fields
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const toggleTag = (tag) => {
    setDietaryTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    if (showPasswordChange) {
      if (!currentPassword) {
        setErrorMsg('Please enter your current password to update it.');
        return;
      }
      if (newPassword.length < 8) {
        setErrorMsg('New password must be at least 8 characters long.');
        return;
      }
      if (newPassword !== confirmPassword) {
        setErrorMsg('New password and confirmation do not match.');
        return;
      }
    }

    setLoading(true);
    try {
      const payload = {
        display_name: displayName.trim(),
        budget_ceiling: Number(budgetCeiling),
        dietary_tags: dietaryTags
      };

      if (showPasswordChange && newPassword) {
        payload.current_password = currentPassword;
        payload.new_password = newPassword;
      }

      const updated = await api.updateProfile(payload);
      authStorage.saveTokens(authStorage.getAccessToken(), authStorage.getRefreshToken(), updated);
      onUpdateUser(updated);
      setSuccessMsg('Profile updated successfully!');
      if (showPasswordChange) {
        setShowPasswordChange(false);
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      }
      setTimeout(() => {
        setSuccessMsg(null);
      }, 3000);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to update profile.');
    } finally {
      setLoading(false);
    }
  };

  const initials = (user.display_name || 'U').split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();

  const formattedJoinDate = user.created_at
    ? new Date(user.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
    : 'Active Member';

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 100,
      backdropFilter: 'blur(3px)',
      padding: '16px'
    }}>
      <div style={{
        background: '#FFFFFF',
        width: '520px',
        maxHeight: '90vh',
        borderRadius: '16px',
        padding: '28px',
        boxShadow: '0 10px 30px rgba(0,0,0,0.15)',
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ background: '#FEE2E2', color: 'var(--primary)', padding: '6px', borderRadius: '8px' }}>
              <User size={18} />
            </div>
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: 800 }}>Account & Profile Settings</h2>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Authenticated Traveler Details</span>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ color: '#888', padding: '6px', borderRadius: '6px' }}
            title="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Identity Card */}
        <div style={{
          background: 'linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          padding: '16px',
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
          marginBottom: '20px'
        }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            background: 'var(--primary)',
            color: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
            fontSize: '18px'
          }}>
            {initials}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: 800, fontSize: '16px' }}>{user.display_name}</span>
              <span style={{
                background: user.role === 'admin' ? '#EDE9FE' : (user.role === 'leader' ? '#FEF3C7' : '#E0F2FE'),
                color: user.role === 'admin' ? '#6D28D9' : (user.role === 'leader' ? '#B45309' : '#0369A1'),
                fontSize: '11px',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '12px',
                textTransform: 'uppercase'
              }}>
                {user.role}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Mail size={13} />
              <span>{user.email}</span>
              <span>· Member since {formattedJoinDate}</span>
            </div>
          </div>
        </div>

        {/* Alerts */}
        {errorMsg && (
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
            gap: '8px'
          }}>
            <AlertCircle size={16} />
            <span>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div style={{
            background: '#ECFDF5',
            border: '1px solid #6EE7B7',
            color: '#065F46',
            padding: '10px 12px',
            borderRadius: '8px',
            fontSize: '12px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <Check size={16} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Edit Form */}
        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
              Full Display Name
            </label>
            <input
              type="text"
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              required
              style={{ width: '100%', padding: '9px 12px', borderRadius: '8px', border: '1px solid var(--border)' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
              Daily Budget Ceiling ($ / €)
            </label>
            <input
              type="number"
              min={20}
              max={2000}
              value={budgetCeiling}
              onChange={e => setBudgetCeiling(e.target.value)}
              required
              style={{ width: '100%', padding: '9px 12px', borderRadius: '8px', border: '1px solid var(--border)' }}
            />
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
              Used by the Logistics Engine and AI Concierge to ensure group activities never exceed your personal threshold.
            </span>
          </div>

          <div>
            <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '6px' }}>
              Personal Dietary Requirements
            </label>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {DIETARY_OPTIONS.map(tag => {
                const active = dietaryTags.includes(tag);
                return (
                  <button
                    type="button"
                    key={tag}
                    onClick={() => toggleTag(tag)}
                    style={{
                      fontSize: '12px',
                      fontWeight: 700,
                      padding: '5px 12px',
                      borderRadius: '8px',
                      background: active ? '#DCFCE7' : '#F1F3F5',
                      color: active ? '#166534' : 'var(--text-main)',
                      border: active ? '1px solid #86EFAC' : '1px solid var(--border)',
                      textTransform: 'capitalize',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    {active && <Check size={13} />}
                    {tag}
                  </button>
                );
              })}
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
              The RAG Concierge enforces the union of all group members' dietary tags when recommending dining venues.
            </span>
          </div>

          {/* Change Password Collapsible Section */}
          <div style={{ borderTop: '1px solid var(--border)', paddingTop: '14px' }}>
            <button
              type="button"
              onClick={() => setShowPasswordChange(!showPasswordChange)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '13px',
                fontWeight: 700,
                color: 'var(--text-main)',
                background: 'transparent',
                padding: '4px 0'
              }}
            >
              <Key size={14} />
              <span>{showPasswordChange ? 'Cancel Password Change' : 'Change Password'}</span>
            </button>

            {showPasswordChange && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '12px', background: '#F8F9FA', padding: '12px', borderRadius: '10px', border: '1px solid var(--border)' }}>
                <div>
                  <label style={{ fontSize: '11px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Current Password</label>
                  <input
                    type="password"
                    value={currentPassword}
                    onChange={e => setCurrentPassword(e.target.value)}
                    placeholder="Enter current password"
                    style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border)' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>New Password (min 8 chars)</label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    placeholder="Enter new password"
                    style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border)' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Confirm New Password</label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    placeholder="Confirm new password"
                    style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border)' }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: '10px 18px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                background: '#FFFFFF',
                fontSize: '13px',
                fontWeight: 600
              }}
            >
              Close
            </button>
            <button
              type="submit"
              disabled={loading}
              style={{
                background: 'var(--primary)',
                color: '#FFFFFF',
                padding: '10px 22px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 700,
                opacity: loading ? 0.7 : 1
              }}
            >
              {loading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
