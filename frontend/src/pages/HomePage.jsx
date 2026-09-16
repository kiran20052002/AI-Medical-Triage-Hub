import React from 'react';
import { Link } from 'react-router-dom';

const HomePage = () => (
  <div className="hero min-h-screen bg-base-200">
    <div className="hero-content text-center">
      <div className="max-w-2xl px-4">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 mb-8">
           <span className="w-2 h-2 rounded-full bg-green-500"></span>
           <span className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-400">Next-Gen Medical Ecosystem</span>
        </div>

        <h1 className="mb-6 text-6xl md:text-7xl font-bold text-white tracking-tighter leading-none">
          Medical <span className="text-primary">Hub</span>
        </h1>

        <p className="mb-10 text-gray-400 text-lg md:text-xl font-medium leading-relaxed max-w-lg mx-auto">
          AI-Powered Smart System for streamlined patient care and instant clinical assessments.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <Link to="/auth/login" className="btn btn-primary btn-lg rounded-2xl px-10">
            Patient Portal
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-5 h-5 ml-2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
          </Link>
          <Link to="/auth/doctor-login" className="btn btn-ghost btn-lg rounded-2xl px-10 border border-white/10 text-gray-300">
            Doctor Access
          </Link>
        </div>

        <div className="mt-16 pt-10 border-t border-white/5">
          <Link to="/auth/admin-login" className="text-gray-600 text-[10px] hover:text-primary transition-colors uppercase font-black tracking-[0.3em]">
            System Administration
          </Link>
        </div>
      </div>
    </div>
  </div>
);

export default HomePage;
