const Footer = () => (
  <footer className="site-footer">
    <div className="max-w-7xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-10 mb-12">

        {/* Brand */}
        <div className="md:col-span-2">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-9 h-9 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <i className="fas fa-layer-group text-white text-base"></i>
            </div>
            <span className="text-xl font-extrabold tracking-tight">
              INVENTORY<span className="text-indigo-500">.</span>
            </span>
          </div>
          <p className="text-slate-400 text-sm leading-relaxed max-w-xs">
            AI-powered ERP inventory &amp; BOM management system. Natural language queries,
            real-time stock tracking, and automated vendor ordering — all in one place.
          </p>
          <div className="flex gap-3 mt-5">
            <span className="px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold">
              Local LLM
            </span>
            <span className="px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-semibold">
              MCP Tools
            </span>
            <span className="px-3 py-1 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-400 text-xs font-semibold">
              Discord Bot
            </span>
          </div>
        </div>

        {/* Quick Links */}
        <div>
          <h4 className="text-sm font-bold text-white mb-4 uppercase tracking-widest">Navigation</h4>
          <a className="footer-link" href="#home">Home</a>
          <a className="footer-link" href="#inventory">Inventory</a>
          <a className="footer-link" href="#bom">Bill of Materials</a>
          <a className="footer-link" href="#assistant">AI Assistant</a>
        </div>

        {/* Contact */}
        <div>
          <h4 className="text-sm font-bold text-white mb-4 uppercase tracking-widest">System</h4>
          <a className="footer-link" href="http://localhost:8000/docs" target="_blank" rel="noreferrer">
            <i className="fas fa-book mr-2 text-indigo-400"></i>API Docs
          </a>
          <a className="footer-link" href="http://localhost:8000/health" target="_blank" rel="noreferrer">
            <i className="fas fa-heartbeat mr-2 text-emerald-400"></i>Health Check
          </a>
          <a className="footer-link" href="http://localhost:3000/health" target="_blank" rel="noreferrer">
            <i className="fas fa-envelope mr-2 text-cyan-400"></i>Mailer Status
          </a>
          <a className="footer-link" href="https://github.com/Rahul-6363/SXMCP035-luminus" target="_blank" rel="noreferrer">
            <i className="fab fa-github mr-2 text-slate-400"></i>GitHub
          </a>
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-white/5 pt-6 flex flex-col md:flex-row items-center justify-between gap-3">
        <p className="text-slate-500 text-xs">
          © {new Date().getFullYear()} Luminus ERP · Built with FastAPI, React &amp; Ollama
        </p>
        <p className="text-slate-600 text-xs">
          Powered by <span className="text-indigo-400 font-semibold">gemma4:26b</span> via Ollama · MCP Architecture
        </p>
      </div>
    </div>
  </footer>
);

export default Footer;
