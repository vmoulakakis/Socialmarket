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
          setMessage(`Ο λογαριασμός ${email || 'Google'} δεν έχει δικαίωμα πρόσβασης. Συνδέσου με ${ADMIN_EMAIL}.`);
          setLoading(false);
        }
        return;
      }

      setSession(nextSession);
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

  async function signInWithGoogle() {
    if (signingIn) return;
    setSigningIn(true);
    setMessage('');
    try {
      const redirectTo = typeof window !== 'undefined'
        ? `${window.location.origin}${pathname || '/admin'}`
        : undefined;
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo,
          queryParams: {
            prompt: 'select_account',
            login_hint: ADMIN_EMAIL,
          },
        },
      });
      if (error) {
        setMessage(error.message || 'Δεν ήταν δυνατή η έναρξη σύνδεσης Google.');
        setSigningIn(false);
      }
    } catch (error) {
      setMessage(error?.message || 'Δεν ήταν δυνατή η έναρξη σύνδεσης Google.');
      setSigningIn(false);
    }
  }

  async function signOut() {
    try {
      await Promise.race([supabase.auth.signOut(), timeoutResult(5000, null)]);
    } finally {
      setSession(null);
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
        <p className="sub">Σύνδεση διαχειριστή με Google.</p>
        <div className="auth-form">
          <button className="button" type="button" onClick={signInWithGoogle} disabled={signingIn}>
            {signingIn ? 'Μετάβαση στη Google…' : 'Σύνδεση με Google'}
          </button>
          <p className="muted">Επιτρεπόμενος λογαριασμός: <strong>{ADMIN_EMAIL}</strong>. Άλλοι λογαριασμοί Google αποσυνδέονται αυτόματα.</p>
          <button className="link-button" type="button" onClick={() => window.location.reload()}>Δοκίμασε ξανά</button>
        </div>
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
