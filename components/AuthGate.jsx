'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { supabase } from '@/lib/supabase';

const ADMIN_EMAIL = 'vmoulakakis@gmail.com';
const SESSION_TIMEOUT_MS = 6000;

function timeoutResult(ms, value) {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export default function AuthGate({ children }) {
  const pathname = usePathname();
  const publicRoute = pathname === '/marketplace' || pathname?.startsWith('/marketplace/') || pathname === '/luxecorner' || pathname?.startsWith('/luxecorner/');
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [password, setPassword] = useState('');
  const [signingIn, setSigningIn] = useState(false);

  useEffect(() => {
    if (publicRoute) {
      setLoading(false);
      return undefined;
    }

    let mounted = true;
    const hardStop = setTimeout(() => {
      if (!mounted) return;
      setLoading(false);
      setMessage((old) => old || 'Ο έλεγχος σύνδεσης καθυστέρησε. Δοκίμασε ξανά.');
    }, SESSION_TIMEOUT_MS);

    const acceptSession = async (nextSession) => {
      if (!mounted) return;
      if (!nextSession) {
        setSession(null);
        setLoading(false);
        return;
      }

      const email = String(nextSession.user?.email || '').toLowerCase();
      if (email !== ADMIN_EMAIL) {
        try {
          await Promise.race([supabase.auth.signOut({ scope: 'local' }), timeoutResult(3000, null)]);
        } catch {}
        if (mounted) {
          setSession(null);
          setMessage(`Ο λογαριασμός ${email || 'που επιλέχθηκε'} δεν έχει δικαίωμα πρόσβασης. Συνδέσου με ${ADMIN_EMAIL}.`);
          setLoading(false);
        }
        return;
      }

      setSession(nextSession);
      setPassword('');
      setMessage('');
      setLoading(false);
    };

    Promise.race([
      supabase.auth.getSession(),
      timeoutResult(SESSION_TIMEOUT_MS, { timeout: true }),
    ]).then((result) => {
      if (!mounted || result?.timeout) return;
      void acceptSession(result?.data?.session ?? null);
    }).catch((error) => {
      if (!mounted) return;
      setMessage(error?.message || 'Αποτυχία ελέγχου σύνδεσης.');
      setLoading(false);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      void acceptSession(nextSession ?? null);
    });

    return () => {
      mounted = false;
      clearTimeout(hardStop);
      listener.subscription.unsubscribe();
    };
  }, [publicRoute]);

  async function signIn(event) {
    event.preventDefault();
    if (signingIn) return;
    setSigningIn(true);
    setMessage('');
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email: ADMIN_EMAIL,
        password,
      });
      if (error) {
        setMessage('Δεν ήταν δυνατή η σύνδεση. Έλεγξε τον κωδικό ή βεβαιώσου ότι έχει οριστεί κωδικός για αυτόν τον λογαριασμό στο Supabase.');
        setSigningIn(false);
        return;
      }
      setPassword('');
      setSigningIn(false);
    } catch {
      setMessage('Παρουσιάστηκε σφάλμα σύνδεσης. Δοκίμασε ξανά.');
      setSigningIn(false);
    }
  }

  async function signOut() {
    try {
      await Promise.race([supabase.auth.signOut(), timeoutResult(5000, null)]);
    } finally {
      setSession(null);
      setPassword('');
    }
  }

  if (publicRoute) return children;

  if (loading) {
    return <div className="auth-card"><div className="eyebrow">Private Admin</div><h2>Έλεγχος πρόσβασης…</h2></div>;
  }

  if (!session) {
    return <main className="auth-wrap">
      <div className="auth-card">
        <div className="eyebrow">Private Admin</div>
        <h1>SocialMarket AI</h1>
        <p className="sub">Σύνδεση διαχειριστή με email και κωδικό.</p>
        <form onSubmit={signIn} className="auth-form">
          <input className="search" type="email" value={ADMIN_EMAIL} readOnly autoComplete="username" aria-label="Email διαχειριστή" />
          <input
            className="search"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Κωδικός πρόσβασης"
            autoComplete="current-password"
            required
            aria-label="Κωδικός πρόσβασης"
          />
          <button className="button" type="submit" disabled={signingIn || !password}>
            {signingIn ? 'Σύνδεση…' : 'Σύνδεση'}
          </button>
          <p className="muted">Επιτρέπεται μόνο ο λογαριασμός <strong>{ADMIN_EMAIL}</strong>.</p>
          <button className="link-button" type="button" onClick={() => window.location.reload()}>Δοκίμασε ξανά</button>
        </form>
        {message && <p className="muted" role="alert">{message}</p>}
      </div>
    </main>;
  }

  return <>
    <div className="admin-session">
      <span className="muted">{session.user.email}</span>
      <button className="link-button" onClick={signOut}>Sign out</button>
    </div>
    {children}
  </>;
}
