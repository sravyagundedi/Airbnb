import React from 'react';
import { Compass, Sparkles, MapPin, Users, Calculator, Receipt, ShieldCheck, ArrowRight, X } from 'lucide-react';

export default function SplashScreen({ isOpen, onClose, onOpenEstimator, onOpenMyTrips }) {
  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.65)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1100,
      backdropFilter: 'blur(6px)',
      padding: '20px'
    }}>
      <div style={{
        background: '#FFFFFF',
        borderRadius: '24px',
        width: '100%',
        maxWidth: '720px',
        maxHeight: '90vh',
        boxShadow: '0 30px 60px -15px rgba(0, 0, 0, 0.3)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative'
      }}>
        {/* Close Button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '18px',
            right: '18px',
            background: 'rgba(255, 255, 255, 0.9)',
            border: 'none',
            borderRadius: '50%',
            width: '32px',
            height: '32px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            zIndex: 10,
            boxShadow: '0 2px 6px rgba(0,0,0,0.1)'
          }}
        >
          <X size={18} />
        </button>

        {/* Hero Header */}
        <div style={{
          background: 'linear-gradient(135deg, #FF385C 0%, #E00B41 100%)',
          color: '#FFFFFF',
          padding: '36px 32px 30px',
          textAlign: 'center'
        }}>
          <div style={{
            background: '#FFFFFF',
            color: 'var(--primary)',
            width: '56px',
            height: '56px',
            borderRadius: '16px',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '14px',
            boxShadow: '0 8px 16px rgba(0,0,0,0.15)'
          }}>
            <Compass size={32} />
          </div>
          <h1 style={{ fontSize: '26px', fontWeight: 900, margin: '0 0 6px', letterSpacing: '-0.5px' }}>
            AI Trip War Room
          </h1>
          <p style={{ fontSize: '15px', opacity: 0.95, fontWeight: 500, maxWidth: '520px', margin: '0 auto' }}>
            Collaborative Group Itinerary Canvas & Real-Time Logistics Engine
          </p>

        </div>

        {/* Feature Cards Grid */}
        <div style={{ padding: '28px 32px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div style={{
              border: '1px solid var(--border)',
              borderRadius: '14px',
              padding: '16px',
              background: '#F8FAFC'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 800, fontSize: '14px', color: '#0F172A', marginBottom: '6px' }}>
                <MapPin size={18} color="var(--primary)" /> Worldwide Destinations
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                Plan in Tokyo, Paris, New York, or Lisbon. Automatically adapts to local currencies (EUR, JPY, USD, INR) with live suggestions.
              </div>
            </div>

            <div style={{
              border: '1px solid var(--border)',
              borderRadius: '14px',
              padding: '16px',
              background: '#F8FAFC'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 800, fontSize: '14px', color: '#0F172A', marginBottom: '6px' }}>
                <Users size={18} color="#059669" /> Multi-User Live Canvas
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                Collaborate in real time with optimistic concurrency (under 100ms sync), version conflict locks, timed polls, and activity threads.
              </div>

            </div>

            <div style={{
              border: '1px solid var(--border)',
              borderRadius: '14px',
              padding: '16px',
              background: '#F8FAFC'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 800, fontSize: '14px', color: '#0F172A', marginBottom: '6px' }}>
                <Sparkles size={18} color="#7C3AED" /> Grounded AI Concierge
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                RAG concierge that enforces hard group constraints (budget, dietary, transit buffers) with zero hallucinations and real citations.
              </div>
            </div>

            <div style={{
              border: '1px solid var(--border)',
              borderRadius: '14px',
              padding: '16px',
              background: '#F8FAFC'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 800, fontSize: '14px', color: '#0F172A', marginBottom: '6px' }}>
                <Receipt size={18} color="#D97706" /> Hamilton-Hare Expenses
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                Split shared costs to the exact integer cent. Instant debt settlement plan minimizes transactions so settling up is painless.
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div style={{
            display: 'flex',
            gap: '12px',
            borderTop: '1px solid var(--border)',
            paddingTop: '20px'
          }}>
            <button
              onClick={() => { onClose(); onOpenMyTrips(); }}
              style={{
                flex: 1,
                padding: '12px',
                borderRadius: '12px',
                background: 'var(--primary)',
                color: '#FFFFFF',
                border: 'none',
                fontWeight: 700,
                fontSize: '14px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px'
              }}
            >
              My War Rooms & Trips <ArrowRight size={16} />
            </button>

            <button
              onClick={() => { onClose(); onOpenEstimator(); }}
              style={{
                flex: 1,
                padding: '12px',
                borderRadius: '12px',
                background: '#F1F5F9',
                color: 'var(--text-main)',
                border: '1px solid var(--border)',
                fontWeight: 700,
                fontSize: '14px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px'
              }}
            >
              <Calculator size={16} /> Pre-Trip Budget Estimator
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
