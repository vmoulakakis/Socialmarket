'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

const ADMIN_EMAIL = 'vmoulakakis@gmail.com';

export default function AuthGate({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [signingIn, setSigningIn] = useState(false);

  useEffect(() => {
    let mounted = true;

    const acceptSession = async (nextSession) => {
      if (!mounted) return;

      if (!nextSession) {
        setSession(null);
        setLoading(false);
        return;
      }

      const email = String(nextSession.user?.email || '').toLowerCase();
      if (email !== ADMIN_EMAIL) {
        await supabase.auth.signOut({ scope: 'local' });
        if (mounted) {
          setSession(null);
          setMessage('Δεν επιτρέπεται πρόσβαση σε αυτόν τον λογαριασμό.');
          setLoading(false);
        }
        return;
      }

      setSession(nextSession);
      setLoading(false);
    };

    supabase.auth.getSession().then(({ data }) => acceptSession(data.session ?? null));
    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      void acceptSession(nextSession ?? null);
    });

    return () => {
      mounted = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  async function signIn(event) {
    event.preventDefault();
    if (!password) return;
    setSigningIn(true);
    setMessage('');

    const { error } = await supabase.auth.signInWithPassword({
      email: ADMIN_EMAIL,
      password,
    });

    if (error) {
      setMessage(error.message === 'Invalid login credentials' ? 'Λάθος password.' : error.message);
      setSigningIn(false);
      return;
    }

    setPassword('');
    setSigningIn(false);
  }

  async function signOut() {
    await supabase.auth.signOut();
    setSession(null);
    setPassword('');
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
