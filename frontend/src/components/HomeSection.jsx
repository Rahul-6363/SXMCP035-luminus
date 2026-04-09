import { useState, useEffect } from 'react';
import { BACKEND_URL } from '../utils/constants';

const HomeSection = ({ totalItems, setActiveSection }) => {
  const [backendOk, setBackendOk] = useState(null); // null=checking, true=ok, false=down

  useEffect(() => {
    fetch(`${BACKEND_URL}/health`)
      .then(r => r.ok ? setBackendOk(true) : setBackendOk(false))
      .catch(() => setBackendOk(false));
  }, []);

  return (
    <div>
      {/* ── Existing hero — unchanged ───────────────────────── */}
      <section className="animate-in">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <span className="px-4 py-2 rounded-full bg-indigo-500/10 text-indigo-400 text-sm font-bold border border-indigo-500/20 mb-6 inline-block">
              Database Integrated
            </span>
            <h1 className="text-6xl lg:text-7xl font-extrabold mb-6 leading-[1.1]">
              Control your <br />
              <span className="grad-text">Inventory</span> like never <br /> before.
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
              <button
                onClick={() => setActiveSection('bom')}
                className="bg-slate-800 hover:bg-slate-700 text-white px-8 py-4 rounded-2xl font-bold transition-all flex items-center gap-3"
              >
                View BOMs <i className="fas fa-layer-group text-sm"></i>
              </button>
            </div>
          </div>

          <div className="relative">
            <div className="absolute -inset-4 bg-indigo-500/20 blur-3xl rounded-full"></div>
            <div className="glass rounded-[2.5rem] p-8 relative border-white/10">
              <div className="flex items-center justify-between mb-8">
                <h3 className="text-lg font-bold">System Status</h3>
                {backendOk === null && (
                  <span className="flex items-center gap-2 text-slate-400 text-sm font-bold">
                    <i className="fas fa-spinner fa-spin"></i> Checking…
                  </span>
                )}
                {backendOk === true && (
                  <span className="flex items-center gap-2 text-emerald-400 text-sm font-bold">
                    <span className="w-2 h-2 bg-emerald-500 rounded-full animate-ping"></span> Live
                  </span>
                )}
                {backendOk === false && (
                  <span className="flex items-center gap-2 text-rose-400 text-sm font-bold">
                    <span className="w-2 h-2 bg-rose-500 rounded-full"></span> Offline
                  </span>
                )}
              </div>
              <div className="space-y-4">
                <div className="p-4 rounded-2xl bg-white/5 flex justify-between items-center">
                  <span className="text-slate-400">Total Components</span>
                  <span className="text-xl font-bold">{totalItems.toLocaleString()}</span>
                </div>
                <div className="p-4 rounded-2xl bg-white/5 flex justify-between items-center">
                  <span className="text-slate-400">Backend API</span>
                  <span className={`text-sm font-bold px-3 py-1 rounded-full ${
                    backendOk === true  ? 'text-emerald-400 bg-emerald-500/10' :
                    backendOk === false ? 'text-rose-400 bg-rose-500/10' :
                                          'text-slate-400 bg-slate-700'
                  }`}>
                    {backendOk === true ? 'Connected' : backendOk === false ? 'Unreachable' : 'Checking'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── NEW: Why this MCP? ──────────────────────────────── */}
      <section className="mt-32 animate-in animate-in-delay-1">
        <div className="text-center mb-14">
          <span className="section-label">Why this MCP?</span>
          <div className="glow-divider"></div>
          <h2 className="text-4xl lg:text-5xl font-extrabold mb-4">
            Built for real <span className="grad-text">production</span> workflows
          </h2>
          <p className="text-slate-400 text-lg max-w-xl mx-auto">
            Every feature is designed to eliminate manual ERP overhead and let your team focus on building.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Card 1 */}
          <div className="feature-card animate-in animate-in-delay-1">
            <div className="icon-badge bg-indigo-500/10">
              <i className="fas fa-bolt text-indigo-400"></i>
            </div>
            <h3 className="font-bold text-white text-lg mb-2">Fast</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Single-call LLM architecture runs locally — no round-trips to external APIs, no latency.
            </p>
          </div>

          {/* Card 2 */}
          <div className="feature-card animate-in animate-in-delay-2">
            <div className="icon-badge bg-emerald-500/10">
              <i className="fas fa-database text-emerald-400"></i>
            </div>
            <h3 className="font-bold text-white text-lg mb-2">Live Data</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Queries run directly against your MySQL database in real time — always accurate, never stale.
            </p>
          </div>

          {/* Card 3 */}
          <div className="feature-card animate-in animate-in-delay-3">
            <div className="icon-badge bg-cyan-500/10">
              <i className="fas fa-robot text-cyan-400"></i>
            </div>
            <h3 className="font-bold text-white text-lg mb-2">AI-Powered</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Natural language interface — ask in plain English, receive structured ERP actions automatically.
            </p>
          </div>

          {/* Card 4 */}
          <div className="feature-card animate-in animate-in-delay-4">
            <div className="icon-badge bg-violet-500/10">
              <i className="fab fa-discord text-violet-400"></i>
            </div>
            <h3 className="font-bold text-white text-lg mb-2">Integrated</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Works on the web and in Discord — same intelligence, same tools, wherever your team works.
            </p>
          </div>
        </div>
      </section>

      {/* ── NEW: How It Works ───────────────────────────────── */}
      <section className="mt-32 animate-in animate-in-delay-2">
        <div className="text-center mb-14">
          <span className="section-label">How It Works</span>
          <div className="glow-divider"></div>
          <h2 className="text-4xl lg:text-5xl font-extrabold mb-4">
            From query to <span className="grad-text">action</span> in seconds
          </h2>
          <p className="text-slate-400 text-lg max-w-xl mx-auto">
            A four-step pipeline processes every request — from natural language input to live database results.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 relative">
          {/* Connector lines — desktop only, purely decorative */}
          <div className="hidden lg:block absolute top-11 left-[calc(25%+1.5rem)] right-[calc(25%+1.5rem)] h-px bg-gradient-to-r from-indigo-500/30 via-cyan-400/30 to-violet-500/30 pointer-events-none" />

          {/* Step 1 */}
          <div className="step-card animate-in animate-in-delay-1">
            <div className="step-num">1</div>
            <div className="icon-badge bg-indigo-500/10 w-10 h-10 text-base">
              <i className="fas fa-keyboard text-indigo-400"></i>
            </div>
            <h3 className="font-bold text-white text-base mb-2">User Query</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Type naturally in the assistant bar or mention the Discord bot — any phrasing works.
            </p>
          </div>

          {/* Step 2 */}
          <div className="step-card animate-in animate-in-delay-2">
            <div className="step-num">2</div>
            <div className="icon-badge bg-cyan-500/10 w-10 h-10 text-base">
              <i className="fas fa-microchip text-cyan-400"></i>
            </div>
            <h3 className="font-bold text-white text-base mb-2">MCP Processing</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              The local LLM reads the query and outputs a structured JSON intent with the correct tool name and parameters.
            </p>
          </div>

          {/* Step 3 */}
          <div className="step-card animate-in animate-in-delay-3">
            <div className="step-num">3</div>
            <div className="icon-badge bg-violet-500/10 w-10 h-10 text-base">
              <i className="fas fa-route text-violet-400"></i>
            </div>
            <h3 className="font-bold text-white text-base mb-2">Tool Routing</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              The MCP host maps the intent to the right tool — inventory check, BOM run, stock update, or email order.
            </p>
          </div>

          {/* Step 4 */}
          <div className="step-card animate-in animate-in-delay-4">
            <div className="step-num">4</div>
            <div className="icon-badge bg-emerald-500/10 w-10 h-10 text-base">
              <i className="fas fa-paper-plane text-emerald-400"></i>
            </div>
            <h3 className="font-bold text-white text-base mb-2">Response Generation</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Results stream back word-by-word. Shortages trigger the vendor email flow automatically.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
};

export default HomeSection;
