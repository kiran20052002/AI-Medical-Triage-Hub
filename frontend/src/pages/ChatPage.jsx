import React, { useEffect, useState, useRef } from 'react';
import { io } from 'socket.io-client';
import api from '../services/api';
import { Send, User, MessageSquare, Clock, ShieldCheck, ChevronRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const SOCKET_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const ChatPage = () => {
  const [tickets, setTickets] = useState([]);
  const [activeTicket, setActiveTicket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const { user } = useAuth();
  const [socket, setSocket] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const messagesEndRef = useRef(null);
  const activeTicketRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  useEffect(() => {
    activeTicketRef.current = activeTicket;
  }, [activeTicket]);

  useEffect(() => {
    const init = async () => {
      try {
        const ticketsRes = await api.get('/tickets/');
        
        const activeTickets = ticketsRes.data.tickets.filter(t => 
          (t.connectionStatus === 'accepted' || t.connection_status === 'accepted')
        );
        setTickets(activeTickets);
        
        const newSocket = io(SOCKET_URL, {
          path: '/socket.io/',
          transports: ['websocket']
        });

        newSocket.on('connect', () => {
          console.log('Connected to socket');
        });

        newSocket.on('new_message', (msg) => {
          const currentTicket = activeTicketRef.current;
          if (currentTicket) {
            const tId = currentTicket._id || currentTicket.id;
            if (msg.ticketId === tId) {
              setMessages((prev) => [...prev, msg]);
            }
          }
        });

        setSocket(newSocket);
      } catch (err) {
        console.error('Initialization error:', err);
      } finally {
        setIsLoading(false);
      }
    };

    init();

    return () => {
      if (socket) socket.disconnect();
    };
  }, []);

  useEffect(() => {
    if (activeTicket && socket) {
      // Fetch history
      const tId = activeTicket._id || activeTicket.id;
      api.get(`/chat/history/${tId}`).then((res) => {
        setMessages(res.data.messages || []);
      });

      // Join room
      socket.emit('join_room', { room: `ticket-${tId}` });
    }
  }, [activeTicket]);

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !activeTicket || !socket || !user) return;

    const messageData = {
      ticketId: activeTicket._id || activeTicket.id,
      senderId: user.id || user._id,
      senderName: user.email,
      senderRole: user.role,
      text: newMessage
    };

    socket.emit('send_message', messageData);
    setNewMessage('');
    // Note: The message will be updated in state via the 'new_message' listener
  };

  if (isLoading) return (
    <div className="h-screen flex items-center justify-center bg-base-300">
      <span className="loading loading-spinner loading-lg text-primary"></span>
    </div>
  );

  return (
    <div className="h-screen flex bg-base-300 overflow-hidden font-sans text-slate-200">
      {/* Sidebar: Ticket List */}
      <div className="w-80 border-r border-white/5 flex flex-col bg-base-300 shadow-2xl relative z-10">
        <header className="p-6 border-b border-white/5 bg-base-300/50 backdrop-blur-md">
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-3">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.5)] animate-pulse"></div>
            <span>Consultations</span>
          </h2>
        </header>
        
        <div className="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar">
          {tickets.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-slate-500 px-6 text-center space-y-2">
              <MessageSquare size={32} opacity={0.3} />
              <p className="text-sm">No active consultations found.</p>
            </div>
          ) : (
            tickets.map((ticket) => (
              <button
                key={ticket._id}
                onClick={() => setActiveTicket(ticket)}
                className={`w-full p-4 rounded-2xl flex flex-col gap-1 transition-all duration-300 text-left group
                  ${activeTicket?._id === ticket._id 
                    ? 'bg-primary text-white shadow-lg shadow-primary/20 scale-[0.98]' 
                    : 'hover:bg-white/5 text-slate-400'}`}
              >
                <div className="flex items-center justify-between">
                  <span className={`font-semibold truncate ${activeTicket?._id === ticket._id ? 'text-white' : 'text-slate-200'}`}>
                    {ticket.title}
                  </span>
                  <ChevronRight size={16} className={`transition-transform duration-300 ${activeTicket?._id === ticket._id ? 'translate-x-1' : 'opacity-0'}`} />
                </div>
                <p className="text-xs truncate opacity-60">ID: {(ticket._id || ticket.id).slice(-8)}</p>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-base-100/30 relative">
        {activeTicket ? (
          <>
            {/* Chat Header */}
            <header className="p-6 border-b border-white/5 bg-base-200/50 backdrop-blur-xl flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-lg">
                  <User className="text-white" size={24} />
                </div>
                <div>
                  <h3 className="font-bold text-slate-100 text-lg">{activeTicket.title}</h3>
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <span className="flex items-center gap-1"><Clock size={12} /> Live Support</span>
                    <span className="w-1 h-1 rounded-full bg-slate-600"></span>
                    <span className="flex items-center gap-1"><ShieldCheck size={12} className="text-emerald-500" /> Secure</span>
                  </div>
                </div>
              </div>
            </header>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-8 space-y-6 custom-scrollbar bg-base-100/10">
              {messages.map((msg, idx) => {
                const isMe = msg.senderId === user.id;
                return (
                  <div key={idx} className={`flex ${isMe ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
                    <div className={`flex flex-col max-w-[70%] gap-1 ${isMe ? 'items-end' : 'items-start'}`}>
                      {!isMe && <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500 ml-2">{msg.senderName.split('@')[0]}</span>}
                      <div className={`p-4 rounded-2xl shadow-sm leading-relaxed
                        ${isMe 
                          ? 'bg-primary text-white rounded-tr-none' 
                          : 'bg-base-300 text-slate-200 rounded-tl-none border border-white/5'}`}
                      >
                        {msg.text}
                      </div>
                      <span className="text-[10px] text-slate-600 mt-1 px-1">
                        {new Date(msg.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Message Input */}
            <form onSubmit={handleSendMessage} className="p-6 bg-base-200/50 border-t border-white/5 backdrop-blur-md">
              <div className="flex gap-4 items-center bg-base-300 rounded-2xl p-2 pr-4 border border-white/5 focus-within:border-primary/50 transition-all shadow-inner">
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder="Type your message..."
                  className="flex-1 bg-transparent border-none focus:ring-0 px-4 py-3 text-slate-200 placeholder:text-slate-500"
                />
                <button
                  type="submit"
                  disabled={!newMessage.trim()}
                  className="bg-primary hover:bg-primary-focus disabled:opacity-50 disabled:hover:bg-primary text-white p-3 rounded-xl transition-all duration-300 shadow-lg shadow-primary/20 hover:scale-105 active:scale-95"
                >
                  <Send size={20} />
                </button>
              </div>
            </form>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center space-y-4 text-slate-500">
            <div className="w-20 h-20 rounded-full bg-base-300 flex items-center justify-center">
               <MessageSquare size={40} opacity={0.2} />
            </div>
            <h3 className="text-xl font-medium">Select a conversation</h3>
            <p className="text-sm max-w-xs text-center opacity-60">Choose a consultation from the sidebar to start secure messaging with your doctor.</p>
          </div>
        )}
      </div>
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.1);
        }
      `}</style>
    </div>
  );
};

export default ChatPage;
