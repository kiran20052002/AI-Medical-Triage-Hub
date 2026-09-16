import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import ChatWidget from '../components/ChatWidget';

const DoctorDashboard = () => {
  const [tickets, setTickets] = useState([]);
  const [patientMap, setPatientMap] = useState({});
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

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

  return (
    <div className="bg-base-200 min-h-screen">
      <div className="max-w-4xl mx-auto pt-8 px-4">
        <h1 className="text-3xl font-bold text-white mb-2">Doctor Dashboard</h1>
        <p className="text-gray-400 mb-8">Welcome back. Here are the cases assigned to you.</p>

        {isLoading ? (
          <div className="flex justify-center py-20">
            <span className="loading loading-spinner loading-lg text-primary"></span>
          </div>
        ) : (
          <div className="grid gap-4">
            {tickets.map((ticket) => (
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

                    <div className="flex gap-2">
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
            {tickets.length === 0 && (
              <div className="text-center py-16 text-gray-500 bg-base-100 rounded-2xl border border-white/5 uppercase tracking-widest text-sm font-bold">
                No cases assigned.
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
