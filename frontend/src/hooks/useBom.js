import { useState, useEffect, useRef, useCallback } from 'react';
import { BACKEND_URL } from '../utils/constants';

const POLL_INTERVAL = 10000; // silent background poll every 10 seconds

export const useBom = () => {
  const [bomData, setBomData] = useState([]);
  const [loading, setLoading] = useState(true);
  const timerRef              = useRef(null);

  const loadBom = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const res  = await fetch(`${BACKEND_URL}/api/bom`);
      if (!res.ok) throw new Error(`Backend returned ${res.status}`);
      const data = await res.json();
      setBomData(prev => {
        const next = Array.isArray(data) ? data : [];
        return JSON.stringify(prev) !== JSON.stringify(next) ? next : prev;
      });
    } catch {
      if (!silent) setBomData([]);
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBom(false);
    timerRef.current = setInterval(() => loadBom(true), POLL_INTERVAL);
    return () => clearInterval(timerRef.current);
  }, [loadBom]);

  return { bomData, loading, refreshBom: () => loadBom(false) };
};
