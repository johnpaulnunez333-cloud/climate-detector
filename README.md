# Philippine Climate Detector

Folders:
- backend: Flask API (deploy to Render)
- frontend: static site with Bootstrap, Vue, React and vanilla JS (deploy to Vercel)

## 1. Database (free, not Supabase): Neon
1. Sign up at https://neon.tech (free plan, no card needed).
2. Create a project, then copy the connection string.
3. Keep it for the DATABASE_URL value below.

## 2. GitHub
1. Create a new repository and push this whole folder.

## 3. Backend on Render (free)
1. Render dashboard > New > Web Service > connect your repository.
2. Root Directory: backend
3. Runtime: Python 3
4. Build Command: pip install -r requirements.txt
5. Start Command: gunicorn app:app
6. Instance type: Free
7. Environment variables:
   - DATABASE_URL = your Neon connection string
   - JWT_SECRET_KEY = a long random string
   - FRONTEND_URL = your Vercel URL (add after step 4, then redeploy)
   - PYTHON_VERSION = 3.11.9
8. Deploy and copy the Render URL.

## 4. Frontend on Vercel (free Hobby plan)
1. Open frontend/js/config.js and set API_URL to your Render URL (no trailing slash).
2. Commit and push.
3. Vercel dashboard > Add New > Project > import the repository.
4. Root Directory: frontend
5. Framework Preset: Other. Leave build and output settings empty.
6. Deploy and copy the Vercel URL.
7. Back in Render, set FRONTEND_URL to that Vercel URL and redeploy.

## Notes
- Render free services sleep after inactivity, so the first request can take around 50 seconds.
- Weather data comes from Open-Meteo, which needs no API key.
- Map tiles come from OpenStreetMap.
