'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

const ADMIN_EMAIL = 'vmoulakakis@gmail.com';
const SESSION_TIMEOUT_MS = 6000;
const SIGNIN_TIMEOUT_MS = 12000;

function timeoutResult(ms, value) {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export default function AuthGate({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [signingIn, setSigningIn] = useState(false);

  useEffect(() => {
    let mounted = true;
    const hardStop = setTimeout(() => {
      if (!mounted) return;
      setLoading(false);
      setMessage((old) => old || 'Ο έλεγχος session καθυστέρησε. Μπορείς να συνδεθείς ξανά.');
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
          await Promise.race([
            supabase.auth.signOut({ scope: 'local' }),
            timeoutResult(3000, null),
          ]);
        } catch {}
        if (mounted) {
          setSession(null);
          setMessage('Δεν επιτρέπεται πρόσβαση σε αυτόν τον λογαριασμό.');
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
      setMessage(error?.message || 'Αποτυχία ελέγχου session.');
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
  }, []);

  async function signIn(event) {
    event.preventDefault();
    if (!password || signingIn) return;
    setSigningIn(true);
    setMessage('');

    try {
      const result = await Promise.race([
        supabase.auth.signInWithPassword({ email: ADMIN_EMAIL, password }),
        timeoutResult(SIGNIN_TIMEOUT_MS, { timeout: true }),
      ]);

      if (result?.timeout) {
        setMessage('Η απάντηση σύνδεσης καθυστέρησε. Αν το login ολοκληρώθηκε, πάτησε “Retry session”.');
        setSigningIn(false);
        return;
      }

      if (result?.error) {
        setMessage(result.error.message === 'Invalid login credentials' ? 'Λάθος password.' : result.error.message);
        setSigningIn(false);
        return;
      }

      setPassword('');
      setSigningIn(false);
    } catch (error) {
      setMessage(error?.message || 'Αποτυχία σύνδεσης.');
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

  if (loading) {
    return <div className="auth-card"><div className="eyebrow">Private Admin</div><h2>Έλεγχος πρόσβασης…</h2></div>;
  }

  if (!session) {
    return <main className="auth-wrap">
      <div className="auth-card">
        <div className="eyebrow">Private Admin</div>
        <h1>SocialMarket AI</h1>
        <p className="sub">Private admin access με email και password.</p>
        <form onSubmit={signIn} className="auth-form">
          <input className="search" type="email" value={ADMIN_EMAIL} readOnly autoComplete="username" aria-label="Admin email" />
          <input className="search" type="password" value={password} onChange={(event)=>setPassword(event.target.value)} placeholder="Password" autoComplete="current-password" required autoFocus />
          <button className="button" type="submit" disabled={signingIn}>{signingIn ? 'Signing in…' : 'Sign in'}</button>
          <button className="link-button" type="button" onClick={()=>window.location.reload()}>Retry session</button>
        </form>
        {message && <p className="muted">{message}</p>}
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
