from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
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

# ==================== MODELS ====================

# Enums
class UserRole(str):
    PLATFORM_OWNER = "platform_owner"
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    TECHNICIAN = "technician"
    CUSTOM = "custom"

class PlanType(str):
    CORE = "CORE"
    PLUS = "PLUS"
    PRIME = "PRIME"
    SCALE = "SCALE"

class OrgStatus(str):
    ACTIVE = "active"
    SUSPENDED = "suspended"

class TicketStatus(str):
    NEW = "new"
    OPEN = "open"
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

# Organization Models
class Organization(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    plan: str = PlanType.CORE
    status: str = OrgStatus.ACTIVE
    language: str = Language.EN
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    max_staff_users: int = 5  # Based on plan

class OrganizationCreate(BaseModel):
    name: str
    plan: str = PlanType.CORE
    language: str = Language.EN

# Staff User Models
class StaffUser(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: Optional[str] = None  # None for Platform Owner
    name: str
    email: EmailStr
    role: str
    status: str = "active"
    is_platform_owner: bool = False
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
    title: str
    description: str
    status: str = TicketStatus.NEW
    priority: str = TicketPriority.MEDIUM
    category: Optional[str] = None
    assigned_staff_id: Optional[str] = None
    end_user_id: Optional[str] = None
    client_company_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TicketCreate(BaseModel):
    title: str
    description: str
    priority: str = TicketPriority.MEDIUM
    category: Optional[str] = None
    assigned_staff_id: Optional[str] = None
    end_user_id: Optional[str] = None
    client_company_id: Optional[str] = None

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_staff_id: Optional[str] = None

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

async def log_audit(organization_id: str, user_id: str, action: str, entity_type: str, entity_id: str, details: dict = {}):
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
        org = await db.organizations.find_one({"id": user_data.organization_id}, {"_id": 0})
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        staff_count = await db.staff_users.count_documents({
            "organization_id": user_data.organization_id,
            "status": "active"
        })
        
        if staff_count >= org.get('max_staff_users', 5):
            raise HTTPException(status_code=400, detail="Staff user limit reached for this plan")
    
    # Hash password
    hashed_pwd = hash_password(user_data.password)
    
    # Create user
    user = StaffUser(
        name=user_data.name,
        email=user_data.email,
        role=user_data.role,
        organization_id=user_data.organization_id,
        is_platform_owner=user_data.organization_id is None
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
        # Don't reveal if email exists
        return {"message": "If email exists, reset link has been sent"}
    
    # Create reset token (valid for 1 hour)
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
            <a href="{reset_link}" style="background: #1a73e8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password</a>
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
        
        # Update password
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

# ==================== ORGANIZATION ROUTES ====================

@api_router.post("/organizations", response_model=Organization)
async def create_organization(org_data: OrganizationCreate, current_user: dict = Depends(get_current_user)):
    # Only platform owners can create organizations
    if not current_user.get('is_platform_owner'):
        raise HTTPException(status_code=403, detail="Only platform owners can create organizations")
    
    # Set max staff based on plan
    plan_limits = {
        PlanType.CORE: 5,
        PlanType.PLUS: 15,
        PlanType.PRIME: 50,
        PlanType.SCALE: 999999
    }
    
    org = Organization(
        name=org_data.name,
        plan=org_data.plan,
        language=org_data.language,
        max_staff_users=plan_limits.get(org_data.plan, 5)
    )
    
    doc = org.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.organizations.insert_one(doc)
    await log_audit(org.id, current_user['id'], "CREATE", "organization", org.id)
    
    return org

@api_router.get("/organizations", response_model=List[Organization])
async def list_organizations(current_user: dict = Depends(get_current_user)):
    # Platform owners see all, others see only their org
    if current_user.get('is_platform_owner'):
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
    # Check permissions
    if not current_user.get('is_platform_owner') and current_user.get('organization_id') != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if isinstance(org.get('created_at'), str):
        org['created_at'] = datetime.fromisoformat(org['created_at'])
    
    return org

# ==================== STAFF USER ROUTES ====================

@api_router.get("/staff-users", response_model=List[StaffUser])
async def list_staff_users(current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    
    if current_user.get('is_platform_owner'):
        # Platform owners see all
        users = await db.staff_users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    else:
        # Others see only their org
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
    
    # Check permissions
    if not current_user.get('is_platform_owner'):
        if current_user.get('organization_id') != user.get('organization_id'):
            raise HTTPException(status_code=403, detail="Access denied")
        if current_user.get('role') not in [UserRole.ADMIN]:
            raise HTTPException(status_code=403, detail="Only admins can update users")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if update_dict:
        await db.staff_users.update_one({"id": user_id}, {"$set": update_dict})
        await log_audit(user.get('organization_id', ''), current_user['id'], "UPDATE", "staff_user", user_id)
    
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
        raise HTTPException(status_code=403, detail="Platform owners cannot create client companies directly")
    
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
        raise HTTPException(status_code=403, detail="Platform owners must specify organization")
    
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
        raise HTTPException(status_code=403, detail="Platform owners cannot create end users directly")
    
    # Verify client company belongs to org
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
        raise HTTPException(status_code=403, detail="Platform owners must specify organization")
    
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
        raise HTTPException(status_code=403, detail="Platform owners cannot create tickets directly")
    
    ticket = Ticket(
        organization_id=org_id,
        title=ticket_data.title,
        description=ticket_data.description,
        priority=ticket_data.priority,
        category=ticket_data.category,
        assigned_staff_id=ticket_data.assigned_staff_id,
        end_user_id=ticket_data.end_user_id,
        client_company_id=ticket_data.client_company_id
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
        raise HTTPException(status_code=403, detail="Platform owners must specify organization")
    
    # Technicians only see assigned tickets
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

# ==================== TASK ROUTES ====================

@api_router.post("/tasks", response_model=Task)
async def create_task(task_data: TaskCreate, current_user: dict = Depends(get_current_user)):
    org_id = current_user.get('organization_id')
    if not org_id:
        raise HTTPException(status_code=403, detail="Platform owners cannot create tasks directly")
    
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
        raise HTTPException(status_code=403, detail="Platform owners must specify organization")
    
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
    
    if current_user.get('is_platform_owner'):
        # Platform owner stats
        total_orgs = await db.organizations.count_documents({})
        active_orgs = await db.organizations.count_documents({"status": "active"})
        total_tickets = await db.tickets.count_documents({})
        total_users = await db.staff_users.count_documents({})
        
        return {
            "total_organizations": total_orgs,
            "active_organizations": active_orgs,
            "total_tickets": total_tickets,
            "total_staff_users": total_users
        }
    else:
        # Organization stats
        total_tickets = await db.tickets.count_documents({"organization_id": org_id})
        open_tickets = await db.tickets.count_documents({"organization_id": org_id, "status": {"$in": ["new", "open", "in_progress"]}})
        total_staff = await db.staff_users.count_documents({"organization_id": org_id, "status": "active"})
        total_end_users = await db.end_users.count_documents({"organization_id": org_id})
        total_companies = await db.client_companies.count_documents({"organization_id": org_id})
        
        # Get organization
        org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
        
        return {
            "organization": org.get('name') if org else '',
            "plan": org.get('plan') if org else '',
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "total_staff": total_staff,
            "max_staff": org.get('max_staff_users', 5) if org else 5,
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
