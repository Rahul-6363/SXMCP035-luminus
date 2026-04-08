import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import HomeSection from './components/HomeSection';
import InventorySection from './components/InventorySection';
import AssistantBar from './components/AssistantBar';
import { useInventory } from './hooks/useInventory';

function App() {
  const [activeSection, setActiveSection] = useState('home');
  const [isDarkMode, setIsDarkMode] = useState(true);
  const { inventoryData, loading, refreshData } = useInventory();

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      document.body.classList.add('bg-slate-950', 'text-slate-100');
      document.body.classList.remove('bg-slate-50', 'text-slate-900');
    } else {
      document.documentElement.classList.remove('dark');
      document.body.classList.remove('bg-slate-950', 'text-slate-100');
      document.body.classList.add('bg-slate-50', 'text-slate-900');
    }
  }, [isDarkMode]);

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
        <div className="text-center">
          <i className="fas fa-spinner fa-spin text-4xl text-indigo-500 mb-4"></i>
          <p className="text-slate-400">Loading inventory data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative">
      <Navbar
        activeSection={activeSection}
        setActiveSection={setActiveSection}
        isDarkMode={isDarkMode}
        toggleTheme={toggleTheme}
      />

      <main className="pt-32 pb-32 px-6 max-w-7xl mx-auto">
        {activeSection === 'home' && (
          <HomeSection totalItems={inventoryData.length} setActiveSection={setActiveSection} />
        )}
        {activeSection === 'inventory' && (
          <InventorySection
            inventoryData={inventoryData}
            refreshData={refreshData}
            isDarkMode={isDarkMode}
          />
        )}
      </main>

      <AssistantBar />
    </div>
  );
}

export default App;