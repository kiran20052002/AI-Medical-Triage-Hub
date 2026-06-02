import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const AdminLoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append('email', email);
      formData.append('password', password);

      const res = await api.post('/auth/admin-login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      
      login(res.data.user);
      navigate('/dashboard/admin');
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid admin credentials');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-base-200 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-[120px] -z-0"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-[120px] -z-0"></div>

      <div className="card w-full max-w-sm glass-card z-10 transition-all duration-300 hover:shadow-primary/20">
        <form onSubmit={handleSubmit} className="card-body">
          <div className="flex flex-col items-center mb-6">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-primary to-indigo-600 flex items-center justify-center mb-4 shadow-lg shadow-primary/30 transform rotate-3 hover:rotate-6 transition-transform">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="white" className="w-8 h-8">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
              </svg>
            </div>
            <h2 className="text-3xl font-bold tracking-wide text-white">Admin Access</h2>
            <p className="text-gray-400 text-sm mt-1 uppercase font-black tracking-widest">System Management Console</p>
          </div>

          {error && (
            <div className="alert alert-error shadow-lg mb-4 bg-red-500/10 border-red-500/20 text-red-200 py-3 rounded-xl border">
              <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-[10px] font-black uppercase tracking-widest">{error}</span>
            </div>
          )}

          <div className="form-control w-full space-y-4">
            <div className="group">
              <label className="label pt-0 pl-0">
                <span className="label-text text-gray-500 text-[10px] uppercase tracking-widest font-black">Email</span>
              </label>
              <div className="relative transition-all duration-300 group-focus-within:scale-[1.01]">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@medicalhub.com"
                  className="input input-bordered w-full bg-base-100/10 border-white/10 focus:border-primary focus:bg-base-100/20 focus:outline-none transition-all pl-10 rounded-xl text-white"
                  required
                />
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 absolute left-3 top-3.5 text-primary group-focus-within:text-white transition-colors">
                  <path d="M3 4a2 2 0 00-2 2v1.161l8.441 4.221a1.25 1.25 0 001.118 0L19 7.162V6a2 2 0 00-2-2H3z" />
                  <path d="M19 8.839l-7.77 3.885a2.75 2.75 0 01-2.46 0L1 8.839V14a2 2 0 002 2h12a2 2 0 002-2V8.839z" />
                </svg>
              </div>
            </div>

            <div className="group">
              <label className="label pt-0 pl-0">
                <span className="label-text text-gray-500 text-[10px] uppercase tracking-widest font-black">Password</span>
              </label>
              <div className="relative transition-all duration-300 group-focus-within:scale-[1.01]">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input input-bordered w-full bg-base-100/10 border-white/10 focus:border-primary focus:bg-base-100/20 focus:outline-none transition-all pl-10 rounded-xl text-white"
                  required
                />
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 absolute left-3 top-3.5 text-primary group-focus-within:text-white transition-colors">
                  <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
                </svg>
              </div>
            </div>
          </div>

          <div className="form-control mt-8">
            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary w-full shadow-lg shadow-primary/20 border-none bg-gradient-to-r from-primary to-indigo-600 hover:from-primary hover:to-indigo-500 hover:shadow-primary/30 hover:scale-[1.02] transition-all duration-300 rounded-xl text-white font-bold tracking-widest uppercase disabled:opacity-50"
            >
              {isLoading ? 'Authenticating...' : 'Authenticate'}
            </button>
          </div>

          <div className="divider opacity-10 text-[10px] font-black uppercase tracking-[0.3em] my-6">Medical Triage Hub System</div>

          <div className="text-center">
            <Link to="/auth/login" className="link link-hover text-primary text-sm hover:text-white transition-colors uppercase font-black tracking-widest">← Back to Login</Link>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AdminLoginPage;
