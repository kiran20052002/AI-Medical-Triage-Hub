import React, { useState, useEffect, useRef } from 'react';
import api from '../services/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const AIChatbotPage = () => {
  const [threads, setThreads] = useState([]);
  const [currentThreadId, setCurrentThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadThreads();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadThreads = async () => {
    try {
      const res = await api.get('/chatbot/threads');
      setThreads(res.data.threads || []);
    } catch (e) {
      console.error('Failed to load threads');
    }
  };

  const selectThread = async (tid) => {
    setCurrentThreadId(tid);
    setIsLoadingHistory(true);
    setMessages([]);
    try {
      const res = await api.get(`/chatbot/history/${encodeURIComponent(tid)}`);
      setMessages(res.data.history || []);
    } catch (e) {
      console.error('Failed to load history');
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const startNewChat = () => {
    setCurrentThreadId(`chat-${Math.random().toString(36).substring(2, 11)}`);
    setMessages([]);
  };

  const handleDeleteThread = async (e, tid) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this chat session permanently?')) return;
    
    try {
      await api.delete(`/chatbot/thread/${encodeURIComponent(tid)}`);
      if (currentThreadId === tid) {
        startNewChat();
      }
      loadThreads();
    } catch (e) {
      console.error('Failed to delete thread');
    }
  };

  const handleApproveAction = async (idx, action, tid) => {
    // Disable buttons to prevent double click
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

      // Update message status to streaming
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
    if (!text) return;

    let tid = currentThreadId;
    if (!tid) {
      tid = `chat-${Math.random().toString(36).substring(2, 11)}`;
      setCurrentThreadId(tid);
    }

    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setInputText('');

    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      const response = await fetch(`${baseUrl}/chatbot/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text, thread_id: tid }),
        credentials: 'include',
      });

      if (!response.ok) throw new Error('Query failed');

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
      loadThreads();
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'I encountered an error. Please try again.', error: true }]);
    }
  };

  return (
    <div className="h-screen flex animate-in fade-in duration-700 overflow-hidden">
      {/* Sidebar - Threads */}
      <div className="w-80 flex flex-col bg-base-300/80 backdrop-blur-xl border-r border-white/5 overflow-hidden">
        <header className="p-6 border-b border-white/5 flex items-center justify-between bg-white/5">
          <h2 className="text-xl font-bold text-white flex items-center gap-2 tracking-tight">
             <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-5 h-5 text-primary">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            <span>History</span>
          </h2>
          <button 
            onClick={startNewChat}
            className="btn btn-primary btn-square btn-sm rounded-lg shadow-lg shadow-primary/20"
          >
             <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-4 h-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
          </button>
        </header>
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {threads.length === 0 ? (
            <p className="text-center text-gray-500 py-10 text-[10px] font-black uppercase tracking-widest italic">No recent sessions</p>
          ) : (
            [...threads].reverse().map(tid => (
              <button
                key={tid}
                onClick={() => selectThread(tid)}
                className={`w-full text-left p-4 rounded-xl transition-all border duration-300 group flex items-center justify-between ${
                  currentThreadId === tid 
                    ? 'bg-primary text-white border-primary shadow-lg shadow-primary/20' 
                    : 'hover:bg-white/5 border-transparent text-gray-400'
                }`}
              >
                <div className="flex items-center space-x-3 truncate">
                  <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${currentThreadId === tid ? 'bg-white' : 'bg-gray-700'}`}></div>
                  <span className="truncate text-[10px] font-bold uppercase tracking-widest">{tid}</span>
                </div>
                <div 
                  onClick={(e) => handleDeleteThread(e, tid)}
                  className={`opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500 rounded-md transition-all ${currentThreadId === tid ? 'text-white' : 'text-gray-500'}`}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-3 h-3">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                  </svg>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-base-100/50 backdrop-blur-xl shadow-2xl overflow-hidden relative">
        <header className="p-6 border-b border-white/5 flex items-center justify-between bg-base-300/50">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-primary to-indigo-600 flex items-center justify-center text-white shadow-xl shadow-primary/20">
               <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-7 h-7">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
                </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight leading-none uppercase">Health Assistant</h1>
              <div className="flex items-center gap-1.5 mt-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-[10px] text-gray-500 font-black uppercase tracking-widest">Medical Flow</span>
              </div>
            </div>
          </div>
          {currentThreadId && <div className="text-[10px] font-mono text-gray-600 uppercase tracking-tighter">SESSION: {currentThreadId}</div>}
        </header>

        <div className="flex-1 overflow-y-auto p-8 space-y-6">
          {messages.length === 0 && !isLoadingHistory ? (
            <div className="h-full flex flex-col items-center justify-center text-center opacity-20 grayscale-0 pointer-events-none">
                <div className="w-24 h-24 bg-white/5 rounded-full flex items-center justify-center mb-6">
                     <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="gray" className="w-12 h-12">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
                     </svg>
                </div>
              <h2 className="text-3xl font-bold text-white uppercase tracking-tighter">Virtual Assistant</h2>
              <p className="text-gray-400 mt-2 max-w-sm text-sm font-medium">Describe your health concern. I'll assist with a preliminary assessment and system routing.</p>
            </div>
          ) : isLoadingHistory ? (
            <div className="h-full flex items-center justify-center">
               <span className="loading loading-spinner loading-md text-primary"></span>
            </div>
          ) : (
            <div className="space-y-6 max-w-4xl mx-auto">
              {messages.map((msg, idx) => (
                <div key={idx} className={`chat ${msg.role === 'user' ? 'chat-end' : 'chat-start'} animate-in slide-in-from-bottom-2 duration-500`}>
                    <div className="chat-header text-[10px] font-black uppercase tracking-tighter text-gray-500 mb-1">
                      {msg.role === 'user' ? 'Patient' : 'AI Assistant'}
                    </div>
                    {msg.requiresApproval ? (
                      <div className="chat-bubble bg-base-200 border border-warning/20 rounded-2xl p-6 max-w-md shadow-xl">
                        <div className="flex items-center gap-3 text-warning mb-3">
                          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-6 h-6">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          <h3 className="font-bold text-sm uppercase tracking-wider text-white">Ticket Approval Required</h3>
                        </div>
                        <p className="text-xs text-gray-400 mb-4">The assistant wants to create a support ticket with these details:</p>
                        <div className="bg-base-300/50 rounded-xl p-4 border border-white/5 space-y-3 mb-5">
                          <div>
                            <span className="text-[10px] font-black uppercase tracking-widest text-gray-500">Title</span>
                            <p className="text-sm font-semibold text-white mt-0.5">{msg.ticketDetails?.title || 'No Title'}</p>
                          </div>
                          <div>
                            <span className="text-[10px] font-black uppercase tracking-widest text-gray-500">Description</span>
                            <p className="text-xs font-medium text-gray-300 mt-1 leading-relaxed whitespace-pre-wrap">{msg.ticketDetails?.description || 'No Description'}</p>
                          </div>
                        </div>
                        <div className="flex gap-3">
                          <button
                            disabled={msg.approvalLoading}
                            onClick={() => handleApproveAction(idx, 'approve', currentThreadId)}
                            className="btn btn-primary btn-sm flex-1 font-bold rounded-xl uppercase tracking-wider shadow-lg shadow-primary/20"
                          >
                            {msg.approvalLoading ? <span className="loading loading-spinner loading-xs"></span> : 'Approve'}
                          </button>
                          <button
                            disabled={msg.approvalLoading}
                            onClick={() => handleApproveAction(idx, 'reject', currentThreadId)}
                            className="btn btn-ghost btn-sm flex-1 font-bold rounded-xl border border-white/10 uppercase tracking-wider hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/20"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className={`chat-bubble whitespace-pre-wrap text-sm font-medium leading-relaxed max-w-[90%] md:max-w-2xl ${
                        msg.role === 'user' 
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
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <footer className="p-4 bg-base-300/50 border-t border-white/5 backdrop-blur-md">
          <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto flex gap-4 items-center">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Describe your health concern..."
              className="input input-bordered flex-grow bg-base-100 border-white/10 focus:border-primary transition-all rounded-xl h-14 text-lg"
            />
            <button 
              disabled={!inputText.trim()}
              className="btn btn-primary h-14 px-8 rounded-xl font-bold uppercase tracking-widest shadow-lg shadow-primary/20"
            >
              <span>Analyze</span>
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-5 h-5 ml-2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
              </svg>
            </button>
          </form>
        </footer>
      </div>
    </div>
  );
};

export default AIChatbotPage;