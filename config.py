# config.py
import os

# --- AI CONFIGURATION ---
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()

# --- COLLEGE LINKS ---
GNDEC = {
    "home": "https://www.gndec.ac.in/",
    "principal_desk": "https://www.gndec.ac.in/?q=node/5",
    "academic_calendar_pdf": "https://www.gndec.ac.in/sites/default/files/ac_jul_dec2025.pdf",
    "academic_calendar_page": "https://gndec.ac.in/?q=node/23",
    "holiday_list_page": "https://gndec.ac.in/?q=holidays",
    "holiday_list_2026_pdf": "https://gndec.ac.in/sites/default/files/LoH26.pdf",
    "fee_notice_pdf": "https://gndec.ac.in/sites/default/files/fnjd25.pdf",
    "fee_structure_page": "https://admission.gndec.ac.in/Fee_Structure.php",
    "hostel_rules_pdf": "https://gndec.ac.in/sites/default/files/Hostel%20Rules_24.pdf",
    "hostel_helpline_pdf": "https://gndec.ac.in/sites/default/files/Helpline%20Hostel%20Querries.pdf",
    "admission_portal": "https://admission.gndec.ac.in/",
    "admission_notices": "https://admission.gndec.ac.in/important_notices.php",
    "exam_portal": "https://exam.gndec.ac.in/",
    "academic_portal": "https://academics.gndec.ac.in/",
    "programs": "https://academics.gndec.ac.in/programs/",
    "library": "https://library.gndec.ac.in/?q=node/2",
    "library_home": "https://gndec.ac.in/library/",
    "sre_page": "https://www.gndec.ac.in/?q=node/509",
    "sports_department": "https://sports.gndec.ac.in/?q=node/9",
    "oat_page": "https://gndec.ac.in/cultural/?q=facilities",
    "campus_life": "https://gndec.ac.in/?q=node/58",
    "cse": "https://cse.gndec.ac.in/",
    "cse_timetable": "https://cse.gndec.ac.in/sites/default/files/TT%20Jan-June%202026_groups_days_horizontal%20%282%29_0.html",
    "cse_teacher_timetable": "https://cse.gndec.ac.in/sites/default/files/TT%20Jan-June%202026_teachers_days_horizontal%20%283%29.html",
    "ece": "https://ece.gndec.ac.in/",
    "ece_timetable": "https://ece.gndec.ac.in/sites/default/files/classes%20individual%20%283%29.html",
    "ee": "https://ee.gndec.ac.in/",
    "ee_timetable": "https://ee.gndec.ac.in/?q=node/5",
    "it": "https://it.gndec.ac.in/",
    "it_timetable": "https://it.gndec.ac.in/sites/default/files/jan_june2025_6%2027%20dec_years_days_horizontal%20%286%29.html",
    "civil": "https://ce.gndec.ac.in/",
    "civil_timetable": "https://ce.gndec.ac.in/sites/default/files/TT_19.01.2026_data_and_timetable_groups_days_horizontal.html",
    "mechanical": "https://me.gndec.ac.in/",
    "mechanical_timetable": "https://me.gndec.ac.in/sites/default/files/JAN%20MAY%202026%20lock_groups_days_horizontal%20%281%29_0.html",
    "appsc": "https://appsc.gndec.ac.in/",
    "appsc_timetable": "https://appsc.gndec.ac.in/time_tables",
}

# --- DEPARTMENT MAPPING ---
DEPARTMENTS = {
    "CSE": {"label": "Computer Science and Engineering", "page": GNDEC["cse"], "timetable": GNDEC["cse_timetable"]},
    "ECE": {"label": "Electronics and Communication Engineering", "page": GNDEC["ece"], "timetable": GNDEC["ece_timetable"]},
    "EE": {"label": "Electrical Engineering", "page": GNDEC["ee"], "timetable": GNDEC["ee_timetable"]},
    "IT": {"label": "Information Technology", "page": GNDEC["it"], "timetable": GNDEC["it_timetable"]},
    "CIVIL": {"label": "Civil Engineering", "page": GNDEC["civil"], "timetable": GNDEC["civil_timetable"]},
    "MECHANICAL": {"label": "Mechanical and Production Engineering", "page": GNDEC["mechanical"], "timetable": GNDEC["mechanical_timetable"]},
    "APPSC": {"label": "Applied Sciences", "page": GNDEC["appsc"], "timetable": GNDEC["appsc_timetable"]},
}
