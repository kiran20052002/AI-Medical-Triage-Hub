import React, { useEffect, useState, useRef } from 'react';
import { StreamChat } from 'stream-chat';
import api from '../services/api';

const TriageChatPage = () => {
  const [chatClient, setChatClient] = useState(null);
  const [channels, setChannels] = useState([]);
  const [activeChannel, setActiveChannel] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    initChat();
    return () => {
      if (chatClient) chatClient.disconnectUser();
    };
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const initChat = async () => {
    try {
      const tokenRes = await api.get('/chat/token');
      const { token, userId, stream_api_key } = tokenRes.data;

      const client = StreamChat.getInstance(stream_api_key);
      await client.connectUser({ id: userId, name: userId }, token);

      const filter = { type: 'messaging', members: { $in: [userId] } };
      const sort = { last_message_at: -1 };
      const chatChannels = await client.queryChannels(filter, sort, {
        watch: true,
        state: true,
      });

      setChatClient(client);
      setChannels(chatChannels);
    } catch (err) {
      console.error('Chat init error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const selectChannel = async (channel) => {
    await channel.watch();
    setActiveChannel(channel);
    setMessages(channel.state.messages);
    
    channel.on('message.new', event => {
      setMessages(prev => [...prev, event.message]);
    });
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputText.trim() || !activeChannel) return;

    try {
      await activeChannel.sendMessage({ text: inputText });
      setInputText('');
    } catch (err) {
      console.error('Send error:', err);
    }
  };

  if (isLoading) return (
    <div className="h-[calc(100vh-12rem)] flex items-center justify-center bg-base-200 rounded-3xl border border-white/5 shadow-2xl">
      <span className="loading loading-spinner loading-lg text-primary"></span>
    </div>
  );

  return (
    <div className="h-screen flex bg-base-300/50 backdrop-blur-xl overflow-hidden animate-in fade-in duration-700">
      {/* Sidebar */}
      <div className="w-80 border-r border-white/5 flex flex-col bg-base-300">
        <header className="p-6 border-b border-white/5">
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
             <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            <span>Doctor Consults</span>
          </h2>
        </header>
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {channels.length === 0 ? (
            <p className="text-center text-gray-500 py-10 text-xs font-bold uppercase tracking-widest italic">No active medical chats</p>
          ) : (
            channels.map(channel => (
              <button
                key={channel.id}
                onClick={() => selectChannel(channel)}
                className={`w-full text-left p-4 rounded-xl transition-all duration-300 ${
                  activeChannel?.id === channel.id 
                    ? 'bg-primary text-white shadow-lg shadow-primary/20 scale-[1.02]' 
                    : 'hover:bg-white/5 text-gray-400'
                }`}
              >
                <div className="font-bold text-xs truncate uppercase tracking-widest">
                  {channel.data?.name || 'Medical Case'}
                </div>
                <div className={`text-[10px] mt-1 truncate font-medium ${activeChannel?.id === channel.id ? 'text-white/80' : 'text-gray-500'}`}>
                  {channel.state.messages[channel.state.messages.length - 1]?.text || 'Start conversation...'}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-base-100/30">
        {activeChannel ? (
          <>
            <header className="p-6 border-b border-white/5 flex items-center justify-between bg-base-300/50">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-primary to-indigo-600 flex items-center justify-center font-bold text-white">
                  { (activeChannel.data?.name || 'M')[0] }
                </div>
                <div>
                  <h3 className="font-bold text-white leading-none tracking-tight">{activeChannel.data?.name || 'Triage Session'}</h3>
                  <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mt-1.5 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                    Secure Encryption Active
                  </p>
                </div>
              </div>
            </header>
            
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((msg, idx) => {
                const isMe = msg.user.id === chatClient?.userID;
                return (
                  <div key={idx} className={`chat ${isMe ? 'chat-end' : 'chat-start'}`}>
                    <div className="chat-header text-[10px] font-black uppercase tracking-tighter text-gray-500 mb-1">
                      {isMe ? 'You' : (msg.user.name || msg.user.id)}
                    </div>
                    <div className={`chat-bubble text-sm font-medium leading-relaxed ${
                      isMe 
                        ? 'bg-primary text-white rounded-2xl shadow-lg shadow-primary/10' 
                        : 'bg-base-200 text-gray-300 border border-white/5 rounded-2xl'
                    }`}>
                      {msg.text}
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            <footer className="p-4 bg-base-300/50 border-t border-white/5">
              <form onSubmit={handleSendMessage} className="flex space-x-3 max-w-5xl mx-auto items-center">
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="Type your medical query or response..."
                  className="input input-bordered flex-grow bg-base-100 border-white/10 focus:border-primary transition-all rounded-xl h-14"
                />
                <button className="btn btn-primary h-14 w-14 rounded-xl shadow-lg shadow-primary/20">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-6 h-6">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                    </svg>
                </button>
              </form>
            </footer>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-10">
            <div className="w-24 h-24 bg-white/5 rounded-full flex items-center justify-center mb-6 animate-bounce">
               <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="gray" className="w-12 h-12">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.451-.066-.933-.408-1.248C3.113 16.36 2.25 14.28 2.25 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
                </svg>
            </div>
            <h3 className="text-2xl font-bold text-white tracking-tight">Select a case to begin triage</h3>
            <p className="text-gray-500 mt-2 max-w-sm text-sm font-medium">Secure, direct communication channel between you and assigned medical professionals.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default TriageChatPage;
