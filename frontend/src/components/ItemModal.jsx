import React from 'react';

const ItemModal = ({ item, onClose }) => {
  if (!item) return null;

  const cost = parseFloat(item.standard_cost).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const totalVal = (item.quantity * item.standard_cost).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return (
    <div className="fixed inset-0 bg-slate-950/90 backdrop-blur-md z-[100] p-6 flex items-center justify-center">
      <div className="glass max-w-2xl w-full rounded-[2.5rem] p-10 border-white/10 relative max-h-[90vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute top-6 right-8 text-2xl text-slate-500 hover:text-white"
        >
          &times;
        </button>

        <div className="flex items-center justify-between mb-2">
          <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-lg text-xs font-mono text-indigo-400">
            {item.code}
          </span>
          <span
            className={`px-3 py-1 rounded-full text-xs font-bold ${
              item.status === 'Active'
                ? 'bg-emerald-500/10 text-emerald-400'
                : 'bg-rose-500/10 text-rose-400'
            }`}
          >
            {item.status}
          </span>
        </div>

        <h2 className="text-3xl font-extrabold mb-1 mt-4 leading-tight">{item.description}</h2>
        <p className="text-slate-400 font-bold mb-8 uppercase tracking-widest text-xs">
          {item.category} • {item.component_classification}
        </p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white/5 p-4 rounded-2xl">
            <p className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">Available</p>
            <p className="text-2xl font-bold font-mono text-emerald-400">
              {item.available ?? item.quantity} <span className="text-sm text-slate-400">{item.uom}</span>
            </p>
            {item.quantity_in_use > 0 && (
              <p className="text-xs text-amber-400 mt-1">{item.quantity_in_use} in use</p>
            )}
          </div>
          <div className="bg-white/5 p-4 rounded-2xl">
            <p className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">Std Cost</p>
            <p className="text-xl font-bold font-mono text-emerald-400">₹{cost}</p>
          </div>
          <div className="bg-white/5 p-4 rounded-2xl">
            <p className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">Total Value</p>
            <p className="text-xl font-bold font-mono text-indigo-400">₹{totalVal}</p>
          </div>
          <div className="bg-white/5 p-4 rounded-2xl">
            <p className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">Lead Time</p>
            <p className="text-2xl font-bold font-mono">
              {item.lead_time} <span className="text-sm text-slate-400 font-sans">Days</span>
            </p>
          </div>
        </div>

        <div className="border-t border-white/10 pt-6">
          <h4 className="text-sm font-bold text-slate-300 mb-4">Technical Specifications</h4>
          <div className="grid grid-cols-2 gap-y-4 gap-x-8 text-sm">
            <div className="flex justify-between border-b border-white/5 pb-2">
              <span className="text-slate-500">Part Grade</span>
              <span className="font-medium">{item.part_grade || '-'}</span>
            </div>
            <div className="flex justify-between border-b border-white/5 pb-2">
              <span className="text-slate-500">Revision</span>
              <span className="font-medium font-mono">{item.revision || '-'}</span>
            </div>
            <div className="flex justify-between border-b border-white/5 pb-2">
              <span className="text-slate-500">MSL Level</span>
              <span className="font-medium">{item.msl_level || '-'}</span>
            </div>
            <div className="flex justify-between border-b border-white/5 pb-2">
              <span className="text-slate-500">Classification</span>
              <span className="font-medium">{item.component_classification || '-'}</span>
            </div>
          </div>
        </div>

        <button
          onClick={onClose}
          className="w-full mt-8 py-4 bg-slate-800 hover:bg-slate-700 text-white rounded-2xl font-bold transition-all border border-white/5 hover:border-white/20"
        >
          Close Panel
        </button>
      </div>
    </div>
  );
};

export default ItemModal;