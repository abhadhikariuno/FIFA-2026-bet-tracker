#!/bin/bash
set -e
sed -i "s|const GOOGLE_CLIENT_ID  = '[^']*'|const GOOGLE_CLIENT_ID  = '${GOOGLE_CLIENT_ID}'|" index.html
sed -i "s|const SUPABASE_URL      = '[^']*'|const SUPABASE_URL      = '${SUPABASE_URL}'|" index.html
sed -i "s|const SUPABASE_ANON_KEY = '[^']*'|const SUPABASE_ANON_KEY = '${SUPABASE_ANON_KEY}'|" index.html
