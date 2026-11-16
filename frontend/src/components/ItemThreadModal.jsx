import React, { useState, useEffect } from 'react';
import { X, MessageSquare, Send, User, Clock, MapPin, DollarSign } from 'lucide-react';
import { api } from '../api';

export default function ItemThreadModal({ isOpen, onClose, trip, item, currentUser }) {
  const [comments, setComments] = useState([]);
  const [newContent, setNewContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (isOpen && trip?.id && item?.id) {
      loadComments();
    }
  }, [isOpen, trip?.id, item?.id]);

  const loadComments = async () => {
    try {
      setLoading(true);
      const data = await api.getItemComments(trip.id, item.id);
      setComments(data || []);
    } catch (err) {
      console.error('Failed to load item comments:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSendComment = async (e) => {
    e.preventDefault();
    if (!newContent.trim()) return;

    try {
      setSending(true);
      const c = await api.addItemComment(trip.id, item.id, newContent.trim());
      setComments(prev => [...prev, c]);
      setNewContent('');
    } catch (err) {
      console.error('Failed to send comment:', err);
    } finally {
      setSending(false);
    }
  };

  if (!isOpen || !item) return null;

  const symbol = trip?.currency_symbol || '€';

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
        maxWidth: '560px',
        height: '620px',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'linear-gradient(135deg, #FFF1F2 0%, #FFFFFF 100%)'
        }}>
          <div>
            <div style={{ fontSize: '11px', fontWeight: 800, color: 'var(--primary)', textTransform: 'uppercase' }}>
              Day {item.day_index} • {item.start_time} - {item.end_time}
            </div>
            <h2 style={{ fontSize: '16px', fontWeight: 800, margin: '2px 0 0 0', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <MessageSquare size={18} color="var(--primary)" />
              {item.venue_name || `Activity #${item.id}`}
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{
              background: '#F1F3F5',
              border: 'none',
              borderRadius: '50%',
              width: '30px',
              height: '30px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer'
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Item Summary Banner */}
        <div style={{
          padding: '10px 20px',
          background: '#F8F9FA',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '12px',
          color: 'var(--text-muted)'
        }}>
          <span>Category: <strong style={{ color: 'var(--text-main)' }}>{item.category || 'Sightseeing'}</strong></span>
          <span>Price: <strong style={{ color: 'var(--primary)' }}>{symbol}{item.price_per_person || 0}</strong> / person</span>
          <span>Lifecycle: <strong style={{ textTransform: 'capitalize' }}>{item.lifecycle_stage}</strong></span>
        </div>

        {/* Messages Body */}
        <div style={{
          flex: 1,
          padding: '20px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
              Loading discussion...
            </div>
          ) : comments.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
              <div style={{ fontSize: '32px', marginBottom: '8px' }}>💬</div>
              <div style={{ fontWeight: 700, fontSize: '14px', color: 'var(--text-main)', marginBottom: '4px' }}>
                No thread comments yet
              </div>
              <div style={{ fontSize: '12px' }}>
                Ask a question, share a reservation link, or leave a note about this venue.
              </div>
            </div>
          ) : (
            comments.map(c => {
              const isMe = c.user_id === currentUser?.id;
              return (
                <div
                  key={c.id}
                  style={{
                    alignSelf: isMe ? 'flex-end' : 'flex-start',
                    maxWidth: '82%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isMe ? 'flex-end' : 'flex-start'
                  }}
                >
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '3px' }}>
                    {c.user_name} • {new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                  <div style={{
                    padding: '10px 14px',
                    borderRadius: '14px',
                    background: isMe ? 'var(--primary)' : '#F1F3F5',
                    color: isMe ? '#FFFFFF' : 'var(--text-main)',
                    fontSize: '13px',
                    lineHeight: '1.4',
                    borderBottomRightRadius: isMe ? '2px' : '14px',
                    borderBottomLeftRadius: !isMe ? '2px' : '14px'
                  }}>
                    {c.content}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Input Bar */}
        <form
          onSubmit={handleSendComment}
          style={{
            padding: '14px 18px',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            gap: '10px',
            background: '#FFFFFF'
          }}
        >
          <input
            type="text"
            placeholder="Discuss timing, tickets, dress code..."
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            style={{
              flex: 1,
              padding: '10px 14px',
              border: '1px solid var(--border)',
              borderRadius: '24px',
              fontSize: '13px'
            }}
          />
          <button
            type="submit"
            disabled={sending || !newContent.trim()}
            style={{
              background: 'var(--primary)',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '50%',
              width: '40px',
              height: '40px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: (!newContent.trim() || sending) ? 'not-allowed' : 'pointer',
              opacity: (!newContent.trim() || sending) ? 0.6 : 1
            }}
          >
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}
