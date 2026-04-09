import { useState, useEffect, useRef, useCallback } from 'react';
import { BACKEND_URL } from '../utils/constants';

const POLL_INTERVAL = 8000; // silent background poll every 8 seconds

export const useInventory = () => {
  const [inventoryData, setInventoryData] = useState([]);
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState(null);
  const timerRef                          = useRef(null);

  // silentRefresh = true → don't set loading spinner (background poll)
  const loadInventory = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/items`);
      if (!res.ok) throw new Error(`Backend returned ${res.status}`);
      const data = await res.json();
      setInventoryData(prev => {
        const next = Array.isArray(data) ? data : [];
        // Only trigger re-render if data actually changed
        return JSON.stringify(prev) !== JSON.stringify(next) ? next : prev;
      });
    } catch (err) {
      if (!silent) {
        console.error("Inventory fetch failed:", err.message);
        setError(err.message);
        setInventoryData([]);
      }
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInventory(false); // initial load with spinner

    // Background polling — silent, no spinner
    timerRef.current = setInterval(() => loadInventory(true), POLL_INTERVAL);
    return () => clearInterval(timerRef.current);
  }, [loadInventory]);

  return { inventoryData, loading, error, refreshData: () => loadInventory(false) };
};