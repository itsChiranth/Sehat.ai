from fastapi import FastAPI
from fastapi.responses import JSONResponse
import json
from pathlib import Path

app = FastAPI(title="Sehat.a Backend", version="3.4.0")

# -------------------------------
# Data Directory
# -------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"

def load_json(file_path: Path, fallback):
    """Utility to safely load a JSON file and log status"""
    print(f"🔍 Looking for: {file_path}")
    if not file_path.exists():
        print(f"⚠️ File not found: {file_path}")
        return fallback
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            print(f"✅ Loaded {file_path.name} with {len(data) if isinstance(data, list) else len(data.keys())} records")
            return data
    except Exception as e:
        print(f"⚠️ Error reading {file_path}: {e}")
        return fallback

# -------------------------------
# Load Datasets
# -------------------------------
DISEASES_PATH = DATA_DIR / "diseases.json"
SYMPTOMS_PATH = DATA_DIR / "symptoms.json"
VACCINATION_PATH = DATA_DIR / "vaccination_schedule.json"

disease_data = load_json(DISEASES_PATH, [])
symptom_data = load_json(SYMPTOMS_PATH, [])
vaccination_data = load_json(VACCINATION_PATH, {})

print(
    f"✅ Summary: diseases={len(disease_data)}, "
    f"symptoms={len(symptom_data)}, "
    f"vaccination_sections={len(vaccination_data.get('vaccinations', {})) if vaccination_data else 0}"
)

# -------------------------------
# Routes
# -------------------------------

@app.get("/")
def home():
    return {"message": "✅ Sehat.a Backend Running 🚑"}

# -------------------------------
# Vaccination Endpoints
# -------------------------------

@app.get("/vaccination/all")
def get_all_vaccines():
    """Return all vaccines (NIS + optional/private)"""
    if not vaccination_data:
        return {"error": "Vaccination dataset not loaded"}
    return vaccination_data.get("vaccinations", {})

@app.get("/vaccination/{age}")
def get_vaccines_by_age(age: str):
    """
    Return vaccines due at a specific age.
    Example: /vaccination/at%20birth  OR /vaccination/9-12%20months
    Flexible matching: '9 months' matches '9-12 months'
    """
    if not vaccination_data:
        return {"error": "Vaccination dataset not loaded"}

    age_query = age.lower().strip()
    results = []

    for category in ["NIS_vaccines", "optional_private_vaccines"]:
        for v in vaccination_data.get("vaccinations", {}).get(category, []):
            vaccine_age = v["age"].lower()
            if age_query in vaccine_age or vaccine_age in age_query:
                results.append(v)

    if results:
        return {"age": age, "vaccines": results}

    return {"error": f"No vaccines found for age '{age}'"}
