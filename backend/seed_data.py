import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from passlib.context import CryptContext
import uuid
from datetime import datetime, timezone, timedelta

load_dotenv()

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_database():
    print("🌱 Seeding FOXITE database...")
    
    # Clear existing data
    await db.organizations.delete_many({})
    await db.staff_users.delete_many({})
    await db.client_companies.delete_many({})
    await db.end_users.delete_many({})
    await db.tickets.delete_many({})
    await db.tasks.delete_many({})
    await db.notifications.delete_many({})
    await db.audit_logs.delete_many({})
    await db.subscriptions.delete_many({})
    await db.ticket_comments.delete_many({})
    await db.ticket_attachments.delete_many({})
    await db.sessions.delete_many({})
    await db.sla_policies.delete_many({})
    await db.business_hours.delete_many({})
    await db.saved_views.delete_many({})
    await db.devices.delete_many({})
    await db.licenses.delete_many({})
    print("✓ Cleared existing data")
    
    # 1. Create SaaS Owner
    owner_id = str(uuid.uuid4())
    owner = {
        "id": owner_id,
        "organization_id": None,
        "name": "SaaS Owner",
        "email": "owner@foxite.com",
        "password_hash": pwd_context.hash("foxite2025"),
        "role": "owner",
        "status": "active",
        "is_owner": True,
        "last_login": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.staff_users.insert_one(owner)
    print(f"✓ Created SaaS Owner: owner@foxite.com / foxite2025")
    
    # 2. Create Demo Organization
    org_id = str(uuid.uuid4())
    organization = {
        "id": org_id,
        "name": "TechPro MSP",
        "legal_name": "TechPro Managed Services Ltd.",
        "country": "US",
        "timezone": "America/New_York",
        "language": "en",
        "plan": "PLUS",
        "billing_cycle": "monthly",
        "seat_count": 5,
        "status": "active",
        "trial_ends_at": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.organizations.insert_one(organization)
    print(f"✓ Created Organization: TechPro MSP (PLUS plan, 5 seats)")
    
    # Create subscription for the organization
    subscription_id = str(uuid.uuid4())
    start_date = datetime.now(timezone.utc)
    next_billing = start_date + timedelta(days=30)
    subscription = {
        "id": subscription_id,
        "org_id": org_id,
        "plan_id": "PLUS",
        "billing_cycle": "monthly",
        "status": "active",
        "start_date": start_date.isoformat(),
        "next_billing_date": next_billing.isoformat(),
        "discount_percent": 0.0,
        "override_price": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.subscriptions.insert_one(subscription)
    print(f"✓ Created Subscription: $55/month (PLUS plan)")
    
    # 2a. Create Business Hours (Mon-Fri, 9 AM - 5 PM EST)
    business_hours_id = str(uuid.uuid4())
    business_hours = {
        "id": business_hours_id,
        "organization_id": org_id,
        "timezone": "America/New_York",
        "work_days": [1, 2, 3, 4, 5],  # Monday through Friday
        "start_time": "09:00",
        "end_time": "17:00",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.business_hours.insert_one(business_hours)
    print(f"✓ Created Business Hours: Mon-Fri 9-5 EST")
    
    # 2b. Create SLA Policies (one per priority)
    sla_policies = [
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": "Low Priority SLA",
            "priority": "low",
            "response_time_minutes": 480,  # 8 hours
            "resolution_time_minutes": 2880,  # 2 business days
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": "Medium Priority SLA",
            "priority": "medium",
            "response_time_minutes": 240,  # 4 hours
            "resolution_time_minutes": 1440,  # 1 business day
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": "High Priority SLA",
            "priority": "high",
            "response_time_minutes": 120,  # 2 hours
            "resolution_time_minutes": 480,  # 8 hours
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": "Urgent Priority SLA",
            "priority": "urgent",
            "response_time_minutes": 30,  # 30 minutes
            "resolution_time_minutes": 240,  # 4 hours
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.sla_policies.insert_many(sla_policies)
    print(f"✓ Created 4 SLA Policies (Low/Medium/High/Urgent)")
    
    # 3. Create Staff Users
    admin_id = str(uuid.uuid4())
    supervisor_id = str(uuid.uuid4())
    tech1_id = str(uuid.uuid4())
    tech2_id = str(uuid.uuid4())
    
    staff_users = [
        {
            "id": admin_id,
            "organization_id": org_id,
            "name": "Sarah Admin",
            "email": "admin@techpro.com",
            "password_hash": pwd_context.hash("admin123"),
            "role": "admin",
            "status": "active",
            "is_owner": False,
            "last_login": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": supervisor_id,
            "organization_id": org_id,
            "name": "Mike Supervisor",
            "email": "supervisor@techpro.com",
            "password_hash": pwd_context.hash("super123"),
            "role": "supervisor",
            "status": "active",
            "is_owner": False,
            "last_login": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": tech1_id,
            "organization_id": org_id,
            "name": "John Tech",
            "email": "tech1@techpro.com",
            "password_hash": pwd_context.hash("tech123"),
            "role": "technician",
            "status": "active",
            "is_owner": False,
            "last_login": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": tech2_id,
            "organization_id": org_id,
            "name": "Emma Tech",
            "email": "tech2@techpro.com",
            "password_hash": pwd_context.hash("tech123"),
            "role": "technician",
            "status": "active",
            "is_owner": False,
            "last_login": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.staff_users.insert_many(staff_users)
    print(f"✓ Created Staff Users:")
    print(f"  - Admin: admin@techpro.com / admin123")
    print(f"  - Supervisor: supervisor@techpro.com / super123")
    print(f"  - Technician 1: tech1@techpro.com / tech123")
    print(f"  - Technician 2: tech2@techpro.com / tech123")
    
    # 4. Create Client Companies
    company1_id = str(uuid.uuid4())
    company2_id = str(uuid.uuid4())
    company3_id = str(uuid.uuid4())
    
    companies = [
        {
            "id": company1_id,
            "organization_id": org_id,
            "name": "Acme Corporation",
            "country": "USA",
            "city": "New York",
            "contact_email": "contact@acme.com",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": company2_id,
            "organization_id": org_id,
            "name": "GlobalTech Solutions",
            "country": "UK",
            "city": "London",
            "contact_email": "info@globaltech.co.uk",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": company3_id,
            "organization_id": org_id,
            "name": "Innovate Inc",
            "country": "Canada",
            "city": "Toronto",
            "contact_email": "support@innovate.ca",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.client_companies.insert_many(companies)
    print(f"✓ Created 3 Client Companies")
    
    # 5. Create End Users
    end_users = []
    for i in range(8):
        company_id = [company1_id, company2_id, company3_id][i % 3]
        company_name = ["acme", "globaltech", "innovate"][i % 3]
        end_users.append({
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "client_company_id": company_id,
            "name": f"End User {i+1}",
            "email": f"user{i+1}@{company_name}.com",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    await db.end_users.insert_many(end_users)
    print(f"✓ Created 8 End Users")
    
    # 5a. Create Devices
    device1_id = str(uuid.uuid4())  # Active laptop linked to ticket
    device2_id = str(uuid.uuid4())  # Active server
    device3_id = str(uuid.uuid4())  # Maintenance printer (linked to ticket 2)
    device4_id = str(uuid.uuid4())  # Retired laptop
    device5_id = str(uuid.uuid4())  # Active laptop for CEO (linked to ticket 5)
    
    devices = [
        {
            "id": device1_id,
            "organization_id": org_id,
            "client_company_id": company1_id,
            "name": "Marketing Team Laptop 01",
            "device_type": "laptop",
            "manufacturer": "Dell",
            "model": "XPS 15 9520",
            "serial_number": "DXPS15-2023-001",
            "os_type": "Windows",
            "os_version": "11 Pro",
            "assigned_to": end_users[0]["id"],
            "status": "active",
            "purchase_date": (datetime.now(timezone.utc) - timedelta(days=365)).isoformat(),
            "warranty_expiry": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "notes": "Marketing department laptop with Adobe suite installed",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": device2_id,
            "organization_id": org_id,
            "client_company_id": company1_id,
            "name": "Acme Web Server",
            "device_type": "server",
            "manufacturer": "HP",
            "model": "ProLiant DL380 Gen10",
            "serial_number": "HPDL380-2022-001",
            "os_type": "Linux",
            "os_version": "Ubuntu Server 22.04 LTS",
            "assigned_to": None,
            "status": "active",
            "purchase_date": (datetime.now(timezone.utc) - timedelta(days=730)).isoformat(),
            "warranty_expiry": (datetime.now(timezone.utc) + timedelta(days=95)).isoformat(),
            "notes": "Primary web server for Acme Corporation",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": device3_id,
            "organization_id": org_id,
            "client_company_id": company1_id,
            "name": "3rd Floor Network Printer",
            "device_type": "printer",
            "manufacturer": "HP",
            "model": "LaserJet Enterprise MFP M636",
            "serial_number": "HPLJ-3FL-2021-001",
            "os_type": None,
            "os_version": None,
            "assigned_to": None,
            "status": "maintenance",
            "purchase_date": (datetime.now(timezone.utc) - timedelta(days=1095)).isoformat(),
            "warranty_expiry": (datetime.now(timezone.utc) - timedelta(days=365)).isoformat(),
            "notes": "Network printer - currently experiencing connectivity issues",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": device4_id,
            "organization_id": org_id,
            "client_company_id": company2_id,
            "name": "Old Finance Laptop",
            "device_type": "laptop",
            "manufacturer": "Lenovo",
            "model": "ThinkPad T480",
            "serial_number": "LNV-T480-2019-001",
            "os_type": "Windows",
            "os_version": "10 Pro",
            "assigned_to": None,
            "status": "retired",
            "purchase_date": (datetime.now(timezone.utc) - timedelta(days=1825)).isoformat(),
            "warranty_expiry": (datetime.now(timezone.utc) - timedelta(days=730)).isoformat(),
            "notes": "Retired device - replaced with newer model",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": device5_id,
            "organization_id": org_id,
            "client_company_id": company3_id,
            "name": "CEO Executive Laptop",
            "device_type": "laptop",
            "manufacturer": "Apple",
            "model": "MacBook Pro 16-inch M3 Max",
            "serial_number": "APL-MBP-2024-CEO",
            "os_type": "macOS",
            "os_version": "Sonoma 14.4",
            "assigned_to": end_users[6]["id"],
            "status": "active",
            "purchase_date": (datetime.now(timezone.utc) - timedelta(days=90)).isoformat(),
            "warranty_expiry": (datetime.now(timezone.utc) + timedelta(days=640)).isoformat(),
            "notes": "Executive laptop experiencing performance issues",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.devices.insert_many(devices)
    print(f"✓ Created 5 Devices (laptop, server, printer - active, maintenance, retired)")
    
    # 5b. Create Licenses
    license1_id = str(uuid.uuid4())  # Active license
    license2_id = str(uuid.uuid4())  # Expiring soon (within 60 days)
    license3_id = str(uuid.uuid4())  # Already expired
    license4_id = str(uuid.uuid4())  # Active subscription
    license5_id = str(uuid.uuid4())  # Expiring very soon (within 5 days)
    
    licenses = [
        {
            "id": license1_id,
            "organization_id": org_id,
            "client_company_id": company1_id,
            "name": "Microsoft 365 Business Premium",
            "license_type": "subscription",
            "provider": "Microsoft",
            "license_key": "M365-ACME-2024-XXXXX",
            "assigned_to": None,
            "quantity": 50,
            "purchase_date": (datetime.now(timezone.utc) - timedelta(days=180)).isoformat(),
            "expiration_date": (datetime.now(timezone.utc) + timedelta(days=185)).isoformat(),
            "renewal_cost": 1250.00,
            "billing_cycle": "yearly",
            "status": "active",
            "notes": "Company-wide Microsoft 365 license",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": license2_id,
            "organization_id": org_id,
            "client_company_id": company1_id,
            "name": "Antivirus Enterprise Suite",
            "license_type": "software",
            "provider": "Norton",
            "license_key": "NRT-ENT-2023-XXXXX",
            "assigned_to": None,
            "quantity": 100,
            "purchase_date": (datetime.now(timezone.utc) - timedelta(days=330)).isoformat(),
            "expiration_date": (datetime.now(timezone.utc) + timedelta(days=35)).isoformat(),
            "renewal_cost": 2500.00,
            "billing_cycle": "yearly",
            "status": "active",
            "notes": "Enterprise antivirus - expiring soon",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": license3_id,
            "organization_id": org_id,
            "client_company_id": company2_id,
            "name": "Adobe Creative Cloud (Expired)",
            "license_type": "subscription",
            "provider": "Adobe",
            "license_key": "ADO-CC-2022-XXXXX",
            "assigned_to": end_users[4]["id"],
            "quantity": 5,
            "purchase_date": (datetime.now(timezone.utc) - timedelta(days=400)).isoformat(),
            "expiration_date": (datetime.now(timezone.utc) - timedelta(days=35)).isoformat(),
            "renewal_cost": 450.00,
            "billing_cycle": "monthly",
            "status": "expired",
            "notes": "License has expired - needs renewal",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": license4_id,
            "organization_id": org_id,
            "client_company_id": company2_id,
            "name": "Slack Business+",
            "license_type": "subscription",
            "provider": "Slack",
            "license_key": "SLK-BUS-2024-XXXXX",
            "assigned_to": None,
            "quantity": 25,
            "purchase_date": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
            "expiration_date": (datetime.now(timezone.utc) + timedelta(days=305)).isoformat(),
            "renewal_cost": 187.50,
            "billing_cycle": "monthly",
            "status": "active",
            "notes": "Team communication platform",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": license5_id,
            "organization_id": org_id,
            "client_company_id": company2_id,
            "name": "Adobe Creative Cloud (Expiring)",
            "license_type": "subscription",
            "provider": "Adobe",
            "license_key": "ADO-CC-2024-XXXXX",
            "assigned_to": end_users[4]["id"],
            "quantity": 5,
            "purchase_date": (datetime.now(timezone.utc) - timedelta(days=360)).isoformat(),
            "expiration_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
            "renewal_cost": 450.00,
            "billing_cycle": "monthly",
            "status": "active",
            "notes": "Marketing team Adobe license - expiring in 5 days!",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.licenses.insert_many(licenses)
    print(f"✓ Created 5 Licenses (active, expiring soon, expired)")
    
    # 6. Create Tickets
    tickets = [
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "ticket_number": 1,
            "title": "Email not working for marketing team",
            "description": "Multiple users in marketing cannot send emails. Outlook gives authentication error.",
            "status": "open",
            "priority": "high",
            "category": "Email",
            "assigned_staff_id": tech1_id,
            "requester_id": end_users[0]["id"],
            "client_company_id": company1_id,
            "device_id": device1_id,  # Linked to Marketing Team Laptop
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "updated_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "ticket_number": 2,
            "title": "Printer connection issues",
            "description": "Office printer on 3rd floor not responding. Network printer shows offline.",
            "status": "in_progress",
            "priority": "medium",
            "category": "Hardware",
            "assigned_staff_id": tech2_id,
            "requester_id": end_users[1]["id"],
            "client_company_id": company1_id,
            "device_id": device3_id,  # Linked to 3rd Floor Network Printer
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
            "updated_at": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "ticket_number": 3,
            "title": "VPN access request for remote employee",
            "description": "New employee needs VPN credentials to access company network remotely.",
            "status": "new",
            "priority": "medium",
            "category": "Access",
            "assigned_staff_id": None,
            "requester_id": end_users[3]["id"],
            "client_company_id": company2_id,
            "device_id": None,
            "created_at": (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat(),
            "updated_at": (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "ticket_number": 4,
            "title": "Software license expiring soon",
            "description": "Adobe Creative Cloud license expires in 5 days. Need renewal.",
            "status": "open",
            "priority": "low",
            "category": "Licensing",
            "assigned_staff_id": tech1_id,
            "requester_id": end_users[4]["id"],
            "client_company_id": company2_id,
            "device_id": None,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "updated_at": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "ticket_number": 5,
            "title": "Laptop running extremely slow",
            "description": "CEO's laptop taking 10+ minutes to boot. Very sluggish performance.",
            "status": "new",
            "priority": "urgent",
            "category": "Hardware",
            "assigned_staff_id": tech2_id,
            "requester_id": end_users[6]["id"],
            "client_company_id": company3_id,
            "device_id": device5_id,  # Linked to CEO Executive Laptop
            "created_at": (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat(),
            "updated_at": (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "ticket_number": 6,
            "title": "Password reset - locked account",
            "description": "User locked out after multiple failed login attempts. Need password reset.",
            "status": "resolved",
            "priority": "medium",
            "category": "Access",
            "assigned_staff_id": tech1_id,
            "requester_id": end_users[7]["id"],
            "client_company_id": company3_id,
            "device_id": None,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            "updated_at": (datetime.now(timezone.utc) - timedelta(days=1, hours=20)).isoformat()
        }
    ]
    
    await db.tickets.insert_many(tickets)
    print(f"✓ Created 6 Sample Tickets")
    
    # 6a. Create Sample Ticket Comments
    ticket_comments = [
        {
            "id": str(uuid.uuid4()),
            "ticket_id": tickets[0]["id"],
            "organization_id": org_id,
            "author_id": tech1_id,
            "author_name": "John Tech",
            "author_type": "staff",
            "comment_type": "internal_note",
            "content": "Checked with IT team - seems to be an Azure AD sync issue. Working on resolution.",
            "created_at": (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "ticket_id": tickets[0]["id"],
            "organization_id": org_id,
            "author_id": tech1_id,
            "author_name": "John Tech",
            "author_type": "staff",
            "comment_type": "public_reply",
            "content": "Hi, I've identified the issue and am working on a fix. This should be resolved within the next hour.",
            "created_at": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "ticket_id": tickets[1]["id"],
            "organization_id": org_id,
            "author_id": tech2_id,
            "author_name": "Emma Tech",
            "author_type": "staff",
            "comment_type": "internal_note",
            "content": "Printer driver needs updating. Will schedule maintenance window.",
            "created_at": (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
        }
    ]
    
    await db.ticket_comments.insert_many(ticket_comments)
    print(f"✓ Created 3 Sample Comments")
    
    # 6b. Create Sample Ticket Attachments
    ticket_attachments = [
        {
            "id": str(uuid.uuid4()),
            "ticket_id": tickets[0]["id"],
            "organization_id": org_id,
            "uploaded_by": tech1_id,
            "uploaded_by_name": "John Tech",
            "filename": "error_screenshot.png",
            "file_url": "https://example.com/files/error_screenshot.png",
            "file_type": "image/png",
            "file_size": 245678,
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "ticket_id": tickets[4]["id"],
            "organization_id": org_id,
            "uploaded_by": tech2_id,
            "uploaded_by_name": "Emma Tech",
            "filename": "diagnostic_report.pdf",
            "file_url": "https://example.com/files/diagnostic_report.pdf",
            "file_type": "application/pdf",
            "file_size": 1024567,
            "created_at": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        }
    ]
    
    await db.ticket_attachments.insert_many(ticket_attachments)
    print(f"✓ Created 2 Sample Attachments")
    
    # 6c. Create Sample Sessions (Time Tracking)
    now = datetime.now(timezone.utc)
    
    # Session 1: Completed session (2 hours on ticket 1)
    session1_start = now - timedelta(hours=3)
    session1_end = now - timedelta(hours=1)
    session1_duration = int((session1_end - session1_start).total_seconds() / 60)
    
    # Session 2: Completed session (45 minutes on ticket 2)
    session2_start = now - timedelta(hours=6)
    session2_end = now - timedelta(hours=5, minutes=15)
    session2_duration = int((session2_end - session2_start).total_seconds() / 60)
    
    # Session 3: Active session (started 30 minutes ago, no end time)
    session3_start = now - timedelta(minutes=30)
    
    sessions = [
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "ticket_id": tickets[0]["id"],
            "agent_id": tech1_id,
            "agent_name": "John Tech",
            "start_time": session1_start.isoformat(),
            "end_time": session1_end.isoformat(),
            "duration_minutes": session1_duration,
            "note": "Fixed Azure AD sync issue",
            "created_at": session1_start.isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "ticket_id": tickets[1]["id"],
            "agent_id": tech2_id,
            "agent_name": "Emma Tech",
            "start_time": session2_start.isoformat(),
            "end_time": session2_end.isoformat(),
            "duration_minutes": session2_duration,
            "note": "Diagnosed printer connection issue",
            "created_at": session2_start.isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "ticket_id": tickets[4]["id"],
            "agent_id": tech2_id,
            "agent_name": "Emma Tech",
            "start_time": session3_start.isoformat(),
            "end_time": None,
            "duration_minutes": None,
            "note": "Currently working on laptop diagnostics",
            "created_at": session3_start.isoformat()
        }
    ]
    
    await db.sessions.insert_many(sessions)
    print(f"✓ Created 3 Sessions (2 completed, 1 active)")
    
    # 7. Create Tasks
    tasks = [
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "title": "Check email server logs",
            "description": "Review authentication logs for marketing team email issues",
            "status": "in_progress",
            "due_date": (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat(),
            "assigned_staff_id": tech1_id,
            "ticket_id": tickets[0]["id"],
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "title": "Replace printer network cable",
            "description": "Test with new ethernet cable to rule out connectivity issues",
            "status": "todo",
            "due_date": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            "assigned_staff_id": tech2_id,
            "ticket_id": tickets[1]["id"],
            "created_at": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        }
    ]
    
    await db.tasks.insert_many(tasks)
    print(f"✓ Created 2 Sample Tasks")
    
    # 8. Create Notifications
    notifications = [
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "user_id": admin_id,
            "title": "New Urgent Ticket",
            "message": "CEO's laptop running extremely slow - marked as urgent",
            "read": False,
            "created_at": (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "user_id": tech1_id,
            "title": "Ticket Assigned",
            "message": "You've been assigned: Email not working for marketing team",
            "read": False,
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        }
    ]
    
    await db.notifications.insert_many(notifications)
    print(f"✓ Created 2 Notifications")
    
    # 10. Create Sample Saved Views
    saved_views = [
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "entity_type": "tickets",
            "name": "My Open High Priority Tickets",
            "filters": {
                "priority": "high",
                "status": "open",
                "assigned_to": admin_id
            },
            "created_by": admin_id,
            "created_by_name": "Sarah Admin",
            "is_shared": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "entity_type": "tickets",
            "name": "All Urgent Tickets (Shared)",
            "filters": {
                "priority": "urgent"
            },
            "created_by": admin_id,
            "created_by_name": "Sarah Admin",
            "is_shared": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "entity_type": "tickets",
            "name": "SLA Breached Tickets",
            "filters": {
                "sla_breached_resolution": True
            },
            "created_by": supervisor_id,
            "created_by_name": "Mike Supervisor",
            "is_shared": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "entity_type": "tasks",
            "name": "Overdue Tasks",
            "filters": {
                "completed": False,
                "due_date_to": datetime.now(timezone.utc).isoformat()
            },
            "created_by": admin_id,
            "created_by_name": "Sarah Admin",
            "is_shared": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.saved_views.insert_many(saved_views)
    print(f"✓ Created 4 Saved Views (2 tickets, 1 task, 2 shared)")
    
    print("\n✅ Database seeding complete!")
    print("\n=== LOGIN CREDENTIALS ===")
    print("SaaS Owner: owner@foxite.com / foxite2025")
    print("Admin: admin@techpro.com / admin123")
    print("Supervisor: supervisor@techpro.com / super123")
    print("Technician: tech1@techpro.com / tech123")
    print("========================\n")

if __name__ == "__main__":
    asyncio.run(seed_database())
