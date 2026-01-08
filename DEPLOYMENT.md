# 🚀 آموزش کامل نصب SecureChat روی سرور

## 📋 پیش‌نیازها

- سرور Ubuntu 22.04 یا 24.04 (حداقل 2GB RAM)
- دامنه (اختیاری، برای HTTPS)
- دسترسی SSH به سرور

---

## مرحله ۱: اتصال به سرور

```bash
ssh root@YOUR_SERVER_IP
# یا با کاربر sudo
ssh username@YOUR_SERVER_IP
```

---

## مرحله ۲: به‌روزرسانی سیستم

```bash
# به‌روزرسانی پکیج‌ها
sudo apt update && sudo apt upgrade -y

# نصب ابزارهای ضروری
sudo apt install -y curl git wget nano ufw
```

---

## مرحله ۳: نصب Docker

```bash
# حذف نسخه‌های قدیمی (اگر وجود دارد)
sudo apt remove docker docker-engine docker.io containerd runc 2>/dev/null

# نصب پیش‌نیازها
sudo apt install -y ca-certificates curl gnupg lsb-release

# اضافه کردن کلید GPG رسمی Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# اضافه کردن مخزن Docker
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# نصب Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# اضافه کردن کاربر به گروه docker (برای اجرا بدون sudo)
sudo usermod -aG docker $USER

# فعال‌سازی Docker در استارتاپ
sudo systemctl enable docker
sudo systemctl start docker

# بررسی نصب
docker --version
docker compose version
```

> ⚠️ بعد از اضافه کردن کاربر به گروه docker، یک بار **logout** و دوباره **login** کنید.

---

## مرحله ۴: تنظیم فایروال

```bash
# فعال‌سازی UFW
sudo ufw enable

# باز کردن پورت‌های ضروری
sudo ufw allow ssh          # پورت 22 - SSH
sudo ufw allow http         # پورت 80 - HTTP
sudo ufw allow https        # پورت 443 - HTTPS

# بررسی وضعیت
sudo ufw status
```

---

## مرحله ۵: کلون کردن پروژه

```bash
# ایجاد پوشه برای پروژه‌ها
sudo mkdir -p /var/www
cd /var/www

# کلون از GitHub
git clone https://github.com/YOUR_USERNAME/Messenger.git
cd Messenger

# یا اگر private است:
git clone https://YOUR_TOKEN@github.com/YOUR_USERNAME/Messenger.git
```

---

## مرحله ۶: تنظیم Environment Variables

```bash
# کپی فایل نمونه
cp .env.example .env

# ویرایش فایل
nano .env
```

### محتوای فایل `.env` را به این شکل تغییر دهید:

```env
# Django Settings
DEBUG=False
DJANGO_SECRET_KEY=یک-رشته-تصادفی-بسیار-طولانی-حداقل-50-کاراکتر-اینجا-بنویسید
JWT_SECRET_KEY=یک-رشته-تصادفی-دیگر-برای-jwt-توکن-ها

# Database
DB_NAME=secure_chat
DB_USER=chat_user
DB_PASSWORD=یک-پسورد-قوی-برای-دیتابیس
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PASSWORD=یک-پسورد-قوی-برای-ردیس

# Room Encryption
ROOM_KEY_PASSWORD=کلید-رمزگذاری-اتاق-ها-تغییر-دهید

# Domain - دامنه خود را وارد کنید
DOMAIN=yourdomain.com
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com,YOUR_SERVER_IP
CORS_ORIGINS=http://localhost,https://yourdomain.com
```

### تولید کلید تصادفی امن:

```bash
# روش ۱: با OpenSSL
openssl rand -base64 50

# روش ۲: با Python
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

ذخیره کنید: `Ctrl+X` → `Y` → `Enter`

---

## مرحله ۷: اجرای پروژه

```bash
# ساخت و اجرای کانتینرها
docker compose up -d --build

# بررسی وضعیت کانتینرها
docker compose ps

# مشاهده لاگ‌ها
docker compose logs -f
```

### خروجی مورد انتظار:
```
NAME                  STATUS    PORTS
secure_chat_db        running   5432/tcp
secure_chat_redis     running   6379/tcp
secure_chat_web       running   8000/tcp
secure_chat_nginx     running   0.0.0.0:80->80/tcp
```

---

## مرحله ۸: بررسی عملکرد

```bash
# تست HTTP
curl http://localhost

# یا از مرورگر
http://YOUR_SERVER_IP
```

---

## مرحله ۹: نصب SSL با Let's Encrypt (رایگان)

### ۹.۱ نصب Certbot

```bash
sudo apt install -y certbot
```

### ۹.۲ توقف موقت Nginx

```bash
docker compose stop nginx
```

### ۹.۳ دریافت گواهی SSL

```bash
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
```

### ۹.۴ کپی گواهی‌ها به پروژه

```bash
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./ssl/
sudo chown $USER:$USER ./ssl/*.pem
```

### ۹.۵ فعال‌سازی HTTPS در Nginx

فایل `nginx.conf` را ویرایش کنید:

```bash
nano nginx.conf
```

بخش زیر را از حالت کامنت خارج کنید (خط‌های آخر فایل):

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    # ... بقیه تنظیمات
}
```

### ۹.۶ ری‌استارت

```bash
docker compose up -d --build
```

### ۹.۷ تنظیم تمدید خودکار SSL

```bash
# ایجاد اسکریپت تمدید
sudo nano /etc/cron.d/certbot-renew
```

محتوا:
```
0 3 * * * root certbot renew --quiet && cp /etc/letsencrypt/live/yourdomain.com/*.pem /var/www/Messenger/ssl/ && docker compose -f /var/www/Messenger/docker-compose.yml restart nginx
```

---

## مرحله ۱۰: تغییر پسورد ادمین

```bash
# ورود به کانتینر
docker compose exec web python manage.py changepassword admin
```

---

## 🔧 دستورات مفید

### مدیریت کانتینرها

```bash
# مشاهده وضعیت
docker compose ps

# توقف همه
docker compose down

# ری‌استارت
docker compose restart

# ری‌استارت یک سرویس
docker compose restart web

# مشاهده لاگ یک سرویس
docker compose logs -f web
```

### مدیریت دیتابیس

```bash
# پشتیبان‌گیری
docker compose exec db pg_dump -U chat_user secure_chat > backup_$(date +%Y%m%d).sql

# بازیابی
cat backup.sql | docker compose exec -T db psql -U chat_user secure_chat
```

### به‌روزرسانی پروژه

```bash
cd /var/www/Messenger

# دریافت تغییرات از GitHub
git pull origin main

# ساخت مجدد
docker compose up -d --build
```

### ایجاد کاربر ادمین جدید

```bash
docker compose exec web python manage.py createsuperuser
```

---

## 🔍 عیب‌یابی

### مشکل: کانتینر web ری‌استارت می‌شود

```bash
# بررسی لاگ
docker compose logs web

# معمولاً مشکل از متغیرهای محیطی یا دیتابیس است
```

### مشکل: خطای دیتابیس

```bash
# بررسی اتصال
docker compose exec web python manage.py dbshell

# اجرای مجدد migrations
docker compose exec web python manage.py migrate
```

### مشکل: WebSocket کار نمی‌کند

```bash
# بررسی Redis
docker compose exec redis redis-cli ping
# باید PONG برگرداند

# بررسی لاگ
docker compose logs web | grep -i websocket
```

### مشکل: صفحه سفید یا 502

```bash
# بررسی Nginx
docker compose logs nginx

# بررسی web
docker compose logs web
```

---

## 📊 مانیتورینگ

### استفاده از منابع

```bash
docker stats
```

### فضای دیسک

```bash
docker system df
```

### پاکسازی فضا

```bash
# پاکسازی کانتینرهای متوقف و image های بلااستفاده
docker system prune -a
```

---

## 🔐 چک‌لیست امنیتی

- [ ] کلیدهای `.env` را تغییر داده‌اید
- [ ] پسورد ادمین را تغییر داده‌اید
- [ ] SSL فعال است
- [ ] فایروال تنظیم شده
- [ ] پورت‌های غیرضروری بسته است
- [ ] پشتیبان‌گیری خودکار فعال است

---

## 💡 نکات تکمیلی

### استفاده از Cloudflare (توصیه می‌شود)

1. دامنه را به Cloudflare اضافه کنید
2. DNS را به IP سرور تنظیم کنید
3. SSL را روی "Full (Strict)" بگذارید
4. حفاظت DDoS خودکار فعال می‌شود

### پشتیبان‌گیری خودکار روزانه

```bash
# ایجاد اسکریپت
sudo nano /opt/backup-chat.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/secure_chat"
DATE=$(date +%Y%m%d_%H%M)
mkdir -p $BACKUP_DIR

# پشتیبان از دیتابیس
docker compose -f /var/www/Messenger/docker-compose.yml exec -T db pg_dump -U chat_user secure_chat > $BACKUP_DIR/db_$DATE.sql

# حذف پشتیبان‌های قدیمی‌تر از ۷ روز
find $BACKUP_DIR -type f -mtime +7 -delete
```

```bash
sudo chmod +x /opt/backup-chat.sh

# اضافه به cron
sudo crontab -e
# اضافه کنید:
0 2 * * * /opt/backup-chat.sh
```

---

## ✅ تمام!

اپلیکیشن شما الان باید در آدرس زیر در دسترس باشد:

- **HTTP:** `http://YOUR_SERVER_IP`
- **HTTPS:** `https://yourdomain.com`

برای ورود:
- آدرس: `/accounts/login/`
- پنل ادمین: `/admin/`
