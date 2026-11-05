import React, { useState } from 'react';
import { Sparkles, Compass, AlertCircle, CheckCircle, Clock, MapPin, Plus } from 'lucide-react';
import { api } from '../api';

export default function ConciergePanel({
  tripId,
  onPinVenue,
  venuesCatalog = [],
  destination = 'Lisbon',
  country = 'Portugal',
  currencySymbol = '€'
}) {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const samplePrompts = [
    `Where can we have a vegetarian dinner under ${currencySymbol}35 in central ${destination}?`,
    `Recommend a historic morning tour in ${destination}`,
    `Best rooftop lounge for drinks under ${currencySymbol}25/person in ${destination}`,
    `Authentic ${country} dinner with gluten-free options`
  ];

  const handleAsk = async (queryText) => {
    const q = queryText || question;
    if (!q.trim() || loading) return;

    setLoading(true);
    setError(null);
    try {
      const res = await api.askAI(tripId, q);
      setResponse(res);
    } catch (err) {
      setError(err.message || 'AI Concierge service unavailable');
    } finally {
      setLoading(false);
    }
  };

  const suggestedVenue = response?.suggestedVenueId
    ? venuesCatalog.find(v => v.venueId === response.suggestedVenueId)
    : null;

  return (
    <div style={{
      width: '320px',
      borderLeft: '1px solid var(--border)',
      background: '#FAFAFB',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      padding: '16px',
      overflowY: 'auto'
    }}>
      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
        <div style={{ background: '#FFE4E6', color: 'var(--primary)', padding: '6px', borderRadius: '8px' }}>
          <Sparkles size={18} />
        </div>
        <div>
          <span style={{ fontWeight: 800, fontSize: '15px' }}>AI Concierge</span>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block' }}>
            RAG-grounded with hard deterministic constraint filtering.
          </span>
        </div>
      </div>

      {/* Query Form */}
      <form onSubmit={(e) => { e.preventDefault(); handleAsk(); }} style={{ marginBottom: '14px' }}>
        <textarea
          rows={3}
          placeholder="Ask for group recommendations (budget, dietary, hours, location)..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          style={{
            width: '100%',
            padding: '10px',
            border: '1px solid var(--border)',
            borderRadius: '10px',
            fontSize: '13px',
            resize: 'none',
            outline: 'none',
            background: '#FFFFFF'
          }}
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          style={{
            width: '100%',
            marginTop: '8px',
            background: loading || !question.trim() ? '#E5E7EB' : 'var(--primary)',
            color: '#FFFFFF',
            padding: '8px',
            borderRadius: '8px',
            fontWeight: 700,
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px'
          }}
        >
          {loading ? `Consulting ${destination} Concierge...` : <><Sparkles size={15} /> Ask Concierge</>}
        </button>
      </form>

      {/* Quick Prompts */}
      <div style={{ marginBottom: '16px' }}>
        <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
          Quick Prompt Templates
        </span>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '6px' }}>
          {samplePrompts.map((p, i) => (
            <button
              key={i}
              onClick={() => { setQuestion(p); handleAsk(p); }}
              style={{
                textAlign: 'left',
                background: '#FFFFFF',
                border: '1px solid var(--border)',
                padding: '6px 10px',
                borderRadius: '6px',
                fontSize: '12px',
                color: 'var(--text-main)',
                lineHeight: 1.3
              }}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div style={{ background: '#FEF2F2', border: '1px solid #FCA5A5', padding: '10px', borderRadius: '8px', color: '#991B1B', fontSize: '12px', marginBottom: '12px' }}>
          {error}
        </div>
      )}

      {/* Answer Display */}
      {response && (
        <div style={{
          background: '#FFFFFF',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          padding: '14px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontWeight: 800, fontSize: '13px', color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Compass size={14} /> Concierge Recommendation
            </span>
            {response.latencyMs && (
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                {response.latencyMs} ms
              </span>
            )}
          </div>

          <div style={{ fontSize: '13px', lineHeight: 1.4, color: 'var(--text-main)', marginBottom: '12px' }}>
            {response.answer}
          </div>

          {/* Citations */}
          {response.sourceEvents?.length > 0 && (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', borderTop: '1px solid var(--border)', paddingTop: '8px' }}>
              <span style={{ fontWeight: 700 }}>Grounding Evidence: </span>
              {response.sourceEvents.join(', ')}
            </div>
          )}

          {/* Suggested Venue Card */}
          {suggestedVenue && (
            <div style={{
              marginTop: '12px',
              padding: '10px',
              background: '#F0FDF4',
              border: '1px solid #BBF7D0',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div>
                <span style={{ fontWeight: 700, fontSize: '13px', display: 'block' }}>{suggestedVenue.name}</span>
                <span style={{ fontSize: '12px', color: '#166534', fontWeight: 600 }}>€{suggestedVenue.pricePerPerson}/person</span>
              </div>
              <button
                onClick={() => onPinVenue(suggestedVenue.venueId, 1, '19:30', '21:30')}
                style={{
                  background: '#16A34A',
                  color: '#FFFFFF',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  fontWeight: 700,
                  fontSize: '11px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <Plus size={12} /> Pin Day 1
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
