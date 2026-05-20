# GNDEC Chatbot Fresh Project

A clean Flask GNDEC helper chatbot with:
- dark modern UI
- multilingual selector
- direct official URL/PDF opening
- timetable link resolution from official department timetable pages where possible
- academic calendar PDF, fee notice PDF, hostel PDFs, library and admission official links

## Project Objectives
- Help students and visitors quickly access official GNDEC information.
- Provide multilingual support across English, Hindi, Punjabi, Hinglish, and Roman Punjabi.
- Allow students to interact with administrators and request document approval digitally through chatbot-guided workflows and official support links.

## Planning Assets
- `data/gndec_chatbot_blueprint.md`: intent roadmap, source map, personas, and build priorities
- `data/gndec_intent_dataset.json`: categorized seed intent dataset with sample queries and official source mapping

## Run
py -m venv venv
venv\Scripts\activate
py -m pip install -r requirements.txt
py app.py

Open http://127.0.0.1:5000
