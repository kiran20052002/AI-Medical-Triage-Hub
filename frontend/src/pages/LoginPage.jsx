import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const LoginPage = () => {
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

      const res = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      
      login(res.data.user);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid email or password');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-base-200 relative overflow-hidden">
      {/* Background Decorative Element */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-[120px] -z-0"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-[120px] -z-0"></div>

      <div className="card w-full max-w-sm glass-card z-10 transition-all duration-300 hover:shadow-indigo-900/20">
        <form onSubmit={handleSubmit} className="card-body">
          <div className="flex flex-col items-center mb-6">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-[#6366f1] to-[#818cf8] flex items-center justify-center mb-4 shadow-lg shadow-indigo-500/30 transform -rotate-3 hover:rotate-0 transition-transform">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="white" className="w-8 h-8">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
              </svg>
            </div>
            <h2 className="text-3xl font-bold tracking-wide text-white">Patient Portal</h2>
            <p className="text-indigo-200/60 text-sm mt-1">Access Your Health Dashboard</p>
          </div>

          {error && (
            <div className="alert alert-error shadow-lg mb-4 bg-red-500/20 border-red-500/20 text-red-200 py-3 rounded-xl border">
              <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm font-medium">{error}</span>
            </div>
          )}

          <div className="form-control w-full space-y-4">
            <div className="group">
              <label className="label pt-0 pl-0">
                <span className="label-text text-indigo-300/80 text-xs uppercase tracking-wider font-semibold">Email</span>
              </label>
              <div className="relative transition-all duration-300 group-focus-within:scale-[1.01]">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="patient@email.com"
                  className="input input-bordered w-full bg-base-100/10 border-white/10 focus:border-indigo-500 focus:bg-base-100/20 focus:outline-none transition-all pl-10 rounded-xl text-white"
                  required
                />
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 absolute left-3 top-3.5 text-indigo-400 group-focus-within:text-violet-400 transition-colors">
                  <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                  <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
                </svg>
              </div>
            </div>

            <div className="group">
              <label className="label pt-0 pl-0">
                <span className="label-text text-indigo-300/80 text-xs uppercase tracking-wider font-semibold">Password</span>
              </label>
              <div className="relative transition-all duration-300 group-focus-within:scale-[1.01]">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input input-bordered w-full bg-base-100/10 border-white/10 focus:border-indigo-500 focus:bg-base-100/20 focus:outline-none transition-all pl-10 rounded-xl text-white"
                  required
                />
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 absolute left-3 top-3.5 text-indigo-400 group-focus-within:text-violet-400 transition-colors">
                  <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
                </svg>
              </div>
            </div>
          </div>

          <div className="form-control mt-8">
            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary w-full shadow-lg shadow-indigo-900/40 border-none bg-[#6366f1] hover:bg-[#4f46e5] hover:shadow-indigo-500/30 hover:scale-[1.02] transition-all duration-300 rounded-xl text-white font-bold tracking-wide disabled:bg-indigo-400"
            >
              {isLoading ? 'Processing...' : 'Login'}
            </button>
          </div>

          <div className="divider before:bg-indigo-900/50 after:bg-indigo-900/50 text-indigo-500/50 text-xs">New to Medical Hub?</div>

          <Link
            to="/auth/signup"
            className="btn btn-outline border-indigo-500/30 text-indigo-300 hover:bg-indigo-600/20 hover:border-indigo-400 w-full rounded-xl group relative overflow-hidden"
          >
            <span className="relative z-10">Create Account</span>
          </Link>

          <div className="mt-4 flex flex-col gap-2 text-center">
            <Link to="/auth/doctor-login" className="text-indigo-400 text-sm hover:text-violet-300 hover:underline">Doctor Login</Link>
            <Link to="/auth/admin-login" className="text-gray-500 text-xs hover:text-gray-300 hover:underline">Admin Login</Link>
          </div>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
