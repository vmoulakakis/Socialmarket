'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

export default function AuthGate({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session ?? null);
      setLoading(false);
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession ?? null);
      setLoading(false);
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  async function sendMagicLink(event) {
    event.preventDefault();
    setMessage('');
    const clean = email.trim().toLowerCase();
    if (!clean) return;
    const { error } = await supabase.auth.signInWithOtp({
      email: clean,
      options: { emailRedirectTo: window.location.origin }
    });
    setMessage(error ? error.message : 'Σου έστειλα ασφαλές magic link. Άνοιξέ το από το email σου.');
  }

  if (loading) return <div className="auth-card"><div className="eyebrow">Private Admin</div><h2>Έλεγχος πρόσβασης…</h2></div>;

  if (!session) {
    return <main className="auth-wrap">
      <div className="auth-card">
        <div className="eyebrow">Private Admin</div>
        <h1>SocialMarket AI</h1>
        <p className="sub">Η βάση, τα market signals, τα HIGO scores και τα creatives είναι διαθέσιμα μόνο στο εγκεκριμένο admin account.</p>
        <form onSubmit={sendMagicLink} className="auth-form">
          <input className="search" type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="Admin email" autoComplete="email" required />
          <button className="button" type="submit">Send magic link</button>
        </form>
        {message && <p className="muted">{message}</p>}
      </div>
    </main>;
  }

  return <>
    <div className="admin-session"><span className="muted">{session.user.email}</span><button className="link-button" onClick={()=>supabase.auth.signOut()}>Sign out</button></div>
    {children}
  </>;
}
