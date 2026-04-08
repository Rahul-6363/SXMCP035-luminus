import { useState, useEffect } from 'react';
import { BACKEND_URL } from '../utils/constants';
import { mockInventoryData } from '../utils/mockData';

export const useInventory = () => {
  const [inventoryData, setInventoryData] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadInventory = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/items`);
      const data = await res.json();
      setInventoryData(data);
    } catch (err) {
      console.warn("Backend not available, loading simulated schema data.");
      setInventoryData(mockInventoryData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInventory();
  }, []);

  return { inventoryData, loading, refreshData: loadInventory };
};