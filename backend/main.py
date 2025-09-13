from fastapi import FastAPI
from fastapi.responses import JSONResponse
import json
from pathlib import Path
from difflib import SequenceMatcher

app = FastAPI(title="Sehat.a Backend", version="3.2.0")

# -------------------------------
# Data Directory
# -------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"

def load_json(file_path: Path, fallback):
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
# Load Datasets
# -------------------------------
DISEASES_PATH = DATA_DIR / "diseases.json"
SYMPTOMS_PATH = DATA_DIR / "symptoms.json"

disease_data = load_json(DISEASES_PATH, [])
symptom_data = load_json(SYMPTOMS_PATH, [])

print(f"✅ Loaded datasets: diseases={len(disease_data)}, symptoms={len(symptom_data)}")

# -------------------------------
# Symptom Synonyms (Indian terms)
# -------------------------------
SYMPTOM_SYNONYMS = {
    "bukhar": "fever",
    "sardi": "cold",
    "khansi": "cough",
    "dast": "diarrhea",
    "ultee": "vomiting",
    "saans phoolna": "shortness of breath",
    "sir dard": "headache",
    "pet dard": "abdominal pain",
    "jaundis": "jaundice"
}

# -------------------------------
# Utility Functions
# -------------------------------
def normalize_symptom(symptom: str):
    """Map synonyms & lowercase symptoms"""
    symptom = symptom.lower().strip()
    return SYMPTOM_SYNONYMS.get(symptom, symptom)

def fuzzy_match(a, b):
    """Return similarity ratio between two strings"""
    return SequenceMatcher(None, a, b).ratio()

def get_symptom_weight(symptom: str):
    """Assign weights (specific symptoms higher weight)"""
    specific_keywords = ["jaundice", "bloody", "rash", "retro-orbital", "convulsion", "chest pain"]
    for keyword in specific_keywords:
        if keyword in symptom:
            return 2.0  # double weight for specific red-flag symptoms
    return 1.0

# -------------------------------
# Routes
# -------------------------------
@app.get("/")
def home():
    return {"message": "✅ Sehat.a Backend Running 🚑"}

@app.get("/disease/{name}")
def get_disease(name: str):
    query = name.lower().strip()
    matches = [d for d in disease_data if query in d["disease"].lower()]
    if matches:
        return {"results": matches}
    return {"error": f"No data found for '{name}'"}

@app.get("/symptoms/{name}")
def get_symptom(name: str):
    query = normalize_symptom(name)
    matches = [s for s in symptom_data if query in s["symptom"].lower()]
    if matches:
        return {"results": matches}
    return {"error": f"No data found for symptom '{name}'"}

@app.get("/symptom-check")
def symptom_check(symptoms: str):
    """
    Pass comma-separated symptoms to get possible diseases.
    Example: /symptom-check?symptoms=fever,rash,joint pain
    """
    if not symptoms:
        return JSONResponse(status_code=400, content={"error": "Symptoms parameter is required"})

    user_symptoms = [normalize_symptom(s) for s in symptoms.split(",")]
    possible_diseases = {}

    for record in symptom_data:
        symptom = record["symptom"].lower()
        for user_symptom in user_symptoms:
            # Check exact match OR fuzzy similarity > 0.7
            if user_symptom == symptom or fuzzy_match(user_symptom, symptom) > 0.7:
                weight = get_symptom_weight(user_symptom)
                for d in record["related_diseases"]:
                    possible_diseases[d] = possible_diseases.get(d, 0) + weight

    # Sort diseases by score
    sorted_matches = sorted(possible_diseases.items(), key=lambda x: x[1], reverse=True)

    if not sorted_matches:
        return {"input_symptoms": user_symptoms, "results": "No close matches found"}

    results = [{"disease": d, "match_score": score} for d, score in sorted_matches]
    return {"input_symptoms": user_symptoms, "results": results[:10]}
