import React, { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import api from "../services/api";
import ChatWidget from "../components/ChatWidget";

const PatientDashboard = () => {
  const [tickets, setTickets] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTicket, setNewTicket] = useState({ title: "", description: "" });
  const [valError, setValError] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    fetchTickets();
  }, []);

  const fetchTickets = async () => {
    try {
      const response = await api.get("/tickets/");
      setTickets(response.data.tickets || []);
    } catch (err) {
      setError("Failed to load tickets");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateTicket = async (e) => {
    e.preventDefault();
    setValError(null);
    try {
      const formData = new FormData();
      formData.append("title", newTicket.title);
      formData.append("description", newTicket.description);

      await api.post("/tickets/create", formData, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      setNewTicket({ title: "", description: "" });
      setIsModalOpen(false);
      fetchTickets();
    } catch (err) {
      setValError(
        "Your ticket was not created because the description provided was unclear or not health-related. Please describe your medical issue clearly.",
      );
    }
  };

  const handleDeleteTicket = async (id) => {
    if (window.confirm("Are you sure you want to delete this ticket?")) {
      try {
        await api.delete(`/tickets/${id}`);
        fetchTickets();
      } catch (err) {
        console.error("Failed to delete ticket", err);
      }
    }
  };

  return (
    <div className="bg-base-200 min-h-screen">
      <div className="max-w-4xl mx-auto pt-8 px-4">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-white tracking-tight">
            My Tickets
          </h1>
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn btn-primary shadow-lg shadow-indigo-500/20"
          >
            Create Ticket
          </button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-20">
            <span className="loading loading-spinner loading-lg text-primary"></span>
          </div>
        ) : error ? (
          <div className="alert alert-error shadow-lg">
            <span>{error}</span>
          </div>
        ) : (
          <div className="grid gap-6">
            {tickets.map((ticket) => (
              <div
                key={ticket.id}
                className="card bg-base-100 shadow-xl border border-white/5 hover:border-white/10 transition-all group"
              >
                <div className="card-body">
                  <h2 className="card-title flex justify-between text-white font-bold">
                    {ticket.title}
                    <div
                      className={`badge badge-outline uppercase tracking-wider font-bold text-[10px] ${
                        ticket.status === "resolved"
                          ? "badge-primary"
                          : "badge-primary"
                      }`}
                    >
                      {ticket.status}
                    </div>
                  </h2>
                  <p className="text-gray-400 text-sm leading-relaxed mb-4">
                    {ticket.description}
                  </p>
                  <div className="card-actions justify-end">
                    <button
                      onClick={() => handleDeleteTicket(ticket._id || ticket.id)}
                      className="btn btn-sm btn-error btn-outline hover:bg-red-500 hover:text-white transition-colors"
                    >
                      Delete
                    </button>
                    <Link
                      to={`/tickets/${ticket._id || ticket.id}`}
                      className="btn btn-sm btn-ghost hover:bg-white/10 transition-colors"
                    >
                      View Details
                    </Link>
                  </div>
                </div>
              </div>
            ))}
            {tickets.length === 0 && (
              <div className="text-center p-16 card bg-base-100/50 border border-dashed border-white/10">
                <p className="text-gray-500 font-medium">
                  No tickets found. Create one to get started!
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* React Integrated Modal */}
      {isModalOpen && (
        <div className="modal modal-open" role="dialog">
          <div className="modal-box bg-base-100 border border-white/10 shadow-2xl">
            <h3 className="font-bold text-xl text-white">Create New Ticket</h3>
            
            {valError && (
              <div className="alert alert-error shadow-lg my-4 bg-red-500/20 border-red-500/20 text-red-100 flex justify-between">
                <span className="text-xs font-medium">{valError}</span>
                <button type="button" className="btn btn-xs btn-ghost btn-circle" onClick={() => setValError(null)}>✕</button>
              </div>
            )}

            <form onSubmit={handleCreateTicket} className="py-4 space-y-4">
              <div className="form-control w-full">
                <label className="label">
                  <span className="label-text text-gray-400 font-semibold uppercase text-xs tracking-widest">
                    Title
                  </span>
                </label>
                <input
                  type="text"
                  value={newTicket.title}
                  onChange={(e) =>
                    setNewTicket({ ...newTicket, title: e.target.value })
                  }
                  placeholder="Summary of issue"
                  className="input input-bordered w-full bg-base-200 border-white/10 focus:border-primary transition-all rounded-xl"
                  required
                />
              </div>
              <div className="form-control w-full">
                <label className="label">
                  <span className="label-text text-gray-400 font-semibold uppercase text-xs tracking-widest">
                    Description
                  </span>
                </label>
                <textarea
                  value={newTicket.description}
                  onChange={(e) =>
                    setNewTicket({ ...newTicket, description: e.target.value })
                  }
                  className="textarea textarea-bordered h-32 bg-base-200 border-white/10 focus:border-primary transition-all rounded-xl resize-none"
                  placeholder="Describe your medical concerns in detail..."
                  required
                ></textarea>
              </div>
              <div className="modal-action">
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary px-8">
                  Create Ticket
                </button>
              </div>
            </form>
          </div>
          <div
            className="modal-backdrop bg-black/40 backdrop-blur-sm"
            onClick={() => setIsModalOpen(false)}
          ></div>
        </div>
      )}

      <ChatWidget />
    </div>
  );
};

export default PatientDashboard;
