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
  const [newPassword, setNewPassword] = useState('');
  const [recoveryFlow, setRecoveryFlow] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (publicRoute) {
      setLoading(false);
      return undefined;
    }

    let mounted = true;
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      const hashParams = new URLSearchParams(url.hash.slice(1));
      if (url.searchParams.get('resetPassword') === '1' || hashParams.get('type') === 'recovery') {
        setRecoveryFlow(true);
      }
      const authError = hashParams.get('error_description');
      if (authError) setMessage('Ο σύνδεσμος επαναφοράς δεν είναι έγκυρος ή έχει λήξει. Ζήτησε νέο σύνδεσμο.');
    }

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

    const { data: listener } = supabase.auth.onAuthStateChange((event, nextSession) => {
      if (event === 'PASSWORD_RECOVERY') setRecoveryFlow(true);
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
    if (busy) return;
    setBusy(true);
    setMessage('');
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email: ADMIN_EMAIL,
        password,
      });
      if (error) {
        setMessage('Δεν ήταν δυνατή η σύνδεση. Έλεγξε τον κωδικό ή χρησιμοποίησε την επαναφορά κωδικού.');
        setBusy(false);
        return;
      }
      setPassword('');
      setBusy(false);
    } catch {
      setMessage('Παρουσιάστηκε σφάλμα σύνδεσης. Δοκίμασε ξανά.');
      setBusy(false);
    }
  }

  async function sendPasswordReset() {
    if (busy) return;
    setBusy(true);
    setMessage('');
    try {
      const redirectTo = typeof window !== 'undefined'
        ? `${window.location.origin}${pathname || '/admin'}?resetPassword=1`
        : undefined;
      const { error } = await supabase.auth.resetPasswordForEmail(ADMIN_EMAIL, { redirectTo });
      const rateLimited = error && (
        error.status === 429
        || error.code === 'over_email_send_rate_limit'
        || /rate limit|too many requests/i.test(error.message || '')
      );
      setMessage(error
        ? rateLimited
          ? 'Το όριο αποστολής email επαναφοράς του Supabase έφτασε τα 2 email/ώρα. Περίμενε περίπου μία ώρα από την τελευταία αποστολή και δοκίμασε μία φορά.'
          : 'Δεν στάλθηκε email επαναφοράς. Έλεγξε τη ρύθμιση αποστολής email του Supabase.'
        : `Στάλθηκε σύνδεσμος επαναφοράς στο ${ADMIN_EMAIL}. Άνοιξέ τον και όρισε νέο κωδικό.`);
    } catch {
      setMessage('Δεν στάλθηκε email επαναφοράς. Δοκίμασε ξανά.');
    } finally {
      setBusy(false);
    }
  }

  async function updatePassword(event) {
    event.preventDefault();
    if (busy) return;
    if (newPassword.length < 8) {
      setMessage('Ο νέος κωδικός πρέπει να έχει τουλάχιστον 8 χαρακτήρες.');
      return;
    }
    setBusy(true);
    setMessage('');
    try {
      const { error } = await supabase.auth.updateUser({ password: newPassword });
      if (error) {
        setMessage('Δεν έγινε αλλαγή κωδικού. Ο σύνδεσμος επαναφοράς μπορεί να έχει λήξει· ζήτησε νέο.');
        setBusy(false);
        return;
      }
      setNewPassword('');
      setRecoveryFlow(false);
      setMessage('Ο νέος κωδικός αποθηκεύτηκε. Έχεις συνδεθεί.');
      if (typeof window !== 'undefined') {
        window.history.replaceState({}, '', pathname || '/admin');
      }
      setBusy(false);
    } catch {
      setMessage('Παρουσιάστηκε σφάλμα. Ζήτησε νέο σύνδεσμο επαναφοράς.');
      setBusy(false);
    }
  }

  async function signOut() {
    try {
      await Promise.race([supabase.auth.signOut(), timeoutResult(5000, null)]);
    } finally {
      setSession(null);
      setPassword('');
      setNewPassword('');
    }
  }

  if (publicRoute) return children;

  if (loading) {
    return <div className="auth-card"><div className="eyebrow">Private Admin</div><h2>Έλεγχος πρόσβασης…</h2></div>;
  }

  if (recoveryFlow && session) {
    return <main className="auth-wrap">
      <div className="auth-card">
        <div className="eyebrow">Password recovery</div>
        <h1>Όρισε νέο κωδικό</h1>
        <p className="sub">Ο σύνδεσμος επαλήθευσε τον λογαριασμό {ADMIN_EMAIL}. Διάλεξε έναν νέο κωδικό τουλάχιστον 8 χαρακτήρων.</p>
        <form onSubmit={updatePassword} className="auth-form">
          <input
            className="search"
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            placeholder="Νέος κωδικός"
            autoComplete="new-password"
            minLength={8}
            required
            aria-label="Νέος κωδικός"
          />
          <button className="button" type="submit" disabled={busy || newPassword.length < 8}>
            {busy ? 'Αποθήκευση…' : 'Αποθήκευση νέου κωδικού'}
          </button>
        </form>
        {message && <p className="muted" role="alert">{message}</p>}
      </div>
    </main>;
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
          <button className="button" type="submit" disabled={busy || !password}>
            {busy ? 'Σύνδεση…' : 'Σύνδεση'}
          </button>
          <button className="link-button" type="button" onClick={sendPasswordReset} disabled={busy}>
            {busy ? 'Περίμενε…' : 'Ξέχασα τον κωδικό'}
          </button>
          <p className="muted">Επιτρέπεται μόνο ο λογαριασμός <strong>{ADMIN_EMAIL}</strong>.</p>
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
