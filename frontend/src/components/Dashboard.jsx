import React, { useState, useEffect } from 'react';
import { Plus, Compass, Users, Sparkles, Shield, BarChart3, ArrowRight, DollarSign, Tag, Check, Calendar } from 'lucide-react';
import { api } from '../api';
import AdminPanel from './AdminPanel';

export default function Dashboard({ user, onSelectTrip }) {
  const [dashboardData, setDashboardData] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [showAdminModal, setShowAdminModal] = useState(false);
  const [selectedAnalytics, setSelectedAnalytics] = useState(null);

  // Form states
  const [newTitle, setNewTitle] = useState('Lisbon Adventure');
  const [maxParticipants, setMaxParticipants] = useState(10);
  const [joinCode, setJoinCode] = useState('');
  const [formError, setFormError] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [dash, recs] = await Promise.all([
        api.getDashboard(),
        api.getRecommendations(user.id, 6)
      ]);
      setDashboardData(dash);
      setRecommendations(recs);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTrip = async (e) => {
    e.preventDefault();
    setFormError(null);
    try {
      const trip = await api.createTrip(newTitle, 'Lisbon', maxParticipants);
      setShowCreateModal(false);
      onSelectTrip(trip);
    } catch (err) {
      setFormError(err.message);
    }
  };

  const handleJoinTrip = async (e) => {
    e.preventDefault();
    setFormError(null);
    try {
      const trip = await api.joinTrip(joinCode.trim().toUpperCase());
      setShowJoinModal(false);
      onSelectTrip(trip);
    } catch (err) {
      setFormError(err.message);
    }
  };

  const handleViewAnalytics = async (tripId) => {
    try {
      const stats = await api.getTripAnalytics(tripId);
      setSelectedAnalytics(stats);
    } catch (err) {
      alert(`Could not fetch analytics: ${err.message}`);
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 24px' }}>
      {/* Top Welcome Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.5px' }}>
            Welcome back, {user.display_name}!
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Your collaborative itinerary war room and real-time logistics center for Lisbon.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          {user.role === 'admin' && (
            <button
              onClick={() => setShowAdminModal(true)}
              style={{
                background: '#EDE9FE',
                color: '#6D28D9',
                padding: '10px 16px',
                borderRadius: '8px',
                fontWeight: 700,
                fontSize: '13px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <Shield size={16} /> Admin Portal
            </button>
          )}

          <button
            onClick={() => setShowJoinModal(true)}
            style={{
              background: '#FFFFFF',
              border: '1px solid var(--border)',
              color: 'var(--text-main)',
              padding: '10px 18px',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '13px'
            }}
          >
            Join with Code
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            style={{
              background: 'var(--primary)',
              color: '#FFFFFF',
              padding: '10px 20px',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Plus size={16} /> Create Trip Room
          </button>
        </div>
      </div>

      {/* Grid: Trips & Preferences */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px', marginBottom: '36px' }}>
        {/* Trips Column */}
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 800, marginBottom: '14px' }}>Your Trip Rooms</h2>
          {dashboardData?.trips?.length === 0 ? (
            <div style={{ background: '#FFFFFF', border: '1px solid var(--border)', borderRadius: '12px', padding: '32px', textAlign: 'center' }}>
              <Compass size={36} color="var(--primary)" style={{ margin: '0 auto 12px' }} />
              <div style={{ fontWeight: 700, fontSize: '16px' }}>No trip rooms yet</div>
              <p style={{ color: 'var(--text-muted)', fontSize: '13px', margin: '6px 0 16px' }}>
                Create a new war room for Lisbon or join an existing trip with an invite code.
              </p>
              <button
                onClick={() => setShowCreateModal(true)}
                style={{ background: 'var(--primary)', color: '#FFF', padding: '8px 16px', borderRadius: '8px', fontWeight: 700, fontSize: '13px' }}
              >
                Create Your First Trip
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {dashboardData?.trips?.map(trip => (
                <div
                  key={trip.id}
                  style={{
                    background: '#FFFFFF',
                    border: trip.isActive ? '2px solid var(--primary)' : '1px solid var(--border)',
                    borderRadius: '12px',
                    padding: '16px 20px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    boxShadow: '0 2px 6px rgba(0,0,0,0.03)'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 800, fontSize: '16px' }}>{trip.title}</span>
                      {trip.isActive && (
                        <span style={{ background: '#DCFCE7', color: '#166534', fontSize: '11px', fontWeight: 700, padding: '2px 8px', borderRadius: '12px' }}>
                          ● LIVE ROOM ({trip.activeParticipants} active)
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Invite Code: <code>{trip.inviteCode}</code> · Role: <strong style={{ textTransform: 'capitalize' }}>{trip.role}</strong>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <button
                      onClick={() => handleViewAnalytics(trip.id)}
                      style={{ padding: '8px', borderRadius: '6px', color: 'var(--text-muted)', background: '#F8F9FA' }}
                      title="View Reconciliation Analytics"
                    >
                      <BarChart3 size={16} />
                    </button>
                    <button
                      onClick={() => onSelectTrip(trip)}
                      style={{
                        background: 'var(--primary)',
                        color: '#FFFFFF',
                        padding: '8px 18px',
                        borderRadius: '8px',
                        fontWeight: 700,
                        fontSize: '13px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                    >
                      Enter Room <ArrowRight size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Derived Preferences Card */}
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 800, marginBottom: '14px' }}>Travel Persona</h2>
          <div style={{ background: '#FFFFFF', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <div style={{ background: '#FEF3C7', color: '#D97706', padding: '6px', borderRadius: '8px' }}>
                <Sparkles size={18} />
              </div>
              <div>
                <span style={{ fontWeight: 700, fontSize: '14px' }}>Derived Preferences</span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block' }}>Reconciled from history & interactions</span>
              </div>
            </div>

            <div style={{ marginBottom: '14px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                Budget Ceiling
              </span>
              <div style={{ fontWeight: 800, fontSize: '18px', color: '#10B981', marginTop: '2px' }}>
                €{user.budget_ceiling} <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 400 }}>/day ceiling</span>
              </div>
            </div>

            <div style={{ marginBottom: '14px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                Top Category Affinities
              </span>
              <div style={{ display: 'flex', gap: '6px', marginTop: '6px', flexWrap: 'wrap' }}>
                {dashboardData?.preferences?.topCategories?.map(cat => (
                  <span key={cat} style={{ background: '#F0F2F5', padding: '3px 8px', borderRadius: '6px', fontSize: '12px', fontWeight: 600, textTransform: 'capitalize' }}>
                    {cat}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                Dietary Requirements
              </span>
              <div style={{ display: 'flex', gap: '6px', marginTop: '6px', flexWrap: 'wrap' }}>
                {user.dietary_tags?.length === 0 ? (
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>None specified</span>
                ) : (
                  user.dietary_tags?.map(tag => (
                    <span key={tag} style={{ background: '#DCFCE7', color: '#166534', padding: '3px 8px', borderRadius: '6px', fontSize: '12px', fontWeight: 600 }}>
                      {tag}
                    </span>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recommendations Rail */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 800 }}>Recommended Lisbon Venues For You</h2>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Offline-evaluated Hybrid Recommender (P@5 &gt;= 0.6) combining item-item cosine collaborative filtering and user feature centroids.
            </p>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
          {recommendations.map(v => (
            <div
              key={v.venueId}
              style={{
                background: '#FFFFFF',
                border: '1px solid var(--border)',
                borderRadius: '12px',
                padding: '16px',
                boxShadow: '0 2px 6px rgba(0,0,0,0.03)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between'
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '11px', background: '#F0F2F5', padding: '2px 6px', borderRadius: '4px', textTransform: 'capitalize', fontWeight: 600 }}>
                    {v.category}
                  </span>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#F59E0B' }}>★ {v.rating}</span>
                </div>
                <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '4px' }}>{v.name}</h3>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4, marginBottom: '10px' }}>
                  {v.description?.slice(0, 95)}...
                </p>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border)', paddingTop: '10px' }}>
                <span style={{ fontWeight: 800, color: '#10B981', fontSize: '14px' }}>€{v.pricePerPerson}</span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{v.hours?.open} - {v.hours?.close}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Analytics Modal */}
      {selectedAnalytics && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, backdropFilter: 'blur(3px)' }}>
          <div style={{ background: '#FFFFFF', width: '500px', borderRadius: '16px', padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 800 }}>Trip #{selectedAnalytics.tripId} Reconciled Analytics</h3>
              <button onClick={() => setSelectedAnalytics(null)} style={{ fontSize: '18px', color: '#888' }}>✕</button>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
              Reconciled strictly against the append-only events log table.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginBottom: '20px' }}>
              <div style={{ background: '#F8F9FA', padding: '12px', borderRadius: '8px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Planning Duration</span>
                <div style={{ fontSize: '18px', fontWeight: 800 }}>{selectedAnalytics.planningDurationMinutes} min</div>
              </div>
              <div style={{ background: '#F8F9FA', padding: '12px', borderRadius: '8px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Peak Planners</span>
                <div style={{ fontSize: '18px', fontWeight: 800 }}>{selectedAnalytics.peakConcurrentPlanners}</div>
              </div>
              <div style={{ background: '#F8F9FA', padding: '12px', borderRadius: '8px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>AI Questions Asked</span>
                <div style={{ fontSize: '18px', fontWeight: 800 }}>{selectedAnalytics.aiQuestionsCount}</div>
              </div>
              <div style={{ background: '#F8F9FA', padding: '12px', borderRadius: '8px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Conflicts Resolved</span>
                <div style={{ fontSize: '18px', fontWeight: 800 }}>{selectedAnalytics.conflictsResolved}</div>
              </div>
            </div>

            <button onClick={() => setSelectedAnalytics(null)} style={{ width: '100%', padding: '10px', background: 'var(--primary)', color: '#FFF', borderRadius: '8px', fontWeight: 700 }}>
              Done
            </button>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <form onSubmit={handleCreateTrip} style={{ background: '#FFF', width: '420px', borderRadius: '16px', padding: '24px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 800, marginBottom: '14px' }}>Create Lisbon Trip War Room</h3>
            {formError && <div style={{ color: '#DC2626', fontSize: '12px', marginBottom: '10px' }}>{formError}</div>}
            <div style={{ marginBottom: '12px' }}>
              <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Trip Title</label>
              <input type="text" value={newTitle} onChange={e => setNewTitle(e.target.value)} required style={{ width: '100%', padding: '8px', borderRadius: '8px', border: '1px solid var(--border)' }} />
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Max Participants (Capacity Limit)</label>
              <input type="number" min={2} max={25} value={maxParticipants} onChange={e => setMaxParticipants(Number(e.target.value))} required style={{ width: '100%', padding: '8px', borderRadius: '8px', border: '1px solid var(--border)' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button type="button" onClick={() => setShowCreateModal(false)} style={{ padding: '8px 14px' }}>Cancel</button>
              <button type="submit" style={{ background: 'var(--primary)', color: '#FFF', padding: '8px 18px', borderRadius: '8px', fontWeight: 700 }}>Create Room</button>
            </div>
          </form>
        </div>
      )}

      {/* Join Modal */}
      {showJoinModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <form onSubmit={handleJoinTrip} style={{ background: '#FFF', width: '380px', borderRadius: '16px', padding: '24px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 800, marginBottom: '14px' }}>Join Trip by Invite Code</h3>
            {formError && <div style={{ color: '#DC2626', fontSize: '12px', marginBottom: '10px' }}>{formError}</div>}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '4px' }}>Invite Code (e.g. AB-XXXX)</label>
              <input type="text" placeholder="AB-XXXX" value={joinCode} onChange={e => setJoinCode(e.target.value)} required style={{ width: '100%', padding: '8px', borderRadius: '8px', border: '1px solid var(--border)', textTransform: 'uppercase', fontFamily: 'monospace' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button type="button" onClick={() => setShowJoinModal(false)} style={{ padding: '8px 14px' }}>Cancel</button>
              <button type="submit" style={{ background: 'var(--primary)', color: '#FFF', padding: '8px 18px', borderRadius: '8px', fontWeight: 700 }}>Join Trip</button>
            </div>
          </form>
        </div>
      )}

      {showAdminModal && <AdminPanel onClose={() => setShowAdminModal(false)} />}
    </div>
  );
}
