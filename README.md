# AI JobTrust

Hackathon MVP for explainable fake-job and recruitment-scam detection.

## Implemented in this MVP

- Flutter Material 3 mobile experience for text-based job-message analysis
- FastAPI rule detection API with SSRF-safe URL analysis
- Suspicious-text highlights and rule-risk score
- Free email-domain and basic salary-realism checks
- Safety chatbot endpoint and company/website check endpoint
- Model-status endpoint with clear "not trained" disclosure
- Explainable evidence output with no unsupported confidence percentages
- Supabase-ready PostgreSQL schema and Row Level Security policies
- React/Vite responsive admin dashboard shell
- Backend and Flutter focused test coverage

## Architecture

```text
Flutter / Web --> FastAPI REST API --> Detection Engine
                                      + Rule configuration
                                      + URL safety validation
                                      + Verification placeholders
                                       |
                                       --> PostgreSQL / Supabase

React Admin --> FastAPI protected moderation APIs
```

## Run the backend

```powershell
cd D:\Hackthon\backend
py -3 -m pip install -r requirements.txt
py -3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API documentation: `http://localhost:8000/docs`

## Run Flutter

```powershell
cd D:\Hackthon\mobile_app
flutter pub get
flutter run -d chrome
```

For Android, start an emulator or connect a device and run `flutter run`.
Set `--dart-define=API_BASE_URL=http://10.0.2.2:8000` on Android; use
`http://localhost:8000` for browser or desktop.

## Run admin dashboard

Node.js must be installed and approved by the user. Then:

```powershell
cd D:\Hackthon\admin_dashboard
npm install
npm run dev
```

## Supabase setup

1. Copy `backend/.env.example` to `backend/.env`.
2. Create a Supabase project.
3. Set `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and
   `SUPABASE_SERVICE_ROLE_KEY`.
4. Apply `database/schema.sql`, then `database/policies.sql`.
5. Never expose the service-role key in Flutter or React.

## Security limitations

- Supabase auth and role enforcement are scaffolded in the database design;
  production authentication must be integrated before accepting real accounts.
- AI-hosted context analysis is not yet connected.
- OCR and screenshot upload require a provider implementation and storage policy.
- Company verification uses no claims until a reliable public source is integrated.
- URL scanning checks DNS resolution, HTTPS, private-address access and shorteners;
  it does not prove domain reputation or perform redirect fetching.

## Tests

```powershell
cd D:\Hackthon\backend
py -3 -m pytest -q

cd D:\Hackthon\mobile_app
flutter test
flutter analyze
```
