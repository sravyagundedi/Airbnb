import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, Smile, MessageSquare } from 'lucide-react';

const REACTION_EMOJIS = ['👍', '❤️', '🍷', '⛵', '🎉'];

export default function ChatPanel({
  messages = [],
  typingUsers = {},
  onSendMessage,
  onSendTyping,
  onSendReaction,
  currentUserId
}) {
  const [inputText, setInputText] = useState('');
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, typingUsers]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    onSendMessage(inputText);
    setInputText('');
  };

  const handleInputChange = (e) => {
    setInputText(e.target.value);
    onSendTyping();
  };

  const typingList = Object.values(typingUsers);

  return (
    <div style={{
      width: '320px',
      borderLeft: '1px solid var(--border)',
      background: '#FFFFFF',
      display: 'flex',
      flexDirection: 'column',
      height: '100%'
    }}>
      {/* Header */}
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <MessageSquare size={18} color="var(--primary)" />
        <span style={{ fontWeight: 800, fontSize: '14px' }}>Room War Chat</span>
      </div>

      {/* Messages Scroll Area */}
      <div style={{ flex: 1, padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {messages.map((m, idx) => {
          const isMe = m.userId === currentUserId;
          const isAI = m.messageType === 'ai_answer' || m.userName === 'AI Concierge';

          return (
            <div
              key={m.id || idx}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: isMe ? 'flex-end' : 'flex-start',
                width: '100%'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '2px', fontSize: '11px', color: 'var(--text-muted)' }}>
                {isAI && <Bot size={13} color="var(--primary)" />}
                <span style={{ fontWeight: 700 }}>{m.userName}</span>
              </div>

              <div style={{
                background: isAI ? '#FFF0F3' : (isMe ? 'var(--primary)' : '#F1F3F5'),
                color: isAI ? '#991B1B' : (isMe ? '#FFFFFF' : '#1A1A1A'),
                border: isAI ? '1px solid #FFCCD5' : 'none',
                padding: '8px 12px',
                borderRadius: isMe ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                fontSize: '13px',
                maxWidth: '90%',
                lineHeight: 1.4,
                wordBreak: 'break-word',
                boxShadow: isAI ? '0 2px 6px rgba(255, 56, 92, 0.08)' : 'none'
              }}>
                {m.content}
              </div>

              {/* Reaction bar */}
              <div style={{ display: 'flex', gap: '2px', marginTop: '4px' }}>
                {REACTION_EMOJIS.map(emoji => (
                  <button
                    key={emoji}
                    onClick={() => onSendReaction(m.id, emoji)}
                    style={{ fontSize: '11px', padding: '1px 3px', borderRadius: '4px' }}
                    title={`React with ${emoji}`}
                  >
                    {emoji}
                  </button>
                ))}
              </div>
            </div>
          );
        })}

        {/* Typing indicator */}
        {typingList.length > 0 && (
          <div style={{ fontSize: '11px', fontStyle: 'italic', color: 'var(--text-muted)' }}>
            {typingList.join(', ')} {typingList.length === 1 ? 'is' : 'are'} typing...
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} style={{ padding: '12px', borderTop: '1px solid var(--border)', display: 'flex', gap: '8px' }}>
        <input
          type="text"
          placeholder="Discuss plans or tag AI..."
          value={inputText}
          onChange={handleInputChange}
          maxLength={1000}
          style={{
            flex: 1,
            padding: '8px 12px',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            fontSize: '13px',
            outline: 'none'
          }}
        />
        <button
          type="submit"
          disabled={!inputText.trim()}
          style={{
            background: inputText.trim() ? 'var(--primary)' : '#E5E7EB',
            color: '#FFFFFF',
            padding: '8px 12px',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          <Send size={15} />
        </button>
      </form>
    </div>
  );
}
