from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
import jwt
import resend
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', 1440))

# Email Configuration
resend.api_key = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app
app = FastAPI(title="FOXITE API")
api_router = APIRouter(prefix="/api")

# ==================== PLAN DEFINITIONS ====================

PLAN_FEATURES = {
    "CORE": {
        "name": "CORE",
        "price": 25,
        "currency": "USD",
        "max_staff_users": 3,
        "features": {
            "tickets": True,
            "end_users": True,
            "tasks": True,
            "devices_inventory": True,
            "licenses_inventory": False,
            "knowledge_base": True,
            "calendar": True,
            "email_notifications": True,
            "ai_features": False,
            "sla_management": "basic",
            "reports": "basic",
            "api_access": False,
            "end_user_portal_customization": False,
            "workflows": False,
            "saved_filters": False,
            "custom_dashboards": False,
            "audit_logs": False,
            "alerts_escalations": "basic"
        }
    },
    "PLUS": {
        "name": "PLUS",
        "price": 55,
        "currency": "USD",
        "max_staff_users": 10,
        "features": {
            "tickets": True,
            "end_users": True,
            "tasks": True,
            "devices_inventory": True,
            "licenses_inventory": True,
            "knowledge_base": True,
            "calendar": True,
            "email_notifications": True,
            "ai_features": "limited",
            "sla_management": "advanced",
            "reports": "advanced",
            "api_access": "read_only",
            "end_user_portal_customization": False,
            "workflows": True,
            "saved_filters": True,
            "custom_dashboards": False,
            "audit_logs": False,
            "alerts_escalations": "advanced"
        }
    },
    "PRIME": {
        "name": "PRIME",
        "price": 90,
        "currency": "USD",
        "max_staff_users": 999999,  # Unlimited
        "features": {
            "tickets": True,
            "end_users": True,
            "tasks": True,
            "devices_inventory": True,
            "licenses_inventory": True,
            "knowledge_base": True,
            "calendar": True,
            "email_notifications": True,
            "ai_features": "unlimited",
            "sla_management": "advanced",
            "reports": "advanced",
            "api_access": "full",
            "end_user_portal_customization": True,
            "workflows": True,
            "saved_filters": True,
            "custom_dashboards": True,
            "audit_logs": True,
            "alerts_escalations": "advanced"
        }
    }
}

# ==================== FEATURE GATING SYSTEM ====================

async def get_plan_limits(org_id: str) -> Dict[str, Any]:
    """Get plan limits and features for an organization"""
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    plan_id = org.get('plan', 'CORE')
    return PLAN_FEATURES.get(plan_id, PLAN_FEATURES["CORE"])

async def can_use_feature(org_id: str, feature_name: str) -> bool:
    """Check if organization can use a specific feature based on their plan"""
    try:
        plan_limits = await get_plan_limits(org_id)
        feature_value = plan_limits["features"].get(feature_name, False)
        
        # Handle boolean features
        if isinstance(feature_value, bool):
            return feature_value
        
        # Handle tiered features (basic, advanced, unlimited)
        if isinstance(feature_value, str):
            return feature_value in ["basic", "advanced", "unlimited", "limited", "read_only", "full"]
        
        return False
    except:
        return False

async def check_staff_limit(org_id: str) -> bool:
    """Check if organization can add more staff users"""
    plan_limits = await get_plan_limits(org_id)
    max_staff = plan_limits.get("max_staff_users", 3)
    
    current_staff = await db.staff_users.count_documents({
        "organization_id": org_id,
        "status": "active"
    })
    
    return current_staff < max_staff

# ==================== ENUMS ====================

class UserRole(str):
    OWNER = "owner"  # SaaS Owner
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    TECHNICIAN = "technician"
    CUSTOM = "custom"

class PlanType(str):
    CORE = "CORE"
    PLUS = "PLUS"
    PRIME = "PRIME"

class OrgStatus(str):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"

class SubscriptionStatus(str):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    TRIALING = "trialing"

class BillingCycle(str):
    MONTHLY = "monthly"
    YEARLY = "yearly"

class TicketStatus(str):
    NEW = "new"
    OPEN = "open"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    RESOLVED = "resolved"
    CLOSED = "closed"

class TicketPriority(str):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskStatus(str):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"

class Language(str):
    EN = "en"
    ES = "es"

class CommentType(str):
    INTERNAL_NOTE = "internal_note"  # Staff-only
    PUBLIC_REPLY = "public_reply"    # Visible to end users

class AuthorType(str):
    STAFF = "staff"
    END_USER = "end_user"

# ==================== MODELS ====================

# Auth Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    token: str
    user: dict

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

# Subscription Models
class Subscription(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    plan_id: str
    billing_cycle: str = BillingCycle.MONTHLY
    status: str = SubscriptionStatus.ACTIVE
    start_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    next_billing_date: Optional[datetime] = None
    discount_percent: float = 0.0
    override_price: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SubscriptionCreate(BaseModel):
    org_id: str
    plan_id: str
    billing_cycle: str = BillingCycle.MONTHLY
    discount_percent: float = 0.0
    override_price: Optional[float] = None

# Organization Models
class Organization(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    legal_name: Optional[str] = None
    country: str = "US"
    timezone: str = "UTC"
    language: str = Language.EN
    plan: str = PlanType.CORE
    status: str = OrgStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrganizationCreate(BaseModel):
    name: str
    legal_name: Optional[str] = None
    country: str = "US"
    timezone: str = "UTC"
    language: str = Language.EN
    plan: str = PlanType.CORE

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    plan: Optional[str] = None
    status: Optional[str] = None

# Staff User Models
class StaffUser(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: Optional[str] = None  # None for SaaS Owner
    name: str
    email: EmailStr
    role: str
    status: str = "active"
    is_owner: bool = False  # SaaS Owner flag
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StaffUserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str
    organization_id: Optional[str] = None

class StaffUserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None

# End User Models
class EndUser(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    client_company_id: str
    name: str
    email: EmailStr
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EndUserCreate(BaseModel):
    client_company_id: str
    name: str
    email: EmailStr

# Client Company Models
class ClientCompany(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    name: str
    country: str
    city: str
    contact_email: EmailStr
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ClientCompanyCreate(BaseModel):
    name: str
    country: str
    city: str
    contact_email: EmailStr

# Ticket Models
class Ticket(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    ticket_number: int  # Auto-increment per org
    title: str
    description: str
    status: str = TicketStatus.NEW
    priority: str = TicketPriority.MEDIUM
    category: Optional[str] = None
    requester_id: Optional[str] = None  # End User ID
    assigned_staff_id: Optional[str] = None
    client_company_id: Optional[str] = None
    device_id: Optional[str] = None  # Future: link to device inventory
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TicketCreate(BaseModel):
    title: str
    description: str
    priority: str = TicketPriority.MEDIUM
    category: Optional[str] = None
    requester_id: Optional[str] = None
    assigned_staff_id: Optional[str] = None
    client_company_id: Optional[str] = None
    device_id: Optional[str] = None

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_staff_id: Optional[str] = None

# Ticket Comment Models
class TicketComment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str
    organization_id: str
    author_id: str
    author_name: str  # Denormalized for display
    author_type: str  # "staff" or "end_user"
    comment_type: str  # "internal_note" or "public_reply"
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TicketCommentCreate(BaseModel):
    comment_type: str
    content: str

# Ticket Attachment Models
class TicketAttachment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str
    organization_id: str
    uploaded_by: str
    uploaded_by_name: str  # Denormalized
    filename: str
    file_url: str  # Placeholder URL (no actual storage yet)
    file_type: str  # mime type
    file_size: int  # bytes
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TicketAttachmentCreate(BaseModel):
    filename: str
    file_url: str
    file_type: str
    file_size: int

# Task Models
class Task(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    title: str
    description: str
    status: str = TaskStatus.TODO
    due_date: Optional[datetime] = None
    assigned_staff_id: Optional[str] = None
    ticket_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaskCreate(BaseModel):
    title: str
    description: str
    due_date: Optional[datetime] = None
    assigned_staff_id: Optional[str] = None
    ticket_id: Optional[str] = None

# Notification Models
class Notification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    user_id: str
    title: str
    message: str
    read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Audit Log Models
class AuditLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    user_id: str
    action: str
    entity_type: str
    entity_id: str
    details: dict = {}
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ==================== HELPER FUNCTIONS ====================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await db.staff_users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update last login
    await db.staff_users.update_one(
        {"id": user_id},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
    )
    
    return user

async def require_owner(current_user: dict = Depends(get_current_user)):
    """Require SaaS Owner role"""
    if not current_user.get('is_owner'):
        raise HTTPException(status_code=403, detail="SaaS Owner access required")
    return current_user

async def log_audit(organization_id: str, user_id: str, action: str, entity_type: str, entity_id: str, details: dict = {}):
    # Only log if organization has audit logs enabled
    if organization_id:
        has_audit = await can_use_feature(organization_id, "audit_logs")
        if not has_audit:
            return
    
    audit = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details
    )
    doc = audit.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    await db.audit_logs.insert_one(doc)

async def get_next_ticket_number(org_id: str) -> int:
    """Get next auto-increment ticket number for organization"""
    # Find the highest ticket number for this org
    highest = await db.tickets.find_one(
        {"organization_id": org_id},
        {"_id": 0, "ticket_number": 1},
        sort=[("ticket_number", -1)]
    )
    
    if highest and highest.get('ticket_number'):
        return highest['ticket_number'] + 1
    return 1  # First ticket

async def send_email_async(recipient: str, subject: str, html: str):
    """Send email asynchronously"""
    if not resend.api_key or resend.api_key == 're_placeholder_add_your_key':
        logging.warning("Resend API key not configured. Email not sent.")
        return {"status": "skipped", "message": "Email service not configured"}
    
    params = {
        "from": SENDER_EMAIL,
        "to": [recipient],
        "subject": subject,
        "html": html
    }
    
    try:
        email = await asyncio.to_thread(resend.Emails.send, params)
        return {"status": "success", "email_id": email.get("id")}
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
        return {"status": "error", "message": str(e)}

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=StaffUser)
async def register(user_data: StaffUserCreate):
    # Check if email exists
    existing = await db.staff_users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check staff limit for organization
    if user_data.organization_id:
        can_add = await check_staff_limit(user_data.organization_id)
        if not can_add:
            raise HTTPException(status_code=400, detail="Staff user limit reached for this plan")
        
        org = await db.organizations.find_one({"id": user_data.organization_id}, {"_id": 0})
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
    
    # Hash password
    hashed_pwd = hash_password(user_data.password)
    
    # Create user
    user = StaffUser(
        name=user_data.name,
        email=user_data.email,
        role=user_data.role,
        organization_id=user_data.organization_id,
        is_owner=user_data.organization_id is None and user_data.role == UserRole.OWNER
    )
    
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['password_hash'] = hashed_pwd
    
    await db.staff_users.insert_one(doc)
    return user

@api_router.post("/auth/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    user = await db.staff_users.find_one({"email": credentials.email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(credentials.password, user.get('password_hash', '')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.get('status') != 'active':
        raise HTTPException(status_code=403, detail="Account is disabled")
    
    # Create token
    token = create_access_token({"user_id": user['id']})
    
    # Remove password from response
    user.pop('password_hash', None)
    
    return LoginResponse(token=token, user=user)

@api_router.get("/auth/me", response_model=StaffUser)
async def get_me(current_user: dict = Depends(get_current_user)):
    current_user.pop('password_hash', None)
    return current_user

@api_router.post("/auth/password-reset-request")
async def request_password_reset(request: PasswordResetRequest):
    user = await db.staff_users.find_one({"email": request.email}, {"_id": 0})
    if not user:
        return {"message": "If email exists, reset link has been sent"}
    
    reset_token = create_access_token({
        "user_id": user['id'],
        "purpose": "password_reset",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    })
    
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
    
    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Password Reset Request</h2>
            <p>Click the link below to reset your password:</p>
            <a href="{reset_link}" style="background: #f97316; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password</a>
            <p>This link expires in 1 hour.</p>
            <p>If you didn't request this, please ignore this email.</p>
        </body>
    </html>
    """
    
    await send_email_async(request.email, "FOXITE - Password Reset Request", html)
    
    return {"message": "If email exists, reset link has been sent"}

@api_router.post("/auth/password-reset-confirm")
async def confirm_password_reset(request: PasswordResetConfirm):
    try:
        payload = decode_token(request.token)
        if payload.get('purpose') != 'password_reset':
            raise HTTPException(status_code=400, detail="Invalid token")
        
        user_id = payload.get('user_id')
        
        hashed_pwd = hash_password(request.new_password)
        result = await db.staff_users.update_one(
            {"id": user_id},
            {"$set": {"password_hash": hashed_pwd}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": "Password reset successful"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

# ==================== SAAS OWNER ROUTES ====================

@api_router.get("/owner/metrics")
async def get_owner_metrics(current_user: dict = Depends(require_owner)):
    """Get SaaS-level metrics for owner dashboard"""
    total_orgs = await db.organizations.count_documents({})
    active_orgs = await db.organizations.count_documents({"status": "active"})
    suspended_orgs = await db.organizations.count_documents({"status": "suspended"})
    total_staff = await db.staff_users.count_documents({"is_owner": False})
    total_tickets = await db.tickets.count_documents({})
    
    # Calculate MRR (Monthly Recurring Revenue) placeholder
    subscriptions = await db.subscriptions.find({"status": "active"}, {"_id": 0}).to_list(1000)
    mrr = 0
    for sub in subscriptions:
        plan_info = PLAN_FEATURES.get(sub.get('plan_id', 'CORE'), PLAN_FEATURES['CORE'])
        price = sub.get('override_price') or plan_info['price']
        discount = sub.get('discount_percent', 0)
        final_price = price * (1 - discount / 100)
        
        if sub.get('billing_cycle') == 'yearly':
            final_price = final_price / 12
        
        mrr += final_price
    
    # AI usage placeholder
    ai_usage = {
        "total_requests": 0,
        "organizations_using_ai": 0
    }
    
    # Storage usage placeholder
    storage_usage = {
        "total_gb": 0,
        "organizations": []
    }
    
    return {
        "organizations": {
            "total": total_orgs,
            "active": active_orgs,
            "suspended": suspended_orgs
        },
        "users": {
            "total_staff": total_staff
        },
        "tickets": {
            "total": total_tickets
        },
        "revenue": {
            "mrr": round(mrr, 2),
            "currency": "USD"
        },
        "ai_usage": ai_usage,
        "storage_usage": storage_usage
    }

@api_router.get("/owner/organizations")
async def list_all_organizations(current_user: dict = Depends(require_owner)):
    """List all organizations with subscription details"""
    orgs = await db.organizations.find({}, {"_id": 0}).to_list(1000)
    
    for org in orgs:
        if isinstance(org.get('created_at'), str):
            org['created_at'] = datetime.fromisoformat(org['created_at'])
        
        # Get subscription
        sub = await db.subscriptions.find_one({"org_id": org['id']}, {"_id": 0})
        org['subscription'] = sub
        
        # Get staff count
        staff_count = await db.staff_users.count_documents({
            "organization_id": org['id'],
            "status": "active"
        })
        org['staff_count'] = staff_count
        
        # Get plan limits
        plan_info = PLAN_FEATURES.get(org.get('plan', 'CORE'), PLAN_FEATURES['CORE'])
        org['plan_info'] = plan_info
    
    return orgs

@api_router.patch("/owner/organizations/{org_id}")
async def update_organization_as_owner(
    org_id: str,
    update_data: OrganizationUpdate,
    current_user: dict = Depends(require_owner)
):
    """SaaS Owner can update any organization"""
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if update_dict:
        await db.organizations.update_one({"id": org_id}, {"$set": update_dict})
        await log_audit("SYSTEM", current_user['id'], "UPDATE", "organization", org_id, update_dict)
    
    updated_org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    
    if isinstance(updated_org.get('created_at'), str):
        updated_org['created_at'] = datetime.fromisoformat(updated_org['created_at'])
    
    return updated_org

@api_router.get("/owner/plans")
async def get_all_plans(current_user: dict = Depends(require_owner)):
    """Get all available subscription plans"""
    return PLAN_FEATURES

# ==================== SUBSCRIPTION ROUTES ====================

@api_router.post("/subscriptions", response_model=Subscription)
async def create_subscription(sub_data: SubscriptionCreate, current_user: dict = Depends(require_owner)):
    """Create subscription for an organization (Owner only)"""
    org = await db.organizations.find_one({"id": sub_data.org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Check if subscription already exists
    existing = await db.subscriptions.find_one({"org_id": sub_data.org_id}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Subscription already exists for this organization")
    
    # Calculate next billing date
    start = datetime.now(timezone.utc)
    if sub_data.billing_cycle == BillingCycle.MONTHLY:
        next_billing = start + timedelta(days=30)
    else:
        next_billing = start + timedelta(days=365)
    
    subscription = Subscription(
        org_id=sub_data.org_id,
        plan_id=sub_data.plan_id,
        billing_cycle=sub_data.billing_cycle,
        start_date=start,
        next_billing_date=next_billing,
        discount_percent=sub_data.discount_percent,
        override_price=sub_data.override_price
    )
    
    doc = subscription.model_dump()
    doc['start_date'] = doc['start_date'].isoformat()
    doc['next_billing_date'] = doc['next_billing_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.subscriptions.insert_one(doc)
    await log_audit("SYSTEM", current_user['id'], "CREATE", "subscription", subscription.id)
    
    return subscription

@api_router.get("/subscriptions/{org_id}")
async def get_subscription(org_id: str, current_user: dict = Depends(get_current_user)):
    """Get subscription for an organization"""
    # Check permissions
    if not current_user.get('is_owner') and current_user.get('organization_id') != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    sub = await db.subscriptions.find_one({"org_id": org_id}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    if isinstance(sub.get('start_date'), str):
        sub['start_date'] = datetime.fromisoformat(sub['start_date'])
    if sub.get('next_billing_date') and isinstance(sub.get('next_billing_date'), str):
        sub['next_billing_date'] = datetime.fromisoformat(sub['next_billing_date'])
    if isinstance(sub.get('created_at'), str):
        sub['created_at'] = datetime.fromisoformat(sub['created_at'])
    
    return sub

# ==================== ORGANIZATION ROUTES ====================

@api_router.post("/organizations", response_model=Organization)
async def create_organization(org_data: OrganizationCreate, current_user: dict = Depends(require_owner)):
    """Create organization (SaaS Owner only)"""
    org = Organization(
        name=org_data.name,
        legal_name=org_data.legal_name,
        country=org_data.country,
        timezone=org_data.timezone,
        language=org_data.language,
        plan=org_data.plan
    )
    
    doc = org.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.organizations.insert_one(doc)
    await log_audit("SYSTEM", current_user['id'], "CREATE", "organization", org.id)
    
    return org

@api_router.get("/organizations", response_model=List[Organization])
async def list_organizations(current_user: dict = Depends(get_current_user)):
    """List organizations - Owner sees all, others see only their org"""
    if current_user.get('is_owner'):
        orgs = await db.organizations.find({}, {"_id": 0}).to_list(1000)
    else:
        org_id = current_user.get('organization_id')
        if not org_id:
            return []
        orgs = await db.organizations.find({"id": org_id}, {"_id": 0}).to_list(1)
    
    for org in orgs:
        if isinstance(org.get('created_at'), str):
            org['created_at'] = datetime.fromisoformat(org['created_at'])
    
    return orgs

@api_router.get("/organizations/{org_id}", response_model=Organization)
async def get_organization(org_id: str, current_user: dict = Depends(get_current_user)):
    """Get organization details"""
    if not current_user.get('is_owner') and current_user.get('organization_id') != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if isinstance(org.get('created_at'), str):
        org['created_at'] = datetime.fromisoformat(org['created_at'])
    
    return org

@api_router.get("/organizations/{org_id}/features")
async def get_organization_features(org_id: str, current_user: dict = Depends(get_current_user)):
    """Get available features for an organization based on their plan"""
    if not current_user.get('is_owner') and current_user.get('organization_id') != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    plan_limits = await get_plan_limits(org_id)
    return plan_limits

# ==================== STAFF USER ROUTES ====================

@api_router.get("/staff-users", response_model=List[StaffUser])
async def list_staff_users(current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    
    if current_user.get('is_platform_owner'):
        users = await db.staff_users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    else:
        users = await db.staff_users.find({"organization_id": org_id}, {"_id": 0, "password_hash": 0}).to_list(1000)
    
    for user in users:
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
        if user.get('last_login') and isinstance(user.get('last_login'), str):
            user['last_login'] = datetime.fromisoformat(user['last_login'])
    
    return users

@api_router.patch("/staff-users/{user_id}", response_model=StaffUser)
async def update_staff_user(user_id: str, update_data: StaffUserUpdate, current_user: dict = Depends(get_current_user)):
    user = await db.staff_users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not current_user.get('is_owner'):
        if current_user.get('organization_id') != user.get('organization_id'):
            raise HTTPException(status_code=403, detail="Access denied")
        if current_user.get('role') not in [UserRole.ADMIN]:
            raise HTTPException(status_code=403, detail="Only admins can update users")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if update_dict:
        await db.staff_users.update_one({"id": user_id}, {"$set": update_dict})
        await log_audit(user.get('organization_id', 'SYSTEM'), current_user['id'], "UPDATE", "staff_user", user_id)
    
    updated_user = await db.staff_users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    
    if isinstance(updated_user.get('created_at'), str):
        updated_user['created_at'] = datetime.fromisoformat(updated_user['created_at'])
    if updated_user.get('last_login') and isinstance(updated_user.get('last_login'), str):
        updated_user['last_login'] = datetime.fromisoformat(updated_user['last_login'])
    
    return updated_user

# ==================== CLIENT COMPANY ROUTES ====================

@api_router.post("/client-companies", response_model=ClientCompany)
async def create_client_company(company_data: ClientCompanyCreate, current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners cannot create client companies directly")
    
    company = ClientCompany(
        organization_id=org_id,
        name=company_data.name,
        country=company_data.country,
        city=company_data.city,
        contact_email=company_data.contact_email
    )
    
    doc = company.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.client_companies.insert_one(doc)
    await log_audit(org_id, current_user['id'], "CREATE", "client_company", company.id)
    
    return company

@api_router.get("/client-companies", response_model=List[ClientCompany])
async def list_client_companies(current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners must specify organization")
    
    companies = await db.client_companies.find({"organization_id": org_id}, {"_id": 0}).to_list(1000)
    
    for company in companies:
        if isinstance(company.get('created_at'), str):
            company['created_at'] = datetime.fromisoformat(company['created_at'])
    
    return companies

# ==================== END USER ROUTES ====================

@api_router.post("/end-users", response_model=EndUser)
async def create_end_user(user_data: EndUserCreate, current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners cannot create end users directly")
    
    company = await db.client_companies.find_one({
        "id": user_data.client_company_id,
        "organization_id": org_id
    }, {"_id": 0})
    
    if not company:
        raise HTTPException(status_code=404, detail="Client company not found")
    
    end_user = EndUser(
        organization_id=org_id,
        client_company_id=user_data.client_company_id,
        name=user_data.name,
        email=user_data.email
    )
    
    doc = end_user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.end_users.insert_one(doc)
    await log_audit(org_id, current_user['id'], "CREATE", "end_user", end_user.id)
    
    return end_user

@api_router.get("/end-users", response_model=List[EndUser])
async def list_end_users(current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners must specify organization")
    
    users = await db.end_users.find({"organization_id": org_id}, {"_id": 0}).to_list(1000)
    
    for user in users:
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
    
    return users

# ==================== TICKET ROUTES ====================

@api_router.post("/tickets", response_model=Ticket)
async def create_ticket(ticket_data: TicketCreate, current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners cannot create tickets directly")
    
    # Get next ticket number for this organization
    ticket_number = await get_next_ticket_number(org_id)
    
    ticket = Ticket(
        organization_id=org_id,
        ticket_number=ticket_number,
        title=ticket_data.title,
        description=ticket_data.description,
        priority=ticket_data.priority,
        category=ticket_data.category,
        requester_id=ticket_data.requester_id,
        assigned_staff_id=ticket_data.assigned_staff_id,
        client_company_id=ticket_data.client_company_id,
        device_id=ticket_data.device_id
    )
    
    doc = ticket.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.tickets.insert_one(doc)
    await log_audit(org_id, current_user['id'], "CREATE", "ticket", ticket.id)
    
    return ticket

@api_router.get("/tickets", response_model=List[Ticket])
async def list_tickets(current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners must specify organization")
    
    query = {"organization_id": org_id}
    if current_user.get('role') == UserRole.TECHNICIAN:
        query["assigned_staff_id"] = current_user['id']
    
    tickets = await db.tickets.find(query, {"_id": 0}).to_list(1000)
    
    for ticket in tickets:
        if isinstance(ticket.get('created_at'), str):
            ticket['created_at'] = datetime.fromisoformat(ticket['created_at'])
        if isinstance(ticket.get('updated_at'), str):
            ticket['updated_at'] = datetime.fromisoformat(ticket['updated_at'])
    
    return tickets

@api_router.get("/tickets/{ticket_id}", response_model=Ticket)
async def get_ticket(ticket_id: str, current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    
    ticket = await db.tickets.find_one({"id": ticket_id, "organization_id": org_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if isinstance(ticket.get('created_at'), str):
        ticket['created_at'] = datetime.fromisoformat(ticket['created_at'])
    if isinstance(ticket.get('updated_at'), str):
        ticket['updated_at'] = datetime.fromisoformat(ticket['updated_at'])
    
    return ticket

@api_router.patch("/tickets/{ticket_id}", response_model=Ticket)
async def update_ticket(ticket_id: str, update_data: TicketUpdate, current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    
    ticket = await db.tickets.find_one({"id": ticket_id, "organization_id": org_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    if update_dict:
        await db.tickets.update_one({"id": ticket_id}, {"$set": update_dict})
        await log_audit(org_id, current_user['id'], "UPDATE", "ticket", ticket_id)
    
    updated_ticket = await db.tickets.find_one({"id": ticket_id}, {"_id": 0})
    
    if isinstance(updated_ticket.get('created_at'), str):
        updated_ticket['created_at'] = datetime.fromisoformat(updated_ticket['created_at'])
    if isinstance(updated_ticket.get('updated_at'), str):
        updated_ticket['updated_at'] = datetime.fromisoformat(updated_ticket['updated_at'])
    
    return updated_ticket

# ==================== TICKET COMMENTS ====================

@api_router.post("/tickets/{ticket_id}/comments", response_model=TicketComment)
async def create_ticket_comment(
    ticket_id: str,
    comment_data: TicketCommentCreate,
    current_user: dict = Depends(get_current_user)
):
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners cannot create comments")
    
    # Verify ticket exists and belongs to org
    ticket = await db.tickets.find_one({"id": ticket_id, "organization_id": org_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Validate comment type
    if comment_data.comment_type not in [CommentType.INTERNAL_NOTE, CommentType.PUBLIC_REPLY]:
        raise HTTPException(status_code=400, detail="Invalid comment type")
    
    comment = TicketComment(
        ticket_id=ticket_id,
        organization_id=org_id,
        author_id=current_user['id'],
        author_name=current_user['name'],
        author_type=AuthorType.STAFF,
        comment_type=comment_data.comment_type,
        content=comment_data.content
    )
    
    doc = comment.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.ticket_comments.insert_one(doc)
    
    # Update ticket's updated_at timestamp
    await db.tickets.update_one(
        {"id": ticket_id},
        {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return comment

@api_router.get("/tickets/{ticket_id}/comments", response_model=List[TicketComment])
async def list_ticket_comments(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verify ticket access
    ticket = await db.tickets.find_one({"id": ticket_id, "organization_id": org_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Get comments (filter internal notes for non-staff users if needed)
    comments = await db.ticket_comments.find(
        {"ticket_id": ticket_id, "organization_id": org_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(1000)
    
    for comment in comments:
        if isinstance(comment.get('created_at'), str):
            comment['created_at'] = datetime.fromisoformat(comment['created_at'])
    
    return comments

# ==================== TICKET ATTACHMENTS ====================

@api_router.post("/tickets/{ticket_id}/attachments", response_model=TicketAttachment)
async def create_ticket_attachment(
    ticket_id: str,
    attachment_data: TicketAttachmentCreate,
    current_user: dict = Depends(get_current_user)
):
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners cannot upload attachments")
    
    # Verify ticket exists
    ticket = await db.tickets.find_one({"id": ticket_id, "organization_id": org_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    attachment = TicketAttachment(
        ticket_id=ticket_id,
        organization_id=org_id,
        uploaded_by=current_user['id'],
        uploaded_by_name=current_user['name'],
        filename=attachment_data.filename,
        file_url=attachment_data.file_url,
        file_type=attachment_data.file_type,
        file_size=attachment_data.file_size
    )
    
    doc = attachment.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.ticket_attachments.insert_one(doc)
    
    # Update ticket's updated_at
    await db.tickets.update_one(
        {"id": ticket_id},
        {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return attachment

@api_router.get("/tickets/{ticket_id}/attachments", response_model=List[TicketAttachment])
async def list_ticket_attachments(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verify ticket access
    ticket = await db.tickets.find_one({"id": ticket_id, "organization_id": org_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    attachments = await db.ticket_attachments.find(
        {"ticket_id": ticket_id, "organization_id": org_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    
    for attachment in attachments:
        if isinstance(attachment.get('created_at'), str):
            attachment['created_at'] = datetime.fromisoformat(attachment['created_at'])
    
    return attachments

# ==================== TASK ROUTES ====================

@api_router.post("/tasks", response_model=Task)
async def create_task(task_data: TaskCreate, current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners cannot create tasks directly")
    
    # Check if organization has tasks feature
    has_tasks = await can_use_feature(org_id, "tasks")
    if not has_tasks:
        raise HTTPException(status_code=403, detail="Tasks feature not available in your plan")
    
    task = Task(
        organization_id=org_id,
        title=task_data.title,
        description=task_data.description,
        due_date=task_data.due_date,
        assigned_staff_id=task_data.assigned_staff_id,
        ticket_id=task_data.ticket_id
    )
    
    doc = task.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    if doc.get('due_date'):
        doc['due_date'] = doc['due_date'].isoformat()
    
    await db.tasks.insert_one(doc)
    await log_audit(org_id, current_user['id'], "CREATE", "task", task.id)
    
    return task

@api_router.get("/tasks", response_model=List[Task])
async def list_tasks(current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners must specify organization")
    
    query = {"organization_id": org_id}
    if current_user.get('role') == UserRole.TECHNICIAN:
        query["assigned_staff_id"] = current_user['id']
    
    tasks = await db.tasks.find(query, {"_id": 0}).to_list(1000)
    
    for task in tasks:
        if isinstance(task.get('created_at'), str):
            task['created_at'] = datetime.fromisoformat(task['created_at'])
        if task.get('due_date') and isinstance(task.get('due_date'), str):
            task['due_date'] = datetime.fromisoformat(task['due_date'])
    
    return tasks

# ==================== DASHBOARD STATS ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    
    if current_user.get('is_owner'):
        # SaaS Owner stats
        total_orgs = await db.organizations.count_documents({})
        active_orgs = await db.organizations.count_documents({"status": "active"})
        total_tickets = await db.tickets.count_documents({})
        total_users = await db.staff_users.count_documents({"is_owner": False})
        
        return {
            "total_organizations": total_orgs,
            "active_organizations": active_orgs,
            "total_tickets": total_tickets,
            "total_staff_users": total_users
        }
    else:
        # Organization stats
        total_tickets = await db.tickets.count_documents({"organization_id": org_id})
        open_tickets = await db.tickets.count_documents({
            "organization_id": org_id,
            "status": {"$in": ["new", "open", "in_progress"]}
        })
        total_staff = await db.staff_users.count_documents({
            "organization_id": org_id,
            "status": "active"
        })
        total_end_users = await db.end_users.count_documents({"organization_id": org_id})
        total_companies = await db.client_companies.count_documents({"organization_id": org_id})
        
        org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
        plan_limits = await get_plan_limits(org_id)
        
        return {
            "organization": org.get('name') if org else '',
            "plan": org.get('plan') if org else '',
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "total_staff": total_staff,
            "max_staff": plan_limits.get('max_staff_users', 3),
            "total_end_users": total_end_users,
            "total_client_companies": total_companies
        }

# ==================== NOTIFICATIONS ====================

@api_router.get("/notifications", response_model=List[Notification])
async def list_notifications(current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id', '')
    
    notifications = await db.notifications.find(
        {"organization_id": org_id, "user_id": current_user['id']},
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    
    for notif in notifications:
        if isinstance(notif.get('created_at'), str):
            notif['created_at'] = datetime.fromisoformat(notif['created_at'])
    
    return notifications

@api_router.patch("/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, current_user: dict = Depends(get_current_user)):
    await db.notifications.update_one(
        {"id": notif_id, "user_id": current_user['id']},
        {"$set": {"read": True}}
    )
    return {"message": "Notification marked as read"}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
