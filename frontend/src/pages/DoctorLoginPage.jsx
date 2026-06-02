import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const DoctorLoginPage = () => {
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

      const res = await api.post('/auth/doctor-login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      
      login(res.data.user);
      navigate('/dashboard/doctor');
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid doctor credentials');
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
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3" />
              </svg>
            </div>
            <h2 className="text-3xl font-bold tracking-wide text-white">Doctor Portal</h2>
            <p className="text-gray-400 text-sm mt-1 uppercase font-black tracking-widest">Medical Staff Access</p>
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
                  placeholder="doctor@hospital.com"
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
          </div>

          <div className="form-control mt-8">
            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary w-full shadow-lg shadow-primary/20 border-none bg-gradient-to-r from-primary to-indigo-600 hover:from-primary hover:to-indigo-500 hover:shadow-primary/30 hover:scale-[1.02] transition-all duration-300 rounded-xl text-white font-bold tracking-widest uppercase disabled:opacity-50"
            >
              {isLoading ? 'Secure Login...' : 'Secure Login'}
            </button>
          </div>

          <div className="divider opacity-10 text-[10px] font-black uppercase tracking-[0.3em] my-6">Medical Triage Hub</div>

          <div className="text-center">
            <Link to="/auth/login" className="text-primary text-sm hover:text-white hover:underline transition-colors uppercase font-black tracking-widest">Not a Doctor? Patient Login</Link>
          </div>
        </form>
      </div>
    </div>
  );
};

export default DoctorLoginPage;
