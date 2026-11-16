import React, { useState, useEffect } from 'react';
import ItemCard from './ItemCard';
import { Plus, AlertTriangle, Vote, MapPin, Search, Heart, Sparkles, Bookmark } from 'lucide-react';
import { api } from '../api';

export default function TripCanvas({
  items,
  conflicts,
  userRole,
  isLeader,
  onMove,
  onPin,
  onLock,
  onUnlock,
  onRemove,
  onOpenVote,
  onOpenThread,
  venuesCatalog = [],
  currencySymbol = '€',
  destination = 'Lisbon'
}) {
  const [showCatalogModal, setShowCatalogModal] = useState(false);
  const [selectedDayForPin, setSelectedDayForPin] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [catalogTab, setCatalogTab] = useState('catalog'); // 'catalog' | 'saved'
  const [savedVenues, setSavedVenues] = useState([]);
  const [savedIds, setSavedIds] = useState(new Set());

  const days = [1, 2, 3];

  useEffect(() => {
    if (showCatalogModal) {
      loadSavedVenues();
    }
  }, [showCatalogModal]);

  const loadSavedVenues = async () => {
    try {
      const data = await api.getSavedVenues();
      setSavedVenues(data || []);
      setSavedIds(new Set((data || []).map(sv => sv.venue_id)));
    } catch (err) {
      console.error('Failed to load saved venues:', err);
    }
  };

  const handleToggleSave = async (venueId, e) => {
    e.stopPropagation();
    try {
      if (savedIds.has(venueId)) {
        await api.unsaveVenue(venueId);
        setSavedIds(prev => {
          const next = new Set(prev);
          next.delete(venueId);
          return next;
        });
        setSavedVenues(prev => prev.filter(v => v.venue_id !== venueId));
      } else {
        const res = await api.saveVenue(venueId);
        setSavedIds(prev => new Set(prev).add(venueId));
        setSavedVenues(prev => [res, ...prev]);
      }
    } catch (err) {
      console.error('Toggle save failed:', err);
    }
  };


  const getItemsForDay = (dayIndex) => {
    return items
      .filter(i => Number(i.dayIndex) === Number(dayIndex))
      .sort((a, b) => (a.startMin || 0) - (b.startMin || 0));
  };

  const getConflictsForDay = (dayIndex) => {
    return conflicts.filter(c => c.type === 'overlap' && Number(c.dayIndex) === Number(dayIndex));
  };

  const filteredVenues = venuesCatalog.filter(v => {
    const matchCat = selectedCategory === 'all' || v.category === selectedCategory;
    const matchSearch = !searchQuery || v.name.toLowerCase().includes(searchQuery.toLowerCase()) || v.category.toLowerCase().includes(searchQuery.toLowerCase());
    return matchCat && matchSearch;
  });

  const handleQuickPin = (venue) => {
    // Default times based on category
    let sTime = '12:30';
    let eTime = '14:00';
    if (venue.category === 'breakfast') { sTime = '09:00'; eTime = '10:15'; }
    else if (venue.category === 'dinner') { sTime = '19:30'; eTime = '21:30'; }
    else if (venue.category === 'nightlife') { sTime = '22:00'; eTime = '23:45'; }
    else if (venue.category === 'activity') { sTime = '10:30'; eTime = '13:00'; }

    onPin(venue.venueId, selectedDayForPin, sTime, eTime);
    setShowCatalogModal(false);
  };

  return (
    <div style={{ flex: 1, padding: '20px', overflowY: 'auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 800 }}>Itinerary Canvas</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Real-time collaborative group schedule. Optimistic drag & drop with optimistic concurrency conflict resolution.
          </p>
        </div>

        {userRole !== 'viewer' && (
          <button
            onClick={() => { setSelectedDayForPin(1); setShowCatalogModal(true); }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'var(--primary)',
              color: '#FFFFFF',
              padding: '8px 16px',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '13px'
            }}
          >
            <Plus size={16} /> Pin Venue
          </button>
        )}
      </div>

      {/* 3 Day Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', minHeight: '600px' }}>
        {days.map(day => {
          const dayItems = getItemsForDay(day);
          const dayConflicts = getConflictsForDay(day);
          const hasOverlap = dayConflicts.length > 0;

          return (
            <div
              key={day}
              style={{
                background: '#F1F3F5',
                borderRadius: '16px',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column'
              }}
            >
              {/* Day Header */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                <div>
                  <span style={{ fontSize: '16px', fontWeight: 800, color: '#1A1A1A' }}>Day {day}</span>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block' }}>
                    {dayItems.length} activities planned
                  </span>
                </div>

                {userRole !== 'viewer' && (
                  <button
                    onClick={() => { setSelectedDayForPin(day); setShowCatalogModal(true); }}
                    style={{ background: '#FFFFFF', padding: '6px', borderRadius: '6px', color: '#444' }}
                    title={`Add Activity to Day ${day}`}
                  >
                    <Plus size={16} />
                  </button>
                )}
              </div>

              {/* Conflict banner if overlap */}
              {hasOverlap && (
                <div style={{
                  background: '#FEF2F2',
                  border: '1px solid #FCA5A5',
                  padding: '10px 12px',
                  borderRadius: '10px',
                  marginBottom: '14px',
                  fontSize: '12px',
                  color: '#991B1B'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, marginBottom: '4px' }}>
                    <AlertTriangle size={15} /> Time Overlap Detected
                  </div>
                  <div>Two items share an overlapping time slot on Day {day}.</div>
                  {userRole !== 'viewer' && (
                    <button
                      onClick={() => {
                        const itemIds = dayConflicts[0].itemIds;
                        onOpenVote(itemIds, 30);
                      }}
                      style={{
                        marginTop: '8px',
                        background: '#DC2626',
                        color: '#FFF',
                        padding: '4px 10px',
                        borderRadius: '6px',
                        fontWeight: 700,
                        fontSize: '11px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      <Vote size={13} /> Open Contested Slot Vote
                    </button>
                  )}
                </div>
              )}

              {/* Items List */}
              <div style={{ flex: 1, minHeight: '300px' }}>
                {dayItems.length === 0 ? (
                  <div style={{
                    border: '2px dashed #D0D5DD',
                    borderRadius: '12px',
                    height: '180px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--text-muted)',
                    fontSize: '13px',
                    textAlign: 'center',
                    padding: '16px'
                  }}>
                    <MapPin size={24} style={{ marginBottom: '8px', opacity: 0.5 }} />
                    <span>No activities pinned for Day {day}.</span>
                    {userRole !== 'viewer' && (
                      <button
                        onClick={() => { setSelectedDayForPin(day); setShowCatalogModal(true); }}
                        style={{ marginTop: '8px', color: 'var(--primary)', fontWeight: 700, fontSize: '12px' }}
                      >
                        + Pin Nearby Venue
                      </button>
                    )}
                  </div>
                ) : (
                  dayItems.map(item => (
                    <ItemCard
                      key={item.id}
                      item={item}
                      userRole={userRole}
                      isLeader={isLeader}
                      onMove={onMove}
                      onLock={onLock}
                      onUnlock={onUnlock}
                      onRemove={onRemove}
                      onOpenVote={onOpenVote}
                      onOpenThread={onOpenThread}
                      hasConflict={dayConflicts.some(c => c.itemIds?.includes(item.id))}
                      currencySymbol={currencySymbol}
                    />

                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Catalog Modal */}
      {showCatalogModal && (
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
            width: '600px',
            maxHeight: '80vh',
            borderRadius: '16px',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 20px 40px rgba(0,0,0,0.2)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 800 }}>Pin {destination} Venue to Day {selectedDayForPin}</h3>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Explore local restaurants, cultural sights, and activities in {destination}.</p>
              </div>
              <button onClick={() => setShowCatalogModal(false)} style={{ fontSize: '18px', color: '#888' }}>✕</button>
            </div>

            {/* Catalog vs Saved Places Tabs */}
            <div style={{ display: 'flex', background: '#F1F3F5', borderRadius: '8px', padding: '3px', marginBottom: '14px' }}>
              <button
                onClick={() => setCatalogTab('catalog')}
                style={{
                  flex: 1,
                  padding: '6px',
                  borderRadius: '6px',
                  border: 'none',
                  fontSize: '12px',
                  fontWeight: 700,
                  background: catalogTab === 'catalog' ? '#FFF' : 'transparent',
                  color: catalogTab === 'catalog' ? 'var(--text-main)' : 'var(--text-muted)',
                  cursor: 'pointer'
                }}
              >
                Explore Catalog ({venuesCatalog.length})
              </button>
              <button
                onClick={() => setCatalogTab('saved')}
                style={{
                  flex: 1,
                  padding: '6px',
                  borderRadius: '6px',
                  border: 'none',
                  fontSize: '12px',
                  fontWeight: 700,
                  background: catalogTab === 'saved' ? '#FFF' : 'transparent',
                  color: catalogTab === 'saved' ? 'var(--primary)' : 'var(--text-muted)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '4px'
                }}
              >
                <Heart size={13} fill={catalogTab === 'saved' ? 'var(--primary)' : 'none'} />
                Saved Wishlist ({savedVenues.length})
              </button>
            </div>

            {/* Filters */}
            <div style={{ display: 'flex', gap: '10px', marginBottom: '14px' }}>
              <div style={{ flex: 1, position: 'relative' }}>
                <Search size={16} style={{ position: 'absolute', left: '10px', top: '10px', color: '#999' }} />
                <input
                  type="text"
                  placeholder="Search venues..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ width: '100%', padding: '8px 8px 8px 34px', borderRadius: '8px', border: '1px solid var(--border)' }}
                />
              </div>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                style={{ padding: '8px', borderRadius: '8px', border: '1px solid var(--border)', textTransform: 'capitalize' }}
              >
                <option value="all">All Categories</option>
                <option value="dinner">Dinner</option>
                <option value="lunch">Lunch</option>
                <option value="breakfast">Breakfast</option>
                <option value="activity">Activity</option>
                <option value="nightlife">Nightlife</option>
              </select>
            </div>

            {/* Venues scroll list */}
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px', paddingRight: '4px' }}>
              {(catalogTab === 'catalog' ? filteredVenues : savedVenues).length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
                  {catalogTab === 'saved' ? 'No saved places in your wishlist yet. Click the heart icon on any venue to save it!' : 'No matching venues found.'}
                </div>
              ) : (
                (catalogTab === 'catalog' ? filteredVenues : savedVenues).map(v => {
                  const vid = v.venueId || v.venue_id;
                  const vPrice = v.pricePerPerson ?? v.price_per_person ?? 0;
                  const vTags = v.dietaryTags || v.dietary_tags || [];
                  const isSaved = savedIds.has(vid);

                  return (
                    <div
                      key={vid}
                      style={{
                        padding: '12px',
                        borderRadius: '10px',
                        border: '1px solid var(--border)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between'
                      }}
                    >
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 700, fontSize: '14px' }}>{v.name}</span>
                          <span style={{ fontSize: '11px', background: '#F0F2F5', padding: '1px 6px', borderRadius: '4px', textTransform: 'capitalize' }}>
                            {v.category}
                          </span>
                          <span style={{ fontSize: '11px', color: '#F59E0B', fontWeight: 700 }}>★ {v.rating}</span>
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {(v.description || 'Authentic local venue').slice(0, 85)}...
                        </div>
                        <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
                          {vTags.map(tag => (
                            <span key={tag} style={{ fontSize: '10px', background: '#DCFCE7', color: '#166534', padding: '1px 5px', borderRadius: '4px' }}>
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <button
                            onClick={(e) => handleToggleSave(vid, e)}
                            style={{
                              background: 'none',
                              border: 'none',
                              cursor: 'pointer',
                              color: isSaved ? '#EF4444' : '#9CA3AF',
                              padding: '2px'
                            }}
                            title={isSaved ? 'Remove from wishlist' : 'Save to wishlist'}
                          >
                            <Heart size={16} fill={isSaved ? '#EF4444' : 'none'} />
                          </button>
                          <span style={{ fontWeight: 700, color: '#10B981', fontSize: '14px' }}>
                            {currencySymbol}
                            {currencySymbol === '¥' || currencySymbol === '₩'
                              ? Math.round(Number(vPrice)).toLocaleString()
                              : Number(vPrice).toFixed(2)}
                          </span>
                        </div>
                        <button
                          onClick={() => handleQuickPin({ ...v, venueId: vid })}
                          style={{
                            background: 'var(--primary)',
                            color: '#FFF',
                            padding: '4px 10px',
                            borderRadius: '6px',
                            fontSize: '12px',
                            fontWeight: 700
                          }}
                        >
                          Pin
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
