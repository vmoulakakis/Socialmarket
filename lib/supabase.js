import { createClient } from '@supabase/supabase-js';

const APPROVED_SUPABASE_URL = 'https://rpfadpdnnxequgvdcfoq.supabase.co';
const APPROVED_PUBLISHABLE_KEY = 'sb_publishable_NkMSCtURWbZcA8MCY1H5sA_W_G10WYD';
const APPROVED_ADMIN_EMAIL = 'vmoulakakis@gmail.com';

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
