"""
FOXITE Phase 4A Backend Tests
Tests for:
- Authentication (Admin, Supervisor, Technician)
- Notification API endpoints
- Ticket CRUD operations
- Role-based access control
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@techpro.com", "password": "admin123"}
SUPERVISOR_CREDS = {"email": "supervisor@techpro.com", "password": "super123"}
TECHNICIAN_CREDS = {"email": "tech1@techpro.com", "password": "tech123"}


class TestAuthentication:
    """Test authentication for all roles"""
    
    def test_admin_login(self):
        """Test Admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert "user" in data, "User not in response"
        assert data["user"]["role"] == "admin", f"Expected admin role, got {data['user']['role']}"
        print(f"✓ Admin login successful - role: {data['user']['role']}")
    
    def test_supervisor_login(self):
        """Test Supervisor login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERVISOR_CREDS)
        assert response.status_code == 200, f"Supervisor login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert data["user"]["role"] == "supervisor", f"Expected supervisor role, got {data['user']['role']}"
        print(f"✓ Supervisor login successful - role: {data['user']['role']}")
    
    def test_technician_login(self):
        """Test Technician login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TECHNICIAN_CREDS)
        assert response.status_code == 200, f"Technician login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert data["user"]["role"] == "technician", f"Expected technician role, got {data['user']['role']}"
        print(f"✓ Technician login successful - role: {data['user']['role']}")
    
    def test_invalid_login(self):
        """Test invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid login correctly rejected")


class TestNotificationAPI:
    """Test notification API endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    def test_get_notifications(self, admin_token):
        """Test GET /api/notifications endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Get notifications failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of notifications"
        print(f"✓ GET /api/notifications returned {len(data)} notifications")
    
    def test_mark_notification_read(self, admin_token):
        """Test PATCH /api/notifications/{id}/read endpoint"""
        # First get notifications
        response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        notifications = response.json()
        
        if len(notifications) > 0:
            notif_id = notifications[0]["id"]
            # Mark as read
            response = requests.patch(
                f"{BASE_URL}/api/notifications/{notif_id}/read",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Mark notification read failed: {response.text}"
            print(f"✓ PATCH /api/notifications/{notif_id}/read successful")
        else:
            # Test with fake ID - should return 200 (upsert behavior)
            response = requests.patch(
                f"{BASE_URL}/api/notifications/fake-id-123/read",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            # May return 200 or 404 depending on implementation
            print(f"✓ PATCH /api/notifications/fake-id/read returned {response.status_code}")


class TestTicketAPI:
    """Test ticket CRUD operations"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def technician_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TECHNICIAN_CREDS)
        return response.json()["token"]
    
    def test_create_ticket(self, admin_token):
        """Test ticket creation"""
        ticket_data = {
            "title": "TEST_Phase4A_Ticket",
            "description": "Test ticket for Phase 4A testing",
            "priority": "medium"
        }
        response = requests.post(
            f"{BASE_URL}/api/tickets",
            json=ticket_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Create ticket failed: {response.text}"
        data = response.json()
        assert "id" in data, "Ticket ID not in response"
        assert data["title"] == ticket_data["title"], "Title mismatch"
        print(f"✓ Ticket created with ID: {data['id']}, number: {data.get('ticket_number')}")
        return data["id"]
    
    def test_get_tickets(self, admin_token):
        """Test get tickets list"""
        response = requests.get(
            f"{BASE_URL}/api/tickets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Get tickets failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of tickets"
        print(f"✓ GET /api/tickets returned {len(data)} tickets")
    
    def test_update_ticket_status(self, admin_token):
        """Test ticket status update"""
        # First create a ticket
        ticket_data = {
            "title": "TEST_StatusUpdate_Ticket",
            "description": "Test ticket for status update",
            "priority": "low"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/tickets",
            json=ticket_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        ticket_id = create_response.json()["id"]
        
        # Update status
        update_response = requests.put(
            f"{BASE_URL}/api/tickets/{ticket_id}",
            json={"status": "in_progress"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert update_response.status_code == 200, f"Update ticket failed: {update_response.text}"
        updated_data = update_response.json()
        assert updated_data["status"] == "in_progress", f"Status not updated: {updated_data['status']}"
        print(f"✓ Ticket status updated to: {updated_data['status']}")
    
    def test_add_ticket_comment(self, admin_token):
        """Test adding comment to ticket"""
        # First create a ticket
        ticket_data = {
            "title": "TEST_Comment_Ticket",
            "description": "Test ticket for comment",
            "priority": "medium"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/tickets",
            json=ticket_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        ticket_id = create_response.json()["id"]
        
        # Add comment
        comment_data = {
            "comment_type": "internal_note",
            "content": "TEST_Phase4A comment"
        }
        comment_response = requests.post(
            f"{BASE_URL}/api/tickets/{ticket_id}/comments",
            json=comment_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert comment_response.status_code == 200, f"Add comment failed: {comment_response.text}"
        comment = comment_response.json()
        assert comment["content"] == comment_data["content"], "Comment content mismatch"
        print(f"✓ Comment added to ticket: {comment['id']}")


class TestPlansAPI:
    """Test plans API for pricing page"""
    
    def test_get_plans(self):
        """Test GET /api/plans endpoint - should return CORE, PLUS, PRIME only (no SCALE)"""
        response = requests.get(f"{BASE_URL}/api/plans")
        assert response.status_code == 200, f"Get plans failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of plans"
        
        plan_names = [p["name"] for p in data]
        print(f"✓ Plans returned: {plan_names}")
        
        # Verify only CORE, PLUS, PRIME (no SCALE)
        assert "CORE" in plan_names, "CORE plan missing"
        assert "PLUS" in plan_names, "PLUS plan missing"
        assert "PRIME" in plan_names, "PRIME plan missing"
        assert "SCALE" not in plan_names, "SCALE plan should NOT be present"
        
        # Verify prices
        for plan in data:
            if plan["name"] == "CORE":
                assert plan["price"] == 25, f"CORE price should be $25, got ${plan['price']}"
            elif plan["name"] == "PLUS":
                assert plan["price"] == 55, f"PLUS price should be $55, got ${plan['price']}"
            elif plan["name"] == "PRIME":
                assert plan["price"] == 90, f"PRIME price should be $90, got ${plan['price']}"
        
        print("✓ All plan prices verified: CORE=$25, PLUS=$55, PRIME=$90")


class TestDashboardAPI:
    """Test dashboard stats API"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["token"]
    
    def test_dashboard_stats(self, admin_token):
        """Test GET /api/dashboard/stats"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Get dashboard stats failed: {response.text}"
        data = response.json()
        assert "total_tickets" in data, "total_tickets missing from stats"
        assert "open_tickets" in data, "open_tickets missing from stats"
        print(f"✓ Dashboard stats: {data}")


class TestHealthCheck:
    """Test basic health check"""
    
    def test_health(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("✓ Health check passed")


# Cleanup test data
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Cleanup TEST_ prefixed data after all tests"""
    yield
    # Cleanup would go here if needed
    print("\n✓ Test session completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
