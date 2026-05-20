import json
import os

# =========================
# INTENT KEYWORDS
# =========================
INTENT_KEYWORDS = {
    "greeting": ["hi", "hello", "hey", "namaste", "sat sri akal", "good morning"],
    "goodbye": ["bye", "goodbye", "thanks", "thank you", "exit", "stop"],
    "timetable": ["timetable", "time table", "schedule", "routine", "class timetable"],
    "academic_calendar": ["academic calendar", "calendar", "holiday list"],
    "fees": ["fee", "fees", "fee structure", "payment", "scholarship"],
    "admission": ["admission", "apply", "programs", "course", "eligibility"],
    "library": ["library", "books", "digital library", "opac", "fine"],
    "hostel": ["hostel", "warden", "hostel rules", "mess"],
    "department": ["department", "hod", "faculty", "lab", "contact"],
    "notice": ["notice", "notices", "circular", "announcement"],
    "exams": ["date sheet", "datesheet", "examination", "mst", "end semester", "admit card"],
    "results": ["result", "results", "marks", "grade card", "sgpa", "cgpa"],
    "syllabus": ["syllabus", "curriculum", "study material", "notes"],
    "placements": ["placement", "placements", "tnp", "training", "internship", "job", "company"],
    "facilities": ["canteen", "dispensary", "medical", "gym", "sports", "bank", "atm"],
    "events": ["fest", "genonext", "workshop", "club", "society", "technical event"],
    "certificates": ["bonafide", "transcript", "character certificate", "degree", "noc"],
}

TAG_TO_RUNTIME_INTENT = {
    "admission_process": "admission",
    "admission_eligibility": "admission",
    "admission_documents": "admission",
    "admission_contact": "admission",
    "management_quota": "admission",
    "sre_exam": "admission",
    "principal_info": "college",
    "timetable": "timetable",
    "academic_calendar": "academic_calendar",
    "holiday_list": "academic_calendar",
    "syllabus_query": "syllabus",
    "previous_papers": "syllabus",
    "exam_datesheet": "exams",
    "makeup_exam_info": "exams",
    "re_evaluation": "exams",
    "admit_card": "exams",
    "backlog_form": "exams",
    "internal_marks": "results",
    "fee_structure": "fees",
    "fee_deadline": "fees",
    "late_fee": "fees",
    "online_fee_payment": "fees",
    "hod_info": "department",
    "faculty_list": "department",
    "department_website": "department",
    "lab_facilities": "department",
    "placement_stats_department": "placements",
    "btech_courses": "department",
    "hostel_warden": "hostel",
    "hostel_rules": "hostel",
    "hostel_fee": "hostel",
    "hostel_apply": "hostel",
    "cafeteria_info": "facilities",
    "sports_department": "facilities",
    "oat_info": "events",
    "library_access": "library",
    "latest_notices": "notice",
    "academic_portal": "department",
    "placement_support": "placements",
    "student_documents": "certificates",
    "admin_document_approval": "certificates",
    "administrator_contact": "certificates",
}

# =========================
# LOAD JSON FILES
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
INTENTS_FILE = os.path.join(BASE_DIR, "intents.json")
SEED_DATASET_FILE = os.path.join(BASE_DIR, "data", "gndec_intent_dataset.json")
HIGH_SIGNAL_SHORT_TOKENS = {"oat", "sre", "opac"}
MATCH_STOPWORDS = {
    "the", "is", "a", "an", "of", "for", "to", "in", "on", "at",
    "what", "who", "where", "when", "how", "about", "tell", "show", "give",
    "me", "my", "do", "please", "details", "detail", "info", "information",
    "ke", "ki", "ka", "me", "mei", "mein", "bare", "baare", "batao", "dasso",
    "hai", "kya", "di", "da", "de", "barei", "baarei",
}


def load_primary_intents():
    if not os.path.exists(INTENTS_FILE):
        print("Warning: intents.json not found")
        return []

    try:
        with open(INTENTS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data.get("intents", [])
    except Exception as error:
        print("Error loading intents.json:", error)
        return []


def load_seed_intents():
    if not os.path.exists(SEED_DATASET_FILE):
        return []

    try:
        with open(SEED_DATASET_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception as error:
        print("Error loading gndec_intent_dataset.json:", error)
        return []

    flattened = []
    for category in data.get("categories", []):
        for item in category.get("intents", []):
            flattened.append({
                "tag": item.get("tag"),
                "patterns": item.get("patterns", []),
                "responses": [],
                "links": item.get("official_sources", []),
                "category": category.get("id"),
                "answer_mode": item.get("answer_mode"),
            })

    return flattened


def load_intents():
    # Prefer the newer curated seed dataset first so updated GNDEC-specific
    # answers override older generic canned intents when patterns overlap.
    return load_seed_intents() + load_primary_intents()


def map_tag_to_runtime_intent(tag: str) -> str:
    return TAG_TO_RUNTIME_INTENT.get(tag or "", "general")


# =========================
# MATCH QUERY WITH JSON
# =========================
def get_json_match(query: str):
    query = query.lower().strip()
    data = load_intents()

    best_match = None
    best_score = 0

    for item in data:
        patterns = item.get("patterns", [])
        score = 0
        query_words = {word for word in query.split() if word and word not in MATCH_STOPWORDS}

        for pattern in patterns:
            normalized = pattern.lower().strip()
            pattern_words = {word for word in normalized.split() if word and word not in MATCH_STOPWORDS}
            overlap = query_words.intersection(pattern_words)

            if normalized == query:
                score += 12
            elif normalized in query:
                score += 6

            score += len(overlap)
            score += 3 * len(overlap.intersection(HIGH_SIGNAL_SHORT_TOKENS))

        if score > best_score:
            best_score = score
            best_match = item

    return best_match if best_score >= 3 else None
