import { useState, useEffect, useRef, useCallback } from 'react';
import { BACKEND_URL } from '../utils/constants';

export const useShipments = () => {
  const [shipments, setShipments]   = useState([]);
  const [pendingCount, setPending]  = useState(0);
  const [loading, setLoading]       = useState(true);
  const timerRef                    = useRef(null);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const [sRes, cRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/shipments?status=all`),
        fetch(`${BACKEND_URL}/api/shipments/pending-count`),
      ]);
      if (sRes.ok) {
        const data = await sRes.json();
        setShipments(prev => {
          const next = Array.isArray(data) ? data : [];
          return JSON.stringify(prev) !== JSON.stringify(next) ? next : prev;
        });
      }
      if (cRes.ok) {
        const { count } = await cRes.json();
        setPending(count);
      }
    } catch { /* silent */ }
    finally { if (!silent) setLoading(false); }
  }, []);

  useEffect(() => {
    load(false);
    timerRef.current = setInterval(() => load(true), 30000);
    return () => clearInterval(timerRef.current);
  }, [load]);

  const approve = async (id) => {
    const res  = await fetch(`${BACKEND_URL}/api/shipments/${id}/approve`, { method: 'POST' });
    const data = await res.json();
    await load(true);
    return data;
  };

  const reject = async (id) => {
    const res  = await fetch(`${BACKEND_URL}/api/shipments/${id}/reject`, { method: 'POST' });
    const data = await res.json();
    await load(true);
    return data;
  };

  return { shipments, pendingCount, loading, refresh: () => load(false), approve, reject };
};
