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
# Use branded email sender for notifications
SENDER_EMAIL = "FOXITE Notifications <notifications@foxite.com>"
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app
app = FastAPI(title="FOXITE API")
api_router = APIRouter(prefix="/api")

# ==================== PLAN DEFINITIONS ====================
# Single source of truth for all plan configurations
# Plans: CORE, PLUS, PRIME (Pro)

PLAN_FEATURES = {
    "CORE": {
        "name": "CORE",
        "display_name": "Core",
        "price_per_seat": 18,
        "min_seats": 3,
        "currency": "USD",
        "yearly_discount": 0.15,
        "max_slas": 1,
        # Resource limits - None means unlimited
        "limits": {
            "staff_users": None,      # Controlled by seat_count
            "tickets": None,          # Unlimited
            "end_users": None,        # Unlimited
            "devices": 25,            # Limited to 25 devices
            "licenses": 0,            # No licenses on Core
            "saved_views": 5,         # Limited saved views
            "automations": 0,         # No automations
            "ai_requests_monthly": 0, # No AI
        },
        # Feature flags - True/False or tier string
        "features": {
            "tickets": True,
            "end_users": True,
            "tasks": True,
            "devices_inventory": True,
            "licenses_inventory": False,  # Not available on Core
            "knowledge_base": True,
            "calendar": True,
            "email_notifications": True,
            "ai_features": False,
            "ai_ticket_summary": False,
            "ai_response_suggestions": False,
            "sla_management": "basic",
            "reports": "basic",
            "api_access": False,
            "end_user_portal_customization": False,
            "workflows": False,
            "automation_rules": False,
            "saved_filters": False,
            "custom_dashboards": False,
            "audit_logs": False,
            "alerts_escalations": "basic",
            "time_tracking": True,
            "asset_linking": True,
        }
    },
    "PLUS": {
        "name": "PLUS",
        "display_name": "Plus",
        "price_per_seat": 55,
        "min_seats": 3,
        "currency": "USD",
        "yearly_discount": 0.15,
        "max_slas": 3,
        "limits": {
            "staff_users": None,       # Controlled by seat_count
            "tickets": None,           # Unlimited
            "end_users": None,         # Unlimited
            "devices": 100,            # Up to 100 devices
            "licenses": 50,            # Up to 50 licenses
            "saved_views": 25,         # More saved views
            "automations": 10,         # Up to 10 automation rules
            "ai_requests_monthly": 100, # 100 AI requests/month
        },
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
            "ai_ticket_summary": True,
            "ai_response_suggestions": False,
            "sla_management": "advanced",
            "reports": "full",
            "api_access": "read_only",
            "end_user_portal_customization": False,
            "workflows": True,
            "automation_rules": True,
            "saved_filters": True,
            "custom_dashboards": False,
            "audit_logs": False,
            "alerts_escalations": "advanced",
            "time_tracking": True,
            "asset_linking": True,
        }
    },
    "PRIME": {
        "name": "PRIME",
        "display_name": "Prime",
        "price_per_seat": 100,
        "min_seats": 1,
        "currency": "USD",
        "yearly_discount": 0.15,
        "max_slas": None,  # Unlimited
        "limits": {
            "staff_users": None,        # Controlled by seat_count
            "tickets": None,            # Unlimited
            "end_users": None,          # Unlimited
            "devices": None,            # Unlimited
            "licenses": None,           # Unlimited
            "saved_views": None,        # Unlimited
            "automations": None,        # Unlimited
            "ai_requests_monthly": None, # Unlimited
        },
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
            "ai_ticket_summary": True,
            "ai_response_suggestions": True,
            "sla_management": "advanced",
            "reports": "full",
            "api_access": "full",
            "end_user_portal_customization": True,
            "workflows": True,
            "automation_rules": True,
            "saved_filters": True,
            "custom_dashboards": True,
            "audit_logs": True,
            "alerts_escalations": "advanced",
            "time_tracking": True,
            "asset_linking": True,
        }
    }
}

# Billing cycle options
class BillingCycle(str):
    MONTHLY = "monthly"
    YEARLY = "yearly"

# ==================== PLAN ENFORCEMENT ERRORS ====================

class PlanLimitError(HTTPException):
    """Custom exception for plan limit violations"""
    def __init__(self, resource: str, limit: int, plan: str):
        detail = {
            "error": "plan_limit_exceeded",
            "resource": resource,
            "limit": limit,
            "plan": plan,
            "message": f"You have reached the {resource} limit ({limit}) for your {plan} plan. Please upgrade to add more.",
            "upgrade_url": "/settings/billing"
        }
        super().__init__(status_code=403, detail=detail)

class FeatureNotAvailableError(HTTPException):
    """Custom exception for feature not available on plan"""
    def __init__(self, feature: str, plan: str, required_plan: str = "PLUS"):
        detail = {
            "error": "feature_not_available",
            "feature": feature,
            "plan": plan,
            "required_plan": required_plan,
            "message": f"The '{feature}' feature is not available on your {plan} plan. Please upgrade to {required_plan} or higher.",
            "upgrade_url": "/settings/billing"
        }
        super().__init__(status_code=403, detail=detail)

class SeatLimitExceededError(HTTPException):
    """Custom exception for seat limit exceeded"""
    def __init__(self, current_users: int, seat_count: int):
        detail = {
            "error": "seat_limit_exceeded",
            "current_users": current_users,
            "seat_count": seat_count,
            "message": f"Cannot add more users. You have {current_users} users but only {seat_count} seats. Please increase your seat count.",
            "upgrade_url": "/settings/billing"
        }
        super().__init__(status_code=403, detail=detail)

class OrganizationSuspendedError(HTTPException):
    """Custom exception for suspended organization"""
    def __init__(self):
        detail = {
            "error": "organization_suspended",
            "message": "Your organization is currently suspended. Please contact support or update your billing information.",
            "upgrade_url": "/settings/billing"
        }
        super().__init__(status_code=403, detail=detail)

# ==================== PRICING & BILLING HELPERS ====================

def calculate_pricing(plan_id: str, seat_count: int, billing_cycle: str) -> dict:
    """Calculate pricing for a plan with seat count and billing cycle"""
    plan = PLAN_FEATURES.get(plan_id, PLAN_FEATURES["CORE"])
    price_per_seat = plan.get("price_per_seat", 18)
    min_seats = plan.get("min_seats", 3)
    yearly_discount = plan.get("yearly_discount", 0.15)
    
    # Ensure minimum seats
    effective_seats = max(seat_count, min_seats)
    
    # Calculate monthly price
    monthly_total = price_per_seat * effective_seats
    
    # Calculate yearly price with discount
    yearly_total = monthly_total * 12 * (1 - yearly_discount)
    
    if billing_cycle == BillingCycle.YEARLY:
        effective_monthly = yearly_total / 12
        total_price = yearly_total
        savings = (monthly_total * 12) - yearly_total
    else:
        effective_monthly = monthly_total
        total_price = monthly_total
        savings = 0
    
    return {
        "plan_id": plan_id,
        "plan_name": plan.get("display_name", plan_id),
        "price_per_seat": price_per_seat,
        "seat_count": effective_seats,
        "min_seats": min_seats,
        "billing_cycle": billing_cycle,
        "monthly_subtotal": monthly_total,
        "yearly_discount_percent": int(yearly_discount * 100),
        "effective_monthly": round(effective_monthly, 2),
        "total_price": round(total_price, 2),
        "savings": round(savings, 2),
        "currency": plan.get("currency", "USD")
    }

async def check_seat_availability(org_id: str, exclude_user_id: str = None) -> dict:
    """Check if organization has available seats"""
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    seat_count = org.get("seat_count", 3)
    
    # Count current active staff users
    query = {"organization_id": org_id, "status": "active"}
    if exclude_user_id:
        query["id"] = {"$ne": exclude_user_id}
    current_users = await db.staff_users.count_documents(query)
    
    return {
        "seat_count": seat_count,
        "current_users": current_users,
        "available_seats": max(0, seat_count - current_users),
        "can_add_user": current_users < seat_count
    }

async def check_org_suspended(org_id: str) -> bool:
    """Check if organization is suspended"""
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org.get("status") == OrgStatus.SUSPENDED

async def enforce_not_suspended(org_id: str):
    """Raise error if organization is suspended"""
    if await check_org_suspended(org_id):
        raise OrganizationSuspendedError()

async def check_sla_limit(org_id: str) -> dict:
    """Check SLA limit for organization based on plan"""
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    plan_id = org.get("plan", "CORE")
    plan = PLAN_FEATURES.get(plan_id, PLAN_FEATURES["CORE"])
    max_slas = plan.get("max_slas")
    
    current_slas = await db.sla_policies.count_documents({"organization_id": org_id})
    
    return {
        "max_slas": max_slas,
        "current_slas": current_slas,
        "can_add_sla": max_slas is None or current_slas < max_slas
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
    """Check if organization can add more staff users based on seat_count"""
    seat_info = await check_seat_availability(org_id)
    return seat_info["can_add_user"]

async def get_resource_limit(org_id: str, resource: str) -> Optional[int]:
    """Get the limit for a specific resource (None = unlimited)"""
    plan = await get_plan_limits(org_id)
    return plan.get("limits", {}).get(resource, None)

async def get_current_resource_count(org_id: str, resource: str) -> int:
    """Get current count of a resource for an organization"""
    collection_map = {
        "devices": "devices",
        "licenses": "licenses",
        "saved_views": "saved_views",
        "staff_users": "staff_users",
        "automations": "automation_rules",  # Future collection
    }
    
    collection_name = collection_map.get(resource)
    if not collection_name:
        return 0
    
    # Check if collection exists
    collection = db[collection_name]
    count = await collection.count_documents({"organization_id": org_id})
    return count

async def check_resource_limit(org_id: str, resource: str) -> Dict[str, Any]:
    """
    Check if organization can add more of a resource.
    Returns dict with: can_add (bool), current (int), limit (int or None), plan (str)
    """
    plan = await get_plan_limits(org_id)
    plan_name = plan.get("name", "CORE")
    limit = plan.get("limits", {}).get(resource, None)
    current = await get_current_resource_count(org_id, resource)
    
    # None means unlimited
    can_add = limit is None or current < limit
    
    return {
        "can_add": can_add,
        "current": current,
        "limit": limit,
        "plan": plan_name,
        "unlimited": limit is None
    }

async def enforce_resource_limit(org_id: str, resource: str):
    """
    Enforce resource limit - raises PlanLimitError if limit exceeded.
    Call this before creating a new resource.
    """
    result = await check_resource_limit(org_id, resource)
    
    if not result["can_add"]:
        raise PlanLimitError(
            resource=resource,
            limit=result["limit"],
            plan=result["plan"]
        )

async def enforce_feature_access(org_id: str, feature: str, required_plan: str = "PLUS"):
    """
    Enforce feature access - raises FeatureNotAvailableError if not available.
    Call this before accessing a gated feature.
    """
    plan = await get_plan_limits(org_id)
    plan_name = plan.get("name", "CORE")
    
    if not await can_use_feature(org_id, feature):
        raise FeatureNotAvailableError(
            feature=feature,
            plan=plan_name,
            required_plan=required_plan
        )

def get_minimum_plan_for_feature(feature: str) -> str:
    """Get the minimum plan required for a feature"""
    for plan_name in ["CORE", "PLUS", "PRIME"]:
        plan = PLAN_FEATURES[plan_name]
        feature_value = plan["features"].get(feature, False)
        if feature_value and feature_value != False:
            return plan_name
    return "PRIME"  # Default to highest if not found

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
    billing_cycle: str = BillingCycle.MONTHLY
    seat_count: int = 3  # Number of paid seats
    status: str = OrgStatus.ACTIVE
    trial_ends_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrganizationCreate(BaseModel):
    name: str
    legal_name: Optional[str] = None
    country: str = "US"
    timezone: str = "UTC"
    language: str = Language.EN
    plan: str = PlanType.CORE
    billing_cycle: str = BillingCycle.MONTHLY
    seat_count: int = 3

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    plan: Optional[str] = None
    billing_cycle: Optional[str] = None
    seat_count: Optional[int] = None
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
    phone: Optional[str] = None
    status: str = "active"
    custom_fields_data: dict = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EndUserCreate(BaseModel):
    client_company_id: Optional[str] = None
    name: str
    email: EmailStr
    phone: Optional[str] = None
    custom_fields_data: dict = {}

class EndUserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    client_company_id: Optional[str] = None
    status: Optional[str] = None
    custom_fields_data: Optional[dict] = None

# Client Company Models
class ClientCompany(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    status: str = "active"
    custom_fields_data: dict = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ClientCompanyCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    custom_fields_data: dict = {}

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
    sla_policy_id: Optional[str] = None  # SLA policy applied
    response_due_at: Optional[datetime] = None  # When first response is due
    resolution_due_at: Optional[datetime] = None  # When resolution is due
    first_response_at: Optional[datetime] = None  # When first staff reply was made
    sla_breached_response: bool = False  # Response SLA breached
    sla_breached_resolution: bool = False  # Resolution SLA breached
    custom_fields_data: dict = {}  # Dynamic custom fields storage
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
    custom_fields_data: dict = {}

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_staff_id: Optional[str] = None
    device_id: Optional[str] = None
    custom_fields_data: Optional[dict] = None

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

# Session (Time Tracking) Models
class Session(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    ticket_id: str
    agent_id: str
    agent_name: str  # Denormalized for display
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None  # Auto-calculated
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SessionStart(BaseModel):
    ticket_id: str
    note: Optional[str] = None

class SessionStop(BaseModel):
    session_id: str
    note: Optional[str] = None

class SessionManual(BaseModel):
    ticket_id: str
    start_time: datetime
    end_time: datetime
    note: Optional[str] = None

# SLA Models
class SLAPolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    name: str
    priority: str  # low, medium, high, urgent
    response_time_minutes: int
    resolution_time_minutes: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SLAPolicyCreate(BaseModel):
    name: str
    priority: str
    response_time_minutes: int
    resolution_time_minutes: int

class SLAPolicyUpdate(BaseModel):
    name: Optional[str] = None
    response_time_minutes: Optional[int] = None
    resolution_time_minutes: Optional[int] = None

class BusinessHours(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    timezone: str = "UTC"
    work_days: List[int] = [1, 2, 3, 4, 5]  # Monday=1 to Sunday=7
    start_time: str = "09:00"  # HH:MM format
    end_time: str = "17:00"    # HH:MM format
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BusinessHoursCreate(BaseModel):
    timezone: str = "UTC"
    work_days: List[int] = [1, 2, 3, 4, 5]
    start_time: str = "09:00"
    end_time: str = "17:00"

# Saved View Models
class SavedView(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    entity_type: str  # "tickets", "tasks", "sessions"
    name: str
    filters: dict  # JSON filter configuration
    created_by: str
    created_by_name: str  # Denormalized
    is_shared: bool = False  # Shared with organization
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SavedViewCreate(BaseModel):
    entity_type: str
    name: str
    filters: dict
    is_shared: bool = False

class SavedViewUpdate(BaseModel):
    name: Optional[str] = None
    filters: Optional[dict] = None
    is_shared: Optional[bool] = None

# Device Models (Asset Inventory)
class Device(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    client_company_id: str
    name: str
    device_type: str  # laptop, server, printer, network, mobile, other
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    assigned_to: Optional[str] = None  # end_user_id
    status: str = "active"  # active, maintenance, retired, disposed
    purchase_date: Optional[datetime] = None
    warranty_expiry: Optional[datetime] = None
    notes: Optional[str] = None
    custom_fields_data: dict = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DeviceCreate(BaseModel):
    client_company_id: Optional[str] = None
    name: str
    device_type: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    assigned_to: Optional[str] = None
    status: str = "active"
    purchase_date: Optional[datetime] = None
    warranty_expiry: Optional[datetime] = None
    notes: Optional[str] = None
    custom_fields_data: dict = {}

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    device_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[str] = None
    purchase_date: Optional[datetime] = None
    warranty_expiry: Optional[datetime] = None
    notes: Optional[str] = None
    custom_fields_data: Optional[dict] = None

# License Models (Asset Inventory)
class License(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    client_company_id: Optional[str] = None
    name: str
    license_type: str  # software, service, subscription, other
    provider: Optional[str] = None
    license_key: Optional[str] = None
    assigned_to: Optional[str] = None  # end_user_id
    quantity: int = 1
    seats_total: int = 1
    purchase_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    renewal_cost: Optional[float] = None
    billing_cycle: Optional[str] = None  # monthly, yearly, one-time
    status: str = "active"  # active, expired, cancelled
    days_until_expiration: Optional[int] = None  # Calculated field
    expiring_soon: bool = False  # Calculated: < 60 days
    expired: bool = False  # Calculated: past expiration
    notes: Optional[str] = None
    custom_fields_data: dict = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LicenseCreate(BaseModel):
    client_company_id: Optional[str] = None
    name: str
    license_type: str
    provider: Optional[str] = None
    license_key: Optional[str] = None
    assigned_to: Optional[str] = None
    quantity: int = 1
    seats_total: int = 1
    purchase_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    renewal_cost: Optional[float] = None
    billing_cycle: Optional[str] = None
    status: str = "active"
    notes: Optional[str] = None
    custom_fields_data: dict = {}

class LicenseUpdate(BaseModel):
    name: Optional[str] = None
    license_type: Optional[str] = None
    provider: Optional[str] = None
    license_key: Optional[str] = None
    assigned_to: Optional[str] = None
    quantity: Optional[int] = None
    seats_total: Optional[int] = None
    purchase_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    renewal_cost: Optional[float] = None
    billing_cycle: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

# Task Models
class Task(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    title: str
    description: str = ""
    priority: str = "medium"
    status: str = TaskStatus.TODO
    due_date: Optional[datetime] = None
    assigned_staff_id: Optional[str] = None
    ticket_id: Optional[str] = None
    custom_fields_data: dict = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    status: str = "pending"
    due_date: Optional[datetime] = None
    assigned_staff_id: Optional[str] = None
    ticket_id: Optional[str] = None
    custom_fields_data: dict = {}

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    assigned_staff_id: Optional[str] = None
    custom_fields_data: Optional[dict] = None

# ==================== CUSTOM FIELDS MODELS ====================

class FieldType(str):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    DROPDOWN = "dropdown"
    FILE = "file"

class EntityType(str):
    TICKET = "ticket"
    DEVICE = "device"
    COMPANY = "company"
    END_USER = "end_user"
    LICENSE = "license"
    TASK = "task"

class CustomField(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    entity_type: str  # ticket, device, company, end_user, license, task
    label: str
    field_type: str  # text, number, date, boolean, dropdown, file
    required: bool = False
    options: List[str] = []  # For dropdown type
    active: bool = True
    order: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CustomFieldCreate(BaseModel):
    entity_type: str
    label: str
    field_type: str
    required: bool = False
    options: List[str] = []
    order: int = 0

class CustomFieldUpdate(BaseModel):
    label: Optional[str] = None
    required: Optional[bool] = None
    options: Optional[List[str]] = None
    active: Optional[bool] = None
    order: Optional[int] = None

# ==================== ATTACHMENTS MODELS ====================

class Attachment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    entity_type: str  # ticket, device, company, end_user, license
    entity_id: str
    file_name: str
    file_url: str
    file_size: int = 0
    mime_type: str = "application/octet-stream"
    uploaded_by: str  # user_id
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AttachmentCreate(BaseModel):
    entity_type: str
    entity_id: str
    file_name: str
    file_url: str
    file_size: int = 0
    mime_type: str = "application/octet-stream"

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

def calculate_duration(start_time: datetime, end_time: datetime) -> int:
    """Calculate duration in minutes between start and end time"""
    if not start_time or not end_time:
        return 0
    
    # Ensure both are datetime objects
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    
    delta = end_time - start_time
    return max(0, int(delta.total_seconds() / 60))

async def check_session_overlap(org_id: str, agent_id: str, start_time: datetime, end_time: Optional[datetime] = None, exclude_session_id: Optional[str] = None) -> bool:
    """Check if a session overlaps with existing sessions for an agent"""
    # Build query to find overlapping sessions
    query = {
        "organization_id": org_id,
        "agent_id": agent_id
    }
    
    if exclude_session_id:
        query["id"] = {"$ne": exclude_session_id}
    
    # Get all sessions for this agent
    existing_sessions = await db.sessions.find(query, {"_id": 0}).to_list(1000)
    
    for session in existing_sessions:
        session_start = session.get('start_time')
        session_end = session.get('end_time')
        
        # Convert to datetime if strings
        if isinstance(session_start, str):
            session_start = datetime.fromisoformat(session_start.replace('Z', '+00:00'))
        if session_end and isinstance(session_end, str):
            session_end = datetime.fromisoformat(session_end.replace('Z', '+00:00'))
        
        # If existing session has no end time (active), check if new session starts during it
        if not session_end:
            if start_time >= session_start:
                return True  # Overlap with active session
        else:
            # Check for overlap
            if end_time:
                # Both sessions have end times
                if (start_time < session_end and end_time > session_start):
                    return True
            else:
                # New session has no end time (being started)
                if start_time < session_end:
                    return True
    
    return False

def calculate_business_hours_due_date(start_time: datetime, minutes_to_add: int, business_hours: dict) -> datetime:
    """Calculate due date adding minutes only during business hours"""
    if not business_hours:
        # No business hours configured, add minutes directly
        return start_time + timedelta(minutes=minutes_to_add)
    
    from datetime import time as dt_time
    import pytz
    
    # Parse business hours
    tz_str = business_hours.get('timezone', 'UTC')
    try:
        tz = pytz.timezone(tz_str)
    except:
        tz = pytz.UTC
    
    work_days = business_hours.get('work_days', [1, 2, 3, 4, 5])
    start_time_str = business_hours.get('start_time', '09:00')
    end_time_str = business_hours.get('end_time', '17:00')
    
    # Parse work hours
    work_start_hour, work_start_min = map(int, start_time_str.split(':'))
    work_end_hour, work_end_min = map(int, end_time_str.split(':'))
    
    work_start = dt_time(work_start_hour, work_start_min)
    work_end = dt_time(work_end_hour, work_end_min)
    
    # Calculate minutes per work day
    work_minutes_per_day = (work_end_hour * 60 + work_end_min) - (work_start_hour * 60 + work_start_min)
    
    # Ensure start_time is timezone-aware
    if start_time.tzinfo is None:
        start_time = pytz.UTC.localize(start_time)
    
    # Convert to business timezone
    current = start_time.astimezone(tz)
    remaining_minutes = minutes_to_add
    
    while remaining_minutes > 0:
        # Check if current day is a work day
        weekday = current.isoweekday()  # Monday=1, Sunday=7
        
        if weekday in work_days:
            current_time = current.time()
            
            # If before work hours, jump to work start
            if current_time < work_start:
                current = current.replace(hour=work_start_hour, minute=work_start_min, second=0, microsecond=0)
                current_time = current.time()
            
            # If after work hours, jump to next day's work start
            if current_time >= work_end:
                current = current + timedelta(days=1)
                current = current.replace(hour=work_start_hour, minute=work_start_min, second=0, microsecond=0)
                continue
            
            # Calculate minutes until end of work day
            current_minutes = current_time.hour * 60 + current_time.minute
            work_end_minutes = work_end_hour * 60 + work_end_min
            minutes_until_end = work_end_minutes - current_minutes
            
            if remaining_minutes <= minutes_until_end:
                # Can finish within this work day
                current = current + timedelta(minutes=remaining_minutes)
                remaining_minutes = 0
            else:
                # Use up this work day and continue to next
                remaining_minutes -= minutes_until_end
                current = current + timedelta(days=1)
                current = current.replace(hour=work_start_hour, minute=work_start_min, second=0, microsecond=0)
        else:
            # Non-work day, skip to next day
            current = current + timedelta(days=1)
            current = current.replace(hour=work_start_hour, minute=work_start_min, second=0, microsecond=0)
    
    # Convert back to UTC
    return current.astimezone(pytz.UTC)

async def apply_sla_to_ticket(ticket_id: str, org_id: str, priority: str, created_at: datetime):
    """Apply SLA policy to ticket based on priority"""
    # Find SLA policy for this priority
    sla_policy = await db.sla_policies.find_one({
        "organization_id": org_id,
        "priority": priority
    }, {"_id": 0})
    
    if not sla_policy:
        # No SLA policy for this priority
        return
    
    # Get business hours
    business_hours = await db.business_hours.find_one({"organization_id": org_id}, {"_id": 0})
    
    # Calculate due dates
    response_due = calculate_business_hours_due_date(
        created_at,
        sla_policy['response_time_minutes'],
        business_hours
    )
    
    resolution_due = calculate_business_hours_due_date(
        created_at,
        sla_policy['resolution_time_minutes'],
        business_hours
    )
    
    # Update ticket with SLA info
    await db.tickets.update_one(
        {"id": ticket_id},
        {"$set": {
            "sla_policy_id": sla_policy['id'],
            "response_due_at": response_due.isoformat(),
            "resolution_due_at": resolution_due.isoformat()
        }}
    )

async def check_sla_breach(ticket: dict):
    """Check if SLA has been breached and update flags"""
    now = datetime.now(timezone.utc)
    
    updates = {}
    
    # Check response SLA
    if ticket.get('response_due_at') and not ticket.get('first_response_at'):
        response_due = ticket['response_due_at']
        if isinstance(response_due, str):
            response_due = datetime.fromisoformat(response_due)
        
        if now > response_due and not ticket.get('sla_breached_response'):
            updates['sla_breached_response'] = True
    
    # Check resolution SLA
    if ticket.get('resolution_due_at') and ticket.get('status') not in ['resolved', 'closed']:
        resolution_due = ticket['resolution_due_at']
        if isinstance(resolution_due, str):
            resolution_due = datetime.fromisoformat(resolution_due)
        
        if now > resolution_due and not ticket.get('sla_breached_resolution'):
            updates['sla_breached_resolution'] = True
    
    # Update if needed
    if updates:
        await db.tickets.update_one({"id": ticket['id']}, {"$set": updates})

def calculate_license_expiration_status(license: dict) -> dict:
    """Calculate expiration status for a license (data only, no alerts)"""
    expiration_date = license.get('expiration_date')
    
    if not expiration_date:
        return {
            'days_until_expiration': None,
            'expiring_soon': False,
            'expired': False
        }
    
    # Convert to datetime if string
    if isinstance(expiration_date, str):
        expiration_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
    
    # Ensure timezone aware
    if expiration_date.tzinfo is None:
        expiration_date = expiration_date.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    delta = expiration_date - now
    days_until = delta.days
    
    return {
        'days_until_expiration': days_until,
        'expiring_soon': days_until < 60 and days_until >= 0,
        'expired': days_until < 0
    }

def parse_filters(filters: dict, entity_type: str) -> dict:
    """Parse filter parameters into MongoDB query"""
    query = {}
    
    # Common filters
    if filters.get('status'):
        query['status'] = filters['status']
    
    if filters.get('priority'):
        query['priority'] = filters['priority']
    
    if filters.get('assigned_to'):
        query['assigned_staff_id'] = filters['assigned_to']
    
    if filters.get('created_at_from') or filters.get('created_at_to'):
        query['created_at'] = {}
        if filters.get('created_at_from'):
            query['created_at']['$gte'] = filters['created_at_from']
        if filters.get('created_at_to'):
            query['created_at']['$lte'] = filters['created_at_to']
    
    if filters.get('updated_at_from') or filters.get('updated_at_to'):
        query['updated_at'] = {}
        if filters.get('updated_at_from'):
            query['updated_at']['$gte'] = filters['updated_at_from']
        if filters.get('updated_at_to'):
            query['updated_at']['$lte'] = filters['updated_at_to']
    
    # Entity-specific filters
    if entity_type == 'tickets':
        if filters.get('ticket_number'):
            query['ticket_number'] = filters['ticket_number']
        
        if filters.get('requester_id'):
            query['requester_id'] = filters['requester_id']
        
        if filters.get('sla_breached_response') is not None:
            query['sla_breached_response'] = filters['sla_breached_response']
        
        if filters.get('sla_breached_resolution') is not None:
            query['sla_breached_resolution'] = filters['sla_breached_resolution']
        
        # Text search on title and description
        if filters.get('search'):
            query['$or'] = [
                {'title': {'$regex': filters['search'], '$options': 'i'}},
                {'description': {'$regex': filters['search'], '$options': 'i'}}
            ]
    
    elif entity_type == 'tasks':
        if filters.get('due_date_from') or filters.get('due_date_to'):
            query['due_date'] = {}
            if filters.get('due_date_from'):
                query['due_date']['$gte'] = filters['due_date_from']
            if filters.get('due_date_to'):
                query['due_date']['$lte'] = filters['due_date_to']
        
        if filters.get('completed') is not None:
            query['status'] = 'done' if filters['completed'] else {'$ne': 'done'}
        
        # Text search on title
        if filters.get('search'):
            query['title'] = {'$regex': filters['search'], '$options': 'i'}
    
    elif entity_type == 'sessions':
        if filters.get('agent_id'):
            query['agent_id'] = filters['agent_id']
        
        if filters.get('ticket_id'):
            query['ticket_id'] = filters['ticket_id']
        
        if filters.get('start_time_from') or filters.get('start_time_to'):
            query['start_time'] = {}
            if filters.get('start_time_from'):
                query['start_time']['$gte'] = filters['start_time_from']
            if filters.get('start_time_to'):
                query['start_time']['$lte'] = filters['start_time_to']
        
        # Text search on note
        if filters.get('search'):
            query['note'] = {'$regex': filters['search'], '$options': 'i'}
    
    return query

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

# ==================== NOTIFICATION SERVICE ====================

def get_email_template(title: str, content: str, action_url: str = None, action_label: str = None) -> str:
    """Generate a branded HTML email template"""
    action_button = ""
    if action_url and action_label:
        action_button = f'''
        <div style="text-align: center; margin-top: 24px;">
            <a href="{action_url}" style="background: #f97316; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">{action_label}</a>
        </div>
        '''
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f3f4f6; margin: 0; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <div style="background: linear-gradient(135deg, #1f2937 0%, #111827 100%); padding: 24px; text-align: center;">
                <h1 style="color: #f97316; margin: 0; font-size: 24px; font-weight: bold;">FOXITE</h1>
            </div>
            <div style="padding: 32px;">
                <h2 style="color: #1f2937; margin: 0 0 16px 0; font-size: 20px;">{title}</h2>
                <div style="color: #4b5563; font-size: 15px; line-height: 1.6;">
                    {content}
                </div>
                {action_button}
            </div>
            <div style="background: #f9fafb; padding: 16px 32px; text-align: center; border-top: 1px solid #e5e7eb;">
                <p style="color: #9ca3af; font-size: 13px; margin: 0;">© 2026 FOXITE. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

async def create_in_app_notification(org_id: str, user_id: str, title: str, message: str):
    """Create an in-app notification for a user"""
    notification = Notification(
        organization_id=org_id,
        user_id=user_id,
        title=title,
        message=message
    )
    doc = notification.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.notifications.insert_one(doc)
    return notification

async def notify_ticket_created(ticket: dict, creator: dict):
    """Send notifications when a ticket is created"""
    org_id = ticket.get('organization_id')
    ticket_number = ticket.get('ticket_number', 'N/A')
    ticket_title = ticket.get('title', 'Untitled')
    ticket_id = ticket.get('id')
    
    ticket_url = f"{FRONTEND_URL}/tickets/{ticket_id}"
    
    # Notify assigned technician if assigned
    if ticket.get('assigned_staff_id'):
        assignee = await db.staff_users.find_one({"id": ticket['assigned_staff_id']}, {"_id": 0})
        if assignee and assignee.get('email'):
            # Create in-app notification
            await create_in_app_notification(
                org_id, assignee['id'],
                f"Ticket #{ticket_number} assigned to you",
                f"New ticket: {ticket_title}"
            )
            # Send email
            content = f"""
            <p>A new ticket has been assigned to you:</p>
            <div style="background: #f9fafb; padding: 16px; border-radius: 8px; margin: 16px 0;">
                <p style="margin: 0 0 8px 0;"><strong>Ticket:</strong> #{ticket_number}</p>
                <p style="margin: 0 0 8px 0;"><strong>Subject:</strong> {ticket_title}</p>
                <p style="margin: 0 0 8px 0;"><strong>Priority:</strong> {ticket.get('priority', 'medium').upper()}</p>
                <p style="margin: 0;"><strong>Created by:</strong> {creator.get('name', 'System')}</p>
            </div>
            """
            html = get_email_template(
                f"New Ticket Assigned: #{ticket_number}",
                content,
                ticket_url,
                "View Ticket"
            )
            asyncio.create_task(send_email_async(assignee['email'], f"[FOXITE] Ticket #{ticket_number} assigned to you", html))

async def notify_ticket_assigned(ticket: dict, assignee_id: str, assigner: dict):
    """Send notification when a ticket is assigned to someone"""
    org_id = ticket.get('organization_id')
    ticket_number = ticket.get('ticket_number', 'N/A')
    ticket_title = ticket.get('title', 'Untitled')
    ticket_id = ticket.get('id')
    
    ticket_url = f"{FRONTEND_URL}/tickets/{ticket_id}"
    
    assignee = await db.staff_users.find_one({"id": assignee_id}, {"_id": 0})
    if assignee and assignee.get('email'):
        # Create in-app notification
        await create_in_app_notification(
            org_id, assignee['id'],
            f"Ticket #{ticket_number} assigned to you",
            f"{assigner.get('name', 'Someone')} assigned you to: {ticket_title}"
        )
        # Send email
        content = f"""
        <p>{assigner.get('name', 'A team member')} has assigned you to a ticket:</p>
        <div style="background: #f9fafb; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <p style="margin: 0 0 8px 0;"><strong>Ticket:</strong> #{ticket_number}</p>
            <p style="margin: 0 0 8px 0;"><strong>Subject:</strong> {ticket_title}</p>
            <p style="margin: 0;"><strong>Priority:</strong> {ticket.get('priority', 'medium').upper()}</p>
        </div>
        """
        html = get_email_template(
            f"Ticket Assigned: #{ticket_number}",
            content,
            ticket_url,
            "View Ticket"
        )
        asyncio.create_task(send_email_async(assignee['email'], f"[FOXITE] Ticket #{ticket_number} assigned to you", html))

async def notify_ticket_status_changed(ticket: dict, old_status: str, new_status: str, changer: dict):
    """Send notification when a ticket's status changes"""
    org_id = ticket.get('organization_id')
    ticket_number = ticket.get('ticket_number', 'N/A')
    ticket_title = ticket.get('title', 'Untitled')
    ticket_id = ticket.get('id')
    
    ticket_url = f"{FRONTEND_URL}/tickets/{ticket_id}"
    
    # Notify requester about status change
    if ticket.get('requester_id'):
        requester = await db.end_users.find_one({"id": ticket['requester_id']}, {"_id": 0})
        if requester and requester.get('email'):
            status_display = new_status.replace('_', ' ').title()
            content = f"""
            <p>The status of your ticket has been updated:</p>
            <div style="background: #f9fafb; padding: 16px; border-radius: 8px; margin: 16px 0;">
                <p style="margin: 0 0 8px 0;"><strong>Ticket:</strong> #{ticket_number}</p>
                <p style="margin: 0 0 8px 0;"><strong>Subject:</strong> {ticket_title}</p>
                <p style="margin: 0 0 8px 0;"><strong>New Status:</strong> <span style="color: #f97316; font-weight: 600;">{status_display}</span></p>
                <p style="margin: 0;"><strong>Updated by:</strong> {changer.get('name', 'Support Team')}</p>
            </div>
            """
            html = get_email_template(
                f"Ticket Update: #{ticket_number}",
                content,
                ticket_url,
                "View Ticket"
            )
            asyncio.create_task(send_email_async(requester['email'], f"[FOXITE] Ticket #{ticket_number} - Status: {status_display}", html))
    
    # Also notify assigned technician if different from changer
    if ticket.get('assigned_staff_id') and ticket['assigned_staff_id'] != changer.get('id'):
        assignee = await db.staff_users.find_one({"id": ticket['assigned_staff_id']}, {"_id": 0})
        if assignee and assignee.get('email'):
            await create_in_app_notification(
                org_id, assignee['id'],
                f"Ticket #{ticket_number} status changed",
                f"Status changed from {old_status} to {new_status}"
            )

async def notify_ticket_comment_added(ticket: dict, comment: dict, commenter: dict):
    """Send notification when a comment is added to a ticket"""
    org_id = ticket.get('organization_id')
    ticket_number = ticket.get('ticket_number', 'N/A')
    ticket_title = ticket.get('title', 'Untitled')
    ticket_id = ticket.get('id')
    
    ticket_url = f"{FRONTEND_URL}/tickets/{ticket_id}"
    
    # Only send email for public replies, not internal notes
    if comment.get('comment_type') == 'public_reply':
        # Notify requester
        if ticket.get('requester_id'):
            requester = await db.end_users.find_one({"id": ticket['requester_id']}, {"_id": 0})
            if requester and requester.get('email'):
                content_preview = comment.get('content', '')[:200]
                if len(comment.get('content', '')) > 200:
                    content_preview += '...'
                
                content = f"""
                <p>A new reply has been added to your ticket:</p>
                <div style="background: #f9fafb; padding: 16px; border-radius: 8px; margin: 16px 0;">
                    <p style="margin: 0 0 8px 0;"><strong>Ticket:</strong> #{ticket_number}</p>
                    <p style="margin: 0 0 8px 0;"><strong>Subject:</strong> {ticket_title}</p>
                    <p style="margin: 0 0 8px 0;"><strong>From:</strong> {commenter.get('name', 'Support Team')}</p>
                </div>
                <div style="background: #fff7ed; padding: 16px; border-radius: 8px; border-left: 4px solid #f97316;">
                    <p style="margin: 0; color: #1f2937;">{content_preview}</p>
                </div>
                """
                html = get_email_template(
                    f"New Reply on Ticket #{ticket_number}",
                    content,
                    ticket_url,
                    "View Full Conversation"
                )
                asyncio.create_task(send_email_async(requester['email'], f"[FOXITE] New reply on ticket #{ticket_number}", html))
    
    # Notify assigned technician about new comments (internal or public) if they didn't write it
    if ticket.get('assigned_staff_id') and ticket['assigned_staff_id'] != commenter.get('id'):
        assignee = await db.staff_users.find_one({"id": ticket['assigned_staff_id']}, {"_id": 0})
        if assignee:
            comment_type_label = "internal note" if comment.get('comment_type') == 'internal_note' else "reply"
            await create_in_app_notification(
                org_id, assignee['id'],
                f"New {comment_type_label} on #{ticket_number}",
                f"{commenter.get('name', 'Someone')} added a {comment_type_label}"
            )

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

@api_router.get("/organizations/{org_id}/usage")
async def get_organization_usage(org_id: str, current_user: dict = Depends(get_current_user)):
    """Get current resource usage vs plan limits for an organization"""
    if not current_user.get('is_owner') and current_user.get('organization_id') != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    plan = await get_plan_limits(org_id)
    plan_name = plan.get("name", "CORE")
    limits = plan.get("limits", {})
    
    # Get current usage for all limited resources
    usage = {}
    for resource in ["devices", "licenses", "saved_views", "staff_users"]:
        current = await get_current_resource_count(org_id, resource)
        limit = limits.get(resource)
        usage[resource] = {
            "current": current,
            "limit": limit,
            "unlimited": limit is None,
            "percentage": round((current / limit) * 100, 1) if limit else 0,
            "remaining": (limit - current) if limit else None
        }
    
    return {
        "plan": plan_name,
        "usage": usage,
        "features": plan.get("features", {}),
        "can_upgrade": plan_name != "PRIME"
    }

@api_router.get("/plans")
async def get_available_plans():
    """Get all available subscription plans (public endpoint)"""
    plans = []
    for plan_id, plan in PLAN_FEATURES.items():
        plans.append({
            "id": plan_id,
            "name": plan.get("display_name", plan_id),
            "price_per_seat": plan.get("price_per_seat"),
            "min_seats": plan.get("min_seats", 1),
            "yearly_discount": plan.get("yearly_discount", 0.15),
            "max_slas": plan.get("max_slas"),
            "currency": plan.get("currency", "USD"),
            "limits": plan.get("limits", {}),
            "features": plan.get("features", {})
        })
    return plans

@api_router.get("/pricing/calculate")
async def calculate_plan_pricing(plan: str = "CORE", seats: int = 3, billing: str = "monthly"):
    """Calculate pricing for a plan configuration (public endpoint)"""
    if plan not in PLAN_FEATURES:
        raise HTTPException(status_code=400, detail="Invalid plan")
    if billing not in [BillingCycle.MONTHLY, BillingCycle.YEARLY]:
        raise HTTPException(status_code=400, detail="Invalid billing cycle")
    return calculate_pricing(plan, seats, billing)

@api_router.get("/organization/billing")
async def get_organization_billing(current_user: dict = Depends(get_current_user)):
    """Get billing information for current organization"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Owner account has no billing")
    
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    plan_id = org.get("plan", "CORE")
    billing_cycle = org.get("billing_cycle", BillingCycle.MONTHLY)
    seat_count = org.get("seat_count", 3)
    
    # Get pricing info
    pricing = calculate_pricing(plan_id, seat_count, billing_cycle)
    
    # Get seat usage
    seat_info = await check_seat_availability(org_id)
    
    # Get SLA usage
    sla_info = await check_sla_limit(org_id)
    
    return {
        "organization_id": org_id,
        "organization_name": org.get("name"),
        "status": org.get("status", "active"),
        "trial_ends_at": org.get("trial_ends_at"),
        "pricing": pricing,
        "seats": seat_info,
        "sla_limits": sla_info
    }

@api_router.patch("/organization/seats")
async def update_organization_seats(seat_count: int, current_user: dict = Depends(get_current_user)):
    """Update seat count for organization (Admin only)"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    if current_user.get('role') not in [UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only admins can modify seats")
    
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    plan_id = org.get("plan", "CORE")
    plan = PLAN_FEATURES.get(plan_id, PLAN_FEATURES["CORE"])
    min_seats = plan.get("min_seats", 3)
    
    # Validate minimum seats
    if seat_count < min_seats:
        raise HTTPException(status_code=400, detail=f"{plan_id} plan requires minimum {min_seats} seats")
    
    # Check current users don't exceed new seat count
    current_users = await db.staff_users.count_documents({"organization_id": org_id, "status": "active"})
    if seat_count < current_users:
        raise HTTPException(status_code=400, detail=f"Cannot reduce seats below current user count ({current_users})")
    
    await db.organizations.update_one({"id": org_id}, {"$set": {"seat_count": seat_count}})
    
    return {"message": "Seat count updated", "seat_count": seat_count}

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

@api_router.get("/client-companies/{company_id}")
async def get_client_company(company_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific client company"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    company = await db.client_companies.find_one({"id": company_id, "organization_id": org_id}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if isinstance(company.get('created_at'), str):
        company['created_at'] = datetime.fromisoformat(company['created_at'])
    
    return company

@api_router.patch("/client-companies/{company_id}")
async def update_client_company(company_id: str, update_data: dict, current_user: dict = Depends(get_current_user)):
    """Update a client company"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if current_user.get('role') not in ['admin', 'supervisor']:
        raise HTTPException(status_code=403, detail="Only admin/supervisor can update companies")
    
    company = await db.client_companies.find_one({"id": company_id, "organization_id": org_id}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Filter allowed fields
    allowed_fields = ['name', 'domain', 'industry', 'country', 'city', 'address', 'phone', 'contact_email', 'status', 'custom_fields_data']
    update_dict = {k: v for k, v in update_data.items() if k in allowed_fields and v is not None}
    
    if update_dict:
        await db.client_companies.update_one({"id": company_id}, {"$set": update_dict})
        await log_audit(org_id, current_user['id'], "UPDATE", "company", company_id)
    
    updated = await db.client_companies.find_one({"id": company_id}, {"_id": 0})
    return updated

@api_router.delete("/client-companies/{company_id}")
async def delete_client_company(company_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a client company"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if current_user.get('role') not in ['admin', 'supervisor']:
        raise HTTPException(status_code=403, detail="Only admin/supervisor can delete companies")
    
    company = await db.client_companies.find_one({"id": company_id, "organization_id": org_id}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check for linked end users
    linked_users = await db.end_users.count_documents({"client_company_id": company_id})
    if linked_users > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete company with {linked_users} linked end users")
    
    await db.client_companies.delete_one({"id": company_id})
    await log_audit(org_id, current_user['id'], "DELETE", "company", company_id)
    
    return {"message": "Company deleted"}

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

@api_router.post("/tickets")
async def create_ticket(ticket_data: TicketCreate, current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners cannot create tickets directly")
    
    # Check if org is suspended
    await enforce_not_suspended(org_id)
    
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
    
    # Apply SLA policy based on priority
    await apply_sla_to_ticket(ticket.id, org_id, ticket.priority, ticket.created_at)
    
    # Get updated ticket with SLA info
    updated_ticket = await db.tickets.find_one({"id": ticket.id}, {"_id": 0})
    
    # Send notifications for ticket creation
    asyncio.create_task(notify_ticket_created(updated_ticket, current_user))
    
    # Convert datetime strings back to objects for response
    for field in ['created_at', 'updated_at', 'response_due_at', 'resolution_due_at', 'first_response_at']:
        if updated_ticket.get(field) and isinstance(updated_ticket[field], str):
            updated_ticket[field] = datetime.fromisoformat(updated_ticket[field])
    
    return updated_ticket

@api_router.get("/tickets", response_model=List[Ticket])
async def list_tickets(
    current_user: dict = Depends(get_current_user),
    filters: Optional[str] = None
):
    """List tickets with optional filtering"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners must specify organization")
    
    # Base query with multi-tenant isolation
    query = {"organization_id": org_id}
    
    # Apply role-based filtering
    if current_user.get('role') == UserRole.TECHNICIAN:
        query["assigned_staff_id"] = current_user['id']
    
    # Parse and apply filters if provided
    if filters:
        try:
            import json
            filter_dict = json.loads(filters)
            filter_query = parse_filters(filter_dict, 'tickets')
            query.update(filter_query)
        except:
            raise HTTPException(status_code=400, detail="Invalid filter format")
    
    tickets = await db.tickets.find(query, {"_id": 0}).to_list(1000)
    
    # Convert datetime strings
    for ticket in tickets:
        for field in ['created_at', 'updated_at', 'response_due_at', 'resolution_due_at', 'first_response_at']:
            if ticket.get(field) and isinstance(ticket[field], str):
                ticket[field] = datetime.fromisoformat(ticket[field])
    
    return tickets

@api_router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    
    ticket = await db.tickets.find_one({"id": ticket_id, "organization_id": org_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if isinstance(ticket.get('created_at'), str):
        ticket['created_at'] = datetime.fromisoformat(ticket['created_at'])
    if isinstance(ticket.get('updated_at'), str):
        ticket['updated_at'] = datetime.fromisoformat(ticket['updated_at'])
    
    # Calculate total time spent from sessions
    sessions = await db.sessions.find(
        {"ticket_id": ticket_id, "organization_id": org_id},
        {"_id": 0, "duration_minutes": 1}
    ).to_list(1000)
    
    total_time_spent = sum(s.get('duration_minutes', 0) for s in sessions if s.get('duration_minutes'))
    ticket['total_time_spent'] = total_time_spent
    
    return ticket

@api_router.patch("/tickets/{ticket_id}", response_model=Ticket)
async def update_ticket(ticket_id: str, update_data: TicketUpdate, current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    
    ticket = await db.tickets.find_one({"id": ticket_id, "organization_id": org_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Store old values for notification comparison
    old_status = ticket.get('status')
    old_assigned_staff_id = ticket.get('assigned_staff_id')
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    if update_dict:
        await db.tickets.update_one({"id": ticket_id}, {"$set": update_dict})
        await log_audit(org_id, current_user['id'], "UPDATE", "ticket", ticket_id)
    
    updated_ticket = await db.tickets.find_one({"id": ticket_id}, {"_id": 0})
    
    # Send notifications for status change
    new_status = update_data.status
    if new_status and new_status != old_status:
        asyncio.create_task(notify_ticket_status_changed(updated_ticket, old_status, new_status, current_user))
    
    # Send notifications for assignment change
    new_assigned_staff_id = update_data.assigned_staff_id
    if new_assigned_staff_id and new_assigned_staff_id != old_assigned_staff_id:
        asyncio.create_task(notify_ticket_assigned(updated_ticket, new_assigned_staff_id, current_user))
    
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
    
    # Send notifications for new comment
    asyncio.create_task(notify_ticket_comment_added(ticket, doc, current_user))
    
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

# ==================== SESSION ROUTES ====================

@api_router.post("/sessions/start", response_model=Session)
async def start_session(session_data: SessionStart, current_user: dict = Depends(get_current_user)):
    """Start a new time tracking session"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners cannot track time")
    
    # Verify ticket exists
    ticket = await db.tickets.find_one({"id": session_data.ticket_id, "organization_id": org_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check for active sessions
    active_session = await db.sessions.find_one({
        "organization_id": org_id,
        "agent_id": current_user['id'],
        "end_time": None
    }, {"_id": 0})
    
    if active_session:
        raise HTTPException(status_code=400, detail="You have an active session. Please stop it before starting a new one.")
    
    start_time = datetime.now(timezone.utc)
    
    # Check for overlaps (shouldn't happen with active session check, but double-check)
    has_overlap = await check_session_overlap(org_id, current_user['id'], start_time)
    if has_overlap:
        raise HTTPException(status_code=400, detail="Session overlaps with existing session")
    
    session = Session(
        organization_id=org_id,
        ticket_id=session_data.ticket_id,
        agent_id=current_user['id'],
        agent_name=current_user['name'],
        start_time=start_time,
        note=session_data.note
    )
    
    doc = session.model_dump()
    doc['start_time'] = doc['start_time'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.sessions.insert_one(doc)
    await log_audit(org_id, current_user['id'], "START", "session", session.id)
    
    return session

@api_router.post("/sessions/stop", response_model=Session)
async def stop_session(session_data: SessionStop, current_user: dict = Depends(get_current_user)):
    """Stop an active time tracking session"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Find the session
    session = await db.sessions.find_one({
        "id": session_data.session_id,
        "organization_id": org_id,
        "agent_id": current_user['id']
    }, {"_id": 0})
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.get('end_time'):
        raise HTTPException(status_code=400, detail="Session already stopped")
    
    end_time = datetime.now(timezone.utc)
    start_time = session.get('start_time')
    
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    
    duration = calculate_duration(start_time, end_time)
    
    # Update session
    update_data = {
        "end_time": end_time.isoformat(),
        "duration_minutes": duration
    }
    
    if session_data.note:
        update_data["note"] = session_data.note
    
    await db.sessions.update_one(
        {"id": session_data.session_id},
        {"$set": update_data}
    )
    
    await log_audit(org_id, current_user['id'], "STOP", "session", session_data.session_id)
    
    # Get updated session
    updated_session = await db.sessions.find_one({"id": session_data.session_id}, {"_id": 0})
    
    if isinstance(updated_session.get('start_time'), str):
        updated_session['start_time'] = datetime.fromisoformat(updated_session['start_time'])
    if isinstance(updated_session.get('end_time'), str):
        updated_session['end_time'] = datetime.fromisoformat(updated_session['end_time'])
    if isinstance(updated_session.get('created_at'), str):
        updated_session['created_at'] = datetime.fromisoformat(updated_session['created_at'])
    
    return updated_session

@api_router.post("/sessions/manual", response_model=Session)
async def create_manual_session(session_data: SessionManual, current_user: dict = Depends(get_current_user)):
    """Create a completed session manually (with start and end time)"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners cannot create sessions")
    
    # Verify ticket exists
    ticket = await db.tickets.find_one({"id": session_data.ticket_id, "organization_id": org_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Validate times
    if session_data.end_time <= session_data.start_time:
        raise HTTPException(status_code=400, detail="End time must be after start time")
    
    # Check for overlaps
    has_overlap = await check_session_overlap(
        org_id,
        current_user['id'],
        session_data.start_time,
        session_data.end_time
    )
    
    if has_overlap:
        raise HTTPException(status_code=400, detail="Session overlaps with existing session")
    
    duration = calculate_duration(session_data.start_time, session_data.end_time)
    
    session = Session(
        organization_id=org_id,
        ticket_id=session_data.ticket_id,
        agent_id=current_user['id'],
        agent_name=current_user['name'],
        start_time=session_data.start_time,
        end_time=session_data.end_time,
        duration_minutes=duration,
        note=session_data.note
    )
    
    doc = session.model_dump()
    doc['start_time'] = doc['start_time'].isoformat()
    doc['end_time'] = doc['end_time'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.sessions.insert_one(doc)
    await log_audit(org_id, current_user['id'], "CREATE", "session", session.id)
    
    return session

@api_router.get("/tickets/{ticket_id}/sessions", response_model=List[Session])
async def list_ticket_sessions(ticket_id: str, current_user: dict = Depends(get_current_user)):
    """List all time tracking sessions for a ticket"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verify ticket access
    ticket = await db.tickets.find_one({"id": ticket_id, "organization_id": org_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    sessions = await db.sessions.find(
        {"ticket_id": ticket_id, "organization_id": org_id},
        {"_id": 0}
    ).sort("start_time", -1).to_list(1000)
    
    for session in sessions:
        if isinstance(session.get('start_time'), str):
            session['start_time'] = datetime.fromisoformat(session['start_time'])
        if session.get('end_time') and isinstance(session.get('end_time'), str):
            session['end_time'] = datetime.fromisoformat(session['end_time'])
        if isinstance(session.get('created_at'), str):
            session['created_at'] = datetime.fromisoformat(session['created_at'])
    
    return sessions

@api_router.get("/staff-users/{agent_id}/sessions", response_model=List[Session])
async def list_agent_sessions(agent_id: str, current_user: dict = Depends(get_current_user)):
    """List all time tracking sessions for an agent"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verify agent belongs to org and user has access
    if current_user['id'] != agent_id and current_user.get('role') not in ['admin', 'supervisor']:
        raise HTTPException(status_code=403, detail="You can only view your own sessions")
    
    sessions = await db.sessions.find(
        {"agent_id": agent_id, "organization_id": org_id},
        {"_id": 0}
    ).sort("start_time", -1).to_list(1000)
    
    for session in sessions:
        if isinstance(session.get('start_time'), str):
            session['start_time'] = datetime.fromisoformat(session['start_time'])
        if session.get('end_time') and isinstance(session.get('end_time'), str):
            session['end_time'] = datetime.fromisoformat(session['end_time'])
        if isinstance(session.get('created_at'), str):
            session['created_at'] = datetime.fromisoformat(session['created_at'])
    
    return sessions

@api_router.get("/sessions", response_model=List[Session])
async def list_sessions(
    current_user: dict = Depends(get_current_user),
    filters: Optional[str] = None
):
    """List all sessions with optional filtering"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Base query with multi-tenant isolation
    query = {"organization_id": org_id}
    
    # Technicians only see their own sessions
    if current_user.get('role') == UserRole.TECHNICIAN:
        query["agent_id"] = current_user['id']
    
    # Parse and apply filters if provided
    if filters:
        try:
            import json
            filter_dict = json.loads(filters)
            filter_query = parse_filters(filter_dict, 'sessions')
            query.update(filter_query)
        except:
            raise HTTPException(status_code=400, detail="Invalid filter format")
    
    sessions = await db.sessions.find(query, {"_id": 0}).sort("start_time", -1).to_list(1000)
    
    # Convert datetime strings
    for session in sessions:
        if isinstance(session.get('start_time'), str):
            session['start_time'] = datetime.fromisoformat(session['start_time'])
        if session.get('end_time') and isinstance(session.get('end_time'), str):
            session['end_time'] = datetime.fromisoformat(session['end_time'])
        if isinstance(session.get('created_at'), str):
            session['created_at'] = datetime.fromisoformat(session['created_at'])
    
    return sessions

# ==================== SLA POLICY ROUTES ====================

@api_router.post("/sla-policies", response_model=SLAPolicy)
async def create_sla_policy(policy_data: SLAPolicyCreate, current_user: dict = Depends(get_current_user)):
    """Create SLA policy for an organization"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners cannot create SLA policies directly")
    
    # Check if suspended
    await enforce_not_suspended(org_id)
    
    # Check if admin
    if current_user.get('role') not in ['admin']:
        raise HTTPException(status_code=403, detail="Only admins can manage SLA policies")
    
    # Check SLA limit based on plan
    sla_info = await check_sla_limit(org_id)
    if not sla_info["can_add_sla"]:
        org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
        plan_id = org.get("plan", "CORE")
        raise HTTPException(
            status_code=403, 
            detail=f"SLA limit reached ({sla_info['current_slas']}/{sla_info['max_slas']}). Upgrade from {plan_id} plan for more SLAs."
        )
    
    # Check if policy for this priority already exists
    existing = await db.sla_policies.find_one({
        "organization_id": org_id,
        "priority": policy_data.priority
    }, {"_id": 0})
    
    if existing:
        raise HTTPException(status_code=400, detail=f"SLA policy for priority '{policy_data.priority}' already exists")
    
    policy = SLAPolicy(
        organization_id=org_id,
        name=policy_data.name,
        priority=policy_data.priority,
        response_time_minutes=policy_data.response_time_minutes,
        resolution_time_minutes=policy_data.resolution_time_minutes
    )
    
    doc = policy.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.sla_policies.insert_one(doc)
    await log_audit(org_id, current_user['id'], "CREATE", "sla_policy", policy.id)
    
    return policy

@api_router.get("/sla-policies", response_model=List[SLAPolicy])
async def list_sla_policies(current_user: dict = Depends(get_current_user)):
    """List all SLA policies for organization"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    policies = await db.sla_policies.find({"organization_id": org_id}, {"_id": 0}).to_list(100)
    
    for policy in policies:
        if isinstance(policy.get('created_at'), str):
            policy['created_at'] = datetime.fromisoformat(policy['created_at'])
    
    return policies

@api_router.get("/sla-policies/{policy_id}", response_model=SLAPolicy)
async def get_sla_policy(policy_id: str, current_user: dict = Depends(get_current_user)):
    """Get specific SLA policy"""
    org_id = current_user.get('organization_id')
    
    policy = await db.sla_policies.find_one({
        "id": policy_id,
        "organization_id": org_id
    }, {"_id": 0})
    
    if not policy:
        raise HTTPException(status_code=404, detail="SLA policy not found")
    
    if isinstance(policy.get('created_at'), str):
        policy['created_at'] = datetime.fromisoformat(policy['created_at'])
    
    return policy

@api_router.patch("/sla-policies/{policy_id}", response_model=SLAPolicy)
async def update_sla_policy(
    policy_id: str,
    update_data: SLAPolicyUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update SLA policy"""
    org_id = current_user.get('organization_id')
    
    if current_user.get('role') not in ['admin']:
        raise HTTPException(status_code=403, detail="Only admins can update SLA policies")
    
    policy = await db.sla_policies.find_one({
        "id": policy_id,
        "organization_id": org_id
    }, {"_id": 0})
    
    if not policy:
        raise HTTPException(status_code=404, detail="SLA policy not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if update_dict:
        await db.sla_policies.update_one({"id": policy_id}, {"$set": update_dict})
        await log_audit(org_id, current_user['id'], "UPDATE", "sla_policy", policy_id)
    
    updated_policy = await db.sla_policies.find_one({"id": policy_id}, {"_id": 0})
    
    if isinstance(updated_policy.get('created_at'), str):
        updated_policy['created_at'] = datetime.fromisoformat(updated_policy['created_at'])
    
    return updated_policy

# ==================== CUSTOM FIELDS ROUTES ====================

@api_router.get("/custom-fields")
async def get_custom_fields(entity_type: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Get custom fields for organization, optionally filtered by entity type"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {"organization_id": org_id}
    if entity_type:
        query["entity_type"] = entity_type
    
    fields = await db.custom_fields.find(query, {"_id": 0}).sort("order", 1).to_list(1000)
    
    for field in fields:
        if isinstance(field.get('created_at'), str):
            field['created_at'] = datetime.fromisoformat(field['created_at'])
    
    return fields

@api_router.post("/custom-fields", response_model=CustomField)
async def create_custom_field(field_data: CustomFieldCreate, current_user: dict = Depends(get_current_user)):
    """Create a custom field (Admin only)"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if current_user.get('role') not in ['admin', 'supervisor']:
        raise HTTPException(status_code=403, detail="Only admin/supervisor can manage custom fields")
    
    # Validate entity_type
    valid_types = ['ticket', 'device', 'company', 'end_user', 'license', 'task']
    if field_data.entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entity_type. Must be one of: {valid_types}")
    
    # Validate field_type
    valid_field_types = ['text', 'number', 'date', 'boolean', 'dropdown', 'file']
    if field_data.field_type not in valid_field_types:
        raise HTTPException(status_code=400, detail=f"Invalid field_type. Must be one of: {valid_field_types}")
    
    field = CustomField(
        organization_id=org_id,
        entity_type=field_data.entity_type,
        label=field_data.label,
        field_type=field_data.field_type,
        required=field_data.required,
        options=field_data.options,
        order=field_data.order
    )
    
    doc = field.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.custom_fields.insert_one(doc)
    await log_audit(org_id, current_user['id'], "CREATE", "custom_field", field.id)
    
    return field

@api_router.patch("/custom-fields/{field_id}")
async def update_custom_field(field_id: str, update_data: CustomFieldUpdate, current_user: dict = Depends(get_current_user)):
    """Update a custom field"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if current_user.get('role') not in ['admin', 'supervisor']:
        raise HTTPException(status_code=403, detail="Only admin/supervisor can manage custom fields")
    
    field = await db.custom_fields.find_one({"id": field_id, "organization_id": org_id}, {"_id": 0})
    if not field:
        raise HTTPException(status_code=404, detail="Custom field not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if update_dict:
        await db.custom_fields.update_one({"id": field_id}, {"$set": update_dict})
        await log_audit(org_id, current_user['id'], "UPDATE", "custom_field", field_id)
    
    updated = await db.custom_fields.find_one({"id": field_id}, {"_id": 0})
    return updated

@api_router.delete("/custom-fields/{field_id}")
async def delete_custom_field(field_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a custom field"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if current_user.get('role') not in ['admin', 'supervisor']:
        raise HTTPException(status_code=403, detail="Only admin/supervisor can manage custom fields")
    
    field = await db.custom_fields.find_one({"id": field_id, "organization_id": org_id}, {"_id": 0})
    if not field:
        raise HTTPException(status_code=404, detail="Custom field not found")
    
    await db.custom_fields.delete_one({"id": field_id})
    await log_audit(org_id, current_user['id'], "DELETE", "custom_field", field_id)
    
    return {"message": "Custom field deleted"}

@api_router.post("/custom-fields/reorder")
async def reorder_custom_fields(field_orders: List[dict], current_user: dict = Depends(get_current_user)):
    """Reorder custom fields. Expects list of {id, order}"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if current_user.get('role') not in ['admin', 'supervisor']:
        raise HTTPException(status_code=403, detail="Only admin/supervisor can manage custom fields")
    
    for item in field_orders:
        if 'id' in item and 'order' in item:
            await db.custom_fields.update_one(
                {"id": item['id'], "organization_id": org_id},
                {"$set": {"order": item['order']}}
            )
    
    return {"message": "Fields reordered"}

# ==================== ATTACHMENTS ROUTES ====================

@api_router.get("/attachments")
async def get_attachments(entity_type: str, entity_id: str, current_user: dict = Depends(get_current_user)):
    """Get attachments for an entity"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    attachments = await db.attachments.find({
        "organization_id": org_id,
        "entity_type": entity_type,
        "entity_id": entity_id
    }, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    for att in attachments:
        if isinstance(att.get('created_at'), str):
            att['created_at'] = datetime.fromisoformat(att['created_at'])
    
    return attachments

@api_router.post("/attachments", response_model=Attachment)
async def create_attachment(attachment_data: AttachmentCreate, current_user: dict = Depends(get_current_user)):
    """Create an attachment record"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if suspended
    await enforce_not_suspended(org_id)
    
    attachment = Attachment(
        organization_id=org_id,
        entity_type=attachment_data.entity_type,
        entity_id=attachment_data.entity_id,
        file_name=attachment_data.file_name,
        file_url=attachment_data.file_url,
        file_size=attachment_data.file_size,
        mime_type=attachment_data.mime_type,
        uploaded_by=current_user['id']
    )
    
    doc = attachment.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.attachments.insert_one(doc)
    await log_audit(org_id, current_user['id'], "CREATE", "attachment", attachment.id)
    
    return attachment

@api_router.delete("/attachments/{attachment_id}")
async def delete_attachment(attachment_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an attachment"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    attachment = await db.attachments.find_one({"id": attachment_id, "organization_id": org_id}, {"_id": 0})
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # Only uploader, admin, or supervisor can delete
    if attachment['uploaded_by'] != current_user['id'] and current_user.get('role') not in ['admin', 'supervisor']:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.attachments.delete_one({"id": attachment_id})
    await log_audit(org_id, current_user['id'], "DELETE", "attachment", attachment_id)
    
    return {"message": "Attachment deleted"}

# ==================== BUSINESS HOURS ROUTES ====================

@api_router.post("/business-hours", response_model=BusinessHours)
async def create_or_update_business_hours(
    hours_data: BusinessHoursCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create or update business hours for organization"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if current_user.get('role') not in ['admin']:
        raise HTTPException(status_code=403, detail="Only admins can manage business hours")
    
    # Check if business hours already exist
    existing = await db.business_hours.find_one({"organization_id": org_id}, {"_id": 0})
    
    if existing:
        # Update existing
        update_dict = hours_data.model_dump()
        await db.business_hours.update_one(
            {"id": existing['id']},
            {"$set": update_dict}
        )
        await log_audit(org_id, current_user['id'], "UPDATE", "business_hours", existing['id'])
        
        updated = await db.business_hours.find_one({"id": existing['id']}, {"_id": 0})
        if isinstance(updated.get('created_at'), str):
            updated['created_at'] = datetime.fromisoformat(updated['created_at'])
        return updated
    else:
        # Create new
        hours = BusinessHours(
            organization_id=org_id,
            timezone=hours_data.timezone,
            work_days=hours_data.work_days,
            start_time=hours_data.start_time,
            end_time=hours_data.end_time
        )
        
        doc = hours.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        
        await db.business_hours.insert_one(doc)
        await log_audit(org_id, current_user['id'], "CREATE", "business_hours", hours.id)
        
        return hours

@api_router.get("/business-hours", response_model=BusinessHours)
async def get_business_hours(current_user: dict = Depends(get_current_user)):
    """Get business hours for organization"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    hours = await db.business_hours.find_one({"organization_id": org_id}, {"_id": 0})
    
    if not hours:
        raise HTTPException(status_code=404, detail="Business hours not configured")
    
    if isinstance(hours.get('created_at'), str):
        hours['created_at'] = datetime.fromisoformat(hours['created_at'])
    
    return hours

# ==================== SAVED VIEWS ROUTES ====================

@api_router.post("/saved-views", response_model=SavedView)
async def create_saved_view(view_data: SavedViewCreate, current_user: dict = Depends(get_current_user)):
    """Create a saved view/filter"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # PLAN ENFORCEMENT: Check feature access (saved_filters not available on CORE)
    await enforce_feature_access(org_id, "saved_filters", required_plan="PLUS")
    
    # PLAN ENFORCEMENT: Check saved views limit
    await enforce_resource_limit(org_id, "saved_views")
    
    # Validate entity type
    if view_data.entity_type not in ['tickets', 'tasks', 'sessions']:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    view = SavedView(
        organization_id=org_id,
        entity_type=view_data.entity_type,
        name=view_data.name,
        filters=view_data.filters,
        created_by=current_user['id'],
        created_by_name=current_user['name'],
        is_shared=view_data.is_shared
    )
    
    doc = view.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.saved_views.insert_one(doc)
    await log_audit(org_id, current_user['id'], "CREATE", "saved_view", view.id)
    
    return view

@api_router.get("/saved-views", response_model=List[SavedView])
async def list_saved_views(
    current_user: dict = Depends(get_current_user),
    entity: Optional[str] = None
):
    """List saved views, optionally filtered by entity type"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Build query: user's own views OR shared views in organization
    query = {
        "organization_id": org_id,
        "$or": [
            {"created_by": current_user['id']},
            {"is_shared": True}
        ]
    }
    
    # Filter by entity type if provided
    if entity:
        if entity not in ['tickets', 'tasks', 'sessions']:
            raise HTTPException(status_code=400, detail="Invalid entity type")
        query["entity_type"] = entity
    
    views = await db.saved_views.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Convert datetime strings
    for view in views:
        if isinstance(view.get('created_at'), str):
            view['created_at'] = datetime.fromisoformat(view['created_at'])
    
    return views

@api_router.get("/saved-views/{view_id}", response_model=SavedView)
async def get_saved_view(view_id: str, current_user: dict = Depends(get_current_user)):
    """Get specific saved view"""
    org_id = current_user.get('organization_id')
    
    view = await db.saved_views.find_one({
        "id": view_id,
        "organization_id": org_id
    }, {"_id": 0})
    
    if not view:
        raise HTTPException(status_code=404, detail="Saved view not found")
    
    # Check access: must be creator or view must be shared
    if view['created_by'] != current_user['id'] and not view.get('is_shared'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if isinstance(view.get('created_at'), str):
        view['created_at'] = datetime.fromisoformat(view['created_at'])
    
    return view

@api_router.patch("/saved-views/{view_id}", response_model=SavedView)
async def update_saved_view(
    view_id: str,
    update_data: SavedViewUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update saved view"""
    org_id = current_user.get('organization_id')
    
    view = await db.saved_views.find_one({
        "id": view_id,
        "organization_id": org_id,
        "created_by": current_user['id']
    }, {"_id": 0})
    
    if not view:
        raise HTTPException(status_code=404, detail="Saved view not found or access denied")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if update_dict:
        await db.saved_views.update_one({"id": view_id}, {"$set": update_dict})
        await log_audit(org_id, current_user['id'], "UPDATE", "saved_view", view_id)
    
    updated_view = await db.saved_views.find_one({"id": view_id}, {"_id": 0})
    
    if isinstance(updated_view.get('created_at'), str):
        updated_view['created_at'] = datetime.fromisoformat(updated_view['created_at'])
    
    return updated_view

@api_router.delete("/saved-views/{view_id}")
async def delete_saved_view(view_id: str, current_user: dict = Depends(get_current_user)):
    """Delete saved view"""
    org_id = current_user.get('organization_id')
    
    view = await db.saved_views.find_one({
        "id": view_id,
        "organization_id": org_id,
        "created_by": current_user['id']
    }, {"_id": 0})
    
    if not view:
        raise HTTPException(status_code=404, detail="Saved view not found or access denied")
    
    await db.saved_views.delete_one({"id": view_id})
    await log_audit(org_id, current_user['id'], "DELETE", "saved_view", view_id)
    
    return {"message": "Saved view deleted"}

# ==================== DEVICE ROUTES (ASSET INVENTORY) ====================

@api_router.post("/devices", response_model=Device)
async def create_device(device_data: DeviceCreate, current_user: dict = Depends(get_current_user)):
    """Create device asset"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # PLAN ENFORCEMENT: Check device limit
    await enforce_resource_limit(org_id, "devices")
    
    # Verify company belongs to org
    company = await db.client_companies.find_one({
        "id": device_data.client_company_id,
        "organization_id": org_id
    }, {"_id": 0})
    
    if not company:
        raise HTTPException(status_code=404, detail="Client company not found")
    
    device = Device(
        organization_id=org_id,
        client_company_id=device_data.client_company_id,
        name=device_data.name,
        device_type=device_data.device_type,
        manufacturer=device_data.manufacturer,
        model=device_data.model,
        serial_number=device_data.serial_number,
        os_type=device_data.os_type,
        os_version=device_data.os_version,
        assigned_to=device_data.assigned_to,
        status=device_data.status,
        purchase_date=device_data.purchase_date,
        warranty_expiry=device_data.warranty_expiry,
        notes=device_data.notes
    )
    
    doc = device.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('purchase_date'):
        doc['purchase_date'] = doc['purchase_date'].isoformat()
    if doc.get('warranty_expiry'):
        doc['warranty_expiry'] = doc['warranty_expiry'].isoformat()
    
    await db.devices.insert_one(doc)
    await log_audit(org_id, current_user['id'], "CREATE", "device", device.id)
    
    return device

@api_router.get("/devices", response_model=List[Device])
async def list_devices(
    current_user: dict = Depends(get_current_user),
    filters: Optional[str] = None
):
    """List devices with optional filtering"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {"organization_id": org_id}
    
    # Apply filters if provided
    if filters:
        try:
            import json
            filter_dict = json.loads(filters)
            
            if filter_dict.get('status'):
                query['status'] = filter_dict['status']
            if filter_dict.get('device_type'):
                query['device_type'] = filter_dict['device_type']
            if filter_dict.get('client_company_id'):
                query['client_company_id'] = filter_dict['client_company_id']
            if filter_dict.get('assigned_to'):
                query['assigned_to'] = filter_dict['assigned_to']
            if filter_dict.get('search'):
                query['$or'] = [
                    {'name': {'$regex': filter_dict['search'], '$options': 'i'}},
                    {'serial_number': {'$regex': filter_dict['search'], '$options': 'i'}}
                ]
        except:
            raise HTTPException(status_code=400, detail="Invalid filter format")
    
    devices = await db.devices.find(query, {"_id": 0}).to_list(1000)
    
    # Convert datetime strings
    for device in devices:
        for field in ['created_at', 'updated_at', 'purchase_date', 'warranty_expiry']:
            if device.get(field) and isinstance(device[field], str):
                device[field] = datetime.fromisoformat(device[field])
    
    return devices

@api_router.get("/devices/{device_id}", response_model=Device)
async def get_device(device_id: str, current_user: dict = Depends(get_current_user)):
    """Get device details"""
    org_id = current_user.get('organization_id')
    
    device = await db.devices.find_one({
        "id": device_id,
        "organization_id": org_id
    }, {"_id": 0})
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Convert datetime strings
    for field in ['created_at', 'updated_at', 'purchase_date', 'warranty_expiry']:
        if device.get(field) and isinstance(device[field], str):
            device[field] = datetime.fromisoformat(device[field])
    
    return device

@api_router.patch("/devices/{device_id}", response_model=Device)
async def update_device(
    device_id: str,
    update_data: DeviceUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update device"""
    org_id = current_user.get('organization_id')
    
    device = await db.devices.find_one({
        "id": device_id,
        "organization_id": org_id
    }, {"_id": 0})
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # Convert datetime fields
    for field in ['purchase_date', 'warranty_expiry']:
        if update_dict.get(field) and isinstance(update_dict[field], datetime):
            update_dict[field] = update_dict[field].isoformat()
    
    if update_dict:
        await db.devices.update_one({"id": device_id}, {"$set": update_dict})
        await log_audit(org_id, current_user['id'], "UPDATE", "device", device_id)
    
    updated_device = await db.devices.find_one({"id": device_id}, {"_id": 0})
    
    # Convert datetime strings
    for field in ['created_at', 'updated_at', 'purchase_date', 'warranty_expiry']:
        if updated_device.get(field) and isinstance(updated_device[field], str):
            updated_device[field] = datetime.fromisoformat(updated_device[field])
    
    return updated_device

@api_router.delete("/devices/{device_id}")
async def delete_device(device_id: str, current_user: dict = Depends(get_current_user)):
    """Delete device"""
    org_id = current_user.get('organization_id')
    
    device = await db.devices.find_one({
        "id": device_id,
        "organization_id": org_id
    }, {"_id": 0})
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    await db.devices.delete_one({"id": device_id})
    await log_audit(org_id, current_user['id'], "DELETE", "device", device_id)
    
    return {"message": "Device deleted"}

@api_router.get("/devices/{device_id}/tickets", response_model=List[Ticket])
async def list_device_tickets(device_id: str, current_user: dict = Depends(get_current_user)):
    """List all tickets linked to a device"""
    org_id = current_user.get('organization_id')
    
    # Verify device exists
    device = await db.devices.find_one({
        "id": device_id,
        "organization_id": org_id
    }, {"_id": 0})
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    tickets = await db.tickets.find({
        "device_id": device_id,
        "organization_id": org_id
    }, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Convert datetime strings
    for ticket in tickets:
        for field in ['created_at', 'updated_at', 'response_due_at', 'resolution_due_at', 'first_response_at']:
            if ticket.get(field) and isinstance(ticket[field], str):
                ticket[field] = datetime.fromisoformat(ticket[field])
    
    return tickets

@api_router.get("/client-companies/{company_id}/devices", response_model=List[Device])
async def list_company_devices(company_id: str, current_user: dict = Depends(get_current_user)):
    """List all devices for a client company"""
    org_id = current_user.get('organization_id')
    
    # Verify company belongs to org
    company = await db.client_companies.find_one({
        "id": company_id,
        "organization_id": org_id
    }, {"_id": 0})
    
    if not company:
        raise HTTPException(status_code=404, detail="Client company not found")
    
    devices = await db.devices.find({
        "client_company_id": company_id,
        "organization_id": org_id
    }, {"_id": 0}).to_list(1000)
    
    # Convert datetime strings
    for device in devices:
        for field in ['created_at', 'updated_at', 'purchase_date', 'warranty_expiry']:
            if device.get(field) and isinstance(device[field], str):
                device[field] = datetime.fromisoformat(device[field])
    
    return devices

# ==================== LICENSE ROUTES (ASSET INVENTORY) ====================

@api_router.post("/licenses", response_model=License)
async def create_license(license_data: LicenseCreate, current_user: dict = Depends(get_current_user)):
    """Create license/service asset"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # PLAN ENFORCEMENT: Check feature access (licenses not available on CORE)
    await enforce_feature_access(org_id, "licenses_inventory", required_plan="PLUS")
    
    # PLAN ENFORCEMENT: Check license limit
    await enforce_resource_limit(org_id, "licenses")
    
    # Verify company belongs to org
    company = await db.client_companies.find_one({
        "id": license_data.client_company_id,
        "organization_id": org_id
    }, {"_id": 0})
    
    if not company:
        raise HTTPException(status_code=404, detail="Client company not found")
    
    license_obj = License(
        organization_id=org_id,
        client_company_id=license_data.client_company_id,
        name=license_data.name,
        license_type=license_data.license_type,
        provider=license_data.provider,
        license_key=license_data.license_key,
        assigned_to=license_data.assigned_to,
        quantity=license_data.quantity,
        purchase_date=license_data.purchase_date,
        expiration_date=license_data.expiration_date,
        renewal_cost=license_data.renewal_cost,
        billing_cycle=license_data.billing_cycle,
        status=license_data.status,
        notes=license_data.notes
    )
    
    doc = license_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('purchase_date'):
        doc['purchase_date'] = doc['purchase_date'].isoformat()
    if doc.get('expiration_date'):
        doc['expiration_date'] = doc['expiration_date'].isoformat()
    
    # Calculate expiration status
    expiration_status = calculate_license_expiration_status(doc)
    doc.update(expiration_status)
    
    await db.licenses.insert_one(doc)
    await log_audit(org_id, current_user['id'], "CREATE", "license", license_obj.id)
    
    # Return with calculated fields
    license_obj.days_until_expiration = expiration_status['days_until_expiration']
    license_obj.expiring_soon = expiration_status['expiring_soon']
    license_obj.expired = expiration_status['expired']
    
    return license_obj

@api_router.get("/licenses", response_model=List[License])
async def list_licenses(
    current_user: dict = Depends(get_current_user),
    filters: Optional[str] = None
):
    """List licenses with optional filtering"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {"organization_id": org_id}
    post_filters = {}  # Filters to apply after calculation
    
    # Apply filters if provided
    if filters:
        try:
            import json
            filter_dict = json.loads(filters)
            
            if filter_dict.get('status'):
                query['status'] = filter_dict['status']
            if filter_dict.get('license_type'):
                query['license_type'] = filter_dict['license_type']
            if filter_dict.get('client_company_id'):
                query['client_company_id'] = filter_dict['client_company_id']
            # These are calculated fields - filter after fetching
            if filter_dict.get('expiring_soon') is not None:
                post_filters['expiring_soon'] = filter_dict['expiring_soon']
            if filter_dict.get('expired') is not None:
                post_filters['expired'] = filter_dict['expired']
            if filter_dict.get('search'):
                query['$or'] = [
                    {'name': {'$regex': filter_dict['search'], '$options': 'i'}},
                    {'provider': {'$regex': filter_dict['search'], '$options': 'i'}}
                ]
        except:
            raise HTTPException(status_code=400, detail="Invalid filter format")
    
    licenses = await db.licenses.find(query, {"_id": 0}).to_list(1000)
    
    # Convert datetime strings and calculate expiration status
    result = []
    for license_obj in licenses:
        for field in ['created_at', 'updated_at', 'purchase_date', 'expiration_date']:
            if license_obj.get(field) and isinstance(license_obj[field], str):
                license_obj[field] = datetime.fromisoformat(license_obj[field])
        
        # Recalculate expiration status
        expiration_status = calculate_license_expiration_status(license_obj)
        license_obj.update(expiration_status)
        
        # Apply post-fetch filters on calculated fields
        if post_filters:
            include = True
            if 'expiring_soon' in post_filters and license_obj.get('expiring_soon') != post_filters['expiring_soon']:
                include = False
            if 'expired' in post_filters and license_obj.get('expired') != post_filters['expired']:
                include = False
            if include:
                result.append(license_obj)
        else:
            result.append(license_obj)
    
    return result

@api_router.get("/licenses/expiring", response_model=List[License])
async def list_expiring_licenses(current_user: dict = Depends(get_current_user)):
    """List licenses expiring soon (shortcut endpoint)"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get all licenses and calculate expiration status
    all_licenses = await db.licenses.find({
        "organization_id": org_id
    }, {"_id": 0}).to_list(1000)
    
    expiring_licenses = []
    for license_obj in all_licenses:
        # Convert datetime strings
        for field in ['created_at', 'updated_at', 'purchase_date', 'expiration_date']:
            if license_obj.get(field) and isinstance(license_obj[field], str):
                license_obj[field] = datetime.fromisoformat(license_obj[field])
        
        # Calculate expiration status
        expiration_status = calculate_license_expiration_status(license_obj)
        license_obj.update(expiration_status)
        
        # Filter for expiring soon (< 60 days and not expired)
        if expiration_status.get('expiring_soon') and not expiration_status.get('expired'):
            expiring_licenses.append(license_obj)
    
    return expiring_licenses

@api_router.get("/licenses/{license_id}", response_model=License)
async def get_license(license_id: str, current_user: dict = Depends(get_current_user)):
    """Get license details"""
    org_id = current_user.get('organization_id')
    
    license_obj = await db.licenses.find_one({
        "id": license_id,
        "organization_id": org_id
    }, {"_id": 0})
    
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    
    # Convert datetime strings
    for field in ['created_at', 'updated_at', 'purchase_date', 'expiration_date']:
        if license_obj.get(field) and isinstance(license_obj[field], str):
            license_obj[field] = datetime.fromisoformat(license_obj[field])
    
    # Recalculate expiration status
    expiration_status = calculate_license_expiration_status(license_obj)
    license_obj.update(expiration_status)
    
    return license_obj

@api_router.patch("/licenses/{license_id}", response_model=License)
async def update_license(
    license_id: str,
    update_data: LicenseUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update license"""
    org_id = current_user.get('organization_id')
    
    license_obj = await db.licenses.find_one({
        "id": license_id,
        "organization_id": org_id
    }, {"_id": 0})
    
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # Convert datetime fields
    for field in ['purchase_date', 'expiration_date']:
        if update_dict.get(field) and isinstance(update_dict[field], datetime):
            update_dict[field] = update_dict[field].isoformat()
    
    if update_dict:
        await db.licenses.update_one({"id": license_id}, {"$set": update_dict})
        await log_audit(org_id, current_user['id'], "UPDATE", "license", license_id)
    
    updated_license = await db.licenses.find_one({"id": license_id}, {"_id": 0})
    
    # Convert datetime strings
    for field in ['created_at', 'updated_at', 'purchase_date', 'expiration_date']:
        if updated_license.get(field) and isinstance(updated_license[field], str):
            updated_license[field] = datetime.fromisoformat(updated_license[field])
    
    # Recalculate expiration status
    expiration_status = calculate_license_expiration_status(updated_license)
    updated_license.update(expiration_status)
    
    return updated_license

@api_router.delete("/licenses/{license_id}")
async def delete_license(license_id: str, current_user: dict = Depends(get_current_user)):
    """Delete license"""
    org_id = current_user.get('organization_id')
    
    license_obj = await db.licenses.find_one({
        "id": license_id,
        "organization_id": org_id
    }, {"_id": 0})
    
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    
    await db.licenses.delete_one({"id": license_id})
    await log_audit(org_id, current_user['id'], "DELETE", "license", license_id)
    
    return {"message": "License deleted"}

@api_router.get("/client-companies/{company_id}/licenses", response_model=List[License])
async def list_company_licenses(company_id: str, current_user: dict = Depends(get_current_user)):
    """List all licenses for a client company"""
    org_id = current_user.get('organization_id')
    
    # Verify company belongs to org
    company = await db.client_companies.find_one({
        "id": company_id,
        "organization_id": org_id
    }, {"_id": 0})
    
    if not company:
        raise HTTPException(status_code=404, detail="Client company not found")
    
    licenses = await db.licenses.find({
        "client_company_id": company_id,
        "organization_id": org_id
    }, {"_id": 0}).to_list(1000)
    
    # Convert datetime strings and calculate expiration
    for license_obj in licenses:
        for field in ['created_at', 'updated_at', 'purchase_date', 'expiration_date']:
            if license_obj.get(field) and isinstance(license_obj[field], str):
                license_obj[field] = datetime.fromisoformat(license_obj[field])
        
        expiration_status = calculate_license_expiration_status(license_obj)
        license_obj.update(expiration_status)
    
    return licenses

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
async def list_tasks(
    current_user: dict = Depends(get_current_user),
    filters: Optional[str] = None
):
    """List tasks with optional filtering"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="SaaS Owners must specify organization")
    
    # Base query with multi-tenant isolation
    query = {"organization_id": org_id}
    
    # Apply role-based filtering
    if current_user.get('role') == UserRole.TECHNICIAN:
        query["assigned_staff_id"] = current_user['id']
    
    # Parse and apply filters if provided
    if filters:
        try:
            import json
            filter_dict = json.loads(filters)
            filter_query = parse_filters(filter_dict, 'tasks')
            query.update(filter_query)
        except:
            raise HTTPException(status_code=400, detail="Invalid filter format")
    
    tasks = await db.tasks.find(query, {"_id": 0}).to_list(1000)
    
    # Convert datetime strings
    for task in tasks:
        if isinstance(task.get('created_at'), str):
            task['created_at'] = datetime.fromisoformat(task['created_at'])
        if task.get('due_date') and isinstance(task.get('due_date'), str):
            task['due_date'] = datetime.fromisoformat(task['due_date'])
    
    return tasks

@api_router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific task"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    task = await db.tasks.find_one({"id": task_id, "organization_id": org_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if isinstance(task.get('created_at'), str):
        task['created_at'] = datetime.fromisoformat(task['created_at'])
    if task.get('due_date') and isinstance(task.get('due_date'), str):
        task['due_date'] = datetime.fromisoformat(task['due_date'])
    
    return task

@api_router.patch("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, update_data: TaskUpdate, current_user: dict = Depends(get_current_user)):
    """Update a task"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    task = await db.tasks.find_one({"id": task_id, "organization_id": org_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if update_dict:
        await db.tasks.update_one({"id": task_id}, {"$set": update_dict})
        await log_audit(org_id, current_user['id'], "UPDATE", "task", task_id)
    
    updated = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    
    return updated

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a task"""
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if current_user.get('role') not in ['admin', 'supervisor']:
        raise HTTPException(status_code=403, detail="Only admin/supervisor can delete tasks")
    
    task = await db.tasks.find_one({"id": task_id, "organization_id": org_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await db.tasks.delete_one({"id": task_id})
    await log_audit(org_id, current_user['id'], "DELETE", "task", task_id)
    
    return {"message": "Task deleted"}

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
