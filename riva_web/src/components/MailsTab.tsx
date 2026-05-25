import { useState, useEffect } from 'react';
import { type User } from 'firebase/auth';
import { Loader2, RefreshCw, Mail, ExternalLink, Trash2 } from 'lucide-react';

interface ParsedEmail {
  _id: string;
  subject?: string;
  from?: string;
  snippet?: string;
  parsed_task?: string;
  action_required?: boolean;
  priority?: string;
  received_at?: string;
}

interface MailsTabProps {
  user: User;
  apiUrl: string;
}

export function MailsTab({ user, apiUrl }: MailsTabProps) {
  const [emails, setEmails] = useState<ParsedEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const pageSize = 8;

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${apiUrl}/gmail/status?user_id=${user.uid}`);
      const data = await res.json();
      setConnected(Boolean(data.connected));
    } catch (err) {
      console.warn('Failed to fetch gmail status', err);
      setConnected(null);
    }
  };

  const fetchEmails = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${apiUrl}/gmail/actions?user_id=${user.uid}`);
      const data = await res.json();
      setEmails(data.items || []);
      setPage(0);
    } catch (err) {
      console.error('Failed to fetch mails', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchEmails();
  }, []);

  const syncMails = async () => {
    try {
      setSyncing(true);
      const res = await fetch(`${apiUrl}/gmail/fetch`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: user.uid }) });
      const data = await res.json();
      if (!res.ok) {
        console.error('Sync failed:', data);
        alert(`Sync failed: ${data.detail || 'Unknown error'}`);
        return;
      }
      await fetchStatus();
      await fetchEmails();
    } catch (err) {
      console.error('Failed to sync mails', err);
      alert(`Error: ${err}`);
    } finally {
      setSyncing(false);
    }
  };

  const handleConnect = async () => {
    try {
      const res = await fetch(`${apiUrl}/gmail/oauth/url?user_id=${user.uid}`);
      const data = await res.json();
      if (data.oauth_url) window.open(data.oauth_url, '_blank');
      else console.error('OAuth URL missing:', data);
    } catch (err) {
      console.error('Failed to get oauth url', err);
    }
  };

  const handleDisconnect = async () => {
    try {
      await fetch(`${apiUrl}/gmail/disconnect`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: user.uid }) });
      await fetchStatus();
      await fetchEmails();
    } catch (err) {
      console.error('Failed to disconnect', err);
    }
  };

  const start = page * pageSize;
  const visible = emails.slice(start, start + pageSize);
  const pageCount = Math.ceil(emails.length / pageSize);

  return (
    <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Mail /> Mails</h2>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {connected === null ? null : connected ? (
            <div style={{ color: 'var(--success)' }}>Connected</div>
          ) : (
            <div style={{ color: 'var(--text-muted)' }}>Not connected</div>
          )}

          {connected ? (
            <button className="btn btn-ghost" onClick={handleDisconnect} title="Disconnect Gmail">
              <Trash2 size={14} /> Disconnect
            </button>
          ) : (
            <button className="btn" onClick={handleConnect} title="Connect Gmail">
              <ExternalLink size={14} /> Connect Gmail
            </button>
          )}

          <button className="btn" onClick={fetchEmails} title="Refresh">
            <RefreshCw size={16} /> Refresh
          </button>
          <button className="btn btn-primary" onClick={syncMails} disabled={syncing}>
            {syncing ? <Loader2 size={16} style={{ animation: 'spin-pulse 1s linear infinite' }} /> : 'Sync mails'}
          </button>
        </div>
      </div>

      <div style={{ marginTop: '1rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center' }}><Loader2 size={28} style={{ animation: 'spin-pulse 1s linear infinite' }} /></div>
        ) : emails.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>No action-required emails found.</div>
        ) : (
          visible.map(e => (
            <div key={e._id} style={{ border: '1px solid rgba(0,0,0,0.06)', borderRadius: 8, padding: '0.75rem', display: 'flex', justifyContent: 'space-between', gap: '1rem', background: 'var(--panel-bg)' }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{e.subject || 'No subject'}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{e.from || ''} · {e.received_at ? new Date(e.received_at).toLocaleString() : ''}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 700 }}>{e.priority || ''}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{e.action_required ? 'Action required' : 'Info'}</div>
                  </div>
                </div>

                <div style={{ marginTop: 8 }}>
                  <div style={{ color: 'var(--text-muted)', marginBottom: 6 }}>{e.parsed_task}</div>
                  {expandedId === e._id ? (
                    <div style={{ marginTop: 6, color: 'var(--text-main)', background: 'rgba(0,0,0,0.02)', padding: 8, borderRadius: 6 }}>{e.snippet}</div>
                  ) : null}
                </div>

                <div style={{ marginTop: 8, display: 'flex', gap: '0.5rem' }}>
                  <button className="btn btn-sm" onClick={() => setExpandedId(expandedId === e._id ? null : e._id)}>{expandedId === e._id ? 'Hide preview' : 'Preview'}</button>
                  <a className="btn btn-sm" href={`${apiUrl}/gmail/message/view?user_id=${user.uid}&message_id=${e._id}`} target="_blank" rel="noreferrer">Open in Gmail</a>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {emails.length > pageSize && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 12 }}>
          <button className="btn" onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}>Prev</button>
          <div style={{ display: 'flex', alignItems: 'center', padding: '0 8px' }}>{page + 1} / {pageCount}</div>
          <button className="btn" onClick={() => setPage(p => Math.min(pageCount - 1, p + 1))} disabled={page >= pageCount - 1}>Next</button>
        </div>
      )}
    </div>
  );
}
