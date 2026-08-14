import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabasePublishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

if (!supabaseUrl || !supabasePublishableKey) {
  throw new Error('SocialMarket requires NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY. No fallback database is allowed.');
}

if (!supabaseUrl.includes('rpfadpdnnxequgvdcfoq.supabase.co')) {
  throw new Error('SocialMarket is configured for the wrong Supabase project. Expected shared project rpfadpdnnxequgvdcfoq.');
}

export const supabase = createClient(supabaseUrl, supabasePublishableKey, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
});
