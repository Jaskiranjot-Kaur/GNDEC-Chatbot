import re
from chatbot.intents import INTENT_KEYWORDS, get_json_match, map_tag_to_runtime_intent
from chatbot.translator import choose_language, normalize_multilingual_text

DEPT_ALIASES = {
    "computer science": "CSE",
    "computer science engineering": "CSE",
    "cse": "CSE",
    "cs": "CSE",

    "electronics and communication": "ECE",
    "electronics": "ECE",
    "ece": "ECE",

    "electrical engineering": "EE",
    "electrical": "EE",
    "ee": "EE",

    "information technology": "IT",
    "it": "IT",

    "civil engineering": "CIVIL",
    "civil": "CIVIL",
    "ce": "CIVIL",

    "mechanical engineering": "MECHANICAL",
    "mechanical": "MECHANICAL",
    "me": "MECHANICAL",

    "applied sciences": "APPSC",
    "appsc": "APPSC",
}

SECTIONS = ["A", "B", "C", "D", "E", "F"]

TEACHER_TRIGGER_WORDS = {
    "teacher", "teachers", "faculty", "sir", "madam", "mam", "maam",
    "professor", "prof", "pf", "dr", "timetable", "schedule", "routine",
    "time", "table", "show", "give", "me", "of", "for", "ka", "ki", "ke",
    "da", "di", "de", "please", "batao", "dasso", "kholo", "dikhao", "do",
    "teacher timetable", "faculty timetable",
}

NON_TEACHER_QUERY_WORDS = {
    "hostel", "admission", "exam", "result", "holiday", "calendar", "notice",
    "principal", "hod", "department", "fees", "fee", "library", "syllabus",
    "placement", "portal", "bonafide", "certificate", "girls", "boys",
    "cafeteria", "canteen", "lipton", "blueberry", "blue", "berry", "cafe",
    "happiness", "station", "oat", "open air theatre", "sre",
}

NAME_QUERY_STOPWORDS = {
    "about", "college", "infrastructure", "courses", "course", "offered",
    "offer", "available", "facilities", "facility", "campus", "details",
    "detail", "information", "info", "tell", "explain", "describe", "list",
    "show", "what", "which", "where", "when", "why", "how", "can", "could",
    "should", "please", "college", "gndec", "sports", "cafeteria", "canteen",
    "mess", "oat", "theatre", "theater", "open", "air", "programs", "branches",
    "stream", "streams", "labs", "lab", "institute", "university",
}


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = normalize_multilingual_text(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_debug_text(value: str) -> str:
    try:
        return str(value).encode("cp1252", errors="replace").decode("cp1252")
    except Exception:
        return repr(value)


def detect_response_language(raw_text: str, language: str) -> str:
    raw_text = raw_text or ""
    if re.search(r"[\u0900-\u097F]", raw_text):
        return "hi_native"
    if re.search(r"[\u0A00-\u0A7F]", raw_text):
        return "pa_native"
    return language


def detect_intent(text: str) -> str:
    lower = normalize_text(text)
    json_match = get_json_match(lower)

    if json_match:
        return map_tag_to_runtime_intent(json_match.get("tag"))

    for intent, words in INTENT_KEYWORDS.items():
        if any(w in lower for w in words):
            return intent

    # Fallback: if group like d1/d2/d3/d4 mentioned, likely timetable
    if re.search(r"d[1-4]", lower):
        return "timetable"

    return "general"


def extract_department(text: str):
    lower = normalize_text(text)

    # longest match first
    ordered = sorted(DEPT_ALIASES.items(), key=lambda x: len(x[0]), reverse=True)

    for key, value in ordered:
        token_pattern = r"\b" + re.escape(key).replace(r"\ ", r"\s+") + r"\b"
        compact_pattern = None

        # Only allow compact matching for multi-word or 3+ character aliases.
        # Very short aliases like "me", "ce", "it", and "ee" can appear inside
        # normal Hinglish/Hindi text and cause false department detection.
        if " " in key or len(key) >= 3:
            compact_pattern = r"(?<![a-z])" + re.escape(key).replace(r"\ ", "") + r"(?![a-z])"

        if len(key) < 3 and " " not in key:
            short_code_pattern = (
                rf"\bd[1-4]\s*{re.escape(key)}(?:\s*[a-f])?\b|"
                rf"\b{re.escape(key)}\s*(?:department|dept|branch|faculty|hod|lab|timetable|schedule|section|class)\b|"
                rf"\b(?:department|dept|branch|faculty|hod|lab|timetable|schedule|class)\s*(?:of\s+)?{re.escape(key)}\b"
            )
            if re.search(short_code_pattern, lower):
                return value
            continue

        if re.search(token_pattern, lower) or (compact_pattern and re.search(compact_pattern, lower)):
            return value

    return None


def extract_group(text: str):
    lower = normalize_text(text)

    # catches d1, d2, d3, d4 even in smashed text like d2csa
    m = re.search(r"d[1-4]", lower)
    if m:
        return m.group(0).upper()

    return None


def extract_section(text: str):
    upper = normalize_text(text).upper().strip()

    # 1. standalone section letter
    for sec in SECTIONS:
        if re.search(rf"\b{sec}\b", upper):
            return sec

    # 2. smashed formats like D2CSA / D3CSEB / D4CSD
    m = re.search(r"D[1-4](?:CSE|CS|ECE|EE|IT|CE|ME|APPSC|AS)?([A-F])$", upper)
    if m:
        return m.group(1)

    return None


def build_aliases(group, dept, section):
    aliases = []

    if not group or not dept:
        return aliases

    short = dept
    if dept == "CSE":
        short = "CS"
    elif dept == "CIVIL":
        short = "CE"
    elif dept == "MECHANICAL":
        short = "ME"
    elif dept == "APPSC":
        short = "AS"

    if section:
        aliases.extend([
            f"{group} {short} {section}",
            f"{group}{short}{section}",
            f"{group} {dept} {section}",
            f"{group}{dept}{section}",
        ])

    aliases.extend([
        f"{group} {short}",
        f"{group}{short}",
        f"{group} {dept}",
        f"{group}{dept}",
    ])

    # remove duplicates while preserving order
    unique_aliases = []
    seen = set()

    for alias in aliases:
        normalized = alias.upper().strip()
        if normalized not in seen:
            seen.add(normalized)
            unique_aliases.append(alias)

    return unique_aliases


def extract_teacher_name(text: str, intent: str = "", json_tag: str = ""):
    raw = (text or "").strip()
    if not raw:
        return None

    normalized = normalize_text(raw)
    if not normalized:
        return None

    if re.search(r"\bd[1-4]\b", normalized):
        return None

    if json_tag and json_tag not in {"timetable", "faculty_list", "hod_info"}:
        return None

    if intent and intent not in {"timetable", "department", "general"}:
        return None

    if any(word in normalized for word in NON_TEACHER_QUERY_WORDS):
        return None

    explicit_teacher_query = any(word in normalized for word in ["teacher", "faculty", "timetable", "schedule", "routine", "sir", "madam", "prof", "professor", "dr"])

    cleaned = normalized
    cleaned = re.sub(r"\b(?:teacher|teachers|faculty|sir|madam|mam|maam|professor|prof|pf|dr)\b", " ", cleaned)
    cleaned = re.sub(r"\b(?:timetable|schedule|routine|show|give|me|of|for|ka|ki|ke|da|di|de|please|batao|dasso|kholo|dikhao|do)\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    tokens = [token for token in cleaned.split() if token.isalpha()]
    if not tokens:
        return None

    if len(tokens) > 4:
        return None

    if len(tokens) == 1 and len(tokens[0]) < 4:
        return None

    if any(token in NAME_QUERY_STOPWORDS for token in tokens):
        return None

    if explicit_teacher_query:
        return " ".join(tokens)

    if 2 <= len(tokens) <= 3 and all(len(token) >= 3 for token in tokens):
        return " ".join(tokens)

    return None


def parse_query(text: str, ui_language: str = "auto") -> dict:
    raw_text = (text or "").strip()
    text = normalize_text(raw_text)
    json_match = get_json_match(text)

    dept = extract_department(text)
    group = extract_group(text)
    section = extract_section(text)
    intent = detect_intent(text)
    aliases = build_aliases(group, dept, section)
    teacher_name = extract_teacher_name(raw_text, intent=intent, json_tag=json_match.get("tag") if json_match else "")
    language = choose_language(ui_language, raw_text)
    response_language = detect_response_language(raw_text, language)

    print("\n--- PARSER DEBUG ---")
    print(f"Raw Input:  '{safe_debug_text(raw_text)}'")
    print(f"Normalized: '{safe_debug_text(text)}'")
    print(f"Intent:     {intent}")
    print(f"Department: {dept}")
    print(f"Group:      {group}")
    print(f"Section:    {section}")
    print(f"Aliases:    {aliases}")
    print(f"Teacher:    {safe_debug_text(teacher_name)}")
    print(f"Language:   {language}")
    print(f"Response:   {response_language}")
    print(f"JSON Tag:   {json_match.get('tag') if json_match else None}")
    print("--------------------\n")

    return {
        "raw": raw_text,
        "original": raw_text,
        "normalized": text,
        "language": language,
        "response_language": response_language,
        "intent": intent,
        "department": dept,
        "group": group,
        "section": section,
        "aliases": aliases,
        "teacher_name": teacher_name,
        "json_tag": json_match.get("tag") if json_match else None,
        "json_category": json_match.get("category") if json_match else None,
        "json_answer_mode": json_match.get("answer_mode") if json_match else None,
        "json_links": (json_match.get("links") or []) if json_match else [],
    }
