'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

const ADMIN_EMAIL = 'vmoulakakis@gmail.com';

export default function AuthGate({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

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
      const provider = String(nextSession.user?.app_metadata?.provider || '').toLowerCase();
      const providers = Array.isArray(nextSession.user?.app_metadata?.providers)
        ? nextSession.user.app_metadata.providers.map((value) => String(value).toLowerCase())
        : [];
      const isGoogle = provider === 'google' || providers.includes('google');
      const isApprovedAdmin = email === ADMIN_EMAIL && isGoogle;

      if (!isApprovedAdmin) {
        await supabase.auth.signOut({ scope: 'local' });
        if (mounted) {
          setSession(null);
          setMessage('Η πρόσβαση επιτρέπεται μόνο μέσω Google με το εγκεκριμένο admin account.');
          setLoading(false);
        }
        return;
      }

      if (window.location.hash || window.location.search) {
        window.history.replaceState({}, document.title, window.location.pathname);
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

  async function signInWithGoogle() {
    setMessage('');

    const redirectTo = window.location.origin;
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo,
        queryParams: {
          prompt: 'select_account',
        },
      },
    });

    if (error) setMessage(error.message);
  }

  async function signOut() {
    await supabase.auth.signOut();
    setSession(null);
  }

  if (loading) {
    return <div className="auth-card"><div className="eyebrow">Private Admin</div><h2>Έλεγχος πρόσβασης…</h2></div>;
  }

  if (!session) {
    return <main className="auth-wrap">
      <div className="auth-card">
        <div className="eyebrow">Private Admin</div>
        <h1>SocialMarket AI</h1>
        <p className="sub">Η βάση, τα market signals, τα HIGO scores και τα creatives είναι διαθέσιμα μόνο στο εγκεκριμένο Google admin account.</p>
        <button className="button" type="button" onClick={signInWithGoogle}>Continue with Google</button>
        <p className="muted">Μόνο {ADMIN_EMAIL} μέσω Google OAuth.</p>
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
