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
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.organizations.insert_one(organization)
    print(f"✓ Created Organization: TechPro MSP (PLUS plan)")
    
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
            "device_id": None,
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
            "device_id": None,
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
            "device_id": None,
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
    
    print("\n✅ Database seeding complete!")
    print("\n=== LOGIN CREDENTIALS ===")
    print("SaaS Owner: owner@foxite.com / foxite2025")
    print("Admin: admin@techpro.com / admin123")
    print("Supervisor: supervisor@techpro.com / super123")
    print("Technician: tech1@techpro.com / tech123")
    print("========================\n")

if __name__ == "__main__":
    asyncio.run(seed_database())
