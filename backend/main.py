from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
import json
from datetime import datetime
from pathlib import Path

# Initialize FastAPI app
app = FastAPI(title="Sehat.a Backend", version="2.0.0")

# -------------------------------
# Data Directory
# -------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"

def load_json(file_path: Path, fallback):
    """Utility to safely load a JSON file"""
    if not file_path.exists():
        print(f"⚠️ File not found: {file_path}")
        return fallback
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error reading {file_path}: {e}")
        return fallback

# -------------------------------
# Load All Datasets
# -------------------------------
INTENTS_PATH = DATA_DIR / "intents.json"
HEALTH_DATA_PATH = DATA_DIR / "Indian-Healthcare-Symptom-Disease-Dataset.json"
DENGUE_PATH = DATA_DIR / "dengue.json"
SYMPTOM_PROFILE_PATH = DATA_DIR / "Disease_symptom_and_patient_profile_dataset.json"
GENERIC_PATH = DATA_DIR / "6266beac-ae27-49a3-8f2a-e6719f7862e1.json"

intents = load_json(INTENTS_PATH, {"intents": []})
disease_data = load_json(HEALTH_DATA_PATH, [])
dengue_data = load_json(DENGUE_PATH, [])
symptom_profile_data = load_json(SYMPTOM_PROFILE_PATH, [])
generic_data = load_json(GENERIC_PATH, [])

print(f"✅ Loaded datasets: intents={len(intents.get('intents', []))}, "
      f"diseases={len(disease_data)}, dengue={len(dengue_data)}, "
      f"symptom_profile={len(symptom_profile_data)}, generic={len(generic_data)}")

# -------------------------------
# CoWIN API Config
# -------------------------------
BASE_URL = "https://cdn-api.co-vin.in/api/v2"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/98.0.4758.102 Safari/537.36",
    "Accept-Language": "en_US"
}

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
    return {"message": "✅ Welcome to Sehat.a Backend API 🚑"}


@app.get("/states")
def get_states():
    return {"supported_states": STATE_IDS}


@app.get("/districts/{state_name}")
def get_districts(state_name: str):
    state_id = STATE_IDS.get(state_name)
    if not state_id:
        return JSONResponse(status_code=404,
                            content={"error": f"State '{state_name}' not supported. Use: {list(STATE_IDS.keys())}"})

    url = f"{BASE_URL}/admin/location/districts/{state_id}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return {"error": f"Failed to fetch districts: {res.status_code}", "details": res.text[:200]}
    return res.json()


@app.get("/slots/{district_id}")
def get_slots(district_id: int, date: str = None):
    if not date:
        date = datetime.now().strftime("%d-%m-%Y")

    url = f"{BASE_URL}/appointment/sessions/public/findByDistrict?district_id={district_id}&date={date}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return {"error": f"Failed to fetch slots: {res.status_code}", "details": res.text[:200]}
    return res.json()


@app.get("/health/query")
def health_query(message: str):
    if not message:
        return JSONResponse(status_code=400, content={"error": "Message parameter is required"})

    msg = message.lower().strip()

    # 1️⃣ Check intents.json
    for intent in intents.get("intents", []):
        for pattern in intent.get("patterns", []):
            if pattern.lower() in msg:
                return {"intent": intent["tag"], "replies": intent.get("responses", [])}

    # 2️⃣ Fallback: check disease dataset
    for record in disease_data:
        disease_name = str(record.get("Disease", "")).lower()
        if msg in disease_name:
            return {
                "disease": record.get("Disease"),
                "symptoms": record.get("Symptoms", []),
                "precautions": record.get("Precautions", [])
            }

    return {"reply": "❌ Sorry, I don’t know that yet. Please consult a doctor."}


@app.get("/disease/{name}")
def get_disease_info(name: str):
    if not disease_data:
        return {"error": "Dataset not loaded"}

    query = name.lower().strip()
    matches = []
    for record in disease_data:
        disease_name = str(record.get("Disease", "")).lower().strip()
        if query in disease_name:   # partial match
            matches.append({
                "disease": record.get("Disease"),
                "symptoms": record.get("Symptoms", []),
                "precautions": record.get("Precautions", [])
            })

    if matches:
        return {"results": matches}

    # Suggest close matches
    suggestions = [rec.get("Disease") for rec in disease_data if query[0] in str(rec.get("Disease", "")).lower()][:5]
    return {"error": f"No data found for '{name}'", "did_you_mean": suggestions}


@app.get("/symptom-check")
def symptom_check(symptoms: str):
    if not disease_data:
        return {"error": "Dataset not loaded"}

    user_symptoms = [s.strip().lower() for s in symptoms.split(",")]
    matches = []
    for record in disease_data:
        disease_symptoms = [s.strip().lower() for s in record.get("Symptoms", [])]
        score = len(set(user_symptoms) & set(disease_symptoms))
        if score > 0:
            matches.append({
                "disease": record.get("Disease"),
                "match_score": score,
                "symptoms": record.get("Symptoms", [])
            })

    matches = sorted(matches, key=lambda x: x["match_score"], reverse=True)
    return {"input_symptoms": user_symptoms, "possible_diseases": matches[:5] or "No close matches found"}
