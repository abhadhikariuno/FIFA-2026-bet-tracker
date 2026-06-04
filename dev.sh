#!/bin/bash
# Local dev server — injects credentials and serves on localhost:8080
set -a; source .env; set +a

cp index.html index.dev.html

sed -i "s|const GOOGLE_CLIENT_ID   = '[^']*'|const GOOGLE_CLIENT_ID   = '${GOOGLE_CLIENT_ID}'|" index.dev.html
sed -i "s|const SUPABASE_URL       = '[^']*'|const SUPABASE_URL       = '${SUPABASE_URL}'|" index.dev.html
sed -i "s|const SUPABASE_ANON_KEY  = '[^']*'|const SUPABASE_ANON_KEY  = '${SUPABASE_ANON_KEY}'|" index.dev.html
sed -i "s|const EMAILJS_SERVICE_ID  = '[^']*'|const EMAILJS_SERVICE_ID  = '${EMAILJS_SERVICE_ID}'|" index.dev.html
sed -i "s|const EMAILJS_TEMPLATE_ID = '[^']*'|const EMAILJS_TEMPLATE_ID = '${EMAILJS_TEMPLATE_ID}'|" index.dev.html
sed -i "s|const EMAILJS_PUBLIC_KEY  = '[^']*'|const EMAILJS_PUBLIC_KEY  = '${EMAILJS_PUBLIC_KEY}'|" index.dev.html

cp index.dev.html index.html.bak 2>/dev/null || true

echo "Opening http://localhost:8080"
python3 -m http.server 8080
