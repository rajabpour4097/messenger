#!/bin/bash

#################################################
# SSL Setup Script for SecureChat
# استفاده: ./setup-ssl.sh yourdomain.com
#################################################

set -e

DOMAIN=$1

if [ -z "$DOMAIN" ]; then
    echo "Usage: ./setup-ssl.sh yourdomain.com"
    exit 1
fi

echo "🔐 Setting up SSL for $DOMAIN"

# Install certbot
echo "[*] Installing Certbot..."
sudo apt install -y certbot

# Stop nginx temporarily
echo "[*] Stopping Nginx..."
docker compose stop nginx

# Get certificate
echo "[*] Obtaining SSL certificate..."
sudo certbot certonly --standalone -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

# Copy certificates
echo "[*] Copying certificates..."
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ./ssl/
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ./ssl/
sudo chown $USER:$USER ./ssl/*.pem

# Update .env with domain
echo "[*] Updating configuration..."
sed -i "s|DOMAIN=.*|DOMAIN=$DOMAIN|g" .env
sed -i "s|ALLOWED_HOSTS=.*|ALLOWED_HOSTS=localhost,127.0.0.1,$DOMAIN|g" .env
sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=http://localhost,https://$DOMAIN|g" .env

# Restart containers
echo "[*] Restarting containers..."
docker compose up -d --build

# Setup auto-renewal
echo "[*] Setting up auto-renewal..."
CRON_CMD="0 3 * * * certbot renew --quiet --post-hook 'cp /etc/letsencrypt/live/$DOMAIN/*.pem $(pwd)/ssl/ && docker compose -f $(pwd)/docker-compose.yml restart nginx'"
(crontab -l 2>/dev/null | grep -v "certbot renew"; echo "$CRON_CMD") | crontab -

echo ""
echo "✅ SSL setup complete!"
echo "🌐 Your site is now available at: https://$DOMAIN"
echo ""
