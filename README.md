# IntelliCode API

## Setup

```bash
# Create and activate conda environment
conda env create -f environment.yml
conda activate intellicode

# Run server
python run.py
```

## Routes Documentation

### Authentication Routes

#### POST /auth/register
Register a new user account.

**Request:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "secure_password123"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user_id": "users/123456"
}
```

#### POST /auth/login
Login user and receive JWT token.

**Request:**
```json
{
  "email": "john@example.com",
  "password": "secure_password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### POST /auth/token
OAuth2 compatible token endpoint.

**Request:** (form-data)
```
username: john@example.com
password: secure_password123
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### GET /auth/me
Get current authenticated user information.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "_key": "123456",
  "email": "john@example.com",
  "name": "John Doe",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": null,
  "skill_level": null,
  "onboarding_completed": false
}
```

### General Routes

#### GET /
API information and health status.

**Response:**
```json
{
  "message": "IntelliCode API",
  "version": "1.0.0",
  "docs": "/docs",
  "status": "healthy"
}
```
