from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import json
from pathlib import Path
from datetime import datetime

app = FastAPI(title="Sehat.a Backend", version="4.5.0")

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
        with open(file_path, "r", encoding="utf-8") as f:
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
TRANSLATIONS_PATH = DATA_DIR / "translations.json"

disease_data = load_json(DISEASES_PATH, [])
symptom_data = load_json(SYMPTOMS_PATH, [])
vaccination_data = load_json(VACCINATION_PATH, {})
translations = load_json(TRANSLATIONS_PATH, {})

print(
    f"✅ Summary: diseases={len(disease_data)}, "
    f"symptoms={len(symptom_data)}, "
    f"vaccination_sections={len(vaccination_data.get('vaccinations', {})) if vaccination_data else 0}, "
    f"translations={len(translations)} keys"
)

# -------------------------------
# Helper: Translation
# -------------------------------
def t(key: str, lang: str = "en") -> str:
    """Fetch translation for given key and language"""
    if key in translations:
        return translations[key].get(lang, translations[key].get("en", key))
    return key

# -------------------------------
# Routes
# -------------------------------

@app.get("/")
def home(lang: str = Query("en", description="Language code: en, hi, ta, kn, te, ml, or")):
    return {"message": t("welcome", lang)}

@app.get("/favicon.ico")
def favicon():
    return JSONResponse(content={}, status_code=204)

# -------------------------------
# Disease Endpoints
# -------------------------------

@app.get("/disease/{name}")
def get_disease_info(name: str, lang: str = "en"):
    if not disease_data:
        return {"error": t("unknown_query", lang)}

    query = name.lower().strip()
    matches = []

    for record in disease_data:
        disease_name = str(record.get("disease", "")).lower().strip()
        if query in disease_name:
            matches.append(record)

    if matches:
        return {
            "message": t("disease_info", lang),
            "results": matches
        }

    suggestions = [rec.get("disease") for rec in disease_data if query[0] in str(rec.get("disease", "")).lower()][:5]
    return {"error": f"No data found for '{name}'", "did_you_mean": suggestions}

# -------------------------------
# Symptom Checker
# -------------------------------

@app.get("/symptom-check")
def symptom_check(symptoms: str, lang: str = "en"):
    if not disease_data:
        return {"error": t("unknown_query", lang)}

    user_symptoms = [s.strip().lower() for s in symptoms.split(",")]
    matches = []

    for record in disease_data:
        disease_symptoms = [s.strip().lower() for s in record.get("common_symptoms", [])]
        score = len(set(user_symptoms) & set(disease_symptoms))
        if score > 0:
            matches.append({
                "disease": record.get("disease"),
                "match_score": score,
                "symptoms": record.get("common_symptoms", [])
            })

    matches = sorted(matches, key=lambda x: x["match_score"], reverse=True)
    return {
        "input_symptoms": user_symptoms,
        "possible_diseases": matches[:5] or t("unknown_query", lang)
    }

# -------------------------------
# Vaccination Endpoints
# -------------------------------

@app.get("/vaccination/all")
def get_all_vaccines(lang: str = "en"):
    if not vaccination_data:
        return {"error": t("unknown_query", lang)}
    return vaccination_data.get("vaccinations", {})

@app.get("/vaccination/{age}")
def get_vaccines_by_age(age: str, lang: str = "en"):
    if not vaccination_data:
        return {"error": t("unknown_query", lang)}

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

@app.get("/vaccination/due")
def get_due_vaccines(dob: str, lang: str = "en"):
    if not vaccination_data:
        return {"error": t("unknown_query", lang)}

    try:
        dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}

    today = datetime.today().date()
    age_days = (today - dob_date).days
    age_months = age_days // 30

    due_vaccines = []
    upcoming_vaccine = None

    for category in ["NIS_vaccines", "optional_private_vaccines"]:
        for v in vaccination_data.get("vaccinations", {}).get(category, []):
            age_str = v["age"].lower()

            if "birth" in age_str and age_months == 0:
                due_vaccines.append(v)
            elif "6 weeks" in age_str and 1 <= age_months <= 2:
                due_vaccines.append(v)
            elif "10 weeks" in age_str and 2 <= age_months <= 3:
                due_vaccines.append(v)
            elif "14 weeks" in age_str and 3 <= age_months <= 4:
                due_vaccines.append(v)
            elif "9-12 months" in age_str and 9 <= age_months <= 12:
                due_vaccines.append(v)
            elif "16-24 months" in age_str and 16 <= age_months <= 24:
                due_vaccines.append(v)
            elif "5-6 years" in age_str and 60 <= age_months <= 72:
                due_vaccines.append(v)
            elif "10 years" in age_str and 120 <= age_months <= 132:
                due_vaccines.append(v)

            if not upcoming_vaccine and "months" in age_str:
                try:
                    min_age = int(age_str.split("-")[0].replace("months", "").strip())
                    if min_age > age_months:
                        upcoming_vaccine = v
                except:
                    pass

    return {
        "dob": str(dob_date),
        "age_months": age_months,
        "due_vaccines": due_vaccines,
        "upcoming_vaccine": upcoming_vaccine
    }
