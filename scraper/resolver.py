import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from chatbot.translator import normalize_multilingual_text
from config import DEPARTMENTS, GNDEC


MAIN_SITE = "https://www.gndec.ac.in/"
ADMISSION_SITE = "https://admission.gndec.ac.in/"
ACADEMICS_SITE = "https://academics.gndec.ac.in/"
EXAM_SITE = "https://exam.gndec.ac.in/"
CSE_SITE = "https://cse.gndec.ac.in/"
ECE_SITE = "https://ece.gndec.ac.in/"
EE_SITE = "https://ee.gndec.ac.in/"
IT_SITE = "https://it.gndec.ac.in/"
CE_SITE = "https://ce.gndec.ac.in/"
ME_SITE = "https://me.gndec.ac.in/"
APPSC_SITE = "https://appsc.gndec.ac.in/"
TNP_SITE = "https://www.tnpgndec.com/"
PRINCIPAL_DESK_LINK = GNDEC["principal_desk"]

HOSTEL_RULES_PDF = "https://gndec.ac.in/sites/default/files/Hostel%20Rules_24.pdf"
FEE_NOTICE_PDF = "https://gndec.ac.in/sites/default/files/fnjd25.pdf"
FEE_STRUCTURE_PAGE = GNDEC.get("fee_structure_page", ADMISSION_SITE)
ACADEMIC_CALENDAR_PDF = "https://www.gndec.ac.in/sites/default/files/ac_jul_dec2025.pdf"
ACADEMIC_CALENDAR_PAGE = GNDEC["academic_calendar_page"]
HOLIDAY_LIST_PAGE = GNDEC["holiday_list_page"]
HOLIDAY_LIST_2026_PDF = GNDEC["holiday_list_2026_pdf"]
EXAM_PORTAL_LINK = GNDEC["exam_portal"]
ACADEMIC_PORTAL_LINK = GNDEC["academic_portal"]
PROGRAMS_LINK = GNDEC["programs"]
HOSTEL_HELP_PDF = GNDEC["hostel_helpline_pdf"]
CSE_TEACHER_TIMETABLE = GNDEC.get("cse_teacher_timetable", CSE_SITE)
ADMISSION_NOTICES_PAGE = GNDEC.get("admission_notices", ADMISSION_SITE)
SRE_PAGE = GNDEC.get("sre_page", ADMISSION_SITE)
SPORTS_DEPARTMENT_PAGE = GNDEC.get("sports_department", MAIN_SITE)
OAT_PAGE = GNDEC.get("oat_page", MAIN_SITE)
CAMPUS_LIFE_PAGE = GNDEC.get("campus_life", MAIN_SITE)

DEPARTMENT_SITES = {
    "CSE": CSE_SITE,
    "ECE": ECE_SITE,
    "EE": EE_SITE,
    "IT": IT_SITE,
    "CIVIL": CE_SITE,
    "MECHANICAL": ME_SITE,
    "APPSC": APPSC_SITE,
}

DEPARTMENT_TIMETABLES = {
    code: data["timetable"]
    for code, data in DEPARTMENTS.items()
}

# Official CSE FET timetable anchors extracted from the published Jan-June 2026
# groups HTML so class-section jumps keep working even if live anchor scraping fails.
CSE_TIMETABLE_ANCHORS = {
    "d2 cs a": "#table_2",
    "d2 cs b": "#table_6",
    "d2 cs c": "#table_10",
    "d2 cs d": "#table_14",
    "d2 cs e": "#table_18",
    "d2 cs f": "#table_22",
    "d3 cs a": "#table_26",
    "d3 cs b": "#table_32",
    "d3 cs c": "#table_38",
    "d3 cs d": "#table_44",
    "d3 cs e": "#table_50",
    "d4 cs a": "#table_57",
    "d4 cs b": "#table_63",
    "d4 cs c": "#table_69",
    "d1 cs a1": "#table_85",
    "d1 cs a2": "#table_87",
    "d1 cs b1": "#table_90",
    "d1 cs b2": "#table_92",
    "d1 cs c1": "#table_95",
    "d1 cs c2": "#table_97",
    "d1 cs d1": "#table_100",
    "d1 cs d2": "#table_102",
    "d1 cs e1": "#table_105",
    "d1 cs e2": "#table_107",
    "d1 cs f1": "#table_110",
    "d1 cs f2": "#table_112",
}

BASE_URLS = [
    MAIN_SITE,
    ADMISSION_SITE,
    ACADEMICS_SITE,
    EXAM_SITE,
    CSE_SITE,
    ECE_SITE,
    EE_SITE,
    IT_SITE,
    CE_SITE,
    ME_SITE,
    APPSC_SITE,
]

DEFAULT_CONTEXT = """
Guru Nanak Dev Engineering College (GNDEC), Ludhiana publishes official information on the main website, admission portal, academics portal, exam portal, and department websites.
Use the linked official resource below for the latest details.
""".strip()

COLLEGE_OVERVIEW_CONTEXT = """
Guru Nanak Dev Engineering College (GNDEC), Ludhiana is a well-known engineering college in Punjab.
The college shares official information about admissions, departments, timetables, examinations, notices, hostel facilities, library services, and student resources through its official GNDEC websites.
Students usually use the main GNDEC website along with the admission, academics, exam, and department portals for the latest updates.
""".strip()

JUNK_PATTERNS = [
    "skip to main content",
    "administration",
    "vision mission goals",
    "balance sheets",
    "mandatory disclosure",
    "annual report",
    "statutory committees",
    "non statutory",
    "service and conduct rules",
    "governance",
    "institutional distinctiveness",
    "newsletter",
    "press release",
    "alumni",
    "cyber crime",
    "public corner",
    "download app",
    "green audit report",
    "national student congress",
    "information corner",
]


def safe_get(url: str, timeout: int = 15):
    return requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=timeout,
    )


def normalize(text: str) -> str:
    normalized = normalize_multilingual_text(text or "")
    normalized = normalized.replace("time table", "timetable")
    normalized = normalized.replace("class schedule", "timetable")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def detect_kind(link: str) -> str:
    if not link:
        return "url"
    lower = link.lower()
    if ".pdf" in lower:
        return "pdf"
    if ".html" in lower or "#table_" in lower:
        return "html"
    return "url"


def classify_query(query: str) -> str:
    q = normalize(query)

    if any(x in q for x in ["timetable", "schedule", "class routine"]) or re.search(r"\bd[1-4]\b", q):
        return "timetable"

    if any(x in q for x in [
        "oat", "open air theatre", "open air theater", "anand utsav",
        "cafeteria", "canteen", "lipton", "happiness station", "blue berry", "blueberry",
        "sports complex", "sports department", "swimming pool", "gym"
    ]):
        return "facility"

    if any(x in q for x in ["holiday list", "holidays", "gazetted holiday", "list of holidays"]):
        return "holiday"

    if any(x in q for x in [
        "admission", "apply", "eligibility", "criteria", "counselling",
        "counseling", "brochure", "admission procedure", "procedure",
        "registration", "documents required", "how to take admission",
        "sre", "sikh religion exam", "sikh religion examination", "sikh minority quota"
    ]):
        return "admission"

    if any(x in q for x in ["girls hostel", "boys hostel", "hostel", "warden", "mess", "accommodation", "hostel rules"]):
        return "hostel"

    if any(x in q for x in ["exam", "examination", "datesheet", "mst", "admit card", "makeup exam", "make up exam", "supplementary", "reappear", "backlog"]):
        return "exam"

    if any(x in q for x in ["fee", "fees", "payment", "scholarship", "tuition"]):
        return "fee"

    if any(x in q for x in ["library", "opac", "books", "digital library"]):
        return "library"

    if any(x in q for x in ["calendar", "holiday list", "academic calendar"]):
        return "calendar"

    if any(x in q for x in [
        "portal", "erp", "attendance", "marks portal", "academic portal",
        "login", "forgot password", "profile update"
    ]):
        return "portal"

    if any(x in q for x in ["result", "results", "sgpa", "cgpa", "marks"]):
        return "result"

    if any(x in q for x in ["notice", "notices", "announcement", "circular"]):
        return "notice"

    if any(x in q for x in [
        "department", "faculty", "hod", "lab",
        "cse", "ece", "ee", "it", "civil", "mechanical", "appsc",
        "branch", "branches", "courses", "programs", "streams"
    ]):
        return "department"

    return "college"


def allowed_bases_for_query(query_type: str):
    if query_type == "facility":
        return [MAIN_SITE, CAMPUS_LIFE_PAGE, OAT_PAGE, SPORTS_DEPARTMENT_PAGE]
    if query_type == "admission":
        return [ADMISSION_SITE, MAIN_SITE, ACADEMICS_SITE]
    if query_type == "exam":
        return [EXAM_SITE, ACADEMICS_SITE, MAIN_SITE]
    if query_type == "fee":
        return [ADMISSION_SITE, MAIN_SITE, ACADEMICS_SITE]
    if query_type == "hostel":
        return [MAIN_SITE]
    if query_type == "library":
        return [MAIN_SITE]
    if query_type == "calendar":
        return [ACADEMICS_SITE, MAIN_SITE]
    if query_type == "result":
        return [EXAM_SITE, ACADEMICS_SITE]
    if query_type == "department":
        return [CSE_SITE, ECE_SITE, EE_SITE, IT_SITE, CE_SITE, ME_SITE, APPSC_SITE, MAIN_SITE]
    if query_type == "timetable":
        return [CSE_SITE, ECE_SITE, EE_SITE, IT_SITE, CE_SITE, ME_SITE, APPSC_SITE]
    return BASE_URLS


def query_keywords(query_type: str):
    mapping = {
        "facility": ["oat", "open air theatre", "canteen", "cafeteria", "lipton", "blue berry", "blueberry", "happiness station", "sports", "gym", "swimming pool", "campus"],
        "admission": ["admission", "eligibility", "criteria", "apply", "counselling", "brochure", "program", "registration", "document"],
        "hostel": ["hostel", "warden", "mess", "girls hostel", "boys hostel", "rules", "accommodation", "room"],
        "exam": ["exam", "examination", "datesheet", "mst", "admit card", "semester", "makeup", "supplementary", "reappear", "backlog"],
        "fee": ["fee", "fees", "payment", "scholarship", "tuition"],
        "library": ["library", "opac", "books", "digital library", "timing", "fine"],
        "calendar": ["calendar", "holiday", "academic calendar", "session", "semester"],
        "result": ["result", "results", "sgpa", "cgpa", "marks", "grade"],
        "notice": ["notice", "notices", "announcement", "circular"],
        "holiday": ["holiday", "holidays", "holiday list"],
        "portal": ["portal", "erp", "attendance", "marks", "login", "password"],
        "department": ["department", "faculty", "hod", "lab", "engineering", "course", "program", "branch"],
        "timetable": ["timetable", "schedule", "class", "section", "d1", "d2", "d3", "d4"],
        "college": ["college", "campus", "programs", "departments", "facilities", "academics"],
    }
    return mapping.get(query_type, [])


def build_campus_resource(query: str, json_tag: str = ""):
    q = normalize(query)

    if json_tag == "oat_info" or any(term in q for term in ["oat", "open air theatre", "open air theater", "anand utsav"]):
        return {
            "reply": "",
            "link": OAT_PAGE,
            "context": (
                "GNDEC's official cultural facilities resource covers the Open Air Theatre (OAT). "
                "It is the campus open venue used for cultural programs, stage events, and large student gatherings. "
                "If you need the exact venue details or latest official description, open the linked OAT resource."
            ),
            "exact": "GNDEC Open Air Theatre",
            "auto_open": False,
        }

    if json_tag == "cafeteria_info" or any(term in q for term in ["cafeteria", "canteen", "lipton", "happiness station", "blue berry", "blueberry"]):
        return {
            "reply": "",
            "link": CAMPUS_LIFE_PAGE,
            "context": (
                "At Guru Nanak Dev Engineering College (GNDEC), Ludhiana, the combination of Lipton, Blue Berry Cafe, "
                "and Happiness Station represents the most recognizable student refreshment layout and campus-food vibe. "
                "The Lipton kiosk works as the go-to point for quick tea and chilled breaks between lectures. "
                "Blue Berry Cafe is the smaller campus cafe known for thicker fruit shakes, coolers, and mocktail-style refreshments. "
                "The Coca-Cola Happiness Station near the Day Scholar Club area is a central open-air hangout where students usually gather to relax and socialize. "
                "For the exact official campus-life reference, open the linked resource below."
            ),
            "exact": "GNDEC cafeteria, Lipton, Blue Berry Cafe, and Happiness Station",
            "auto_open": False,
        }

    if json_tag == "sports_department" or any(term in q for term in ["sports", "gym", "swimming pool"]):
        return {
            "reply": "",
            "link": SPORTS_DEPARTMENT_PAGE,
            "context": (
                "GNDEC's official sports department resource covers sports infrastructure and related campus facilities. "
                "Use the linked page for the latest official details about sports spaces, support, and facility access."
            ),
            "exact": "GNDEC sports department",
            "auto_open": False,
        }

    return None


def build_sre_resource(json_links):
    return {
        "reply": "",
        "link": json_links[0] if json_links else SRE_PAGE,
        "context": (
            "The Sikh Religion Examination (SRE) is the official GNDEC-linked resource used for Sikh Minority quota queries. "
            "Use the official page for eligibility, registration, exam pattern, dates, and related admission guidance."
        ),
        "exact": "Sikh Religion Examination",
        "auto_open": False,
    }


def query_focus_terms(query: str):
    q = normalize(query)

    if any(term in q for term in ["hod", "head of department", "department head"]):
        return ["head of department", "professor and head", "email:", "phone:"]

    if "faculty" in q or "staff" in q:
        return ["list of faculty", "faculty details", "faculty", "staff", "professor", "assistant professor", "associate professor"]

    if "lab" in q or "laboratory" in q:
        return ["laboratories", "laboratory", "lab"]

    if any(term in q for term in ["contact", "phone", "email"]):
        return ["email:", "phone:", "contact"]

    return []


def clean_lines(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue

        lower = line.lower()

        if any(j in lower for j in JUNK_PATTERNS):
            continue

        if len(line) < 25:
            continue

        if len(line.split()) > 45:
            continue

        lines.append(line)

    return "\n".join(lines)


def scrape_text(url: str, max_chars: int = 14000) -> str:
    try:
        if not url or ".pdf" in url.lower():
            return ""

        res = safe_get(url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()

        text = soup.get_text("\n", strip=True)
        return clean_lines(text)[:max_chars]

    except Exception as e:
        print("scrape_text error:", url, e)
        return ""


def scrape_structured_text(url: str, max_chars: int = 14000, min_len: int = 3) -> str:
    try:
        if not url or ".pdf" in url.lower():
            return ""

        res = safe_get(url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        lines = []
        for line in soup.get_text("\n", strip=True).splitlines():
            line = re.sub(r"\s+", " ", line).strip()
            if not line:
                continue
            lower = line.lower()
            if any(j in lower for j in JUNK_PATTERNS):
                continue
            if len(line) < min_len:
                continue
            lines.append(line)

        return "\n".join(lines)[:max_chars]
    except Exception as e:
        print("scrape_structured_text error:", url, e)
        return ""


def score_text(query: str, text: str) -> int:
    q_words = [w for w in normalize(query).split() if len(w) > 2]
    t = normalize(text)
    score = 0
    for w in q_words:
        if w in t:
            score += 2
    return score


def extract_department_from_query(parsed):
    if isinstance(parsed, dict) and parsed.get("department"):
        return parsed["department"]

    q = normalize(parsed if isinstance(parsed, str) else parsed.get("raw", ""))

    if "cse" in q or "computer science" in q:
        return "CSE"
    if "ece" in q:
        return "ECE"
    if re.search(r"\bee\b", q):
        return "EE"
    if re.search(r"\bit\b", q):
        return "IT"
    if "civil" in q or re.search(r"\bce\b", q):
        return "CIVIL"
    if "mechanical" in q or re.search(r"\bme\b", q):
        return "MECHANICAL"
    if "appsc" in q or "applied science" in q:
        return "APPSC"
    return None


def extract_group_section(parsed):
    if isinstance(parsed, dict):
        return parsed.get("group"), parsed.get("section")

    q = normalize(parsed).upper()
    m_group = re.search(r"\bD([1-4])\b", q)
    group = f"D{m_group.group(1)}" if m_group else None
    m_section = re.search(r"\b([A-F])\b", q)
    section = m_section.group(1) if m_section else None
    return group, section


def build_teacher_aliases(teacher_name: str):
    normalized_name = normalize(teacher_name)
    words = [word for word in re.findall(r"[a-z]+", normalized_name) if word not in {"dr", "pf", "prof", "professor", "mr", "mrs", "ms", "er"}]
    if not words:
        return set()

    aliases = {" ".join(words)}
    if len(words) >= 2:
        aliases.add(words[-1])
        aliases.add(f"{words[0]} {words[-1]}")
    if len(words) >= 2:
        aliases.add("".join(word[0] for word in words))

    for prefix in ["dr", "pf", "prof", "professor"]:
        aliases.add(f"{prefix} {' '.join(words)}")

    return {normalize(alias) for alias in aliases if alias.strip()}


def extract_year_score(text: str) -> int:
    matches = re.findall(r"20\d{2}", text)
    latest = max((int(item) for item in matches), default=0)
    return max(0, latest - 2000)


def extract_term_score(text: str) -> int:
    normalized = normalize(text)
    if "jan june" in normalized or "jan-june" in normalized or "jan may" in normalized:
        return 2
    if "july dec" in normalized or "july-dec" in normalized or "jul dec" in normalized:
        return 1
    return 0


def strict_filter(query: str, link: str, text: str) -> bool:
    q = normalize(query)
    l = normalize((link or "") + " " + (text or ""))

    if "admission" in q and "admission" not in l:
        return False
    if "hostel" in q and "hostel" not in l:
        return False
    if "warden" in q and not ("warden" in l or "hostel" in l):
        return False
    if "exam" in q and not ("exam" in l or "datesheet" in l or "examination" in l):
        return False
    if "datesheet" in q and not ("datesheet" in l or "exam" in l):
        return False
    if "fee" in q and not ("fee" in l or "fees" in l or "payment" in l or "scholarship" in l):
        return False
    if "library" in q and "library" not in l:
        return False
    if any(word in q for word in ["branch", "branches", "courses", "programs", "streams"]):
        if not any(x in l for x in ["program", "course", "b.tech", "m.tech", "mba", "mca", "bca", "bba", "department"]):
            return False

    return True


def topic_boost(query_type: str, full_link: str, anchor_text: str) -> int:
    link_l = normalize(full_link)
    anchor_l = normalize(anchor_text)
    boost = 0

    if query_type == "admission":
        if "admission.gndec.ac.in" in link_l:
            boost += 35
        if "admission" in link_l:
            boost += 18
        if any(k in anchor_l for k in ["admission", "apply", "eligibility", "criteria", "brochure", "program"]):
            boost += 12
    elif query_type == "hostel":
        if "hostel" in link_l:
            boost += 26
        if any(k in anchor_l for k in ["hostel", "warden", "mess", "rules", "girls hostel", "boys hostel"]):
            boost += 12
    elif query_type == "exam":
        if "exam.gndec.ac.in" in link_l:
            boost += 26
        if "datesheet" in link_l or "exam" in link_l:
            boost += 16
        if any(k in anchor_l for k in ["exam", "datesheet", "mst", "admit card"]):
            boost += 10
    elif query_type == "fee":
        if "fee" in link_l or "fees" in link_l:
            boost += 18
        if any(k in anchor_l for k in ["fee", "fees", "payment", "scholarship"]):
            boost += 10
    elif query_type == "library":
        if "library" in link_l:
            boost += 18
        if any(k in anchor_l for k in ["library", "opac", "books"]):
            boost += 10
    elif query_type == "calendar":
        if "academic" in link_l or "calendar" in link_l:
            boost += 16
    elif query_type == "result":
        if "exam" in link_l or "result" in link_l:
            boost += 16
    elif query_type == "department":
        if any(k in link_l for k in ["cse", "ece", "ee", "it", "ce", "me", "appsc", "program", "course"]):
            boost += 12

    return boost


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += max(1, chunk_size - overlap)
    return chunks


def extract_relevant_chunks(query: str, text: str, top_k: int = 4):
    q_type = classify_query(query)
    keywords = query_keywords(q_type)
    chunks = chunk_text(text)
    ranked = []

    for chunk in chunks:
        chunk_l = normalize(chunk)
        score = score_text(query, chunk)

        for keyword in keywords:
            if keyword in chunk_l:
                score += 4

        if any(j in chunk_l for j in JUNK_PATTERNS):
            score -= 12

        if score > 0:
            ranked.append((score, chunk.strip()))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in ranked[:top_k]]


def exact_extract(query: str, text: str) -> str:
    q_type = classify_query(query)
    lines = [re.sub(r"\s+", " ", item).strip() for item in text.splitlines() if item.strip()]
    useful = []
    keys = query_keywords(q_type)
    focus_terms = query_focus_terms(query)

    if focus_terms:
        for index, line in enumerate(lines):
            lower = line.lower()

            if any(j in lower for j in JUNK_PATTERNS):
                continue

            if any(term in lower for term in focus_terms):
                start = max(0, index - 1)
                end = min(len(lines), index + 5)
                return "\n".join(lines[start:end])

    for line in lines:
        lower = line.lower()

        if any(j in lower for j in JUNK_PATTERNS):
            continue

        if keys and any(key in lower for key in keys):
            useful.append(line)

        if len(useful) >= 10:
            break

    return "\n".join(useful[:8])


def find_department_resource(parsed):
    query = parsed.get("raw", "") or parsed.get("normalized", "")
    department_code = parsed.get("department")
    department_link = DEPARTMENTS.get(department_code, {}).get("page")

    if not department_link:
        return MAIN_SITE, "", ""

    normalized_query = normalize(query)
    try:
        res = safe_get(department_link)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        print("find_department_resource error:", department_link, e)
        page_context = scrape_structured_text(department_link, 14000, min_len=3)
        exact = exact_extract(query, page_context)
        return department_link, page_context, exact

    candidates = [{
        "title": "Department Home",
        "link": department_link,
        "score": 10,
    }]

    for anchor in soup.find_all("a", href=True):
        title = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True)).strip()
        full_link = urljoin(department_link, anchor["href"])
        combined = normalize(f"{title} {full_link}")
        score = 0

        if "faculty" in normalized_query:
            if "list of faculty" in combined:
                score += 120
            if "faculty details" in combined:
                score += 90
            if "faculty" in combined or "staff" in combined:
                score += 70
            if ".pdf" in full_link.lower():
                score += 20
            if any(term in combined for term in ["publication", "journals", "conference", "grants", "workshop", "consultancy"]):
                score -= 120

        if any(term in normalized_query for term in ["hod", "head of department", "department head", "contact", "phone", "email"]):
            if "head of department" in combined:
                score += 120
            if "about us" in combined:
                score += 90
            if "department home" in combined or full_link.rstrip("/") == department_link.rstrip("/"):
                score += 80
            if "faculty" in combined:
                score -= 20

        if "lab" in normalized_query or "laboratory" in normalized_query:
            if "laboratories" in combined or "lab" in combined:
                score += 90

        if score > 0:
            candidates.append({
                "title": title or "Department Resource",
                "link": full_link,
                "score": score,
            })

    best = max(candidates, key=lambda item: item["score"])
    best_link = best["link"]

    if "faculty" in normalized_query and ".pdf" not in best_link.lower():
        try:
            res = safe_get(best_link)
            res.raise_for_status()
            inner_soup = BeautifulSoup(res.text, "html.parser")
            pdf_candidates = []
            for anchor in inner_soup.find_all("a", href=True):
                title = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True)).strip()
                full_link = urljoin(best_link, anchor["href"])
                combined = normalize(f"{title} {full_link}")
                score = 0
                if "list of faculty" in combined:
                    score += 120
                if "faculty details" in combined:
                    score += 90
                if "faculty" in combined:
                    score += 60
                if any(term in combined for term in ["publication", "journals", "conference", "grants", "workshop", "consultancy"]):
                    score -= 120
                if ".pdf" in full_link.lower():
                    score += 25
                if score > 0:
                    pdf_candidates.append((score, full_link))
            if pdf_candidates:
                pdf_candidates.sort(reverse=True)
                best_link = pdf_candidates[0][1]
        except Exception as e:
            print("find_department_resource nested error:", best_link, e)

    if ".pdf" in best_link.lower():
        return best_link, "", ""

    page_context = scrape_structured_text(best_link, 14000, min_len=3)
    exact = exact_extract(query, page_context)
    return best_link, page_context, exact


def find_best_resource(query: str):
    best_link = None
    best_page_text = ""
    best_score = -1
    query_type = classify_query(query)
    q = normalize(query)

    if query_type == "admission":
        return ADMISSION_SITE, scrape_text(ADMISSION_SITE, 12000)

    if query_type == "hostel":
        if any(x in q for x in ["warden", "contact", "helpline", "girls hostel", "boys hostel"]):
            return HOSTEL_HELP_PDF, ""
        return HOSTEL_RULES_PDF, ""

    if query_type == "fee":
        return FEE_NOTICE_PDF, ""

    if query_type == "calendar":
        link, context, exact = find_academic_calendar_resource(query)
        page_text = (exact + "\n\n" + context).strip() if exact else context
        return link, page_text

    if query_type == "holiday":
        return HOLIDAY_LIST_2026_PDF, ""

    if query_type == "department" and any(x in q for x in ["branch", "branches", "courses", "programs", "streams"]):
        return PROGRAMS_LINK, scrape_text(PROGRAMS_LINK, 12000)

    if query_type == "portal":
        return ACADEMIC_PORTAL_LINK, scrape_text(ACADEMIC_PORTAL_LINK, 12000)

    if query_type == "exam":
        if any(x in q for x in ["re evaluation", "reevaluation", "re-evaluation", "admit card", "backlog", "reappear", "supplementary", "makeup", "make up", "date sheet", "datesheet", "internal marks"]):
            return EXAM_PORTAL_LINK, scrape_text(EXAM_PORTAL_LINK, 12000)

    for base in allowed_bases_for_query(query_type):
        try:
            res = safe_get(base)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            page_text = soup.get_text(" ", strip=True)
            page_score = score_text(query, page_text)

            if query_type == "admission" and "admission.gndec.ac.in" in base.lower():
                page_score += 20
            elif query_type == "exam" and ("exam" in base.lower() or "academics" in base.lower()):
                page_score += 15
            elif query_type == "library" and "library" in base.lower():
                page_score += 15

            if page_score > best_score:
                best_score = page_score
                best_link = base
                best_page_text = page_text[:12000]

            for anchor in soup.find_all("a", href=True):
                anchor_text = anchor.get_text(" ", strip=True)
                href = anchor["href"].strip()
                full_link = urljoin(base, href)

                if not strict_filter(query, full_link, anchor_text):
                    continue

                score = score_text(query, anchor_text + " " + href)
                score += topic_boost(query_type, full_link, anchor_text)

                if score > best_score:
                    best_score = score
                    best_link = full_link
                    best_page_text = page_text[:12000]

        except Exception as e:
            print("find_best_resource error:", base, e)

    return best_link, best_page_text


def find_academic_calendar_resource(query: str):
    try:
        res = safe_get(ACADEMIC_CALENDAR_PAGE)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        print("find_academic_calendar_resource error:", e)
        return ACADEMIC_CALENDAR_PAGE, "Official academic calendar page for GNDEC.", ""

    requested_years = re.findall(r"20\d{2}", query or "")
    requested_year = int(requested_years[0]) if requested_years else None

    resources = []
    for anchor in soup.find_all("a", href=True):
        title = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True)).strip()
        href = urljoin(ACADEMIC_CALENDAR_PAGE, anchor["href"])
        combined = normalize(f"{title} {href}")

        if "academic calendar" not in combined:
            continue

        years = [int(item) for item in re.findall(r"20\d{2}", title)]
        latest_year = max(years) if years else 0
        score = latest_year

        if requested_year and requested_year in years:
            score += 5000

        if "july" in combined or "jul" in combined:
            score += 15
        if "revised" in combined:
            score -= 2

        resources.append({
            "title": title,
            "href": href,
            "years": years,
            "score": score,
        })

    if not resources:
        return ACADEMIC_CALENDAR_PAGE, "Official academic calendar page for GNDEC.", ""

    resources.sort(key=lambda item: item["score"], reverse=True)
    best = resources[0]
    available_years = sorted({year for item in resources for year in item["years"]}, reverse=True)

    if requested_year and requested_year not in available_years:
        context = (
            f"Requested academic calendar year: {requested_year}. "
            f"No official academic calendar for {requested_year} was found on the GNDEC page. "
            f"Latest listed calendar found: {best['title']}."
        )
    else:
        context = f"Latest official academic calendar resource found: {best['title']}."

    return best["href"], context, best["title"]


def collect_timetable_resources(timetable_page: str):
    try:
        res = safe_get(timetable_page)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        print("collect_timetable_resources error:", timetable_page, e)
        return []

    resources = []
    for anchor in soup.find_all("a", href=True):
        title = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True)).strip()
        href = urljoin(timetable_page, anchor["href"])

        if not title:
            continue

        combined = normalize(title + " " + href)
        if not any(keyword in combined for keyword in ["timetable", "time table", "students", "student", "groups", "group"]):
            continue

        resources.append({
            "title": title,
            "href": href,
            "kind": detect_kind(href),
        })

    return resources


def score_timetable_resource(item, department_code: str):
    title = item["title"]
    href = item["href"]
    combined = normalize(title + " " + href)
    score = 0

    if "student" in combined or "students" in combined or "group" in combined or "groups" in combined:
        score += 40
    if "ug" in combined:
        score += 18
    if "ph.d" in combined or "phd" in combined or "minor degree" in combined:
        score -= 12
    if "faculty" in combined or "class room" in combined or "rooms" in combined:
        score -= 30
    if item["kind"] == "html":
        score += 10

    score += extract_year_score(combined) * 5
    score += extract_term_score(combined) * 10

    dept_token = (department_code or "").lower()
    if dept_token and dept_token in combined:
        score += 6

    return score


def find_best_group_anchor(resource_url: str, aliases):
    try:
        res = safe_get(resource_url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        print("find_best_group_anchor error:", resource_url, e)
        return None, None

    alias_set = {normalize(alias) for alias in aliases if alias}
    best_score = -1
    best_match = None

    for anchor in soup.find_all("a", href=True):
        label = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True)).strip()
        href = anchor["href"].strip()

        if not label:
            continue

        normalized_label = normalize(label)
        score = 0

        for alias in alias_set:
            if normalized_label == alias:
                score += 100
            elif alias in normalized_label:
                score += 60

        if re.search(r"\bd[1-4]\b", normalized_label):
            score += 10

        if href.startswith("#table_"):
            score += 18

        if score > best_score:
            best_score = score
            best_match = {
                "label": label,
                "url": urljoin(resource_url, href),
            }

    if best_score <= 0:
        return None, None

    return best_match["url"], best_match["label"]


def find_best_teacher_anchor(resource_url: str, teacher_name: str):
    try:
        res = safe_get(resource_url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        print("find_best_teacher_anchor error:", resource_url, e)
        return None, None

    alias_set = build_teacher_aliases(teacher_name)
    if not alias_set:
        return None, None

    best_score = -1
    best_match = None

    for anchor in soup.find_all("a", href=True):
        label = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True)).strip()
        href = anchor["href"].strip()
        if not label:
            continue

        normalized_label = normalize(label)
        score = 0

        for alias in alias_set:
            if normalized_label == alias:
                score += 120
            elif alias in normalized_label:
                score += 80
            elif normalized_label in alias:
                score += 30

        if "(" in label and ")" in label:
            score += 8
        if href.startswith("#"):
            score += 18

        if score > best_score:
            best_score = score
            best_match = {
                "label": label,
                "url": urljoin(resource_url, href),
            }

    if best_score <= 0:
        return None, None

    return best_match["url"], best_match["label"]


def find_static_cse_group_anchor(resource_url: str, aliases):
    alias_set = {normalize(alias) for alias in aliases if alias}
    for alias in alias_set:
        fragment = CSE_TIMETABLE_ANCHORS.get(alias)
        if fragment:
            return urljoin(resource_url, fragment), alias.upper()
    return None, None


def find_timetable_link(parsed):
    query = parsed.get("raw", "")
    department_code = extract_department_from_query(parsed) or "CSE"
    teacher_name = parsed.get("teacher_name")
    timetable_page = DEPARTMENT_TIMETABLES.get(department_code, DEPARTMENT_TIMETABLES["CSE"])
    department_page = DEPARTMENT_SITES.get(department_code, DEPARTMENT_SITES["CSE"])
    group, section = extract_group_section(parsed)
    aliases = parsed.get("aliases") or []

    if teacher_name:
        teacher_resource = CSE_TEACHER_TIMETABLE
        anchor_url, matched_label = find_best_teacher_anchor(teacher_resource, teacher_name)
        final_url = anchor_url or teacher_resource
        teacher_label = matched_label or teacher_name.title()
        context = f"Matched exact teacher timetable section {teacher_label} for {teacher_name.title()}." if matched_label else f"Opened the official CSE teacher timetable resource for {teacher_name.title()}."
        return {
            "reply": "",
            "link": final_url,
            "context": context,
            "exact": teacher_label,
            "auto_open": True,
        }

    resources = collect_timetable_resources(timetable_page)
    if not resources:
        resources = [{"title": "Department timetable page", "href": timetable_page, "kind": detect_kind(timetable_page)}]

    best_resource = max(resources, key=lambda item: score_timetable_resource(item, department_code))
    final_url = best_resource["href"]
    matched_label = None

    if best_resource["kind"] == "html" and aliases:
        anchor_url, matched_label = find_best_group_anchor(best_resource["href"], aliases)
        if not anchor_url and department_code == "CSE":
            anchor_url, matched_label = find_static_cse_group_anchor(best_resource["href"], aliases)
        if anchor_url:
            final_url = anchor_url

    class_name = " ".join(part for part in [group, department_code if department_code != "CIVIL" else "CE", section] if part)
    if matched_label:
        context = f"Matched exact timetable section {matched_label} for {class_name or query}."
    elif class_name:
        context = f"Opened the most relevant official {department_code} timetable resource for {class_name}."
    else:
        context = f"Opened the latest official {department_code} timetable resource."

    return {
        "reply": "",
        "link": final_url or timetable_page or department_page,
        "context": context,
        "exact": matched_label or class_name,
        "auto_open": True,
    }


def resolve_official_query(parsed):
    query = parsed.get("raw", "") or parsed.get("normalized", "")
    query_type = classify_query(query)
    department_code = parsed.get("department")
    json_tag = parsed.get("json_tag")
    json_links = parsed.get("json_links") or []

    if parsed.get("teacher_name"):
        return find_timetable_link(parsed)

    if query_type == "timetable":
        return find_timetable_link(parsed)

    if json_tag in ["placement_support", "placement_stats_department"]:
        return {
            "reply": "",
            "link": json_links[0] if json_links else TNP_SITE,
            "context": "Official GNDEC training and placement resource for placement drives, registration, internships, and department placement updates.",
            "exact": "GNDEC Training and Placement resource",
            "auto_open": False,
        }

    campus_resource = build_campus_resource(query, json_tag=json_tag or "")
    if campus_resource:
        return campus_resource

    if json_tag == "sre_exam":
        return build_sre_resource(json_links)

    if json_tag == "previous_papers":
        return {
            "reply": "",
            "link": json_links[0] if json_links else MAIN_SITE,
            "context": "Official previous question paper and academic search resource for GNDEC students.",
            "exact": "Previous question paper resource",
            "auto_open": False,
        }

    if json_tag == "student_documents":
        return {
            "reply": "",
            "link": json_links[0] if json_links else MAIN_SITE,
            "context": "GNDEC administrative support queries such as bonafide certificate, branch change, and office contacts are usually handled through official college offices and notices.",
            "exact": "GNDEC administrative support",
            "auto_open": False,
        }

    if json_tag in {"admin_document_approval", "administrator_contact"}:
        return {
            "reply": "",
            "link": json_links[0] if json_links else MAIN_SITE,
            "context": "GNDEC administrative coordination, office contact, and document approval support are generally handled through official notices, office routes, and college administration channels.",
            "exact": "GNDEC administrative coordination",
            "auto_open": False,
        }

    if json_tag == "principal_info" or "principal" in normalize(query):
        principal_context = scrape_structured_text(PRINCIPAL_DESK_LINK, 14000, min_len=3)
        if not principal_context:
            principal_context = scrape_text(PRINCIPAL_DESK_LINK, 14000)
        if not principal_context:
            principal_context = "Official GNDEC principal desk resource."
        return {
            "reply": "",
            "link": PRINCIPAL_DESK_LINK,
            "context": principal_context,
            "exact": "GNDEC Principal Desk",
            "auto_open": False,
        }

    if query_type == "college":
        return {
            "reply": "",
            "link": MAIN_SITE,
            "context": COLLEGE_OVERVIEW_CONTEXT,
            "exact": "GNDEC college overview",
            "auto_open": False,
        }

    if query_type == "department" and department_code and any(
        term in normalize(query) for term in ["hod", "head of department", "faculty", "staff", "lab", "contact", "phone", "email"]
    ):
        department_link, page_context, exact = find_department_resource(parsed)
        context = exact if exact else page_context[:1800]
        return {
            "reply": "",
            "link": department_link or MAIN_SITE,
            "context": context or DEFAULT_CONTEXT,
            "exact": exact,
            "auto_open": False,
        }

    if query_type == "portal":
        return {
            "reply": "",
            "link": ACADEMIC_PORTAL_LINK,
            "context": "GNDEC students generally use the academics portal for attendance, marks, and profile-related academic access.",
            "exact": "GNDEC academic portal",
            "auto_open": False,
        }

    if query_type == "facility":
        facility_resource = build_campus_resource(query, json_tag=json_tag or "")
        if facility_resource:
            return facility_resource

    if json_links:
        fallback_contexts = {
            "admission_contact": "Official GNDEC admission help resource for admission cell details and portal access.",
            "admission_documents": "Official GNDEC admission resource for document checklist and application guidance.",
            "management_quota": "Official GNDEC admission resource for seat categories, counseling, and admission-related details.",
            "sre_exam": "Official GNDEC Sikh Religion Examination resource for Sikh Minority quota eligibility, dates, pattern, and registration details.",
            "syllabus_query": "Official GNDEC academic resource for syllabus, academic structure, and subject-related details.",
            "fee_structure": "Official GNDEC fee resource for fee notices, fee structure, and payment-related updates.",
            "fee_deadline": "Official GNDEC fee resource for fee due dates and payment notices.",
            "late_fee": "Official GNDEC fee resource for payment notices and applicable fee-related conditions.",
            "online_fee_payment": "Official GNDEC academic or fee portal resource for payment access and student fee services.",
            "hostel_fee": "Official GNDEC hostel or fee-related resource for hostel and mess charges.",
            "hostel_apply": "Official GNDEC resource for hostel process and admission-related hostel support.",
            "cafeteria_info": "Official GNDEC campus resource for general campus-facility context and student hangout areas.",
            "sports_department": "Official GNDEC sports department resource for sports infrastructure, charges, and contact information.",
            "oat_info": "Official GNDEC cultural facilities resource for the Open Air Theatre and event venue details.",
            "library_access": "Official GNDEC library resource for OPAC, timings, e-books, and library support.",
            "latest_notices": "Official GNDEC main website resource for latest notices, circulars, and announcements.",
            "academic_portal": "Official GNDEC academics portal for student academic access such as attendance, marks, and login-related services.",
            "department_website": "Official GNDEC department website resource.",
            "lab_facilities": "Official GNDEC department resource for lab and infrastructure-related information.",
            "admin_document_approval": "Relevant GNDEC administrative resource for digital document approval requests, document submission guidance, and follow-up support.",
            "administrator_contact": "Relevant GNDEC administrative support resource for contacting administrators and office support teams.",
        }
        return {
            "reply": "",
            "link": json_links[0],
            "context": fallback_contexts.get(json_tag, "Relevant official GNDEC resource found for this query."),
            "exact": json_tag.replace("_", " ") if json_tag else "",
            "auto_open": False,
        }

    link, page_text = find_best_resource(query)

    if not link:
        return {
            "reply": "",
            "link": MAIN_SITE,
            "context": DEFAULT_CONTEXT,
            "exact": "",
            "auto_open": False,
        }

    page_context = scrape_text(link, 14000)
    if not page_context:
        page_context = clean_lines(page_text)

    exact = exact_extract(query, page_context)
    chunks = extract_relevant_chunks(query, page_context, top_k=4)

    if exact.strip():
        context = exact + "\n\n" + "\n\n".join(chunks[:2])
    else:
        context = "\n\n".join(chunks) if chunks else page_context[:1400]

    if query_type == "college" and not context.strip():
        context = DEFAULT_CONTEXT
    elif not context.strip():
        context = exact if exact else page_context[:800]

    return {
        "reply": "",
        "link": link,
        "context": context,
        "exact": exact,
        "auto_open": False,
    }
