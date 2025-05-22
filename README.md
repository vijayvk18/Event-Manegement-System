# Event Management System

A robust Django-based Event Management System with real-time features, RESTful API, and rate limiting.

## Features

- User authentication and authorization using JWT
- Event creation, management, and registration
- Real-time updates using WebSocket
- RESTful API with comprehensive documentation
- Rate limiting for API endpoints
- Redis caching for improved performance
- PostgreSQL database
- CORS support
- API filtering, searching, and pagination

## Prerequisites

- Python 3.8+
- PostgreSQL
- Redis
- Virtual Environment (recommended)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd event-management-system
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following variables:
```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=event_management
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
REDIS_HOST=localhost
REDIS_PORT=6379
CORS_ALLOWED_ORIGINS=http://localhost:3000
# Rate Limiting Configuration
ANON_RATE_LIMIT=10  # Number of requests per minute for anonymous users
USER_RATE_LIMIT=60  # Number of requests per minute for authenticated users
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Run the development server:
```bash
python manage.py runserver
```

## API Documentation

The API documentation is available at `/swagger/` and `/redoc/` endpoints when the server is running.

## Rate Limiting

The API implements rate limiting to prevent abuse:
- Anonymous users: 10 requests per minute
- Authenticated users: 60 requests per minute

These limits can be configured through environment variables `ANON_RATE_LIMIT` and `USER_RATE_LIMIT` in the `.env` file.

## Project Structure

```
event_management_system/
├── core/                 # Core functionality and user management
├── events/              # Event-related functionality
├── event_management_system/  # Project settings and configuration
├── manage.py
├── requirements.txt
└── README.md
```
