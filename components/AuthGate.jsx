'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { supabase } from '@/lib/supabase';

const ADMIN_EMAIL = 'vmoulakakis@gmail.com';
const SESSION_TIMEOUT_MS = 6000;
const SIGNIN_TIMEOUT_MS = 12000;

function timeoutResult(ms, value) {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export default function AuthGate({ children }) {
  const pathname = usePathname();
  const publicRoute = pathname === '/marketplace' || pathname?.startsWith('/marketplace/');
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
      setMessage((old) => old || 'Ο έλεγχος session καθυστέρησε. Μπορείς να ζητήσεις νέο magic link.');
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
  }, [publicRoute]);

  async function sendMagicLink(event) {
    event.preventDefault();
    if (signingIn) return;
    setSigningIn(true);
    setMessage('');
    try {
      const redirectTo = typeof window !== 'undefined'
        ? `${window.location.origin}${pathname || '/admin'}`
        : undefined;
      const result = await Promise.race([
        supabase.auth.signInWithOtp({
          email: ADMIN_EMAIL,
          options: {
            shouldCreateUser: false,
            emailRedirectTo: redirectTo,
          },
        }),
        timeoutResult(SIGNIN_TIMEOUT_MS, { timeout: true }),
      ]);
      if (result?.timeout) {
        setMessage('Η αποστολή καθυστέρησε. Έλεγξε το email σου πριν ξαναδοκιμάσεις.');
        setSigningIn(false);
        return;
      }
      if (result?.error) {
        setMessage(result.error.message || 'Αποτυχία αποστολής magic link.');
        setSigningIn(false);
        return;
      }
      setMessage('Magic link στάλθηκε. Άνοιξε το email και πάτησε το link για είσοδο.');
      setSigningIn(false);
    } catch (error) {
      setMessage(error?.message || 'Αποτυχία αποστολής magic link.');
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
        <p className="sub">Passwordless admin access με ασφαλές Supabase Magic Link.</p>
        <form onSubmit={sendMagicLink} className="auth-form">
          <input className="search" type="email" value={ADMIN_EMAIL} readOnly autoComplete="username" aria-label="Admin email" />
          <button className="button" type="submit" disabled={signingIn}>{signingIn ? 'Sending…' : 'Send magic link'}</button>
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
