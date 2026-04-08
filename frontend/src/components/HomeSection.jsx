import React from 'react';

const HomeSection = ({ totalItems, setActiveSection }) => {
  return (
    <section className="animate-in">
      <div className="grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <span className="px-4 py-2 rounded-full bg-indigo-500/10 text-indigo-400 text-sm font-bold border border-indigo-500/20 mb-6 inline-block">
            Database Integrated
          </span>
          <h1 className="text-6xl lg:text-7xl font-extrabold mb-6 leading-[1.1]">
            Control your <br />
            <span className="text-indigo-500">Stock</span> like never <br /> before.
          </h1>
          <p className="text-xl text-slate-400 mb-10 leading-relaxed max-w-md">
            The intelligent interface for modern inventory management. High-speed tracking with professional analytics.
          </p>
          <div className="flex gap-4">
            <button
              onClick={() => setActiveSection('inventory')}
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-4 rounded-2xl font-bold shadow-xl shadow-indigo-600/20 transition-all flex items-center gap-3"
            >
              View Ledger <i className="fas fa-chevron-right text-sm"></i>
            </button>
          </div>
        </div>

        <div className="relative">
          <div className="absolute -inset-4 bg-indigo-500/20 blur-3xl rounded-full"></div>
          <div className="glass rounded-[2.5rem] p-8 relative border-white/10">
            <div className="flex items-center justify-between mb-8">
              <h3 className="text-lg font-bold">System Status</h3>
              <span className="flex items-center gap-2 text-emerald-400 text-sm font-bold">
                <span className="w-2 h-2 bg-emerald-500 rounded-full animate-ping"></span> Live
              </span>
            </div>
            <div className="space-y-6">
              <div className="p-4 rounded-2xl bg-white/5 flex justify-between items-center">
                <span className="text-slate-400">Total Components</span>
                <span className="text-xl font-bold">{totalItems.toLocaleString()}</span>
              </div>
              <div className="p-4 rounded-2xl bg-white/5 flex justify-between items-center">
                <span className="text-slate-400">Database Connection</span>
                <span className="text-sm font-bold text-emerald-400 px-3 py-1 bg-emerald-500/10 rounded-full">
                  Ready
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HomeSection;