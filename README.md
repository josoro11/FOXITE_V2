# 🦊 FOXITE - Multi-Tenant SaaS Platform

**FOXITE** is a multi-tenant B2B SaaS platform designed for MSPs (Managed Service Providers) and IT teams to manage their support operations efficiently.

---

## 🎯 Overview

FOXITE is **software only** - it does NOT provide IT support services. Each customer (MSP/company) uses FOXITE to manage their own clients and end users.

### Key Features
- 🏢 **Multi-tenant architecture** - Isolated organizations
- 🎫 **Unlimited tickets** for all plans
- 👥 **Unlimited end users** for all plans  
- 🏭 **Unlimited client companies** for all plans
- 📊 **Plan-based feature gating** (Staff limits, AI, Storage, Automation)
- 🔐 **JWT-based authentication** with password reset
- 🌍 **Multilingual support** (EN, ES) - ready to scale to PT, FR
- 🎨 **Clean, modern UI** inspired by Freshservice/Linear

---

## 📋 Plans

| Feature | CORE | PLUS | PRIME | SCALE |
|---------|------|------|-------|-------|
| **Tickets** | ∞ Unlimited | ∞ Unlimited | ∞ Unlimited | ∞ Unlimited |
| **End Users** | ∞ Unlimited | ∞ Unlimited | ∞ Unlimited | ∞ Unlimited |
| **Organizations** | ∞ Unlimited | ∞ Unlimited | ∞ Unlimited | ∞ Unlimited |
| **Staff Users** | 5 | 15 | 50 | Unlimited |
| **AI Features** | ❌ | ✅ | ✅ | ✅ |
| **Advanced Reports** | ❌ | ❌ | ✅ | ✅ |
| **Automation** | ❌ | ❌ | ✅ | ✅ |
| **Audit Logs** | ❌ | ❌ | ✅ | ✅ |

---

## 🏗️ Architecture

### Tech Stack
- **Backend**: FastAPI + Python 3.11
- **Frontend**: React 19 + Tailwind CSS
- **Database**: MongoDB
- **Auth**: JWT (JSON Web Tokens)
- **Email**: Resend API

### Project Structure
```
/app/
├── backend/
│   ├── server.py          # Main FastAPI application
│   ├── seed_data.py       # Database seeding script
│   ├── requirements.txt   # Python dependencies
│   └── .env              # Environment variables
├── frontend/
│   ├── src/
│   │   ├── App.js        # Main React application
│   │   ├── App.css       # Styles
│   │   └── components/   # UI components
│   ├── package.json      # Node dependencies
│   └── .env             # Frontend environment
└── README.md
```

---

## 🗄️ Data Models

### Core Entities

1. **Organizations** (Tenants)
   - Multi-tenant isolation
   - Plan assignment
   - Status management

2. **Staff Users** (Limited by plan)
   - Platform Owner (super admin)
   - Admin, Supervisor, Technician
   - Custom roles (RBAC)

3. **End Users** (Unlimited)
   - Belong to client companies
   - No plan restrictions

4. **Client Companies** (Unlimited)
   - Organizations managed by MSPs
   - Contact information

5. **Tickets** (Unlimited)
   - Status, priority, category
   - Assignment to staff
   - SLA tracking structure

6. **Tasks**
   - Internal work items
   - Linked to tickets

7. **Notifications**
   - System-generated alerts
   - Email + internal

8. **Audit Logs**
   - Action tracking
   - Restricted by plan

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB running on localhost:27017
- Yarn package manager

### Installation

1. **Install Backend Dependencies**
```bash
cd /app/backend
pip install -r requirements.txt
```

2. **Install Frontend Dependencies**
```bash
cd /app/frontend
yarn install
```

3. **Seed Database**
```bash
cd /app/backend
python seed_data.py
```

4. **Start Services**
```bash
# Backend (runs on port 8001)
sudo supervisorctl restart backend

# Frontend (runs on port 3000)
sudo supervisorctl restart frontend
```

---

## 🔑 Demo Credentials

### Platform Owner (Super Admin)
- **Email**: `owner@foxite.com`
- **Password**: `foxite2025`
- **Access**: All organizations, all data

### Organization: TechPro MSP (PLUS Plan)

**Admin**
- **Email**: `admin@techpro.com`
- **Password**: `admin123`
- **Access**: Full organization management

**Supervisor**
- **Email**: `supervisor@techpro.com`
- **Password**: `super123`
- **Access**: Ticket oversight, reporting

**Technician 1**
- **Email**: `tech1@techpro.com`
- **Password**: `tech123`
- **Access**: Assigned tickets only

**Technician 2**
- **Email**: `tech2@techpro.com`
- **Password**: `tech123`
- **Access**: Assigned tickets only

---

## 🔌 API Endpoints

### Authentication
```
POST   /api/auth/register              # Register new staff user
POST   /api/auth/login                 # Login
GET    /api/auth/me                    # Get current user
POST   /api/auth/password-reset-request # Request password reset
POST   /api/auth/password-reset-confirm # Confirm password reset
```

### Organizations
```
POST   /api/organizations              # Create organization (Platform Owner only)
GET    /api/organizations              # List organizations
GET    /api/organizations/{id}         # Get organization details
```

### Staff Users
```
GET    /api/staff-users                # List staff users
PATCH  /api/staff-users/{id}           # Update staff user
```

### Tickets
```
POST   /api/tickets                    # Create ticket
GET    /api/tickets                    # List tickets
GET    /api/tickets/{id}               # Get ticket details
PATCH  /api/tickets/{id}               # Update ticket
```

### Client Companies
```
POST   /api/client-companies           # Create client company
GET    /api/client-companies           # List client companies
```

### End Users
```
POST   /api/end-users                  # Create end user
GET    /api/end-users                  # List end users
```

### Tasks
```
POST   /api/tasks                      # Create task
GET    /api/tasks                      # List tasks
```

### Dashboard
```
GET    /api/dashboard/stats            # Get dashboard statistics
```

### Notifications
```
GET    /api/notifications              # List notifications
PATCH  /api/notifications/{id}/read    # Mark as read
```

---

## 🧪 Testing

### Backend API Testing
```bash
# Login and get token
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)
TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@techpro.com","password":"admin123"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

# Get dashboard stats
curl -X GET "$API_URL/api/dashboard/stats" \
  -H "Authorization: Bearer $TOKEN"

# List tickets
curl -X GET "$API_URL/api/tickets" \
  -H "Authorization: Bearer $TOKEN"
```

### Frontend Testing
1. Open browser: `http://localhost:3000`
2. Login with demo credentials
3. Navigate through dashboard, tickets, users

---

## 🔒 Security Features

- ✅ Password hashing with bcrypt
- ✅ JWT token authentication
- ✅ Role-based access control (RBAC)
- ✅ Multi-tenant data isolation
- ✅ Secure password reset flow
- ✅ Environment variable configuration
- ✅ CORS protection

---

## 🌍 Internationalization

### Current Languages
- English (EN) - Default
- Spanish (ES)

### Adding New Languages
1. Add language code to `Language` enum in `server.py`
2. Implement frontend translation files
3. Update organization language settings

---

## 📊 Role Permissions

| Action | Platform Owner | Admin | Supervisor | Technician |
|--------|---------------|-------|------------|------------|
| View all orgs | ✅ | ❌ | ❌ | ❌ |
| Create org | ✅ | ❌ | ❌ | ❌ |
| Manage staff | ✅ | ✅ | ❌ | ❌ |
| View all tickets | ✅ | ✅ | ✅ | ❌ |
| View assigned tickets | ✅ | ✅ | ✅ | ✅ |
| Update tickets | ✅ | ✅ | ✅ | ✅ |
| Create tickets | ✅ | ✅ | ✅ | ✅ |
| View reports | ✅ | ✅ | ✅ | ❌ |
| View audit logs | ✅ | PRIME+ | PRIME+ | ❌ |

---

## 📧 Email Configuration

To enable password reset emails, configure Resend API:

1. Sign up at [resend.com](https://resend.com)
2. Create API key (starts with `re_...`)
3. Update `/app/backend/.env`:
```env
RESEND_API_KEY=re_your_actual_api_key_here
SENDER_EMAIL=your-domain@resend.dev
```
4. Restart backend: `sudo supervisorctl restart backend`

---

## 🎨 UI/UX Design

### Design System
- **Font**: Inter (clean, modern)
- **Color Palette**: Orange/Amber gradient theme
- **Components**: Shadcn/UI components
- **Layout**: Clean dashboard with collapsible sidebar
- **Responsive**: Mobile-friendly design

### Pages
- ✅ Login page with demo credentials
- ✅ Dashboard with real-time stats
- ✅ Tickets list with search and filters
- ✅ End Users management
- ✅ Client Companies
- ✅ Staff management
- ✅ Tasks tracking

---

## 🔮 Future Enhancements (Not Built Yet)

### Phase 2 - AI Module
- AI ticket analysis
- Auto-categorization
- Response suggestions
- Usage tracking

### Phase 3 - Automation
- Workflow builder
- Trigger → Condition → Action
- Auto-assignment rules
- SLA automation

### Phase 4 - Advanced Features
- Time tracking sessions
- Device inventory management
- License & service tracking
- Knowledge base
- Advanced reporting
- SLA engine
- External integrations (Slack, Teams)
- End-user portal

### Phase 5 - Public Website
- Marketing pages
- Pricing comparison
- Contact forms
- Policy pages

---

## 🐛 Known Limitations

- ❌ Email service requires Resend API key (not configured by default)
- ❌ Public website not built yet (admin dashboard only)
- ❌ Advanced SLA engine not implemented
- ❌ No payment integration yet
- ❌ AI features are structural only (no actual AI implementation)
- ❌ Automation workflows are schema only

---

## 📝 Development Notes

### MongoDB Best Practices
- Always exclude `_id` field: `{"_id": 0}`
- Use custom `id` field (UUID string)
- Serialize datetimes to ISO format
- Use Pydantic models for responses

### Code Structure
- Clean separation of concerns
- Modular route organization
- Comprehensive error handling
- Audit logging for critical actions

---

## 🤝 Support

For issues or questions:
1. Check the demo credentials above
2. Verify MongoDB is running
3. Check backend logs: `tail -n 100 /var/log/supervisor/backend.*.log`
4. Check frontend logs in browser console

---

## 📄 License

This is a demo/foundation project. Customize and extend as needed.

---

**Built with ❤️ by FOXITE Team**
