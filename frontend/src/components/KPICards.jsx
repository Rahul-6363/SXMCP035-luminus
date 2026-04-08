import React from 'react';

const KPICards = ({ inventoryData }) => {
  const totalItems = inventoryData.length;
  const totalValue = inventoryData.reduce(
    (sum, i) => sum + i.quantity * parseFloat(i.standard_cost),
    0
  );
  const lowStock = inventoryData.filter((i) => i.quantity < 10).length;

  const cards = [
    {
      label: 'Total Unique Parts',
      val: totalItems,
      icon: 'fa-microchip',
      color: 'text-indigo-500',
      bg: 'bg-indigo-500/10',
    },
    {
      label: 'Inventory Valuation',
      val: `₹${(totalValue / 1000).toFixed(1)}k`,
      icon: 'fa-wallet',
      color: 'text-emerald-500',
      bg: 'bg-emerald-500/10',
    },
    {
      label: 'Critical Stock',
      val: lowStock,
      icon: 'fa-triangle-exclamation',
      color: 'text-amber-500',
      bg: 'bg-amber-500/10',
    },
    {
      label: 'System Health',
      val: '100%',
      icon: 'fa-server',
      color: 'text-cyan-500',
      bg: 'bg-cyan-500/10',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
      {cards.map((card, index) => (
        <div
          key={index}
          className="glass p-6 rounded-3xl border-white/5 hover:scale-[1.02] transition-transform"
        >
          <div
            className={`w-12 h-12 ${card.bg} ${card.color} rounded-2xl flex items-center justify-center mb-4 text-xl`}
          >
            <i className={`fas ${card.icon}`}></i>
          </div>
          <div className="text-3xl font-extrabold mb-1">{card.val}</div>
          <div className="text-slate-500 font-medium text-sm">{card.label}</div>
        </div>
      ))}
    </div>
  );
};

export default KPICards;