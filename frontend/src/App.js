import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { LayoutDashboard, Ticket, Users, Building2, UserCircle, CheckSquare, Bell, LogOut, Menu, X, Plus, Search, Filter } from 'lucide-react';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Toaster, toast } from 'sonner';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

// ==================== AUTH CONTEXT ====================

const AuthContext = React.createContext(null);

const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('foxite_token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      fetchCurrentUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const response = await axios.post(`${API_URL}/auth/login`, { email, password });
    const { token: newToken, user: userData } = response.data;
    setToken(newToken);
    setUser(userData);
    localStorage.setItem('foxite_token', newToken);
    return userData;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('foxite_token');
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

// ==================== LOGIN PAGE ====================

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await login(email, password);
      toast.success('Logged in successfully');
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-amber-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-xl border-orange-100" data-testid="login-card">
        <CardHeader className="space-y-3 text-center">
          <div className="mx-auto w-20 h-20 bg-gradient-to-br from-orange-500 to-amber-600 rounded-2xl flex items-center justify-center shadow-lg">
            <img src="https://customer-assets.emergentagent.com/job_a51d588f-2009-44db-9376-3cece58637a4/artifacts/h7bckm1g_FOXITE_1.png" alt="Foxite" className="w-16 h-16 object-contain" />
          </div>
          <CardTitle className="text-3xl font-bold text-gray-900">FOXITE</CardTitle>
          <CardDescription className="text-base">Sign in to your account</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4" data-testid="login-form">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">Email</label>
              <Input
                type="email"
                placeholder="email@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                data-testid="email-input"
                className="h-11"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">Password</label>
              <Input
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                data-testid="password-input"
                className="h-11"
              />
            </div>
            <Button
              type="submit"
              className="w-full h-11 bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700"
              disabled={isLoading}
              data-testid="login-submit-button"
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600 mb-3">Demo Credentials:</p>
            <div className="text-xs text-gray-500 space-y-1 bg-gray-50 p-3 rounded-lg">
              <p><strong>Admin:</strong> admin@techpro.com / admin123</p>
              <p><strong>Tech:</strong> tech1@techpro.com / tech123</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// ==================== LAYOUT ====================

const DashboardLayout = ({ children }) => {
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
    { icon: Ticket, label: 'Tickets', path: '/tickets' },
    { icon: Users, label: 'End Users', path: '/end-users' },
    { icon: Building2, label: 'Companies', path: '/companies' },
    { icon: UserCircle, label: 'Staff', path: '/staff' },
    { icon: CheckSquare, label: 'Tasks', path: '/tasks' },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-white border-r border-gray-200 transition-all duration-300 flex flex-col`} data-testid="sidebar">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          {sidebarOpen && <h1 className="text-xl font-bold text-orange-600">FOXITE</h1>}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            data-testid="sidebar-toggle-button"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </Button>
        </div>
        
        <nav className="flex-1 p-3 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-orange-50 text-orange-600'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
                data-testid={`nav-${item.label.toLowerCase().replace(' ', '-')}`}
              >
                <Icon size={20} />
                {sidebarOpen && <span className="font-medium">{item.label}</span>}
              </button>
            );
          })}
        </nav>

        <div className="p-3 border-t border-gray-200">
          <div className={`${sidebarOpen ? 'p-3' : 'p-2'} bg-gray-50 rounded-lg mb-2`}>
            {sidebarOpen ? (
              <div>
                <p className="text-sm font-medium text-gray-900">{user?.name}</p>
                <p className="text-xs text-gray-500">{user?.email}</p>
                <Badge className="mt-2 text-xs" variant="outline">{user?.role}</Badge>
              </div>
            ) : (
              <UserCircle size={24} className="mx-auto text-gray-600" />
            )}
          </div>
          <Button
            variant="ghost"
            className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50"
            onClick={logout}
            data-testid="logout-button"
          >
            <LogOut size={20} />
            {sidebarOpen && <span className="ml-3">Logout</span>}
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
};

// ==================== DASHBOARD PAGE ====================

const Dashboard = () => {
  const { token, user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/dashboard/stats`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStats(response.data);
    } catch (error) {
      toast.error('Failed to load dashboard stats');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8" data-testid="dashboard-page">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Welcome back, {user?.name}!</h1>
        <p className="text-gray-600">Here's what's happening with your organization today.</p>
      </div>

      {user?.is_platform_owner ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card data-testid="stat-total-organizations">
            <CardHeader>
              <CardDescription>Total Organizations</CardDescription>
              <CardTitle className="text-3xl">{stats?.total_organizations || 0}</CardTitle>
            </CardHeader>
          </Card>
          <Card data-testid="stat-active-organizations">
            <CardHeader>
              <CardDescription>Active Organizations</CardDescription>
              <CardTitle className="text-3xl text-green-600">{stats?.active_organizations || 0}</CardTitle>
            </CardHeader>
          </Card>
          <Card data-testid="stat-total-tickets">
            <CardHeader>
              <CardDescription>Total Tickets</CardDescription>
              <CardTitle className="text-3xl">{stats?.total_tickets || 0}</CardTitle>
            </CardHeader>
          </Card>
          <Card data-testid="stat-total-staff">
            <CardHeader>
              <CardDescription>Total Staff Users</CardDescription>
              <CardTitle className="text-3xl">{stats?.total_staff_users || 0}</CardTitle>
            </CardHeader>
          </Card>
        </div>
      ) : (
        <>
          <div className="mb-6">
            <Card className="bg-gradient-to-r from-orange-500 to-amber-600 text-white">
              <CardHeader>
                <CardTitle className="text-white">{stats?.organization}</CardTitle>
                <CardDescription className="text-orange-100">
                  Plan: <Badge className="bg-white text-orange-600 ml-2">{stats?.plan}</Badge>
                </CardDescription>
              </CardHeader>
            </Card>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Card data-testid="stat-open-tickets">
              <CardHeader>
                <CardDescription>Open Tickets</CardDescription>
                <CardTitle className="text-3xl text-orange-600">{stats?.open_tickets || 0}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-500">Total: {stats?.total_tickets || 0}</p>
              </CardContent>
            </Card>
            
            <Card data-testid="stat-staff-count">
              <CardHeader>
                <CardDescription>Staff Members</CardDescription>
                <CardTitle className="text-3xl">{stats?.total_staff || 0} / {stats?.max_staff || 0}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-orange-500 h-2 rounded-full"
                    style={{ width: `${((stats?.total_staff || 0) / (stats?.max_staff || 1)) * 100}%` }}
                  ></div>
                </div>
              </CardContent>
            </Card>

            <Card data-testid="stat-end-users">
              <CardHeader>
                <CardDescription>End Users</CardDescription>
                <CardTitle className="text-3xl">{stats?.total_end_users || 0}</CardTitle>
              </CardHeader>
              <CardContent>
                <Badge variant="outline" className="text-green-600 border-green-600">Unlimited</Badge>
              </CardContent>
            </Card>

            <Card data-testid="stat-client-companies">
              <CardHeader>
                <CardDescription>Client Companies</CardDescription>
                <CardTitle className="text-3xl">{stats?.total_client_companies || 0}</CardTitle>
              </CardHeader>
              <CardContent>
                <Badge variant="outline" className="text-green-600 border-green-600">Unlimited</Badge>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
};

// ==================== TICKETS PAGE ====================

const TicketsPage = () => {
  const { token } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchTickets();
  }, []);

  const fetchTickets = async () => {
    try {
      const response = await axios.get(`${API_URL}/tickets`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTickets(response.data);
    } catch (error) {
      toast.error('Failed to load tickets');
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (priority) => {
    const colors = {
      urgent: 'bg-red-100 text-red-700 border-red-200',
      high: 'bg-orange-100 text-orange-700 border-orange-200',
      medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      low: 'bg-blue-100 text-blue-700 border-blue-200'
    };
    return colors[priority] || colors.medium;
  };

  const getStatusColor = (status) => {
    const colors = {
      new: 'bg-purple-100 text-purple-700',
      open: 'bg-blue-100 text-blue-700',
      in_progress: 'bg-orange-100 text-orange-700',
      on_hold: 'bg-gray-100 text-gray-700',
      resolved: 'bg-green-100 text-green-700',
      closed: 'bg-gray-100 text-gray-500'
    };
    return colors[status] || colors.new;
  };

  const filteredTickets = tickets.filter(ticket =>
    ticket.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    ticket.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return <div className="p-8">Loading tickets...</div>;
  }

  return (
    <div className="p-8" data-testid="tickets-page">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Tickets</h1>
          <p className="text-gray-600">Manage and track support tickets</p>
        </div>
        <Button className="bg-orange-500 hover:bg-orange-600" data-testid="create-ticket-button">
          <Plus size={20} className="mr-2" />
          New Ticket
        </Button>
      </div>

      <div className="mb-6 flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
          <Input
            placeholder="Search tickets..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
            data-testid="search-tickets-input"
          />
        </div>
        <Button variant="outline" data-testid="filter-button">
          <Filter size={20} className="mr-2" />
          Filter
        </Button>
      </div>

      <div className="space-y-4">
        {filteredTickets.map((ticket) => (
          <Card key={ticket.id} className="hover:shadow-md transition-shadow" data-testid={`ticket-card-${ticket.id}`}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle className="text-lg mb-2">{ticket.title}</CardTitle>
                  <CardDescription className="line-clamp-2">{ticket.description}</CardDescription>
                </div>
                <div className="flex flex-col items-end gap-2 ml-4">
                  <Badge className={getPriorityColor(ticket.priority)}>
                    {ticket.priority}
                  </Badge>
                  <Badge className={getStatusColor(ticket.status)}>
                    {ticket.status.replace('_', ' ')}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-6 text-sm text-gray-600">
                {ticket.category && (
                  <div className="flex items-center gap-2">
                    <span className="font-medium">Category:</span>
                    <span>{ticket.category}</span>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <span className="font-medium">Created:</span>
                  <span>{new Date(ticket.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredTickets.length === 0 && (
        <div className="text-center py-12" data-testid="no-tickets-message">
          <Ticket size={48} className="mx-auto text-gray-300 mb-4" />
          <p className="text-gray-500">No tickets found</p>
        </div>
      )}
    </div>
  );
};

// ==================== PLACEHOLDER PAGES ====================

const EndUsersPage = () => {
  const { token } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const response = await axios.get(`${API_URL}/end-users`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setUsers(response.data);
      } catch (error) {
        toast.error('Failed to load end users');
      } finally {
        setLoading(false);
      }
    };
    fetchUsers();
  }, []);

  return (
    <div className="p-8" data-testid="end-users-page">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">End Users</h1>
          <p className="text-gray-600">Unlimited end users for all plans</p>
        </div>
        <Button className="bg-orange-500 hover:bg-orange-600" data-testid="create-end-user-button">
          <Plus size={20} className="mr-2" />
          New End User
        </Button>
      </div>
      
      {loading ? (
        <p>Loading...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {users.map(user => (
            <Card key={user.id} data-testid={`end-user-card-${user.id}`}>
              <CardHeader>
                <CardTitle className="text-lg">{user.name}</CardTitle>
                <CardDescription>{user.email}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

const CompaniesPage = () => (
  <div className="p-8" data-testid="companies-page">
    <h1 className="text-3xl font-bold text-gray-900 mb-2">Client Companies</h1>
    <p className="text-gray-600">Manage client organizations (unlimited)</p>
  </div>
);

const StaffPage = () => (
  <div className="p-8" data-testid="staff-page">
    <h1 className="text-3xl font-bold text-gray-900 mb-2">Staff Users</h1>
    <p className="text-gray-600">Manage staff members (limited by plan)</p>
  </div>
);

const TasksPage = () => (
  <div className="p-8" data-testid="tasks-page">
    <h1 className="text-3xl font-bold text-gray-900 mb-2">Tasks</h1>
    <p className="text-gray-600">Track internal work items</p>
  </div>
);

// ==================== PROTECTED ROUTE ====================

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  return user ? children : <Navigate to="/login" />;
};

// ==================== MAIN APP ====================

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <Routes>
                    <Route path="/" element={<Navigate to="/dashboard" />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/tickets" element={<TicketsPage />} />
                    <Route path="/end-users" element={<EndUsersPage />} />
                    <Route path="/companies" element={<CompaniesPage />} />
                    <Route path="/staff" element={<StaffPage />} />
                    <Route path="/tasks" element={<TasksPage />} />
                  </Routes>
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}

export default App;
