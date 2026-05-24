import { useState, useEffect } from 'react';
import { type User } from 'firebase/auth';
import { Package, Loader2 } from 'lucide-react';

interface Order {
  _id: string;
  order_id: string;
  order_status: string;
  merchant?: string;
  items?: any[];
}

interface OrdersTabProps {
  user: User;
  apiUrl: string;
}

export function OrdersTab({ user, apiUrl }: OrdersTabProps) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${apiUrl}/gmail/orders?user_id=${user.uid}`);
      const data = await res.json();
      setOrders(data.orders || []);
    } catch (err) {
      console.error('Failed to fetch orders', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchOrders(); }, []);

  return (
    <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Package /> Orders</h2>
      </div>

      <div style={{ marginTop: '1rem', overflowY: 'auto' }}>
        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center' }}><Loader2 size={28} style={{ animation: 'spin-pulse 1s linear infinite' }} /></div>
        ) : orders.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>No active orders.</div>
        ) : (
          orders.map(o => (
            <div key={o._id} className="order-item">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontWeight: 700 }}>{o.merchant || 'Unknown merchant'}</div>
                  <div style={{ color: 'var(--text-muted)' }}>Order {o.order_id}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 700 }}>{o.order_status}</div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
