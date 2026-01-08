# 🔐 SecureChat - End-to-End Encrypted Chat Room

<div align="center">

![Security](https://img.shields.io/badge/Security-E2E%20Encrypted-green)
![Django](https://img.shields.io/badge/Django-5.0-blue)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

**یک سیستم چت روم تحت وب با رمزگذاری End-to-End**

</div>

## 🛡️ ویژگی‌های امنیتی

### رمزگذاری پیشرفته
- **X25519 ECDH** - تبادل کلید امن (همان الگوریتم Signal/WhatsApp)
- **XChaCha20-Poly1305** - رمزگذاری پیام‌ها (AEAD)
- **Argon2id** - هش پسورد (مقاوم در برابر GPU)
- **Perfect Forward Secrecy** - امنیت رو به جلو

### امنیت سیستم
- احراز هویت JWT با توکن‌های کوتاه‌مدت
- محافظت CSRF و XSS
- Rate Limiting برای جلوگیری از حملات Brute Force
- قفل حساب بعد از تلاش‌های ناموفق
- لاگ امنیتی تمام فعالیت‌ها

## 🚀 شروع سریع

### نیازمندی‌ها
- Docker و Docker Compose
- (اختیاری) Python 3.11+ برای توسعه محلی

### راه‌اندازی با Docker

```bash
# کپی فایل environment
cp .env.example .env

# ویرایش متغیرهای محیطی
nano .env

# راه‌اندازی
docker-compose up -d

# مشاهده لاگ‌ها
docker-compose logs -f
```

### دسترسی به اپلیکیشن

- **وب اپلیکیشن:** http://localhost
- **پنل ادمین:** http://localhost/admin
  - Username: `admin`
  - Password: `adminpassword123`

## 📁 ساختار پروژه

```
Messenger/
├── secure_chat/          # تنظیمات اصلی Django
│   ├── settings.py       # تنظیمات امنیتی
│   ├── asgi.py          # WebSocket support
│   └── urls.py
├── accounts/             # مدیریت کاربران
│   ├── models.py        # مدل کاربر امن
│   └── views.py         # احراز هویت
├── chat/                 # سیستم چت
│   ├── models.py        # مدل‌های چت
│   ├── consumers.py     # WebSocket handlers
│   └── views.py
├── encryption/           # ماژول رمزگذاری
│   ├── e2e_crypto.py    # E2E encryption
│   └── key_manager.py   # مدیریت کلیدها
├── templates/            # قالب‌های HTML
├── docker-compose.yml    # Docker configuration
├── Dockerfile
└── nginx.conf           # Reverse proxy
```

## 🔑 نحوه کار رمزگذاری

### ۱. ثبت‌نام کاربر
```
کاربر ← تولید کلید X25519 ← رمزگذاری کلید خصوصی با پسورد ← ذخیره در دیتابیس
```

### ۲. ایجاد اتاق چت
```
ادمین ← تولید کلید اتاق (256-bit) ← رمزگذاری برای هر عضو ← ذخیره
```

### ۳. ارسال پیام
```
کاربر ← نوشتن پیام ← رمزگذاری با کلید اتاق (XChaCha20) ← ارسال به سرور ← 
سرور ← پخش به اعضا ← رمزگشایی در مرورگر
```

## ⚙️ تنظیمات امنیتی مهم

### تغییر کلیدهای پیش‌فرض (ضروری!)

در فایل `.env`:

```env
# حداقل 50 کاراکتر تصادفی
DJANGO_SECRET_KEY=your-super-secret-key-here

# برای JWT
JWT_SECRET_KEY=another-secret-key-here

# کلید رمزگذاری اتاق‌ها
ROOM_KEY_PASSWORD=master-encryption-key

# پسورد دیتابیس
DB_PASSWORD=very-secure-password
```

### فعال‌سازی HTTPS (برای Production)

1. گواهی SSL تهیه کنید (Let's Encrypt)
2. فایل‌ها را در `ssl/` قرار دهید
3. در `nginx.conf` بخش HTTPS را فعال کنید

## 📡 API Endpoints

### احراز هویت
```
POST /api/token/           # دریافت JWT
POST /api/token/refresh/   # بازنوی توکن
```

### چت
```
GET  /api/rooms/                    # لیست اتاق‌ها
GET  /api/rooms/{id}/messages/      # پیام‌های اتاق
WS   /ws/chat/{room_id}/            # WebSocket چت
```

## 🔒 نکات امنیتی مهم

1. **هرگز** کلیدهای پیش‌فرض را در Production استفاده نکنید
2. **حتماً** HTTPS را فعال کنید
3. پسوردها حداقل 12 کاراکتر باشند
4. به‌روزرسانی منظم وابستگی‌ها
5. مانیتورینگ لاگ‌های امنیتی

## 🛠️ توسعه محلی

```bash
# ایجاد virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# نصب وابستگی‌ها
pip install -r requirements.txt

# اجرای migrations
python manage.py migrate

# ایجاد superuser
python manage.py createsuperuser

# اجرای سرور توسعه
python manage.py runserver
```

## 📜 لایسنس

MIT License - آزاد برای استفاده شخصی و تجاری

## 🤝 مشارکت

Pull Request ها خوش‌آمد هستند!

---

<div align="center">

**⚠️ این پروژه برای اهداف آموزشی است. برای استفاده در Production، بررسی امنیتی حرفه‌ای انجام دهید.**

</div>
