import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../services/api';

const SignupPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('patient');
  const [specialist, setSpecialist] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append('email', email);
      formData.append('password', password);
      formData.append('role', role);
      if (role === 'doctor') {
        formData.append('specialist', specialist);
      }

      await api.post('/auth/signup', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      
      navigate('/auth/login');
    } catch (err) {
      setError(err.response?.data?.error || 'Registration failed. Try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-base-200 relative overflow-hidden">
      {/* Background Decorative Element */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-[120px] -z-0"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-[120px] -z-0"></div>

      <div className="card w-full max-w-sm glass-card z-10 transition-all duration-300 hover:shadow-primary/20">
        <form onSubmit={handleSubmit} className="card-body">
          <div className="flex flex-col items-center mb-6">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-primary to-indigo-600 flex items-center justify-center mb-4 shadow-lg shadow-primary/30 transform hover:scale-105 transition-transform">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="white" className="w-8 h-8">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zM4 19.235v-.11a6.375 6.375 0 0112.75 0v.109A12.318 12.318 0 0110.374 21c-2.331 0-4.512-.645-6.374-1.766z" />
              </svg>
            </div>
            <h2 className="text-3xl font-bold tracking-wide text-white">Join Us</h2>
            <p className="text-gray-400 text-sm mt-1 uppercase font-black tracking-widest">Create Your New Account</p>
          </div>

          {error && (
            <div className="alert alert-error shadow-lg mb-4 bg-red-500/10 border-red-500/20 text-red-200 py-3 rounded-xl border">
              <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-xs font-bold uppercase tracking-widest">{error}</span>
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
                  placeholder="you@example.com"
                  className="input input-bordered w-full bg-base-100/10 border-white/10 focus:border-primary focus:bg-base-100/20 focus:outline-none transition-all pl-10 rounded-xl text-white"
                  required
                />
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 absolute left-3 top-3.5 text-primary group-focus-within:text-white transition-colors">
                  <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                  <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
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

            <div className="group">
              <label className="label pt-0 pl-0">
                <span className="label-text text-gray-500 text-[10px] uppercase tracking-widest font-black">Account Role</span>
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="select select-bordered w-full bg-base-100/10 border-white/10 focus:border-primary focus:bg-base-100/20 focus:outline-none transition-all rounded-xl text-white h-12"
              >
                <option value="patient" className="bg-base-300">Patient</option>
                <option value="doctor" className="bg-base-300">Doctor</option>
              </select>
            </div>

            {role === 'doctor' && (
              <div className="group animate-in fade-in slide-in-from-top-2 duration-300">
                <label className="label pt-0 pl-0">
                  <span className="label-text text-gray-500 text-[10px] uppercase tracking-widest font-black">Clinical Field</span>
                </label>
                <div className="relative transition-all duration-300 group-focus-within:scale-[1.01]">
                  <input
                    type="text"
                    value={specialist}
                    onChange={(e) => setSpecialist(e.target.value)}
                    placeholder="e.g. Cardiology"
                    className="input input-bordered w-full bg-base-100/10 border-white/10 focus:border-primary focus:bg-base-100/20 focus:outline-none transition-all pl-10 rounded-xl text-white"
                    required
                  />
                   <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-5 h-5 absolute left-3 top-3.5 text-primary">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3.75h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008z" />
                  </svg>
                </div>
              </div>
            )}
          </div>

          <div className="form-control mt-8">
            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary w-full shadow-lg shadow-primary/20 border-none bg-gradient-to-r from-primary to-indigo-600 hover:from-primary hover:to-indigo-500 hover:shadow-primary/30 hover:scale-[1.02] transition-all duration-300 rounded-xl text-white font-bold tracking-widest uppercase disabled:opacity-50"
            >
              {isLoading ? 'Creating Account...' : 'Get Started'}
            </button>
          </div>

          <div className="divider opacity-10 text-[10px] font-black uppercase tracking-[0.3em] my-6">OR</div>

          <Link
            to="/auth/login"
            className="btn btn-ghost border border-white/5 text-gray-400 hover:bg-white/5 hover:text-white w-full rounded-xl"
          >
            Access Existing Account
          </Link>
        </form>
      </div>
    </div>
  );
};

export default SignupPage;
