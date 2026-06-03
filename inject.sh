#!/bin/bash
set -e
sed -i "s|const GOOGLE_CLIENT_ID   = '[^']*'|const GOOGLE_CLIENT_ID   = '${GOOGLE_CLIENT_ID}'|" index.html
sed -i "s|const SUPABASE_URL       = '[^']*'|const SUPABASE_URL       = '${SUPABASE_URL}'|" index.html
sed -i "s|const SUPABASE_ANON_KEY  = '[^']*'|const SUPABASE_ANON_KEY  = '${SUPABASE_ANON_KEY}'|" index.html
sed -i "s|const EMAILJS_SERVICE_ID  = '[^']*'|const EMAILJS_SERVICE_ID  = '${EMAILJS_SERVICE_ID}'|" index.html
sed -i "s|const EMAILJS_TEMPLATE_ID = '[^']*'|const EMAILJS_TEMPLATE_ID = '${EMAILJS_TEMPLATE_ID}'|" index.html
sed -i "s|const EMAILJS_PUBLIC_KEY  = '[^']*'|const EMAILJS_PUBLIC_KEY  = '${EMAILJS_PUBLIC_KEY}'|" index.html
