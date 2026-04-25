#!/usr/bin/env bash
# Bootstrap Let's Encrypt cert for chirri.impactia.ai + media.chirri.impactia.ai.
#
# Catch-22: nginx config references the cert files; nginx won't start
# without them; we can't issue the cert without nginx serving HTTP-01.
# Solution: drop a self-signed dummy cert, start nginx, run certbot via
# webroot, then replace the dummy with the real cert.
#
# Idempotent: skips re-issue if a real cert already exists for the domain.
set -euo pipefail

DOMAINS=(chirri.impactia.ai media.chirri.impactia.ai)
PRIMARY="${DOMAINS[0]}"
EMAIL="${LETSENCRYPT_EMAIL:-hello@impactia.ai}"
STAGING="${STAGING:-0}"
LE_PATH="/etc/letsencrypt"

cd "$(dirname "$0")/.."

if [ -d "${LE_PATH}/live/${PRIMARY}" ] && \
   sudo openssl x509 -in "${LE_PATH}/live/${PRIMARY}/fullchain.pem" -noout -issuer 2>/dev/null \
   | grep -q "Let's Encrypt"; then
  echo "[init-letsencrypt] real cert already exists for ${PRIMARY}, skipping issue"
  echo "[init-letsencrypt] starting nginx + certbot renewal loop"
  docker compose -f docker-compose.prod.yml up -d nginx certbot
  exit 0
fi

echo "[init-letsencrypt] preparing dummy self-signed cert so nginx can boot"
sudo mkdir -p "${LE_PATH}/live/${PRIMARY}"
sudo mkdir -p /var/www/certbot

sudo openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
  -keyout "${LE_PATH}/live/${PRIMARY}/privkey.pem" \
  -out    "${LE_PATH}/live/${PRIMARY}/fullchain.pem" \
  -subj "/CN=${PRIMARY}" 2>/dev/null

echo "[init-letsencrypt] starting nginx with dummy cert"
docker compose -f docker-compose.prod.yml up -d nginx

# Allow nginx a moment to bind ports
sleep 3

echo "[init-letsencrypt] removing dummy cert files (certbot needs the dir empty)"
sudo rm -rf "${LE_PATH}/live/${PRIMARY}" \
            "${LE_PATH}/archive/${PRIMARY}" \
            "${LE_PATH}/renewal/${PRIMARY}.conf"

CERTBOT_FLAGS=(
  "certonly" "--webroot" "-w" "/var/www/certbot"
  "--email" "${EMAIL}" "--agree-tos" "--no-eff-email"
  "--non-interactive"
)
if [ "$STAGING" = "1" ]; then
  CERTBOT_FLAGS+=("--staging")
fi
for d in "${DOMAINS[@]}"; do
  CERTBOT_FLAGS+=("-d" "$d")
done

echo "[init-letsencrypt] requesting real cert via certbot"
docker compose -f docker-compose.prod.yml run --rm --entrypoint "certbot ${CERTBOT_FLAGS[*]}" certbot

echo "[init-letsencrypt] reloading nginx with real cert"
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

echo "[init-letsencrypt] starting certbot renewal loop"
docker compose -f docker-compose.prod.yml up -d certbot

echo "[init-letsencrypt] DONE — cert active for: ${DOMAINS[*]}"
