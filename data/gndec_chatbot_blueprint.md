# GNDEC Chatbot Blueprint

## Goal
Build a GNDEC helpdesk chatbot that can answer common queries from:
- Prospective students
- Current students
- Parents and visitors
- Faculty and staff

The bot should prefer official GNDEC sources, give short and clean answers, and open the relevant official page or PDF whenever useful.

## Core Objectives
1. Help users get official GNDEC information quickly and clearly.
2. Support multilingual interaction across English, Hindi, Punjabi, Hinglish, and Roman Punjabi.
3. Allow students to interact with administrators and request document approval digitally through guided chatbot flows, document-support links, and administrative contact routing.

## Primary Personas
- `Prospective student`: asks about admission, eligibility, fees, courses, hostel, documents
- `Current student`: asks about timetable, exams, results, attendance, syllabus, notices
- `Placement-focused student`: asks about T&P drives, eligibility, internships, company visits
- `Administrative seeker`: asks about holidays, academic calendar, certificates, branch change, contacts

## Priority Roadmap
### Phase 1: High confidence support
- Timetable
- Admission process
- B.Tech courses and programs
- HOD and faculty
- Hostel rules and warden contact
- Academic calendar
- Holiday list
- Exam portal and date sheet routing
- Academic portal routing

### Phase 2: Exact academic workflows
- Re-evaluation process
- Admit card flow
- Backlog / reappear exam form
- Internal marks
- Result guidance
- Syllabus by branch and semester
- Previous year papers

### Phase 3: Campus operations
- Scholarships
- Bonafide certificate
- Branch change
- Accounts branch contact
- Administrator interaction for digital document approval
- Document approval status and submission guidance
- Hostel fee and mess fee
- Library timing / fines / issue limits

### Phase 4: Training and placement
- Placement drives
- Eligibility by company
- T&P portal registration
- Internship opportunities
- Placement statistics by department

## Official Source Map
| Topic | Primary Official Source | Notes |
|---|---|---|
| Main college info | `https://www.gndec.ac.in/` | Base source for general queries |
| Admission | `https://admission.gndec.ac.in/` | Best source for application, eligibility, documents |
| Academics / programs | `https://academics.gndec.ac.in/` | Good for courses, academic portal, program pages |
| Exam services | `https://exam.gndec.ac.in/` | Best for date sheet, exam notices, student exam tasks |
| Academic calendar | `https://gndec.ac.in/?q=node/23` | Use latest linked official calendar resource |
| Holiday list | `https://gndec.ac.in/sites/default/files/LoH26.pdf` | Current official holiday list source in project |
| Hostel rules | `https://gndec.ac.in/sites/default/files/Hostel%20Rules_24.pdf` | Rules and hostel policy |
| Hostel helpline / wardens | `https://gndec.ac.in/sites/default/files/Helpline%20Hostel%20Querries.pdf` | Hostel contact details |
| Fee notice | `https://gndec.ac.in/sites/default/files/fnjd25.pdf` | Fee-related official notice |
| CSE | `https://cse.gndec.ac.in/` | HOD, faculty, department details |
| ECE | `https://ece.gndec.ac.in/` | HOD, faculty, department details |
| EE | `https://ee.gndec.ac.in/` | Department information |
| IT | `https://it.gndec.ac.in/` | Department information |
| Civil | `https://ce.gndec.ac.in/` | Department information |
| Mechanical | `https://me.gndec.ac.in/` | Department information |

## Recommended Intent Taxonomy
### Admissions
- `admission_process`
- `admission_eligibility`
- `admission_documents`
- `admission_deadline`
- `admission_contact`
- `lateral_entry`
- `management_quota`

### Academic Support
- `timetable`
- `academic_calendar`
- `holiday_list`
- `syllabus_query`
- `subject_count`
- `previous_papers`
- `class_start`

### Exams
- `exam_datesheet`
- `final_exam_dates`
- `re_evaluation`
- `admit_card`
- `backlog_form`
- `internal_marks`
- `result_query`

### Fees
- `fee_structure`
- `semester_fee`
- `last_fee_date`
- `late_fee`
- `fee_receipt`
- `online_fee_payment`

### Departments
- `hod_info`
- `faculty_list`
- `department_website`
- `lab_facilities`
- `department_contact`
- `placement_stats`

### Hostel
- `hostel_apply`
- `hostel_fee`
- `hostel_rules`
- `hostel_warden`
- `boys_girls_hostel`
- `mess_charges`

### Library
- `library_timing`
- `ebooks_access`
- `opac_link`
- `late_fine_books`
- `books_issue_limit`

### Notices and Events
- `latest_notices`
- `student_circulars`
- `important_announcements`
- `upcoming_events`

### Portals
- `academic_portal`
- `erp_login`
- `forgot_password`
- `attendance_check`
- `marks_portal`
- `profile_update`

### Documents and Admin
- `bonafide_certificate`
- `branch_change`
- `accounts_branch_contact`
- `ccc_location`
- `admin_document_approval`
- `document_approval_status`
- `administrator_contact`

### Placement and Internship
- `placement_drives`
- `placement_eligibility`
- `tnp_registration`
- `internships`

## Answer Strategy Rules
- For official links, answer briefly and attach the source link.
- For timetable, prefer direct class anchor or exact student timetable file.
- For HOD / faculty / warden, answer with structured details and official source.
- For sensitive or changing queries such as fees, dates, admissions, holidays, and exams, prefer official latest resources over memorized summaries.
- If the requested year or item is not listed on the official source, explicitly say that and open the latest available official resource.

## Data Collection Checklist
- Collect 15 to 30 user phrasing variations for each high-priority intent.
- Include Hindi, English, Hinglish, Punjabi, and Roman Punjabi variants.
- Store one `official_sources` list per intent.
- Mark each intent as one of:
  - `exact_answer`
  - `summary_plus_link`
  - `portal_redirect`
  - `pdf_redirect`

## Runtime Gaps To Build Next
- Exact ERP login and password reset workflow
- Exact exam re-evaluation and backlog flow
- Subject-level syllabus retrieval
- Placement company and CGPA filters
- Bonafide and certificate workflows
- Scholarship eligibility rules
