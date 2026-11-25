# Setup Guide

## Windows prerequisites

- Flutter stable (included in this workspace)
- Python 3.11 or later
- Node.js 20 or later for the admin dashboard
- A Supabase project for persistent production features
- Optional Android SDK/device for mobile testing

## Environment

Copy `backend/.env.example` to `backend/.env`. Configure keys only after a provider
is chosen. The MVP runs without hosted AI credentials using rule-based analysis.

## First launch

1. Start the backend.
2. Open `http://localhost:8000/docs`.
3. Start Flutter web.
4. Enter a suspicious message such as "Pay a registration fee and share your OTP".
5. Start the admin dashboard after installing Node.js.
