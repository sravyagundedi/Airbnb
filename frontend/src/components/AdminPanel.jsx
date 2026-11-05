import React, { useState } from 'react';
import { Shield, Upload, RefreshCw, AlertTriangle, CheckCircle } from 'lucide-react';
import { api } from '../api';

export default function AdminPanel({ onClose }) {
  const [jsonText, setJsonText] = useState('');
  const [uploading, setUploading] = useState(false);
  const [retraining, setRetraining] = useState(false);
  const [errorDetails, setErrorDetails] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const handleUpload = async () => {
    setErrorDetails(null);
    setSuccessMsg(null);
    try {
      const parsed = JSON.parse(jsonText);
      const rows = Array.isArray(parsed) ? parsed : [parsed];
      setUploading(true);
      const res = await api.uploadVenues('Lisbon', rows);
      setSuccessMsg(`Successfully processed and committed ${res.venuesProcessed} venue(s) into database!`);
      setJsonText('');
    } catch (err) {
      if (err.message && err.message.includes('rowErrors')) {
        try {
          const parsedErr = JSON.parse(err.message);
          setErrorDetails(parsedErr);
        } catch {
          setErrorDetails({ message: err.message });
        }
      } else {
        setErrorDetails({ message: err.message || 'Validation error' });
      }
    } finally {
      setUploading(false);
    }
  };

  const handleRetrain = async () => {
    setRetraining(true);
    setSuccessMsg(null);
    setErrorDetails(null);
    try {
      const res = await api.triggerRetrain();
      setSuccessMsg(`Model successfully retrained! Precision@5: ${res.precisionAt5}. Artifacts reloaded.`);
    } catch (err) {
      setErrorDetails({ message: err.message || 'Retraining failed' });
    } finally {
      setRetraining(false);
    }
  };

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
      backdropFilter: 'blur(3px)'
    }}>
      <div style={{
        background: '#FFFFFF',
        width: '650px',
        maxHeight: '85vh',
        borderRadius: '16px',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 20px 40px rgba(0,0,0,0.2)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ background: '#EDE9FE', color: '#6D28D9', padding: '6px', borderRadius: '8px' }}>
              <Shield size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: 800 }}>Admin Operations & Dataset Ingestion</h3>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Validate destination venues & trigger recommender retraining</span>
            </div>
          </div>
          <button onClick={onClose} style={{ fontSize: '18px', color: '#888' }}>✕</button>
        </div>

        {/* Retrain Trigger Bar */}
        <div style={{
          background: '#F9FAFB',
          border: '1px solid var(--border)',
          borderRadius: '10px',
          padding: '12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '16px'
        }}>
          <div>
            <span style={{ fontWeight: 700, fontSize: '13px', display: 'block' }}>Recommender Retraining</span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Recomputes hybrid item-item matrix & offline Precision@5</span>
          </div>
          <button
            onClick={handleRetrain}
            disabled={retraining}
            style={{
              background: '#6D28D9',
              color: '#FFFFFF',
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <RefreshCw size={13} className={retraining ? 'animate-spin' : ''} />
            {retraining ? 'Retraining...' : 'Trigger Retrain'}
          </button>
        </div>

        {/* Venue JSON Upload Form */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', marginBottom: '16px' }}>
          <label style={{ fontSize: '12px', fontWeight: 700, marginBottom: '6px' }}>
            Venue Batch JSON (Validates Price &gt; 0, Tags Vocabulary, Coordinates, Hours):
          </label>
          <textarea
            rows={8}
            placeholder={`[\n  {\n    "venueId": "v_test",\n    "name": "New Venue",\n    "category": "dinner",\n    "pricePerPerson": 25,\n    "dietaryTags": ["vegetarian"],\n    "hours": { "open": "18:00", "close": "23:00" },\n    "coordinates": { "lat": 38.71, "lng": -9.14 },\n    "rating": 4.5\n  }\n]`}
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            style={{
              fontFamily: 'monospace',
              fontSize: '12px',
              padding: '10px',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              resize: 'none',
              flex: 1
            }}
          />
        </div>

        {/* Feedback Messages */}
        {successMsg && (
          <div style={{ background: '#ECFDF5', border: '1px solid #A7F3D0', padding: '10px', borderRadius: '8px', color: '#065F46', fontSize: '12px', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle size={15} /> {successMsg}
          </div>
        )}

        {errorDetails && (
          <div style={{ background: '#FEF2F2', border: '1px solid #FCA5A5', padding: '10px', borderRadius: '8px', color: '#991B1B', fontSize: '12px', marginBottom: '12px', maxHeight: '120px', overflowY: 'auto' }}>
            <div style={{ fontWeight: 700, marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <AlertTriangle size={14} /> {errorDetails.message || 'Validation failed'}
            </div>
            {errorDetails.rowErrors?.map((re, idx) => (
              <div key={idx} style={{ marginLeft: '16px', fontSize: '11px', marginTop: '2px' }}>
                • Row {re.row} ({re.venueId}): {re.errors?.join(', ')}
              </div>
            ))}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          <button onClick={onClose} style={{ padding: '8px 16px', color: '#666', fontSize: '13px' }}>
            Close
          </button>
          <button
            onClick={handleUpload}
            disabled={uploading || !jsonText.trim()}
            style={{
              background: 'var(--primary)',
              color: '#FFFFFF',
              padding: '8px 20px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Upload size={14} />
            {uploading ? 'Validating...' : 'Validate & Upload Dataset'}
          </button>
        </div>
      </div>
    </div>
  );
}
