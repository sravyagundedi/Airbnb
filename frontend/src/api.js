const API_BASE = '/api/v1';

export const authStorage = {
  getAccessToken: () => localStorage.getItem('warroom_access_token'),
  getRefreshToken: () => localStorage.getItem('warroom_refresh_token'),
  getUser: () => {
    try {
      const u = localStorage.getItem('warroom_user');
      return u ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  },
  saveTokens: (access, refresh, user) => {
    localStorage.setItem('warroom_access_token', access);
    localStorage.setItem('warroom_refresh_token', refresh);
    if (user) localStorage.setItem('warroom_user', JSON.stringify(user));
  },
  clear: () => {
    localStorage.removeItem('warroom_access_token');
    localStorage.removeItem('warroom_refresh_token');
    localStorage.removeItem('warroom_user');
  }
};

async function request(endpoint, options = {}) {
  const token = authStorage.getAccessToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });

  if (response.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
    // Attempt token refresh
    const rToken = authStorage.getRefreshToken();
    if (rToken) {
      try {
        const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: rToken })
        });
        if (refreshRes.ok) {
          const tokens = await refreshRes.json();
          authStorage.saveTokens(tokens.access_token, tokens.refresh_token, authStorage.getUser());
          headers['Authorization'] = `Bearer ${tokens.access_token}`;
          return fetch(`${API_BASE}${endpoint}`, { ...options, headers }).then(r => r.json());
        }
      } catch (err) {
        authStorage.clear();
      }
    }
    authStorage.clear();
    window.location.reload();
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail?.message || data.detail || response.statusText || 'Request failed');
  }
  return data;
}

export const api = {
  // Auth
  register: (payload) => request('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  login: (email, password) => request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  getMe: () => request('/auth/me'),
  getDashboard: () => request('/me/dashboard'),

  // Trips
  createTrip: (title, destination = 'Lisbon', country = 'Portugal', currency = 'EUR', maxParticipants = 10) =>
    request('/trips', {
      method: 'POST',
      body: JSON.stringify({
        title,
        destination,
        country,
        currency,
        max_participants: maxParticipants
      })
    }),
  joinTrip: (inviteCode) => request('/trips/join', { method: 'POST', body: JSON.stringify({ inviteCode }) }),
  getMyTrips: () => request('/trips'),
  getTripMembers: (tripId) => request(`/trips/${tripId}/members`),
  getTripAnalytics: (tripId) => request(`/trips/${tripId}/analytics`),

  // Global Destinations & Venues
  getCountries: () => request('/destinations/countries'),
  getVenues: (destination = 'Lisbon', near, radiusKm, category, country) => {
    const params = new URLSearchParams();
    if (near) params.set('near', near);
    if (radiusKm) params.set('radiusKm', radiusKm);
    if (category) params.set('category', category);
    if (country) params.set('country', country);
    return request(`/destinations/${destination}/venues?${params.toString()}`);
  },
  getRecommendations: (userId, topK = 6) => request(`/recommendations?top_k=${topK}`),

  // AI Concierge
  askAI: (tripId, question, anchorVenueId = null) =>
    request(`/trips/${tripId}/ai/ask`, {
      method: 'POST',
      body: JSON.stringify({ question, anchor_venue_id: anchorVenueId })
    }),

  // Admin
  uploadVenues: (destination, rows) =>
    request(`/admin/destinations/${destination}/venues`, { method: 'POST', body: JSON.stringify(rows) }),
  triggerRetrain: () => request('/admin/reco/retrain', { method: 'POST' })
};
