# FOXITE PROMPT 2 - Additional Models and Enums

# Additional Ticket Statuses
class TicketStatus(str):
    NEW = "new"
    OPEN = "open"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"

# Task Statuses  
class TaskStatus(str):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"

# Comment Types
class CommentType(str):
    INTERNAL_NOTE = "internal_note"  # Staff-only
    PUBLIC_REPLY = "public_reply"    # Visible to end users

# Session Visibility
class SessionVisibility(str):
    INTERNAL = "internal"
    CLIENT_VISIBLE = "client_visible"

# ==================== NEW MODELS FOR PROMPT 2 ====================

# Ticket Comment Model
class TicketComment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str
    organization_id: str
    author_id: str
    author_type: str  # "staff" or "end_user"
    comment_type: str  # internal_note or public_reply
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TicketCommentCreate(BaseModel):
    comment_type: str
    content: str

# Ticket Attachment Model
class TicketAttachment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str
    organization_id: str
    uploaded_by: str
    filename: str
    file_url: str  # S3/storage URL
    file_type: str  # mime type
    file_size: int  # bytes
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TicketAttachmentCreate(BaseModel):
    filename: str
    file_url: str
    file_type: str
    file_size: int

# Session (Time Tracking) Model
class Session(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    staff_id: str
    ticket_id: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None  # Auto-calculated
    notes: Optional[str] = None
    visible_to_client: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SessionCreate(BaseModel):
    ticket_id: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    notes: Optional[str] = None
    visible_to_client: bool = False

class SessionUpdate(BaseModel):
    end_time: Optional[datetime] = None
    notes: Optional[str] = None
    visible_to_client: Optional[bool] = None

# SLA Policy Model
class SLAPolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    name: str
    priority_level: str  # low, medium, high, urgent
    first_response_minutes: int  # Minutes to first response
    resolution_minutes: int  # Minutes to resolution
    business_hours_id: Optional[str] = None
    escalation_rules: dict = {}  # JSON for escalation logic
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SLAPolicyCreate(BaseModel):
    name: str
    priority_level: str
    first_response_minutes: int
    resolution_minutes: int
    business_hours_id: Optional[str] = None
    escalation_rules: dict = {}

# Business Hours Model
class BusinessHours(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    name: str
    timezone: str
    working_days: List[int] = [1, 2, 3, 4, 5]  # Monday-Friday (1-7)
    working_hours_start: str = "09:00"  # HH:MM format
    working_hours_end: str = "17:00"
    holidays: List[str] = []  # List of dates "YYYY-MM-DD"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BusinessHoursCreate(BaseModel):
    name: str
    timezone: str = "UTC"
    working_days: List[int] = [1, 2, 3, 4, 5]
    working_hours_start: str = "09:00"
    working_hours_end: str = "17:00"
    holidays: List[str] = []

# Saved Filter Model
class SavedFilter(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    user_id: str
    name: str
    entity_type: str  # "tickets", "tasks", "sessions"
    filter_config: dict  # JSON with filter parameters
    is_shared: bool = False  # Share with org
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SavedFilterCreate(BaseModel):
    name: str
    entity_type: str
    filter_config: dict
    is_shared: bool = False
