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

// Defense in depth: this production console accepts only the approved Google identity.
// Any email/password, OTP, magic-link, or other OAuth session is immediately discarded.
if (typeof window !== 'undefined') {
  supabase.auth.onAuthStateChange((_event, session) => {
    if (!session) return;

    const email = String(session.user?.email || '').toLowerCase();
    const provider = String(session.user?.app_metadata?.provider || '').toLowerCase();
    const providers = Array.isArray(session.user?.app_metadata?.providers)
      ? session.user.app_metadata.providers.map((value) => String(value).toLowerCase())
      : [];
    const isGoogle = provider === 'google' || providers.includes('google');
    const isApprovedAdmin = email === APPROVED_ADMIN_EMAIL && isGoogle;

    if (!isApprovedAdmin) {
      // Defer sign-out until the auth callback completes to avoid re-entrant auth events.
      setTimeout(async () => {
        try {
          await supabase.auth.signOut({ scope: 'local' });
        } finally {
          // OAuth implicit flows can place tokens in the URL fragment; remove them immediately.
          if (window.location.hash || window.location.search) {
            window.history.replaceState({}, document.title, window.location.pathname);
          }
        }
      }, 0);
    } else if (window.location.hash) {
      // Keep a successful Google session, but never leave access/refresh tokens in the address bar.
      window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
    }
  });
}
