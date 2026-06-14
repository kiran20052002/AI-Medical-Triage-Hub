import React, { useState, useEffect, useRef } from 'react';
import api from '../services/api';

const AIChatbotPage = () => {
  const [threads, setThreads] = useState([]);
  const [currentThreadId, setCurrentThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const messagesEndRef = useRef(null);

  const { user } = api.context || {}; // Assuming we might need to get user from context if not already available
  // However, I see 'api' is imported. Checking for useAuth context would be better.
  // Actually, I'll use the existing pattern if possible or rely on the navigate.
  
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
    if (isStreaming) return;
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
    if (isStreaming) return;
    setCurrentThreadId(`chat-${Math.random().toString(36).substring(2, 11)}`);
    setMessages([]);
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    const text = inputText.trim();
    if (!text || isStreaming) return;

    let tid = currentThreadId;
    if (!tid) {
      tid = `chat-${Math.random().toString(36).substring(2, 11)}`;
      setCurrentThreadId(tid);
    }

    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setInputText('');
    setIsStreaming(true);

    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      const response = await fetch(`${baseUrl}/chatbot/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text, thread_id: tid, stream: true }),
      });

      if (!response.ok) throw new Error('Query failed');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = '';

      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

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
              if (data.content) {
                assistantMessage += data.content;
                setMessages(prev => {
                  const last = prev[prev.length - 1];
                  const others = prev.slice(0, -1);
                  return [...others, { ...last, content: assistantMessage }];
                });
              }
            } catch (e) {}
          }
        }
      }
      loadThreads();
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'I encountered an error. Please try again.', error: true }]);
    } finally {
      setIsStreaming(false);
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
                className={`w-full text-left p-4 rounded-xl transition-all border duration-300 ${
                  currentThreadId === tid 
                    ? 'bg-primary text-white border-primary shadow-lg shadow-primary/20' 
                    : 'hover:bg-white/5 border-transparent text-gray-400'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className={`w-1.5 h-1.5 rounded-full ${currentThreadId === tid ? 'bg-white' : 'bg-gray-700'}`}></div>
                  <span className="truncate text-[10px] font-bold uppercase tracking-widest">{tid}</span>
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
                <span className="text-[10px] text-gray-500 font-black uppercase tracking-widest">Medical Triage Flow</span>
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
              <h2 className="text-3xl font-bold text-white uppercase tracking-tighter">Virtual Triage</h2>
              <p className="text-gray-400 mt-2 max-w-sm text-sm font-medium">Describe your health concern. I'll assist with a preliminary assessment and system triage.</p>
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
                    <div className={`chat-bubble text-sm font-medium leading-relaxed max-w-[90%] md:max-w-2xl ${
                      msg.role === 'user' 
                        ? 'bg-primary text-white rounded-2xl shadow-lg shadow-primary/10' 
                        : msg.error 
                          ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                          : 'bg-base-200 text-gray-300 border border-white/5 rounded-2xl'
                    }`}>
                        {msg.content || (isStreaming && msg.role === 'assistant' && idx === messages.length - 1 ? (
                            <div className="flex space-x-1.5 py-1.5">
                                <span className="loading loading-dots loading-xs"></span>
                            </div>
                        ) : null)}
                    </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <footer className="p-4 bg-base-300/50 border-t border-white/5 backdrop-blur-md">
          <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto flex gap-4 items-center">
            <input
              disabled={isStreaming}
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Describe your health concern..."
              className="input input-bordered flex-grow bg-base-100 border-white/10 focus:border-primary transition-all rounded-xl h-14 text-lg"
            />
            <button 
              disabled={isStreaming || !inputText.trim()}
              className="btn btn-primary h-14 px-8 rounded-xl font-bold uppercase tracking-widest shadow-lg shadow-primary/20"
            >
              <span>{isStreaming ? 'Thinking...' : 'Analyze'}</span>
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
