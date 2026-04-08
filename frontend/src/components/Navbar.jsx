import React from 'react';

const Navbar = ({ activeSection, setActiveSection, isDarkMode, toggleTheme }) => {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-slate-950/80 backdrop-blur-xl dark:bg-slate-950/80">
      <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <i className="fas fa-layer-group text-white text-xl"></i>
          </div>
          <span className="text-2xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400 dark:from-white dark:to-slate-400">
            INVENTORY<span className="text-indigo-500">.</span>
          </span>
        </div>

        <div className="hidden md:flex items-center gap-8">
          <button
            onClick={() => setActiveSection('home')}
            className={`font-semibold transition-all hover:text-indigo-400 ${
              activeSection === 'home' ? 'nav-active' : 'text-slate-400'
            }`}
          >
            Home
          </button>
          <button
            onClick={() => setActiveSection('inventory')}
            className={`font-semibold transition-all hover:text-indigo-400 ${
              activeSection === 'inventory' ? 'nav-active' : 'text-slate-400'
            }`}
          >
            Inventory
          </button>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={toggleTheme}
            className="w-10 h-10 rounded-full glass flex items-center justify-center hover:scale-110 transition-transform"
          >
            <i className={`fas ${isDarkMode ? 'fa-moon' : 'fa-sun'}`}></i>
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;