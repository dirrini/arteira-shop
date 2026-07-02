# Arteira Marketplace

Production-oriented marketplace scaffold for Brazilian craftwork sellers and buyers.

## Stack

- Python 3.12, Flask, Gunicorn
- MongoDB 7 with explicit indexes
- React 18, Vite, Nginx
- Native email/password authentication and Google Identity Services login
- Mercado Pago Checkout Pro for Brazilian payments

## Features

- Email/password registration and login with salted password hashing
- Google OAuth login with server-side ID token verification and account linking
- Secure HTTP-only JWT session cookie
- Buyer and seller modes from the same account
- Seller profile creation
- Product publishing, search, inventory, categories and images
- Mercado Pago payment preference creation
- Mercado Pago webhook reconciliation for paid, failed, cancelled and refunded orders
- Docker Compose for local/prod-like delivery

## Local Development

1. Copy environment files:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
cp backend/.env.example backend/.env
```

2. Fill in:

- `GOOGLE_CLIENT_ID`
- `VITE_GOOGLE_CLIENT_ID`
- `MERCADO_PAGO_ACCESS_TOKEN`
- strong random values for `SECRET_KEY` and `JWT_SECRET`

3. Start MongoDB and the API:

```bash
docker compose up mongo api
```

4. Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

5. Open `http://localhost:5173`.

## Google OAuth Setup

Create a Web application OAuth client in Google Cloud Console.

Authorized JavaScript origins for local development:

```text
http://localhost:5173
```

For production, add your HTTPS domain. The backend verifies Google ID tokens against `GOOGLE_CLIENT_ID`.

## Mercado Pago Setup

This project uses Mercado Pago Checkout Pro. The backend creates payment preferences with `MERCADO_PAGO_ACCESS_TOKEN`; the browser only receives the checkout URL.

Configure the notification URL in Mercado Pago or rely on the preference value:

```text
https://your-api-domain.com/api/payments/mercadopago/webhook
```

Use test credentials and test users before production credentials. Set `MERCADO_PAGO_WEBHOOK_SECRET` when signature validation is enabled in your Mercado Pago app.

## Production Checklist

- Use HTTPS only.
- Set `COOKIE_SECURE=true`.
- Use `COOKIE_SAMESITE=None` if API and frontend are on different sites; keep `Lax` when same-site.
- Replace default CORS with exact production origins.
- Put MongoDB behind private networking.
- Store secrets in a managed secret store, not in source control.
- Add transactional email verification, password recovery and login rate limiting before a public launch.
- Add seller KYC and payout onboarding before releasing real seller settlements.
- Add shipping calculation, refund workflows, antifraud review and fiscal document handling before a real launch in Brazil.
- Run backups and monitoring for MongoDB, API latency, webhook failures and payment status drift.

## Useful Commands

```bash
docker compose up --build
docker compose logs -f api
cd backend && flask --app wsgi:app run --debug
cd frontend && npm run build
```

The full Compose stack is available at `http://localhost:8080` by default. Change
`WEB_PORT` and the matching local URLs in `.env` if that port is occupied. If an image pull
times out, retry it separately with `docker pull mongo:7`, then run Compose again;
Docker keeps any layers that were downloaded successfully.

## Source Notes

The integration follows Google OAuth web guidance for client credentials and server validation, and Mercado Pago Checkout Pro guidance for backend preference creation and payment notifications.
