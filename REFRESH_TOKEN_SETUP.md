# Refresh Token Implementation

## What Was Added

### Backend Changes:

1. **Config (`app/core/config.py`)**:
   - Added `REFRESH_SECRET_KEY` for signing refresh tokens
   - Added `REFRESH_TOKEN_EXPIRE_DAYS` (default: 7 days)

2. **Security (`app/core/security.py`)**:
   - Added `create_refresh_token()` function
   - Updated `verify_token()` to support both access and refresh tokens

3. **Schemas (`app/schemas/user.py`)**:
   - Updated `Token` model to include `refresh_token`
   - Added `TokenRefresh` model for refresh endpoint

4. **Auth Endpoints (`app/api/v1/endpoints/auth.py`)**:
   - Updated `/login` to return both `access_token` and `refresh_token`
   - Added `/refresh` endpoint to refresh access tokens

### Frontend Changes:

1. **API Client (`src/lib/api.ts`)**:
   - Stores both `access_token` and `refresh_token` in localStorage
   - Automatically refreshes access token on 401 errors
   - Handles token refresh transparently

2. **Auth Context (`src/context/AuthContext.tsx`)**:
   - Updated to store and use both tokens
   - Automatically attempts token refresh on app load if access token is expired

## Environment Variables

Add to your `.env` file:

```env
REFRESH_SECRET_KEY=your-refresh-secret-key-here-change-this-in-production
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## How It Works

1. **Login**: User logs in and receives both access token (30 min) and refresh token (7 days)
2. **API Calls**: Access token is used for authenticated requests
3. **Token Expiry**: When access token expires (401 error), frontend automatically uses refresh token to get new tokens
4. **Refresh Endpoint**: `/api/v1/auth/refresh` accepts refresh token and returns new access + refresh tokens

## Security Features

- Refresh tokens are signed with a separate secret key
- Refresh tokens have longer expiration (7 days vs 30 minutes)
- Refresh tokens are rotated on each refresh (new refresh token issued)
- Invalid refresh tokens result in logout

## API Endpoints

- `POST /api/v1/auth/login` - Returns `{access_token, refresh_token, token_type}`
- `POST /api/v1/auth/refresh` - Accepts `{refresh_token}`, returns `{access_token, refresh_token, token_type}`
- `GET /api/v1/auth/me` - Uses access token for authentication

