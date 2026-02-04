import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation, useParams } from 'react-router-dom';
import axios from 'axios';
import { LayoutDashboard, Ticket, Users, Building2, UserCircle, Monitor, LogOut, Menu, X, Plus, Search, ArrowLeft, Send, MessageSquare, Lock, ChevronDown } from 'lucide-react';
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

  const quickLogin = async (preset) => {
    setIsLoading(true);
    try {
      await login(preset.email, preset.password);
      toast.success(`Logged in as ${preset.role}`);
      navigate('/tickets');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await login(email, password);
      toast.success('Logged in successfully');
      navigate('/tickets');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
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
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md" data-testid="login-card">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold text-orange-600">FOXITE</CardTitle>
          <CardDescription>Beta Testing Login</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4" data-testid="login-form">
            <Input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              data-testid="email-input"
            />
            <Input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              data-testid="password-input"
            />
            <Button type="submit" className="w-full bg-orange-500 hover:bg-orange-600" disabled={isLoading} data-testid="login-submit-button">
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>
          
          <div className="mt-6">
            <p className="text-sm text-gray-500 mb-3 text-center">Quick Login (Role Switcher):</p>
            <div className="grid grid-cols-2 gap-2">
              {presets.map((preset) => (
                <Button
                  key={preset.role}
                  variant="outline"
                  className="text-sm"
                  onClick={() => quickLogin(preset)}
                  disabled={isLoading}
                  data-testid={`quick-login-${preset.role.toLowerCase()}`}
                >
                  <span className={`w-2 h-2 rounded-full ${preset.color} mr-2`}></span>
                  {preset.role}
                </Button>
              ))}
            </div>
          </div>
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
    { icon: Ticket, label: 'Tickets', path: '/tickets' },
    { icon: Users, label: 'End Users', path: '/end-users' },
    { icon: Monitor, label: 'Devices', path: '/devices' },
    { icon: Building2, label: 'Companies', path: '/companies' },
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

  return (
    <div className="flex h-screen bg-gray-50">
      <aside className={`${sidebarOpen ? 'w-64' : 'w-16'} bg-white border-r transition-all duration-200 flex flex-col`} data-testid="sidebar">
        <div className="p-4 border-b flex items-center justify-between">
          {sidebarOpen && <span className="font-bold text-orange-600">FOXITE</span>}
          <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(!sidebarOpen)} data-testid="sidebar-toggle">
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </Button>
        </div>
        
        <nav className="flex-1 p-2 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.path);
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                  isActive ? 'bg-orange-50 text-orange-600' : 'text-gray-700 hover:bg-gray-50'
                }`}
                data-testid={`nav-${item.label.toLowerCase().replace(' ', '-')}`}
              >
                <Icon size={20} />
                {sidebarOpen && <span>{item.label}</span>}
              </button>
            );
          })}
        </nav>

        <div className="p-3 border-t">
          {sidebarOpen && (
            <div className="relative">
              <button
                onClick={() => setShowRoleSwitcher(!showRoleSwitcher)}
                className="w-full p-2 bg-gray-50 rounded-lg text-left hover:bg-gray-100"
                data-testid="role-switcher-toggle"
              >
                <p className="text-sm font-medium">{user?.name}</p>
                <p className="text-xs text-gray-500 flex items-center gap-1">
                  <Badge variant="outline" className="text-xs">{user?.role}</Badge>
                  <ChevronDown size={12} />
                </p>
              </button>
              
              {showRoleSwitcher && (
                <div className="absolute bottom-full left-0 w-full mb-1 bg-white border rounded-lg shadow-lg p-2 z-50" data-testid="role-switcher-menu">
                  <p className="text-xs text-gray-500 px-2 mb-2">Switch Role:</p>
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
          <Button variant="ghost" className="w-full justify-start text-red-600 mt-2" onClick={logout} data-testid="logout-button">
            <LogOut size={18} />
            {sidebarOpen && <span className="ml-2">Logout</span>}
          </Button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
};

// ==================== TICKETS PAGE ====================

const TicketsPage = () => {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => { fetchTickets(); }, []);

  const fetchTickets = async () => {
    try {
      const response = await axios.get(`${API_URL}/tickets`, { headers: { Authorization: `Bearer ${token}` } });
      setTickets(response.data);
    } catch (error) {
      toast.error('Failed to load tickets');
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (p) => ({ urgent: 'bg-red-100 text-red-700', high: 'bg-orange-100 text-orange-700', medium: 'bg-yellow-100 text-yellow-700', low: 'bg-blue-100 text-blue-700' }[p] || 'bg-gray-100');
  const getStatusColor = (s) => ({ new: 'bg-purple-100 text-purple-700', open: 'bg-blue-100 text-blue-700', in_progress: 'bg-orange-100 text-orange-700', resolved: 'bg-green-100 text-green-700', closed: 'bg-gray-100 text-gray-500' }[s] || 'bg-gray-100');

  const filtered = tickets.filter(t => t.title.toLowerCase().includes(searchTerm.toLowerCase()));

  if (loading) return <div className="p-8">Loading...</div>;

  return (
    <div className="p-6" data-testid="tickets-page">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tickets</h1>
        <Button className="bg-orange-500 hover:bg-orange-600" onClick={() => setShowCreate(true)} data-testid="create-ticket-button">
          <Plus size={18} className="mr-1" /> New Ticket
        </Button>
      </div>

      <div className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <Input placeholder="Search tickets..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-10" data-testid="search-tickets" />
        </div>
      </div>

      <div className="space-y-2">
        {filtered.map((ticket) => (
          <Card key={ticket.id} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate(`/tickets/${ticket.id}`)} data-testid={`ticket-row-${ticket.ticket_number}`}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm text-gray-500">#{ticket.ticket_number}</span>
                    <span className="font-medium">{ticket.title}</span>
                  </div>
                  <p className="text-sm text-gray-500 truncate">{ticket.description}</p>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <Badge className={getPriorityColor(ticket.priority)}>{ticket.priority}</Badge>
                  <Badge className={getStatusColor(ticket.status)}>{ticket.status.replace('_', ' ')}</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filtered.length === 0 && <p className="text-center text-gray-500 py-8">No tickets found</p>}

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

  useEffect(() => {
    const fetchDevices = async () => {
      try {
        const res = await axios.get(`${API_URL}/devices`, { headers: { Authorization: `Bearer ${token}` } });
        setDevices(res.data);
      } catch (e) { /* ignore */ }
    };
    fetchDevices();
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API_URL}/tickets`, {
        title, description, priority, category: category || null, device_id: deviceId || null
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Ticket created');
      onCreated();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create ticket');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <Card className="w-full max-w-lg m-4" onClick={(e) => e.stopPropagation()} data-testid="create-ticket-modal">
        <CardHeader>
          <CardTitle>Create New Ticket</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium">Title *</label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} required data-testid="ticket-title-input" />
            </div>
            <div>
              <label className="text-sm font-medium">Description *</label>
              <textarea
                className="w-full border rounded-md p-2 text-sm min-h-[100px]"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                required
                data-testid="ticket-description-input"
              />
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
                <Input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g. Hardware" data-testid="ticket-category-input" />
              </div>
            </div>
            {devices.length > 0 && (
              <div>
                <label className="text-sm font-medium">Link Device (optional)</label>
                <select className="w-full border rounded-md p-2 text-sm" value={deviceId} onChange={(e) => setDeviceId(e.target.value)} data-testid="ticket-device-select">
                  <option value="">-- No device --</option>
                  {devices.map((d) => <option key={d.id} value={d.id}>{d.name} ({d.device_type})</option>)}
                </select>
              </div>
            )}
            <div className="flex gap-2 justify-end">
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
      toast.error('Failed to load ticket');
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
      toast.success(`Status changed to ${status}`);
      fetchTicket();
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const addComment = async () => {
    if (!newComment.trim()) return;
    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/tickets/${id}/comments`, {
        comment_type: commentType,
        content: newComment
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Comment added');
      setNewComment('');
      fetchComments();
    } catch (error) {
      toast.error('Failed to add comment');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="p-8">Loading...</div>;
  if (!ticket) return null;

  const statuses = ['new', 'open', 'in_progress', 'on_hold', 'resolved', 'closed'];
  const getPriorityColor = (p) => ({ urgent: 'bg-red-100 text-red-700', high: 'bg-orange-100 text-orange-700', medium: 'bg-yellow-100 text-yellow-700', low: 'bg-blue-100 text-blue-700' }[p] || 'bg-gray-100');

  return (
    <div className="p-6 max-w-4xl" data-testid="ticket-detail-page">
      <button onClick={() => navigate('/tickets')} className="flex items-center gap-1 text-gray-600 hover:text-gray-900 mb-4" data-testid="back-to-tickets">
        <ArrowLeft size={18} /> Back to Tickets
      </button>

      <Card className="mb-4">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardDescription>Ticket #{ticket.ticket_number}</CardDescription>
              <CardTitle className="text-xl">{ticket.title}</CardTitle>
            </div>
            <Badge className={getPriorityColor(ticket.priority)}>{ticket.priority}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-gray-700 mb-4">{ticket.description}</p>
          <div className="flex flex-wrap gap-4 text-sm text-gray-500">
            {ticket.category && <span>Category: <strong>{ticket.category}</strong></span>}
            {ticket.device_id && <span>Device linked: <strong>Yes</strong></span>}
            <span>Created: {new Date(ticket.created_at).toLocaleString()}</span>
          </div>
        </CardContent>
      </Card>

      {/* Status Changer */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle className="text-base">Change Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {statuses.map((s) => (
              <Button
                key={s}
                variant={ticket.status === s ? 'default' : 'outline'}
                size="sm"
                onClick={() => updateStatus(s)}
                className={ticket.status === s ? 'bg-orange-500' : ''}
                data-testid={`status-btn-${s}`}
              >
                {s.replace('_', ' ')}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Comments */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Comments & Replies</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 mb-4 max-h-80 overflow-y-auto">
            {comments.length === 0 && <p className="text-gray-500 text-sm">No comments yet</p>}
            {comments.map((c) => (
              <div key={c.id} className={`p-3 rounded-lg ${c.comment_type === 'internal_note' ? 'bg-yellow-50 border-l-4 border-yellow-400' : 'bg-gray-50'}`} data-testid={`comment-${c.id}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-sm">{c.author_name}</span>
                  {c.comment_type === 'internal_note' && <Badge variant="outline" className="text-xs"><Lock size={10} className="mr-1" />Internal</Badge>}
                  <span className="text-xs text-gray-400">{new Date(c.created_at).toLocaleString()}</span>
                </div>
                <p className="text-sm text-gray-700">{c.content}</p>
              </div>
            ))}
          </div>

          <div className="border-t pt-4">
            <div className="flex gap-2 mb-2">
              <button
                onClick={() => setCommentType('public_reply')}
                className={`flex items-center gap-1 px-3 py-1 rounded text-sm ${commentType === 'public_reply' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100'}`}
                data-testid="comment-type-public"
              >
                <MessageSquare size={14} /> Public Reply
              </button>
              <button
                onClick={() => setCommentType('internal_note')}
                className={`flex items-center gap-1 px-3 py-1 rounded text-sm ${commentType === 'internal_note' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100'}`}
                data-testid="comment-type-internal"
              >
                <Lock size={14} /> Internal Note
              </button>
            </div>
            <div className="flex gap-2">
              <textarea
                className="flex-1 border rounded-md p-2 text-sm min-h-[60px]"
                placeholder={commentType === 'internal_note' ? 'Add internal note (staff only)...' : 'Write a public reply...'}
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                data-testid="comment-input"
              />
              <Button onClick={addComment} disabled={submitting || !newComment.trim()} className="bg-orange-500 hover:bg-orange-600" data-testid="submit-comment-button">
                <Send size={18} />
              </Button>
            </div>
          </div>
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

  if (loading) return <div className="p-8">Loading...</div>;

  return (
    <div className="p-6" data-testid="end-users-page">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">End Users</h1>
        <Button className="bg-orange-500 hover:bg-orange-600" onClick={() => setShowCreate(true)} data-testid="create-end-user-button">
          <Plus size={18} className="mr-1" /> New End User
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {users.map((user) => (
          <Card key={user.id} data-testid={`end-user-card-${user.id}`}>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">{user.name}</CardTitle>
              <CardDescription>{user.email}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-500">Company: {getCompanyName(user.client_company_id)}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {users.length === 0 && <p className="text-center text-gray-500 py-8">No end users yet</p>}

      {showCreate && <CreateEndUserModal companies={companies} onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); fetchData(); }} />}
    </div>
  );
};

const CreateEndUserModal = ({ companies, onClose, onCreated }) => {
  const { token } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [companyId, setCompanyId] = useState(companies[0]?.id || '');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!companyId) { toast.error('Please select a company'); return; }
    setLoading(true);
    try {
      await axios.post(`${API_URL}/end-users`, { name, email, client_company_id: companyId }, { headers: { Authorization: `Bearer ${token}` } });
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
          <CardTitle>Create End User</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium">Name *</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} required data-testid="end-user-name-input" />
            </div>
            <div>
              <label className="text-sm font-medium">Email *</label>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="end-user-email-input" />
            </div>
            <div>
              <label className="text-sm font-medium">Company *</label>
              <select className="w-full border rounded-md p-2 text-sm" value={companyId} onChange={(e) => setCompanyId(e.target.value)} data-testid="end-user-company-select">
                {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="flex gap-2 justify-end">
              <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
              <Button type="submit" className="bg-orange-500 hover:bg-orange-600" disabled={loading} data-testid="submit-end-user-button">
                {loading ? 'Creating...' : 'Create'}
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
  const getStatusColor = (s) => ({ active: 'bg-green-100 text-green-700', maintenance: 'bg-yellow-100 text-yellow-700', retired: 'bg-gray-100 text-gray-500', disposed: 'bg-red-100 text-red-700' }[s] || 'bg-gray-100');

  if (loading) return <div className="p-8">Loading...</div>;

  return (
    <div className="p-6" data-testid="devices-page">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Devices</h1>
        <Button className="bg-orange-500 hover:bg-orange-600" onClick={() => setShowCreate(true)} data-testid="create-device-button">
          <Plus size={18} className="mr-1" /> New Device
        </Button>
      </div>

      <div className="space-y-2">
        {devices.map((device) => (
          <Card key={device.id} data-testid={`device-card-${device.id}`}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <Monitor size={18} className="text-gray-400" />
                    <span className="font-medium">{device.name}</span>
                    <span className="text-sm text-gray-500">({device.device_type})</span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    {device.manufacturer && `${device.manufacturer} `}{device.model && device.model} • {getCompanyName(device.client_company_id)}
                  </p>
                </div>
                <Badge className={getStatusColor(device.status)}>{device.status}</Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {devices.length === 0 && <p className="text-center text-gray-500 py-8">No devices yet</p>}

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
    if (!companyId) { toast.error('Please select a company'); return; }
    setLoading(true);
    try {
      await axios.post(`${API_URL}/devices`, {
        name, device_type: deviceType, manufacturer: manufacturer || null, model: model || null,
        serial_number: serialNumber || null, client_company_id: companyId, status: 'active'
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Device created');
      onCreated();
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (detail?.error === 'plan_limit_exceeded') {
        toast.error(detail.message);
      } else {
        toast.error(typeof detail === 'string' ? detail : 'Failed to create device');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <Card className="w-full max-w-md m-4" onClick={(e) => e.stopPropagation()} data-testid="create-device-modal">
        <CardHeader>
          <CardTitle>Create Device</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium">Name *</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. Marketing Laptop 01" data-testid="device-name-input" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Type *</label>
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
                <label className="text-sm font-medium">Company *</label>
                <select className="w-full border rounded-md p-2 text-sm" value={companyId} onChange={(e) => setCompanyId(e.target.value)} data-testid="device-company-select">
                  {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Manufacturer</label>
                <Input value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} placeholder="e.g. Dell" data-testid="device-manufacturer-input" />
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
            <div className="flex gap-2 justify-end">
              <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
              <Button type="submit" className="bg-orange-500 hover:bg-orange-600" disabled={loading} data-testid="submit-device-button">
                {loading ? 'Creating...' : 'Create'}
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

  if (loading) return <div className="p-8">Loading...</div>;

  return (
    <div className="p-6" data-testid="companies-page">
      <div className="mb-4">
        <h1 className="text-2xl font-bold">Client Companies</h1>
        <p className="text-gray-500">Organizations your MSP manages</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {companies.map((company) => (
          <Card key={company.id} data-testid={`company-card-${company.id}`}>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Building2 size={18} className="text-gray-400" />
                {company.name}
              </CardTitle>
              <CardDescription>{company.city}, {company.country}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-500">{company.contact_email}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {companies.length === 0 && <p className="text-center text-gray-500 py-8">No companies yet</p>}
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
                  <Route path="/" element={<Navigate to="/tickets" />} />
                  <Route path="/tickets" element={<TicketsPage />} />
                  <Route path="/tickets/:id" element={<TicketDetailPage />} />
                  <Route path="/end-users" element={<EndUsersPage />} />
                  <Route path="/devices" element={<DevicesPage />} />
                  <Route path="/companies" element={<CompaniesPage />} />
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
