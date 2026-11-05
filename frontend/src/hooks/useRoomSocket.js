import { useReducer, useEffect, useRef, useCallback } from 'react';

const initialState = {
  connected: false,
  latencyMs: null,
  items: [],
  messages: [],
  members: [],
  activeParticipants: [],
  budgetTotals: {},
  conflicts: [],
  activeVote: null,
  typingUsers: {},
  frozen: false,
  toast: null,
};

function roomReducer(state, action) {
  switch (action.type) {
    case 'CONNECTED':
      return { ...state, connected: true };
    case 'DISCONNECTED':
      return { ...state, connected: false };
    case 'SET_LATENCY':
      return { ...state, latencyMs: action.payload };
    case 'SET_SNAPSHOT': {
      const snap = action.payload;
      return {
        ...state,
        items: snap.items || [],
        messages: snap.messages || [],
        members: snap.members || [],
        activeParticipants: snap.activeParticipants || [],
        budgetTotals: snap.budgetTotals || {},
        conflicts: snap.conflicts || [],
        activeVote: snap.activeVote || null,
        frozen: snap.frozen || false,
      };
    }
    case 'OPTIMISTIC_MOVE': {
      const { itemId, dayIndex, startTime, endTime } = action.payload;
      return {
        ...state,
        items: state.items.map(it =>
          it.id === itemId
            ? { ...it, dayIndex, startTime, endTime, optimistic: true }
            : it
        ),
      };
    }
    case 'BOARD_UPDATE': {
      const { action: act, item, itemId, budgetTotals, conflicts } = action.payload;
      let newItems = [...state.items];
      if (act === 'pinned') {
        newItems = [...newItems.filter(i => i.id !== item.id), item];
      } else if (act === 'moved' || act === 'locked' || act === 'drafting') {
        newItems = newItems.map(i => (i.id === item.id ? item : i));
      } else if (act === 'removed') {
        newItems = newItems.filter(i => i.id !== itemId);
      }
      return {
        ...state,
        items: newItems,
        budgetTotals: budgetTotals || state.budgetTotals,
        conflicts: conflicts || state.conflicts,
      };
    }
    case 'BOARD_CONFLICT': {
      const { currentState, message } = action.payload;
      return {
        ...state,
        // Roll back conflicted item to authoritative server state
        items: state.items.map(it => (it.id === currentState.id ? currentState : it)),
        toast: { text: message || 'Concurrency conflict: someone else modified this item first.', type: 'warning' },
      };
    }
    case 'ACTION_REJECTED': {
      return {
        ...state,
        toast: { text: action.payload.reason || 'Action rejected by room rules.', type: 'error' },
      };
    }
    case 'PRESENCE_UPDATE': {
      const { participantId, action: pAction, participantCount } = action.payload;
      let active = [...state.activeParticipants];
      if (pAction === 'joined' && !active.includes(participantId)) {
        active.push(participantId);
      } else if (pAction === 'left') {
        active = active.filter(id => id !== participantId);
      }
      return { ...state, activeParticipants: active };
    }
    case 'LEADER_DISCONNECTED': {
      return {
        ...state,
        frozen: true,
        toast: { text: 'Trip Leader disconnected. Structural board changes are frozen for 15s.', type: 'warning' },
      };
    }
    case 'LEADER_RESUMED': {
      return {
        ...state,
        frozen: false,
        toast: { text: 'Trip Leader returned. Board controls unfrozen.', type: 'info' },
      };
    }
    case 'CHAT_MESSAGE': {
      return {
        ...state,
        messages: [...state.messages, action.payload],
      };
    }
    case 'CHAT_TYPING': {
      const { userId, userName } = action.payload;
      return {
        ...state,
        typingUsers: { ...state.typingUsers, [userId]: userName },
      };
    }
    case 'CLEAR_TYPING': {
      const { userId } = action.payload;
      const copy = { ...state.typingUsers };
      delete copy[userId];
      return { ...state, typingUsers: copy };
    }
    case 'VOTE_OPENED': {
      return {
        ...state,
        activeVote: action.payload.vote,
        items: action.payload.items || state.items,
        toast: { text: 'A contested slot vote has opened!', type: 'info' },
      };
    }
    case 'VOTE_CAST': {
      if (!state.activeVote) return state;
      return {
        ...state,
        activeVote: {
          ...state.activeVote,
          votesCount: action.payload.votesCount,
        },
      };
    }
    case 'VOTE_RESOLVED': {
      return {
        ...state,
        activeVote: null,
        items: action.payload.items || state.items,
        budgetTotals: action.payload.budgetTotals || state.budgetTotals,
        conflicts: action.payload.conflicts || state.conflicts,
        toast: { text: `Contested slot vote resolved! Winner item #${action.payload.winnerItemId} locked.`, type: 'success' },
      };
    }
    case 'DISMISS_TOAST':
      return { ...state, toast: null };
    default:
      return state;
  }
}

export function useRoomSocket(tripId, token) {
  const [state, dispatch] = useReducer(roomReducer, initialState);
  const wsRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const pingIntervalRef = useRef(null);

  const sendEvent = useCallback((event, payload = {}) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ event, payload }));
    }
  }, []);

  const connect = useCallback(() => {
    if (!tripId || !token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/trips/${tripId}?token=${token}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      dispatch({ type: 'CONNECTED' });
      reconnectAttempts.current = 0;

      // Start ping/pong drift monitoring
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            event: 'trip.sync.ping',
            payload: { clientSentAt: Date.now() }
          }));
        }
      }, 2000);
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        const { event, payload } = msg;

        if (event === 'trip.room.snapshot') {
          dispatch({ type: 'SET_SNAPSHOT', payload });
        } else if (event === 'trip.sync.pong') {
          const rtt = Date.now() - (payload.clientSentAt || Date.now());
          dispatch({ type: 'SET_LATENCY', payload: rtt });
        } else if (event === 'trip.board.update') {
          dispatch({ type: 'BOARD_UPDATE', payload });
        } else if (event === 'trip.board.conflict') {
          dispatch({ type: 'BOARD_CONFLICT', payload });
        } else if (event === 'trip.action.rejected') {
          dispatch({ type: 'ACTION_REJECTED', payload });
        } else if (event === 'trip.presence.update') {
          dispatch({ type: 'PRESENCE_UPDATE', payload });
        } else if (event === 'trip.leader.disconnected') {
          dispatch({ type: 'LEADER_DISCONNECTED', payload });
        } else if (event === 'trip.leader.resumed') {
          dispatch({ type: 'LEADER_RESUMED', payload });
        } else if (event === 'trip.chat.message') {
          dispatch({ type: 'CHAT_MESSAGE', payload });
        } else if (event === 'trip.chat.typing') {
          dispatch({ type: 'CHAT_TYPING', payload });
          setTimeout(() => {
            dispatch({ type: 'CLEAR_TYPING', payload: { userId: payload.userId } });
          }, 3000);
        } else if (event === 'trip.vote.opened') {
          dispatch({ type: 'VOTE_OPENED', payload });
        } else if (event === 'trip.vote.cast') {
          dispatch({ type: 'VOTE_CAST', payload });
        } else if (event === 'trip.vote.resolved') {
          dispatch({ type: 'VOTE_RESOLVED', payload });
        }
      } catch (err) {
        console.error('WS parse error:', err);
      }
    };

    ws.onclose = (e) => {
      dispatch({ type: 'DISCONNECTED' });
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);

      if (e.code === 4401 || e.code === 4403) {
        dispatch({
          type: 'ACTION_REJECTED',
          payload: { reason: 'Unauthorized room access. Redirecting...' }
        });
        return;
      }

      // Exponential backoff reconnect: 1, 2, 4, 8 up to 15s
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 15000);
      reconnectAttempts.current += 1;
      setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [tripId, token]);

  useEffect(() => {
    connect();
    return () => {
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  // Operational Dispatchers
  const moveItem = useCallback((itemId, seenVersion, dayIndex, startTime, endTime) => {
    // Optimistic UI update
    dispatch({
      type: 'OPTIMISTIC_MOVE',
      payload: { itemId, dayIndex, startTime, endTime }
    });
    // Send mutation over WebSocket
    sendEvent('trip.board.move', {
      itemId,
      seenVersion,
      dayIndex,
      startTime,
      endTime
    });
  }, [sendEvent]);

  const pinVenue = useCallback((venueId, dayIndex, startTime, endTime) => {
    sendEvent('trip.board.pin', { venueId, dayIndex, startTime, endTime });
  }, [sendEvent]);

  const lockItem = useCallback((itemId) => {
    sendEvent('trip.board.lock', { itemId });
  }, [sendEvent]);

  const unlockItem = useCallback((itemId) => {
    sendEvent('trip.board.unlock', { itemId });
  }, [sendEvent]);

  const removeItem = useCallback((itemId) => {
    sendEvent('trip.board.remove', { itemId });
  }, [sendEvent]);

  const sendChatMessage = useCallback((content) => {
    sendEvent('trip.chat.message', { content });
  }, [sendEvent]);

  const sendTyping = useCallback(() => {
    sendEvent('trip.chat.typing', {});
  }, [sendEvent]);

  const sendReaction = useCallback((messageId, emoji) => {
    sendEvent('trip.chat.reaction', { messageId, emoji });
  }, [sendEvent]);

  const openVote = useCallback((itemIds, durationSeconds = 30) => {
    sendEvent('trip.vote.open', { itemIds, durationSeconds });
  }, [sendEvent]);

  const castVote = useCallback((itemId) => {
    sendEvent('trip.vote.cast', { itemId });
  }, [sendEvent]);

  const dismissToast = useCallback(() => {
    dispatch({ type: 'DISMISS_TOAST' });
  }, []);

  return {
    ...state,
    moveItem,
    pinVenue,
    lockItem,
    unlockItem,
    removeItem,
    sendChatMessage,
    sendTyping,
    sendReaction,
    openVote,
    castVote,
    dismissToast,
  };
}
