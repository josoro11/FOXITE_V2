# FOXITE - Multi-Tenant B2B SaaS for MSPs/IT Teams

## Product Overview
FOXITE is a multi-tenant B2B SaaS application similar to Freshservice, designed for Managed Service Providers (MSPs) and IT teams to manage tickets, assets, and client companies.

## Core Architecture
- **Backend:** FastAPI with Motor (async MongoDB driver)
- **Frontend:** React
- **Database:** MongoDB
- **Authentication:** JWT-based
- **Architecture:** Multi-tenant, API-first with plan-based feature gating

## User Roles
- **Platform Owner:** SaaS owner with global access
- **Admin:** Organization-level admin
- **Supervisor:** Team supervisor
- **Technician:** Support staff

## Subscription Plans (Phase 3B - Enforced)
| Resource/Feature | CORE ($25) | PLUS ($55) | PRIME ($90) |
|------------------|------------|------------|-------------|
| **Tickets** | Unlimited | Unlimited | Unlimited |
| **Staff Users** | Unlimited | Unlimited | Unlimited |
| **End Users** | Unlimited | Unlimited | Unlimited |
| **Devices** | 25 | 100 | Unlimited |
| **Licenses** | ✗ (0) | 50 | Unlimited |
| **Saved Views** | ✗ (5)* | 25 | Unlimited |
| **Automations** | ✗ (0) | 10 | Unlimited |
| **AI Requests/mo** | ✗ (0) | 100 | Unlimited |
| Licenses Inventory | ✗ | ✓ | ✓ |
| Saved Filters | ✗ | ✓ | ✓ |
| Workflows | ✗ | ✓ | ✓ |
| AI Features | ✗ | Limited | Unlimited |
| Custom Dashboards | ✗ | ✗ | ✓ |
| Audit Logs | ✗ | ✗ | ✓ |

*CORE plan has some saved views from before enforcement was added

## Implemented Features

### Phase 0 & 1: SaaS Core (✅ Complete)
- Multi-tenant organization structure
- JWT authentication with role-based access
- Staff users, end users, client companies
- Subscription and plan management

### Phase 2A: Enhanced Tickets (✅ Complete)
- Auto-incrementing ticket numbers per organization
- Public replies vs. internal notes
- File attachments (metadata stored, no actual storage)

### Phase 2B: Sessions & Time Tracking (✅ Complete)
- Start/stop time tracking on tickets
- Manual session entry
- Session overlap prevention
- Duration calculation

### Phase 2C: SLA Management (✅ Complete)
- Business hours configuration
- SLA policies per priority level
- Due date calculation (business-hours aware)
- SLA breach tracking

### Phase 2D: Filtering & Saved Views (✅ Complete)
- Reusable filter parser for tickets, tasks, sessions
- Saved views (personal and shared)
- JSON filter configuration

### Phase 3A: Asset Inventory - Core Tracking (✅ Complete - Feb 4, 2026)
**Devices:**
- Full CRUD for hardware assets (laptops, servers, printers, etc.)
- Device types: laptop, server, printer, network, mobile, other
- Status tracking: active, maintenance, retired, disposed
- Device-ticket linking (tickets can reference a device)
- Filtering by status, type, company, assigned user
- Device-to-tickets relationship endpoint

**Licenses:**
- Full CRUD for software licenses and subscriptions
- License types: software, service, subscription, other
- Expiration tracking with calculated fields:
  - `days_until_expiration` - auto-calculated
  - `expiring_soon` - true if <60 days
  - `expired` - true if past expiration
- Dedicated `/licenses/expiring` endpoint
- Filtering by status, type, expired, expiring_soon

### Phase 3B: Plan Enforcement & Feature Gating (✅ Complete - Feb 4, 2026)
**Centralized Plan Configuration:**
- Single source of truth: `PLAN_FEATURES` dict in server.py
- Three plans: CORE ($25), PLUS ($55), PRIME ($90)
- Resource limits (devices, licenses, saved_views, automations, AI requests)
- Feature flags (boolean and tiered)

**Enforcement Middleware:**
- `enforce_resource_limit(org_id, resource)` - Raises PlanLimitError if limit exceeded
- `enforce_feature_access(org_id, feature)` - Raises FeatureNotAvailableError if blocked
- `check_resource_limit(org_id, resource)` - Returns usage info without raising

**Clear Error Responses:**
```json
{
  "error": "plan_limit_exceeded",
  "resource": "licenses",
  "limit": 50,
  "plan": "PLUS",
  "message": "You have reached the licenses limit (50)...",
  "upgrade_url": "/settings/billing"
}
```

**Feature Flags for Future Modules:**
- `ai_features`, `ai_ticket_summary`, `ai_response_suggestions`
- `automation_rules`, `workflows`
- `custom_dashboards`, `audit_logs`

**Applied Enforcement:**
- `/api/devices` POST - Device limit check
- `/api/licenses` POST - Feature + limit check
- `/api/saved-views` POST - Feature + limit check

## API Endpoints

### Plans & Usage
- `GET /api/plans` - List all available plans (public)
- `GET /api/organizations/{id}/features` - Get plan features
- `GET /api/organizations/{id}/usage` - Get resource usage vs limits

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/me` - Current user info
- `POST /api/auth/password-reset-request` - Request password reset
- `POST /api/auth/password-reset-confirm` - Confirm password reset

### Organizations
- `GET /api/organizations` - List organizations
- `POST /api/organizations` - Create organization (owner only)
- `GET /api/organizations/{id}` - Get organization
- `GET /api/organizations/{id}/features` - Get plan features

### Tickets
- `GET /api/tickets` - List tickets (with filters)
- `POST /api/tickets` - Create ticket
- `GET /api/tickets/{id}` - Get ticket
- `PATCH /api/tickets/{id}` - Update ticket
- `POST /api/tickets/{id}/comments` - Add comment
- `GET /api/tickets/{id}/comments` - List comments
- `POST /api/tickets/{id}/attachments` - Add attachment
- `GET /api/tickets/{id}/attachments` - List attachments

### Sessions (Time Tracking)
- `POST /api/sessions/start` - Start session
- `POST /api/sessions/stop` - Stop session
- `POST /api/sessions/manual` - Create manual session
- `GET /api/sessions` - List sessions

### SLA
- `GET /api/sla-policies` - List SLA policies
- `POST /api/sla-policies` - Create SLA policy
- `GET /api/business-hours` - Get business hours
- `POST /api/business-hours` - Create/update business hours

### Saved Views
- `GET /api/saved-views` - List saved views
- `POST /api/saved-views` - Create saved view
- `PATCH /api/saved-views/{id}` - Update saved view
- `DELETE /api/saved-views/{id}` - Delete saved view

### Devices (Asset Inventory)
- `GET /api/devices` - List devices (with filters)
- `POST /api/devices` - Create device
- `GET /api/devices/{id}` - Get device
- `PATCH /api/devices/{id}` - Update device
- `DELETE /api/devices/{id}` - Delete device
- `GET /api/devices/{id}/tickets` - Get linked tickets
- `GET /api/client-companies/{id}/devices` - Get company devices

### Licenses (Asset Inventory)
- `GET /api/licenses` - List licenses (with filters)
- `GET /api/licenses/expiring` - Get expiring licenses (<60 days)
- `POST /api/licenses` - Create license
- `GET /api/licenses/{id}` - Get license
- `PATCH /api/licenses/{id}` - Update license
- `DELETE /api/licenses/{id}` - Delete license
- `GET /api/client-companies/{id}/licenses` - Get company licenses

## Test Credentials
- **SaaS Owner:** owner@foxite.com / foxite2025
- **Admin:** admin@techpro.com / admin123
- **Supervisor:** supervisor@techpro.com / super123
- **Technician:** tech1@techpro.com / tech123

## Known Limitations / Mocked Features
1. **Plan Enforcement:** Plan-based feature gating is documented but not actively enforced
2. **Email Notifications:** Resend integration exists but emails are not sent
3. **File Storage:** Attachment metadata is stored but no actual file storage

## Upcoming Tasks (Backlog)
- **Phase 3B:** TBD (awaiting user specification)
- Public website (Home, Features, Pricing)
- UI polish and frontend implementation
- Plan enforcement middleware
- Email notification execution
- AI module integration
- Automation & workflows engine
- Advanced reporting/dashboards
- Payment integration (Stripe)

## File Structure
```
/app/
├── backend/
│   ├── .env              # Environment variables
│   ├── requirements.txt  # Python dependencies
│   ├── seed_data.py      # Database seeding script
│   └── server.py         # Monolithic FastAPI application (~2700 lines)
├── frontend/
│   ├── .env              # Frontend environment variables
│   ├── package.json      # Node dependencies
│   └── src/
│       ├── App.js        # Main React component
│       └── App.css       # Styles
└── memory/
    └── PRD.md            # This file
```

## Technical Notes
- Backend runs on port 8001 (internal), exposed via `/api` prefix
- Frontend runs on port 3000
- MongoDB connection via MONGO_URL environment variable
- All datetime fields stored as ISO strings in MongoDB
- License expiration status calculated dynamically on fetch
