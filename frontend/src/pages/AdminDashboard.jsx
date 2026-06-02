import React, { useEffect, useState } from 'react';
import api from '../services/api';

const AdminDashboard = () => {
  const [data, setData] = useState({
    total_patients: 0,
    total_doctors: 0,
    total_tickets: 0,
    all_users: [],
    reports: []
  });
  const [activeTab, setActiveTab] = useState('users');
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const response = await api.get('/admin/dashboard');
      setData(response.data);
    } catch (err) {
      console.error('Failed to load admin data');
    } finally {
      setIsLoading(false);
    }
  };

  const filteredUsers = data.all_users.filter(u => 
    u.email.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="bg-base-200 min-h-screen pb-20">
      <div className="max-w-6xl mx-auto pt-8 px-4 animate-in fade-in duration-700">
        <h2 className="text-3xl font-bold text-white mb-8 tracking-tight">System Oversight</h2>
        
        {/* Stats Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          <div className="card bg-base-100/50 backdrop-blur-xl border border-white/5 shadow-xl">
            <div className="card-body p-6">
                <div className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 mb-2">Total Patients</div>
                <div className="text-4xl font-bold text-primary">{data.total_patients}</div>
            </div>
          </div>
          <div className="card bg-base-100/50 backdrop-blur-xl border border-white/5 shadow-xl">
            <div className="card-body p-6">
                <div className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 mb-2">Total Doctors</div>
                <div className="text-4xl font-bold text-primary">{data.total_doctors}</div>
            </div>
          </div>
          <div className="card bg-base-100/50 backdrop-blur-xl border border-white/5 shadow-xl">
            <div className="card-body p-6">
                <div className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 mb-2">Total Tickets</div>
                <div className="text-4xl font-bold text-white">{data.total_tickets}</div>
            </div>
          </div>
        </div>

        {/* Tabs Section */}
        <div role="tablist" className="tabs tabs-boxed mb-8 bg-base-300/50 border border-white/5 p-1.5 backdrop-blur-xl inline-flex">
          <button 
            role="tab" 
            className={`tab font-bold transition-all px-8 ${activeTab === 'users' ? 'tab-active !bg-primary !text-white rounded-lg shadow-lg shadow-primary/20' : 'text-gray-500 hover:text-gray-300'}`}
            onClick={() => setActiveTab('users')}
          >
            Manage Staff
          </button>
          <button 
            role="tab" 
            className={`tab font-bold transition-all px-8 ${activeTab === 'reports' ? 'tab-active !bg-primary !text-white rounded-lg shadow-lg shadow-primary/20' : 'text-gray-500 hover:text-gray-300'}`}
            onClick={() => setActiveTab('reports')}
          >
            Medical Reports
          </button>
        </div>

        {activeTab === 'users' && (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
            <div className="relative mb-8 max-w-md">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search database..."
                className="input input-bordered w-full bg-base-100 border-white/10 focus:border-primary transition-all rounded-xl h-12"
              />
            </div>

            <div className="overflow-x-auto bg-base-100/30 backdrop-blur-md rounded-2xl border border-white/5 shadow-2xl">
              <table className="table w-full">
                <thead>
                  <tr className="text-gray-500 uppercase text-[10px] tracking-widest border-b border-white/5">
                    <th className="px-8 py-5">Email Address</th>
                    <th className="px-8 py-5">Assigned Role</th>
                    <th className="px-8 py-5">Clinical Specialization</th>
                  </tr>
                </thead>
                <tbody className="text-gray-300">
                  {filteredUsers.map((user) => (
                    <tr key={user.id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                      <td className="px-8 py-5 font-medium text-white">{user.email}</td>
                      <td className="px-8 py-5">
                        <span className={`badge badge-sm font-black uppercase tracking-widest py-3 px-3 h-auto ${user.role === 'doctor' ? 'badge-primary shadow-lg shadow-primary/10' : 'badge-ghost border-white/10'}`}>
                          {user.role}
                        </span>
                      </td>
                      <td className="px-8 py-5 text-[10px] font-bold uppercase tracking-widest text-gray-500">
                        {user.specialist ? user.specialist.join(', ') : <span className="opacity-30">N/A</span>}
                      </td>
                    </tr>
                  ))}
                  {filteredUsers.length === 0 && (
                    <tr>
                      <td colSpan="3" className="text-center py-16 text-gray-500 uppercase text-[10px] font-black tracking-[0.3em] italic">No records found</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'reports' && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500 max-w-4xl">
            {data.reports.length === 0 ? (
              <div className="bg-base-100/30 backdrop-blur-md p-20 text-center rounded-3xl border border-white/5 shadow-xl">
                 <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1" stroke="gray" className="w-16 h-16 mx-auto mb-4 opacity-20">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
                <p className="text-gray-500 font-black uppercase text-[10px] tracking-[0.3em]">No medical records found</p>
              </div>
            ) : (
              data.reports.map((report, idx) => (
                <div key={idx} className="collapse collapse-arrow bg-base-100/50 backdrop-blur-xl border border-white/5 shadow-lg rounded-2xl overflow-hidden">
                  <input type="checkbox" /> 
                  <div className="collapse-title text-lg font-bold text-white flex justify-between items-center py-6 px-8">
                    <span>Clinical Report #{data.reports.length - idx}</span>
                    <span className="text-[10px] text-gray-500 font-black uppercase tracking-widest">{new Date(report.createdAt || report.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="collapse-content border-t border-white/5 p-8 bg-base-200/30">
                    <div className="prose prose-sm max-w-none text-gray-400">
                      <div className="flex items-center gap-2 mb-4">
                           <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
                           <h4 className="text-primary font-bold uppercase text-[10px] tracking-widest my-0">Medical Diagnostic Plan</h4>
                      </div>
                      <p className="leading-relaxed whitespace-pre-wrap text-gray-300 font-medium">{report.content?.plan}</p>
                      
                      <div className="mt-10 pt-6 border-t border-white/5 grid grid-cols-2 gap-4">
                        <div className="flex flex-col gap-1">
                            <span className="text-[8px] uppercase font-black text-gray-600 tracking-widest">Ticket Correlation</span>
                            <span className="text-[10px] font-mono text-gray-400">{report.ticket_id}</span>
                        </div>
                        <div className="flex flex-col gap-1">
                            <span className="text-[8px] uppercase font-black text-gray-600 tracking-widest">Authenticated Clinician</span>
                            <span className="text-[10px] font-mono text-gray-400">{report.content?.doctor_id}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;
