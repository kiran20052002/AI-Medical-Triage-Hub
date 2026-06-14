import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import api from '../services/api';

const TicketDetailPage = () => {
  const { id } = useParams();
  const [ticket, setTicket] = useState(null);
  const [assignedEmail, setAssignedEmail] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    try {
      const response = await api.get(`/tickets/${id}`);
      setTicket(response.data.ticket);
      setAssignedEmail(response.data.assigned_email);
      setUser(response.data.user);
    } catch (err) {
      console.error('Failed to load ticket details:', err);
      navigate('/dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  const getDashboardLink = () => {
    if (!user) return "/dashboard";
    if (user.role === 'admin') return "/dashboard/admin";
    if (user.role === 'doctor') return "/dashboard/doctor";
    return "/dashboard";
  };

  const handleSmartClose = async () => {
    if (!window.confirm('Run AI Analysis for closure?')) return;
    try {
      const response = await api.post(`/tickets/${id}/analyze-closure`);
      const { status, message } = response.data;
      if (status === 'blocked') {
        alert('⚠️ ' + message);
        fetchData();
      } else if (status === 'closed') {
        alert('✅ ' + message);
        fetchData();
      }
    } catch (err) {
      alert('Error during closure analysis');
    }
  };

  const handleRequestConnection = async () => {
    try {
      await api.post(`/tickets/${id}/request-connection`);
      fetchData();
    } catch (err) {
      alert('Failed to request connection');
    }
  };

  const handleAcceptConnection = async () => {
    try {
      await api.post(`/tickets/${id}/accept-connection`);
      fetchData();
    } catch (err) {
      alert('Failed to accept connection');
    }
  };

  if (isLoading) return (
    <div className="flex justify-center items-center min-h-[60vh]">
      <span className="loading loading-spinner loading-lg text-primary"></span>
    </div>
  );
  if (!ticket) return null;

  return (
    <div className="max-w-3xl mx-auto p-4 pb-20 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link to={getDashboardLink()} className="btn btn-sm btn-ghost mb-2 px-0 hover:bg-transparent text-gray-400 hover:text-white">
            ← Back to Dashboard
          </Link>
          <h2 className="text-3xl font-bold text-white tracking-tight">Ticket Details</h2>
        </div>

        <div className="flex gap-2">
          {user?.role !== 'patient' && ticket.status !== 'completed' && (
            <button 
              onClick={handleSmartClose}
              className="btn btn-primary shadow-lg shadow-primary/20 hover:scale-[1.02] transition-all"
            >
              Smart Close
            </button>
          )}
        </div>
      </div>

      {/* Ticket Info Card */}
      <div className="card bg-base-100 shadow-xl border border-white/5 overflow-hidden">
        <div className="card-body p-8 space-y-6">
          <div className="flex justify-between items-start">
            <h3 className="text-2xl font-bold text-white">{ticket.title}</h3>
            <div className={`badge badge-primary badge-outline uppercase font-black text-[10px] tracking-widest px-3 py-3 border-primary/30`}>{ticket.status}</div>
          </div>

          <p className="text-gray-300 leading-relaxed text-lg">{ticket.description}</p>

          <div className="divider opacity-30 uppercase font-black text-[10px] tracking-[0.2em] text-gray-500">Metadata</div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-y-6 gap-x-12">
            <div className="space-y-1">
              <span className="text-[10px] uppercase font-black text-gray-500 tracking-widest">Status</span>
              <p className="text-white font-medium">{ticket.status}</p>
            </div>
            
            {ticket.priority && (
              <div className="space-y-1">
                <span className="text-[10px] uppercase font-black text-gray-500 tracking-widest">Priority</span>
                <p className={`font-bold ${ticket.priority === 'High' ? 'text-red-400' : 'text-primary'}`}>{ticket.priority}</p>
              </div>
            )}

            {ticket.specialist && (
              <div className="space-y-1">
                <span className="text-[10px] uppercase font-black text-gray-500 tracking-widest">Needed Specialists</span>
                <p className="text-white font-medium">{ticket.specialist.join(', ')}</p>
              </div>
            )}

            <div className="space-y-1">
              <span className="text-[10px] uppercase font-black text-gray-500 tracking-widest">Assigned To</span>
              <p className="text-white font-medium">
                {assignedEmail || ((ticket.assignedTo || ticket.assigned_to) ? <span className="text-gray-500 text-xs italic">System ID: {ticket.assignedTo || ticket.assigned_to}</span> : <span className="text-gray-600 italic">Unassigned</span>)}
              </p>
            </div>

            {/* Connection Flow */}
            <div className="col-span-full border-t border-white/5 pt-6 mt-2">
              {(ticket.assignedTo || ticket.assigned_to) ? (
                (ticket.connectionStatus === 'accepted' || ticket.connection_status === 'accepted') ? (
                  <div className="flex items-center gap-4">
                    <div className="badge badge-primary badge-lg font-bold uppercase text-[10px] tracking-widest py-4 px-6 shadow-lg shadow-indigo-500/20">Connection Accepted</div>
                    <Link to="/chat" className="btn btn-sm btn-outline border-white/10 hover:bg-white/5 text-xs uppercase font-black tracking-widest">
                      Go to Chat
                    </Link>
                  </div>
                ) : (ticket.connectionStatus === 'requested' || ticket.connection_status === 'requested') ? (
                  user?.role !== 'patient' && (ticket.assignedTo === user?.id || ticket.assigned_to === user?.id) ? (
                    <button onClick={handleAcceptConnection} className="btn btn-primary text-white w-full md:w-auto px-12 shadow-lg shadow-primary/20">
                      Accept Connection
                    </button>
                  ) : (
                    <div className="alert bg-amber-500/10 border-amber-500/20 text-amber-200 shadow-sm py-3 px-4 rounded-xl">
                       <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="stroke-current shrink-0 w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                      <span className="text-xs font-bold uppercase tracking-widest">Pending connection acceptance</span>
                    </div>
                  )
                ) : user?.role === 'patient' && (ticket.createdBy === user?.id || ticket.created_by === user?.id) ? (
                  <button onClick={handleRequestConnection} className="btn btn-primary w-full md:w-auto px-12 shadow-lg shadow-primary/20">
                    Request Connection
                  </button>
                ) : (
                  <div className="text-sm text-gray-500 italic flex items-center gap-2">
                    <span className="loading loading-dots loading-xs text-primary"></span>
                    Awaiting connection request...
                  </div>
                )
              ) : (
                <div className="text-sm text-gray-500 italic flex items-center gap-2">
                   <span className="loading loading-spinner loading-xs text-primary"></span>
                  No doctor assigned yet. AI is analyzing...
                </div>
              )}
            </div>

            <div className="col-span-full pt-4">
              <p className="text-[10px] text-gray-600 uppercase font-black tracking-widest">
                Created At: {new Date(ticket.createdAt || ticket.created_at).toLocaleString()}
              </p>
            </div>
          </div>

          {ticket.helpful_notes && (
            <div className="bg-base-200/50 p-6 rounded-2xl mt-4 border border-white/5 space-y-3">
              <strong className="text-primary uppercase text-[10px] tracking-[0.2em] font-black">Helpful Notes</strong>
              <div className="prose prose-sm max-w-none text-gray-400 italic leading-relaxed">
                {ticket.helpful_notes}
              </div>
            </div>
          )}

          {ticket.suggested_solution && (
            <div className="alert alert-info bg-indigo-500/10 border-indigo-500/20 text-indigo-100 p-6 rounded-2xl flex-col items-start gap-2 shadow-lg shadow-indigo-500/5">
              <span className="font-black uppercase text-[10px] tracking-widest text-indigo-400">AI Suggestion</span>
              <p className="text-sm leading-relaxed">{ticket.suggested_solution}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TicketDetailPage;
