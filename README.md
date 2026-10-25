# Personalized Travel Itinerary Planner

A Streamlit travel-planning app for destination discovery, day-by-day itineraries, activity swaps, session trip history, and offline PDF export.

## Run locally

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

The app has no database requirement. Trip history is held in Streamlit session state and is cleared when that session ends. The recommendation season fit is a lightweight month-based guide, not a live weather forecast. Cost estimates are approximate activity and meal costs; they exclude lodging, transport, taxes, and live pricing.
