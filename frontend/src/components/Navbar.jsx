const Navbar = ({ activeSection, setActiveSection, isDarkMode, toggleTheme, pendingShipments = 0 }) => {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-slate-950/75 backdrop-blur-2xl" style={{boxShadow:'0 1px 0 rgba(255,255,255,0.04),0 4px 32px rgba(0,0,0,0.4)'}}>
      <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/30"
               style={{background:'linear-gradient(135deg,#6366f1,#a78bfa)'}}>
            <i className="fas fa-layer-group text-white text-lg"></i>
          </div>
          <span className="text-2xl font-extrabold tracking-tight">
            <span className="bg-clip-text text-transparent" style={{backgroundImage:'linear-gradient(90deg,#fff,#94a3b8)'}}>INVENTORY</span><span className="text-indigo-400">.</span>
          </span>
        </div>

        <div className="hidden md:flex items-center gap-8">
          {[
            { key: 'home',      label: 'Home' },
            { key: 'inventory', label: 'Inventory' },
            { key: 'bom',       label: 'BOM' },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveSection(key)}
              className={`font-semibold transition-all hover:text-indigo-400 ${
                activeSection === key ? 'nav-active' : 'text-slate-400'
              }`}
            >
              {label}
            </button>
          ))}

          {/* Shipments tab with pending badge */}
          <button
            onClick={() => setActiveSection('shipments')}
            className={`relative font-semibold transition-all hover:text-indigo-400 ${
              activeSection === 'shipments' ? 'nav-active' : 'text-slate-400'
            }`}
          >
            Shipments
            {pendingShipments > 0 && (
              <span className="absolute -top-2 -right-4 min-w-[18px] h-[18px] px-1 rounded-full
                bg-amber-500 text-slate-900 text-[10px] font-bold flex items-center justify-center">
                {pendingShipments > 9 ? '9+' : pendingShipments}
              </span>
            )}
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