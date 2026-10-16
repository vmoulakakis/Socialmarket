import { supabase } from '@/lib/supabase';

export async function workspace(section = 'overview', options = {}) {
  const { data, error } = await supabase.rpc('socialmarket_workspace', {
    p_section: section,
    p_query: options.query || '',
    p_limit: options.limit || 100,
    p_offset: options.offset || 0,
    p_id: options.id || null,
  });
  if (error) throw new Error(error.message);
  return data;
}
