import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '../context/AuthContext';

const WELCOME_MESSAGE = { role: 'assistant', content: 'Hello! I am your medical assistant. How can I help you today?' };

const ChatWidget = () => {
  const { user } = useAuth();
  const threadStorageKey = `widget_thread_id:${user?.id}`;
  const [isOpen, setIsOpen] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [showSessions, setShowSessions] = useState(false);
  const [currentThreadId, setCurrentThreadId] = useState(() => localStorage.getItem(`widget_thread_id:${user?.id}`));
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [inputText, setInputText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [threads, setThreads] = useState([]);
  const hasLoadedHistoryRef = useRef(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (currentThreadId) {
      localStorage.setItem(threadStorageKey, currentThreadId);
    } else {
      localStorage.removeItem(threadStorageKey);
    }
  }, [currentThreadId, threadStorageKey]);

  useEffect(() => {
    if (isOpen && currentThreadId && !hasLoadedHistoryRef.current) {
      hasLoadedHistoryRef.current = true;
      loadHistory(currentThreadId);
    }
  }, [isOpen, currentThreadId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const createThread = async () => {
    const res = await api.post('/chatbot/threads');
    const threadId = res.data.thread_id;
    setCurrentThreadId(threadId);
    return threadId;
  };

  const loadHistory = async (tid) => {
    try {
      const res = await api.get(`/chatbot/history/${encodeURIComponent(tid)}`);
      if (res.data.history && res.data.history.length > 0) {
        setMessages([WELCOME_MESSAGE, ...res.data.history]);
      }
    } catch (e) {
      console.error('Failed to load history');
    }
  };

  const loadThreads = async () => {
    try {
      const res = await api.get('/chatbot/threads');
      setThreads(res.data.threads || []);
    } catch (e) {
      console.error('Failed to load threads');
    }
  };

  const toggleSessions = () => {
    setShowSessions(!showSessions);
    if (!showSessions) loadThreads();
  };

  const startNewChat = async () => {
    try {
      const tid = await createThread();
      hasLoadedHistoryRef.current = true;
      setMessages([WELCOME_MESSAGE]);
      setShowSessions(false);
      loadThreads();
      return tid;
    } catch (e) {
      console.error('Failed to create chat session');
    }
  };

  const selectThread = async (tid) => {
    setCurrentThreadId(tid);
    hasLoadedHistoryRef.current = true;
    setMessages([WELCOME_MESSAGE]);
    setShowSessions(false);
    await loadHistory(tid);
  };

  const toggleClosureSelection = (idx, ticketId) => {
    setMessages(prev => {
      const copy = [...prev];
      const current = copy[idx].selectedClosureIds || [];
      const next = current.includes(ticketId)
        ? current.filter(id => id !== ticketId)
        : [...current, ticketId];
      copy[idx] = { ...copy[idx], selectedClosureIds: next };
      return copy;
    });
  };

  const toggleReportSelection = (idx, ticketId) => {
    setMessages(prev => {
      const copy = [...prev];
      const current = copy[idx].selectedReportIds || [];
      const next = current.includes(ticketId)
        ? current.filter(id => id !== ticketId)
        : [...current, ticketId];
      copy[idx] = { ...copy[idx], selectedReportIds: next };
      return copy;
    });
  };

  const handleApproveAction = async (idx, action, tid, selectedIds) => {
    setMessages(prev => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], approvalLoading: true };
      return copy;
    });

    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      const body = { thread_id: tid, action: action };
      if (selectedIds) body.selected_ids = selectedIds;
      const response = await fetch(`${baseUrl}/chatbot/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        credentials: 'include',
      });

      if (!response.ok) throw new Error('Action failed');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = '';
      let isFirstChunk = true;

      setMessages(prev => {
        const copy = [...prev];
        copy[idx] = {
          role: 'assistant',
          content: 'Processing...',
          requiresApproval: false,
          requiresClosureApproval: false,
          requiresReportApproval: false
        };
        return copy;
      });

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.substring(6);
            if (dataStr === '[DONE]') continue;

            try {
              const data = JSON.parse(dataStr);
              if (data.status === 'requires_approval') {
                setMessages(prev => {
                  const copy = [...prev];
                  copy[idx] = {
                    role: 'assistant',
                    content: '',
                    requiresApproval: true,
                    ticketDetails: data.ticket_details
                  };
                  return copy;
                });
                return;
              }

              if (data.status === 'requires_closure_approval') {
                setMessages(prev => {
                  const copy = [...prev];
                  copy[idx] = {
                    role: 'assistant',
                    content: '',
                    requiresClosureApproval: true,
                    closureDetails: data.closure_details,
                    selectedClosureIds: (data.closure_details?.candidates || []).map(c => c.id)
                  };
                  return copy;
                });
                return;
              }

              if (data.status === 'requires_report_approval') {
                setMessages(prev => {
                  const copy = [...prev];
                  copy[idx] = {
                    role: 'assistant',
                    content: '',
                    requiresReportApproval: true,
                    reportDetails: data.report_details,
                    selectedReportIds: (data.report_details?.candidates || []).map(c => c.id)
                  };
                  return copy;
                });
                return;
              }

              if (data.content) {
                if (isFirstChunk) {
                  assistantMessage = data.content;
                  isFirstChunk = false;
                } else {
                  assistantMessage += data.content;
                }
                setMessages(prev => {
                  const copy = [...prev];
                  copy[idx] = {
                    role: 'assistant',
                    content: assistantMessage,
                    requiresApproval: false,
                    requiresClosureApproval: false,
                    requiresReportApproval: false
                  };
                  return copy;
                });
              }
            } catch (e) {}
          }
        }
      }
    } catch (err) {
      setMessages(prev => {
        const copy = [...prev];
        copy[idx] = {
          role: 'assistant',
          content: 'I encountered an error processing your approval. Please try again.',
          error: true,
          requiresApproval: false,
          requiresClosureApproval: false,
          requiresReportApproval: false
        };
        return copy;
      });
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    const text = inputText.trim();
    if (!text || isStreaming) return;

    let tid = currentThreadId;
    if (!tid) {
      try {
        tid = await createThread();
      } catch (e) {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Could not start a chat session. Please try again.', error: true }]);
        return;
      }
    }

    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setInputText('');
    setIsStreaming(true);

    try {
      await sendQueryToThread(tid, text);
    } catch (err) {
      if (err?.status === 404) {
        try {
          const freshTid = await createThread();
          await sendQueryToThread(freshTid, text);
          return;
        } catch (retryErr) {
          // fall through to generic error below
        }
      }
      setMessages(prev => [...prev, { role: 'assistant', content: 'I encountered an error. Please try again.', error: true }]);
    } finally {
      setIsStreaming(false);
    }
  };

  const sendQueryToThread = async (tid, text) => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    const response = await fetch(`${baseUrl}/chatbot/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: text, thread_id: tid }),
      credentials: 'include',
    });

    if (!response.ok) {
      const error = new Error('Query failed');
      error.status = response.status;
      throw error;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let assistantMessage = '';
    let isFirstChunk = true;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.substring(6);
          if (dataStr === '[DONE]') continue;

          try {
            const data = JSON.parse(dataStr);
            if (data.status === 'requires_approval') {
              setMessages(prev => {
                const others = isFirstChunk ? prev : prev.slice(0, -1);
                return [
                  ...others,
                  {
                    role: 'assistant',
                    content: '',
                    requiresApproval: true,
                    ticketDetails: data.ticket_details
                  }
                ];
              });
              return;
            }

            if (data.status === 'requires_closure_approval') {
              setMessages(prev => {
                const others = isFirstChunk ? prev : prev.slice(0, -1);
                return [
                  ...others,
                  {
                    role: 'assistant',
                    content: '',
                    requiresClosureApproval: true,
                    closureDetails: data.closure_details,
                    selectedClosureIds: (data.closure_details?.candidates || []).map(c => c.id)
                  }
                ];
              });
              return;
            }

            if (data.status === 'requires_report_approval') {
              setMessages(prev => {
                const others = isFirstChunk ? prev : prev.slice(0, -1);
                return [
                  ...others,
                  {
                    role: 'assistant',
                    content: '',
                    requiresReportApproval: true,
                    reportDetails: data.report_details,
                    selectedReportIds: (data.report_details?.candidates || []).map(c => c.id)
                  }
                ];
              });
              return;
            }

            if (data.content) {
              if (isFirstChunk) {
                assistantMessage = data.content;
                setMessages(prev => [...prev, { role: 'assistant', content: assistantMessage }]);
                isFirstChunk = false;
              } else {
                assistantMessage += data.content;
                setMessages(prev => {
                  const last = prev[prev.length - 1];
                  const others = prev.slice(0, -1);
                  return [...others, { ...last, content: assistantMessage }];
                });
              }
            }
          } catch (e) {}
        }
      }
    }
  };

  return (
    <div className="fixed bottom-8 right-8 z-[100] flex flex-col items-end pointer-events-none">
      {/* Chat Window */}
      {isOpen && (
        <div
          className={`pointer-events-auto bg-base-100/90 backdrop-blur-2xl rounded-3xl shadow-2xl border border-white/10 mb-6 flex flex-col overflow-hidden transition-all duration-300 ease-in-out transform origin-bottom-right animate-in zoom-in-90 fade-in duration-200 ${
            isMaximized ? 'w-[700px] h-[70vh]' : 'w-96 h-[600px]'
          }`}
        >
          {/* Header */}
          <header className="bg-gradient-to-r from-primary to-indigo-600 p-5 flex justify-between items-center text-white shrink-0">
            <div className="flex items-center space-x-3">
              <button
                onClick={toggleSessions}
                className="btn btn-ghost btn-square btn-sm hover:bg-white/10 text-white"
              >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-5 h-5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
              </button>
              <h3 className="font-bold tracking-tight uppercase text-xs">AI Assistant</h3>
            </div>
            <div className="flex items-center gap-1">
              <button onClick={startNewChat} className="btn btn-ghost btn-square btn-sm hover:bg-white/10 text-white" title="New Chat">
                 <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-5 h-5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                  </svg>
              </button>
              <Link to="/chatbot" className="btn btn-ghost btn-square btn-sm hover:bg-white/10 text-white" title="Full Page View">
                 <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-5 h-5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                  </svg>
              </Link>
              <button onClick={() => setIsMaximized(!isMaximized)} className="btn btn-ghost btn-square btn-sm hover:bg-white/10 text-white">
                 {isMaximized ? (
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-4 h-4"><path strokeLinecap="round" strokeLinejoin="round" d="M9 9V4.5M9 9H4.5M9 9L3 3m12 12V19.5m0-4.5h4.5m-4.5 0l6 6" /></svg>
                 ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-4 h-4"><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" /></svg>
                 )}
              </button>
              <button onClick={() => setIsOpen(false)} className="btn btn-ghost btn-square btn-sm hover:bg-white/10 text-white">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
          </header>

          {/* Body */}
          <div className="flex-1 relative overflow-hidden flex flex-col min-h-0 bg-base-100/50">
            {/* Messages */}
            <div className={`flex-1 overflow-y-auto p-6 space-y-4 ${showSessions ? 'blur-sm grayscale pointer-events-none' : ''}`}>
              {messages.map((msg, idx) => {
                 const isMe = msg.role === 'user';
                 return (
                  <div key={idx} className={`chat ${isMe ? 'chat-end' : 'chat-start'}`}>
                    {msg.requiresApproval ? (
                      <div className="chat-bubble bg-base-200 border border-warning/20 rounded-2xl p-4 max-w-sm shadow-xl">
                        <div className="flex items-center gap-2 text-warning mb-2">
                          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-5 h-5">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          <h3 className="font-bold text-xs uppercase tracking-wider text-white">Approval Required</h3>
                        </div>
                        <p className="text-[11px] text-gray-400 mb-3">Create support ticket:</p>
                        <div className="bg-base-300/50 rounded-lg p-3 border border-white/5 space-y-2 mb-4">
                          <div>
                            <span className="text-[9px] font-black uppercase tracking-widest text-gray-500">Title</span>
                            <p className="text-xs font-semibold text-white mt-0.5">{msg.ticketDetails?.title || 'No Title'}</p>
                          </div>
                          <div>
                            <span className="text-[9px] font-black uppercase tracking-widest text-gray-500">Description</span>
                            <p className="text-[11px] font-medium text-gray-300 mt-1 leading-relaxed line-clamp-3">{msg.ticketDetails?.description || 'No Description'}</p>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <button
                            disabled={msg.approvalLoading}
                            onClick={() => handleApproveAction(idx, 'approve', currentThreadId)}
                            className="btn btn-primary btn-xs flex-1 font-bold rounded-lg uppercase tracking-wider shadow-lg shadow-primary/20"
                          >
                            {msg.approvalLoading ? <span className="loading loading-spinner loading-xs"></span> : 'Approve'}
                          </button>
                          <button
                            disabled={msg.approvalLoading}
                            onClick={() => handleApproveAction(idx, 'reject', currentThreadId)}
                            className="btn btn-ghost btn-xs flex-1 font-bold rounded-lg border border-white/10 uppercase tracking-wider hover:bg-red-500/10 hover:text-red-400"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : msg.requiresClosureApproval ? (
                      <div className="chat-bubble bg-base-200 border border-warning/20 rounded-2xl p-4 max-w-sm shadow-xl">
                        <div className="flex items-center gap-2 text-warning mb-2">
                          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-5 h-5">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          <h3 className="font-bold text-xs uppercase tracking-wider text-white">Confirm Closures</h3>
                        </div>
                        <p className="text-[11px] text-gray-400 mb-3">Select tickets to close:</p>
                        <div className="space-y-2 mb-4 max-h-56 overflow-y-auto">
                          {(msg.closureDetails?.candidates || []).map(c => (
                            <label key={c.id} className="flex items-start gap-2 bg-base-300/50 rounded-lg p-2.5 border border-white/5 cursor-pointer">
                              <input
                                type="checkbox"
                                className="checkbox checkbox-primary checkbox-xs mt-0.5"
                                checked={(msg.selectedClosureIds || []).includes(c.id)}
                                disabled={msg.approvalLoading}
                                onChange={() => toggleClosureSelection(idx, c.id)}
                              />
                              <div className="min-w-0">
                                <p className="text-xs font-semibold text-white">{c.title}</p>
                                <p className="text-[10px] text-gray-400 mt-0.5 leading-relaxed line-clamp-2">{c.reasoning}</p>
                              </div>
                            </label>
                          ))}
                        </div>
                        <div className="flex gap-2">
                          <button
                            disabled={msg.approvalLoading || (msg.selectedClosureIds || []).length === 0}
                            onClick={() => handleApproveAction(idx, 'approve', currentThreadId, msg.selectedClosureIds || [])}
                            className="btn btn-primary btn-xs flex-1 font-bold rounded-lg uppercase tracking-wider shadow-lg shadow-primary/20"
                          >
                            {msg.approvalLoading ? <span className="loading loading-spinner loading-xs"></span> : `Close (${(msg.selectedClosureIds || []).length})`}
                          </button>
                          <button
                            disabled={msg.approvalLoading}
                            onClick={() => handleApproveAction(idx, 'reject', currentThreadId)}
                            className="btn btn-ghost btn-xs flex-1 font-bold rounded-lg border border-white/10 uppercase tracking-wider hover:bg-red-500/10 hover:text-red-400"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : msg.requiresReportApproval ? (
                      <div className="chat-bubble bg-base-200 border border-warning/20 rounded-2xl p-4 max-w-sm shadow-xl">
                        <div className="flex items-center gap-2 text-warning mb-2">
                          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-5 h-5">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
                          </svg>
                          <h3 className="font-bold text-xs uppercase tracking-wider text-white">Confirm Reports</h3>
                        </div>
                        <p className="text-[11px] text-gray-400 mb-3">Select closed tickets to generate a report for:</p>
                        <div className="space-y-2 mb-4 max-h-56 overflow-y-auto">
                          {(msg.reportDetails?.candidates || []).map(c => (
                            <label key={c.id} className="flex items-start gap-2 bg-base-300/50 rounded-lg p-2.5 border border-white/5 cursor-pointer">
                              <input
                                type="checkbox"
                                className="checkbox checkbox-primary checkbox-xs mt-0.5"
                                checked={(msg.selectedReportIds || []).includes(c.id)}
                                disabled={msg.approvalLoading}
                                onChange={() => toggleReportSelection(idx, c.id)}
                              />
                              <div className="min-w-0">
                                <p className="text-xs font-semibold text-white">{c.title}</p>
                                <p className="text-[10px] text-gray-400 mt-0.5 leading-relaxed line-clamp-2">{c.reasoning}</p>
                              </div>
                            </label>
                          ))}
                        </div>
                        <div className="flex gap-2">
                          <button
                            disabled={msg.approvalLoading || (msg.selectedReportIds || []).length === 0}
                            onClick={() => handleApproveAction(idx, 'approve', currentThreadId, msg.selectedReportIds || [])}
                            className="btn btn-primary btn-xs flex-1 font-bold rounded-lg uppercase tracking-wider shadow-lg shadow-primary/20"
                          >
                            {msg.approvalLoading ? <span className="loading loading-spinner loading-xs"></span> : `Generate (${(msg.selectedReportIds || []).length})`}
                          </button>
                          <button
                            disabled={msg.approvalLoading}
                            onClick={() => handleApproveAction(idx, 'reject', currentThreadId)}
                            className="btn btn-ghost btn-xs flex-1 font-bold rounded-lg border border-white/10 uppercase tracking-wider hover:bg-red-500/10 hover:text-red-400"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className={`chat-bubble text-[13px] font-medium leading-relaxed ${
                        isMe
                          ? 'bg-primary text-white rounded-2xl shadow-lg shadow-primary/10'
                          : msg.error
                            ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                            : 'bg-base-200 text-gray-300 border border-white/5 rounded-2xl'
                      }`}>
                        <div className="prose prose-sm prose-invert max-w-none">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content}
                          </ReactMarkdown>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Sessions Overlay */}
            {showSessions && (
              <div className="absolute inset-0 bg-base-300/95 backdrop-blur-md z-20 flex flex-col p-6 animate-in fade-in slide-in-from-left-4 duration-300">
                <div className="flex justify-between items-center mb-6">
                  <h4 className="font-black uppercase tracking-[0.2em] text-[10px] text-gray-500">Recent Sessions</h4>
                  <button onClick={() => setShowSessions(false)} className="btn btn-ghost btn-xs text-primary font-bold uppercase tracking-widest px-0 hover:bg-transparent">Close</button>
                </div>
                <div className="flex-1 overflow-y-auto space-y-2">
                  {threads.length === 0 ? (
                    <p className="text-center text-gray-500 py-10 text-[10px] font-black uppercase tracking-widest italic">No recent sessions</p>
                  ) : (
                    [...threads].reverse().map(tid => (
                      <button
                        key={tid}
                        onClick={() => selectThread(tid)}
                        className={`w-full text-left p-4 rounded-xl transition-all border duration-300 ${
                          currentThreadId === tid ? 'bg-primary text-white border-primary shadow-lg shadow-primary/20' : 'hover:bg-white/5 border-transparent text-gray-400'
                        }`}
                      >
                        <div className="text-[10px] uppercase font-bold opacity-50 mb-1 tracking-widest leading-none">Session ID</div>
                        <div className="truncate text-[10px] font-mono">{tid}</div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <footer className="p-5 bg-base-300/50 border-t border-white/5 shrink-0">
            <form onSubmit={handleSendMessage} className="flex space-x-2">
              <input
                disabled={isStreaming}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Ask health question..."
                className="input input-bordered flex-1 bg-base-100 border-white/10 focus:border-primary transition-all rounded-xl h-11 text-sm text-white"
              />
              <button disabled={isStreaming} className="btn btn-primary btn-square h-11 w-11 rounded-xl shadow-lg shadow-primary/20">
                 <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" /></svg>
              </button>
            </form>
          </footer>
        </div>
      )}

      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="pointer-events-auto btn btn-primary btn-circle w-16 h-16 shadow-2xl hover:scale-110 active:scale-95 transition-all shadow-primary/40 p-0 border-none bg-gradient-to-tr from-primary to-indigo-600"
      >
        {isOpen ? (
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2.5" stroke="white" className="w-8 h-8"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
        ) : (
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="white" className="w-9 h-9"><path strokeLinecap="round" strokeLinejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48.432.447.74 1.04.586 1.641a4.483 4.483 0 01-.923 1.785A5.969 5.969 0 006 21c1.282 0 2.47-.402 3.445-1.087.81.22 1.668.337 2.555.337z" /></svg>
        )}
      </button>
    </div>
  );
};

export default ChatWidget;
