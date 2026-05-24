import { useState, useEffect } from 'react';
import { type User } from 'firebase/auth';
import { Loader2, RefreshCw, Mail } from 'lucide-react';

interface ParsedEmail {
  _id: string;
  subject?: string;
  parsed_task?: string;
  action_required?: boolean;
  priority?: string;
}

interface MailsTabProps {
  user: User;
  apiUrl: string;
}

export function MailsTab({ user, apiUrl }: MailsTabProps) {
  const [emails, setEmails] = useState<ParsedEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const fetchEmails = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${apiUrl}/gmail/actions?user_id=${user.uid}`);
      const data = await res.json();
      setEmails(data.items || []);
    } catch (err) {
      console.error('Failed to fetch mails', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmails();
  }, []);

  const syncMails = async () => {
    try {
      setSyncing(true);
      await fetch(`${apiUrl}/gmail/fetch`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: user.uid }) });
      await fetchEmails();
    } catch (err) {
      console.error('Failed to sync mails', err);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Mail /> Mails</h2>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn" onClick={fetchEmails} title="Refresh">
            <RefreshCw size={16} /> Refresh
          </button>
          <button className="btn btn-primary" onClick={syncMails} disabled={syncing}>
            {syncing ? <Loader2 size={16} style={{ animation: 'spin-pulse 1s linear infinite' }} /> : 'Sync mails'}
          </button>
        </div>
      </div>

      <div style={{ marginTop: '1rem', overflowY: 'auto' }}>
        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center' }}><Loader2 size={28} style={{ animation: 'spin-pulse 1s linear infinite' }} /></div>
        ) : emails.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>No action-required emails found.</div>
        ) : (
          emails.map(e => (
            <div key={e._id} className="mail-item">
              <div className="mail-left">
                <div className="mail-subject">{e.subject}</div>
                <div className="mail-task">{e.parsed_task}</div>
              </div>
              <div className="mail-right">
                <div className="mail-priority">{e.priority}</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
