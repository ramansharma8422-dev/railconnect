# Mini Railway Booking Backend

A fictional railway ticket-booking REST API built with FastAPI, SQLModel, and SQLite. It includes passenger accounts, admin train/station management, train search, booking/PNR generation, cancellations, password reset, JWT authentication, and automated API tests. No frontend, real IRCTC integration, or real payments are included.

## Features

- Signup/login with bcrypt password hashing and JWT access tokens.
- Logout revokes the current token using a database denylist.
- Forgot/reset password flow with expiring, single-use reset tokens. In development, the reset endpoint returns the token to simulate email delivery; remove this field and connect an email provider before production.
- User profile and booking endpoints are scoped to the authenticated passenger.
- Admin-only station/train creation, train updates, and deactivation.
- Search by origin, destination, and journey date.
- Booking PNRs, simulated payment status, booking history, and cancellation.
- Atomic conditional seat decrement and database transactions help prevent overselling; duplicate cancellation is rejected.
- Swagger UI at `/docs`.

## Tech stack

Python 3.11+, FastAPI, Uvicorn, SQLModel, SQLite, Pydantic, pydantic-settings, python-jose, bcrypt, email-validator, httpx, pytest.

## Installation

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Edit `.env`: set `JWT_SECRET_KEY` to a long random secret and set a strong admin password. Never commit `.env`, database files, tokens, or real credentials. The default admin credentials are for local development only and must be changed.

## Run

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

The database tables and the configured development admin are initialized on startup. Station and train data are fictional and must be added through admin endpoints.

## Run tests

```bash
pytest -q
```

Tests use the configured database. For repeatable isolated test runs, set `DATABASE_URL` to a temporary SQLite file before running tests and remove that file afterward. Tests create accounts and a small fictional route.

## Important endpoints

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/auth/signup` | Public | Create passenger account |
| POST | `/auth/login` | Public | Get JWT |
| POST | `/auth/logout` | Authenticated | Revoke current access token |
| POST | `/auth/forgot-password` | Public | Generate development reset token |
| POST | `/auth/reset-password` | Public | Reset password once |
| GET | `/users/me` | Authenticated | Own profile |
| POST | `/admin/stations` | Admin | Add station |
| GET | `/stations` | Public | List stations |
| POST | `/admin/trains` | Admin | Add train |
| PATCH | `/admin/trains/{train_id}` | Admin | Update train |
| POST | `/admin/trains/{train_id}/deactivate` | Admin | Deactivate train |
| GET | `/trains/search?origin=NDLS&destination=CNB&journey_date=YYYY-MM-DD` | Public | Search trains |
| POST | `/bookings` | Authenticated | Book seats and receive PNR |
| GET | `/bookings/me` | Authenticated | Own booking history |
| GET | `/bookings/{pnr}` | Authenticated | Own booking details |
| POST | `/bookings/{pnr}/cancel` | Authenticated | Cancel eligible booking |
| GET | `/health` | Public | Health check |

For protected endpoints, use Swagger's **Authorize** button and enter `Bearer <token>` if prompted, or use the `Authorization: Bearer <token>` header in an API client.

## Example workflow

1. Sign up a passenger at `/auth/signup`, then log in at `/auth/login`.
2. Log in as the configured admin and create New Delhi (`NDLS`) and Kanpur Central (`CNB`) stations.
3. Add a train through `/admin/trains`.
4. Search with `/trains/search`.
5. Book through `/bookings`; the response contains a unique PNR.
6. Check `/bookings/me` and cancel using `/bookings/{pnr}/cancel`.

### Development admin

The admin is created from `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env` on first startup if that email does not exist. If you change these values after the admin already exists, the existing account is not automatically changed; update the database or use a fresh local database.

## Security notes and limitations

- Passwords are hashed; plaintext passwords are never stored.
- JWT access tokens expire. Logout adds a token's `jti` to a revocation table; clients should also discard the token.
- Password-reset tokens are stored as SHA-256 hashes, expire, and can be used only once. The development response exposes the reset token solely to simulate email delivery.
- The database uses SQLite for local development. The conditional seat update is atomic and checked for affected rows. For high-concurrency production deployments, use a server database such as PostgreSQL, transaction isolation/locking, rate limits, email delivery, audit logging, and a reviewed migration strategy.
- Booking and seat updates share a transaction; no real payment is processed.
- Cancellation is allowed only for future journeys. Fare refunds are not implemented.
- Add rate limiting, email verification, structured logging, migrations, and production secret management before deployment.

## Screenshots

Capture screenshots from your own running application and save them in this folder. Never include passwords, JWT access tokens, reset tokens, or secrets. The placeholders below are intentionally not fake screenshots; replace them with screenshots you personally capture.

- `screenshots/01-signup-login.png` — Signup and successful login.
- `screenshots/02-failed-login-unauthorized.png` — Failed login and unauthorized protected request.
- `screenshots/03-password-reset.png` — Forgot-password and reset-password results (blur the reset token).
- `screenshots/04-admin-add-train.png` — Admin creates stations and a train.
- `screenshots/05-search-seats.png` — Train search and available seats.
- `screenshots/06-booking-pnr.png` — Successful booking response with PNR (hide bearer token).
- `screenshots/07-booking-cancel.png` — Booking history and cancellation result.
- `screenshots/08-tests.png` — Successful test run.

Add your real screenshots with these image links after capturing them. Until you add the files, these images will appear as missing in GitHub; do not replace them with fabricated screenshots.

![Signup and login](screenshots/01-signup-login.png)
![Failed login and unauthorized access](screenshots/02-failed-login-unauthorized.png)
![Forgot-password and reset-password](screenshots/03-password-reset.png)
![Admin adding a train](screenshots/04-admin-add-train.png)
![Train search and seat availability](screenshots/05-search-seats.png)
![Booking confirmation and PNR](screenshots/06-booking-pnr.png)
![Booking history and cancellation](screenshots/07-booking-cancel.png)
![Automated tests passing](screenshots/08-tests.png)

## License

For learning and portfolio use. Add a license of your choice before publishing.
