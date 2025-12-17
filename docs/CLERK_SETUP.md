# Clerk Authentication Setup Guide

## Overview

MinouChat uses Clerk for authentication. You need to set up a Clerk account and configure the API keys.

## Step 1: Create a Clerk Account

1. Go to [https://clerk.com](https://clerk.com)
2. Sign up for a free account
3. Create a new application

## Step 2: Get Your API Keys

1. In your Clerk dashboard, go to **API Keys**
2. You'll find two keys:
   - **Publishable Key** (starts with `pk_test_` or `pk_live_`)
   - **Secret Key** (starts with `sk_test_` or `sk_live_`)

## Step 3: Configure Environment Variables

Update your `.env` file with your Clerk keys:

```bash
# Clerk Authentication
CLERK_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
CLERK_SECRET_KEY=sk_test_your_secret_key_here
```

**Important:** 
- Use `pk_test_` and `sk_test_` keys for development
- Use `pk_live_` and `sk_live_` keys for production
- Never commit your secret keys to version control

## Step 4: Configure Clerk Application Settings

In your Clerk dashboard:

1. **Allowed Origins**: Add your application URL
   - For local development: `http://localhost:8080`
   - For production: Your production domain

2. **Redirect URLs**: Configure where users go after sign-in/sign-up
   - Sign-in redirect: `http://localhost:8080/dashboard`
   - Sign-up redirect: `http://localhost:8080/dashboard`

3. **Email/Password**: Enable email/password authentication (or your preferred method)

## Step 5: Restart Docker Container

After updating `.env`, restart the container:

```bash
docker compose down
docker compose up -d
```

## Step 6: Verify Setup

1. Navigate to http://localhost:8080/auth/login
2. You should see the Clerk sign-in component (not the "Authentication not configured" message)
3. Try signing up or signing in

## Troubleshooting

### "Authentication not configured" message
- Check that both `CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` are set in `.env`
- Verify the keys are not commented out (no `#` at the start)
- Restart the Docker container after updating `.env`

### 403 Forbidden errors
- Check that your Clerk secret key is correct
- Verify the User-Agent header is set (already configured in code)
- Check Clerk dashboard for API usage limits

### Users not syncing
- Check Docker logs: `docker compose logs minouchat`
- Verify the `/auth/sync` endpoint is working
- Check that Clerk webhooks are configured (if using)

## Development Without Clerk

If you want to develop without Clerk authentication:

1. The application will show "Authentication not configured"
2. Some features may be limited
3. You can still test the application, but user authentication won't work

## Security Notes

- **Never commit `.env` file** - it's already in `.gitignore`
- **Use test keys for development** - `pk_test_` and `sk_test_`
- **Rotate keys if exposed** - Generate new keys in Clerk dashboard
- **Use environment variables in production** - Don't hardcode keys

