import { createClient } from '@supabase/supabase-js';
import { APPROVED_ADMIN_EMAIL, APPROVED_PUBLISHABLE_KEY, APPROVED_SUPABASE_URL } from '@/lib/supabase-config';

// The browser/client layer has one canonical database: VMDB.
// Public Supabase URL/publishable key are intentionally pinned here so a stale
// Vercel Preview env cannot silently route traffic back to a legacy project.
const configuredUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
if (configuredUrl && configuredUrl !== APPROVED_SUPABASE_URL) {
  console.warn('Ignoring stale NEXT_PUBLIC_SUPABASE_URL; SocialMarket is pinned to shared VMDB.');
}

export const supabase = createClient(APPROVED_SUPABASE_URL, APPROVED_PUBLISHABLE_KEY, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});

// Defense in depth: only the approved admin email may remain signed in.
if (typeof window !== 'undefined') {
  supabase.auth.onAuthStateChange((_event, session) => {
    if (!session) return;

    const email = String(session.user?.email || '').toLowerCase();
    if (email !== APPROVED_ADMIN_EMAIL) {
      setTimeout(() => {
        void supabase.auth.signOut({ scope: 'local' });
      }, 0);
    }
  });
}
