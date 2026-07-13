import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const ChatWidget = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [showSessions, setShowSessions] = useState(false);
  const [currentThreadId, setCurrentThreadId] = useState(() => {
    return localStorage.getItem('widget_thread_id') || `widget-${Math.random().toString(36).substring(2, 11)}`;
  });
  const [messages, setMessages] = useState([{ role: 'assistant', content: 'Hello! I am your medical assistant. How can I help you today?' }]);
  const [inputText, setInputText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [threads, setThreads] = useState([]);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    localStorage.setItem('widget_thread_id', currentThreadId);
    if (isOpen && messages.length <= 1) {
      loadHistory();
    }
  }, [currentThreadId, isOpen]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadHistory = async () => {
    try {
      const res = await api.get(`/chatbot/history/${encodeURIComponent(currentThreadId)}`);
      if (res.data.history && res.data.history.length > 0) {
        setMessages([{ role: 'assistant', content: 'Hello! I am your medical assistant. How can I help you today?' }, ...res.data.history]);
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

  const startNewChat = () => {
    const newTid = `widget-${Math.random().toString(36).substring(2, 11)}`;
    setCurrentThreadId(newTid);
    setMessages([{ role: 'assistant', content: 'Hello! I am your medical assistant. How can I help you today?' }]);
    setShowSessions(false);
  };

  const handleApproveAction = async (idx, action, tid) => {
    setMessages(prev => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], approvalLoading: true };
      return copy;
    });

    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      const response = await fetch(`${baseUrl}/chatbot/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: tid, action: action }),
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
          requiresApproval: false 
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
                    requiresApproval: false 
                  };
                  return copy;
                });
              }
            } catch (e) {}
          }
        }
      }
      loadThreads();
    } catch (err) {
      setMessages(prev => {
        const copy = [...prev];
        copy[idx] = { 
          role: 'assistant', 
          content: 'I encountered an error processing your approval. Please try again.', 
          error: true,
          requiresApproval: false
        };
        return copy;
      });
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    const text = inputText.trim();
    if (!text || isStreaming) return;

    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setInputText('');
    setIsStreaming(true);

    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      const response = await fetch(`${baseUrl}/chatbot/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ query: text, thread_id: currentThreadId, stream: true }),
      });

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
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Issue connecting. Try again.', error: true }]);
    } finally {
      setIsStreaming(false);
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
                  {[...threads].reverse().map(tid => (
                    <button
                      key={tid}
                      onClick={() => { setCurrentThreadId(tid); setShowSessions(false); }}
                      className={`w-full text-left p-4 rounded-xl transition-all border duration-300 ${
                        currentThreadId === tid ? 'bg-primary text-white border-primary shadow-lg shadow-primary/20' : 'hover:bg-white/5 border-transparent text-gray-400'
                      }`}
                    >
                      <div className="text-[10px] uppercase font-bold opacity-50 mb-1 tracking-widest leading-none">Session ID</div>
                      <div className="truncate text-[10px] font-mono">{tid}</div>
                    </button>
                  ))}
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
