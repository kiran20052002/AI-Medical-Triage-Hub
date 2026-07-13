import React from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import ChatWidget from './ChatWidget';
import { useAuth } from '../context/AuthContext';

const Layout = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const getDashboardLink = () => {
    if (!user) return "/auth/login";
    if (user.role === 'admin') return "/dashboard/admin";
    if (user.role === 'doctor') return "/dashboard/doctor";
    return "/dashboard";
  };

  return (
    <div className="min-h-screen bg-base-200 flex flex-col font-sans transition-colors duration-300 text-gray-300">
      {/* Navigation - Hidden on Full-Screen Chat Routes */}
      {!['/chat', '/chatbot'].includes(location.pathname) && (
        <nav className="navbar bg-base-300/80 backdrop-blur-md sticky top-0 z-50 border-b border-white/5 px-4 md:px-8">
          <div className="flex-1">
            <Link to="/" className="flex items-center gap-3 group">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary to-indigo-600 flex items-center justify-center shadow-lg shadow-primary/20 group-hover:scale-105 transition-transform">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="white" className="w-6 h-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
              </div>
              <span className="text-xl font-bold text-white tracking-tight">Med Hub</span>
            </Link>
          </div>

          <div className="flex-none gap-2">
            {/* Desktop Menu */}
            <div className="hidden md:flex items-center gap-2">
              {user && (
                <>
                  <Link to={getDashboardLink()} className={`btn btn-ghost btn-sm rounded-lg hover:bg-white/5 ${location.pathname.includes('dashboard') ? 'bg-white/10 text-white' : ''}`}>Dashboard</Link>
                  {(user.role === 'patient' || user.role === 'doctor') && (
                    <Link to="/chatbot" className={`btn btn-ghost btn-sm rounded-lg hover:bg-white/5 ${location.pathname === '/chatbot' ? 'bg-white/10 text-white' : ''}`}>AI Assistant</Link>
                  )}
                  <div className="divider divider-horizontal mx-1"></div>
                </>
              )}
              
              {!user ? (
                <>
                  <Link to="/auth/login" className="btn btn-ghost btn-sm rounded-lg hover:bg-white/5">Login</Link>
                  <Link to="/auth/signup" className="btn btn-primary btn-sm rounded-lg px-6">Sign Up</Link>
                </>
              ) : (
                <button onClick={logout} className="btn btn-ghost btn-sm rounded-lg hover:bg-white/5 text-red-400">Logout</button>
              )}
            </div>

            {/* Mobile menu button */}
            <div className="md:hidden dropdown dropdown-end">
              <label tabIndex={0} className="btn btn-ghost btn-circle">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h7" />
                </svg>
              </label>
              <ul tabIndex={0} className="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow-2xl bg-base-300 rounded-box w-52 border border-white/5">
                {user && (
                  <>
                    <li><Link to={getDashboardLink()}>Dashboard</Link></li>
                    {(user.role === 'patient' || user.role === 'doctor') && <li><Link to="/chatbot">AI Assistant</Link></li>}
                    <div className="divider my-1"></div>
                  </>
                )}
                {!user ? (
                  <>
                    <li><Link to="/auth/login">Login</Link></li>
                    <li><Link to="/auth/signup">Sign Up</Link></li>
                  </>
                ) : (
                  <li><button onClick={logout} className="text-red-400">Logout</button></li>
                )}
              </ul>
            </div>
          </div>
        </nav>
      )}

      {/* Main Content Area */}
      <main className={`flex-grow ${['/chat', '/chatbot'].includes(location.pathname) ? 'pt-0' : 'pt-4'}`}>
        <Outlet />
      </main>

      {user && (user.role === 'doctor' || user.role === 'patient') && <ChatWidget />}

      {/* Footer - Only on Home Page */}
      {location.pathname === '/' && (
        <footer className="footer footer-center p-10 bg-base-300 text-base-content border-t border-white/5 mt-auto">
          <aside>
            <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center mb-4">
               <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
            </div>
            <p className="font-bold">
              Medical Hub <br />
              <span className="font-normal text-gray-500">Intelligent Healthcare Coordination</span>
            </p> 
            <p className="text-gray-600 text-xs">© {new Date().getFullYear()} - All rights reserved</p>
          </aside> 
        </footer>
      )}
    </div>
  );
};

export default Layout;
