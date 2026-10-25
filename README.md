# Personalized Travel Itinerary Planner

A travel-planning capstone with two runnable clients: a Streamlit Community Cloud demo (`app.py`) and a React/Vite client (`frontend/`) backed by FastAPI (`backend/`). Both use the same destination and itinerary engine in `travel_core.py`.

## Streamlit demo

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Demo mode works without credentials. To use AI generation, select Gemini or Groq in the sidebar and enter an API key. Keys are used only for the current session and are not included in saved trips. For a deployed app, you may instead configure `GEMINI_API_KEY` or `GROQ_API_KEY` in Streamlit Community Cloud Secrets.

Example `.streamlit/secrets.toml` (do not commit real secrets):

```toml
GEMINI_API_KEY = "your-key"
# or
GROQ_API_KEY = "your-key"
```

## Deploy to Streamlit Community Cloud

1. Push this project to a GitHub repository.
2. In Streamlit Community Cloud, create an app from the repository and set the main file to `app.py`.
3. Add an optional Gemini or Groq API key under the app's Secrets settings.

Trip history in the Streamlit demo is session-scoped. Seasonal recommendations use a month guide, not live weather. Activity and meal costs are estimates; they exclude lodging, transport, taxes, and live pricing.

## Full-stack development

Install both Python dependency sets and the frontend packages:

```powershell
python -m pip install -r requirements.txt -r backend/requirements.txt
Push-Location frontend
npm install
Pop-Location
```

Run the API and React app in separate terminals:

```powershell
python -m uvicorn backend.main:app --reload --port 8000
```

```powershell
Push-Location frontend
npm run dev
Pop-Location
```

The API docs are available at `http://127.0.0.1:8000/docs`. Without Supabase configuration, the API uses a per-session in-memory trip list. For account-backed persistence, apply `backend/schema.sql` to a Supabase project and configure `backend/.env` using `backend/.env.example`. The frontend uses the Supabase anon key only; never put a service-role key in `VITE_*` variables.

For the React app, set `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, and `VITE_SUPABASE_ANON_KEY` in Vercel. The Render blueprint is `render.yaml`; configure `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `FRONTEND_ORIGINS` in the Render service. Use distinct API URLs for the React deployment and the Streamlit app.

## Tests

```powershell
python -m pytest backend/tests -q
Push-Location frontend
npm run build
Pop-Location
```
