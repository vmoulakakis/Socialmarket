import { createClient } from '@supabase/supabase-js';

const APPROVED_SUPABASE_URL = 'https://rpfadpdnnxequgvdcfoq.supabase.co';
const APPROVED_PUBLISHABLE_KEY = 'sb_publishable_NkMSCtURWbZcA8MCY1H5sA_W_G10WYD';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || APPROVED_SUPABASE_URL;
const supabasePublishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || APPROVED_PUBLISHABLE_KEY;

if (supabaseUrl !== APPROVED_SUPABASE_URL) {
  throw new Error('SocialMarket is configured for the wrong Supabase project. Expected shared project rpfadpdnnxequgvdcfoq.');
}

export const supabase = createClient(supabaseUrl, supabasePublishableKey, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
});
