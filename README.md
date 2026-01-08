# Kenang Backend API

Backend service untuk Kenang - Platform preservasi memori untuk Indonesia.

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+ dengan SQLAlchemy 2.0 (async)
- **Auth**: Phone OTP (Fazpass) + JWT
- **Cache**: Redis
- **Background Jobs**: Celery
- **Storage**: AWS S3 (ap-southeast-1)
- **AI**: OpenAI Whisper (transcription)
- **Payments**: Midtrans (GoPay, OVO, DANA)

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis
- Docker & Docker Compose (optional)

### Installation

```bash
# Clone repository
git clone git@github.com:alfikri-rizky/Kenang-BE.git
cd Kenang-BE

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env dengan konfigurasi yang sesuai

# Start services (Docker)
docker-compose up -d

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

## API Documentation

Server akan running di `http://localhost:8000`

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Project Structure

```
Kenang-BE/
├── alembic/                # Database migrations
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth/       # Authentication endpoints
│   │   │   ├── users/      # User management
│   │   │   ├── circles/    # Circle management (core feature)
│   │   │   ├── photos/     # Photo management
│   │   │   ├── stories/    # Story/voice recording
│   │   │   ├── ai/         # AI prompts & transcription
│   │   │   └── subscriptions/  # Payment & subscriptions
│   │   └── deps.py         # FastAPI dependencies
│   ├── core/
│   │   ├── config.py       # Settings & configuration
│   │   ├── security.py     # JWT utilities
│   │   ├── exceptions.py   # Custom exceptions
│   │   └── logging.py      # Structured logging
│   ├── db/
│   │   ├── models/         # SQLAlchemy models
│   │   ├── base.py         # Base model & mixins
│   │   └── session.py      # Database session
│   ├── services/           # Business logic layer
│   ├── tasks/              # Celery background tasks
│   └── main.py             # FastAPI application
├── tests/                  # Test files
├── docker-compose.yml      # Local development services
├── requirements.txt        # Python dependencies
└── .env.example            # Environment template
```

## Development Commands

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app

# Format code
black .
isort .

# Lint
flake8 app/
mypy app/

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Environment Variables

Key environment variables (see `.env.example` for complete list):

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/kenang

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# AWS S3
AWS_REGION=ap-southeast-1
S3_BUCKET_NAME=kenang-prod

# Fazpass (OTP)
FAZPASS_API_KEY=your-api-key
FAZPASS_GATEWAY_KEY=your-gateway-key

# Midtrans (Payments)
MIDTRANS_SERVER_KEY=your-server-key
MIDTRANS_CLIENT_KEY=your-client-key

# OpenAI (Whisper)
OPENAI_API_KEY=your-api-key
```

## Implemented Features

### Phase 1: Database Models ✅
- User, OTPCode
- Circle, CircleMembership, CircleMember
- Photo, PhotoTag
- Story
- Subscription, Payment
- Invite, Notification, TimeCapsule

### Phase 2: Auth Module ✅
- `POST /api/v1/auth/request-otp` - Send OTP
- `POST /api/v1/auth/verify-otp` - Verify OTP & get tokens
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout

### Phase 3: Users Module ✅
- `GET /api/v1/users/me` - Get profile
- `PATCH /api/v1/users/me` - Update profile
- `DELETE /api/v1/users/me` - Delete account
- `GET /api/v1/users/me/stats` - Get usage statistics

### Phase 4: Circles Module ✅
- `POST /api/v1/circles` - Create circle
- `GET /api/v1/circles` - List circles
- `GET /api/v1/circles/{id}` - Get circle detail
- `PATCH /api/v1/circles/{id}` - Update circle
- `DELETE /api/v1/circles/{id}` - Delete circle
- `GET /api/v1/circles/{id}/members` - List members
- `POST /api/v1/circles/{id}/members` - Add member
- `PATCH /api/v1/circles/{id}/members/{member_id}` - Update role
- `DELETE /api/v1/circles/{id}/members/{member_id}` - Remove member
- `POST /api/v1/circles/{id}/invites` - Create invite
- `POST /api/v1/circles/join` - Join via invite
- `POST /api/v1/circles/{id}/leave` - Leave circle

## Circle Types

Kenang supports 7 circle types:

- 👨‍👩‍👧 **Keluarga** (Family) - Nuclear & extended family
- 💑 **Pasangan** (Couple) - Romantic relationships
- 👫 **Sahabat** (Friends) - Close friendships
- 💼 **Rekan Kerja** (Colleagues) - Work relationships
- 🎯 **Komunitas** (Community) - Groups & organizations
- 🎓 **Mentor** - Mentor/mentee relationships
- 📔 **Pribadi** (Personal) - Private/solo journaling

## Subscription Tiers

| Tier | Circles | Photos | Stories | Price |
|------|---------|--------|---------|-------|
| Free | 3 | 50 | 10 | Rp 0 |
| Personal | 10 | 200 | Unlimited | Rp 29.000/mo |
| Plus | 25 | 1000 | Unlimited | Rp 69.000/mo |
| Premium | Unlimited | Unlimited | Unlimited | Rp 149.000/mo |

## License

Proprietary - All rights reserved

## Contact

For questions or support, contact the development team.
