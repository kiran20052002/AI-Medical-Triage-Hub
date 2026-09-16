import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import ChatWidget from '../components/ChatWidget';

const CLOSED_STATUSES = ['completed', 'resolved', 'report sent'];
const isClosed = (status) => CLOSED_STATUSES.includes((status || '').toLowerCase());

const PRIORITY_RANK = { high: 0, medium: 1, low: 2 };
const priorityRank = (priority) => PRIORITY_RANK[(priority || '').toLowerCase()] ?? 3;

const DoctorDashboard = () => {
  const [tickets, setTickets] = useState([]);
  const [patientMap, setPatientMap] = useState({});
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('active');
  const [priorityFilter, setPriorityFilter] = useState('all');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const response = await api.get('/tickets/');
      setTickets(response.data.tickets || []);
      setPatientMap(response.data.patient_map || {});
      setUser(response.data.user);
    } catch (err) {
      console.error('Failed to load tickets');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendReport = async (ticketId) => {
    if (!window.confirm('Generate and Save Report?')) return;
    try {
      const formData = new FormData();
      formData.append('ticket_id', ticketId);
      await api.post('/reports/generate', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      fetchData();
    } catch (err) {
      alert('Failed to generate report');
    }
  };

  const handlePriorityChange = async (ticketId, priority) => {
    if (!window.confirm(`Set priority to "${priority.toUpperCase()}" for this ticket?`)) return;

    setTickets((prev) =>
      prev.map((t) => ((t._id || t.id) === ticketId ? { ...t, priority } : t))
    );
    try {
      const formData = new FormData();
      formData.append('priority', priority);
      await api.post(`/tickets/${ticketId}/priority`, formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
    } catch (err) {
      alert('Failed to update priority');
      fetchData();
    }
  };

  const visibleTickets = tickets
    .filter((ticket) => (activeTab === 'closed' ? isClosed(ticket.status) : !isClosed(ticket.status)))
    .filter((ticket) => priorityFilter === 'all' || (ticket.priority || '').toLowerCase() === priorityFilter)
    .sort((a, b) => priorityRank(a.priority) - priorityRank(b.priority));

  return (
    <div className="bg-base-200 min-h-screen">
      <div className="max-w-4xl mx-auto pt-8 px-4">
        <h1 className="text-3xl font-bold text-white mb-2">Doctor Dashboard</h1>
        <p className="text-gray-400 mb-8">Welcome back. Here are the cases assigned to you.</p>

        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div role="tablist" className="tabs tabs-boxed w-fit bg-base-100 border border-white/5">
            <a
              role="tab"
              className={`tab uppercase text-xs font-bold tracking-widest ${activeTab === 'active' ? 'tab-active' : ''}`}
              onClick={() => setActiveTab('active')}
            >
              In Progress ({tickets.filter((t) => !isClosed(t.status)).length})
            </a>
            <a
              role="tab"
              className={`tab uppercase text-xs font-bold tracking-widest ${activeTab === 'closed' ? 'tab-active' : ''}`}
              onClick={() => setActiveTab('closed')}
            >
              Closed ({tickets.filter((t) => isClosed(t.status)).length})
            </a>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-500 uppercase tracking-widest font-black">Filter:</span>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="select select-sm select-bordered bg-base-100 border-white/5 uppercase text-[10px] font-bold tracking-widest"
            >
              <option value="all">All Priorities</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-20">
            <span className="loading loading-spinner loading-lg text-primary"></span>
          </div>
        ) : (
          <div className="grid gap-4">
            {visibleTickets.map((ticket) => (
              <div key={ticket.id} className="card bg-base-100 shadow-md border border-white/5">
                <div className="card-body p-5">
                  <div className="flex justify-between items-start">
                    <h3 className="font-bold text-lg text-white">
                      <Link to={`/tickets/${ticket.id}`} className="hover:underline hover:text-primary transition-colors uppercase">
                        {ticket.title}
                      </Link>
                    </h3>
                    <span className={`badge uppercase font-bold text-[10px] ${
                      ticket.status === 'completed' || ticket.status === 'Report Sent' ? 'badge-primary badge-outline' : 'badge-primary'
                    }`}>
                      {ticket.status}
                    </span>
                  </div>
                  <p className="text-sm text-gray-400 leading-relaxed mt-2">{ticket.description}</p>

                  <div className="flex justify-between items-center mt-6 border-t border-white/5 pt-4">
                    <div className="text-[10px] text-gray-500 uppercase tracking-widest font-black flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <span>Created by:</span>
                        <span className="text-gray-300">{patientMap[ticket.createdBy || ticket.created_by] || ticket.createdBy || ticket.created_by}</span>
                      </div>
                      <span className="opacity-40 lowercase font-medium tracking-normal">{new Date(ticket.createdAt || ticket.created_at).toLocaleString()}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      {!isClosed(ticket.status) && (
                        <select
                          value={(ticket.priority || '').toLowerCase()}
                          onChange={(e) => handlePriorityChange(ticket._id || ticket.id, e.target.value)}
                          className="select select-sm select-bordered bg-base-200 border-white/10 uppercase text-[10px] font-bold tracking-widest"
                        >
                          <option value="" disabled>Priority</option>
                          <option value="high">High</option>
                          <option value="medium">Medium</option>
                          <option value="low">Low</option>
                        </select>
                      )}
                      {(ticket.status === 'completed' || ticket.status === 'resolved') && (
                        <button
                          onClick={() => handleSendReport(ticket._id || ticket.id)}
                          className="btn btn-sm btn-primary px-4 shadow-lg shadow-primary/20"
                        >
                          Send Report
                        </button>
                      )}
                      <Link to={`/tickets/${ticket._id || ticket.id}`} className="btn btn-sm btn-ghost">
                        Details
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {visibleTickets.length === 0 && (
              <div className="text-center py-16 text-gray-500 bg-base-100 rounded-2xl border border-white/5 uppercase tracking-widest text-sm font-bold">
                {activeTab === 'closed' ? 'No closed cases.' : 'No cases in progress.'}
              </div>
            )}
          </div>
        )}
      </div>

      <ChatWidget />
    </div>
  );
};

export default DoctorDashboard;
