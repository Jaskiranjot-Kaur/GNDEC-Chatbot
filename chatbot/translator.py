import re

ROMAN_HINDI_MARKERS = {
    "kya", "kaise", "kaun", "kahan", "kab", "kyu", "kyon", "kitna", "kitni",
    "batao", "batado", "btao", "dikhao", "dikha", "dikha do", "dikado",
    "chahiye", "chaiye", "hai", "hain", "mera", "meri", "mere", "mujhe",
    "mujhko", "samjhao", "samjha", "kholna", "kripya", "kripiya",
    "pleaseji", "karna", "karni", "milta", "milti", "hoga", "hogi", "kon",
    "konsa", "kaunsa", "kabse", "nahi", "kya hai", "bata do", "dikha do",
}

ROMAN_PUNJABI_MARKERS = {
    "kiven", "kidda", "kiwe", "ki haal", "haal chaal", "tusi", "tuhada",
    "tuhadi", "tuhanu", "sanu", "dasso", "daso", "daso ji", "kholo",
    "vekhao", "vekhna", "vekh", "baare", "bare", "veerji", "hanji", "layi",
    "lai", "vich", "kithon", "keda", "kehda", "kehri", "kehda hai", "kadon",
    "pata", "milde", "rab rakha", "gal", "da timetable", "de bare",
    "di details", "da result", "di fee", "chahidi", "chahida",
}

HINGLISH_HINTS = {
    "admission", "fees", "hostel", "timetable", "result", "notice", "portal",
    "department", "faculty", "hod", "principal", "calendar", "holiday",
    "exam", "examinations", "makeup", "revaluation", "syllabus", "attendance",
}

MULTILINGUAL_REPLACEMENTS = [
    (r"\btime[\s-]*table\b", " timetable "),
    (r"\bclass[\s-]*routine\b", " timetable "),
    (r"\bclass[\s-]*schedule\b", " timetable "),
    (r"\bperiod[\s-]*table\b", " timetable "),
    (r"\bhsotel\b", " hostel "),
    (r"\bhostelz\b", " hostel "),
    (r"\bhostal\b", " hostel "),
    (r"\bhostle\b", " hostel "),
    (r"\bfeez\b", " fees "),
    (r"\bfee[\s-]*structure\b", " fees "),
    (r"\bexamz\b", " exams "),
    (r"\bexaminations\b", " exam "),
    (r"\bmake[\s-]*up\b", " makeup "),
    (r"\bprincipal\s+name\b", " principal info "),
    (r"\bteacher[\s-]*timetable\b", " teacher timetable "),
    (r"\bfaculty[\s-]*timetable\b", " teacher timetable "),
    (r"\bteachers[\s-]*schedule\b", " teacher timetable "),
    (r"\bmadam[\s-]*timetable\b", " teacher timetable "),
    (r"\bsir[\s-]*timetable\b", " teacher timetable "),
    (r"\bhod\s+kon\b", " hod kaun "),
    (r"\bkon\b", " kaun "),
    (r"\bkonsa\b", " kaunsa "),
    (r"\bbtao\b", " batao "),
    (r"\bbtado\b", " bata do "),
    (r"\bdikado\b", " dikha do "),
    (r"\bdikhaado\b", " dikha do "),
    (r"\bplz\b", " please "),
    (r"\bpls\b", " please "),
    (r"\bdept\b", " department "),
    (r"\buni\b", " university "),
    (r"\bcafeteria\b", " canteen "),
    (r"\bcanteen\b", " canteen "),
    (r"\bopen[\s-]*air[\s-]*theatre\b", " oat "),
    (r"\bopen[\s-]*air[\s-]*theater\b", " oat "),
    (r"\boat\b", " oat "),
    (r"\bsre\b", " sre exam "),
    (r"\bsikh[\s-]*religion[\s-]*exam(?:ination)?\b", " sre exam "),
    (r"\bsports[\s-]*department\b", " sports department "),
    (r"\bsports[\s-]*complex\b", " sports department "),
    (r"\bdocuments?\b", " documents "),
    (r"\bdoc(?:ument)?s?\b", " documents "),
    (r"\bsamay\s+saarini\b", " timetable "),
    (r"समय\s*सारिणी", " timetable "),
    (r"टाइम\s*टेबल", " timetable "),
    (r"ਫੀਸ", " fees "),
    (r"फीस", " fees "),
    (r"ਦਾਖਲਾ", " admission "),
    (r"प्रवेश", " admission "),
    (r"admissions", " admission "),
    (r"ਹੋਸਟਲ", " hostel "),
    (r"छात्रावास", " hostel "),
    (r"परिणाम", " result "),
    (r"ਨਤੀਜਾ", " result "),
    (r"नोटिस", " notice "),
    (r"ਨੋਟਿਸ", " notice "),
    (r"कैलेंडर", " calendar "),
    (r"ਕੈਲੰਡਰ", " calendar "),
    (r"ਪੰਜਾਬੀ", " punjabi "),
    (r"à¤¦à¤¸à¥à¤¤à¤¾à¤µà¥‡à¤œà¤¼", " documents "),
    (r"à¤¦à¤¸à¥à¤¤à¤¾à¤µà¥‡à¤œ", " documents "),
    (r"à¨¦à¨¸à¨¤à¨¾à¨µà©‡à¨œà¨¼", " documents "),
    (r"à¨¦à¨¸à¨¤à¨¾à¨µà©‡à¨œ", " documents "),
    (r"à¤•à¥ˆà¤‚à¤Ÿà¥€à¤¨", " canteen "),
    (r"à¤•à¥ˆà¤«à¥‡à¤Ÿà¥‡à¤°à¤¿à¤¯à¤¾", " canteen "),
    (r"à¨•à©ˆà¨‚à¨Ÿà©€à¨¨", " canteen "),
    (r"à¨•à©ˆà¨«à©‡à¨Ÿà©‡à¨°à©€à¨†", " canteen "),
    (r"à¤–à¥‡à¤²\s*à¤µà¤¿à¤­à¤¾à¤—", " sports department "),
    (r"à¤¸à¥à¤ªà¥‹à¤°à¥à¤Ÿà¥à¤¸\s*à¤µà¤¿à¤­à¤¾à¤—", " sports department "),
    (r"à¨–à©‡à¨¡\s*à¨µà¨¿à¨­à¨¾à¨—", " sports department "),
    (r"à¨¸à¨ªà©‹à¨°à¨Ÿà¨¸\s*à¨µà¨¿à¨­à¨¾à¨—", " sports department "),
    (r"à¤–à¥à¤²à¤¾\s*à¤®à¤‚à¤š", " oat "),
    (r"à¤“à¤ªà¤¨\s*à¤à¤¯à¤°\s*à¤¥à¤¿à¤à¤Ÿà¤°", " oat "),
    (r"à¨–à©à©±à¨²à¨¾\s*à¨®à©°à¨š", " oat "),
    (r"à¨“à¨ªà¨¨\s*à¨à¨…à¨°\s*à¨¥à¨¿à¨à¨Ÿà¨°", " oat "),
    (r"à¤¸à¤¿à¤–\s*à¤°à¤¿à¤²à¥€à¤œà¤¨\s*à¤à¤—à¥à¤œà¤¾à¤®", " sre exam "),
    (r"à¤à¤¸à¤†à¤°à¤ˆ", " sre exam "),
    (r"à¨¸à¨¿à©±à¨–\s*à¨°à¨¿à¨²à©€à¨œà¨¨\s*à¨à¨—à¨œà¨¼à¨¾à¨®", " sre exam "),
    (r"à¨à¨¸à¨†à¨°à¨ˆ", " sre exam "),
    (r"\bpinglish\b", " punjabi "),
    (r"\bpunjlish\b", " punjabi "),
    (r"\u0932\u095c\u0915\u093f\u092f\u094b\u0902?", " girls "),
    (r"\u0932\u095c\u0915\u094b\u0902?", " boys "),
    (r"\u0939\u0949\u0938\u094d\u091f\u0932", " hostel "),
    (r"\u0939\u094b\u0938\u094d\u091f\u0932", " hostel "),
    (r"\u091b\u093e\u0924\u094d\u0930\u093e\u0935\u093e\u0938", " hostel "),
    (r"\u0936\u093f\u0915\u094d\u0937\u0915\s*\u0938\u092e\u092f\u0938\u093e\u0930\u093f\u0923\u0940", " teacher timetable "),
    (r"\u091f\u0940\u091a\u0930\s*\u091f\u093e\u0907\u092e\u091f\u0947\u092c\u0932", " teacher timetable "),
    (r"\u092b\u0948\u0915\u0932\u094d\u091f\u0940\s*\u091f\u093e\u0907\u092e\u091f\u0947\u092c\u0932", " teacher timetable "),
    (r"\u0a15\u0a41\u0a5c\u0a40\u0a06\u0a02", " girls "),
    (r"\u0a2e\u0a41\u0a70\u0a21\u0a3f\u0a06\u0a02", " boys "),
    (r"\u0a39\u0a4b\u0a38\u0a1f\u0a32", " hostel "),
    (r"\u0a05\u0a27\u0a3f\u0a06\u0a2a\u0a15\s*\u0a1f\u0a3e\u0a088\u0a2e\u0a1f\u0a47\u0a2c\u0a32", " teacher timetable "),
    (r"\u0a1f\u0a40\u0a1a\u0a30\s*\u0a1f\u0a3e\u0a088\u0a2e\u0a1f\u0a47\u0a2c\u0a32", " teacher timetable "),
    (r"लड़कियों?\s*के?\s*हॉस्टल", " girls hostel "),
    (r"लड़कियों?\s*के?\s*होस्टल", " girls hostel "),
    (r"लड़कियों?\s*के?\s*छात्रावास", " girls hostel "),
    (r"लड़कों?\s*के?\s*हॉस्टल", " boys hostel "),
    (r"लड़कों?\s*के?\s*होस्टल", " boys hostel "),
    (r"लड़कों?\s*के?\s*छात्रावास", " boys hostel "),
    (r"शिक्षक\s*समयसारिणी", " teacher timetable "),
    (r"टीचर\s*टाइमटेबल", " teacher timetable "),
    (r"फैकल्टी\s*टाइमटेबल", " teacher timetable "),
    (r"ਅਧਿਆਪਕ\s*ਟਾਈਮਟੇਬਲ", " teacher timetable "),
    (r"ਟੀਚਰ\s*ਟਾਈਮਟੇਬਲ", " teacher timetable "),
    (r"ਕੁੜੀਆਂ\s*ਦੇ?\s*ਹੋਸਟਲ", " girls hostel "),
    (r"ਮੁੰਡਿਆਂ\s*ਦੇ?\s*ਹੋਸਟਲ", " boys hostel "),
    (r"\bhinglish\b", " hinglish "),
    (r"ਕੰਪਿਊਟਰ\s*ਸਾਇੰਸ", " cse "),
    (r"computer\s*science", " cse "),
    (r"कंप्यूटर\s*साइंस", " cse "),
]


def normalize_multilingual_text(text: str) -> str:
    normalized = (text or "").strip().lower()

    for pattern, replacement in MULTILINGUAL_REPLACEMENTS:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^0-9a-zA-Z\u0900-\u097F\u0A00-\u0A7F#]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def token_set(text: str):
    return set(re.findall(r"[a-zA-Z]+", (text or "").lower()))


def phrase_score(text: str, phrases) -> int:
    lower = (text or "").lower()
    return sum(1 for phrase in phrases if phrase in lower)


def detect_language(text: str) -> str:
    text = (text or "").strip()
    lower = normalize_multilingual_text(text)
    tokens = token_set(lower)

    if re.search(r"[\u0A00-\u0A7F]", text):
        return "pa"

    if re.search(r"[\u0900-\u097F]", text):
        return "hi"

    punjabi_score = phrase_score(lower, ROMAN_PUNJABI_MARKERS)
    hindi_score = phrase_score(lower, ROMAN_HINDI_MARKERS)
    english_hint_score = sum(1 for word in HINGLISH_HINTS if word in tokens)

    if punjabi_score >= 2 and punjabi_score >= hindi_score:
        return "pa"

    if punjabi_score >= 1 and english_hint_score >= 1 and hindi_score == 0:
        return "pa"

    if hindi_score >= 2:
        return "hi"

    if hindi_score >= 1 and english_hint_score >= 1:
        return "hi"

    if punjabi_score >= 1:
        return "pa"

    if hindi_score >= 1:
        return "hi"

    return "en"


def choose_language(ui_language: str, text: str) -> str:
    if ui_language and ui_language != "auto":
        return ui_language
    return detect_language(text)
