import React, { useState } from 'react';
import KPICards from './KPICards';
import Charts from './Charts';
import InventoryTable from './InventoryTable';
import ItemModal from './ItemModal';

const InventorySection = ({ inventoryData, refreshData, isDarkMode }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedItem, setSelectedItem] = useState(null);

  const filteredData = inventoryData.filter(
    (item) =>
      item.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.category.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <section className="animate-in">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-10">
        <div>
          <h2 className="text-4xl font-extrabold mb-2">Inventory Ledger</h2>
          <p className="text-slate-400">Manage component specifications and tracking.</p>
        </div>
        <div className="flex gap-3 w-full md:w-auto">
          <div className="relative flex-grow">
            <i className="fas fa-search absolute left-4 top-1/2 -translate-y-1/2 text-slate-500"></i>
            <input
              type="text"
              placeholder="Search code or description..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-slate-900 border border-white/10 rounded-2xl pl-12 pr-4 py-3 outline-none focus:ring-2 ring-indigo-500/50 w-full md:w-80 transition-all text-base"
            />
          </div>
          <button
            onClick={refreshData}
            className="bg-slate-800 hover:bg-slate-700 p-4 rounded-2xl transition-all"
            title="Refresh Data"
          >
            <i className="fas fa-sync-alt"></i>
          </button>
        </div>
      </div>

      <KPICards inventoryData={inventoryData} />
      <Charts inventoryData={inventoryData} isDarkMode={isDarkMode} />
      <InventoryTable inventoryData={filteredData} onItemClick={setSelectedItem} />

      {selectedItem && <ItemModal item={selectedItem} onClose={() => setSelectedItem(null)} />}
    </section>
  );
};

export default InventorySection;