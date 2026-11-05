import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Time, Text,
    ForeignKey, CheckConstraint, Index, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="planner")
    budget_ceiling = Column(Integer, default=150, nullable=False)
    dietary_tags = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("role in ('viewer','planner','leader','admin')", name="chk_user_role"),
    )

    memberships = relationship("TripMember", back_populates="user", cascade="all, delete-orphan")


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    destination = Column(String(100), default="Lisbon", nullable=False, index=True)
    invite_code = Column(String(20), unique=True, index=True, nullable=False)
    max_participants = Column(Integer, default=10, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    members = relationship("TripMember", back_populates="trip", cascade="all, delete-orphan")
    items = relationship("ItineraryItem", back_populates="trip", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="trip", cascade="all, delete-orphan")


class TripMember(Base):
    __tablename__ = "trip_members"

    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(20), nullable=False, default="planner")
    joined_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("role in ('viewer','planner','leader')", name="chk_trip_member_role"),
    )

    trip = relationship("Trip", back_populates="members")
    user = relationship("User", back_populates="memberships")


class VenueMetadata(Base):
    __tablename__ = "venue_metadata"

    id = Column(String(50), primary_key=True)  # e.g., 'v_3391'
    name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)
    price_per_person = Column(Float, nullable=False)
    destination = Column(String(100), default="Lisbon", nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    rating = Column(Float, default=4.0, nullable=False)
    open_time = Column(String(10), default="09:00", nullable=False)
    close_time = Column(String(10), default="22:00", nullable=False)
    open_min = Column(Integer, default=540, nullable=False)
    close_min = Column(Integer, default=1320, nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_venue_dest_lat_lng", "destination", "lat", "lng"),
    )

    dietary_tags = relationship("VenueDietaryTag", back_populates="venue", cascade="all, delete-orphan")


class VenueDietaryTag(Base):
    __tablename__ = "venue_dietary_tags"

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(String(50), ForeignKey("venue_metadata.id", ondelete="CASCADE"), index=True, nullable=False)
    tag = Column(String(50), index=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("venue_id", "tag", name="uq_venue_dietary_tag"),
    )

    venue = relationship("VenueMetadata", back_populates="dietary_tags")


class ItineraryItem(Base):
    __tablename__ = "itinerary_items"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), index=True, nullable=False)
    venue_id = Column(String(50), ForeignKey("venue_metadata.id"), nullable=False)
    day_index = Column(Integer, default=1, nullable=False)
    start_time = Column(String(10), nullable=False, default="12:00")
    end_time = Column(String(10), nullable=False, default="13:30")
    start_min = Column(Integer, nullable=False, default=720)
    end_min = Column(Integer, nullable=False, default=810)
    lifecycle_stage = Column(String(20), default="drafting", nullable=False)
    pinned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    position_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_item_trip_day", "trip_id", "day_index"),
        CheckConstraint("lifecycle_stage in ('drafting','voting','locked')", name="chk_lifecycle_stage"),
        CheckConstraint("end_min > start_min", name="chk_item_time_range"),
    )

    trip = relationship("Trip", back_populates="items")
    venue = relationship("VenueMetadata")
    pinned_by = relationship("User")
    votes = relationship("ItemVote", back_populates="item", cascade="all, delete-orphan")


class ItemVote(Base):
    __tablename__ = "item_votes"

    item_id = Column(Integer, ForeignKey("itinerary_items.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    choice = Column(String(20), default="approve", nullable=False)
    cast_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    item = relationship("ItineraryItem", back_populates="votes")
    user = relationship("User")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_name = Column(String(100), nullable=False, default="System")
    message_type = Column(String(30), default="chat", nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    trip = relationship("Trip", back_populates="messages")


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    venue_id = Column(String(50), ForeignKey("venue_metadata.id"), index=True, nullable=False)
    interaction_type = Column(String(50), default="like", nullable=False)
    weight = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class EventLog(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, index=True, nullable=False)
    user_id = Column(Integer, nullable=True)
    type = Column(String(100), index=True, nullable=False)
    payload = Column(JSON, default=dict, nullable=False)
    ts = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
