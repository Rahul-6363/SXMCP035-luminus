import React from 'react';

const InventoryTable = ({ inventoryData, onItemClick }) => {
  return (
    <div className="glass rounded-[2rem] overflow-hidden border-white/5">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse whitespace-nowrap">
          <thead>
            <tr className="bg-white/5 text-slate-400 text-sm uppercase tracking-widest">
              <th className="px-6 py-5 font-semibold">Code</th>
              <th className="px-6 py-5 font-semibold">Description</th>
              <th className="px-6 py-5 font-semibold">Category</th>
              <th className="px-6 py-5 font-semibold">Stock (UoM)</th>
              <th className="px-6 py-5 font-semibold">Std Cost</th>
              <th className="px-6 py-5 font-semibold">Stock Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-base">
            {inventoryData.map((item) => {
              const isLow = item.quantity < 10;
              const statusBadgeClass = isLow
                ? 'bg-rose-500/10 text-rose-500 border border-rose-500/20'
                : 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20';
              const cost = parseFloat(item.standard_cost).toLocaleString('en-IN', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              });

              return (
                <tr
                  key={item.id}
                  onClick={() => onItemClick(item)}
                  className="hover:bg-white/[0.04] transition-colors cursor-pointer group"
                >
                  <td className="px-6 py-5 font-mono font-bold text-indigo-400 group-hover:text-indigo-300">
                    {item.code}
                  </td>
                  <td className="px-6 py-5 font-bold text-slate-200 truncate max-w-[280px]">
                    {item.description}
                  </td>
                  <td className="px-6 py-5">
                    <span className="text-sm font-medium px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-white/5">
                      {item.category}
                    </span>
                  </td>
                  <td className="px-6 py-5 font-mono font-bold">
                    {item.quantity}{' '}
                    <span className="text-xs text-slate-500 font-sans ml-1">{item.uom}</span>
                  </td>
                  <td className="px-6 py-5 text-slate-300 font-mono">₹{cost}</td>
                  <td className="px-6 py-5">
                    <span
                      className={`text-xs uppercase tracking-tighter font-black px-3 py-1.5 rounded-lg ${statusBadgeClass}`}
                    >
                      {isLow ? 'Reorder' : 'Optimal'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default InventoryTable;