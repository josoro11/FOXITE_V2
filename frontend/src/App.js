import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation, useParams } from 'react-router-dom';
import axios from 'axios';
import { 
  LayoutDashboard, Ticket, Users, Building2, Monitor, LogOut, Menu, X, Plus, Search, 
  ArrowLeft, Send, MessageSquare, Lock, ChevronDown, Clock, CheckSquare, FileText,
  Filter, Play, Square, AlertTriangle, Calendar, RefreshCw, Trash2, Edit, Eye,
  Shield, TrendingUp, AlertCircle, Package
} from 'lucide-react';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Toaster, toast } from 'sonner';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';
const IS_DEV = process.env.NODE_ENV === 'development' || window.location.hostname.includes('preview');

// ==================== UTILITY FUNCTIONS ====================

const formatDuration = (minutes) => {
  if (!minutes) return '0m';
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return hrs > 0 ? `${hrs}h ${mins}m` : `${mins}m`;
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
};

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

// ==================== EMPTY STATE COMPONENT ====================

const EmptyState = ({ icon: Icon, title, description, action, actionLabel }) => (
  <div className="flex flex-col items-center justify-center py-16 px-4" data-testid="empty-state">
    <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
      <Icon size={32} className="text-gray-400" />
    </div>
    <h3 className="text-lg font-medium text-gray-900 mb-1">{title}</h3>
    <p className="text-gray-500 text-center max-w-sm mb-4">{description}</p>
    {action && (
      <Button onClick={action} className="bg-orange-500 hover:bg-orange-600">
        <Plus size={16} className="mr-1" /> {actionLabel}
      </Button>
    )}
  </div>
);

// ==================== CONFIRMATION DIALOG ====================

const ConfirmDialog = ({ open, onClose, onConfirm, title, message, confirmText = 'Confirm', danger = false }) => {
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <Card className="w-full max-w-md m-4" onClick={(e) => e.stopPropagation()} data-testid="confirm-dialog">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {danger && <AlertTriangle className="text-red-500" size={20} />}
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600 mb-6">{message}</p>
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={onConfirm} className={danger ? 'bg-red-500 hover:bg-red-600' : 'bg-orange-500 hover:bg-orange-600'} data-testid="confirm-button">
              {confirmText}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// ==================== LOGIN PAGE ====================

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const quickLogin = async (preset) => {
    setIsLoading(true);
    try {
      await login(preset.email, preset.password);
      toast.success(`Welcome back!`);
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Invalid credentials. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      toast.error('Please enter both email and password');
      return;
    }
    setIsLoading(true);
    try {
      await login(email, password);
      toast.success('Welcome to FOXITE!');
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Invalid credentials. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const presets = [
    { role: 'Admin', email: 'admin@techpro.com', password: 'admin123', color: 'bg-purple-500' },
    { role: 'Supervisor', email: 'supervisor@techpro.com', password: 'super123', color: 'bg-blue-500' },
    { role: 'Technician', email: 'tech1@techpro.com', password: 'tech123', color: 'bg-green-500' },
    { role: 'Owner', email: 'owner@foxite.com', password: 'foxite2025', color: 'bg-orange-500' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-amber-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-lg" data-testid="login-card">
        <CardHeader className="text-center pb-2">
          <div className="w-12 h-12 bg-orange-500 rounded-xl flex items-center justify-center mx-auto mb-3">
            <Shield className="text-white" size={24} />
          </div>
          <CardTitle className="text-2xl font-bold text-gray-900">FOXITE</CardTitle>
          <CardDescription>IT Service Management for MSPs</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4" data-testid="login-form">
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Email Address</label>
              <Input
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                data-testid="email-input"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Password</label>
              <Input
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                data-testid="password-input"
              />
            </div>
            <Button type="submit" className="w-full bg-orange-500 hover:bg-orange-600" disabled={isLoading} data-testid="login-submit-button">
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>
          
          {IS_DEV && (
            <div className="mt-6 pt-4 border-t">
              <p className="text-xs text-gray-500 mb-3 text-center flex items-center justify-center gap-1">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                Development Mode - Quick Login
              </p>
              <div className="grid grid-cols-2 gap-2">
                {presets.map((preset) => (
                  <Button
                    key={preset.role}
                    variant="outline"
                    size="sm"
                    className="text-xs"
                    onClick={() => quickLogin(preset)}
                    disabled={isLoading}
                    data-testid={`quick-login-${preset.role.toLowerCase()}`}
                  >
                    <span className={`w-2 h-2 rounded-full ${preset.color} mr-1.5`}></span>
                    {preset.role}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// ==================== LAYOUT ====================

const DashboardLayout = ({ children }) => {
  const { user, logout, login } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showRoleSwitcher, setShowRoleSwitcher] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
    { icon: Ticket, label: 'Tickets', path: '/tickets' },
    { icon: CheckSquare, label: 'Tasks', path: '/tasks' },
    { icon: Clock, label: 'Time Tracking', path: '/sessions' },
    { icon: Users, label: 'End Users', path: '/end-users' },
    { icon: Monitor, label: 'Devices', path: '/devices' },
    { icon: Package, label: 'Licenses', path: '/licenses' },
    { icon: Building2, label: 'Companies', path: '/companies' },
    { icon: Filter, label: 'Saved Views', path: '/saved-views' },
  ];

  const rolePresets = [
    { role: 'Admin', email: 'admin@techpro.com', password: 'admin123' },
    { role: 'Supervisor', email: 'supervisor@techpro.com', password: 'super123' },
    { role: 'Technician', email: 'tech1@techpro.com', password: 'tech123' },
    { role: 'Owner', email: 'owner@foxite.com', password: 'foxite2025' },
  ];

  const switchRole = async (preset) => {
    try {
      await login(preset.email, preset.password);
      toast.success(`Switched to ${preset.role}`);
      setShowRoleSwitcher(false);
    } catch (error) {
      toast.error('Failed to switch role');
    }
  };

  const handleLogout = () => {
    logout();
    toast.success('Logged out successfully');
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <aside className={`${sidebarOpen ? 'w-56' : 'w-16'} bg-white border-r transition-all duration-200 flex flex-col`} data-testid="sidebar">
        <div className="p-3 border-b flex items-center justify-between">
          {sidebarOpen && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center">
                <Shield className="text-white" size={16} />
              </div>
              <span className="font-bold text-gray-900">FOXITE</span>
            </div>
          )}
          <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(!sidebarOpen)} data-testid="sidebar-toggle">
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </Button>
        </div>
        
        <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.path);
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors text-sm ${
                  isActive ? 'bg-orange-50 text-orange-600 font-medium' : 'text-gray-600 hover:bg-gray-50'
                }`}
                data-testid={`nav-${item.label.toLowerCase().replace(' ', '-')}`}
              >
                <Icon size={18} />
                {sidebarOpen && <span>{item.label}</span>}
              </button>
            );
          })}
        </nav>

        <div className="p-2 border-t">
          {sidebarOpen && (
            <div className="relative mb-2">
              <button
                onClick={() => IS_DEV && setShowRoleSwitcher(!showRoleSwitcher)}
                className={`w-full p-2.5 bg-gray-50 rounded-lg text-left ${IS_DEV ? 'hover:bg-gray-100 cursor-pointer' : ''}`}
                data-testid="role-switcher-toggle"
              >
                <p className="text-sm font-medium text-gray-900 truncate">{user?.name}</p>
                <div className="flex items-center gap-1 mt-0.5">
                  <Badge variant="outline" className="text-xs capitalize">{user?.role}</Badge>
                  {IS_DEV && <ChevronDown size={12} className="text-gray-400" />}
                </div>
              </button>
              
              {IS_DEV && showRoleSwitcher && (
                <div className="absolute bottom-full left-0 w-full mb-1 bg-white border rounded-lg shadow-lg p-1.5 z-50" data-testid="role-switcher-menu">
                  <p className="text-xs text-gray-400 px-2 py-1">Switch Role (Dev)</p>
                  {rolePresets.map((preset) => (
                    <button
                      key={preset.role}
                      onClick={() => switchRole(preset)}
                      className={`w-full text-left px-2 py-1.5 rounded text-sm hover:bg-gray-50 ${user?.role === preset.role.toLowerCase() ? 'bg-orange-50 text-orange-600' : ''}`}
                      data-testid={`switch-role-${preset.role.toLowerCase()}`}
                    >
                      {preset.role}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          <Button variant="ghost" size="sm" className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50" onClick={handleLogout} data-testid="logout-button">
            <LogOut size={16} />
            {sidebarOpen && <span className="ml-2">Sign Out</span>}
          </Button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
};

// ==================== DASHBOARD PAGE ====================

const DashboardPage = () => {
  const { token, user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [recentTickets, setRecentTickets] = useState([]);
  const [activeSessions, setActiveSessions] = useState([]);
  const [expiringLicenses, setExpiringLicenses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [statsRes, ticketsRes, sessionsRes, licensesRes] = await Promise.all([
        axios.get(`${API_URL}/dashboard/stats`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API_URL}/tickets?filters=${encodeURIComponent(JSON.stringify({status: 'open'}))}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API_URL}/sessions`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API_URL}/licenses/expiring`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => ({ data: [] }))
      ]);
      setStats(statsRes.data);
      setRecentTickets(ticketsRes.data.slice(0, 5));
      setActiveSessions(sessionsRes.data.filter(s => !s.end_time).slice(0, 3));
      setExpiringLicenses(licensesRes.data.slice(0, 3));
    } catch (error) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (p) => ({ urgent: 'bg-red-100 text-red-700', high: 'bg-orange-100 text-orange-700', medium: 'bg-yellow-100 text-yellow-700', low: 'bg-blue-100 text-blue-700' }[p] || 'bg-gray-100');

  if (loading) return <div className="p-6"><div className="animate-pulse space-y-4"><div className="h-8 bg-gray-200 rounded w-1/4"></div><div className="grid grid-cols-4 gap-4">{[...Array(4)].map((_, i) => <div key={i} className="h-24 bg-gray-200 rounded"></div>)}</div></div></div>;

  return (
    <div className="p-6" data-testid="dashboard-page">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Welcome back, {user?.name?.split(' ')[0]}!</h1>
        <p className="text-gray-500">Here's what's happening today</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/tickets')} data-testid="stat-open-tickets">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Open Tickets</p>
                <p className="text-2xl font-bold text-orange-600">{stats?.open_tickets || 0}</p>
              </div>
              <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                <Ticket className="text-orange-600" size={20} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card data-testid="stat-total-tickets">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Tickets</p>
                <p className="text-2xl font-bold">{stats?.total_tickets || 0}</p>
              </div>
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <TrendingUp className="text-blue-600" size={20} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/end-users')} data-testid="stat-end-users">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">End Users</p>
                <p className="text-2xl font-bold">{stats?.total_end_users || 0}</p>
              </div>
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <Users className="text-green-600" size={20} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/companies')} data-testid="stat-companies">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Client Companies</p>
                <p className="text-2xl font-bold">{stats?.total_client_companies || 0}</p>
              </div>
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <Building2 className="text-purple-600" size={20} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Tickets */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Recent Open Tickets</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => navigate('/tickets')}>View All</Button>
            </div>
          </CardHeader>
          <CardContent>
            {recentTickets.length === 0 ? (
              <p className="text-gray-500 text-sm py-4 text-center">No open tickets. Great job!</p>
            ) : (
              <div className="space-y-2">
                {recentTickets.map((ticket) => (
                  <div key={ticket.id} onClick={() => navigate(`/tickets/${ticket.id}`)} className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">#{ticket.ticket_number} {ticket.title}</p>
                      <p className="text-xs text-gray-500">{formatDateTime(ticket.created_at)}</p>
                    </div>
                    <Badge className={getPriorityColor(ticket.priority)} variant="secondary">{ticket.priority}</Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions & Alerts */}
        <div className="space-y-4">
          {/* Active Time Tracking */}
          {activeSessions.length > 0 && (
            <Card className="border-green-200 bg-green-50">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Clock className="text-green-600" size={16} />
                  Active Sessions
                </CardTitle>
              </CardHeader>
              <CardContent>
                {activeSessions.map((session) => (
                  <div key={session.id} className="text-sm mb-2">
                    <p className="font-medium">Ticket #{session.ticket_id?.slice(0, 8)}</p>
                    <p className="text-xs text-gray-600">Started {formatDateTime(session.start_time)}</p>
                  </div>
                ))}
                <Button size="sm" variant="outline" className="w-full mt-2" onClick={() => navigate('/sessions')}>
                  Manage Sessions
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Expiring Licenses */}
          {expiringLicenses.length > 0 && (
            <Card className="border-amber-200 bg-amber-50">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertCircle className="text-amber-600" size={16} />
                  Licenses Expiring Soon
                </CardTitle>
              </CardHeader>
              <CardContent>
                {expiringLicenses.map((license) => (
                  <div key={license.id} className="text-sm mb-2">
                    <p className="font-medium truncate">{license.name}</p>
                    <p className="text-xs text-amber-700">{license.days_until_expiration} days remaining</p>
                  </div>
                ))}
                <Button size="sm" variant="outline" className="w-full mt-2" onClick={() => navigate('/licenses')}>
                  View All Licenses
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Quick Actions */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" size="sm" className="w-full justify-start" onClick={() => navigate('/tickets?create=true')}>
                <Plus size={14} className="mr-2" /> New Ticket
              </Button>
              <Button variant="outline" size="sm" className="w-full justify-start" onClick={() => navigate('/tasks?create=true')}>
                <Plus size={14} className="mr-2" /> New Task
              </Button>
              <Button variant="outline" size="sm" className="w-full justify-start" onClick={() => navigate('/sessions')}>
                <Clock size={14} className="mr-2" /> Start Time Tracking
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

// ==================== TICKETS PAGE ====================

const TicketsPage = () => {
  const { token } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreate, setShowCreate] = useState(location.search.includes('create=true'));

  useEffect(() => { fetchTickets(); }, [statusFilter]);

  const fetchTickets = async () => {
    try {
      let url = `${API_URL}/tickets`;
      if (statusFilter !== 'all') {
        url += `?filters=${encodeURIComponent(JSON.stringify({ status: statusFilter }))}`;
      }
      const response = await axios.get(url, { headers: { Authorization: `Bearer ${token}` } });
      setTickets(response.data);
    } catch (error) {
      toast.error('Failed to load tickets');
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (p) => ({ urgent: 'bg-red-100 text-red-700', high: 'bg-orange-100 text-orange-700', medium: 'bg-yellow-100 text-yellow-700', low: 'bg-blue-100 text-blue-700' }[p] || 'bg-gray-100');
  const getStatusColor = (s) => ({ new: 'bg-purple-100 text-purple-700', open: 'bg-blue-100 text-blue-700', in_progress: 'bg-orange-100 text-orange-700', on_hold: 'bg-gray-100 text-gray-600', resolved: 'bg-green-100 text-green-700', closed: 'bg-gray-100 text-gray-500' }[s] || 'bg-gray-100');

  const filtered = tickets.filter(t => 
    t.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    t.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    String(t.ticket_number).includes(searchTerm)
  );

  if (loading) return <div className="p-6">Loading tickets...</div>;

  return (
    <div className="p-6" data-testid="tickets-page">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tickets</h1>
          <p className="text-gray-500 text-sm">Manage support requests</p>
        </div>
        <Button className="bg-orange-500 hover:bg-orange-600" onClick={() => setShowCreate(true)} data-testid="create-ticket-button">
          <Plus size={16} className="mr-1" /> New Ticket
        </Button>
      </div>

      <div className="mb-4 flex gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
          <Input placeholder="Search by title, description, or ticket #..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-9" data-testid="search-tickets" />
        </div>
        <select className="border rounded-lg px-3 text-sm" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} data-testid="status-filter">
          <option value="all">All Statuses</option>
          <option value="new">New</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="on_hold">On Hold</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState 
          icon={Ticket} 
          title="No tickets found" 
          description={searchTerm || statusFilter !== 'all' ? "Try adjusting your search or filters" : "Create your first ticket to get started"} 
          action={!searchTerm && statusFilter === 'all' ? () => setShowCreate(true) : null}
          actionLabel="Create Ticket"
        />
      ) : (
        <div className="space-y-2">
          {filtered.map((ticket) => (
            <Card key={ticket.id} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate(`/tickets/${ticket.id}`)} data-testid={`ticket-row-${ticket.ticket_number}`}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm text-gray-400 font-mono">#{ticket.ticket_number}</span>
                      <span className="font-medium text-gray-900 truncate">{ticket.title}</span>
                    </div>
                    <p className="text-sm text-gray-500 truncate">{ticket.description}</p>
                  </div>
                  <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                    <Badge className={getPriorityColor(ticket.priority)}>{ticket.priority}</Badge>
                    <Badge className={getStatusColor(ticket.status)}>{ticket.status.replace('_', ' ')}</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {showCreate && <CreateTicketModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); fetchTickets(); }} />}
    </div>
  );
};

// ==================== CREATE TICKET MODAL ====================

const CreateTicketModal = ({ onClose, onCreated }) => {
  const { token } = useAuth();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('medium');
  const [category, setCategory] = useState('');
  const [deviceId, setDeviceId] = useState('');
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    axios.get(`${API_URL}/devices`, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => setDevices(res.data))
      .catch(() => {});
  }, [token]);

  const validate = () => {
    const errs = {};
    if (!title.trim()) errs.title = 'Title is required';
    if (title.length > 200) errs.title = 'Title must be less than 200 characters';
    if (!description.trim()) errs.description = 'Description is required';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    try {
      await axios.post(`${API_URL}/tickets`, {
        title: title.trim(), description: description.trim(), priority, 
        category: category.trim() || null, device_id: deviceId || null
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Ticket created successfully');
      onCreated();
    } catch (error) {
      toast.error(error.response?.data?.detail?.message || error.response?.data?.detail || 'Failed to create ticket');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <Card className="w-full max-w-lg m-4" onClick={(e) => e.stopPropagation()} data-testid="create-ticket-modal">
        <CardHeader>
          <CardTitle>Create New Ticket</CardTitle>
          <CardDescription>Submit a new support request</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium">Title <span className="text-red-500">*</span></label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Brief summary of the issue" data-testid="ticket-title-input" className={errors.title ? 'border-red-500' : ''} />
              {errors.title && <p className="text-red-500 text-xs mt-1">{errors.title}</p>}
            </div>
            <div>
              <label className="text-sm font-medium">Description <span className="text-red-500">*</span></label>
              <textarea
                className={`w-full border rounded-md p-2 text-sm min-h-[100px] ${errors.description ? 'border-red-500' : ''}`}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Detailed description of the issue..."
                data-testid="ticket-description-input"
              />
              {errors.description && <p className="text-red-500 text-xs mt-1">{errors.description}</p>}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Priority</label>
                <select className="w-full border rounded-md p-2 text-sm" value={priority} onChange={(e) => setPriority(e.target.value)} data-testid="ticket-priority-select">
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium">Category</label>
                <Input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g. Hardware, Network" data-testid="ticket-category-input" />
              </div>
            </div>
            {devices.length > 0 && (
              <div>
                <label className="text-sm font-medium">Link to Device</label>
                <select className="w-full border rounded-md p-2 text-sm" value={deviceId} onChange={(e) => setDeviceId(e.target.value)} data-testid="ticket-device-select">
                  <option value="">-- None --</option>
                  {devices.map((d) => <option key={d.id} value={d.id}>{d.name} ({d.device_type})</option>)}
                </select>
              </div>
            )}
            <div className="flex gap-2 justify-end pt-2">
              <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
              <Button type="submit" className="bg-orange-500 hover:bg-orange-600" disabled={loading} data-testid="submit-ticket-button">
                {loading ? 'Creating...' : 'Create Ticket'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

// ==================== TICKET DETAIL PAGE ====================

const TicketDetailPage = () => {
  const { token, user } = useAuth();
  const { id } = useParams();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState(null);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [commentType, setCommentType] = useState('public_reply');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { fetchTicket(); fetchComments(); }, [id]);

  const fetchTicket = async () => {
    try {
      const res = await axios.get(`${API_URL}/tickets/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      setTicket(res.data);
    } catch (error) {
      toast.error('Ticket not found');
      navigate('/tickets');
    } finally {
      setLoading(false);
    }
  };

  const fetchComments = async () => {
    try {
      const res = await axios.get(`${API_URL}/tickets/${id}/comments`, { headers: { Authorization: `Bearer ${token}` } });
      setComments(res.data);
    } catch (error) { /* ignore */ }
  };

  const updateStatus = async (status) => {
    try {
      await axios.patch(`${API_URL}/tickets/${id}`, { status }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`Status updated to "${status.replace('_', ' ')}"`);
      fetchTicket();
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const addComment = async () => {
    if (!newComment.trim()) {
      toast.error('Please enter a comment');
      return;
    }
    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/tickets/${id}/comments`, {
        comment_type: commentType,
        content: newComment.trim()
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(commentType === 'internal_note' ? 'Internal note added' : 'Reply sent');
      setNewComment('');
      fetchComments();
    } catch (error) {
      toast.error('Failed to add comment');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="p-6">Loading...</div>;
  if (!ticket) return null;

  const statuses = ['new', 'open', 'in_progress', 'on_hold', 'resolved', 'closed'];
  const getPriorityColor = (p) => ({ urgent: 'bg-red-100 text-red-700 border-red-200', high: 'bg-orange-100 text-orange-700 border-orange-200', medium: 'bg-yellow-100 text-yellow-700 border-yellow-200', low: 'bg-blue-100 text-blue-700 border-blue-200' }[p] || 'bg-gray-100');

  return (
    <div className="p-6 max-w-4xl" data-testid="ticket-detail-page">
      <button onClick={() => navigate('/tickets')} className="flex items-center gap-1 text-gray-500 hover:text-gray-700 mb-4 text-sm" data-testid="back-to-tickets">
        <ArrowLeft size={16} /> Back to Tickets
      </button>

      <Card className="mb-4">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardDescription className="font-mono">Ticket #{ticket.ticket_number}</CardDescription>
              <CardTitle className="text-xl mt-1">{ticket.title}</CardTitle>
            </div>
            <Badge className={getPriorityColor(ticket.priority) + ' border'}>{ticket.priority}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-gray-700 mb-4 whitespace-pre-wrap">{ticket.description}</p>
          <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-gray-500">
            {ticket.category && <span>Category: <strong className="text-gray-700">{ticket.category}</strong></span>}
            {ticket.device_id && <span className="flex items-center gap-1"><Monitor size={14} /> Device linked</span>}
            <span>Created: {formatDateTime(ticket.created_at)}</span>
          </div>
        </CardContent>
      </Card>

      <Card className="mb-4">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {statuses.map((s) => (
              <Button
                key={s}
                variant={ticket.status === s ? 'default' : 'outline'}
                size="sm"
                onClick={() => updateStatus(s)}
                className={ticket.status === s ? 'bg-orange-500 hover:bg-orange-600' : ''}
                data-testid={`status-btn-${s}`}
              >
                {s.replace('_', ' ')}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 mb-4 max-h-96 overflow-y-auto">
            {comments.length === 0 && <p className="text-gray-400 text-sm py-4 text-center">No activity yet</p>}
            {comments.map((c) => (
              <div key={c.id} className={`p-3 rounded-lg ${c.comment_type === 'internal_note' ? 'bg-amber-50 border-l-4 border-amber-400' : 'bg-gray-50'}`} data-testid={`comment-${c.id}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-sm">{c.author_name}</span>
                  {c.comment_type === 'internal_note' && <Badge variant="outline" className="text-xs text-amber-700 border-amber-300"><Lock size={10} className="mr-1" />Internal</Badge>}
                  <span className="text-xs text-gray-400 ml-auto">{formatDateTime(c.created_at)}</span>
                </div>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{c.content}</p>
              </div>
            ))}
          </div>

          <div className="border-t pt-4">
            <div className="flex gap-2 mb-3">
              <button
                onClick={() => setCommentType('public_reply')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${commentType === 'public_reply' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                data-testid="comment-type-public"
              >
                <MessageSquare size={14} /> Public Reply
              </button>
              <button
                onClick={() => setCommentType('internal_note')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${commentType === 'internal_note' ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                data-testid="comment-type-internal"
              >
                <Lock size={14} /> Internal Note
              </button>
            </div>
            <div className="flex gap-2">
              <textarea
                className="flex-1 border rounded-lg p-3 text-sm min-h-[80px] resize-none"
                placeholder={commentType === 'internal_note' ? 'Add internal note (visible to staff only)...' : 'Write a reply...'}
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                data-testid="comment-input"
              />
            </div>
            <div className="flex justify-end mt-2">
              <Button onClick={addComment} disabled={submitting || !newComment.trim()} className="bg-orange-500 hover:bg-orange-600" data-testid="submit-comment-button">
                <Send size={14} className="mr-1" /> {commentType === 'internal_note' ? 'Add Note' : 'Send Reply'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// ==================== TASKS PAGE ====================

const TasksPage = () => {
  const { token } = useAuth();
  const location = useLocation();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(location.search.includes('create=true'));
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => { fetchTasks(); }, []);

  const fetchTasks = async () => {
    try {
      const res = await axios.get(`${API_URL}/tasks`, { headers: { Authorization: `Bearer ${token}` } });
      setTasks(res.data);
    } catch (error) {
      toast.error('Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  const updateTaskStatus = async (taskId, status) => {
    try {
      await axios.patch(`${API_URL}/tasks/${taskId}`, { status }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Task updated');
      fetchTasks();
    } catch (error) {
      toast.error('Failed to update task');
    }
  };

  const getStatusColor = (s) => ({ pending: 'bg-gray-100 text-gray-600', in_progress: 'bg-blue-100 text-blue-700', completed: 'bg-green-100 text-green-700', cancelled: 'bg-red-100 text-red-600' }[s] || 'bg-gray-100');
  const getPriorityColor = (p) => ({ high: 'text-red-600', medium: 'text-orange-600', low: 'text-blue-600' }[p] || 'text-gray-600');

  const filtered = statusFilter === 'all' ? tasks : tasks.filter(t => t.status === statusFilter);

  if (loading) return <div className="p-6">Loading tasks...</div>;

  return (
    <div className="p-6" data-testid="tasks-page">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tasks</h1>
          <p className="text-gray-500 text-sm">Internal work items and to-dos</p>
        </div>
        <Button className="bg-orange-500 hover:bg-orange-600" onClick={() => setShowCreate(true)} data-testid="create-task-button">
          <Plus size={16} className="mr-1" /> New Task
        </Button>
      </div>

      <div className="mb-4">
        <select className="border rounded-lg px-3 py-2 text-sm" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} data-testid="task-status-filter">
          <option value="all">All Tasks</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState 
          icon={CheckSquare} 
          title="No tasks found" 
          description={statusFilter !== 'all' ? "No tasks with this status" : "Create your first task to stay organized"} 
          action={statusFilter === 'all' ? () => setShowCreate(true) : null}
          actionLabel="Create Task"
        />
      ) : (
        <div className="space-y-2">
          {filtered.map((task) => (
            <Card key={task.id} data-testid={`task-card-${task.id}`}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <input
                      type="checkbox"
                      checked={task.status === 'completed'}
                      onChange={() => updateTaskStatus(task.id, task.status === 'completed' ? 'pending' : 'completed')}
                      className="w-5 h-5 rounded border-gray-300 text-orange-500 focus:ring-orange-500"
                    />
                    <div className="flex-1 min-w-0">
                      <p className={`font-medium truncate ${task.status === 'completed' ? 'line-through text-gray-400' : ''}`}>{task.title}</p>
                      {task.description && <p className="text-sm text-gray-500 truncate">{task.description}</p>}
                      {task.due_date && (
                        <p className="text-xs text-gray-400 flex items-center gap-1 mt-1">
                          <Calendar size={12} /> Due: {formatDate(task.due_date)}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <span className={`text-xs font-medium ${getPriorityColor(task.priority)}`}>{task.priority}</span>
                    <Badge className={getStatusColor(task.status)}>{task.status.replace('_', ' ')}</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {showCreate && <CreateTaskModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); fetchTasks(); }} />}
    </div>
  );
};

const CreateTaskModal = ({ onClose, onCreated }) => {
  const { token } = useAuth();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('medium');
  const [dueDate, setDueDate] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) { toast.error('Please enter a task title'); return; }
    setLoading(true);
    try {
      await axios.post(`${API_URL}/tasks`, {
        title: title.trim(),
        description: description.trim() || null,
        priority,
        due_date: dueDate || null
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Task created');
      onCreated();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create task');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <Card className="w-full max-w-md m-4" onClick={(e) => e.stopPropagation()} data-testid="create-task-modal">
        <CardHeader>
          <CardTitle>Create New Task</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium">Title <span className="text-red-500">*</span></label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="What needs to be done?" data-testid="task-title-input" />
            </div>
            <div>
              <label className="text-sm font-medium">Description</label>
              <textarea className="w-full border rounded-md p-2 text-sm min-h-[80px]" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Additional details..." data-testid="task-description-input" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Priority</label>
                <select className="w-full border rounded-md p-2 text-sm" value={priority} onChange={(e) => setPriority(e.target.value)} data-testid="task-priority-select">
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium">Due Date</label>
                <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} data-testid="task-due-date-input" />
              </div>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
              <Button type="submit" className="bg-orange-500 hover:bg-orange-600" disabled={loading} data-testid="submit-task-button">
                {loading ? 'Creating...' : 'Create Task'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

// ==================== SESSIONS (TIME TRACKING) PAGE ====================

const SessionsPage = () => {
  const { token, user } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeSession, setActiveSession] = useState(null);
  const [showManual, setShowManual] = useState(false);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [sessionsRes, ticketsRes] = await Promise.all([
        axios.get(`${API_URL}/sessions`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API_URL}/tickets`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setSessions(sessionsRes.data);
      setTickets(ticketsRes.data);
      const active = sessionsRes.data.find(s => !s.end_time);
      setActiveSession(active || null);
    } catch (error) {
      toast.error('Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  const startSession = async (ticketId) => {
    if (!ticketId) { toast.error('Please select a ticket'); return; }
    try {
      await axios.post(`${API_URL}/sessions/start`, { ticket_id: ticketId }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Timer started');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to start session');
    }
  };

  const stopSession = async () => {
    if (!activeSession) return;
    try {
      await axios.post(`${API_URL}/sessions/stop`, { session_id: activeSession.id }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Timer stopped');
      fetchData();
    } catch (error) {
      toast.error('Failed to stop session');
    }
  };

  const getTicketTitle = (ticketId) => {
    const ticket = tickets.find(t => t.id === ticketId);
    return ticket ? `#${ticket.ticket_number} ${ticket.title}` : ticketId;
  };

  const totalMinutes = sessions.filter(s => s.end_time).reduce((sum, s) => sum + (s.duration_minutes || 0), 0);

  if (loading) return <div className="p-6">Loading sessions...</div>;

  return (
    <div className="p-6" data-testid="sessions-page">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Time Tracking</h1>
          <p className="text-gray-500 text-sm">Track time spent on tickets</p>
        </div>
        <Button variant="outline" onClick={() => setShowManual(true)} data-testid="manual-entry-button">
          <Plus size={16} className="mr-1" /> Manual Entry
        </Button>
      </div>

      {/* Active Session or Start New */}
      <Card className={`mb-6 ${activeSession ? 'border-green-300 bg-green-50' : ''}`}>
        <CardContent className="p-4">
          {activeSession ? (
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-green-700 font-medium flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                  Timer Running
                </p>
                <p className="text-lg font-semibold mt-1">{getTicketTitle(activeSession.ticket_id)}</p>
                <p className="text-sm text-gray-600">Started {formatDateTime(activeSession.start_time)}</p>
              </div>
              <Button onClick={stopSession} variant="destructive" data-testid="stop-timer-button">
                <Square size={14} className="mr-1" /> Stop Timer
              </Button>
            </div>
          ) : (
            <div>
              <p className="text-sm text-gray-600 mb-3">Start tracking time on a ticket:</p>
              <div className="flex gap-2">
                <select id="ticket-select" className="flex-1 border rounded-lg px-3 py-2 text-sm" data-testid="ticket-select-for-session">
                  <option value="">Select a ticket...</option>
                  {tickets.filter(t => !['closed', 'resolved'].includes(t.status)).map(t => (
                    <option key={t.id} value={t.id}>#{t.ticket_number} - {t.title}</option>
                  ))}
                </select>
                <Button onClick={() => startSession(document.getElementById('ticket-select').value)} className="bg-green-600 hover:bg-green-700" data-testid="start-timer-button">
                  <Play size={14} className="mr-1" /> Start
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Summary */}
      <div className="mb-4 flex items-center gap-4">
        <div className="bg-blue-50 px-4 py-2 rounded-lg">
          <p className="text-xs text-blue-600">Total Logged</p>
          <p className="text-lg font-bold text-blue-700">{formatDuration(totalMinutes)}</p>
        </div>
        <div className="bg-gray-50 px-4 py-2 rounded-lg">
          <p className="text-xs text-gray-600">Sessions</p>
          <p className="text-lg font-bold">{sessions.filter(s => s.end_time).length}</p>
        </div>
      </div>

      {/* Session List */}
      {sessions.filter(s => s.end_time).length === 0 ? (
        <EmptyState icon={Clock} title="No time entries yet" description="Start a timer or add a manual entry to track your work" />
      ) : (
        <div className="space-y-2">
          {sessions.filter(s => s.end_time).sort((a, b) => new Date(b.end_time) - new Date(a.end_time)).map((session) => (
            <Card key={session.id} data-testid={`session-card-${session.id}`}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{getTicketTitle(session.ticket_id)}</p>
                    <p className="text-sm text-gray-500">
                      {formatDateTime(session.start_time)} → {formatDateTime(session.end_time)}
                    </p>
                  </div>
                  <Badge variant="secondary" className="text-base font-semibold">{formatDuration(session.duration_minutes)}</Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {showManual && <ManualSessionModal tickets={tickets} onClose={() => setShowManual(false)} onCreated={() => { setShowManual(false); fetchData(); }} />}
    </div>
  );
};

const ManualSessionModal = ({ tickets, onClose, onCreated }) => {
  const { token } = useAuth();
  const [ticketId, setTicketId] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('10:00');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!ticketId) { toast.error('Please select a ticket'); return; }
    
    const start = new Date(`${date}T${startTime}`);
    const end = new Date(`${date}T${endTime}`);
    if (end <= start) { toast.error('End time must be after start time'); return; }

    setLoading(true);
    try {
      await axios.post(`${API_URL}/sessions/manual`, {
        ticket_id: ticketId,
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        notes: notes.trim() || null
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Time entry added');
      onCreated();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add entry');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <Card className="w-full max-w-md m-4" onClick={(e) => e.stopPropagation()} data-testid="manual-session-modal">
        <CardHeader>
          <CardTitle>Add Manual Time Entry</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium">Ticket <span className="text-red-500">*</span></label>
              <select className="w-full border rounded-md p-2 text-sm" value={ticketId} onChange={(e) => setTicketId(e.target.value)} data-testid="manual-ticket-select">
                <option value="">Select a ticket...</option>
                {tickets.map(t => <option key={t.id} value={t.id}>#{t.ticket_number} - {t.title}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium">Date</label>
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} data-testid="manual-date-input" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Start Time</label>
                <Input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} data-testid="manual-start-time" />
              </div>
              <div>
                <label className="text-sm font-medium">End Time</label>
                <Input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} data-testid="manual-end-time" />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">Notes</label>
              <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="What did you work on?" data-testid="manual-notes-input" />
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
              <Button type="submit" className="bg-orange-500 hover:bg-orange-600" disabled={loading} data-testid="submit-manual-session">
                {loading ? 'Adding...' : 'Add Entry'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

// ==================== END USERS PAGE ====================

const EndUsersPage = () => {
  const { token } = useAuth();
  const [users, setUsers] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [usersRes, companiesRes] = await Promise.all([
        axios.get(`${API_URL}/end-users`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API_URL}/client-companies`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setUsers(usersRes.data);
      setCompanies(companiesRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const getCompanyName = (id) => companies.find(c => c.id === id)?.name || 'Unknown';

  const filtered = users.filter(u => 
    u.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-6" data-testid="end-users-page">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">End Users</h1>
          <p className="text-gray-500 text-sm">People who submit support requests</p>
        </div>
        <Button className="bg-orange-500 hover:bg-orange-600" onClick={() => setShowCreate(true)} data-testid="create-end-user-button">
          <Plus size={16} className="mr-1" /> New End User
        </Button>
      </div>

      <div className="mb-4">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
          <Input placeholder="Search users..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-9" data-testid="search-end-users" />
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState 
          icon={Users} 
          title={searchTerm ? "No users found" : "No end users yet"} 
          description={searchTerm ? "Try a different search term" : "Add your first end user to start managing contacts"} 
          action={!searchTerm ? () => setShowCreate(true) : null}
          actionLabel="Add End User"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((user) => (
            <Card key={user.id} data-testid={`end-user-card-${user.id}`}>
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-lg font-medium text-gray-600">{user.name.charAt(0).toUpperCase()}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{user.name}</p>
                    <p className="text-sm text-gray-500 truncate">{user.email}</p>
                    <p className="text-xs text-gray-400 mt-1">{getCompanyName(user.client_company_id)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {showCreate && <CreateEndUserModal companies={companies} onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); fetchData(); }} />}
    </div>
  );
};

const CreateEndUserModal = ({ companies, onClose, onCreated }) => {
  const { token } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [companyId, setCompanyId] = useState(companies[0]?.id || '');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) { toast.error('Please enter a name'); return; }
    if (!email.trim()) { toast.error('Please enter an email'); return; }
    if (!companyId) { toast.error('Please select a company'); return; }
    setLoading(true);
    try {
      await axios.post(`${API_URL}/end-users`, { 
        name: name.trim(), 
        email: email.trim().toLowerCase(), 
        phone: phone.trim() || null,
        client_company_id: companyId 
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('End user created');
      onCreated();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create user');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <Card className="w-full max-w-md m-4" onClick={(e) => e.stopPropagation()} data-testid="create-end-user-modal">
        <CardHeader>
          <CardTitle>Add End User</CardTitle>
          <CardDescription>Add a new contact who can submit tickets</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium">Full Name <span className="text-red-500">*</span></label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="John Doe" data-testid="end-user-name-input" />
            </div>
            <div>
              <label className="text-sm font-medium">Email <span className="text-red-500">*</span></label>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="john@company.com" data-testid="end-user-email-input" />
            </div>
            <div>
              <label className="text-sm font-medium">Phone</label>
              <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+1 (555) 123-4567" data-testid="end-user-phone-input" />
            </div>
            <div>
              <label className="text-sm font-medium">Company <span className="text-red-500">*</span></label>
              <select className="w-full border rounded-md p-2 text-sm" value={companyId} onChange={(e) => setCompanyId(e.target.value)} data-testid="end-user-company-select">
                {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
              <Button type="submit" className="bg-orange-500 hover:bg-orange-600" disabled={loading} data-testid="submit-end-user-button">
                {loading ? 'Creating...' : 'Add User'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

// ==================== DEVICES PAGE ====================

const DevicesPage = () => {
  const { token } = useAuth();
  const [devices, setDevices] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [devicesRes, companiesRes] = await Promise.all([
        axios.get(`${API_URL}/devices`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API_URL}/client-companies`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setDevices(devicesRes.data);
      setCompanies(companiesRes.data);
    } catch (error) {
      toast.error('Failed to load devices');
    } finally {
      setLoading(false);
    }
  };

  const getCompanyName = (id) => companies.find(c => c.id === id)?.name || 'Unknown';
  const getStatusColor = (s) => ({ active: 'bg-green-100 text-green-700', maintenance: 'bg-yellow-100 text-yellow-700', retired: 'bg-gray-100 text-gray-500', disposed: 'bg-red-100 text-red-600' }[s] || 'bg-gray-100');

  let filtered = devices;
  if (typeFilter !== 'all') filtered = filtered.filter(d => d.device_type === typeFilter);
  if (statusFilter !== 'all') filtered = filtered.filter(d => d.status === statusFilter);

  if (loading) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-6" data-testid="devices-page">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Devices</h1>
          <p className="text-gray-500 text-sm">Hardware inventory and asset tracking</p>
        </div>
        <Button className="bg-orange-500 hover:bg-orange-600" onClick={() => setShowCreate(true)} data-testid="create-device-button">
          <Plus size={16} className="mr-1" /> Add Device
        </Button>
      </div>

      <div className="mb-4 flex gap-3">
        <select className="border rounded-lg px-3 py-2 text-sm" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} data-testid="device-type-filter">
          <option value="all">All Types</option>
          <option value="laptop">Laptop</option>
          <option value="server">Server</option>
          <option value="printer">Printer</option>
          <option value="network">Network</option>
          <option value="mobile">Mobile</option>
          <option value="other">Other</option>
        </select>
        <select className="border rounded-lg px-3 py-2 text-sm" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} data-testid="device-status-filter">
          <option value="all">All Statuses</option>
          <option value="active">Active</option>
          <option value="maintenance">Maintenance</option>
          <option value="retired">Retired</option>
          <option value="disposed">Disposed</option>
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState 
          icon={Monitor} 
          title="No devices found" 
          description={typeFilter !== 'all' || statusFilter !== 'all' ? "Try adjusting your filters" : "Add your first device to start tracking assets"} 
          action={typeFilter === 'all' && statusFilter === 'all' ? () => setShowCreate(true) : null}
          actionLabel="Add Device"
        />
      ) : (
        <div className="space-y-2">
          {filtered.map((device) => (
            <Card key={device.id} data-testid={`device-card-${device.id}`}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                      <Monitor size={20} className="text-gray-500" />
                    </div>
                    <div>
                      <p className="font-medium">{device.name}</p>
                      <p className="text-sm text-gray-500">
                        {device.manufacturer && `${device.manufacturer} `}{device.model} • {getCompanyName(device.client_company_id)}
                      </p>
                      {device.serial_number && <p className="text-xs text-gray-400 font-mono">S/N: {device.serial_number}</p>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="capitalize">{device.device_type}</Badge>
                    <Badge className={getStatusColor(device.status)}>{device.status}</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {showCreate && <CreateDeviceModal companies={companies} onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); fetchData(); }} />}
    </div>
  );
};

const CreateDeviceModal = ({ companies, onClose, onCreated }) => {
  const { token } = useAuth();
  const [name, setName] = useState('');
  const [deviceType, setDeviceType] = useState('laptop');
  const [manufacturer, setManufacturer] = useState('');
  const [model, setModel] = useState('');
  const [serialNumber, setSerialNumber] = useState('');
  const [companyId, setCompanyId] = useState(companies[0]?.id || '');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) { toast.error('Please enter a device name'); return; }
    if (!companyId) { toast.error('Please select a company'); return; }
    setLoading(true);
    try {
      await axios.post(`${API_URL}/devices`, {
        name: name.trim(), device_type: deviceType, manufacturer: manufacturer.trim() || null, 
        model: model.trim() || null, serial_number: serialNumber.trim() || null, 
        client_company_id: companyId, status: 'active'
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Device added successfully');
      onCreated();
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (detail?.error === 'plan_limit_exceeded') {
        toast.error(detail.message);
      } else {
        toast.error(typeof detail === 'string' ? detail : 'Failed to add device');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <Card className="w-full max-w-md m-4" onClick={(e) => e.stopPropagation()} data-testid="create-device-modal">
        <CardHeader>
          <CardTitle>Add Device</CardTitle>
          <CardDescription>Track a new hardware asset</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium">Device Name <span className="text-red-500">*</span></label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Marketing Laptop 01" data-testid="device-name-input" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Type</label>
                <select className="w-full border rounded-md p-2 text-sm" value={deviceType} onChange={(e) => setDeviceType(e.target.value)} data-testid="device-type-select">
                  <option value="laptop">Laptop</option>
                  <option value="server">Server</option>
                  <option value="printer">Printer</option>
                  <option value="network">Network</option>
                  <option value="mobile">Mobile</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium">Company <span className="text-red-500">*</span></label>
                <select className="w-full border rounded-md p-2 text-sm" value={companyId} onChange={(e) => setCompanyId(e.target.value)} data-testid="device-company-select">
                  {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Manufacturer</label>
                <Input value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} placeholder="e.g. Dell, HP" data-testid="device-manufacturer-input" />
              </div>
              <div>
                <label className="text-sm font-medium">Model</label>
                <Input value={model} onChange={(e) => setModel(e.target.value)} placeholder="e.g. XPS 15" data-testid="device-model-input" />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">Serial Number</label>
              <Input value={serialNumber} onChange={(e) => setSerialNumber(e.target.value)} placeholder="Optional" data-testid="device-serial-input" />
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
              <Button type="submit" className="bg-orange-500 hover:bg-orange-600" disabled={loading} data-testid="submit-device-button">
                {loading ? 'Adding...' : 'Add Device'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

// ==================== LICENSES PAGE ====================

const LicensesPage = () => {
  const { token } = useAuth();
  const [licenses, setLicenses] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [filter, setFilter] = useState('all');

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [licensesRes, companiesRes] = await Promise.all([
        axios.get(`${API_URL}/licenses`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API_URL}/client-companies`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setLicenses(licensesRes.data);
      setCompanies(companiesRes.data);
    } catch (error) {
      if (error.response?.status === 403 && error.response?.data?.detail?.error === 'feature_not_available') {
        toast.error('License management is not available on your plan');
      } else {
        toast.error('Failed to load licenses');
      }
    } finally {
      setLoading(false);
    }
  };

  const getCompanyName = (id) => companies.find(c => c.id === id)?.name || 'Unknown';
  const getStatusColor = (license) => {
    if (license.expired) return 'bg-red-100 text-red-700';
    if (license.expiring_soon) return 'bg-amber-100 text-amber-700';
    return 'bg-green-100 text-green-700';
  };
  const getStatusText = (license) => {
    if (license.expired) return 'Expired';
    if (license.expiring_soon) return `${license.days_until_expiration}d left`;
    return 'Active';
  };

  let filtered = licenses;
  if (filter === 'expiring') filtered = licenses.filter(l => l.expiring_soon && !l.expired);
  if (filter === 'expired') filtered = licenses.filter(l => l.expired);
  if (filter === 'active') filtered = licenses.filter(l => !l.expired && !l.expiring_soon);

  if (loading) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-6" data-testid="licenses-page">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Licenses</h1>
          <p className="text-gray-500 text-sm">Software licenses and subscriptions</p>
        </div>
        <Button className="bg-orange-500 hover:bg-orange-600" onClick={() => setShowCreate(true)} data-testid="create-license-button">
          <Plus size={16} className="mr-1" /> Add License
        </Button>
      </div>

      <div className="mb-4 flex gap-2">
        {['all', 'active', 'expiring', 'expired'].map(f => (
          <Button key={f} variant={filter === f ? 'default' : 'outline'} size="sm" onClick={() => setFilter(f)} className={filter === f ? 'bg-orange-500' : ''} data-testid={`license-filter-${f}`}>
            {f === 'all' ? 'All' : f === 'expiring' ? 'Expiring Soon' : f.charAt(0).toUpperCase() + f.slice(1)}
            {f === 'expiring' && licenses.filter(l => l.expiring_soon && !l.expired).length > 0 && (
              <span className="ml-1 bg-amber-500 text-white text-xs px-1.5 rounded-full">{licenses.filter(l => l.expiring_soon && !l.expired).length}</span>
            )}
          </Button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <EmptyState 
          icon={Package} 
          title={filter !== 'all' ? `No ${filter} licenses` : "No licenses yet"} 
          description={filter !== 'all' ? "Try a different filter" : "Add your first license to track software subscriptions"} 
          action={filter === 'all' ? () => setShowCreate(true) : null}
          actionLabel="Add License"
        />
      ) : (
        <div className="space-y-2">
          {filtered.map((license) => (
            <Card key={license.id} className={license.expired ? 'border-red-200' : license.expiring_soon ? 'border-amber-200' : ''} data-testid={`license-card-${license.id}`}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${license.expired ? 'bg-red-100' : license.expiring_soon ? 'bg-amber-100' : 'bg-blue-100'}`}>
                      <Package size={20} className={license.expired ? 'text-red-600' : license.expiring_soon ? 'text-amber-600' : 'text-blue-600'} />
                    </div>
                    <div>
                      <p className="font-medium">{license.name}</p>
                      <p className="text-sm text-gray-500">{license.provider} • {getCompanyName(license.client_company_id)}</p>
                      {license.expiration_date && (
                        <p className="text-xs text-gray-400">Expires: {formatDate(license.expiration_date)}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="capitalize">{license.license_type}</Badge>
                    <Badge className={getStatusColor(license)}>{getStatusText(license)}</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {showCreate && <CreateLicenseModal companies={companies} onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); fetchData(); }} />}
    </div>
  );
};

const CreateLicenseModal = ({ companies, onClose, onCreated }) => {
  const { token } = useAuth();
  const [name, setName] = useState('');
  const [licenseType, setLicenseType] = useState('subscription');
  const [provider, setProvider] = useState('');
  const [licenseKey, setLicenseKey] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [expirationDate, setExpirationDate] = useState('');
  const [companyId, setCompanyId] = useState(companies[0]?.id || '');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) { toast.error('Please enter a license name'); return; }
    if (!companyId) { toast.error('Please select a company'); return; }
    setLoading(true);
    try {
      await axios.post(`${API_URL}/licenses`, {
        name: name.trim(),
        license_type: licenseType,
        provider: provider.trim() || null,
        license_key: licenseKey.trim() || null,
        quantity: parseInt(quantity) || 1,
        expiration_date: expirationDate ? new Date(expirationDate).toISOString() : null,
        client_company_id: companyId,
        status: 'active'
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('License added successfully');
      onCreated();
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (detail?.error === 'feature_not_available') {
        toast.error(detail.message);
      } else if (detail?.error === 'plan_limit_exceeded') {
        toast.error(detail.message);
      } else {
        toast.error(typeof detail === 'string' ? detail : 'Failed to add license');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <Card className="w-full max-w-md m-4" onClick={(e) => e.stopPropagation()} data-testid="create-license-modal">
        <CardHeader>
          <CardTitle>Add License</CardTitle>
          <CardDescription>Track a software license or subscription</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium">License Name <span className="text-red-500">*</span></label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Microsoft 365 Business" data-testid="license-name-input" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Type</label>
                <select className="w-full border rounded-md p-2 text-sm" value={licenseType} onChange={(e) => setLicenseType(e.target.value)} data-testid="license-type-select">
                  <option value="subscription">Subscription</option>
                  <option value="perpetual">Perpetual</option>
                  <option value="trial">Trial</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium">Company <span className="text-red-500">*</span></label>
                <select className="w-full border rounded-md p-2 text-sm" value={companyId} onChange={(e) => setCompanyId(e.target.value)} data-testid="license-company-select">
                  {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Provider</label>
                <Input value={provider} onChange={(e) => setProvider(e.target.value)} placeholder="e.g. Microsoft" data-testid="license-provider-input" />
              </div>
              <div>
                <label className="text-sm font-medium">Quantity</label>
                <Input type="number" min="1" value={quantity} onChange={(e) => setQuantity(e.target.value)} data-testid="license-quantity-input" />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">License Key</label>
              <Input value={licenseKey} onChange={(e) => setLicenseKey(e.target.value)} placeholder="Optional" data-testid="license-key-input" />
            </div>
            <div>
              <label className="text-sm font-medium">Expiration Date</label>
              <Input type="date" value={expirationDate} onChange={(e) => setExpirationDate(e.target.value)} data-testid="license-expiration-input" />
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
              <Button type="submit" className="bg-orange-500 hover:bg-orange-600" disabled={loading} data-testid="submit-license-button">
                {loading ? 'Adding...' : 'Add License'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

// ==================== COMPANIES PAGE ====================

const CompaniesPage = () => {
  const { token } = useAuth();
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await axios.get(`${API_URL}/client-companies`, { headers: { Authorization: `Bearer ${token}` } });
        setCompanies(res.data);
      } catch (error) {
        toast.error('Failed to load companies');
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [token]);

  if (loading) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-6" data-testid="companies-page">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Client Companies</h1>
        <p className="text-gray-500 text-sm">Organizations you provide support for</p>
      </div>

      {companies.length === 0 ? (
        <EmptyState icon={Building2} title="No companies yet" description="Client companies will appear here once added" />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {companies.map((company) => (
            <Card key={company.id} data-testid={`company-card-${company.id}`}>
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Building2 size={20} className="text-purple-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium">{company.name}</p>
                    <p className="text-sm text-gray-500">{company.city}, {company.country}</p>
                    <p className="text-xs text-gray-400 mt-1">{company.contact_email}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

// ==================== SAVED VIEWS PAGE ====================

const SavedViewsPage = () => {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [views, setViews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  useEffect(() => { fetchViews(); }, []);

  const fetchViews = async () => {
    try {
      const res = await axios.get(`${API_URL}/saved-views`, { headers: { Authorization: `Bearer ${token}` } });
      setViews(res.data);
    } catch (error) {
      if (error.response?.status === 403) {
        toast.error('Saved views are not available on your plan');
      } else {
        toast.error('Failed to load saved views');
      }
    } finally {
      setLoading(false);
    }
  };

  const deleteView = async (viewId) => {
    try {
      await axios.delete(`${API_URL}/saved-views/${viewId}`, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('View deleted');
      fetchViews();
    } catch (error) {
      toast.error('Failed to delete view');
    }
    setDeleteConfirm(null);
  };

  const applyView = (view) => {
    const filterStr = encodeURIComponent(JSON.stringify(view.filters));
    navigate(`/${view.entity_type}?filters=${filterStr}`);
    toast.success(`Applied "${view.name}" filter`);
  };

  const getEntityIcon = (type) => {
    const icons = { tickets: Ticket, tasks: CheckSquare, sessions: Clock };
    return icons[type] || Filter;
  };

  if (loading) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-6" data-testid="saved-views-page">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Saved Views</h1>
          <p className="text-gray-500 text-sm">Quick access to filtered lists</p>
        </div>
        <Button className="bg-orange-500 hover:bg-orange-600" onClick={() => setShowCreate(true)} data-testid="create-view-button">
          <Plus size={16} className="mr-1" /> New View
        </Button>
      </div>

      {views.length === 0 ? (
        <EmptyState 
          icon={Filter} 
          title="No saved views yet" 
          description="Save your favorite filters for quick access" 
          action={() => setShowCreate(true)}
          actionLabel="Create View"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {views.map((view) => {
            const Icon = getEntityIcon(view.entity_type);
            return (
              <Card key={view.id} className="hover:shadow-md transition-shadow" data-testid={`view-card-${view.id}`}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3 flex-1 min-w-0 cursor-pointer" onClick={() => applyView(view)}>
                      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Icon size={20} className="text-blue-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium">{view.name}</p>
                        <p className="text-sm text-gray-500 capitalize">{view.entity_type}</p>
                        {view.is_shared && <Badge variant="outline" className="text-xs mt-1">Shared</Badge>}
                      </div>
                    </div>
                    <Button variant="ghost" size="icon" className="text-gray-400 hover:text-red-600" onClick={() => setDeleteConfirm(view)} data-testid={`delete-view-${view.id}`}>
                      <Trash2 size={16} />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {showCreate && <CreateViewModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); fetchViews(); }} />}
      
      <ConfirmDialog
        open={!!deleteConfirm}
        onClose={() => setDeleteConfirm(null)}
        onConfirm={() => deleteView(deleteConfirm?.id)}
        title="Delete View"
        message={`Are you sure you want to delete "${deleteConfirm?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        danger
      />
    </div>
  );
};

const CreateViewModal = ({ onClose, onCreated }) => {
  const { token } = useAuth();
  const [name, setName] = useState('');
  const [entityType, setEntityType] = useState('tickets');
  const [isShared, setIsShared] = useState(false);
  const [filterStatus, setFilterStatus] = useState('');
  const [filterPriority, setFilterPriority] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) { toast.error('Please enter a view name'); return; }
    
    const filters = {};
    if (filterStatus) filters.status = filterStatus;
    if (filterPriority) filters.priority = filterPriority;

    setLoading(true);
    try {
      await axios.post(`${API_URL}/saved-views`, {
        name: name.trim(),
        entity_type: entityType,
        filters,
        is_shared: isShared
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('View saved');
      onCreated();
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (detail?.error === 'feature_not_available') {
        toast.error(detail.message);
      } else if (detail?.error === 'plan_limit_exceeded') {
        toast.error(detail.message);
      } else {
        toast.error('Failed to save view');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <Card className="w-full max-w-md m-4" onClick={(e) => e.stopPropagation()} data-testid="create-view-modal">
        <CardHeader>
          <CardTitle>Create Saved View</CardTitle>
          <CardDescription>Save a filter for quick access</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium">View Name <span className="text-red-500">*</span></label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. My Open Tickets" data-testid="view-name-input" />
            </div>
            <div>
              <label className="text-sm font-medium">Entity Type</label>
              <select className="w-full border rounded-md p-2 text-sm" value={entityType} onChange={(e) => setEntityType(e.target.value)} data-testid="view-entity-select">
                <option value="tickets">Tickets</option>
                <option value="tasks">Tasks</option>
                <option value="sessions">Sessions</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Status Filter</label>
                <select className="w-full border rounded-md p-2 text-sm" value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} data-testid="view-status-filter">
                  <option value="">Any</option>
                  <option value="new">New</option>
                  <option value="open">Open</option>
                  <option value="in_progress">In Progress</option>
                  <option value="resolved">Resolved</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium">Priority Filter</label>
                <select className="w-full border rounded-md p-2 text-sm" value={filterPriority} onChange={(e) => setFilterPriority(e.target.value)} data-testid="view-priority-filter">
                  <option value="">Any</option>
                  <option value="urgent">Urgent</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="shared" checked={isShared} onChange={(e) => setIsShared(e.target.checked)} className="rounded border-gray-300" />
              <label htmlFor="shared" className="text-sm">Share with team</label>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
              <Button type="submit" className="bg-orange-500 hover:bg-orange-600" disabled={loading} data-testid="submit-view-button">
                {loading ? 'Saving...' : 'Save View'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

// ==================== PROTECTED ROUTE ====================

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div></div>;
  return user ? children : <Navigate to="/login" />;
};

// ==================== MAIN APP ====================

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/*" element={
            <ProtectedRoute>
              <DashboardLayout>
                <Routes>
                  <Route path="/" element={<Navigate to="/dashboard" />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/tickets" element={<TicketsPage />} />
                  <Route path="/tickets/:id" element={<TicketDetailPage />} />
                  <Route path="/tasks" element={<TasksPage />} />
                  <Route path="/sessions" element={<SessionsPage />} />
                  <Route path="/end-users" element={<EndUsersPage />} />
                  <Route path="/devices" element={<DevicesPage />} />
                  <Route path="/licenses" element={<LicensesPage />} />
                  <Route path="/companies" element={<CompaniesPage />} />
                  <Route path="/saved-views" element={<SavedViewsPage />} />
                  <Route path="*" element={<Navigate to="/dashboard" />} />
                </Routes>
              </DashboardLayout>
            </ProtectedRoute>
          } />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}

export default App;
