import { useState } from 'react';

const STATUS_STYLE = {
  pending:  'bg-amber-500/15 text-amber-300 border border-amber-500/30',
  approved: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30',
  rejected: 'bg-rose-500/15 text-rose-300 border border-rose-500/30',
};

const STATUS_ICON = {
  pending:  'fa-clock',
  approved: 'fa-check-circle',
  rejected: 'fa-times-circle',
};

export default function ShipmentPanel({ shipments, loading, refresh, approve, reject }) {
  const [busy, setBusy]         = useState({});    // id → true while request in-flight
  const [feedback, setFeedback] = useState({});   // id → message string
  const [filter, setFilter]     = useState('pending');
  const [expanded, setExpanded] = useState(null); // id of expanded card

  const visible = shipments.filter(s =>
    filter === 'all' ? true : s.status === filter
  );

  const act = async (id, fn, label) => {
    setBusy(b => ({ ...b, [id]: true }));
    try {
      const res = await fn(id);
      setFeedback(f => ({ ...f, [id]: res.message || `${label} successful.` }));
    } catch {
      setFeedback(f => ({ ...f, [id]: `${label} failed.` }));
    } finally {
      setBusy(b => ({ ...b, [id]: false }));
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Incoming Shipments</h2>
          <p className="text-slate-400 text-sm mt-1">
            Vendor replies parsed from email — approve to update inventory, reject to dismiss.
          </p>
        </div>
        <button
          onClick={refresh}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-all"
        >
          <i className="fas fa-sync-alt text-xs"></i> Refresh
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {['pending', 'approved', 'rejected', 'all'].map(tab => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold capitalize transition-all
              ${filter === tab
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'}`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <i className="fas fa-spinner fa-spin text-indigo-400 text-2xl mr-3"></i>
          <span className="text-slate-400">Loading shipments…</span>
        </div>
      )}

      {/* Empty state */}
      {!loading && visible.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mb-4">
            <i className="fas fa-inbox text-slate-500 text-2xl"></i>
          </div>
          <p className="text-slate-400 font-medium">No {filter === 'all' ? '' : filter} shipments</p>
          <p className="text-slate-600 text-sm mt-1">
            {filter === 'pending'
              ? 'When a vendor replies to a purchase order, it will appear here.'
              : 'Nothing to show for this filter.'}
          </p>
        </div>
      )}

      {/* Shipment cards */}
      <div className="space-y-4">
        {visible.map(s => {
          const items   = Array.isArray(s.parsed_items) ? s.parsed_items : [];
          const isOpen  = expanded === s.id;
          const isBusy  = busy[s.id];
          const msg     = feedback[s.id];

          return (
            <div
              key={s.id}
              className={`rounded-2xl border bg-slate-900/60 backdrop-blur-xl transition-all
                ${s.status === 'pending'
                  ? 'border-amber-500/20 hover:border-amber-500/40'
                  : s.status === 'approved'
                  ? 'border-emerald-500/20'
                  : 'border-slate-700/40'}`}
            >
              {/* Card header */}
              <div
                className="flex items-start justify-between p-5 cursor-pointer"
                onClick={() => setExpanded(isOpen ? null : s.id)}
              >
                <div className="flex items-start gap-4 min-w-0">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0
                    ${s.status === 'pending'  ? 'bg-amber-500/15' :
                      s.status === 'approved' ? 'bg-emerald-500/15' : 'bg-slate-800'}`}>
                    <i className={`fas ${STATUS_ICON[s.status]}
                      ${s.status === 'pending'  ? 'text-amber-400' :
                        s.status === 'approved' ? 'text-emerald-400' : 'text-slate-500'}`}></i>
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-slate-100 truncate">
                        {s.subject || '(no subject)'}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${STATUS_STYLE[s.status]}`}>
                        {s.status}
                      </span>
                      {items.length > 0 && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/25">
                          {items.length} item{items.length !== 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                    <p className="text-slate-400 text-sm mt-0.5 truncate">
                      From: {s.sender}
                    </p>
                    <p className="text-slate-600 text-xs mt-0.5">
                      #{s.id} · {new Date(s.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <i className={`fas fa-chevron-${isOpen ? 'up' : 'down'} text-slate-500 mt-1 ml-4 shrink-0`}></i>
              </div>

              {/* Expanded body */}
              {isOpen && (
                <div className="px-5 pb-5 border-t border-white/5 pt-4 space-y-4">

                  {/* Parsed items table */}
                  {items.length > 0 ? (
                    <div>
                      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                        Parsed Shipment Items
                      </p>
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-slate-500 text-xs border-b border-white/5">
                            <th className="text-left py-2 font-medium">Item Code</th>
                            <th className="text-left py-2 font-medium">Description</th>
                            <th className="text-right py-2 font-medium">Qty</th>
                            <th className="text-right py-2 font-medium">UOM</th>
                          </tr>
                        </thead>
                        <tbody>
                          {items.map((item, i) => (
                            <tr key={i} className="border-b border-white/5 hover:bg-white/2">
                              <td className="py-2 font-mono text-indigo-300">{item.item_code || '—'}</td>
                              <td className="py-2 text-slate-300">{item.description || '—'}</td>
                              <td className="py-2 text-right font-bold text-emerald-400">{item.quantity}</td>
                              <td className="py-2 text-right text-slate-400">{item.uom}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-amber-400 text-sm">
                      <i className="fas fa-exclamation-triangle mr-2"></i>
                      No items could be parsed automatically — check the raw email below.
                    </p>
                  )}

                  {/* Raw excerpt */}
                  {s.raw_excerpt && (
                    <details className="group">
                      <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-300 select-none">
                        <i className="fas fa-envelope-open-text mr-1"></i>
                        View raw email excerpt
                      </summary>
                      <pre className="mt-2 p-3 bg-slate-950/60 rounded-xl text-xs text-slate-400 whitespace-pre-wrap overflow-x-auto border border-white/5 max-h-48 overflow-y-auto">
                        {s.raw_excerpt}
                      </pre>
                    </details>
                  )}

                  {/* Feedback message */}
                  {msg && (
                    <p className={`text-sm font-medium ${msg.includes('fail') ? 'text-rose-400' : 'text-emerald-400'}`}>
                      <i className={`fas ${msg.includes('fail') ? 'fa-times-circle' : 'fa-check-circle'} mr-2`}></i>
                      {msg}
                    </p>
                  )}

                  {/* Action buttons — only for pending */}
                  {s.status === 'pending' && (
                    <div className="flex gap-3 pt-1">
                      <button
                        onClick={() => act(s.id, approve, 'Approval')}
                        disabled={isBusy}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                          bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white
                          font-semibold text-sm transition-all"
                      >
                        {isBusy
                          ? <i className="fas fa-spinner fa-spin"></i>
                          : <i className="fas fa-check"></i>}
                        Approve &amp; Update Inventory
                      </button>
                      <button
                        onClick={() => act(s.id, reject, 'Rejection')}
                        disabled={isBusy}
                        className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                          bg-slate-700 hover:bg-rose-600/70 disabled:opacity-50 text-slate-200
                          font-semibold text-sm transition-all"
                      >
                        <i className="fas fa-times"></i> Reject
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
