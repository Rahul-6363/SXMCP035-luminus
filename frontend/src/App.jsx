import { useState, useRef } from 'react';
import Navbar from './components/Navbar';
import HomeSection from './components/HomeSection';
import InventorySection from './components/InventorySection';
import BomSection from './components/BomSection';
import ShipmentPanel from './components/ShipmentPanel';
import AssistantBar from './components/AssistantBar';
import Footer from './components/Footer';
import { useInventory } from './hooks/useInventory';
import { useBom } from './hooks/useBom';
import { useShipments } from './hooks/useShipments';

function App() {
  const [activeSection, setActiveSection] = useState('home');
  const [isDarkMode, setIsDarkMode]       = useState(true);
  const assistantRef                       = useRef(null);

  const { inventoryData, loading: invLoading, refreshData } = useInventory();
  const { bomData, refreshBom } = useBom();
  const { shipments, pendingCount, loading: shipLoading, refresh: refreshShipments, approve, reject } = useShipments();

  // Only block the full page on the very first load (no data yet)
  const initialLoad = invLoading && inventoryData.length === 0;

  const toggleTheme = () => {
    setIsDarkMode(prev => {
      const next = !prev;
      document.documentElement.classList.toggle('dark', next);
      document.body.classList.toggle('bg-slate-950', next);
      document.body.classList.toggle('text-slate-100', next);
      document.body.classList.toggle('bg-slate-50', !next);
      document.body.classList.toggle('text-slate-900', !next);
      return next;
    });
  };

  // Called by BOM modal run buttons — pre-fills the AssistantBar input
  const sendToChat = (text) => {
    assistantRef.current?.submitText(text);
    setActiveSection('inventory'); // switch to inventory to see result
  };

  if (initialLoad) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
        <div className="text-center">
          <i className="fas fa-spinner fa-spin text-4xl text-indigo-500 mb-4"></i>
          <p className="text-slate-400">Loading ERP data…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative">
      {/* Ambient background orbs — pure CSS, no logic */}
      <div className="orb orb-1" aria-hidden="true" />
      <div className="orb orb-2" aria-hidden="true" />
      <div className="orb orb-3" aria-hidden="true" />
      <Navbar
        activeSection={activeSection}
        setActiveSection={setActiveSection}
        isDarkMode={isDarkMode}
        toggleTheme={toggleTheme}
        pendingShipments={pendingCount}
      />

      <main className="pt-32 pb-48 px-6 max-w-7xl mx-auto">
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
        {activeSection === 'bom' && (
          <BomSection
            bomData={bomData}
            refreshBom={refreshBom}
            onSendToChat={sendToChat}
          />
        )}
        {activeSection === 'shipments' && (
          <ShipmentPanel
            shipments={shipments}
            loading={shipLoading}
            refresh={refreshShipments}
            approve={approve}
            reject={reject}
          />
        )}
      </main>

      <AssistantBar
        ref={assistantRef}
        onActionComplete={() => { refreshData(); refreshBom(); }}
      />

      {activeSection === 'home' && <Footer />}
    </div>
  );
}

export default App;
