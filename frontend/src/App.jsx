import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Dashboard from './components/Dashboard';
import TripCanvas from './components/TripCanvas';
import BudgetPanel from './components/BudgetPanel';
import ChatPanel from './components/ChatPanel';
import ConciergePanel from './components/ConciergePanel';
import VotePanel from './components/VotePanel';
import LoginModal from './components/LoginModal';
import { useRoomSocket } from './hooks/useRoomSocket';
import { api, authStorage } from './api';
import { Sparkles, MessageSquare, AlertCircle, CheckCircle, Info } from 'lucide-react';

export default function App() {
  const [currentUser, setCurrentUser] = useState(authStorage.getUser());
  const [currentTrip, setCurrentTrip] = useState(null);
  const [venuesCatalog, setVenuesCatalog] = useState([]);
  const [rightPanelTab, setRightPanelTab] = useState('concierge'); // 'concierge' | 'chat'

  // Load user profile & venues catalog
  useEffect(() => {
    if (authStorage.getAccessToken()) {
      api.getMe()
        .then(u => {
          setCurrentUser(u);
          authStorage.saveTokens(authStorage.getAccessToken(), authStorage.getRefreshToken(), u);
        })
        .catch(() => authStorage.clear());

      api.getVenues('Lisbon')
        .then(setVenuesCatalog)
        .catch(console.error);
    }
  }, []);

  // WebSocket hook for the active room
  const token = authStorage.getAccessToken();
  const room = useRoomSocket(currentTrip?.id, token);

  const handleLogout = () => {
    authStorage.clear();
    setCurrentUser(null);
    setCurrentTrip(null);
  };

  if (!currentUser) {
    return <LoginModal onLoginSuccess={setCurrentUser} />;
  }

  const isLeader = currentUser.role === 'leader' || currentTrip?.creator_id === currentUser.id;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* Toast Alert */}
      {room.toast && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          background: room.toast.type === 'error' ? '#EF4444' : (room.toast.type === 'warning' ? '#F59E0B' : '#10B981'),
          color: '#FFFFFF',
          padding: '12px 18px',
          borderRadius: '10px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
          zIndex: 200,
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '13px',
          fontWeight: 600,
          animation: 'fadeIn 0.2s ease-out'
        }}>
          {room.toast.type === 'error' ? <AlertCircle size={16} /> : (room.toast.type === 'warning' ? <AlertCircle size={16} /> : <CheckCircle size={16} />)}
          <span>{room.toast.text}</span>
          <button onClick={room.dismissToast} style={{ color: '#FFFFFF', opacity: 0.8, marginLeft: '8px', fontSize: '14px' }}>✕</button>
        </div>
      )}

      {/* Header */}
      <Header
        user={currentUser}
        currentTrip={currentTrip}
        latencyMs={room.latencyMs}
        connected={room.connected}
        activeParticipants={room.activeParticipants}
        onBackToDashboard={() => setCurrentTrip(null)}
        onLogout={handleLogout}
      />

      {/* Main View: Dashboard or Room Canvas */}
      {!currentTrip ? (
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <Dashboard
            user={currentUser}
            onSelectTrip={(trip) => setCurrentTrip(trip)}
          />
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Canvas + Side Panel Layout */}
          <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
            <TripCanvas
              items={room.items}
              conflicts={room.conflicts}
              userRole={currentUser.role}
              isLeader={isLeader}
              onMove={room.moveItem}
              onPin={room.pinVenue}
              onLock={room.lockItem}
              onUnlock={room.unlockItem}
              onRemove={room.removeItem}
              onOpenVote={room.openVote}
              venuesCatalog={venuesCatalog}
            />

            {/* Right Tabs and Panel (Concierge vs Chat) */}
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', borderLeft: '1px solid var(--border)' }}>
              {/* Tab Selector */}
              <div style={{ display: 'flex', background: '#F1F3F5', borderBottom: '1px solid var(--border)' }}>
                <button
                  onClick={() => setRightPanelTab('concierge')}
                  style={{
                    flex: 1,
                    padding: '10px',
                    fontWeight: 700,
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                    background: rightPanelTab === 'concierge' ? '#FFFFFF' : 'transparent',
                    color: rightPanelTab === 'concierge' ? 'var(--primary)' : 'var(--text-muted)'
                  }}
                >
                  <Sparkles size={14} /> AI Concierge
                </button>
                <button
                  onClick={() => setRightPanelTab('chat')}
                  style={{
                    flex: 1,
                    padding: '10px',
                    fontWeight: 700,
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                    background: rightPanelTab === 'chat' ? '#FFFFFF' : 'transparent',
                    color: rightPanelTab === 'chat' ? 'var(--primary)' : 'var(--text-muted)'
                  }}
                >
                  <MessageSquare size={14} /> Room Chat
                </button>
              </div>

              {/* Panel Content */}
              <div style={{ flex: 1, overflow: 'hidden' }}>
                {rightPanelTab === 'concierge' ? (
                  <ConciergePanel
                    tripId={currentTrip.id}
                    onPinVenue={room.pinVenue}
                    venuesCatalog={venuesCatalog}
                  />
                ) : (
                  <ChatPanel
                    messages={room.messages}
                    typingUsers={room.typingUsers}
                    onSendMessage={room.sendChatMessage}
                    onSendTyping={room.sendTyping}
                    onSendReaction={room.sendReaction}
                    currentUserId={currentUser.id}
                  />
                )}
              </div>
            </div>
          </div>

          {/* Active Vote Floating Panel */}
          {room.activeVote && (
            <VotePanel
              activeVote={room.activeVote}
              items={room.items}
              onCastVote={room.castVote}
              currentUserId={currentUser.id}
              userRole={currentUser.role}
            />
          )}

          {/* Bottom Running Logistics & Integer-Cent Budget Split Engine */}
          <BudgetPanel
            budgetTotals={room.budgetTotals}
            members={room.members}
            conflicts={room.conflicts}
          />
        </div>
      )}
    </div>
  );
}
