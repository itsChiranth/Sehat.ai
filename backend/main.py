from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
import json
from datetime import datetime
from pathlib import Path

# Initialize FastAPI app
app = FastAPI(title="Sehat.a Backend", version="1.3.0")

# -------------------------------
# Load Health Data (intents.json)
# -------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"
INTENTS_PATH = DATA_DIR / "intents.json"

print("🔍 Looking for intents.json at:", INTENTS_PATH)

if INTENTS_PATH.exists():
    try:
        with open(INTENTS_PATH, "r") as f:
            intents = json.load(f)
        print("✅ intents.json loaded successfully")
    except Exception as e:
        intents = {"intents": []}
        print(f"⚠️ Error reading intents.json: {e}")
else:
    intents = {"intents": []}
    print(f"⚠️ Could not find intents.json at {INTENTS_PATH}")

# -------------------------------
# CoWIN API Config
# -------------------------------
BASE_URL = "https://cdn-api.co-vin.in/api/v2"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Supported States with fixed state_ids
STATE_IDS = {
    "Odisha": 27,
    "Tamil Nadu": 29,
    "Andhra Pradesh": 36,
    "Karnataka": 16,
    "Kerala": 2
}

# -------------------------------
# Routes
# -------------------------------

@app.get("/")
def home():
    """Root endpoint"""
    return {"message": "✅ Welcome to Sehat.a Backend API 🚑"}


@app.get("/states")
def get_states():
    """Return supported states"""
    return {"supported_states": STATE_IDS}


@app.get("/districts/{state_name}")
def get_districts(state_name: str):
    """Return all districts for a given state"""
    state_id = STATE_IDS.get(state_name)
    if not state_id:
        return JSONResponse(
            status_code=404,
            content={"error": f"State '{state_name}' not supported. Use one of: {list(STATE_IDS.keys())}"}
        )

    url = f"{BASE_URL}/admin/location/districts/{state_id}"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return JSONResponse(status_code=res.status_code, content={"error": "Failed to fetch districts"})
    
    return res.json()


@app.get("/slots/{district_id}")
def get_slots(district_id: int, date: str = None):
    """Return vaccination slots for a given district on a date (dd-mm-yyyy)"""
    if not date:
        date = datetime.now().strftime("%d-%m-%Y")

    url = f"{BASE_URL}/appointment/sessions/public/findByDistrict?district_id={district_id}&date={date}"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return JSONResponse(status_code=res.status_code, content={"error": "Failed to fetch slot data"})

    return res.json()


@app.get("/health/query")
def health_query(message: str):
    """
    Rule-based health chatbot using intents.json
    Example: /health/query?message=How to treat fever?
    """
    if not message:
        return JSONResponse(status_code=400, content={"error": "Message parameter is required"})

    message = message.lower()
    for intent in intents.get("intents", []):
        for pattern in intent.get("patterns", []):
            if pattern.lower() in message:
                return {
                    "intent": intent["tag"],
                    "replies": intent["responses"]  # return all possible responses
                }

    return {"reply": "❌ Sorry, I don’t know that yet. Please consult a doctor."}
