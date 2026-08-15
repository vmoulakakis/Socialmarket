import { createClient } from '@supabase/supabase-js';
import { APPROVED_ADMIN_EMAIL, APPROVED_PUBLISHABLE_KEY, APPROVED_SUPABASE_URL } from '@/lib/supabase-config';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || APPROVED_SUPABASE_URL;
const supabasePublishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || APPROVED_PUBLISHABLE_KEY;

if (supabaseUrl !== APPROVED_SUPABASE_URL) {
  throw new Error('SocialMarket is configured for the wrong Supabase project. Expected shared project rpfadpdnnxequgvdcfoq.');
}

export const supabase = createClient(supabaseUrl, supabasePublishableKey, {
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
