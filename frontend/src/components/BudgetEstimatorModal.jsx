import React, { useState, useEffect } from 'react';
import { X, Calculator, DollarSign, Users, Calendar, Sparkles, TrendingUp, ShieldCheck, ArrowRight } from 'lucide-react';
import { api } from '../api';

const TRAVEL_STYLES = [
  { id: 'budget', label: '🎒 Budget', desc: 'Hostels, local eateries, public transit' },
  { id: 'balanced', label: '🏖️ Balanced', desc: 'Boutique stays, sit-down dining, highlights' },
  { id: 'luxury', label: '✨ Luxury', desc: '5-star resorts, fine dining, private transfers' }
];

export default function BudgetEstimatorModal({ isOpen, onClose, defaultCountry = 'Portugal', defaultDestination = 'Lisbon', onApplyBudget }) {
  const [countries, setCountries] = useState([]);
  const [country, setCountry] = useState(defaultCountry);
  const [destination, setDestination] = useState(defaultDestination);
  const [durationDays, setDurationDays] = useState(4);
  const [travelersCount, setTravelersCount] = useState(3);
  const [travelStyle, setTravelStyle] = useState('balanced');
  const [currency, setCurrency] = useState('EUR');
  const [estimate, setEstimate] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getCountries().then(data => {
      setCountries(data || []);
      const matched = (data || []).find(c => c.country.toLowerCase() === defaultCountry.toLowerCase());
      if (matched) {
        setCurrency(matched.currency);
      }
    }).catch(console.error);
  }, [defaultCountry]);

  useEffect(() => {
    if (isOpen) {
      calculateEstimate();
    }
  }, [isOpen, country, destination, durationDays, travelersCount, travelStyle, currency]);

  const handleCountryChange = (selectedCountryName) => {
    setCountry(selectedCountryName);
    const cObj = countries.find(c => c.country === selectedCountryName);
    if (cObj) {
      setCurrency(cObj.currency);
      setDestination(cObj.defaultCity || (cObj.cities && cObj.cities[0]) || destination);
    }
  };

  const calculateEstimate = async () => {
    try {
      setLoading(true);
      const res = await api.estimateBudget({
        destination,
        country,
        duration_days: Number(durationDays),
        travelers_count: Number(travelersCount),
        travel_style: travelStyle,
        currency
      });
      setEstimate(res);
    } catch (err) {
      console.error('Estimate failed:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const currentCountryObj = countries.find(c => c.country === country);

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
        maxWidth: '780px',
        maxHeight: '90vh',
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
              <Calculator size={20} color="var(--primary)" />
              Pre-Trip Group Budget Estimator
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
              Calculate living costs, dining, and logistics tailored to any destination worldwide
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
        <div style={{ padding: '24px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Controls Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            {/* Country */}
            <div>
              <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '6px' }}>Destination Country</label>
              <select
                value={country}
                onChange={(e) => handleCountryChange(e.target.value)}
                style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '14px' }}
              >
                {countries.map(c => (
                  <option key={c.country} value={c.country}>
                    {c.flag} {c.country} ({c.currency})
                  </option>
                ))}
              </select>
            </div>

            {/* City */}
            <div>
              <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '6px' }}>City / Region</label>
              {currentCountryObj && currentCountryObj.cities?.length > 0 ? (
                <select
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '14px' }}
                >
                  {currentCountryObj.cities.map(cty => (
                    <option key={cty} value={cty}>{cty}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '14px' }}
                />
              )}
            </div>

            {/* Duration */}
            <div>
              <label style={{ fontSize: '12px', fontWeight: 700, display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span>Trip Duration</span>
                <span style={{ color: 'var(--primary)' }}>{durationDays} Days</span>
              </label>
              <input
                type="range"
                min="1"
                max="30"
                value={durationDays}
                onChange={(e) => setDurationDays(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--primary)' }}
              />
            </div>

            {/* Party Size */}
            <div>
              <label style={{ fontSize: '12px', fontWeight: 700, display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span>Travelers</span>
                <span style={{ color: 'var(--primary)' }}>{travelersCount} People</span>
              </label>
              <input
                type="range"
                min="1"
                max="20"
                value={travelersCount}
                onChange={(e) => setTravelersCount(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--primary)' }}
              />
            </div>
          </div>

          {/* Travel Style Selector */}
          <div>
            <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', marginBottom: '8px' }}>Travel Tier & Style</label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
              {TRAVEL_STYLES.map(s => {
                const isSelected = travelStyle === s.id;
                return (
                  <div
                    key={s.id}
                    onClick={() => setTravelStyle(s.id)}
                    style={{
                      border: isSelected ? '2px solid var(--primary)' : '1px solid var(--border)',
                      background: isSelected ? '#FFF5F5' : '#FFFFFF',
                      borderRadius: '12px',
                      padding: '12px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ fontWeight: 800, fontSize: '14px', marginBottom: '4px' }}>{s.label}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{s.desc}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Estimation Results */}
          {estimate && (
            <div style={{
              background: '#F8F9FA',
              borderRadius: '16px',
              padding: '20px',
              border: '1px solid var(--border)'
            }}>
              {/* Totals Banner */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid var(--border)', paddingBottom: '16px' }}>
                <div>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    Projected Total Group Budget
                  </div>
                  <div style={{ fontSize: '28px', fontWeight: 900, color: 'var(--primary)' }}>
                    {estimate.currency_symbol}{estimate.total_trip_cost.toLocaleString()}
                    <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-muted)', marginLeft: '6px' }}>
                      {estimate.currency}
                    </span>
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    Per Person Total
                  </div>
                  <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-main)' }}>
                    {estimate.currency_symbol}{estimate.per_person_total.toLocaleString()}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {estimate.currency_symbol}{(estimate.per_person_total / durationDays).toFixed(0)} / day / person
                  </div>
                </div>
              </div>

              {/* Category Breakdown Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '10px', marginBottom: '16px' }}>
                <div style={{ background: '#FFF', padding: '10px', borderRadius: '10px', border: '1px solid var(--border)', textAlign: 'center' }}>
                  <div style={{ fontSize: '18px', marginBottom: '4px' }}>🏨</div>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)' }}>Lodging</div>
                  <div style={{ fontSize: '13px', fontWeight: 800 }}>{estimate.currency_symbol}{estimate.category_totals.lodging.toLocaleString()}</div>
                </div>
                <div style={{ background: '#FFF', padding: '10px', borderRadius: '10px', border: '1px solid var(--border)', textAlign: 'center' }}>
                  <div style={{ fontSize: '18px', marginBottom: '4px' }}>🍽️</div>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)' }}>Food</div>
                  <div style={{ fontSize: '13px', fontWeight: 800 }}>{estimate.currency_symbol}{estimate.category_totals.food.toLocaleString()}</div>
                </div>
                <div style={{ background: '#FFF', padding: '10px', borderRadius: '10px', border: '1px solid var(--border)', textAlign: 'center' }}>
                  <div style={{ fontSize: '18px', marginBottom: '4px' }}>🎟️</div>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)' }}>Activities</div>
                  <div style={{ fontSize: '13px', fontWeight: 800 }}>{estimate.currency_symbol}{estimate.category_totals.activities.toLocaleString()}</div>
                </div>
                <div style={{ background: '#FFF', padding: '10px', borderRadius: '10px', border: '1px solid var(--border)', textAlign: 'center' }}>
                  <div style={{ fontSize: '18px', marginBottom: '4px' }}>🚇</div>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)' }}>Transit</div>
                  <div style={{ fontSize: '13px', fontWeight: 800 }}>{estimate.currency_symbol}{estimate.category_totals.transit.toLocaleString()}</div>
                </div>
                <div style={{ background: '#FFF', padding: '10px', borderRadius: '10px', border: '1px solid var(--border)', textAlign: 'center' }}>
                  <div style={{ fontSize: '18px', marginBottom: '4px' }}>🛡️</div>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)' }}>Buffer (15%)</div>
                  <div style={{ fontSize: '13px', fontWeight: 800 }}>{estimate.currency_symbol}{estimate.category_totals.buffer.toLocaleString()}</div>
                </div>
              </div>

              {/* Local Travel Tips */}
              {estimate.recommendations && (
                <div style={{ background: '#EFF6FF', borderRadius: '10px', padding: '12px 14px', border: '1px solid #BFDBFE' }}>
                  <div style={{ fontSize: '12px', fontWeight: 800, color: '#1E40AF', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Sparkles size={14} /> Local Logistics & Cost Tips
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: '#1E3A8A', lineHeight: '1.6' }}>
                    {estimate.recommendations.map((tip, i) => (
                      <li key={i}>{tip}</li>
                    ))}
                  </ul>
                </div>
              )}
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

          {onApplyBudget && estimate && (
            <button
              onClick={() => {
                onApplyBudget(estimate);
                onClose();
              }}
              style={{
                background: 'var(--primary)',
                color: '#FFF',
                border: 'none',
                borderRadius: '8px',
                padding: '10px 20px',
                fontWeight: 700,
                fontSize: '13px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              Apply Estimated Budget to War Room <ArrowRight size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
