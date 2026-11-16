import React, { useState, useEffect } from 'react';
import { X, Receipt, Plus, CheckCircle, ArrowRight, DollarSign, Wallet, Check, AlertCircle } from 'lucide-react';
import { api } from '../api';

const CATEGORIES = [
  { id: 'dining', label: '🍽️ Dining & Drinks' },
  { id: 'lodging', label: '🏨 Lodging & Stays' },
  { id: 'activity', label: '🎟️ Tickets & Tours' },
  { id: 'transit', label: '🚕 Transit & Rides' },
  { id: 'other', label: '🛒 Groceries & Misc' }
];

export default function ExpenseModal({ isOpen, onClose, trip, currentUser }) {
  const [activeTab, setActiveTab] = useState('record'); // 'record' | 'ledger' | 'settle'
  const [title, setTitle] = useState('');
  const [amount, setAmount] = useState('');
  const [category, setCategory] = useState('dining');
  const [payerId, setPayerId] = useState(currentUser?.id || '');
  const [members, setMembers] = useState([]);
  const [selectedUserIds, setSelectedUserIds] = useState([]);
  const [expensesData, setExpensesData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && trip?.id) {
      loadMembers();
      loadExpenses();
    }
  }, [isOpen, trip?.id]);

  const loadMembers = async () => {
    try {
      const data = await api.getTripMembers(trip.id);
      setMembers(data || []);
      setSelectedUserIds((data || []).map(m => m.user_id));
      if (!payerId && currentUser?.id) {
        setPayerId(currentUser.id);
      }
    } catch (err) {
      console.error('Failed to load members:', err);
    }
  };

  const loadExpenses = async () => {
    try {
      setLoading(true);
      const data = await api.getExpenses(trip.id);
      setExpensesData(data);
    } catch (err) {
      console.error('Failed to load expenses:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleParticipant = (userId) => {
    setSelectedUserIds(prev =>
      prev.includes(userId)
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };

  const handleRecordExpense = async (e) => {
    e.preventDefault();
    if (!amount || Number(amount) <= 0) {
      setError('Please enter a valid amount.');
      return;
    }
    if (selectedUserIds.length === 0) {
      setError('Select at least one traveler to split this expense.');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      await api.createExpense(trip.id, {
        title: title.trim(),
        amount: parseFloat(amount),
        category,
        paid_by_user_id: Number(payerId),
        split_user_ids: selectedUserIds
      });

      setTitle('');
      setAmount('');
      setSuccessMsg('Expense recorded successfully!');
      setTimeout(() => setSuccessMsg(null), 3000);
      await loadExpenses();
      setActiveTab('ledger');
    } catch (err) {
      setError(err?.message || 'Failed to record expense.');
    } finally {
      setSaving(false);
    }
  };

  const handleSettleAll = async () => {
    try {
      setSaving(true);
      await api.settleExpenses(trip.id);
      setSuccessMsg('All trip expenses marked as settled!');
      setTimeout(() => setSuccessMsg(null), 3000);
      await loadExpenses();
    } catch (err) {
      setError(err?.message || 'Failed to settle expenses.');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  const symbol = trip?.currency_symbol || '€';
  const currency = trip?.currency || 'EUR';

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
        maxWidth: '720px',
        maxHeight: '88vh',
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
          alignItems: 'center',
          background: 'linear-gradient(135deg, #FFF1F2 0%, #FFFFFF 100%)'
        }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Receipt size={20} color="var(--primary)" />
              Expense Ledger & Settle Up
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
              Hamilton-Hare exact cents split & minimal debt settlement for {trip?.title}
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

        {/* Tab switch */}
        <div style={{ display: 'flex', padding: '12px 24px 0', gap: '8px', borderBottom: '1px solid var(--border)' }}>
          <button
            onClick={() => setActiveTab('record')}
            style={{
              padding: '8px 16px',
              border: 'none',
              background: 'none',
              fontWeight: 700,
              fontSize: '13px',
              color: activeTab === 'record' ? 'var(--primary)' : 'var(--text-muted)',
              borderBottom: activeTab === 'record' ? '2px solid var(--primary)' : '2px solid transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Plus size={15} /> Add Expense
          </button>
          <button
            onClick={() => setActiveTab('ledger')}
            style={{
              padding: '8px 16px',
              border: 'none',
              background: 'none',
              fontWeight: 700,
              fontSize: '13px',
              color: activeTab === 'ledger' ? 'var(--primary)' : 'var(--text-muted)',
              borderBottom: activeTab === 'ledger' ? '2px solid var(--primary)' : '2px solid transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Receipt size={15} /> Expense History ({expensesData?.expenses?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('settle')}
            style={{
              padding: '8px 16px',
              border: 'none',
              background: 'none',
              fontWeight: 700,
              fontSize: '13px',
              color: activeTab === 'settle' ? 'var(--primary)' : 'var(--text-muted)',
              borderBottom: activeTab === 'settle' ? '2px solid var(--primary)' : '2px solid transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Wallet size={15} /> Settle Up ({expensesData?.settlement_plan?.length || 0})
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
          {successMsg && (
            <div style={{
              background: '#F0FDF4',
              border: '1px solid #86EFAC',
              color: '#166534',
              padding: '10px 14px',
              borderRadius: '8px',
              fontSize: '13px',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <CheckCircle size={16} />
              <span>{successMsg}</span>
            </div>
          )}

          {error && (
            <div style={{
              background: '#FEF2F2',
              border: '1px solid #FCA5A5',
              color: '#991B1B',
              padding: '10px 14px',
              borderRadius: '8px',
              fontSize: '13px',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          {/* TAB 1: RECORD EXPENSE */}
          {activeTab === 'record' && (
            <form onSubmit={handleRecordExpense} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Description / Item</label>
                  <input
                    type="text"
                    placeholder="e.g. Group Dinner at Taberna da Rua"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '14px' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                    Amount ({currency})
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    placeholder="0.00"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    required
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '14px' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Category</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '14px' }}
                  >
                    {CATEGORIES.map(c => (
                      <option key={c.id} value={c.id}>{c.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Paid By</label>
                  <select
                    value={payerId}
                    onChange={(e) => setPayerId(e.target.value)}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '14px' }}
                  >
                    {members.map(m => (
                      <option key={m.user_id} value={m.user_id}>
                        {m.display_name} {m.user_id === currentUser?.id ? '(You)' : ''}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Split selection */}
              <div>
                <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '8px' }}>
                  Split Equally Between ({selectedUserIds.length} travelers):
                </label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {members.map(m => {
                    const isChecked = selectedUserIds.includes(m.user_id);
                    return (
                      <button
                        type="button"
                        key={m.user_id}
                        onClick={() => handleToggleParticipant(m.user_id)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: '8px',
                          border: isChecked ? '1px solid var(--primary)' : '1px solid var(--border)',
                          background: isChecked ? '#FFE4E6' : '#F8F9FA',
                          color: isChecked ? 'var(--primary)' : 'var(--text-main)',
                          fontSize: '12px',
                          fontWeight: 600,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        {isChecked && <Check size={14} />}
                        {m.display_name}
                      </button>
                    );
                  })}
                </div>
              </div>

              {amount && selectedUserIds.length > 0 && (
                <div style={{ background: '#F8F9FA', borderRadius: '10px', padding: '12px', fontSize: '13px', color: 'var(--text-muted)' }}>
                  Exact split: <strong>{symbol}{(parseFloat(amount) / selectedUserIds.length).toFixed(2)}</strong> per traveler (allocated in exact cents).
                </div>
              )}

              <button
                type="submit"
                disabled={saving}
                style={{
                  background: 'var(--primary)',
                  color: '#FFF',
                  border: 'none',
                  borderRadius: '10px',
                  padding: '12px',
                  fontWeight: 700,
                  fontSize: '14px',
                  cursor: saving ? 'not-allowed' : 'pointer',
                  opacity: saving ? 0.7 : 1
                }}
              >
                {saving ? 'Recording...' : 'Record Expense'}
              </button>
            </form>
          )}

          {/* TAB 2: EXPENSE HISTORY */}
          {activeTab === 'ledger' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Total Group Spend</span>
                  <div style={{ fontSize: '24px', fontWeight: 900, color: 'var(--text-main)' }}>
                    {symbol}{expensesData?.total_expenses?.toFixed(2) || '0.00'} {currency}
                  </div>
                </div>

                {expensesData?.category_totals && (
                  <div style={{ display: 'flex', gap: '8px', fontSize: '11px', color: 'var(--text-muted)' }}>
                    {Object.entries(expensesData.category_totals).map(([cat, tot]) => (
                      <span key={cat} style={{ background: '#F1F3F5', padding: '4px 8px', borderRadius: '6px' }}>
                        {cat}: {symbol}{tot.toFixed(0)}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {expensesData?.expenses?.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
                  No expenses recorded yet. Click "Add Expense" to track group costs.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {expensesData?.expenses?.map(exp => (
                    <div
                      key={exp.id}
                      style={{
                        border: '1px solid var(--border)',
                        borderRadius: '10px',
                        padding: '12px 16px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 700, fontSize: '14px', color: 'var(--text-main)' }}>
                          {exp.title}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                          Paid by <strong>{exp.paid_by_name}</strong> • {exp.shares.length} travelers split
                        </div>
                      </div>

                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontWeight: 800, fontSize: '15px', color: 'var(--primary)' }}>
                          {symbol}{exp.amount.toFixed(2)}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          {new Date(exp.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: SETTLE UP */}
          {activeTab === 'settle' && (
            <div>
              <div style={{ marginBottom: '16px' }}>
                <h3 style={{ fontSize: '15px', fontWeight: 800, margin: '0 0 4px' }}>Pairwise Settlement Plan</h3>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0 }}>
                  Calculated with minimal debt matching algorithm to settle all group debts in the fewest transactions.
                </p>
              </div>

              {expensesData?.settlement_plan?.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 0', background: '#F0FDF4', borderRadius: '12px', color: '#166534' }}>
                  <CheckCircle size={32} style={{ marginBottom: '8px' }} />
                  <div style={{ fontWeight: 800, fontSize: '15px' }}>All Settled Up!</div>
                  <div style={{ fontSize: '12px', marginTop: '4px' }}>No outstanding debts between travelers.</div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
                  {expensesData?.settlement_plan?.map((s, idx) => (
                    <div
                      key={idx}
                      style={{
                        border: '1px solid #E2E8F0',
                        borderRadius: '12px',
                        padding: '14px 18px',
                        background: '#F8FAFC',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontWeight: 700, color: '#334155' }}>{s.from_user_name}</span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-muted)', fontSize: '12px' }}>
                          pays <ArrowRight size={14} />
                        </span>
                        <span style={{ fontWeight: 700, color: 'var(--primary)' }}>{s.to_user_name}</span>
                      </div>

                      <div style={{ fontWeight: 900, fontSize: '16px', color: '#0F172A' }}>
                        {symbol}{s.amount.toFixed(2)} {currency}
                      </div>
                    </div>
                  ))}

                  <button
                    onClick={handleSettleAll}
                    disabled={saving}
                    style={{
                      marginTop: '12px',
                      background: '#10B981',
                      color: '#FFF',
                      border: 'none',
                      borderRadius: '10px',
                      padding: '12px',
                      fontWeight: 700,
                      fontSize: '14px',
                      cursor: saving ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px'
                    }}
                  >
                    <CheckCircle size={16} /> Mark All Debts as Settled
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '14px 24px',
          borderTop: '1px solid var(--border)',
          background: '#F8F9FA',
          textAlign: 'right'
        }}>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '8px 16px',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer'
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
