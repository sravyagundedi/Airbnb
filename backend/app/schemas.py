from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, EmailStr, Field, field_validator
import datetime

# Valid dietary tags vocabulary as specified in Step 5 and Step 20
TAG_VOCABULARY = frozenset({"vegetarian", "vegan", "halal", "gluten-free"})
VALID_CATEGORIES = frozenset({"dinner", "lunch", "breakfast", "activity", "lodging", "nightlife", "transit"})
VALID_ROLES = frozenset({"viewer", "planner", "leader", "admin"})


# --- Auth Schemas ---
class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    display_name: str = Field(..., min_length=1, max_length=100)
    role: Optional[str] = "planner"
    budget_ceiling: Optional[int] = Field(default=150, ge=0)
    dietary_tags: Optional[List[str]] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean.split("@")[-1] or len(clean) < 5:
            raise ValueError("Invalid email format. Must contain '@' and domain (e.g. user@domain.com or user@warroom.local)")
        return clean

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in VALID_ROLES:
            raise ValueError(f"Role must be one of {sorted(VALID_ROLES)}")
        return v

    @field_validator("dietary_tags")
    @classmethod
    def validate_dietary_tags(cls, v):
        for tag in v:
            if tag not in TAG_VOCABULARY:
                raise ValueError(f"Invalid dietary tag '{tag}'. Valid tags: {sorted(TAG_VOCABULARY)}")
        return v


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if "@" not in clean:
            raise ValueError("Invalid email format. Must contain '@'")
        return clean


class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    budget_ceiling: Optional[int] = Field(None, ge=0)
    dietary_tags: Optional[List[str]] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=8)

    @field_validator("dietary_tags")
    @classmethod
    def validate_dietary_tags(cls, v):
        if v is not None:
            for tag in v:
                if tag not in TAG_VOCABULARY:
                    raise ValueError(f"Invalid dietary tag '{tag}'. Valid tags: {sorted(TAG_VOCABULARY)}")
        return v


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    budget_ceiling: int
    dietary_tags: List[str]
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


# --- Trip Schemas ---
class TripCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    destination: str = Field(default="Lisbon", min_length=1)
    country: Optional[str] = Field(default=None)
    currency: Optional[str] = Field(default=None)
    max_participants: int = Field(default=10, ge=2, le=50)


class TripJoinRequest(BaseModel):
    inviteCode: str = Field(..., min_length=4, max_length=20)


class TripMemberResponse(BaseModel):
    user_id: int
    display_name: str
    email: str
    role: str
    joined_at: datetime.datetime


class TripResponse(BaseModel):
    id: int
    title: str
    destination: str
    country: str = "Portugal"
    currency: str = "EUR"
    currency_symbol: str = "€"
    invite_code: str
    max_participants: int
    creator_id: int
    created_at: datetime.datetime
    members_count: Optional[int] = 1


# --- Venue Schemas ---
class HoursDict(BaseModel):
    open: str
    close: str


class CoordinatesDict(BaseModel):
    lat: float
    lng: float


class VenueResponse(BaseModel):
    venueId: str
    name: str
    category: str
    destination: str = "Lisbon"
    country: str = "Portugal"
    currency: str = "EUR"
    pricePerPerson: float
    dietaryTags: List[str]
    hours: HoursDict
    coordinates: CoordinatesDict
    rating: float
    description: str


class AdminVenueRow(BaseModel):
    venueId: str
    name: str = Field(..., min_length=1)
    category: str
    pricePerPerson: float = Field(..., gt=0)
    dietaryTags: List[str] = Field(default_factory=list)
    hours: HoursDict
    coordinates: CoordinatesDict
    rating: float = Field(..., ge=0.0, le=5.0)
    description: Optional[str] = ""

    @field_validator("category")
    @classmethod
    def check_category(cls, v):
        if v.lower() not in VALID_CATEGORIES:
            raise ValueError(f"Category '{v}' invalid. Must be one of {sorted(VALID_CATEGORIES)}")
        return v.lower()

    @field_validator("dietaryTags")
    @classmethod
    def check_tags(cls, v):
        for tag in v:
            if tag.lower() not in TAG_VOCABULARY:
                raise ValueError(f"Invalid tag '{tag}'. Allowed: {sorted(TAG_VOCABULARY)}")
        return [t.lower() for t in v]

    @field_validator("coordinates")
    @classmethod
    def check_coords(cls, v):
        if not (-90.0 <= v.lat <= 90.0):
            raise ValueError(f"lat {v.lat} out of range [-90, 90]")
        if not (-180.0 <= v.lng <= 180.0):
            raise ValueError(f"lng {v.lng} out of range [-180, 180]")
        return v

    @field_validator("hours")
    @classmethod
    def check_hours(cls, v):
        try:
            oh, om = map(int, v.open.split(":"))
            ch, cm = map(int, v.close.split(":"))
            open_min = oh * 60 + om
            close_min = ch * 60 + cm
            if not (0 <= open_min <= 1440 and 0 <= close_min <= 1440):
                raise ValueError("Hours out of 24h clock bounds")
            if close_min <= open_min:
                raise ValueError("close hour must be strictly greater than open hour")
        except Exception as e:
            raise ValueError(f"Invalid hours format (HH:MM expected): {e}")
        return v


# --- AI Concierge Schemas ---
class AIAskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    anchor_venue_id: Optional[str] = None
    slot_start: Optional[str] = None  # "19:00"
    slot_end: Optional[str] = None    # "21:00"


class AIAskResponse(BaseModel):
    answer: str
    suggestedVenueId: Optional[str] = None
    sourceEvents: List[str] = Field(default_factory=list)
    generatedAt: str
    latencyMs: Optional[float] = None


# --- Analytics Schemas ---
class TripAnalytics(BaseModel):
    tripId: int
    planningDurationMinutes: float
    peakConcurrentPlanners: int
    aiQuestionsCount: int
    conflictsFlagged: int
    conflictsResolved: int
    perPersonBreakdown: Dict[int, float]


# --- Password Recovery Schemas ---
class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)


class ResetPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    reset_code: str = Field(..., min_length=4, max_length=10)
    new_password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


# --- Expense & Settlement Schemas ---
class ExpenseCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    amount: float = Field(..., gt=0, description="Amount in currency units")
    category: Optional[str] = "dining"
    paid_by_user_id: Optional[int] = None
    split_user_ids: Optional[List[int]] = None


class ExpenseShareResponse(BaseModel):
    user_id: int
    user_name: str
    share_amount: float
    is_settled: bool


class ExpenseResponse(BaseModel):
    id: int
    trip_id: int
    title: str
    amount: float
    currency: str
    category: str
    paid_by_user_id: int
    paid_by_name: str
    created_at: datetime.datetime
    shares: List[ExpenseShareResponse] = Field(default_factory=list)


class SettlementItem(BaseModel):
    from_user_id: int
    from_user_name: str
    to_user_id: int
    to_user_name: str
    amount: float
    currency: str


class ExpenseSummaryResponse(BaseModel):
    trip_id: int
    total_expenses: float
    currency: str
    category_totals: Dict[str, float]
    expenses: List[ExpenseResponse]
    settlement_plan: List[SettlementItem]


# --- Pre-Trip Budget Estimator Schemas ---
class EstimateBudgetRequest(BaseModel):
    destination: str = "Lisbon"
    country: Optional[str] = "Portugal"
    duration_days: int = Field(default=3, ge=1, le=90)
    travelers_count: int = Field(default=2, ge=1, le=50)
    travel_style: str = Field(default="balanced", description="budget, balanced, or luxury")
    currency: Optional[str] = "EUR"


class DailyCostBreakdown(BaseModel):
    lodging: float
    food: float
    activities: float
    transit: float
    buffer: float


class EstimateBudgetResponse(BaseModel):
    destination: str
    country: str
    currency: str
    currency_symbol: str
    duration_days: int
    travelers_count: int
    travel_style: str
    daily_per_person: DailyCostBreakdown
    total_trip_cost: float
    per_person_total: float
    category_totals: Dict[str, float]
    recommendations: List[str]


# --- Saved Venues Schemas ---
class SavedVenueResponse(BaseModel):
    id: int
    venue_id: str
    name: str
    category: str
    price_per_person: float
    rating: float
    dietary_tags: List[str]
    notes: Optional[str] = None
    saved_at: datetime.datetime


# --- Item Discussion Comment Schemas ---
class ItemCommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class ItemCommentResponse(BaseModel):
    id: int
    item_id: int
    trip_id: int
    user_id: int
    user_name: str
    content: str
    created_at: datetime.datetime

