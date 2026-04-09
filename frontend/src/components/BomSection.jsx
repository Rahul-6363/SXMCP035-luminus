import { useState } from 'react';
import { BACKEND_URL } from '../utils/constants';

const StatusBadge = ({ available, required }) => {
  const ok = available >= required;
  return (
    <span className={`text-xs font-bold px-2 py-1 rounded-lg ${ok ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
      {ok ? 'In Stock' : 'Short'}
    </span>
  );
};

const BomModal = ({ bom, onClose, onRunBom }) => {
  const [qty, setQty]         = useState(1);
  const [detail, setDetail]   = useState(null);
  const [loading, setLoading] = useState(true);

  useState(() => {
    fetch(`${BACKEND_URL}/api/bom/${encodeURIComponent(bom.name)}`)
      .then(r => r.json())
      .then(d => { setDetail(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [bom.name]);

  return (
    <div className="fixed inset-0 bg-slate-950/90 backdrop-blur-md z-[100] p-6 flex items-center justify-center">
      <div className="glass max-w-3xl w-full rounded-[2.5rem] p-10 border-white/10 relative max-h-[90vh] overflow-y-auto">
        <button onClick={onClose} className="absolute top-6 right-8 text-2xl text-slate-500 hover:text-white">&times;</button>

        <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-lg text-xs font-mono text-indigo-400">
          {bom.name}
        </span>
        <h2 className="text-3xl font-extrabold mt-4 mb-1">{bom.description || bom.name}</h2>
        <p className="text-slate-400 text-xs uppercase tracking-widest mb-8">
          Output: {bom.output_quantity} unit(s) · Lead time: {bom.lead_time_days} days · {bom.component_count} component(s)
        </p>

        {loading ? (
          <p className="text-slate-400"><i className="fas fa-spinner fa-spin mr-2"></i>Loading components…</p>
        ) : detail?.components?.length ? (
          <table className="w-full text-sm mb-8 border-collapse">
            <thead>
              <tr className="text-slate-400 text-xs uppercase tracking-widest border-b border-white/10">
                <th className="text-left py-2">Item</th>
                <th className="text-right py-2">Qty / unit</th>
                <th className="text-right py-2">Available</th>
                <th className="text-right py-2">In Use</th>
                <th className="text-right py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {detail.components.map(c => (
                <tr key={c.item_code}>
                  <td className="py-3">
                    <p className="font-mono text-indigo-400 font-bold">{c.item_code}</p>
                    <p className="text-slate-500 text-xs">{c.description}</p>
                  </td>
                  <td className="text-right py-3 font-mono">{c.qty_required} {c.uom}</td>
                  <td className="text-right py-3 font-mono text-emerald-400">{c.available}</td>
                  <td className="text-right py-3 font-mono text-amber-400">{c.quantity_in_use}</td>
                  <td className="text-right py-3">
                    <StatusBadge available={c.available} required={c.qty_required} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-slate-500 mb-8">No components defined for this BOM.</p>
        )}

        {/* Run BOM */}
        <div className="border-t border-white/10 pt-6 flex items-center gap-4">
          <label className="text-slate-400 text-sm font-medium">Run quantity:</label>
          <input
            type="number"
            min={1}
            value={qty}
            onChange={e => setQty(Math.max(1, parseInt(e.target.value) || 1))}
            className="w-24 bg-slate-800 border border-white/10 rounded-xl px-3 py-2 text-center font-mono outline-none focus:ring-2 ring-indigo-500/50"
          />
          <button
            onClick={() => { onRunBom(bom.name, qty); onClose(); }}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2 rounded-xl font-bold transition-all"
          >
            Run BOM
          </button>
          <button
            onClick={() => { onRunBom(`can I build ${bom.name} in quantity ${qty}`, null, true); onClose(); }}
            className="bg-slate-700 hover:bg-slate-600 text-white px-6 py-2 rounded-xl font-semibold transition-all"
          >
            Check Buildability
          </button>
        </div>
      </div>
    </div>
  );
};

const BomSection = ({ bomData, refreshBom, onSendToChat }) => {
  const [selected, setSelected] = useState(null);

  const handleRunBom = (bomName, qty, isCheck = false) => {
    const text = isCheck
      ? bomName  // already full sentence for buildability
      : `run BOM ${bomName} quantity ${qty}`;
    onSendToChat(text);
  };

  return (
    <section className="animate-in">
      <div className="flex justify-between items-center mb-10">
        <div>
          <h2 className="text-4xl font-extrabold mb-2">Bill of Materials</h2>
          <p className="text-slate-400">Define and execute production BOMs against live inventory.</p>
        </div>
        <button
          onClick={refreshBom}
          className="bg-slate-800 hover:bg-slate-700 p-4 rounded-2xl transition-all"
          title="Refresh"
        >
          <i className="fas fa-sync-alt"></i>
        </button>
      </div>

      {bomData.length === 0 ? (
        <div className="glass rounded-[2rem] p-12 text-center text-slate-400">
          <i className="fas fa-layer-group text-4xl mb-4 block text-slate-600"></i>
          No BOMs defined yet. Use the assistant bar to create one.
        </div>
      ) : (
        <div className="glass rounded-[2rem] overflow-hidden border-white/5">
          <table className="w-full text-left border-collapse whitespace-nowrap">
            <thead>
              <tr className="bg-white/5 text-slate-400 text-sm uppercase tracking-widest">
                <th className="px-6 py-5">Name</th>
                <th className="px-6 py-5">Description</th>
                <th className="px-6 py-5 text-right">Output Qty</th>
                <th className="px-6 py-5 text-right">Lead Time</th>
                <th className="px-6 py-5 text-right">Components</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {bomData.map(bom => (
                <tr
                  key={bom.id}
                  onClick={() => setSelected(bom)}
                  className="hover:bg-white/[0.04] transition-colors cursor-pointer group"
                >
                  <td className="px-6 py-5 font-mono font-bold text-indigo-400 group-hover:text-indigo-300">
                    {bom.name}
                  </td>
                  <td className="px-6 py-5 text-slate-300 truncate max-w-[260px]">
                    {bom.description || '—'}
                  </td>
                  <td className="px-6 py-5 text-right font-mono">{bom.output_quantity}</td>
                  <td className="px-6 py-5 text-right">
                    <span className="text-sm font-medium px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-white/5">
                      {bom.lead_time_days}d
                    </span>
                  </td>
                  <td className="px-6 py-5 text-right font-mono text-slate-300">{bom.component_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <BomModal
          bom={selected}
          onClose={() => setSelected(null)}
          onRunBom={handleRunBom}
        />
      )}
    </section>
  );
};

export default BomSection;
