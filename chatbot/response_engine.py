import re
from io import BytesIO

import pdfplumber
import requests

from scraper.resolver import classify_query, resolve_official_query
from chatbot.translator import normalize_multilingual_text

try:
    from google import genai
except Exception:
    genai = None

from config import GEMINI_API_KEY


def normalize_chat_text(text: str) -> str:
    normalized = normalize_multilingual_text(text or "")
    normalized = re.sub(r"[^0-9a-zA-Z\u0900-\u097F\u0A00-\u0A7F\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized


def is_hindi(lang: str) -> bool:
    return lang in {"hi", "hi_native"}


def is_punjabi(lang: str) -> bool:
    return lang in {"pa", "pa_native"}


def is_native_hindi(lang: str) -> bool:
    return lang == "hi_native"


def is_native_punjabi(lang: str) -> bool:
    return lang == "pa_native"


def base_lang(lang: str) -> str:
    if is_hindi(lang):
        return "hi"
    if is_punjabi(lang):
        return "pa"
    return "en"


def safe_debug_text(value: str) -> str:
    try:
        return str(value).encode("cp1252", errors="replace").decode("cp1252")
    except Exception:
        return repr(value)


def is_greeting(query: str) -> bool:
    text = normalize_chat_text(query)
    if not text or len(text.split()) > 6:
        return False

    phrases = [
        "hi", "hello", "hey", "namaste", "sat sri akal", "hii", "helo",
        "ki haal", "kya haal", "hello ji", "hi ji", "hello bot", "hello chatbot",
        "नमस्ते", "नमस्कार", "ਸਤ ਸ੍ਰੀ ਅਕਾਲ"
    ]
    return any(text == item or text.startswith(f"{item} ") for item in phrases)


def is_goodbye(query: str) -> bool:
    text = normalize_chat_text(query)
    if not text or len(text.split()) > 6:
        return False

    phrases = [
        "bye", "goodbye", "bye bye", "see you", "ok bye", "tata",
        "rab rakha", "phir milenge", "milde haan", "अलविदा", "फिर मिलेंगे", "ਰੱਬ ਰਾਖਾ"
    ]
    return text in phrases


def is_thanks(query: str) -> bool:
    text = normalize_chat_text(query)
    if not text or len(text.split()) > 6:
        return False

    phrases = [
        "thanks", "thank you", "thx", "ty", "shukriya", "dhanyavad",
        "bohat shukriya", "thank you so much", "धन्यवाद", "शुक्रिया", "ਧੰਨਵਾਦ"
    ]
    return text in phrases


def is_how_are_you(query: str) -> bool:
    text = normalize_chat_text(query)
    phrases = [
        "how are you", "how are you doing", "kaise ho", "kive ho",
        "kidda", "ki haal", "ki haal chaal", "kya haal hai",
        "आप कैसे हैं", "तुम कैसे हो", "ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ"
    ]
    return text in phrases


def greeting(lang: str) -> str:
    if is_native_hindi(lang):
        return "नमस्ते! मैं आपका GNDEC चैटबॉट हूँ। मैं आपकी कैसे सहायता कर सकता हूँ?"
    if is_native_punjabi(lang):
        return "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ ਤੁਹਾਡਾ GNDEC ਚੈਟਬੋਟ ਹਾਂ। ਮੈਂ ਤੁਹਾਡੀ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?"
    if is_hindi(lang):
        return "Hello! I am your GNDEC chatbot. How can I help you?"
    if is_punjabi(lang):
        return "Hello! I am your GNDEC chatbot. How can I help you?"
    return "Hello! I am your GNDEC chatbot. How can I help you?"


def goodbye(lang: str) -> str:
    if is_native_hindi(lang):
        return "अलविदा! अगर आपको टाइमटेबल, एडमिशन, परीक्षा, हॉस्टल या GNDEC से जुड़ी किसी भी जानकारी में मदद चाहिए हो, तो फिर से संदेश करिए।"
    if is_native_punjabi(lang):
        return "ਅਲਵਿਦਾ! ਜੇ ਤੁਹਾਨੂੰ ਟਾਈਮਟੇਬਲ, ਦਾਖਲਾ, ਇਮਤਿਹਾਨ, ਹੋਸਟਲ ਜਾਂ GNDEC ਨਾਲ ਸੰਬੰਧਿਤ ਕਿਸੇ ਵੀ ਜਾਣਕਾਰੀ ਵਿੱਚ ਮਦਦ ਚਾਹੀਦੀ ਹੋਵੇ, ਤਾਂ ਮੁੜ ਸੰਦੇਸ਼ ਕਰ ਦਿਓ।"
    if is_hindi(lang):
        return "Goodbye! Agar aapko timetable, admission, exam, hostel, ya kisi bhi GNDEC query mein help chahiye ho, phir se message kar dena."
    if is_punjabi(lang):
        return "Goodbye! Je tuhanu timetable, admission, exam, hostel, jaan kise vi GNDEC query vich help chahidi hove, dubara message kar dena."
    return "Goodbye! If you need help with timetables, admissions, exams, hostel, or any GNDEC query, just message again."


def thanks_reply(lang: str) -> str:
    if is_native_hindi(lang):
        return "आपका स्वागत है! आप GNDEC से जुड़ा कोई भी और प्रश्न पूछ सकते हैं।"
    if is_native_punjabi(lang):
        return "ਤੁਹਾਡਾ ਸਵਾਗਤ ਹੈ! ਤੁਸੀਂ GNDEC ਨਾਲ ਸੰਬੰਧਿਤ ਹੋਰ ਕੋਈ ਵੀ ਪ੍ਰਸ਼ਨ ਪੁੱਛ ਸਕਦੇ ਹੋ।"
    if is_hindi(lang):
        return "You are welcome! Aap aur bhi koi GNDEC query pooch sakte ho."
    if is_punjabi(lang):
        return "You are welcome! Tusi hor vi koi GNDEC query puch sakde ho."
    return "You're welcome! Feel free to ask any other GNDEC query."


def how_are_you_reply(lang: str) -> str:
    if is_native_hindi(lang):
        return "मैं पूरी तरह तैयार हूँ और आपकी मदद के लिए यहाँ हूँ। आप GNDEC के बारे में कुछ भी पूछ सकते हैं।"
    if is_native_punjabi(lang):
        return "ਮੈਂ ਪੂਰੀ ਤਰ੍ਹਾਂ ਤਿਆਰ ਹਾਂ ਅਤੇ ਤੁਹਾਡੀ ਮਦਦ ਲਈ ਇੱਥੇ ਹਾਂ। ਤੁਸੀਂ GNDEC ਬਾਰੇ ਕੁਝ ਵੀ ਪੁੱਛ ਸਕਦੇ ਹੋ।"
    if is_hindi(lang):
        return "Main bilkul ready hoon aur aapki help ke liye yahan hoon. Aap GNDEC ke baare mein kuch bhi pooch sakte ho."
    if is_punjabi(lang):
        return "Main bilkul ready haan te tuhadi help layi ithe haan. Tusi GNDEC bare kujh vi puch sakde ho."
    return "I am doing well and I am here to help you. You can ask me anything about GNDEC."


def build_meta(link: str, auto_open: bool = False):
    if not link:
        return None

    lower = link.lower()
    if ".pdf" in lower:
        label = "Open PDF"
    elif "#table_" in lower:
        label = "Open Exact Timetable"
    else:
        label = "Open Official Resource"

    return {
        "title": "Official GNDEC Resource",
        "link": link,
        "kind": "pdf" if ".pdf" in lower else "url",
        "open_label": label,
        "auto_open": auto_open,
    }


def extract_pdf_text(url: str, max_chars: int = 5000) -> str:
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        response.raise_for_status()

        text = ""
        with pdfplumber.open(BytesIO(response.content)) as pdf:
            for page in pdf.pages[:6]:
                text += "\n" + (page.extract_text() or "")

        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as e:
        print("PDF extract error:", e)
        return ""


def clean_context(context: str, query: str) -> str:
    if not context:
        return ""

    query_lower = (query or "").lower()
    junk_words = [
        "newsletter", "press release", "alumni", "cyber crime", "download app",
        "vision mission", "mandatory disclosure", "balance sheets",
        "statutory committees", "public corner", "skip to main content", "national student congress"
    ]

    lines = re.split(r"[\n\r]+", context)
    filtered = []
    query_type = classify_query(query)
    detail_query = query_type == "department" and any(
        term in query_lower for term in ["hod", "head of department", "faculty", "staff", "contact", "phone", "email", "lab", "laboratory"]
    )

    for line in lines:
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue

        lower = line.lower()

        if any(item in lower for item in junk_words):
            continue

        if "admission" in query_lower and not any(key in lower for key in [
            "admission", "eligibility", "criteria", "apply", "counselling",
            "counseling", "program", "registration", "document", "brochure"
        ]):
            continue

        if "hostel" in query_lower and not any(key in lower for key in [
            "hostel", "warden", "mess", "room", "rules", "girls hostel", "boys hostel", "accommodation"
        ]):
            continue

        if any(word in query_lower for word in ["exam", "datesheet", "examination"]) and not any(key in lower for key in [
            "exam", "datesheet", "mst", "semester", "admit card", "examination"
        ]):
            continue

        if any(word in query_lower for word in ["fee", "fees"]) and not any(key in lower for key in [
            "fee", "fees", "payment", "scholarship", "tuition"
        ]):
            continue

        if any(word in query_lower for word in ["branch", "branches", "courses", "programs", "streams"]) and not any(key in lower for key in [
            "program", "course", "b.tech", "m.tech", "mba", "mca", "bca", "bba", "department"
        ]):
            continue

        if not detail_query and len(line) < 20:
            continue

        filtered.append(line)

    cleaned = "\n".join(filtered).strip() if detail_query else " ".join(filtered).strip()
    return cleaned[:2400]


def extract_hod_info(context: str):
    lines = [re.sub(r"\s+", " ", line).strip() for line in re.split(r"[\n\r]+", context or "") if line.strip()]

    for index, line in enumerate(lines):
        lower = line.lower()
        if "head of department" not in lower and "professor and head" not in lower:
            continue

        nearby = lines[max(0, index - 2): min(len(lines), index + 5)]
        name = None
        designation = None
        email = None
        phone = None

        for item in nearby:
            if item.lower().startswith("email"):
                email = item
            elif item.lower().startswith("phone"):
                phone = item
            elif "professor and head" in item.lower() or "associate prof & hod" in item.lower():
                designation = item
            elif re.search(r"\b(dr|prof)\.?\b", item.lower()) and "head" not in item.lower():
                name = item

        details = [item for item in [name, designation or line, email, phone] if item]
        if details:
            return details

    return []


def extract_principal_info(context: str):
    lines = [re.sub(r"\s+", " ", line).strip() for line in re.split(r"[\n\r]+", context or "") if line.strip()]
    compact = " ".join(lines)

    name = None
    designation = "Principal"
    email = None
    phone = None

    explicit_principal = re.search(
        r"Principal[:\s-]*((?:Dr|Prof)\.?\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})",
        compact,
        re.IGNORECASE,
    )
    if explicit_principal:
        name = explicit_principal.group(1).strip(" ,:-")

    for index, line in enumerate(lines):
        lower = line.lower()
        if "principal" not in lower:
            continue

        nearby = lines[max(0, index - 2): min(len(lines), index + 8)]
        for item in nearby:
            if not name:
                name_match = re.search(r"\b(?:Dr|Prof)\.?\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3}", item)
                if name_match and "college" not in item.lower():
                    name = name_match.group(0).strip(" ,:-")

            if not email:
                email_match = re.search(r"[A-Za-z0-9._%+-]+@gndec\.ac\.in", item, re.IGNORECASE)
                if email_match:
                    email = email_match.group(0)

            if not phone:
                phone_match = re.search(r"(?:phone[:\s-]*)?([0-9][0-9(),\-\sA-Za-z]{8,})", item, re.IGNORECASE)
                if phone_match:
                    phone = phone_match.group(1).strip(" .,:;-")

        if name:
            break

    if not name:
        fallback_name = re.search(
            r"principal(?:\s*desk)?[^A-Za-z]+((?:Dr|Prof)\.?\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})",
            compact,
            re.IGNORECASE,
        )
        if fallback_name:
            name = fallback_name.group(1).strip(" ,:-")

    if not email:
        email_match = re.search(r"[A-Za-z0-9._%+-]+@gndec\.ac\.in", compact, re.IGNORECASE)
        if email_match:
            email = email_match.group(0)

    if not phone:
        phone_match = re.search(r"Phone[:\s-]*([0-9(),\-\sA-Za-z]{8,})", compact, re.IGNORECASE)
        if phone_match:
            phone = phone_match.group(1).strip(" .,:;-")

    details = [item for item in [
        name,
        designation if name else None,
        f"Email: {email}" if email else None,
        f"Phone: {phone}" if phone else None,
    ] if item]
    return details


def extract_hostel_entries(context: str):
    compact = re.sub(r"\s+", " ", context or "").strip()
    if not compact:
        return []

    segments = re.split(r"(?=Hostel\s*No\.?\s*\d+)", compact, flags=re.IGNORECASE)
    entries = []

    for segment in segments:
        hostel_match = re.search(r"Hostel\s*No\.?\s*(\d+)", segment, re.IGNORECASE)
        if not hostel_match:
            continue

        hostel_no = hostel_match.group(1)

        category = ""
        lower = segment.lower()
        if "girl" in lower:
            category = "Girls Hostel"
        elif "boy" in lower:
            category = "Boys Hostel"

        note_match = re.search(r"\(([^)]*(?:girl|boy)[^)]*)\)", segment, re.IGNORECASE)
        note = note_match.group(1).strip() if note_match else ""

        contact_matches = list(re.finditer(
            r"((?:Dr|Er|Mr|Mrs|Ms|Prof)\.?\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,4})\s+"
            r"(Warden|Caretaker)\s+(\d{3,5}[-\s]?\d{5,8}|\d{10})",
            segment,
            re.IGNORECASE,
        ))

        if contact_matches:
            for match in contact_matches:
                entries.append({
                    "hostel_no": hostel_no,
                    "name": match.group(1).strip(" ,:-"),
                    "role": match.group(2).strip(" ,:-").title(),
                    "phone": match.group(3).strip(" ,:-"),
                    "category": category,
                    "note": note,
                })
            continue

        name_match = re.search(
            r"((?:Dr|Er|Mr|Mrs|Ms|Prof)\.?\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,4})",
            segment,
            re.IGNORECASE,
        )
        phone_match = re.search(r"(\d{3,5}[-\s]?\d{5,8}|\d{10})", segment)

        entries.append({
            "hostel_no": hostel_no,
            "name": name_match.group(1).strip(" ,:-") if name_match else "",
            "role": "",
            "phone": phone_match.group(1).strip(" ,:-") if phone_match else "",
            "category": category,
            "note": note,
        })

    return entries


def pick_hostel_entries(query: str, entries):
    lower = (query or "").lower().replace("hsotel", "hostel")
    hostel_numbers = re.findall(r"\b([1-9])\b", lower)

    matched = []
    if hostel_numbers:
        wanted = set(hostel_numbers)
        matched = [item for item in entries if item.get("hostel_no") in wanted]
    elif "girls hostel" in lower or "girl hostel" in lower:
        matched = [item for item in entries if "girl" in (item.get("category", "") + " " + item.get("note", "")).lower()]
    elif "boys hostel" in lower or "boy hostel" in lower:
        matched = [item for item in entries if "boy" in (item.get("category", "") + " " + item.get("note", "")).lower()]

    if "warden" in lower:
        role_filtered = [item for item in (matched or entries) if item.get("role", "").lower() == "warden"]
        if role_filtered:
            matched = role_filtered

    if "caretaker" in lower:
        role_filtered = [item for item in (matched or entries) if item.get("role", "").lower() == "caretaker"]
        if role_filtered:
            matched = role_filtered

    return matched or entries[:4]


def split_contact_fields(items):
    name = None
    designation = None
    email = None
    phone = None

    for item in items:
        lower = item.lower()
        if lower.startswith("email"):
            email = item
        elif lower.startswith("phone"):
            phone = item
        elif "professor and head" in lower or "associate prof & hod" in lower or "associate professor and head" in lower:
            designation = item
        elif "head of department" in lower and not designation:
            designation = item
        else:
            name = item

    return name, designation, email, phone


def format_natural_list(items):
    items = [item for item in items if item]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def build_timetable_fallback(context: str, lang: str) -> str:
    matched = re.search(r"Matched exact timetable section\s+(.+?)\s+for\s+(.+?)\.", context or "", re.IGNORECASE)
    opened = re.search(r"Opened the most relevant official\s+(.+?)\s+timetable resource for\s+(.+?)\.", context or "", re.IGNORECASE)
    teacher_matched = re.search(r"Matched exact teacher timetable section\s+(.+?)\s+for\s+(.+?)\.", context or "", re.IGNORECASE)
    teacher_opened = re.search(r"Opened the official\s+(.+?)\s+teacher timetable resource for\s+(.+?)\.", context or "", re.IGNORECASE)

    if teacher_matched:
        section = teacher_matched.group(1).strip()
        teacher = teacher_matched.group(2).strip()
        if is_native_hindi(lang):
            return f"मैंने शिक्षक {teacher} के लिए आधिकारिक टाइमटेबल में सटीक सेक्शन {section} पहचान लिया है। नीचे दिया गया लिंक सीधे उसी शिक्षक के टाइमटेबल सेक्शन तक ले जाना चाहिए।"
        if is_native_punjabi(lang):
            return f"ਮੈਂ ਅਧਿਆਪਕ {teacher} ਲਈ ਅਧਿਕਾਰਿਕ ਟਾਈਮਟੇਬਲ ਵਿੱਚ ਸਹੀ ਭਾਗ {section} ਲੱਭ ਲਿਆ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਤੁਹਾਨੂੰ ਸਿੱਧਾ ਉਸੇ ਅਧਿਆਪਕ ਦੇ ਟਾਈਮਟੇਬਲ ਸੈਕਸ਼ਨ ਤੱਕ ਲੈ ਜਾਣਾ ਚਾਹੀਦਾ ਹੈ।"
        if is_hindi(lang):
            return f"Maine teacher {teacher} ke liye official timetable me exact section {section} identify kar diya hai. Neeche diya gaya link directly usi teacher timetable section tak le jana chahiye."
        if is_punjabi(lang):
            return f"Main teacher {teacher} layi official timetable vich exact section {section} identify kar lia hai. Thalle ditta link sidha usi teacher timetable section wal le jaana chahida hai."
        return f"I found the exact official timetable section {section} for teacher {teacher}. The link below should take you straight to that teacher's timetable."

    if teacher_opened:
        department = teacher_opened.group(1).strip()
        teacher = teacher_opened.group(2).strip()
        if is_native_hindi(lang):
            return f"मैंने शिक्षक {teacher} के लिए आधिकारिक {department} शिक्षक टाइमटेबल स्रोत चुन लिया है। नीचे दिया गया लिंक खोलकर आप उनका टाइमटेबल देख सकते हैं।"
        if is_native_punjabi(lang):
            return f"ਮੈਂ ਅਧਿਆਪਕ {teacher} ਲਈ ਅਧਿਕਾਰਿਕ {department} ਅਧਿਆਪਕ ਟਾਈਮਟੇਬਲ ਸਰੋਤ ਚੁਣ ਲਿਆ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਖੋਲ੍ਹ ਕੇ ਤੁਸੀਂ ਉਹਨਾਂ ਦਾ ਟਾਈਮਟੇਬਲ ਵੇਖ ਸਕਦੇ ਹੋ।"
        if is_hindi(lang):
            return f"Maine teacher {teacher} ke liye official {department} teacher timetable resource select kar diya hai. Neeche diya gaya link open karke aap unka timetable dekh sakte ho."
        if is_punjabi(lang):
            return f"Main teacher {teacher} layi official {department} teacher timetable resource choose kar lia hai. Thalle ditta link open karke tusi ohna da timetable dekh sakde ho."
        return f"I selected the official {department} teacher timetable resource for {teacher}. Open the link below to view that teacher's timetable."

    if matched:
        section = matched.group(1).strip()
        klass = matched.group(2).strip()
        if is_native_hindi(lang):
            return f"मैंने आपकी कक्षा {klass} के लिए आधिकारिक टाइमटेबल में सटीक सेक्शन {section} पहचान लिया है। नीचे दिया गया लिंक सीधे उसी टाइमटेबल सेक्शन तक ले जाना चाहिए, इसलिए आप वहाँ से शेड्यूल देख सकते हैं।"
        if is_native_punjabi(lang):
            return f"ਮੈਂ ਤੁਹਾਡੀ ਕਲਾਸ {klass} ਲਈ ਅਧਿਕਾਰਿਕ ਟਾਈਮਟੇਬਲ ਵਿੱਚ ਸਹੀ ਭਾਗ {section} ਲੱਭ ਲਿਆ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਤੁਹਾਨੂੰ ਸਿੱਧਾ ਉਸੇ ਟਾਈਮਟੇਬਲ ਸੈਕਸ਼ਨ ਤੱਕ ਲੈ ਜਾਣਾ ਚਾਹੀਦਾ ਹੈ, ਇਸ ਲਈ ਤੁਸੀਂ ਉੱਥੇ ਤੋਂ ਸ਼ਡਿਊਲ ਵੇਖ ਸਕਦੇ ਹੋ।"
        if is_hindi(lang):
            return f"Maine aapki class {klass} ke liye official timetable me exact section {section} identify kar diya hai. Neeche diya gaya link directly usi timetable section tak le jana chahiye, isliye aap usse open karke schedule check kar sakte ho."
        if is_punjabi(lang):
            return f"Main tuhadi class {klass} layi official timetable vich exact section {section} labh lia hai. Thalle ditta link sidha usi timetable section wal le jaana chahida hai, is karke tusi schedule turant check kar sakde ho."
        return f"I found the exact official timetable section {section} for your class {klass}. The link below should take you straight to that class timetable so you can check the schedule directly."

    if opened:
        dept = opened.group(1).strip()
        klass = opened.group(2).strip()
        if is_native_hindi(lang):
            return f"मैंने {klass} के लिए सबसे उपयुक्त आधिकारिक {dept} टाइमटेबल स्रोत चुन लिया है। नीचे दिया गया लिंक खोलकर आप नवीनतम कक्षा शेड्यूल सीधे देख सकते हैं।"
        if is_native_punjabi(lang):
            return f"ਮੈਂ {klass} ਲਈ ਸਭ ਤੋਂ ਉਚਿਤ ਅਧਿਕਾਰਿਕ {dept} ਟਾਈਮਟੇਬਲ ਸਰੋਤ ਚੁਣ ਲਿਆ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਖੋਲ੍ਹ ਕੇ ਤੁਸੀਂ ਨਵੀਂ ਕਲਾਸ ਸ਼ਡਿਊਲ ਸਿੱਧਾ ਵੇਖ ਸਕਦੇ ਹੋ।"
        if is_hindi(lang):
            return f"Maine {klass} ke liye sabse relevant official {dept} timetable resource select kar diya hai. Neeche diya gaya link open karke aap latest class schedule directly dekh sakte ho."
        if is_punjabi(lang):
            return f"Main {klass} layi sab ton relevant official {dept} timetable resource choose kar lia hai. Thalle ditta link open karke tusi latest class schedule sidha dekh sakde ho."
        return f"I picked the most relevant official {dept} timetable resource for {klass}. Open the link below and you should be able to view the latest class schedule directly."

    return ""


def infer_department_label(query: str) -> str:
    lower = (query or "").lower()
    if "cse" in lower or "computer science" in lower:
        return "CSE Department"
    if "ece" in lower or "electronics" in lower:
        return "ECE Department"
    if re.search(r"\bit\b", lower):
        return "IT Department"
    if re.search(r"\bee\b", lower) or "electrical" in lower:
        return "EE Department"
    if "civil" in lower:
        return "Civil Department"
    if "mechanical" in lower:
        return "Mechanical Department"
    return "Department"


def build_hod_markdown(details, lang: str, department_label: str = "Department") -> str:
    name, designation, email, phone = split_contact_fields(details)

    if is_native_hindi(lang):
        title = f"## {department_label} HoD"
        summary = f"{name or 'विभागाध्यक्ष'} GNDEC के आधिकारिक विभागीय पेज के अनुसार वर्तमान HoD जानकारी हैं।"
        contact_heading = "### विभागीय संपर्क विवरण"
        about_heading = "### संक्षिप्त सार"
        summary_body = "यह जानकारी आधिकारिक विभागीय स्रोत पर आधारित है। नवीनतम पुष्टि के लिए नीचे दिया गया विभागीय लिंक भी देख सकते हैं।"
    elif is_native_punjabi(lang):
        title = f"## {department_label} HoD"
        summary = f"{name or 'ਵਿਭਾਗ ਮੁਖੀ'} GNDEC ਦੇ ਅਧਿਕਾਰਿਕ ਵਿਭਾਗੀ ਪੰਨੇ ਮੁਤਾਬਕ ਮੌਜੂਦਾ HoD ਜਾਣਕਾਰੀ ਹਨ।"
        contact_heading = "### ਵਿਭਾਗੀ ਸੰਪਰਕ ਵੇਰਵਾ"
        about_heading = "### ਛੋਟਾ ਸਾਰ"
        summary_body = "ਇਹ ਜਾਣਕਾਰੀ ਅਧਿਕਾਰਿਕ ਵਿਭਾਗੀ ਸਰੋਤ 'ਤੇ ਆਧਾਰਿਤ ਹੈ। ਨਵੀਂ ਪੁਸ਼ਟੀ ਲਈ ਹੇਠਾਂ ਦਿੱਤਾ ਵਿਭਾਗੀ ਲਿੰਕ ਵੀ ਵੇਖ ਸਕਦੇ ਹੋ।"
    elif is_hindi(lang):
        title = f"## {department_label} HoD"
        summary = f"{name or 'Department HoD'} GNDEC ke official department page ke hisaab se current HoD information hai."
        contact_heading = "### Department Contact Details"
        about_heading = "### Quick Summary"
        summary_body = "Yeh information official department source se li gayi hai. Latest confirmation ke liye neeche diya gaya department link bhi check kar sakte ho."
    elif is_punjabi(lang):
        title = f"## {department_label} HoD"
        summary = f"{name or 'Department HoD'} GNDEC de official department page mutabik current HoD information hai."
        contact_heading = "### Department Contact Details"
        about_heading = "### Quick Summary"
        summary_body = "Eh information official department source ton lai gai hai. Latest confirmation layi thalle ditta department link vi check kar sakde ho."
    else:
        title = f"## {department_label} HoD"
        summary = f"{name or 'The department HoD'} appears as the current HoD on the official GNDEC department page."
        contact_heading = "### Department Contact Details"
        about_heading = "### Quick Summary"
        summary_body = "This information is based on the official department source. You can use the department link below for the latest confirmation."

    bullets = []
    if name:
        bullets.append(f"- **HoD Name:** {name}")
    if designation:
        bullets.append(f"- **Designation:** {designation}")
    if email:
        bullets.append(f"- **Email:** {email.replace('Email:', '').strip()}")
    if phone:
        bullets.append(f"- **Phone:** {phone.replace('Phone:', '').strip()}")

    return "\n\n".join([
        title,
        summary,
        contact_heading,
        "\n".join(bullets) if bullets else "- Official department information available in the link below.",
        about_heading,
        summary_body,
    ])


def build_principal_markdown(details, lang: str) -> str:
    name = None
    designation = None
    email = None
    phone = None

    for item in details:
        lower = item.lower()
        if lower.startswith("email"):
            email = item
        elif lower.startswith("phone"):
            phone = item
        elif "principal" in lower and not designation:
            designation = item
        elif not name:
            name = item

    if is_native_hindi(lang):
        title = "## Principal Details"
        summary = f"GNDEC के आधिकारिक प्रिंसिपल स्रोत के अनुसार वर्तमान प्रिंसिपल {name or 'आधिकारिक रूप से सूचीबद्ध प्रिंसिपल'} हैं।"
        contact_heading = "### संपर्क विवरण"
        note_heading = "### नोट"
        note = "नवीनतम पुष्टि के लिए नीचे दिया गया आधिकारिक प्रिंसिपल पेज खोल सकते हैं।"
    elif is_native_punjabi(lang):
        title = "## Principal Details"
        summary = f"GNDEC ਦੇ ਅਧਿਕਾਰਿਕ ਪ੍ਰਿੰਸੀਪਲ ਸਰੋਤ ਮੁਤਾਬਕ ਮੌਜੂਦਾ ਪ੍ਰਿੰਸੀਪਲ {name or 'ਅਧਿਕਾਰਿਕ ਤੌਰ ਤੇ ਦਰਜ ਪ੍ਰਿੰਸੀਪਲ'} ਹਨ।"
        contact_heading = "### ਸੰਪਰਕ ਵੇਰਵਾ"
        note_heading = "### ਨੋਟ"
        note = "ਨਵੀਂ ਪੁਸ਼ਟੀ ਲਈ ਹੇਠਾਂ ਦਿੱਤਾ ਅਧਿਕਾਰਿਕ ਪ੍ਰਿੰਸੀਪਲ ਪੰਨਾ ਖੋਲ੍ਹ ਸਕਦੇ ਹੋ।"
    elif is_hindi(lang):
        title = "## Principal Details"
        summary = f"GNDEC ke official principal resource ke hisaab se current principal {name or 'officially listed principal'} hain."
        contact_heading = "### Contact Details"
        note_heading = "### Note"
        note = "Latest confirmation ke liye neeche diya gaya official principal page open kar sakte ho."
    elif is_punjabi(lang):
        title = "## Principal Details"
        summary = f"GNDEC de official principal resource mutabik current principal {name or 'officially listed principal'} han."
        contact_heading = "### Contact Details"
        note_heading = "### Note"
        note = "Latest confirmation layi thalle ditta official principal page open kar sakde ho."
    else:
        title = "## Principal Details"
        summary = f"According to the official GNDEC principal resource, the current principal is {name or 'the officially listed principal'}."
        contact_heading = "### Contact Details"
        note_heading = "### Note"
        note = "You can open the official principal page below for the latest confirmation."

    bullets = []
    if name:
        bullets.append(f"- **Name:** {name}")
    if designation:
        bullets.append(f"- **Designation:** {designation}")
    if email:
        bullets.append(f"- **Email:** {email.replace('Email:', '').strip()}")
    if phone:
        bullets.append(f"- **Phone:** {phone.replace('Phone:', '').strip()}")

    return "\n\n".join([
        title,
        summary,
        contact_heading,
        "\n".join(bullets) if bullets else "- Official principal information is available in the link below.",
        note_heading,
        note,
    ])


def build_hostel_markdown(entries, lang: str) -> str:
    if is_native_hindi(lang):
        title = "## Hostel Contact Details"
        summary = "आधिकारिक GNDEC हॉस्टल हेल्प स्रोत के आधार पर संबंधित हॉस्टल संपर्क विवरण नीचे दिए गए हैं।"
        note_heading = "### नोट"
        note = "नवीनतम पुष्टि के लिए नीचे दिया गया आधिकारिक हॉस्टल स्रोत भी खोल सकते हैं।"
    elif is_native_punjabi(lang):
        title = "## Hostel Contact Details"
        summary = "ਅਧਿਕਾਰਿਕ GNDEC ਹੋਸਟਲ ਹੈਲਪ ਸਰੋਤ ਦੇ ਆਧਾਰ 'ਤੇ ਸੰਬੰਧਿਤ ਹੋਸਟਲ ਸੰਪਰਕ ਵੇਰਵੇ ਹੇਠਾਂ ਦਿੱਤੇ ਗਏ ਹਨ।"
        note_heading = "### ਨੋਟ"
        note = "ਨਵੀਂ ਪੁਸ਼ਟੀ ਲਈ ਹੇਠਾਂ ਦਿੱਤਾ ਅਧਿਕਾਰਿਕ ਹੋਸਟਲ ਸਰੋਤ ਵੀ ਖੋਲ੍ਹ ਸਕਦੇ ਹੋ।"
    elif is_hindi(lang):
        title = "## Hostel Contact Details"
        summary = "Official GNDEC hostel help resource ke basis par relevant hostel contact details neeche di gayi hain."
        note_heading = "### Note"
        note = "Latest confirmation ke liye neeche diya gaya official hostel resource bhi open kar sakte ho."
    elif is_punjabi(lang):
        title = "## Hostel Contact Details"
        summary = "Official GNDEC hostel help resource de basis te relevant hostel contact details thalle dittiyan gayian han."
        note_heading = "### Note"
        note = "Latest confirmation layi thalle ditta official hostel resource vi open kar sakde ho."
    else:
        title = "## Hostel Contact Details"
        summary = "Based on the official GNDEC hostel help resource, the relevant hostel contact details are listed below."
        note_heading = "### Note"
        note = "You can also open the official hostel resource below for the latest confirmation."

    bullets = []
    for item in entries:
        parts = [f"Hostel No. {item.get('hostel_no', '').strip()}"]
        if item.get("category"):
            parts.append(item["category"])
        if item.get("role"):
            parts.append(item["role"])
        label = " - ".join([part for part in parts if part])

        details = []
        if item.get("name"):
            details.append(item["name"])
        if item.get("phone"):
            details.append(item["phone"])
        if item.get("note"):
            details.append(item["note"])

        bullets.append(f"- **{label}:** {' | '.join(details)}".rstrip(" :|"))

    return "\n\n".join([
        title,
        summary,
        "\n".join(bullets) if bullets else "- Official hostel details are available in the link below.",
        note_heading,
        note,
    ])


def build_girls_hostel_overview(lang: str) -> str:
    if is_native_hindi(lang):
        return "\n\n".join([
            "## Girls Hostel Overview",
            "GNDEC का गर्ल्स हॉस्टल आधिकारिक रूप से **Hostel No. 4** है, जो लगभग **300 बाहरी छात्राओं** को ऑन-कैंपस आवास प्रदान करता है।",
            "### सुविधाएँ और सुविधाजनक व्यवस्थाएँ",
            "- **कमरे:** आमतौर पर 3-सीटर या 4-सीटर कमरे होते हैं, और अंतिम वर्ष की छात्राओं को कभी-कभी सीमित सिंगल रूम विकल्प मिल सकता है।",
            "- **मूल सुविधाएँ:** बेड, टेबल, कुर्सी, अलमारी, पंखे, गीजर, वॉशिंग मशीन और वॉटर प्यूरीफायर उपलब्ध होते हैं।",
            "- **कनेक्टिविटी:** हॉस्टल वाई-फाई सक्षम है और छात्राओं के लिए केंद्रीकृत कंप्यूटर सुविधा का भी उल्लेख मिलता है।",
            "- **मनोरंजन:** कॉमन रूम, टीवी, समाचारपत्र, पत्रिकाएँ, शतरंज, बैडमिंटन और टेबल टेनिस जैसी सुविधाएँ उपलब्ध हैं।",
            "- **सुरक्षा और सहायता:** CCTV, 24x7 सुरक्षा, कैंपस डिस्पेंसरी, रेजिडेंट डॉक्टर और एम्बुलेंस सुविधा उपलब्ध है।",
            "### फीस और मेस",
            "- **अनुमानित हॉस्टल फीस:** 2026 सत्र के लिए लगभग **Rs. 31,313 प्रति सेमेस्टर**।",
            "- **मेस सुविधा:** संलग्न शाकाहारी मेस और विशाल डाइनिंग हॉल उपलब्ध है।",
            "- **मासिक मेस बिल:** आमतौर पर **Rs. 2,700 से Rs. 3,000** के बीच।",
            "### प्रमुख संपर्क",
            "- **वार्डन:** Dr. Chahat Jain",
            "### नियम और आवंटन",
            "- **आवंटन:** कमरों का आवंटन सामान्यतः पहले आओ, पहले पाओ के आधार पर होता है।",
            "- **अनुशासन:** रैगिंग, धूम्रपान, शराब और नशे पर सख्त प्रतिबंध है।",
            "### नोट",
            "नवीनतम आवंटन स्थिति, कमरे की उपलब्धता और आधिकारिक संपर्क पुष्टि के लिए नीचे दिया गया आधिकारिक हॉस्टल स्रोत देखिए।",
        ])
    if is_native_punjabi(lang):
        return "\n\n".join([
            "## Girls Hostel Overview",
            "GNDEC ਦਾ ਗਰਲਜ਼ ਹੋਸਟਲ ਅਧਿਕਾਰਿਕ ਤੌਰ 'ਤੇ **Hostel No. 4** ਹੈ, ਜੋ ਲਗਭਗ **300 ਬਾਹਰੀ ਵਿਦਿਆਰਥਣਾਂ** ਨੂੰ ਕੈਂਪਸ ਅੰਦਰ ਰਹਿਣ ਦੀ ਸਹੂਲਤ ਦਿੰਦਾ ਹੈ।",
            "### ਸਹੂਲਤਾਂ",
            "- **ਕਮਰੇ:** ਆਮ ਤੌਰ 'ਤੇ 3-ਸੀਟਰ ਜਾਂ 4-ਸੀਟਰ ਕਮਰੇ ਹੁੰਦੇ ਹਨ, ਅਤੇ ਆਖਰੀ ਸਾਲ ਦੀਆਂ ਵਿਦਿਆਰਥਣਾਂ ਨੂੰ ਕਦੇ-ਕਦੇ ਸੀਮਿਤ ਸਿੰਗਲ ਰੂਮ ਵਿਕਲਪ ਮਿਲ ਸਕਦਾ ਹੈ।",
            "- **ਮੂਲ ਸਹੂਲਤਾਂ:** ਬੈੱਡ, ਟੇਬਲ, ਕੁਰਸੀ, ਅਲਮਾਰੀ, ਪੱਖੇ, ਗੀਜ਼ਰ, ਵਾਸ਼ਿੰਗ ਮਸ਼ੀਨਾਂ ਅਤੇ ਵਾਟਰ ਪਿਊਰੀਫਾਇਰ ਉਪਲਬਧ ਹਨ।",
            "- **ਕਨੈਕਟਿਵਟੀ:** ਹੋਸਟਲ ਵਾਈ-ਫਾਈ ਯੋਗ ਹੈ ਅਤੇ ਵਿਦਿਆਰਥਣਾਂ ਲਈ ਕੇਂਦਰੀ ਕੰਪਿਊਟਰ ਸਹੂਲਤ ਦਾ ਵੀ ਜ਼ਿਕਰ ਮਿਲਦਾ ਹੈ।",
            "- **ਮਨੋਰੰਜਨ:** ਕਾਮਨ ਰੂਮ, ਟੀਵੀ, ਅਖ਼ਬਾਰ, ਮੈਗਜ਼ੀਨ, ਸ਼ਤਰੰਜ, ਬੈਡਮਿੰਟਨ ਅਤੇ ਟੇਬਲ ਟੈਨਿਸ ਵਰਗੀਆਂ ਸਹੂਲਤਾਂ ਹਨ।",
            "- **ਸੁਰੱਖਿਆ ਅਤੇ ਸਿਹਤ:** CCTV, 24x7 ਸੁਰੱਖਿਆ, ਕੈਂਪਸ ਡਿਸਪੈਂਸਰੀ, ਰਿਹਾਇਸ਼ੀ ਡਾਕਟਰ ਅਤੇ ਐਂਬੂਲੈਂਸ ਸਹੂਲਤ ਉਪਲਬਧ ਹੈ।",
            "### ਫੀਸ ਅਤੇ ਮੇਸ",
            "- **ਅਨੁਮਾਨਿਤ ਹੋਸਟਲ ਫੀਸ:** 2026 ਸੈਸ਼ਨ ਲਈ ਲਗਭਗ **Rs. 31,313 ਪ੍ਰਤੀ ਸਮੈਸਟਰ**।",
            "- **ਮੈਸ ਸਹੂਲਤ:** ਨਾਲ ਜੁੜੀ ਸ਼ਾਕਾਹਾਰੀ ਮੈਸ ਅਤੇ ਵਿਸ਼ਾਲ ਡਾਇਨਿੰਗ ਹਾਲ ਉਪਲਬਧ ਹੈ।",
            "- **ਮਾਸਿਕ ਮੈਸ ਬਿੱਲ:** ਆਮ ਤੌਰ 'ਤੇ **Rs. 2,700 ਤੋਂ Rs. 3,000** ਦੇ ਵਿਚਕਾਰ।",
            "### ਮੁੱਖ ਸੰਪਰਕ",
            "- **ਵਾਰਡਨ:** Dr. Chahat Jain",
            "### ਨਿਯਮ ਅਤੇ ਅਲਾਟਮੈਂਟ",
            "- **ਅਲਾਟਮੈਂਟ:** ਕਮਰਿਆਂ ਦੀ ਅਲਾਟਮੈਂਟ ਆਮ ਤੌਰ 'ਤੇ ਪਹਿਲਾਂ ਆਓ, ਪਹਿਲਾਂ ਪਾਓ ਦੇ ਅਧਾਰ 'ਤੇ ਹੁੰਦੀ ਹੈ।",
            "- **ਅਨੁਸ਼ਾਸਨ:** ਰੈਗਿੰਗ, ਧੂਮਰਪਾਨ, ਸ਼ਰਾਬ ਅਤੇ ਨਸ਼ਾ ਸਖ਼ਤ ਮਨਾਹੀ ਹੈ।",
            "### ਨੋਟ",
            "ਨਵੀਂ ਅਲਾਟਮੈਂਟ ਸਥਿਤੀ, ਕਮਰੇ ਦੀ ਉਪਲਬਧਤਾ ਅਤੇ ਅਧਿਕਾਰਿਕ ਸੰਪਰਕ ਪੁਸ਼ਟੀ ਲਈ ਹੇਠਾਂ ਦਿੱਤਾ ਅਧਿਕਾਰਿਕ ਹੋਸਟਲ ਸਰੋਤ ਵੇਖੋ।",
        ])
    if is_hindi(lang):
        return "\n\n".join([
            "## Girls Hostel Overview",
            "GNDEC ka girls hostel officially **Hostel No. 4** hai, jo roughly **300 outstation female students** ke liye on-campus accommodation provide karta hai.",
            "### Facilities and Amenities",
            "- **Room options:** rooms usually 3-seater ya 4-seater hoti hain, aur final year students ko kabhi-kabhi limited single-room option mil sakta hai.",
            "- **Basic utilities:** bed, table, chair, wardrobe, fans, geysers, washing machines, aur water purifiers available hote hain.",
            "- **Connectivity:** hostel Wi-Fi enabled hai aur girls students ke liye centralized computer facility bhi mention ki jaati hai.",
            "- **Recreation:** common room, TV, newspapers, magazines, chess, badminton, aur table tennis jaisi facilities available hoti hain.",
            "- **Safety and support:** CCTV, 24x7 security, campus dispensary, resident doctor, aur ambulance support available hai.",
            "### Fees and Mess",
            "- **Estimated hostel fee:** 2026 session ke liye around **Rs. 31,313 per semester**.",
            "- **Mess facility:** attached vegetarian mess aur spacious dining hall available hota hai.",
            "- **Monthly mess bill:** usually around **Rs. 2,700 to Rs. 3,000**.",
            "### Key Contacts",
            "- **Warden:** Dr. Chahat Jain",
            "### Rules and Allotment",
            "- **Allotment:** room allotment generally first-come, first-served basis par hota hai.",
            "- **Discipline:** ragging, smoking, drinking, aur drug use strictly prohibited hote hain.",
            "### Note",
            "Latest allotment status, current room availability, aur official contact confirmation ke liye neeche diya gaya official hostel resource open karna best rahega.",
        ])
    if is_punjabi(lang):
        return "\n\n".join([
            "## Girls Hostel Overview",
            "GNDEC da girls hostel officially **Hostel No. 4** hai, jo lagbhag **300 outstation female students** layi on-campus accommodation dinda hai.",
            "### Facilities and Amenities",
            "- **Room options:** rooms aam taur te 3-seater jaan 4-seater hundiyan ne, te final year students nu kade-kade limited single-room option vi mil sakda hai.",
            "- **Basic utilities:** bed, table, chair, wardrobe, fans, geysers, washing machines, te water purifiers available hunde ne.",
            "- **Connectivity:** hostel Wi-Fi enabled hai te girls students layi centralized computer facility da vi zikr milda hai.",
            "- **Recreation:** common room, TV, newspapers, magazines, chess, badminton, te table tennis vargian facilities available ne.",
            "- **Safety and support:** CCTV, 24x7 security, campus dispensary, resident doctor, te ambulance support available hai.",
            "### Fees and Mess",
            "- **Estimated hostel fee:** 2026 session layi lagbhag **Rs. 31,313 per semester**.",
            "- **Mess facility:** attached vegetarian mess te spacious dining hall available hunda hai.",
            "- **Monthly mess bill:** aam taur te **Rs. 2,700 to Rs. 3,000** de vich hunda hai.",
            "### Key Contacts",
            "- **Warden:** Dr. Chahat Jain",
            "### Rules and Allotment",
            "- **Allotment:** room allotment generally first-come, first-served basis te hunda hai.",
            "- **Discipline:** ragging, smoking, drinking, te drug use sakht mana hai.",
            "### Note",
            "Latest allotment status, current room availability, te official contact confirmation layi thalle ditta official hostel resource open karna sab ton vadhiya rahega.",
        ])
    return "\n\n".join([
        "## Girls Hostel Overview",
        "The GNDEC girls hostel is officially **Hostel No. 4**, and it provides on-campus accommodation for roughly **300 outstation female students**.",
        "### Facilities and Amenities",
        "- **Room options:** rooms are generally 3-seater or 4-seater, with limited single-room options sometimes available for final-year students.",
        "- **Basic utilities:** beds, tables, chairs, wardrobes, fans, geysers, washing machines, and water purifiers are typically available.",
        "- **Connectivity:** the hostel is Wi-Fi enabled and is also described as having a centralized computer facility for girls.",
        "- **Recreation:** a common room, TV, newspapers, magazines, chess, badminton, and table tennis are part of the usual hostel setup.",
        "- **Safety and support:** CCTV, 24x7 security, a campus dispensary, resident doctor support, and ambulance access are available.",
        "### Fees and Mess",
        "- **Estimated hostel fee:** around **Rs. 31,313 per semester** for the 2026 session.",
        "- **Mess facility:** an attached vegetarian mess and spacious dining hall are available.",
        "- **Monthly mess bill:** usually around **Rs. 2,700 to Rs. 3,000**.",
        "### Key Contacts",
        "- **Warden:** Dr. Chahat Jain",
        "### Rules and Allotment",
        "- **Allotment:** room allotment is generally handled on a first-come, first-served basis.",
        "- **Discipline:** ragging, smoking, drinking, and drug use are strictly prohibited.",
        "### Note",
        "For the latest allotment status, current room availability, and official contact confirmation, the official hostel resource below is the best place to check.",
    ])


def build_boys_hostel_overview(lang: str) -> str:
    if is_native_hindi(lang):
        return "\n\n".join([
            "## Boys Hostel Overview",
            "GNDEC में लड़कों के लिए मुख्य रूप से **Hostel No. 1, Hostel No. 2 और Hostel No. 5** उपयोग किए जाते हैं, और कुल क्षमता लगभग **1,200 छात्रों** के आसपास बताई जाती है।",
            "### आवंटन झलक",
            "- **Hostel No. 5:** सामान्यतः B.Tech प्रथम वर्ष के छात्रों से जोड़ा जाता है और इसे अपेक्षाकृत नई सुविधा माना जाता है।",
            "- **अन्य बॉयज़ हॉस्टल:** सत्र योजना के अनुसार 2nd year, LEET, senior-year और कुछ PG या M.Tech छात्रों को अलग-अलग हॉस्टलों में आवंटित किया जा सकता है।",
            "### सुविधाएँ",
            "- **कमरे:** जूनियर छात्रों के लिए 3-सीटर या 4-सीटर कमरे सामान्य हैं; वरिष्ठ वर्षों में सिंगल क्यूबिकल शैली के कमरे मिल सकते हैं।",
            "- **यूटिलिटीज़:** गीजर, वॉशिंग मशीन, वॉटर प्यूरीफायर और पावर बैकअप उपलब्ध होते हैं।",
            "- **कनेक्टिविटी:** कमरों और कॉमन एरिया में हाई-स्पीड वाई-फाई उपलब्ध है।",
            "- **मनोरंजन और खेल:** कॉमन रूम, टीवी, अख़बार, इनडोर गेम्स और वॉलीबॉल/बैडमिंटन जैसी सुविधाएँ उपलब्ध हैं।",
            "### फीस और प्रशासन",
            "- **अनुमानित सेमेस्टर फीस:** पुराने हॉस्टलों के लिए लगभग **Rs. 31,313**, और Hostel No. 5 के लिए लगभग **Rs. 33,677**।",
            "- **मेस सिक्योरिटी:** प्रथम प्रवेश पर लगभग **Rs. 7,000 से Rs. 12,700** जमा करना पड़ सकता है।",
            "- **मासिक मेस बिल:** आमतौर पर **Rs. 2,700 से Rs. 3,000**।",
            "### प्रमुख संपर्क",
            "- **Chief Warden:** Dr. Puneet Pal Singh Cheema - 97818-16320",
            "- **Hostel No. 1 Caretaker:** Mr. Kewal Singh - 99146-29080",
            "- **Hostel No. 2 Caretaker:** Mr. Jagmail Singh - 84375-20013",
            "- **Hostel No. 5 Caretaker:** Mr. Gurdev Singh - 99143-61995",
            "### नोट",
            "नवीनतम हॉस्टल आवंटन और वर्तमान वार्डन/केयरटेकर पुष्टि के लिए नीचे दिया गया आधिकारिक हॉस्टल स्रोत देखिए।",
        ])
    if is_native_punjabi(lang):
        return "\n\n".join([
            "## Boys Hostel Overview",
            "GNDEC ਵਿੱਚ ਮੁੰਡਿਆਂ ਲਈ ਮੁੱਖ ਤੌਰ 'ਤੇ **Hostel No. 1, Hostel No. 2 ਅਤੇ Hostel No. 5** ਵਰਤੇ ਜਾਂਦੇ ਹਨ, ਅਤੇ ਕੁੱਲ ਸਮਰੱਥਾ ਲਗਭਗ **1,200 ਵਿਦਿਆਰਥੀਆਂ** ਦੇ ਆਸਪਾਸ ਦੱਸੀ ਜਾਂਦੀ ਹੈ।",
            "### ਅਲਾਟਮੈਂਟ ਝਲਕ",
            "- **Hostel No. 5:** ਇਸਨੂੰ ਆਮ ਤੌਰ 'ਤੇ B.Tech ਪਹਿਲੇ ਸਾਲ ਦੇ ਵਿਦਿਆਰਥੀਆਂ ਨਾਲ ਜੋੜਿਆ ਜਾਂਦਾ ਹੈ ਅਤੇ ਇਹ ਨਵੀਂ ਸਹੂਲਤ ਮੰਨੀ ਜਾਂਦੀ ਹੈ।",
            "- **ਹੋਰ ਬੋਇਜ਼ ਹੋਸਟਲ:** ਸੈਸ਼ਨ ਯੋਜਨਾ ਅਨੁਸਾਰ 2nd year, LEET, senior-year ਅਤੇ ਕੁਝ PG ਜਾਂ M.Tech ਵਿਦਿਆਰਥੀਆਂ ਨੂੰ ਵੱਖ-ਵੱਖ ਹੋਸਟਲਾਂ ਵਿੱਚ ਅਲਾਟ ਕੀਤਾ ਜਾ ਸਕਦਾ ਹੈ।",
            "### ਸਹੂਲਤਾਂ",
            "- **ਕਮਰੇ:** ਜੂਨੀਅਰ ਵਿਦਿਆਰਥੀਆਂ ਲਈ 3-ਸੀਟਰ ਜਾਂ 4-ਸੀਟਰ ਕਮਰੇ ਆਮ ਹਨ; ਸੀਨੀਅਰ ਸਾਲਾਂ ਵਿੱਚ ਸਿੰਗਲ ਕਿਊਬਿਕਲ ਰੂਮ ਮਿਲ ਸਕਦੇ ਹਨ।",
            "- **ਯੂਟਿਲਿਟੀਜ਼:** ਗੀਜ਼ਰ, ਵਾਸ਼ਿੰਗ ਮਸ਼ੀਨ, ਵਾਟਰ ਪਿਊਰੀਫਾਇਰ ਅਤੇ ਪਾਵਰ ਬੈਕਅਪ ਉਪਲਬਧ ਹਨ।",
            "- **ਕਨੈਕਟਿਵਟੀ:** ਕਮਰਿਆਂ ਅਤੇ ਸਾਂਝੇ ਖੇਤਰਾਂ ਵਿੱਚ ਹਾਈ-ਸਪੀਡ ਵਾਈ-ਫਾਈ ਉਪਲਬਧ ਹੈ।",
            "- **ਮਨੋਰੰਜਨ ਅਤੇ ਖੇਡਾਂ:** ਕਾਮਨ ਰੂਮ, ਟੀਵੀ, ਅਖ਼ਬਾਰ, ਇਨਡੋਰ ਖੇਡਾਂ ਅਤੇ ਵੌਲੀਬਾਲ/ਬੈਡਮਿੰਟਨ ਵਰਗੀਆਂ ਸਹੂਲਤਾਂ ਮੌਜੂਦ ਹਨ।",
            "### ਫੀਸ ਅਤੇ ਪ੍ਰਸ਼ਾਸਨ",
            "- **ਅਨੁਮਾਨਿਤ ਸਮੈਸਟਰ ਫੀਸ:** ਪੁਰਾਣੇ ਹੋਸਟਲਾਂ ਲਈ ਲਗਭਗ **Rs. 31,313**, ਅਤੇ Hostel No. 5 ਲਈ ਲਗਭਗ **Rs. 33,677**।",
            "- **ਮੈਸ ਸਿਕਿਉਰਟੀ:** ਪਹਿਲੀ ਐਡਮਿਸ਼ਨ 'ਤੇ ਲਗਭਗ **Rs. 7,000 ਤੋਂ Rs. 12,700** ਜਮ੍ਹਾਂ ਕਰਵਾਉਣੀ ਪੈ ਸਕਦੀ ਹੈ।",
            "- **ਮਾਸਿਕ ਮੈਸ ਬਿੱਲ:** ਆਮ ਤੌਰ 'ਤੇ **Rs. 2,700 ਤੋਂ Rs. 3,000**।",
            "### ਮੁੱਖ ਸੰਪਰਕ",
            "- **Chief Warden:** Dr. Puneet Pal Singh Cheema - 97818-16320",
            "- **Hostel No. 1 Caretaker:** Mr. Kewal Singh - 99146-29080",
            "- **Hostel No. 2 Caretaker:** Mr. Jagmail Singh - 84375-20013",
            "- **Hostel No. 5 Caretaker:** Mr. Gurdev Singh - 99143-61995",
            "### ਨੋਟ",
            "ਨਵੀਂ ਹੋਸਟਲ ਅਲਾਟਮੈਂਟ ਅਤੇ ਮੌਜੂਦਾ ਵਾਰਡਨ/ਕੇਅਰਟੇਕਰ ਪੁਸ਼ਟੀ ਲਈ ਹੇਠਾਂ ਦਿੱਤਾ ਅਧਿਕਾਰਿਕ ਹੋਸਟਲ ਸਰੋਤ ਵੇਖੋ।",
        ])
    if is_hindi(lang):
        return "\n\n".join([
            "## Boys Hostel Overview",
            "GNDEC mein boys students ke liye mainly **Hostel No. 1, Hostel No. 2, aur Hostel No. 5** use kiye jaate hain, aur total capacity roughly **1,200 students** ke around batayi jaati hai.",
            "### Allotment Snapshot",
            "- **Hostel No. 5:** commonly B.Tech 1st year students se associated mana jata hai aur newer facility ke roop mein dekha jata hai.",
            "- **Other boys hostels:** session planning ke hisaab se 2nd year, LEET, senior-year, aur kuch PG or M.Tech students ko bhi different boys hostels allot kiye ja sakte hain.",
            "### Facilities and Amenities",
            "- **Rooms:** junior students ke liye 3-seater ya 4-seater rooms common hote hain; senior years mein single cubical style rooms mil sakte hain.",
            "- **Utilities:** geysers, washing machines, water purifiers, aur power backup facilities available hoti hain.",
            "- **Connectivity:** all rooms and common areas mein high-speed Wi-Fi support hota hai.",
            "- **Recreation and sports:** common rooms, TV, newspapers, indoor games, aur volleyball/badminton courts ka access hota hai. Students main sports complex bhi use kar sakte hain.",
            "### Fees and Administration",
            "- **Estimated semester fee:** older boys hostels ke liye around **Rs. 31,313**, aur Hostel No. 5 ke liye around **Rs. 33,677**.",
            "- **Mess security:** first admission ke time roughly **Rs. 7,000 to Rs. 12,700** deposit lag sakta hai.",
            "- **Monthly mess bill:** usually around **Rs. 2,700 to Rs. 3,000**.",
            "### Key Contacts",
            "- **Chief Warden:** Dr. Puneet Pal Singh Cheema - 97818-16320",
            "- **Hostel No. 1 Caretaker:** Mr. Kewal Singh - 99146-29080",
            "- **Hostel No. 2 Caretaker:** Mr. Jagmail Singh - 84375-20013",
            "- **Hostel No. 5 Caretaker:** Mr. Gurdev Singh - 99143-61995",
            "### Note",
            "Latest hostel-wise allotment aur current warden or caretaker confirmation ke liye neeche diya gaya official hostel resource open kar lo.",
        ])
    if is_punjabi(lang):
        return "\n\n".join([
            "## Boys Hostel Overview",
            "GNDEC vich boys students layi mainly **Hostel No. 1, Hostel No. 2, te Hostel No. 5** use hunde ne, te total capacity lagbhag **1,200 students** de around dassi jandi hai.",
            "### Allotment Snapshot",
            "- **Hostel No. 5:** aam taur te B.Tech 1st year students naal jod ke dekheya janda hai te newer facility manni jandi hai.",
            "- **Other boys hostels:** session planning mutabik 2nd year, LEET, senior-year, te kujh PG jaan M.Tech students nu vakh-vakh boys hostels allot ho sakde ne.",
            "### Facilities and Amenities",
            "- **Rooms:** junior students layi 3-seater jaan 4-seater rooms common hunde ne; senior years layi single cubical style rooms vi mil sakde ne.",
            "- **Utilities:** geysers, washing machines, water purifiers, te power backup facilities available hundiyan ne.",
            "- **Connectivity:** rooms te common areas vich high-speed Wi-Fi support milda hai.",
            "- **Recreation and sports:** common rooms, TV, newspapers, indoor games, te volleyball/badminton courts da access hunda hai. Students main sports complex vi use kar sakde ne.",
            "### Fees and Administration",
            "- **Estimated semester fee:** older boys hostels layi lagbhag **Rs. 31,313**, te Hostel No. 5 layi lagbhag **Rs. 33,677**.",
            "- **Mess security:** first admission time roughly **Rs. 7,000 to Rs. 12,700** deposit lag sakda hai.",
            "- **Monthly mess bill:** aam taur te **Rs. 2,700 to Rs. 3,000** de vich hunda hai.",
            "### Key Contacts",
            "- **Chief Warden:** Dr. Puneet Pal Singh Cheema - 97818-16320",
            "- **Hostel No. 1 Caretaker:** Mr. Kewal Singh - 99146-29080",
            "- **Hostel No. 2 Caretaker:** Mr. Jagmail Singh - 84375-20013",
            "- **Hostel No. 5 Caretaker:** Mr. Gurdev Singh - 99143-61995",
            "### Note",
            "Latest hostel-wise allotment te current warden jaan caretaker confirmation layi thalle ditta official hostel resource open kar lo.",
        ])
    return "\n\n".join([
        "## Boys Hostel Overview",
        "At GNDEC, boys students are mainly accommodated in **Hostel No. 1, Hostel No. 2, and Hostel No. 5**, with a combined capacity of roughly **1,200 students**.",
        "### Allotment Snapshot",
        "- **Hostel No. 5:** is commonly associated with B.Tech 1st-year students and is usually described as a newer facility.",
        "- **Other boys hostels:** depending on the session plan, 2nd-year, LEET, senior-year, and some PG or M.Tech students may be allotted across the other boys hostels.",
        "### Facilities and Amenities",
        "- **Rooms:** 3-seater and 4-seater rooms are common for junior students, while single cubical-style rooms may be available in senior years.",
        "- **Utilities:** geysers, washing machines, water purifiers, and power backup are part of the standard setup.",
        "- **Connectivity:** high-speed Wi-Fi is available across rooms and common areas.",
        "- **Recreation and sports:** common rooms, TV, newspapers, indoor games, and access to volleyball, badminton, and the main sports complex are part of the hostel environment.",
        "### Fees and Administration",
        "- **Estimated semester fee:** around **Rs. 31,313** for older boys hostels and around **Rs. 33,677** for Hostel No. 5.",
        "- **Mess security:** roughly **Rs. 7,000 to Rs. 12,700** may be required at first admission.",
        "- **Monthly mess bill:** usually around **Rs. 2,700 to Rs. 3,000**.",
        "### Key Contacts",
        "- **Chief Warden:** Dr. Puneet Pal Singh Cheema - 97818-16320",
        "- **Hostel No. 1 Caretaker:** Mr. Kewal Singh - 99146-29080",
        "- **Hostel No. 2 Caretaker:** Mr. Jagmail Singh - 84375-20013",
        "- **Hostel No. 5 Caretaker:** Mr. Gurdev Singh - 99143-61995",
        "### Note",
        "For the latest hostel-wise allotment and current warden or caretaker confirmation, the official hostel resource below is the best place to check.",
    ])


def build_mess_overview(lang: str) -> str:
    if is_native_hindi(lang):
        return "\n\n".join([
            "## Mess Details",
            "GNDEC के हॉस्टलों में सामान्यतः **शाकाहारी मेस सुविधाएँ** उपलब्ध होती हैं, और गर्ल्स हॉस्टल तथा बॉयज़ हॉस्टलों दोनों के साथ डाइनिंग व्यवस्था जुड़ी होती है।",
            "### भोजन और डाइनिंग",
            "- **भोजन:** सामान्यतः नाश्ता, दोपहर का भोजन, शाम के नाश्ते और रात्रि भोजन की व्यवस्था होती है।",
            "- **मेन्यू शैली:** साप्ताहिक घूमने वाला मेन्यू होता है जिसमें पनीर, राजमा, दाल और मौसमी सब्जियाँ जैसी चीज़ें शामिल रहती हैं।",
            "- **डाइनिंग स्पेस:** डाइनिंग हॉल सामान्यतः विशाल और एयर-कूल्ड होते हैं।",
            "- **क्वालिटी चेक:** भोजन की गुणवत्ता और स्वच्छता की जाँच का भी उल्लेख मिलता है।",
            "### शुल्क और बिलिंग",
            "- **मासिक मेस शुल्क:** सामान्यतः **Rs. 2,700 से Rs. 3,000** प्रति माह।",
            "- **प्रारंभिक सिक्योरिटी डिपॉज़िट:** नए छात्रों को कमरे के आवंटन से पहले लगभग **Rs. 12,700** तक जमा करना पड़ सकता है।",
            "- **बिलिंग नियम:** मासिक बकाया समय पर जमा करना होता है, अन्यथा जुर्माना या मेस अकाउंट से जुड़ी समस्या हो सकती है।",
            "### प्रबंधन",
            "- **मेस काउंसिल:** छात्र प्रतिनिधियों के साथ एक मेस काउंसिल मेन्यू और समस्याओं पर चर्चा करती है।",
            "- **अनिवार्य उपयोग:** हॉस्टल निवासियों के लिए मेस अकाउंट सामान्यतः अनिवार्य होता है।",
            "### नोट",
            "नवीनतम मेस शुल्क, सिक्योरिटी डिपॉज़िट और हॉस्टल-वार नियमों के लिए नीचे दिया गया आधिकारिक स्रोत देखिए।",
        ])
    if is_native_punjabi(lang):
        return "\n\n".join([
            "## Mess Details",
            "GNDEC ਦੇ ਹੋਸਟਲਾਂ ਵਿੱਚ ਆਮ ਤੌਰ 'ਤੇ **ਸ਼ਾਕਾਹਾਰੀ ਮੈਸ ਸਹੂਲਤਾਂ** ਹੁੰਦੀਆਂ ਹਨ, ਅਤੇ ਗਰਲਜ਼ ਹੋਸਟਲ ਤੇ ਬੋਇਜ਼ ਹੋਸਟਲਾਂ ਦੋਹਾਂ ਨਾਲ ਡਾਇਨਿੰਗ ਪ੍ਰਬੰਧ ਜੁੜੇ ਹੁੰਦੇ ਹਨ।",
            "### ਭੋਜਨ ਅਤੇ ਡਾਇਨਿੰਗ",
            "- **ਭੋਜਨ:** ਆਮ ਤੌਰ 'ਤੇ ਨਾਸ਼ਤਾ, ਦੁਪਹਿਰ ਦਾ ਖਾਣਾ, ਸ਼ਾਮ ਦਾ ਨਾਸ਼ਤਾ ਅਤੇ ਰਾਤ ਦਾ ਖਾਣਾ ਮਿਲਦਾ ਹੈ।",
            "- **ਮੇਨੂ ਸ਼ੈਲੀ:** ਹਫ਼ਤਾਵਾਰੀ ਰੋਟੇਟਿੰਗ ਮੇਨੂ ਹੁੰਦਾ ਹੈ ਜਿਸ ਵਿੱਚ ਪਨੀਰ, ਰਾਜਮਾ, ਦਾਲ ਅਤੇ ਮੌਸਮੀ ਸਬਜ਼ੀਆਂ ਵਰਗੀਆਂ ਚੀਜ਼ਾਂ ਸ਼ਾਮਲ ਹੁੰਦੀਆਂ ਹਨ।",
            "- **ਡਾਇਨਿੰਗ ਸਪੇਸ:** ਡਾਇਨਿੰਗ ਹਾਲ ਆਮ ਤੌਰ 'ਤੇ ਵਿਸ਼ਾਲ ਅਤੇ ਏਅਰ-ਕੂਲਡ ਹੁੰਦੇ ਹਨ।",
            "- **ਕੁਆਲਿਟੀ ਚੈਕ:** ਭੋਜਨ ਦੀ ਗੁਣਵੱਤਾ ਅਤੇ ਸਫ਼ਾਈ ਦੀ ਜਾਂਚ ਦਾ ਵੀ ਜ਼ਿਕਰ ਮਿਲਦਾ ਹੈ।",
            "### ਫੀਸ ਅਤੇ ਬਿਲਿੰਗ",
            "- **ਮਾਸਿਕ ਮੈਸ ਸ਼ੁਲਕ:** ਆਮ ਤੌਰ 'ਤੇ **Rs. 2,700 ਤੋਂ Rs. 3,000** ਪ੍ਰਤੀ ਮਹੀਨਾ।",
            "- **ਪ੍ਰਾਰੰਭਿਕ ਸਿਕਿਉਰਟੀ ਡਿਪਾਜ਼ਿਟ:** ਨਵੇਂ ਵਿਦਿਆਰਥੀਆਂ ਨੂੰ ਕਮਰੇ ਦੀ ਅਲਾਟਮੈਂਟ ਤੋਂ ਪਹਿਲਾਂ ਲਗਭਗ **Rs. 12,700** ਤੱਕ ਜਮ੍ਹਾਂ ਕਰਨਾ ਪੈ ਸਕਦਾ ਹੈ।",
            "- **ਬਿਲਿੰਗ ਨਿਯਮ:** ਮਾਸਿਕ ਬਕਾਇਆ ਸਮੇਂ 'ਤੇ ਜਮ੍ਹਾਂ ਕਰਨਾ ਹੁੰਦਾ ਹੈ, ਨਹੀਂ ਤਾਂ ਜੁਰਮਾਨਾ ਜਾਂ ਮੈਸ ਅਕਾਊਂਟ ਨਾਲ ਸੰਬੰਧਿਤ ਸਮੱਸਿਆ ਹੋ ਸਕਦੀ ਹੈ।",
            "### ਪ੍ਰਬੰਧਨ",
            "- **ਮੈਸ ਕਾਉਂਸਿਲ:** ਵਿਦਿਆਰਥੀ ਨੁਮਾਇੰਦਿਆਂ ਨਾਲ ਇੱਕ ਮੈਸ ਕਾਉਂਸਿਲ ਮੇਨੂ ਅਤੇ ਸਮੱਸਿਆਵਾਂ 'ਤੇ ਚਰਚਾ ਕਰਦੀ ਹੈ।",
            "- **ਲਾਜ਼ਮੀ ਵਰਤੋਂ:** ਹੋਸਟਲ ਰਹਿਣ ਵਾਲਿਆਂ ਲਈ ਮੈਸ ਅਕਾਊਂਟ ਆਮ ਤੌਰ 'ਤੇ ਲਾਜ਼ਮੀ ਹੁੰਦਾ ਹੈ।",
            "### ਨੋਟ",
            "ਨਵੀਂ ਮੈਸ ਫੀਸ, ਸਿਕਿਉਰਟੀ ਡਿਪਾਜ਼ਿਟ ਅਤੇ ਹੋਸਟਲ-ਵਾਰ ਨਿਯਮਾਂ ਲਈ ਹੇਠਾਂ ਦਿੱਤਾ ਅਧਿਕਾਰਿਕ ਸਰੋਤ ਵੇਖੋ।",
        ])
    if is_hindi(lang):
        return "\n\n".join([
            "## Mess Details",
            "GNDEC ke hostels mein generally attached **vegetarian mess facilities** hoti hain, aur girls hostel aur boys hostels dono ke saath dining arrangement available hota hai.",
            "### Food and Dining",
            "- **Meals:** usually breakfast, lunch, evening snacks, aur dinner serve kiya jata hai.",
            "- **Menu style:** weekly rotating menu hota hai; paneer, rajma, dal, aur seasonal sabzi jaisi items regularly include hoti hain.",
            "- **Dining space:** dining halls spacious aur air-cooled hote hain.",
            "- **Quality checks:** food quality aur hygiene inspection ka bhi mention milta hai.",
            "### Charges and Billing",
            "- **Monthly mess charges:** mostly around **Rs. 2,700 to Rs. 3,000** per month.",
            "- **Initial security deposit:** new residents ko room allotment se pehle roughly **Rs. 12,700** ke around mess security deposit dena pad sakta hai.",
            "- **Billing rule:** monthly dues time par clear karne hote hain, warna fine ya mess account issue ho sakta hai.",
            "### Management",
            "- **Mess council:** student representatives ke saath mess council menu aur issues discuss karti hai.",
            "- **Mandatory use:** hostel residents ke liye mess account generally mandatory hota hai.",
            "### Note",
            "Latest mess fee, current security deposit, aur hostel-wise mess rules ke liye neeche diya gaya official resource open kar lo.",
        ])
    if is_punjabi(lang):
        return "\n\n".join([
            "## Mess Details",
            "GNDEC de hostels vich aam taur te attached **vegetarian mess facilities** hundiyan ne, te girls hostel te boys hostels dono naal dining arrangement available hunda hai.",
            "### Food and Dining",
            "- **Meals:** aam taur te breakfast, lunch, evening snacks, te dinner serve kita janda hai.",
            "- **Menu style:** weekly rotating menu hunda hai; paneer, rajma, dal, te seasonal sabzi vargian items regular include hundiyan ne.",
            "- **Dining space:** dining halls spacious te air-cooled hunde ne.",
            "- **Quality checks:** food quality te hygiene inspection da vi zikr milda hai.",
            "### Charges and Billing",
            "- **Monthly mess charges:** zyada tar **Rs. 2,700 to Rs. 3,000** per month de around hunde ne.",
            "- **Initial security deposit:** new residents nu room allotment to pehlan roughly **Rs. 12,700** de around mess security deposit dena pai sakda hai.",
            "- **Billing rule:** monthly dues time te clear karne hunde ne, nahin taan fine jaan mess account issue ho sakda hai.",
            "### Management",
            "- **Mess council:** student representatives naal mess council menu te issues discuss kardi hai.",
            "- **Mandatory use:** hostel residents layi mess account generally mandatory hunda hai.",
            "### Note",
            "Latest mess fee, current security deposit, te hostel-wise mess rules layi thalle ditta official resource open kar lo.",
        ])
    return "\n\n".join([
        "## Mess Details",
        "GNDEC hostels generally have attached **vegetarian mess facilities**, and both girls and boys hostels are supported with dining arrangements.",
        "### Food and Dining",
        "- **Meals:** breakfast, lunch, evening snacks, and dinner are typically served.",
        "- **Menu style:** the menu is usually rotated weekly, with items such as paneer, rajma, dal, and seasonal vegetables appearing regularly.",
        "- **Dining space:** dining halls are generally spacious and air-cooled.",
        "- **Quality checks:** food quality and hygiene inspections are part of the mess system.",
        "### Charges and Billing",
        "- **Monthly mess charges:** mostly around **Rs. 2,700 to Rs. 3,000** per month.",
        "- **Initial security deposit:** new residents may need to deposit roughly **Rs. 12,700** before room allotment.",
        "- **Billing rule:** monthly dues should be cleared on time to avoid fines or mess account issues.",
        "### Management",
        "- **Mess council:** a council with student representatives usually discusses menu improvements and issues.",
        "- **Mandatory use:** a mess account is generally mandatory for hostel residents.",
        "### Note",
        "For the latest mess fee, current security deposit, and hostel-wise mess rules, the official resource below is the best place to check.",
    ])


def extract_faculty_entries(context: str):
    compact = re.sub(r"\s+", " ", context or "").strip()
    pattern = re.compile(
        r"\b\d+\.\s+(?P<name>(?:Dr\.|Er\.|Mr\.|Ms\.|Mrs\.)[^0-9]+?)\s+"
        r"(?P<designation>Professor and Head|Associate Prof\s*&\s*HOD|Associate Prof\.?|Assistant Prof\.?|Professor|Associate Professor|Assistant Professor)\b",
        re.IGNORECASE,
    )

    entries = []
    seen = set()
    for match in pattern.finditer(compact):
        name = re.sub(r"\s+", " ", match.group("name")).strip(" ,")
        designation = re.sub(r"\s+", " ", match.group("designation")).strip(" ,")
        key = f"{name}|{designation}".lower()
        if key in seen:
            continue
        seen.add(key)
        entries.append((name, designation))
        if len(entries) >= 8:
            break

    return entries


def build_faculty_markdown(entries, lang: str, department_label: str = "Department") -> str:
    if is_native_hindi(lang):
        title = f"## {department_label} Faculty"
        summary = f"आधिकारिक फैकल्टी सूची के आधार पर {department_label} के कुछ प्रमुख शिक्षक नीचे दिए गए हैं।"
        detail_heading = "### फैकल्टी झलक"
        footer_heading = "### नोट"
        footer = "यह केवल एक त्वरित झलक है। पूरी और नवीनतम फैकल्टी सूची के लिए नीचे दिया गया आधिकारिक स्रोत खोल सकते हैं।"
    elif is_native_punjabi(lang):
        title = f"## {department_label} Faculty"
        summary = f"ਅਧਿਕਾਰਿਕ ਫੈਕਲਟੀ ਸੂਚੀ ਦੇ ਆਧਾਰ 'ਤੇ {department_label} ਦੇ ਕੁਝ ਮੁੱਖ ਅਧਿਆਪਕ ਹੇਠਾਂ ਦਿੱਤੇ ਗਏ ਹਨ।"
        detail_heading = "### ਫੈਕਲਟੀ ਝਲਕ"
        footer_heading = "### ਨੋਟ"
        footer = "ਇਹ ਸਿਰਫ਼ ਇੱਕ ਤੁਰੰਤ ਝਲਕ ਹੈ। ਪੂਰੀ ਅਤੇ ਨਵੀਂ ਫੈਕਲਟੀ ਸੂਚੀ ਲਈ ਹੇਠਾਂ ਦਿੱਤਾ ਅਧਿਕਾਰਿਕ ਸਰੋਤ ਖੋਲ੍ਹ ਸਕਦੇ ਹੋ।"
    elif is_hindi(lang):
        title = f"## {department_label} Faculty"
        summary = f"Official faculty list ke basis par, {department_label} ke kuch key faculty members neeche diye gaye hain."
        detail_heading = "### Faculty Snapshot"
        footer_heading = "### Note"
        footer = "Yeh sirf quick snapshot hai. Complete aur latest faculty list ke liye neeche diya gaya official resource open kar sakte ho."
    elif is_punjabi(lang):
        title = f"## {department_label} Faculty"
        summary = f"Official faculty list de basis te, {department_label} de kujh key faculty members thalle ditte gaye han."
        detail_heading = "### Faculty Snapshot"
        footer_heading = "### Note"
        footer = "Eh sirf quick snapshot hai. Complete te latest faculty list layi thalle ditta official resource open kar sakde ho."
    else:
        title = f"## {department_label} Faculty"
        summary = f"Based on the official faculty list, here is a quick snapshot of some faculty members from {department_label}."
        detail_heading = "### Faculty Snapshot"
        footer_heading = "### Note"
        footer = "This is a quick snapshot only. You can open the official resource below for the complete and latest faculty list."

    bullets = [f"- **{name}** - {designation}" for name, designation in entries]

    return "\n\n".join([
        title,
        summary,
        detail_heading,
        "\n".join(bullets),
        footer_heading,
        footer,
    ])


def build_json_tag_fallback(json_tag: str, lang: str) -> str:
    if json_tag == "admission_process":
        if is_native_hindi(lang):
            return "\n\n".join([
                "## Admission Process",
                "GNDEC लुधियाना में 2026-27 सत्र के लिए प्रवेश प्रक्रिया सक्रिय है। प्रवेश मुख्य रूप से IKGPTU केंद्रीकृत काउंसलिंग के माध्यम से होते हैं, और कुछ सीटें सीधे काउंसलिंग से भरी जाती हैं।",
                "### General Steps",
                "- **ऑनलाइन पंजीकरण:** GNDEC admission portal पर लॉगिन बनाइए।",
                "- **प्रवेश परीक्षा:** आवश्यक परीक्षा देना ज़रूरी है, जैसे B.Tech के लिए JEE Main, M.Tech के लिए GATE और MBA के लिए CMAT।",
                "- **विश्वविद्यालय काउंसलिंग:** IKGPTU counselling portal पर पंजीकरण करके course और college choices भरिए।",
                "- **सीट आवंटन और रिपोर्टिंग:** सीट मिलने पर GNDEC में दस्तावेज़ सत्यापन और semester fee payment कीजिए।",
                "- **Direct counselling:** Rural, Sikh Minority quota या vacant seats के लिए college-level counselling rounds भी होते हैं।",
                "### Eligibility Snapshot",
                "- **B.Tech:** JEE Main score + 10+2 with Physics, Mathematics and one additional subject.",
                "- **MBA:** CMAT score + minimum 3-year bachelor's degree.",
                "- **MCA:** NIMCET या merit + BCA/B.Sc. (CS/IT) with 50% marks and Mathematics background.",
                "- **M.Tech:** GATE score + relevant B.E./B.Tech with 50% marks.",
                "- **BBA / BCA:** 10+2 के बाद merit-based admission.",
                "### Important Dates for 2026",
                "- **Registration open:** March 26, 2026.",
                "- **JEE Main Session 2 result:** expected around April 20, 2026.",
                "- **IKGPTU counselling starts:** tentatively June 2026.",
                "- **Direct or spot counselling:** tentatively August 2026.",
                "### Required Documents",
                "- 10th and 12th DMC या mark sheets",
                "- JEE, GATE, CMAT या NIMCET scorecard",
                "- Punjab State quota के लिए residence certificate",
                "- SC, ST, OBC, Rural या Sikh Minority category certificate",
                "- Candidate और parents का Aadhaar card",
                "- Character और migration certificates",
                "### Note",
                "नवीनतम registration status, counselling notice और official updates के लिए नीचे दिया गया admission portal खोलिए।",
            ])
        if is_native_punjabi(lang):
            return "\n\n".join([
                "## Admission Process",
                "GNDEC ਲੁਧਿਆਣਾ ਵਿੱਚ 2026-27 ਸੈਸ਼ਨ ਲਈ ਦਾਖਲਾ ਪ੍ਰਕਿਰਿਆ ਸਰਗਰਮ ਹੈ। ਦਾਖਲੇ ਮੁੱਖ ਤੌਰ 'ਤੇ IKGPTU ਦੀ ਕੇਂਦਰੀ ਕਾਊਂਸਲਿੰਗ ਰਾਹੀਂ ਹੁੰਦੇ ਹਨ, ਅਤੇ ਕੁਝ ਸੀਟਾਂ ਸਿੱਧੀ ਕਾਊਂਸਲਿੰਗ ਰਾਹੀਂ ਭਰੀਆਂ ਜਾਂਦੀਆਂ ਹਨ।",
                "### General Steps",
                "- **ਆਨਲਾਈਨ ਰਜਿਸਟ੍ਰੇਸ਼ਨ:** GNDEC admission portal 'ਤੇ ਲੌਗਿਨ ਬਣਾਓ।",
                "- **Entrance exam:** ਲੋੜੀਂਦੀ ਪਰੀਖਿਆ ਦੇਣਾ ਜ਼ਰੂਰੀ ਹੈ, ਜਿਵੇਂ B.Tech ਲਈ JEE Main, M.Tech ਲਈ GATE ਅਤੇ MBA ਲਈ CMAT।",
                "- **University counselling:** IKGPTU counselling portal 'ਤੇ ਰਜਿਸਟਰ ਕਰਕੇ course ਅਤੇ college choices ਭਰੋ।",
                "- **Seat allotment and reporting:** ਸੀਟ ਮਿਲਣ 'ਤੇ GNDEC ਵਿੱਚ documents verification ਅਤੇ semester fee payment ਕਰੋ।",
                "- **Direct counselling:** Rural, Sikh Minority quota ਜਾਂ vacant seats ਲਈ college-level counselling rounds ਵੀ ਹੁੰਦੇ ਹਨ।",
                "### Eligibility Snapshot",
                "- **B.Tech:** JEE Main score + 10+2 with Physics, Mathematics and one additional subject.",
                "- **MBA:** CMAT score + minimum 3-year bachelor's degree.",
                "- **MCA:** NIMCET ਜਾਂ merit + BCA/B.Sc. (CS/IT) with 50% marks and Mathematics background.",
                "- **M.Tech:** GATE score + relevant B.E./B.Tech with 50% marks.",
                "- **BBA / BCA:** 10+2 ਤੋਂ ਬਾਅਦ merit-based admission.",
                "### Important Dates for 2026",
                "- **Registration open:** March 26, 2026.",
                "- **JEE Main Session 2 result:** expected around April 20, 2026.",
                "- **IKGPTU counselling starts:** tentatively June 2026.",
                "- **Direct or spot counselling:** tentatively August 2026.",
                "### Required Documents",
                "- 10th ਅਤੇ 12th DMC ਜਾਂ mark sheets",
                "- JEE, GATE, CMAT ਜਾਂ NIMCET scorecard",
                "- Punjab State quota ਲਈ residence certificate",
                "- SC, ST, OBC, Rural ਜਾਂ Sikh Minority category certificate",
                "- Candidate ਅਤੇ parents ਦਾ Aadhaar card",
                "- Character ਅਤੇ migration certificates",
                "### Note",
                "ਨਵੀਂ registration status, counselling notice ਅਤੇ official updates ਲਈ ਹੇਠਾਂ ਦਿੱਤਾ admission portal ਖੋਲ੍ਹੋ।",
            ])
        if is_hindi(lang):
            return "\n\n".join([
                "## Admission Process",
                "GNDEC Ludhiana mein 2026-27 session ke liye admission process active hai. Admissions mainly IKGPTU centralized counselling ke through hoti hain, aur kuch seats direct counselling ke through fill hoti hain.",
                "### General Steps",
                "- **Online registration:** GNDEC admission portal par login create karo.",
                "- **Entrance exam:** required exam dena zaroori hai, jaise B.Tech ke liye JEE Main, M.Tech ke liye GATE, MBA ke liye CMAT.",
                "- **University counselling:** IKGPTU counselling portal par register karke course aur college choices fill karo.",
                "- **Seat allotment and reporting:** seat milne par GNDEC mein document verification aur semester fee payment karo.",
                "- **Direct counselling:** Rural, Sikh Minority quota ya vacant seats ke liye college-level counselling rounds bhi hoti hain.",
                "### Eligibility Snapshot",
                "- **B.Tech:** JEE Main score + 10+2 with Physics, Mathematics, and one additional subject.",
                "- **MBA:** CMAT score + minimum 3-year bachelor's degree.",
                "- **MCA:** NIMCET ya merit + BCA/B.Sc. (CS/IT) with 50% marks and Mathematics background.",
                "- **M.Tech:** GATE score + relevant B.E./B.Tech with 50% marks.",
                "- **BBA / BCA:** merit-based admission after 10+2.",
                "### Important Dates for 2026",
                "- **Registration open:** March 26, 2026.",
                "- **JEE Main Session 2 result:** expected around April 20, 2026.",
                "- **IKGPTU counselling starts:** tentatively June 2026.",
                "- **Direct or spot counselling:** tentatively August 2026.",
                "### Required Documents",
                "- 10th and 12th DMC or mark sheets",
                "- Entrance exam scorecard such as JEE, GATE, CMAT, or NIMCET",
                "- Residence certificate for Punjab State quota",
                "- Category certificate such as SC, ST, OBC, Rural, or Sikh Minority",
                "- Aadhaar card of candidate and parents",
                "- Character and migration certificates from the last attended institute",
                "### Note",
                "Latest registration status, counselling notice, aur official updates ke liye neeche diya gaya admission portal open kar lo.",
            ])
        if is_punjabi(lang):
            return "\n\n".join([
                "## Admission Process",
                "GNDEC Ludhiana vich 2026-27 session layi admission process active hai. Admissions mostly IKGPTU centralized counselling raahi hundiyan han, te kujh seats direct counselling naal fill hundiyan han.",
                "### General Steps",
                "- **Online registration:** GNDEC admission portal te login create karo.",
                "- **Entrance exam:** required exam dena zaroori hai, jiven B.Tech layi JEE Main, M.Tech layi GATE, MBA layi CMAT.",
                "- **University counselling:** IKGPTU counselling portal te register karke course te college choices fill karo.",
                "- **Seat allotment and reporting:** seat allot hon te GNDEC vich document verification te semester fee deposit karo.",
                "- **Direct counselling:** Rural, Sikh Minority quota jaan vacant seats layi college-level counselling rounds vi hunde han.",
                "### Eligibility Snapshot",
                "- **B.Tech:** JEE Main score + 10+2 with Physics, Mathematics, and one additional subject.",
                "- **MBA:** CMAT score + minimum 3-year bachelor's degree.",
                "- **MCA:** NIMCET jaan merit + BCA/B.Sc. (CS/IT) with 50% marks and Mathematics background.",
                "- **M.Tech:** GATE score + relevant B.E./B.Tech with 50% marks.",
                "- **BBA / BCA:** merit-based admission after 10+2.",
                "### Important Dates for 2026",
                "- **Registration open:** March 26, 2026.",
                "- **JEE Main Session 2 result:** expected around April 20, 2026.",
                "- **IKGPTU counselling starts:** tentatively June 2026.",
                "- **Direct or spot counselling:** tentatively August 2026.",
                "### Required Documents",
                "- 10th and 12th DMC or mark sheets",
                "- Entrance exam scorecard jiven JEE, GATE, CMAT, jaan NIMCET",
                "- Residence certificate Punjab State quota layi",
                "- Category certificate jiven SC, ST, OBC, Rural, jaan Sikh Minority",
                "- Aadhaar card of candidate and parents",
                "- Character te migration certificates last attended institute ton",
                "### Note",
                "Latest registration status, counselling notice, te official updates layi thalle ditta admission portal open karo.",
            ])
        return "\n\n".join([
            "## Admission Process",
            "The GNDEC Ludhiana admission process for the 2026-27 session is active. Admissions are mainly handled through IKGPTU centralized counselling, with direct counselling also used for some quota seats and remaining vacancies.",
            "### General Steps",
            "- **Online registration:** create a login on the GNDEC admission portal.",
            "- **Entrance exam:** appear for the required exam, such as JEE Main for B.Tech, GATE for M.Tech, or CMAT for MBA.",
            "- **University counselling:** register on the IKGPTU counselling portal and fill your course and college choices.",
            "- **Seat allotment and reporting:** if a seat is allotted at GNDEC, complete document verification and semester fee payment.",
            "- **Direct counselling:** GNDEC also conducts direct counselling for Rural, Sikh Minority, and vacant-seat categories.",
            "### Eligibility Snapshot",
            "- **B.Tech:** JEE Main score with 10+2 in Physics, Mathematics, and one additional subject.",
            "- **MBA:** CMAT score with a minimum 3-year bachelor's degree.",
            "- **MCA:** NIMCET or merit with BCA/B.Sc. (CS/IT) and 50% marks plus Mathematics background.",
            "- **M.Tech:** GATE score with a relevant B.E./B.Tech and 50% marks.",
            "- **BBA / BCA:** merit-based admission after 10+2.",
            "### Important Dates for 2026",
            "- **Registration open:** March 26, 2026.",
            "- **JEE Main Session 2 results:** expected around April 20, 2026.",
            "- **IKGPTU counselling starts:** tentatively June 2026.",
            "- **Direct or spot counselling:** tentatively August 2026.",
            "### Required Documents",
            "- 10th and 12th DMC or mark sheets",
            "- Entrance exam scorecard such as JEE, GATE, CMAT, or NIMCET",
            "- Residence certificate for the Punjab State quota",
            "- Category certificate such as SC, ST, OBC, Rural, or Sikh Minority",
            "- Aadhaar card of the candidate and parents",
            "- Character and migration certificates from the last attended institute",
            "### Note",
            "For the latest registration status, counselling notice, and official updates, open the admission portal below.",
        ])

    if json_tag == "admission_documents":
        if is_native_hindi(lang):
            return "\n\n".join([
                "## B.Tech Admission Documents",
                "GNDEC में B.Tech प्रवेश के लिए ऑनलाइन आवेदन और physical verification दोनों के लिए दस्तावेज़ तैयार रखना बेहतर रहता है.",
                "### Essential Academic Documents",
                "- **JEE Main 2026 score card**",
                "- **10th DMC / certificate** date of birth proof के लिए",
                "- **10+2 DMC / certificate**",
                "- **Character certificate** last attended school या institute से",
                "- **Migration certificate** यदि बोर्ड PSEB से अलग हो",
                "### Identity and Personal Records",
                "- **Aadhaar card copies** candidate, father और mother की",
                "- **Recent passport-size photographs**",
                "- **Medical fitness certificate** prescribed format में",
                "### Category or Quota Documents",
                "- **Residence certificate** Punjab State quota के लिए",
                "- **Category certificate** जैसे SC, ST, BC, Border Area, Sports, Rural, Sikh Minority",
                "- **SRE result** Sikh Minority quota के लिए",
                "- **Rural area residence और rural education certificate** rural quota के लिए",
                "- **Gap year affidavit** यदि studies में gap हो",
                "- **Income certificate / ITR** TFW या PMS schemes के लिए",
                "### Note",
                "नवीनतम checklist, format और admission notice के लिए नीचे दिया गया official GNDEC admission resource खोलें.",
            ])
        if is_native_punjabi(lang):
            return "\n\n".join([
                "## B.Tech Admission Documents",
                "GNDEC ਵਿੱਚ B.Tech ਦਾਖਲੇ ਲਈ online application ਅਤੇ physical verification ਦੋਵਾਂ ਲਈ ਦਸਤਾਵੇਜ਼ ਤਿਆਰ ਰੱਖਣਾ ਵਧੀਆ ਰਹਿੰਦਾ ਹੈ.",
                "### Essential Academic Documents",
                "- **JEE Main 2026 score card**",
                "- **10th DMC / certificate** date of birth proof ਲਈ",
                "- **10+2 DMC / certificate**",
                "- **Character certificate** ਪਿਛਲੇ school ਜਾਂ institute ਤੋਂ",
                "- **Migration certificate** ਜੇ board PSEB ਤੋਂ ਵੱਖ ਹੋਵੇ",
                "### Identity and Personal Records",
                "- **Aadhaar card copies** candidate, father ਅਤੇ mother ਦੀਆਂ",
                "- **Recent passport-size photographs**",
                "- **Medical fitness certificate** prescribed format ਵਿੱਚ",
                "### Category or Quota Documents",
                "- **Residence certificate** Punjab State quota ਲਈ",
                "- **Category certificate** ਜਿਵੇਂ SC, ST, BC, Border Area, Sports, Rural, Sikh Minority",
                "- **SRE result** Sikh Minority quota ਲਈ",
                "- **Rural area residence ਅਤੇ rural education certificate** rural quota ਲਈ",
                "- **Gap year affidavit** ਜੇ studies ਵਿੱਚ gap ਹੋਵੇ",
                "- **Income certificate / ITR** TFW ਜਾਂ PMS schemes ਲਈ",
                "### Note",
                "ਨਵੀਂ checklist, format ਅਤੇ admission notice ਲਈ ਹੇਠਾਂ ਦਿੱਤਾ official GNDEC admission resource ਖੋਲ੍ਹੋ.",
            ])
        if is_hindi(lang):
            return "\n\n".join([
                "## B.Tech Admission Documents",
                "GNDEC mein B.Tech admission ke liye online application aur physical verification dono ke time yeh documents ready rakhna useful hota hai.",
                "### Essential Academic Documents",
                "- **JEE Main 2026 score card**",
                "- **10th DMC / certificate** as date of birth proof",
                "- **10+2 DMC / certificate**",
                "- **Character certificate** from the last attended school or institute",
                "- **Migration certificate** if your board is different from PSEB",
                "### Identity and Personal Records",
                "- **Aadhaar copies** of candidate, father, and mother",
                "- **Recent passport-size photographs**",
                "- **Medical fitness certificate** in the prescribed format",
                "### Category or Quota Documents",
                "- **Residence certificate** for Punjab State quota",
                "- **Category certificate** such as SC, ST, BC, Border Area, Sports, Rural, or Sikh Minority",
                "- **SRE result** for Sikh Minority quota",
                "- **Rural residence and rural education certificate** for rural quota seats",
                "- **Gap year affidavit** if there is a break in studies",
                "- **Income certificate or ITR** for TFW or PMS schemes",
                "### Note",
                "Latest checklist, format, aur notice ke liye neeche diya gaya official GNDEC admission resource open kar lo.",
            ])
        if is_punjabi(lang):
            return "\n\n".join([
                "## B.Tech Admission Documents",
                "GNDEC vich B.Tech admission layi online application te physical verification dono samay eh documents ready rakhne changa rehnda hai.",
                "### Essential Academic Documents",
                "- **JEE Main 2026 score card**",
                "- **10th DMC / certificate** date of birth proof layi",
                "- **10+2 DMC / certificate**",
                "- **Character certificate** last attended school jaan institute ton",
                "- **Migration certificate** je board PSEB ton vakh hove",
                "### Identity and Personal Records",
                "- **Aadhaar copies** candidate, father, te mother dian",
                "- **Recent passport-size photographs**",
                "- **Medical fitness certificate** prescribed format vich",
                "### Category or Quota Documents",
                "- **Residence certificate** Punjab State quota layi",
                "- **Category certificate** jiven SC, ST, BC, Border Area, Sports, Rural, jaan Sikh Minority",
                "- **SRE result** Sikh Minority quota layi",
                "- **Rural residence te rural education certificate** rural quota seats layi",
                "- **Gap year affidavit** je studies vich break hove",
                "- **Income certificate jaan ITR** TFW jaan PMS schemes layi",
                "### Note",
                "Latest checklist, format, te notice layi thalle ditta official GNDEC admission resource open karo.",
            ])
        return "\n\n".join([
            "## B.Tech Admission Documents",
            "For B.Tech admissions at GNDEC, it is useful to keep both your online-application documents and physical-verification documents ready.",
            "### Essential Academic Documents",
            "- **JEE Main 2026 score card**",
            "- **10th DMC / certificate** for date of birth proof",
            "- **10+2 DMC / certificate**",
            "- **Character certificate** from the last attended school or institute",
            "- **Migration certificate** if you are from a board other than PSEB",
            "### Identity and Personal Records",
            "- **Aadhaar card copies** of the candidate, father, and mother",
            "- **Recent passport-size photographs**",
            "- **Medical fitness certificate** in the prescribed format",
            "### Category or Quota Documents",
            "- **Residence certificate** for Punjab State quota",
            "- **Reserved category certificate** such as SC, ST, BC, Border Area, Sports, Rural, or Sikh Minority",
            "- **SRE result** for the Sikh Minority quota",
            "- **Rural residence and rural education certificate** for rural quota seats",
            "- **Gap year affidavit** if there is a break in studies",
            "- **Income certificate or ITR** for TFW or PMS schemes",
            "### Note",
            "For the latest checklist, exact formats, and current admission notice, open the official GNDEC admission resource below.",
        ])

    if json_tag == "sre_exam":
        if is_native_hindi(lang):
            return "\n\n".join([
                "## SRE Exam Details",
                "Sikh Religion Examination (SRE) GNDEC और SGPC institutes में Sikh Minority quota के लिए महत्वपूर्ण प्रवेश परीक्षा है.",
                "### 2026 Snapshot",
                "- **Examination window:** 21 मार्च 2026 से 8 मई 2026",
                "- **Registration:** GNDEC admission portal के माध्यम से",
                "- **Format:** 25 MCQs, कुल 50 अंक",
                "- **Duration:** 30 minutes",
                "- **Languages:** English और Punjabi",
                "- **Qualifying marks:** 40% यानी 20 marks",
                "- **Attempts:** अधिकतम 2, best score count होता है",
                "### Fees and Documents",
                "- **User creation fee:** Rs. 250",
                "- **Exam fee:** Rs. 350",
                "- **Carry:** Aadhaar card, 10th/12th DMC या admit card, और recent photograph",
                "### Eligibility",
                "- Sikh Minority quota के लिए apply करने वाले Sikh candidates के लिए relevant resource यही है.",
                "### Note",
                "Registration status, final instructions, और latest official update के लिए नीचे दिया गया GNDEC SRE resource खोलें.",
            ])
        if is_native_punjabi(lang):
            return "\n\n".join([
                "## SRE Exam Details",
                "Sikh Religion Examination (SRE) GNDEC ਅਤੇ SGPC institutes ਵਿੱਚ Sikh Minority quota ਲਈ ਮਹੱਤਵਪੂਰਨ entrance test ਹੈ.",
                "### 2026 Snapshot",
                "- **Examination window:** 21 ਮਾਰਚ 2026 ਤੋਂ 8 ਮਈ 2026",
                "- **Registration:** GNDEC admission portal ਰਾਹੀਂ",
                "- **Format:** 25 MCQs, ਕੁੱਲ 50 marks",
                "- **Duration:** 30 minutes",
                "- **Languages:** English ਅਤੇ Punjabi",
                "- **Qualifying marks:** 40% ਅਰਥਾਤ 20 marks",
                "- **Attempts:** ਵੱਧ ਤੋਂ ਵੱਧ 2, best score count ਹੁੰਦਾ ਹੈ",
                "### Fees and Documents",
                "- **User creation fee:** Rs. 250",
                "- **Exam fee:** Rs. 350",
                "- **Carry:** Aadhaar card, 10th/12th DMC ਜਾਂ admit card, ਅਤੇ recent photograph",
                "### Eligibility",
                "- Sikh Minority quota ਲਈ apply ਕਰਨ ਵਾਲੇ Sikh candidates ਲਈ ਇਹ relevant official resource ਹੈ.",
                "### Note",
                "Registration status, final instructions, ਅਤੇ latest official update ਲਈ ਹੇਠਾਂ ਦਿੱਤਾ GNDEC SRE resource ਖੋਲ੍ਹੋ.",
            ])
        if is_hindi(lang):
            return "\n\n".join([
                "## SRE Exam Details",
                "Sikh Religion Examination ya SRE GNDEC aur SGPC institutes mein Sikh Minority quota ke liye important entrance test hai.",
                "### 2026 Snapshot",
                "- **Examination window:** March 21, 2026 to May 8, 2026",
                "- **Registration:** through the GNDEC admission portal",
                "- **Format:** 25 MCQs for a total of 50 marks",
                "- **Duration:** 30 minutes",
                "- **Languages:** English and Punjabi",
                "- **Qualifying marks:** 40% यानी 20 marks",
                "- **Attempts:** maximum 2, and the best score is counted",
                "### Fees and Documents",
                "- **User creation fee:** Rs. 250",
                "- **Exam fee:** Rs. 350",
                "- **Carry:** Aadhaar card, 10th/12th DMC or admit card, and a recent photograph",
                "### Eligibility",
                "- Sikh Minority quota ke liye apply karne wale Sikh candidates ke liye yeh important official resource hai.",
                "### Note",
                "Latest registration status, instructions, aur official update ke liye neeche diya gaya SRE resource open kar lo.",
            ])
        if is_punjabi(lang):
            return "\n\n".join([
                "## SRE Exam Details",
                "Sikh Religion Examination jaan SRE GNDEC te SGPC institutes vich Sikh Minority quota layi important entrance test hai.",
                "### 2026 Snapshot",
                "- **Examination window:** March 21, 2026 ton May 8, 2026",
                "- **Registration:** GNDEC admission portal raahi",
                "- **Format:** 25 MCQs, total 50 marks",
                "- **Duration:** 30 minutes",
                "- **Languages:** English te Punjabi",
                "- **Qualifying marks:** 40% yani 20 marks",
                "- **Attempts:** maximum 2, te best score count hunda hai",
                "### Fees and Documents",
                "- **User creation fee:** Rs. 250",
                "- **Exam fee:** Rs. 350",
                "- **Carry:** Aadhaar card, 10th/12th DMC jaan admit card, te recent photograph",
                "### Eligibility",
                "- Sikh Minority quota layi apply karan wale Sikh candidates layi eh important official resource hai.",
                "### Note",
                "Latest registration status, instructions, te official update layi thalle ditta SRE resource open karo.",
            ])
        return "\n\n".join([
            "## SRE Exam Details",
            "The Sikh Religion Examination (SRE) is an important admission-related test for candidates applying under the Sikh Minority quota at GNDEC and other SGPC institutes.",
            "### 2026 Snapshot",
            "- **Examination window:** March 21, 2026 to May 8, 2026",
            "- **Registration:** through the GNDEC admission portal",
            "- **Format:** 25 MCQs for a total of 50 marks",
            "- **Duration:** 30 minutes",
            "- **Languages:** English and Punjabi",
            "- **Qualifying marks:** 40% or 20 marks",
            "- **Attempts:** maximum 2, with the best score counted",
            "### Fees and Documents",
            "- **User creation fee:** Rs. 250",
            "- **Exam fee:** Rs. 350",
            "- **Carry:** Aadhaar card, 10th/12th DMC or admit card, and a recent photograph",
            "### Note",
            "For registration status, final instructions, and the latest official update, open the GNDEC SRE resource below.",
        ])

    if json_tag == "makeup_exam_info":
        if is_native_hindi(lang):
            return "\n\n".join([
                "## Makeup Examination Details",
                "GNDEC में makeup examinations या re-exams नियमित End Semester Examination के बाद eligible students के लिए आयोजित किए जाते हैं।",
                "### Eligibility and Rules",
                "- **Who can apply:** on-roll students जिनका CIE 60% से ऊपर हो।",
                "- **Failure case:** theory portion में 40% से कम अंक।",
                "- **Absence case:** accident या severe illness जैसे गंभीर कारणों में prior permission के साथ।",
                "- **Not eligible:** dropped, detained या UMC वाले students eligible नहीं होते।",
                "### Key Policy Points",
                "- **Grade rule:** makeup exam का grade सामान्यतः next lower passing grade के रूप में दिया जाता है।",
                "- **Subject limit:** UG में सामान्यतः 2 regular subjects और PG में 1 subject per semester।",
                "- **Fee:** Rs. 1000 per subject.",
                "- **Application process:** GNDEC student login portal पर form fill और lock करना होता है।",
                "### Exam Logistics",
                "- **Venue:** Examination Hall, Diploma Building.",
                "- **Timing:** अधिकांश sessions 1:00 PM से 4:00 PM तक।",
                "- **Carry:** College ID card और admit card दोनों साथ लाएँ।",
                "### Note",
                "नवीनतम notice, form submission window और exact date sheet के लिए नीचे दिया गया official exam portal खोलिए।",
            ])
        if is_native_punjabi(lang):
            return "\n\n".join([
                "## Makeup Examination Details",
                "GNDEC ਵਿੱਚ makeup examinations ਜਾਂ re-exams ਨਿਯਮਤ End Semester Examination ਤੋਂ ਬਾਅਦ eligible students ਲਈ ਕਰਵਾਏ ਜਾਂਦੇ ਹਨ।",
                "### Eligibility and Rules",
                "- **Who can apply:** on-roll students ਜਿਨ੍ਹਾਂ ਦਾ CIE 60% ਤੋਂ ਉੱਪਰ ਹੋਵੇ।",
                "- **Failure case:** theory portion ਵਿੱਚ 40% ਤੋਂ ਘੱਟ ਅੰਕ।",
                "- **Absence case:** accident ਜਾਂ severe illness ਵਰਗੇ ਗੰਭੀਰ ਕਾਰਨਾਂ ਵਿੱਚ prior permission ਨਾਲ।",
                "- **Not eligible:** dropped, detained ਜਾਂ UMC ਵਾਲੇ students eligible ਨਹੀਂ ਹੁੰਦੇ।",
                "### Key Policy Points",
                "- **Grade rule:** makeup exam ਦਾ grade ਆਮ ਤੌਰ 'ਤੇ next lower passing grade ਦੇ ਰੂਪ ਵਿੱਚ ਮਿਲਦਾ ਹੈ।",
                "- **Subject limit:** UG ਵਿੱਚ ਆਮ ਤੌਰ 'ਤੇ 2 regular subjects ਅਤੇ PG ਵਿੱਚ 1 subject per semester।",
                "- **Fee:** Rs. 1000 per subject.",
                "- **Application process:** GNDEC student login portal 'ਤੇ form fill ਅਤੇ lock ਕਰਨਾ ਹੁੰਦਾ ਹੈ।",
                "### Exam Logistics",
                "- **Venue:** Examination Hall, Diploma Building.",
                "- **Timing:** ਵੱਧਤਰ sessions 1:00 PM ਤੋਂ 4:00 PM ਤੱਕ।",
                "- **Carry:** College ID card ਅਤੇ admit card ਦੋਵੇਂ ਨਾਲ ਲਿਆਓ।",
                "### Note",
                "ਨਵੀਂ notice, form submission window ਅਤੇ exact date sheet ਲਈ ਹੇਠਾਂ ਦਿੱਤਾ official exam portal ਖੋਲ੍ਹੋ।",
            ])
        if is_hindi(lang):
            return "\n\n".join([
                "## Makeup Examination Details",
                "GNDEC mein makeup examinations ya re-exams regular End Semester Examination ke baad eligible students ke liye conduct hote hain.",
                "### Eligibility and Rules",
                "- **Who can apply:** on-roll students jinka CIE 60% se above ho.",
                "- **Failure case:** theory portion mein 40% se kam marks.",
                "- **Absence case:** accident ya severe illness jaise serious reasons par prior permission ke saath.",
                "- **Not eligible:** dropped, detained, ya UMC case wale students.",
                "### Key Policy Points",
                "- **Grade rule:** makeup exam ka grade usually next lower passing grade ke form mein award hota hai.",
                "- **Subject limit:** UG mein generally 2 regular subjects aur PG mein 1 subject per semester.",
                "- **Fee:** Rs. 1000 per subject.",
                "- **Application process:** GNDEC student login portal par form fill aur lock karna hota hai.",
                "### Exam Logistics",
                "- **Venue:** Examination Hall, Diploma Building.",
                "- **Timing:** most sessions 1:00 PM se 4:00 PM tak.",
                "- **Carry:** College ID card aur admit card dono zaroor le kar aao.",
                "### Note",
                "Latest notice, form submission window, aur exact date sheet ke liye neeche diya gaya official exam portal open kar lo.",
            ])
        if is_punjabi(lang):
            return "\n\n".join([
                "## Makeup Examination Details",
                "GNDEC vich makeup examinations jaan re-exams regular End Semester Examination to baad eligible students layi karvaye jande han.",
                "### Eligibility and Rules",
                "- **Who can apply:** on-roll students jinna da CIE 60% ton upar hove.",
                "- **Failure case:** theory portion vich 40% ton ghatt marks.",
                "- **Absence case:** accident jaan severe illness varge serious reasons te prior permission naal.",
                "- **Not eligible:** dropped, detained, jaan UMC case wale students.",
                "### Key Policy Points",
                "- **Grade rule:** makeup exam da grade aam taur te next lower passing grade de roop vich milda hai.",
                "- **Subject limit:** UG layi aam taur te 2 regular subjects, PG layi 1 subject per semester.",
                "- **Fee:** Rs. 1000 per subject.",
                "- **Application process:** GNDEC student login portal te form fill te lock karna hunda hai.",
                "### Exam Logistics",
                "- **Venue:** Examination Hall, Diploma Building.",
                "- **Timing:** zyada tar sessions 1:00 PM ton 4:00 PM tak.",
                "- **Carry:** College ID card te admit card dono zaroor le ke aao.",
                "### Note",
                "Latest notice, form submission window, te exact date sheet layi thalle ditta official exam portal open karo.",
            ])
        return "\n\n".join([
            "## Makeup Examination Details",
            "At GNDEC, makeup examinations or re-exams are generally conducted after the regular End Semester Examinations for eligible students.",
            "### Eligibility and Rules",
            "- **Who can apply:** on-roll students with a Continuous Internal Evaluation (CIE) above 60%.",
            "- **Failure case:** students scoring below 40% in the theory portion of the ESE.",
            "- **Absence case:** students absent for serious reasons such as accidents or severe illness, with prior permission from the Office of the Dean Academics.",
            "- **Not eligible:** dropped, detained, or UMC students are excluded.",
            "### Key Policy Points",
            "- **Grade rule:** the makeup exam grade is usually awarded as the next lower passing grade.",
            "- **Subject limit:** generally up to 2 regular subjects for UG and 1 regular subject for PG per semester.",
            "- **Fee:** Rs. 1000 per subject.",
            "- **Application process:** forms are filled and locked through the GNDEC student login portal.",
            "### Exam Logistics",
            "- **Venue:** Examination Hall, Diploma Building.",
            "- **Timing:** most sessions are scheduled from 1:00 PM to 4:00 PM.",
            "- **Carry:** both the College ID card and admit card.",
            "### Note",
                "For the latest notice, exact date sheet, and current form submission window, open the official exam portal below.",
            ])

    if json_tag == "fee_structure":
        if is_native_hindi(lang):
            return "\n\n".join([
                "## Fee Structure Overview",
                "GNDEC में academic fee program और admission category के अनुसार बदलती है. Payment के लिए official admission portal और fee resource सबसे उपयोगी रहते हैं.",
                "### Course Fee Snapshot",
                "- **B.Tech (4 years):** लगभग Rs. 4.49 lakh total",
                "- **B.Tech Lateral Entry (3 years):** लगभग Rs. 3.32 to 3.39 lakh",
                "- **B.Arch (5 years):** लगभग Rs. 4.42 lakh",
                "- **MBA / MCA (2 years):** लगभग Rs. 2.06 lakh",
                "- **BBA / BCA (3 years):** लगभग Rs. 2.09 lakh",
                "- **M.Tech (2 years):** लगभग Rs. 1.62 lakh",
                "### Hostel and Mess",
                "- **Hostel rent:** लगभग Rs. 11,900 to 14,300 per semester",
                "- **Mess fee:** लगभग Rs. 15,200 per semester",
                "- **Security deposit:** लगभग Rs. 5,000 refundable",
                "### Scholarship and Waiver Support",
                "- **PMS:** eligible SC students के लिए reduced semester fee support",
                "- **TFW:** Punjab resident students with lower family income may get tuition fee waiver",
                "- **Sikh Minority scholarship support:** some internal scholarship opportunities may apply",
                "### Note",
                "सटीक current semester fee, branch-wise breakup और latest notice के लिए नीचे दिया गया official fee resource खोलें.",
            ])
        if is_native_punjabi(lang):
            return "\n\n".join([
                "## Fee Structure Overview",
                "GNDEC ਵਿੱਚ academic fee program ਅਤੇ admission category ਮੁਤਾਬਕ ਬਦਲਦੀ ਹੈ. Payment ਲਈ official admission portal ਅਤੇ fee resource ਸਭ ਤੋਂ ਵਧੀਆ ਹਨ.",
                "### Course Fee Snapshot",
                "- **B.Tech (4 years):** ਲਗਭਗ Rs. 4.49 lakh total",
                "- **B.Tech Lateral Entry (3 years):** ਲਗਭਗ Rs. 3.32 to 3.39 lakh",
                "- **B.Arch (5 years):** ਲਗਭਗ Rs. 4.42 lakh",
                "- **MBA / MCA (2 years):** ਲਗਭਗ Rs. 2.06 lakh",
                "- **BBA / BCA (3 years):** ਲਗਭਗ Rs. 2.09 lakh",
                "- **M.Tech (2 years):** ਲਗਭਗ Rs. 1.62 lakh",
                "### Hostel and Mess",
                "- **Hostel rent:** ਲਗਭਗ Rs. 11,900 to 14,300 per semester",
                "- **Mess fee:** ਲਗਭਗ Rs. 15,200 per semester",
                "- **Security deposit:** ਲਗਭਗ Rs. 5,000 refundable",
                "### Scholarship and Waiver Support",
                "- **PMS:** eligible SC students ਲਈ reduced semester fee support",
                "- **TFW:** Punjab resident students with lower family income nu tuition fee waiver mil sakda hai",
                "- **Sikh Minority scholarship support:** kujh internal scholarship opportunities apply ho sakdiyan han",
                "### Note",
                "Exact current semester fee, branch-wise breakup ਅਤੇ latest notice ਲਈ ਹੇਠਾਂ ਦਿੱਤਾ official fee resource ਖੋਲ੍ਹੋ.",
            ])
        if is_hindi(lang):
            return "\n\n".join([
                "## Fee Structure Overview",
                "GNDEC mein academic fee program aur admission category ke hisaab se vary karti hai. Exact payment details ke liye official admission portal aur fee resource best source hote hain.",
                "### Course Fee Snapshot",
                "- **B.Tech (4 years):** around Rs. 4.49 lakh total",
                "- **B.Tech Lateral Entry (3 years):** around Rs. 3.32 to 3.39 lakh",
                "- **B.Arch (5 years):** around Rs. 4.42 lakh",
                "- **MBA / MCA (2 years):** around Rs. 2.06 lakh",
                "- **BBA / BCA (3 years):** around Rs. 2.09 lakh",
                "- **M.Tech (2 years):** around Rs. 1.62 lakh",
                "### Hostel and Mess",
                "- **Hostel rent:** around Rs. 11,900 to 14,300 per semester",
                "- **Mess fee:** around Rs. 15,200 per semester",
                "- **Security deposit:** around Rs. 5,000 refundable",
                "### Scholarship and Waiver Support",
                "- **PMS:** eligible SC students ke liye reduced semester fee support",
                "- **TFW:** eligible Punjab resident students ko tuition fee waiver mil sakta hai",
                "- **Sikh Minority support:** some internal scholarship options may apply",
                "### Note",
                "Exact current semester fee, branch-wise breakup, aur latest notice ke liye neeche diya gaya official fee resource open kar lo.",
            ])
        if is_punjabi(lang):
            return "\n\n".join([
                "## Fee Structure Overview",
                "GNDEC vich academic fee program te admission category de hisaab naal vary kardi hai. Exact payment details layi official admission portal te fee resource sab ton vadhiya source hunde han.",
                "### Course Fee Snapshot",
                "- **B.Tech (4 years):** around Rs. 4.49 lakh total",
                "- **B.Tech Lateral Entry (3 years):** around Rs. 3.32 to 3.39 lakh",
                "- **B.Arch (5 years):** around Rs. 4.42 lakh",
                "- **MBA / MCA (2 years):** around Rs. 2.06 lakh",
                "- **BBA / BCA (3 years):** around Rs. 2.09 lakh",
                "- **M.Tech (2 years):** around Rs. 1.62 lakh",
                "### Hostel and Mess",
                "- **Hostel rent:** around Rs. 11,900 to 14,300 per semester",
                "- **Mess fee:** around Rs. 15,200 per semester",
                "- **Security deposit:** around Rs. 5,000 refundable",
                "### Scholarship and Waiver Support",
                "- **PMS:** eligible SC students layi reduced semester fee support",
                "- **TFW:** eligible Punjab resident students nu tuition fee waiver mil sakda hai",
                "- **Sikh Minority support:** kujh internal scholarship options apply ho sakde han",
                "### Note",
                "Exact current semester fee, branch-wise breakup, te latest notice layi thalle ditta official fee resource open karo.",
            ])
        return "\n\n".join([
            "## Fee Structure Overview",
            "At GNDEC, academic fees vary by program and admission category. The official admission portal and fee resource are the best places to confirm the current fee breakup.",
            "### Course Fee Snapshot",
            "- **B.Tech (4 years):** around Rs. 4.49 lakh total",
            "- **B.Tech Lateral Entry (3 years):** around Rs. 3.32 to 3.39 lakh",
            "- **B.Arch (5 years):** around Rs. 4.42 lakh",
            "- **MBA / MCA (2 years):** around Rs. 2.06 lakh",
            "- **BBA / BCA (3 years):** around Rs. 2.09 lakh",
            "- **M.Tech (2 years):** around Rs. 1.62 lakh",
            "### Hostel and Mess",
            "- **Hostel rent:** around Rs. 11,900 to 14,300 per semester",
            "- **Mess fee:** around Rs. 15,200 per semester",
            "- **Security deposit:** around Rs. 5,000 refundable",
            "### Scholarship and Waiver Support",
            "- **PMS:** reduced semester fee support for eligible SC students",
            "- **TFW:** tuition fee waiver support for eligible Punjab resident students",
            "- **Sikh Minority support:** some internal scholarship options may apply",
            "### Note",
            "For the exact current semester fee, branch-wise breakup, and latest official notice, open the fee resource below.",
        ])

    if json_tag == "hostel_fee":
        if is_native_hindi(lang):
            return "\n\n".join([
                "## Hostel and Mess Details",
                "हॉस्टल और मेस से जुड़े प्रश्नों के लिए आधिकारिक GNDEC hostel या fee resource सबसे प्रासंगिक स्रोत है।",
                "### आप क्या देख सकते हैं",
                "- **Hostel fee:** प्रति सेमेस्टर हॉस्टल शुल्क।",
                "- **Mess charges:** मेस शुल्क या hostel-and-mess combined fee details.",
                "- **Latest notice:** updated payment conditions या current fee notice.",
                "### Note",
                "सटीक नवीनतम राशि और वर्तमान notice के लिए नीचे दिया गया आधिकारिक resource सबसे अच्छा रहेगा।",
            ])
        if is_native_punjabi(lang):
            return "\n\n".join([
                "## Hostel and Mess Details",
                "ਹੋਸਟਲ ਅਤੇ ਮੈਸ ਨਾਲ ਸੰਬੰਧਿਤ ਪ੍ਰਸ਼ਨਾਂ ਲਈ ਅਧਿਕਾਰਿਕ GNDEC hostel ਜਾਂ fee resource ਸਭ ਤੋਂ ਪ੍ਰਾਸੰਗਿਕ ਸਰੋਤ ਹੈ।",
                "### ਤੁਸੀਂ ਕੀ ਵੇਖ ਸਕਦੇ ਹੋ",
                "- **Hostel fee:** ਪ੍ਰਤੀ ਸਮੈਸਟਰ ਹੋਸਟਲ ਸ਼ੁਲਕ।",
                "- **Mess charges:** ਮੈਸ ਸ਼ੁਲਕ ਜਾਂ hostel-and-mess combined fee details.",
                "- **Latest notice:** updated payment conditions ਜਾਂ current fee notice.",
                "### Note",
                "ਸਹੀ ਨਵੀਂ ਰਕਮ ਅਤੇ ਮੌਜੂਦਾ notice ਲਈ ਹੇਠਾਂ ਦਿੱਤਾ ਅਧਿਕਾਰਿਕ resource ਸਭ ਤੋਂ ਵਧੀਆ ਰਹੇਗਾ।",
            ])
        if is_hindi(lang):
            return "\n\n".join([
                "## Hostel and Mess Details",
                "Hostel aur mess related queries ke liye official GNDEC hostel or fee resource sabse relevant source hai.",
                "### Aap kya check kar sakte ho",
                "- **Hostel fee:** per semester hostel-related charges.",
                "- **Mess charges:** mess fee ya hostel and mess combined fee details.",
                "- **Latest notice:** updated payment conditions ya current fee notice.",
                "### Note",
                "Exact latest amount aur current notice ke liye neeche diya gaya official resource open karna best rahega.",
            ])
        if is_punjabi(lang):
            return "\n\n".join([
                "## Hostel and Mess Details",
                "Hostel te mess related queries layi official GNDEC hostel jaan fee resource sab ton relevant source hai.",
                "### Tusi ki check kar sakde ho",
                "- **Hostel fee:** per semester hostel related charges.",
                "- **Mess charges:** mess fee jaan hostel and mess combined fee details.",
                "- **Latest notice:** updated payment conditions jaan current fee notice.",
                "### Note",
                "Exact latest amount te current notice layi thalle ditta official resource open karna sab ton vadhiya rahega.",
            ])
        return "\n\n".join([
            "## Hostel and Mess Details",
            "For hostel and mess-related queries, the official GNDEC hostel or fee resource is the most relevant source.",
            "### What You Can Check",
            "- **Hostel fee:** hostel-related charges per semester.",
            "- **Mess charges:** mess fee or combined hostel-and-mess fee details.",
            "- **Latest notice:** updated payment conditions or the current fee notice.",
            "### Note",
            "For the exact latest amount and current notice, the official resource below is the best place to check.",
        ])

    messages = {
        "admission_contact": {
            "en": "I found the official GNDEC admission resource for you. Open the link below to check admission cell details, portal access, and admission-related contact information.",
            "hi": "Maine aapke liye official GNDEC admission resource identify kar diya hai. Neeche diya gaya link open karke aap admission cell details, portal access, aur admission contact information check kar sakte ho.",
            "pa": "Main tuhade layi official GNDEC admission resource identify kar lia hai. Thalle ditta link open karke tusi admission cell details, portal access te admission contact information check kar sakde ho.",
        },
        "admission_documents": {
            "en": "I found the official GNDEC admission resource for document-related guidance. Open the link below to check the document checklist and admission requirements.",
            "hi": "Maine document-related guidance ke liye official GNDEC admission resource identify kar diya hai. Neeche diya gaya link open karke aap document checklist aur admission requirements check kar sakte ho.",
            "pa": "Document related guidance layi main official GNDEC admission resource identify kar lia hai. Thalle ditta link open karke tusi document checklist te admission requirements check kar sakde ho.",
        },
        "management_quota": {
            "en": "I found the official GNDEC admission resource related to admission categories and counseling. Open the link below to check the latest official details.",
            "hi": "Maine admission categories aur counseling ke liye official GNDEC admission resource identify kar diya hai. Neeche diya gaya link open karke aap latest official details check kar sakte ho.",
            "pa": "Admission categories te counseling layi main official GNDEC admission resource identify kar lia hai. Thalle ditta link open karke tusi latest official details check kar sakde ho.",
        },
        "syllabus_query": {
            "en": "I found the relevant official GNDEC academic resource for syllabus-related information. Open the link below to check the latest academic structure or subject details.",
            "hi": "Maine syllabus-related information ke liye relevant official GNDEC academic resource identify kar diya hai. Neeche diya gaya link open karke aap latest academic structure ya subject details check kar sakte ho.",
            "pa": "Syllabus related information layi main relevant official GNDEC academic resource identify kar lia hai. Thalle ditta link open karke tusi latest academic structure jaan subject details check kar sakde ho.",
        },
        "fee_structure": {
            "en": "I found the official GNDEC fee resource for you. Open the link below to check fee structure, fee notices, and related payment details.",
            "hi": "Maine aapke liye official GNDEC fee resource identify kar diya hai. Neeche diya gaya link open karke aap fee structure, fee notices, aur related payment details check kar sakte ho.",
            "pa": "Main tuhade layi official GNDEC fee resource identify kar lia hai. Thalle ditta link open karke tusi fee structure, fee notices te related payment details check kar sakde ho.",
        },
        "fee_deadline": {
            "en": "I found the official GNDEC fee notice resource. Open the link below to check the latest fee deadlines and payment instructions.",
            "hi": "Maine official GNDEC fee notice resource identify kar diya hai. Neeche diya gaya link open karke aap latest fee deadlines aur payment instructions check kar sakte ho.",
            "pa": "Main official GNDEC fee notice resource identify kar lia hai. Thalle ditta link open karke tusi latest fee deadlines te payment instructions check kar sakde ho.",
        },
        "late_fee": {
            "en": "I found the official GNDEC fee notice resource that should help with late fee and payment-condition details. Open the link below for the latest official update.",
            "hi": "Maine official GNDEC fee notice resource identify kar diya hai jo late fee aur payment-condition details ke liye useful rahega. Latest official update ke liye neeche diya gaya link open karo.",
            "pa": "Main official GNDEC fee notice resource identify kar lia hai jo late fee te payment-condition details layi useful rahega. Latest official update layi thalle ditta link open karo.",
        },
        "online_fee_payment": {
            "en": "I found the relevant official GNDEC portal resource for fee payment and student academic access. Open the link below to continue.",
            "hi": "Maine fee payment aur student academic access ke liye relevant official GNDEC portal resource identify kar diya hai. Continue karne ke liye neeche diya gaya link open karo.",
            "pa": "Fee payment te student academic access layi main relevant official GNDEC portal resource identify kar lia hai. Continue karan layi thalle ditta link open karo.",
        },
        "hostel_fee": {
            "en": "I found the relevant official GNDEC resource for hostel and fee-related information. Open the link below to check the latest official details.",
            "hi": "Maine hostel aur fee-related information ke liye relevant official GNDEC resource identify kar diya hai. Latest official details ke liye neeche diya gaya link open karo.",
            "pa": "Hostel te fee-related information layi main relevant official GNDEC resource identify kar lia hai. Latest official details layi thalle ditta link open karo.",
        },
        "hostel_apply": {
            "en": "I found the relevant official GNDEC resource for hostel application support. Open the link below to check the latest hostel-related process details.",
            "hi": "Maine hostel application support ke liye relevant official GNDEC resource identify kar diya hai. Latest hostel-related process details ke liye neeche diya gaya link open karo.",
            "pa": "Hostel application support layi main relevant official GNDEC resource identify kar lia hai. Latest hostel-related process details layi thalle ditta link open karo.",
        },
        "library_access": {
            "en": "I found the official GNDEC library resource for timings, OPAC, e-books, and library access support. Open the link below to check the latest details.",
            "hi": "Maine timings, OPAC, e-books, aur library access support ke liye official GNDEC library resource identify kar diya hai. Latest details ke liye neeche diya gaya link open karo.",
            "pa": "Timings, OPAC, e-books te library access support layi main official GNDEC library resource identify kar lia hai. Latest details layi thalle ditta link open karo.",
        },
        "latest_notices": {
            "en": "I found the official GNDEC website resource for latest notices, circulars, and announcements. Open the link below to check recent updates.",
            "hi": "Maine latest notices, circulars, aur announcements ke liye official GNDEC website resource identify kar diya hai. Recent updates ke liye neeche diya gaya link open karo.",
            "pa": "Latest notices, circulars te announcements layi main official GNDEC website resource identify kar lia hai. Recent updates layi thalle ditta link open karo.",
        },
        "academic_portal": {
            "en": "I found the official GNDEC academic portal resource for login, attendance, marks, and related student services. Open the link below to continue.",
            "hi": "Maine login, attendance, marks, aur related student services ke liye official GNDEC academic portal resource identify kar diya hai. Continue karne ke liye neeche diya gaya link open karo.",
            "pa": "Login, attendance, marks te related student services layi main official GNDEC academic portal resource identify kar lia hai. Continue karan layi thalle ditta link open karo.",
        },
        "department_website": {
            "en": "I found the official GNDEC department website resource for your query. Open the link below to check department-specific information.",
            "hi": "Maine aapke query ke liye official GNDEC department website resource identify kar diya hai. Department-specific information ke liye neeche diya gaya link open karo.",
            "pa": "Tuhade query layi main official GNDEC department website resource identify kar lia hai. Department-specific information layi thalle ditta link open karo.",
        },
        "lab_facilities": {
            "en": "I found the official GNDEC department resource related to labs and infrastructure. Open the link below to check the latest department details.",
            "hi": "Maine labs aur infrastructure se related official GNDEC department resource identify kar diya hai. Latest department details ke liye neeche diya gaya link open karo.",
            "pa": "Labs te infrastructure naal related official GNDEC department resource main identify kar lia hai. Latest department details layi thalle ditta link open karo.",
        },
        "placement_support": {
            "en": "I found the official GNDEC Training and Placement resource for you. Open the link below to check placement drives, eligibility, registration, and internship-related updates.",
            "hi": "Maine aapke liye official GNDEC Training and Placement resource identify kar diya hai. Neeche diya gaya link open karke aap placement drives, eligibility, registration, aur internship-related updates check kar sakte ho.",
            "pa": "Main tuhade layi official GNDEC Training and Placement resource identify kar lia hai. Thalle ditta link open karke tusi placement drives, eligibility, registration te internship-related updates check kar sakde ho.",
        },
        "placement_stats_department": {
            "en": "I found the official GNDEC Training and Placement resource for department placement information. Open the link below to check the latest official placement details.",
            "hi": "Maine department placement information ke liye official GNDEC Training and Placement resource identify kar diya hai. Neeche diya gaya link open karke aap latest official placement details check kar sakte ho.",
            "pa": "Department placement information layi main official GNDEC Training and Placement resource identify kar lia hai. Thalle ditta link open karke tusi latest official placement details check kar sakde ho.",
        },
        "previous_papers": {
            "en": "I identified the relevant official GNDEC academic resource for previous year question papers. Open the link below to check available papers and related academic material.",
            "hi": "Maine previous year question papers ke liye relevant official GNDEC academic resource identify kar diya hai. Neeche diya gaya link open karke aap available papers aur related academic material check kar sakte ho.",
            "pa": "Main previous year question papers layi relevant official GNDEC academic resource identify kar lia hai. Thalle ditta link open karke tusi available papers te related academic material check kar sakde ho.",
        },
        "student_documents": {
            "en": "I found the relevant official GNDEC resource for bonafide certificate, branch change, office contacts, and other document-related support. Open the link below to check the latest instructions.",
            "hi": "Maine bonafide certificate, branch change, office contacts, aur document-related support ke liye relevant official GNDEC resource identify kar diya hai. Neeche diya gaya link open karke aap latest instructions check kar sakte ho.",
            "pa": "Main bonafide certificate, branch change, office contacts te hor document-related support layi relevant official GNDEC resource identify kar lia hai. Thalle ditta link open karke tusi latest instructions check kar sakde ho.",
        },
        "admin_document_approval": {
            "en": "I found the relevant GNDEC administrative resource for digital document approval support. Open the link below to check the latest office guidance, document workflow details, and follow-up route.",
            "hi": "Maine digital document approval support ke liye relevant GNDEC administrative resource identify kar diya hai. Neeche diya gaya link open karke aap latest office guidance, document workflow details, aur follow-up route check kar sakte ho.",
            "pa": "Main digital document approval support layi relevant GNDEC administrative resource identify kar lia hai. Thalle ditta link open karke tusi latest office guidance, document workflow details te follow-up route check kar sakde ho.",
        },
        "administrator_contact": {
            "en": "I found the relevant GNDEC administrative support resource for contacting administrators and office teams. Open the link below to continue with the latest official route.",
            "hi": "Maine administrators aur office teams se contact ke liye relevant GNDEC administrative support resource identify kar diya hai. Neeche diya gaya link open karke aap latest official route follow kar sakte ho.",
            "pa": "Main administrators te office teams naal contact layi relevant GNDEC administrative support resource identify kar lia hai. Thalle ditta link open karke tusi latest official route follow kar sakde ho.",
        },
    }

    bundle = messages.get(json_tag)
    if not bundle:
        return ""
    return bundle.get(lang) or bundle.get("en") or ""


def build_local_paragraph(query: str, context: str, lang: str, parsed=None) -> str:
    query_type = classify_query(query)
    cleaned = clean_context(context, query)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    json_tag = (parsed or {}).get("json_tag")
    query_lower = ((parsed or {}).get("normalized") or query or "").lower()

    if query_type == "hostel" and "mess" in query_lower:
        return build_mess_overview(lang)

    json_tag_answer = build_json_tag_fallback(json_tag, lang) if json_tag else ""
    if json_tag_answer:
        return json_tag_answer

    if json_tag == "principal_info" or "principal" in (query or "").lower():
        principal_info = extract_principal_info(context)
        if principal_info:
            return build_principal_markdown(principal_info, lang)
        if is_native_hindi(lang):
            return "मैंने आधिकारिक GNDEC प्रिंसिपल स्रोत पहचान लिया है। नीचे दिया गया लिंक खोलकर आप प्रिंसिपल की नवीनतम आधिकारिक जानकारी देख सकते हैं।"
        if is_native_punjabi(lang):
            return "ਮੈਂ ਅਧਿਕਾਰਿਕ GNDEC ਪ੍ਰਿੰਸੀਪਲ ਸਰੋਤ ਲੱਭ ਲਿਆ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਖੋਲ੍ਹ ਕੇ ਤੁਸੀਂ ਪ੍ਰਿੰਸੀਪਲ ਦੀ ਨਵੀਂ ਅਧਿਕਾਰਿਕ ਜਾਣਕਾਰੀ ਵੇਖ ਸਕਦੇ ਹੋ।"
        if is_hindi(lang):
            return "Maine official GNDEC principal resource identify kar diya hai. Neeche diya gaya link open karke aap principal ki latest official information check kar sakte ho."
        if is_punjabi(lang):
            return "Main official GNDEC principal resource identify kar lia hai. Thalle ditta link open karke tusi principal di latest official information check kar sakde ho."
        return "I found the official GNDEC principal resource for you. Open the link below to check the latest official principal information."

    if query_type == "hostel":
        contact_terms = ["warden", "caretaker", "contact", "number", "phone", "helpline"]
        girls_terms = ["girls hostel", "girl hostel"]
        boys_terms = ["boys hostel", "boy hostel", "boys hostels", "all boys hostel", "sab boys hostel"]
        is_girls_query = any(term in query_lower for term in girls_terms) or ("girls" in query_lower and "hostel" in query_lower)
        is_boys_query = any(term in query_lower for term in boys_terms) or ("boys" in query_lower and "hostel" in query_lower)

        if "mess" in query_lower:
            return build_mess_overview(lang)

        if is_girls_query and not any(term in query_lower for term in contact_terms):
            return build_girls_hostel_overview(lang)

        if is_boys_query and not any(term in query_lower for term in contact_terms):
            return build_boys_hostel_overview(lang)

    if query_type == "hostel" and any(term in query_lower for term in ["hostel", "hsotel", "warden", "girls hostel", "boys hostel"]):
        hostel_entries = extract_hostel_entries(context)
        if hostel_entries:
            selected_entries = pick_hostel_entries(query, hostel_entries)
            return build_hostel_markdown(selected_entries, lang)

    if query_type == "college":
        if is_native_hindi(lang):
            return "GNDEC लुधियाना एक प्रतिष्ठित इंजीनियरिंग कॉलेज है जहाँ प्रवेश, विभाग, टाइमटेबल, परीक्षा, हॉस्टल, लाइब्रेरी और छात्र सेवाओं से जुड़ी आधिकारिक जानकारी अलग-अलग GNDEC पोर्टलों पर मिलती है। यदि आप किसी विशेष विषय जैसे प्रवेश, फीस, टाइमटेबल या हॉस्टल के बारे में पूछेंगे, तो मैं उसका सीधा आधिकारिक लिंक और स्पष्ट उत्तर दे दूँगा।"
        if is_native_punjabi(lang):
            return "GNDEC ਲੁਧਿਆਣਾ ਇੱਕ ਮਸ਼ਹੂਰ ਇੰਜੀਨੀਅਰਿੰਗ ਕਾਲਜ ਹੈ ਜਿੱਥੇ ਦਾਖਲਾ, ਵਿਭਾਗ, ਟਾਈਮਟੇਬਲ, ਇਮਤਿਹਾਨ, ਹੋਸਟਲ, ਲਾਇਬ੍ਰੇਰੀ ਅਤੇ ਵਿਦਿਆਰਥੀ ਸੇਵਾਵਾਂ ਨਾਲ ਸੰਬੰਧਿਤ ਅਧਿਕਾਰਿਕ ਜਾਣਕਾਰੀ ਵੱਖ-ਵੱਖ GNDEC ਪੋਰਟਲਾਂ 'ਤੇ ਮਿਲਦੀ ਹੈ। ਜੇ ਤੁਸੀਂ ਕਿਸੇ ਖ਼ਾਸ ਵਿਸ਼ੇ ਜਿਵੇਂ ਦਾਖਲਾ, ਫੀਸ, ਟਾਈਮਟੇਬਲ ਜਾਂ ਹੋਸਟਲ ਬਾਰੇ ਪੁੱਛੋਗੇ, ਤਾਂ ਮੈਂ ਉਸਦਾ ਸਿੱਧਾ ਅਧਿਕਾਰਿਕ ਲਿੰਕ ਅਤੇ ਸਾਫ਼ ਜਵਾਬ ਦੇ ਦਿਆਂਗਾ।"
        if is_hindi(lang):
            return "GNDEC Ludhiana ek reputed engineering college hai jahan admissions, departments, timetables, exams, hostel, library aur student services se related official information alag-alag GNDEC portals par milti hai. Agar aap kisi specific cheez jaise admission, fee, timetable ya hostel ke baare mein puchoge, main uska direct official link aur clear answer de dunga."
        if is_punjabi(lang):
            return "GNDEC Ludhiana ik well-known engineering college hai jithe admissions, departments, timetables, exams, hostel, library te hor student services di official information GNDEC de alag-alag portals te mil di hai. Je tusi kise specific cheez jiven timetable, admission, fee jaan hostel bare puchho, main tuhanu sidha official link de naal clear answer dunga."
        return "GNDEC Ludhiana is a well-known engineering college, and its official portals cover admissions, departments, timetables, exams, hostel facilities, library services, and other student resources. If you ask about any specific topic like admission, fees, hostel, or timetable, I can give you a clearer answer with the direct official link."

    if query_type == "admission":
        if is_native_hindi(lang):
            return "GNDEC से जुड़े प्रवेश संबंधी प्रश्नों के लिए आधिकारिक एडमिशन पोर्टल सबसे उपयोगी स्रोत है। नीचे दिया गया लिंक खोलकर आप आवेदन प्रक्रिया, पात्रता, आवश्यक दस्तावेज़, काउंसलिंग और B.Tech प्रवेश विवरण सीधे देख सकते हैं।"
        if is_native_punjabi(lang):
            return "GNDEC ਨਾਲ ਸੰਬੰਧਿਤ ਦਾਖਲਾ ਪ੍ਰਸ਼ਨਾਂ ਲਈ ਅਧਿਕਾਰਿਕ ਐਡਮਿਸ਼ਨ ਪੋਰਟਲ ਸਭ ਤੋਂ ਲਾਭਦਾਇਕ ਸਰੋਤ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਖੋਲ੍ਹ ਕੇ ਤੁਸੀਂ ਅਰਜ਼ੀ ਪ੍ਰਕਿਰਿਆ, ਯੋਗਤਾ, ਲੋੜੀਂਦੇ ਦਸਤਾਵੇਜ਼, ਕਾਊਂਸਲਿੰਗ ਅਤੇ B.Tech ਦਾਖਲਾ ਵੇਰਵਾ ਸਿੱਧਾ ਵੇਖ ਸਕਦੇ ਹੋ।"
        if is_hindi(lang):
            return "GNDEC ke admission-related queries ke liye sabse useful official source admission portal hai. Neeche diya gaya link open karke aap application process, eligibility, required documents, counselling, aur B.Tech admission details directly check kar sakte ho."
        if is_punjabi(lang):
            return "GNDEC admission related queries layi sab ton useful official source admission portal hai. Thalle ditta link open karke tusi application process, eligibility, required documents, counselling te B.Tech admission details sidhe check kar sakde ho."
        return "For GNDEC admission-related queries, the official admission portal is the most useful source. You can open the link below to check the application process, eligibility, required documents, counselling, and B.Tech admission details directly."

    if query_type == "exam":
        if is_native_hindi(lang):
            return "परीक्षा से जुड़े प्रश्न जैसे डेट शीट, एडमिट कार्ड, पुनर्मूल्यांकन, मेकअप परीक्षा, बैकलॉग फॉर्म या आंतरिक अंक के लिए आधिकारिक परीक्षा पोर्टल सबसे उपयुक्त स्रोत है। नीचे दिया गया लिंक खोलकर नवीनतम परीक्षा नोटिस और छात्र परीक्षा सेवाएँ देख सकते हैं।"
        if is_native_punjabi(lang):
            return "ਪਰੀਖਿਆ ਨਾਲ ਸੰਬੰਧਿਤ ਪ੍ਰਸ਼ਨ ਜਿਵੇਂ ਡੇਟ ਸ਼ੀਟ, ਐਡਮਿਟ ਕਾਰਡ, ਰੀ-ਇਵੈਲੂਏਸ਼ਨ, ਮੇਕਅਪ ਇਮਤਿਹਾਨ, ਬੈਕਲਾਗ ਫਾਰਮ ਜਾਂ ਅੰਦਰੂਨੀ ਅੰਕਾਂ ਲਈ ਅਧਿਕਾਰਿਕ ਇਮਤਿਹਾਨ ਪੋਰਟਲ ਸਭ ਤੋਂ ਉਚਿਤ ਸਰੋਤ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਖੋਲ੍ਹ ਕੇ ਨਵੀਂ ਇਮਤਿਹਾਨ ਨੋਟਿਸਾਂ ਅਤੇ ਵਿਦਿਆਰਥੀ ਸੇਵਾਵਾਂ ਵੇਖ ਸਕਦੇ ਹੋ।"
        if is_hindi(lang):
            return "Exam-related queries jaise date sheet, admit card, re-evaluation, makeup exam, backlog form, ya internal marks ke liye official exam portal sabse relevant source hai. Neeche diya gaya link open karke latest exam notices aur student exam services check kar sakte ho."
        if is_punjabi(lang):
            return "Exam related queries jiven date sheet, admit card, re-evaluation, makeup exam, backlog form jaan internal marks layi official exam portal sab ton relevant source hai. Thalle ditta link open karke latest exam notices te student exam services check kar sakde ho."
        return "For exam-related queries such as date sheet, admit card, re-evaluation, makeup exam, backlog form, or internal marks, the official exam portal is the most relevant source. Open the link below to check the latest exam notices and student exam services."

    if query_type == "calendar":
        if "no official academic calendar for" in (context or "").lower():
            year_match = re.search(r"Requested academic calendar year:\s*(20\d{2})", context or "", re.IGNORECASE)
            latest_match = re.search(r"Latest listed calendar found:\s*(.+?)\.", context or "", re.IGNORECASE)
            year = year_match.group(1) if year_match else "that year"
            latest = latest_match.group(1) if latest_match else "the latest listed academic calendar"
            if is_native_hindi(lang):
                return f"GNDEC की आधिकारिक साइट पर {year} का अकादमिक कैलेंडर अभी सूचीबद्ध नहीं मिला। जो नवीनतम आधिकारिक अकादमिक कैलेंडर स्रोत मिला है वह {latest} है, और नीचे दिया गया लिंक उसी आधिकारिक कैलेंडर स्रोत को खोलेगा।"
            if is_native_punjabi(lang):
                return f"GNDEC ਦੀ ਅਧਿਕਾਰਿਕ ਸਾਈਟ 'ਤੇ {year} ਦਾ ਅਕਾਦਮਿਕ ਕੈਲੰਡਰ ਅਜੇ ਸੂਚੀਬੱਧ ਨਹੀਂ ਮਿਲਿਆ। ਜੇਹੜਾ ਸਭ ਤੋਂ ਨਵਾਂ ਅਧਿਕਾਰਿਕ ਅਕਾਦਮਿਕ ਕੈਲੰਡਰ ਸਰੋਤ ਮਿਲਿਆ ਹੈ, ਉਹ {latest} ਹੈ, ਅਤੇ ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਉਸੇ ਸਰੋਤ ਨੂੰ ਖੋਲ੍ਹੇਗਾ।"
            if is_hindi(lang):
                return f"GNDEC ki official site par {year} ka academic calendar abhi listed nahi mila. Jo latest official academic calendar resource mila hai woh {latest} hai, aur neeche diya gaya link usi official calendar resource ko open karega."
            if is_punjabi(lang):
                return f"GNDEC di official site te {year} da academic calendar aje listed nahi milya. Jeda latest official academic calendar resource milya hai oh {latest} hai, te thalle ditta link usi official calendar resource nu open karega."
            return f"The official GNDEC site does not currently list an academic calendar for {year}. The latest official academic calendar resource I found is {latest}, and the link below opens that official calendar resource."
        if is_native_hindi(lang):
            return "अकादमिक कैलेंडर के लिए आधिकारिक GNDEC अकादमिक कैलेंडर पेज सबसे विश्वसनीय स्रोत है। नीचे दिया गया लिंक खोलकर आप सत्र कार्यक्रम, सेमेस्टर टाइमलाइन, कक्षाओं की शुरुआत की तारीखें और अन्य महत्वपूर्ण शैक्षणिक तिथियाँ देख सकते हैं।"
        if is_native_punjabi(lang):
            return "ਅਕਾਦਮਿਕ ਕੈਲੰਡਰ ਲਈ ਅਧਿਕਾਰਿਕ GNDEC ਅਕਾਦਮਿਕ ਕੈਲੰਡਰ ਪੰਨਾ ਸਭ ਤੋਂ ਭਰੋਸੇਯੋਗ ਸਰੋਤ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਖੋਲ੍ਹ ਕੇ ਤੁਸੀਂ ਸੈਸ਼ਨ ਸ਼ਡਿਊਲ, ਸਮੈਸਟਰ ਟਾਈਮਲਾਈਨ, ਕਲਾਸਾਂ ਦੀ ਸ਼ੁਰੂਆਤ ਦੀਆਂ ਤਾਰੀਖਾਂ ਅਤੇ ਹੋਰ ਮਹੱਤਵਪੂਰਨ ਅਕਾਦਮਿਕ ਮਿਤੀਆਂ ਵੇਖ ਸਕਦੇ ਹੋ।"
        if is_hindi(lang):
            return "Academic calendar ke liye official GNDEC academic calendar page sabse reliable source hai. Neeche diya gaya link open karke aap session schedule, semester timeline, class start dates, aur important academic dates check kar sakte ho."
        if is_punjabi(lang):
            return "Academic calendar layi official GNDEC academic calendar page sab ton reliable source hai. Thalle ditta link open karke tusi session schedule, semester timeline, class start dates te hor important academic dates check kar sakde ho."
        return "For the academic calendar, the official GNDEC academic calendar page is the most reliable source. You can open the link below to check the session schedule, semester timeline, class start dates, and other important academic dates."

    if query_type == "holiday":
        if is_native_hindi(lang):
            return "छुट्टियों की सूची के लिए मैंने आधिकारिक GNDEC अवकाश स्रोत पहचान लिया है। नीचे दिया गया लिंक खोलकर आप नवीनतम अवकाश सूची और अधिसूचित बंद दिनों की जानकारी सीधे देख सकते हैं।"
        if is_native_punjabi(lang):
            return "ਛੁੱਟੀਆਂ ਦੀ ਸੂਚੀ ਲਈ ਮੈਂ ਅਧਿਕਾਰਿਕ GNDEC ਛੁੱਟੀ ਸਰੋਤ ਲੱਭ ਲਿਆ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਖੋਲ੍ਹ ਕੇ ਤੁਸੀਂ ਨਵੀਂ ਛੁੱਟੀਆਂ ਦੀ ਸੂਚੀ ਅਤੇ ਘੋਸ਼ਿਤ ਬੰਦ ਦਿਨਾਂ ਦੀ ਜਾਣਕਾਰੀ ਸਿੱਧੀ ਵੇਖ ਸਕਦੇ ਹੋ।"
        if is_hindi(lang):
            return "Holiday list ke liye maine official GNDEC holidays resource identify kar diya hai. Neeche diya gaya link open karke aap latest holiday list aur notified closed days directly dekh sakte ho."
        if is_punjabi(lang):
            return "Holiday list layi main official GNDEC holidays resource identify kar lia hai. Thalle ditta link open karke tusi latest holiday list te notified closed days sidhe dekh sakde ho."
        return "I found the official GNDEC holidays resource for you. Open the link below to check the latest holiday list and notified closed days directly."

    if query_type == "portal":
        if is_native_hindi(lang):
            return "GNDEC अकादमिक पोर्टल उपस्थिति, अंक और कुछ छात्र शैक्षणिक सेवाओं के लिए उपयोगी है। नीचे दिया गया आधिकारिक पोर्टल लिंक खोलकर आप लॉगिन या संबंधित शैक्षणिक सेवाएँ देख सकते हैं।"
        if is_native_punjabi(lang):
            return "GNDEC ਅਕਾਦਮਿਕ ਪੋਰਟਲ ਹਾਜ਼ਰੀ, ਅੰਕਾਂ ਅਤੇ ਕੁਝ ਵਿਦਿਆਰਥੀ ਅਕਾਦਮਿਕ ਸੇਵਾਵਾਂ ਲਈ ਲਾਭਦਾਇਕ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਅਧਿਕਾਰਿਕ ਪੋਰਟਲ ਲਿੰਕ ਖੋਲ੍ਹ ਕੇ ਤੁਸੀਂ ਲੌਗਿਨ ਜਾਂ ਸੰਬੰਧਿਤ ਅਕਾਦਮਿਕ ਸੇਵਾਵਾਂ ਵੇਖ ਸਕਦੇ ਹੋ।"
        if is_hindi(lang):
            return "GNDEC academic portal attendance, marks, aur kuch student academic services ke liye useful hota hai. Neeche diya gaya official portal link open karke login ya related academic access check kar sakte ho."
        if is_punjabi(lang):
            return "GNDEC academic portal attendance, marks te kujh student academic services layi useful hunda hai. Thalle ditta official portal link open karke tusi login jaan related academic access check kar sakde ho."
        return "The GNDEC academic portal is useful for attendance, marks, and some student academic services. You can open the official portal link below to check login access or related academic services."

    if query_type == "hostel" and any(term in query_lower for term in ["warden", "contact", "helpline", "boys hostel", "girls hostel"]):
        if is_native_hindi(lang):
            return "हॉस्टल वार्डन और हॉस्टल संपर्क विवरण के लिए मैंने आधिकारिक GNDEC हॉस्टल हेल्प स्रोत चुना है। नीचे दिया गया लिंक खोलकर आप बॉयज़ हॉस्टल, गर्ल्स हॉस्टल या हॉस्टल हेल्पलाइन विवरण देख सकते हैं।"
        if is_native_punjabi(lang):
            return "ਹੋਸਟਲ ਵਾਰਡਨ ਅਤੇ ਹੋਸਟਲ ਸੰਪਰਕ ਵੇਰਵਿਆਂ ਲਈ ਮੈਂ ਅਧਿਕਾਰਿਕ GNDEC ਹੋਸਟਲ ਹੈਲਪ ਸਰੋਤ ਚੁਣਿਆ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਖੋਲ੍ਹ ਕੇ ਤੁਸੀਂ ਬੋਇਜ਼ ਹੋਸਟਲ, ਗਰਲਜ਼ ਹੋਸਟਲ ਜਾਂ ਹੋਸਟਲ ਹੈਲਪਲਾਈਨ ਵੇਰਵਾ ਵੇਖ ਸਕਦੇ ਹੋ।"
        if is_hindi(lang):
            return "Hostel warden aur hostel contact details ke liye maine official GNDEC hostel help resource choose kiya hai. Neeche diya gaya link open karke aap boys hostel, girls hostel, ya hostel helpline details check kar sakte ho."
        if is_punjabi(lang):
            return "Hostel warden te hostel contact details layi main official GNDEC hostel help resource choose kita hai. Thalle ditta link open karke tusi boys hostel, girls hostel jaan hostel helpline details check kar sakde ho."
        return "For hostel warden and hostel contact details, I selected the official GNDEC hostel help resource. You can open the link below to check boys hostel, girls hostel, or hostel helpline details."

    if query_type == "hostel" and "mess" in query_lower:
        if is_native_hindi(lang):
            return "मेस शुल्क या हॉस्टल मेस से जुड़ी जानकारी के लिए मैंने प्रासंगिक आधिकारिक GNDEC हॉस्टल या फीस स्रोत चुना है। नीचे दिया गया लिंक खोलकर आप नवीनतम आधिकारिक मेस और हॉस्टल शुल्क जानकारी देख सकते हैं।"
        if is_native_punjabi(lang):
            return "ਮੈਸ ਸ਼ੁਲਕ ਜਾਂ ਹੋਸਟਲ ਮੈਸ ਨਾਲ ਸੰਬੰਧਿਤ ਜਾਣਕਾਰੀ ਲਈ ਮੈਂ ਪ੍ਰਾਸੰਗਿਕ ਅਧਿਕਾਰਿਕ GNDEC ਹੋਸਟਲ ਜਾਂ ਫੀਸ ਸਰੋਤ ਚੁਣਿਆ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਖੋਲ੍ਹ ਕੇ ਤੁਸੀਂ ਨਵੀਂ ਅਧਿਕਾਰਿਕ ਮੈਸ ਅਤੇ ਹੋਸਟਲ ਫੀਸ ਜਾਣਕਾਰੀ ਵੇਖ ਸਕਦੇ ਹੋ।"
        if is_hindi(lang):
            return "Mess charges ya hostel mess related details ke liye maine relevant official GNDEC hostel or fee resource choose kiya hai. Neeche diya gaya link open karke aap latest official mess aur hostel fee information check kar sakte ho."
        if is_punjabi(lang):
            return "Mess charges jaan hostel mess related details layi main relevant official GNDEC hostel jaan fee resource choose kita hai. Thalle ditta link open karke tusi latest official mess te hostel fee information check kar sakde ho."
        return "For mess charges or hostel mess-related details, I selected the relevant official GNDEC hostel or fee resource. Open the link below to check the latest official mess and hostel fee information."

    if query_type == "department" and any(term in query.lower() for term in ["course", "courses", "program", "programs", "btech", "b.tech", "branch", "branches"]):
        if is_native_hindi(lang):
            return "B.Tech पाठ्यक्रमों और शैक्षणिक कार्यक्रमों के लिए आधिकारिक GNDEC academics programs page सबसे उपयोगी स्रोत है। नीचे दिया गया लिंक खोलकर आप उपलब्ध पाठ्यक्रम, विभाग और कार्यक्रम संरचना देख सकते हैं।"
        if is_native_punjabi(lang):
            return "B.Tech ਕੋਰਸਾਂ ਅਤੇ ਅਕਾਦਮਿਕ ਪ੍ਰੋਗਰਾਮਾਂ ਲਈ ਅਧਿਕਾਰਿਕ GNDEC academics programs page ਸਭ ਤੋਂ ਲਾਭਦਾਇਕ ਸਰੋਤ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਖੋਲ੍ਹ ਕੇ ਤੁਸੀਂ ਉਪਲਬਧ ਕੋਰਸ, ਵਿਭਾਗ ਅਤੇ ਪ੍ਰੋਗਰਾਮ ਬਣਤਰ ਵੇਖ ਸਕਦੇ ਹੋ।"
        if is_hindi(lang):
            return "B.Tech courses aur academic programs ke liye official GNDEC academics programs page sabse useful hai. Neeche diya gaya link open karke aap available courses, departments, aur program structure check kar sakte ho."
        if is_punjabi(lang):
            return "B.Tech courses te academic programs layi official GNDEC academics programs page sab ton useful hai. Thalle ditta link open karke tusi available courses, departments te program structure check kar sakde ho."
        return "For B.Tech courses and academic programs, the official GNDEC academics programs page is the most useful source. Open the link below to check available courses, departments, and the program structure."

    if query_type == "timetable":
        timetable_answer = build_timetable_fallback(context, lang)
        if timetable_answer:
            return timetable_answer

    if query_type == "department" and any(term in query.lower() for term in ["hod", "head of department", "department head"]):
        hod_info = extract_hod_info(context)
        if hod_info:
            return build_hod_markdown(hod_info, lang, department_label=infer_department_label(query))

    if query_type == "department" and any(term in query.lower() for term in ["faculty", "staff"]):
        faculty_entries = extract_faculty_entries(context)
        if faculty_entries:
            department_label = infer_department_label(query)
            return build_faculty_markdown(faculty_entries, lang, department_label=department_label)

    if json_tag in ["placement_support", "placement_stats_department"]:
        if is_native_hindi(lang):
            return "प्लेसमेंट और इंटर्नशिप से जुड़े प्रश्नों के लिए आधिकारिक GNDEC Training and Placement resource सबसे उपयोगी स्रोत है। नीचे दिया गया लिंक खोलकर आप प्लेसमेंट ड्राइव, पात्रता, पंजीकरण और इंटर्नशिप अपडेट देख सकते हैं।"
        if is_native_punjabi(lang):
            return "ਪਲੇਸਮੈਂਟ ਅਤੇ ਇੰਟਰਨਸ਼ਿਪ ਨਾਲ ਸੰਬੰਧਿਤ ਪ੍ਰਸ਼ਨਾਂ ਲਈ ਅਧਿਕਾਰਿਕ GNDEC Training and Placement resource ਸਭ ਤੋਂ ਲਾਭਦਾਇਕ ਸਰੋਤ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਖੋਲ੍ਹ ਕੇ ਤੁਸੀਂ ਪਲੇਸਮੈਂਟ ਡਰਾਈਵ, ਯੋਗਤਾ, ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਅਤੇ ਇੰਟਰਨਸ਼ਿਪ ਅਪਡੇਟ ਵੇਖ ਸਕਦੇ ਹੋ।"
        if is_hindi(lang):
            return "Placement aur internship related queries ke liye official GNDEC Training and Placement resource sabse useful source hai. Neeche diya gaya link open karke aap placement drives, eligibility, registration, aur internship updates check kar sakte ho."
        if is_punjabi(lang):
            return "Placement te internship related queries layi official GNDEC Training and Placement resource sab ton useful source hai. Thalle ditta link open karke tusi placement drives, eligibility, registration te internship updates check kar sakde ho."
        return "For placement and internship queries, the official GNDEC Training and Placement resource is the most useful source. Open the link below to check placement drives, eligibility, registration, and internship updates."

    if json_tag == "previous_papers":
        if is_native_hindi(lang):
            return "पिछले वर्षों के प्रश्नपत्रों के लिए मैंने प्रासंगिक आधिकारिक शैक्षणिक स्रोत पहचान लिया है। नीचे दिया गया लिंक खोलकर आप उपलब्ध प्रश्नपत्र और संबंधित शैक्षणिक सामग्री खोज सकते हैं।"
        if is_native_punjabi(lang):
            return "ਪਿਛਲੇ ਸਾਲਾਂ ਦੇ ਪ੍ਰਸ਼ਨ ਪੱਤਰਾਂ ਲਈ ਮੈਂ ਪ੍ਰਾਸੰਗਿਕ ਅਧਿਕਾਰਿਕ ਅਕਾਦਮਿਕ ਸਰੋਤ ਲੱਭ ਲਿਆ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਖੋਲ੍ਹ ਕੇ ਤੁਸੀਂ ਉਪਲਬਧ ਪ੍ਰਸ਼ਨ ਪੱਤਰ ਅਤੇ ਸੰਬੰਧਿਤ ਅਕਾਦਮਿਕ ਸਮੱਗਰੀ ਖੋਜ ਸਕਦੇ ਹੋ।"
        if is_hindi(lang):
            return "Previous year question papers ke liye maine relevant official academic resource identify kar diya hai. Neeche diya gaya link open karke aap available papers aur related academic material search kar sakte ho."
        if is_punjabi(lang):
            return "Previous year question papers layi main relevant official academic resource identify kar lia hai. Thalle ditta link open karke tusi available papers te related academic material search kar sakde ho."
        return "I identified the relevant official academic resource for previous year question papers. Open the link below to search available papers and related academic material."

    if json_tag == "student_documents":
        if is_native_hindi(lang):
            return "बोनाफाइड प्रमाणपत्र, शाखा परिवर्तन, कार्यालय संपर्क या दस्तावेज़ संबंधी प्रश्नों के लिए आधिकारिक GNDEC स्रोत और नोटिस सबसे उपयोगी रहेंगे। नीचे दिया गया लिंक खोलकर आप नवीनतम निर्देश और प्रशासनिक सहायता विवरण देख सकते हैं।"
        if is_native_punjabi(lang):
            return "ਬੋਨਾਫਾਈਡ ਸਰਟੀਫਿਕੇਟ, ਸ਼ਾਖਾ ਬਦਲਾਅ, ਦਫ਼ਤਰੀ ਸੰਪਰਕ ਜਾਂ ਦਸਤਾਵੇਜ਼ ਸੰਬੰਧੀ ਪ੍ਰਸ਼ਨਾਂ ਲਈ ਅਧਿਕਾਰਿਕ GNDEC ਸਰੋਤ ਅਤੇ ਨੋਟਿਸ ਸਭ ਤੋਂ ਲਾਭਦਾਇਕ ਰਹਿਣਗੇ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਖੋਲ੍ਹ ਕੇ ਤੁਸੀਂ ਨਵੇਂ ਨਿਰਦੇਸ਼ ਅਤੇ ਪ੍ਰਸ਼ਾਸਕੀ ਸਹਾਇਤਾ ਵੇਰਵੇ ਵੇਖ ਸਕਦੇ ਹੋ।"
        if is_hindi(lang):
            return "Bonafide certificate, branch change, office contacts, ya document-related queries ke liye official GNDEC resource aur notices sabse useful rahenge. Neeche diya gaya link open karke aap latest instructions aur administrative support details check kar sakte ho."
        if is_punjabi(lang):
            return "Bonafide certificate, branch change, office contacts jaan document related queries layi official GNDEC resource te notices sab ton useful rahenge. Thalle ditta link open karke tusi latest instructions te administrative support details check kar sakde ho."
        return "For bonafide certificate, branch change, office contacts, or document-related queries, the official GNDEC resource and notices are the best place to start. You can open the link below to check the latest instructions and administrative support details."

    if cleaned:
        snippet = cleaned[:600].rstrip(" ,;:")
        if is_native_hindi(lang):
            return f"GNDEC की आधिकारिक जानकारी के अनुसार, {snippet}. यदि आप और सटीक विवरण देखना चाहते हैं, तो नीचे दिया गया आधिकारिक लिंक सबसे उपयुक्त रहेगा।"
        if is_native_punjabi(lang):
            return f"GNDEC ਦੀ ਅਧਿਕਾਰਿਕ ਜਾਣਕਾਰੀ ਮੁਤਾਬਕ, {snippet}. ਜੇ ਤੁਸੀਂ ਹੋਰ ਸਟੀਕ ਵੇਰਵਾ ਵੇਖਣਾ ਚਾਹੁੰਦੇ ਹੋ, ਤਾਂ ਹੇਠਾਂ ਦਿੱਤਾ ਅਧਿਕਾਰਿਕ ਲਿੰਕ ਸਭ ਤੋਂ ਵਧੀਆ ਰਹੇਗਾ।"
        if is_hindi(lang):
            return f"GNDEC ke official information ke hisaab se, {snippet}. Agar aap aur exact detail dekhna chaho, neeche diya gaya official link best rahega."
        if is_punjabi(lang):
            return f"GNDEC di official information de mutabik, {snippet}. Je tusi hor exact detail dekhni hove, thalle ditta official link sab ton vadhiya rahega."
        return f"Based on GNDEC's official information, {snippet}. If you want the exact latest details, the official link below is the best place to check."

    if is_native_hindi(lang):
        return "मैंने आपके प्रश्न के लिए प्रासंगिक GNDEC आधिकारिक स्रोत पहचान लिया है। नीचे दिया गया लिंक खोलकर आप नवीनतम और पूर्ण विवरण सीधे देख सकते हैं।"
    if is_native_punjabi(lang):
        return "ਮੈਂ ਤੁਹਾਡੇ ਪ੍ਰਸ਼ਨ ਲਈ ਪ੍ਰਾਸੰਗਿਕ GNDEC ਅਧਿਕਾਰਿਕ ਸਰੋਤ ਲੱਭ ਲਿਆ ਹੈ। ਹੇਠਾਂ ਦਿੱਤਾ ਲਿੰਕ ਖੋਲ੍ਹ ਕੇ ਤੁਸੀਂ ਨਵੀਂ ਅਤੇ ਪੂਰੀ ਜਾਣਕਾਰੀ ਸਿੱਧੀ ਵੇਖ ਸਕਦੇ ਹੋ।"
    if is_hindi(lang):
        return "Maine aapke question ke liye relevant GNDEC official resource identify kar diya hai. Neeche diya gaya link open karke aap latest aur complete details directly dekh sakte ho."
    if is_punjabi(lang):
        return "Main tuhade question layi relevant GNDEC official resource labh lia hai. Thalle ditta link open karke tusi latest te complete details sidha dekh sakde ho."
    return "I found the most relevant official GNDEC resource for your question. You can open the link below to check the latest and complete details directly."


def ask_gemini(query: str, context: str, lang: str):
    if not genai or not GEMINI_API_KEY:
        print("Gemini SDK or API key missing")
        return None

    context = clean_context(context, query)
    if not context.strip():
        print("Context empty after cleaning")
        return None

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        lang_instruction = {
            "en": "Answer in English.",
            "hi": "Answer in natural Hinglish or simple Roman Hindi.",
            "hi_native": "Answer in proper Hindi using Devanagari script.",
            "pa": "Answer in natural Roman Punjabi when appropriate.",
            "pa_native": "Answer in proper Punjabi using Gurmukhi script.",
        }.get(lang, "Answer in English.")

        prompt = f"""
You are GNDEC Helpdesk AI.

User question:
{query}

Official context:
{context}

Instructions:
- {lang_instruction}
- Understand the user's exact question first.
- Use only the official context provided.
- Keep the answer student-friendly and conversational.
- Prefer a Google AI style response: one short summary sentence, then 1 or 2 compact markdown headings with bullet points when useful.
- Use markdown `##` and `###` headings plus `-` bullets when the answer contains contact details, timetable details, faculty details, or steps.
- If the question is simple, a short clean paragraph is also fine.
- If the user asked for a timetable, mention that the linked official resource is the direct or closest class timetable page.
- If details are incomplete, clearly say that the official link below has the latest complete information.
- Do not invent facts.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        text = getattr(response, "text", None)
        if text and text.strip():
            lines = [line.rstrip() for line in text.strip().splitlines()]
            return "\n".join(lines).strip()

        print("Empty Gemini response")
        return None
    except Exception as e:
        print("Gemini error:", e)
        return None


def generate_response(parsed):
    query = parsed.get("original") or parsed.get("raw", "").strip()
    lang = parsed.get("response_language") or parsed.get("language", "en")

    try:
        if is_greeting(query):
            return {
                "reply": greeting(lang),
                "type": "text",
                "meta": None,
            }

        if is_how_are_you(query):
            return {
                "reply": how_are_you_reply(lang),
                "type": "text",
                "meta": None,
            }

        if is_thanks(query):
            return {
                "reply": thanks_reply(lang),
                "type": "text",
                "meta": None,
            }

        if is_goodbye(query):
            return {
                "reply": goodbye(lang),
                "type": "text",
                "meta": None,
            }

        resolved = resolve_official_query(parsed)
        link = resolved.get("link")
        context = resolved.get("context", "")
        exact = resolved.get("exact", "")
        auto_open = resolved.get("auto_open", False)

        if link and ".pdf" in link.lower():
            pdf_text = extract_pdf_text(link)
            if pdf_text.strip():
                context = (context + "\n\n" + pdf_text).strip()

        if exact.strip():
            context = (exact + "\n\n" + context).strip()

        print("QUERY:", safe_debug_text(query))
        print("CONTEXT LENGTH:", len(context))
        print("CONTEXT PREVIEW:", safe_debug_text(context[:800]))

        ai_answer = ask_gemini(query, context, lang)
        if not ai_answer:
            ai_answer = build_local_paragraph(query, context, lang, parsed=parsed)

        return {
            "reply": ai_answer,
            "type": "text",
            "meta": build_meta(link, auto_open=auto_open),
        }
    except Exception as e:
        print("generate_response error:", e)
        return {
            "reply": "Something went wrong. Please try again.",
            "type": "text",
            "meta": None,
        }
