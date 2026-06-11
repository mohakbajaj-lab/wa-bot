from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse
import httpx
import os

app = FastAPI()


@app.get("/")
async def root():
    return {"status": "alive"}


VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
WHATSAPP_TOKEN = os.environ["WHATSAPP_TOKEN"]
PHONE_NUMBER_ID = os.environ["PHONE_NUMBER_ID"]

# Google Sheets lead logging
SHEETS_WEBHOOK_URL = os.environ.get("SHEETS_WEBHOOK_URL")
SHEETS_SECRET = os.environ.get("SHEETS_SECRET")

user_sessions = {}

# Readable interest labels for menu (list) selections
INTEREST_LABELS = {
    # main menu
    "exams": "Exams", "courses": "Courses", "colleges": "Colleges",
    "class10": "Class 10th", "class12": "Class 12th",
    "studyabroad": "Study Abroad", "other": "Other",
    # course levels
    "course_ug": "UG Courses", "course_pg": "PG Courses",
    "course_diploma": "Diploma", "course_other": "Courses - Other",
    # UG streams
    "ug_engg": "UG Engineering", "ug_medical": "UG Medical", "ug_mgmt": "UG Management",
    "ug_law": "UG Law", "ug_arts": "UG Arts & Science", "ug_commerce": "UG Commerce",
    # PG
    "pg_mba": "MBA", "pg_mtech": "M.Tech", "pg_mca": "MCA", "pg_msc": "M.Sc",
    "pg_mcom": "M.Com", "pg_llm": "LLM", "pg_other": "PG - Other",
    # Diploma
    "dip_engg": "Diploma Engineering", "dip_design": "Diploma Design",
    "dip_mgmt": "Diploma Management", "dip_it": "Diploma IT",
    # exam categories
    "exam_medical": "Medical Exams", "exam_engg": "Engineering Exams",
    "exam_mgmt": "Management Exams", "exam_law": "Law Exams",
    "exam_finance": "Finance Exams", "exam_arts": "Arts Exams",
    "exam_stream_other": "Exams - Other",
    # exam leaves
    "eq_cat": "CAT", "eq_cuet_mgmt": "CUET (Mgmt)", "eq_xat": "XAT", "eq_snap": "SNAP",
    "eq_cmat": "CMAT", "eq_mgmt_other": "Mgmt Exam - Other",
    "eq_clat": "CLAT", "eq_ailet": "AILET", "eq_lsat": "LSAT",
    "eq_mhcet_law": "MH CET Law", "eq_law_other": "Law Exam - Other",
    "eq_jee_main": "JEE Main", "eq_jee_adv": "JEE Advanced", "eq_bitsat": "BITSAT",
    "eq_viteee": "VITEEE", "eq_comedk": "COMEDK", "eq_mhtcet": "MHTCET",
    "eq_wbjee": "WBJEE", "eq_kcet": "KCET", "eq_engg_other": "Engg Exam - Other",
    "eq_neet_ug": "NEET-UG", "eq_neet_pg": "NEET-PG", "eq_aiims_nursing": "AIIMS Nursing",
    "eq_ini_cet": "INI-CET", "eq_neet_ss": "NEET-SS", "eq_medical_other": "Medical Exam - Other",
    "eq_ca": "CA", "eq_cfa": "CFA", "eq_cs": "CS", "eq_cma": "CMA",
    "eq_finance_other": "Finance Exam - Other",
    "eq_cuet_arts": "CUET (Arts)", "eq_nid": "NID DAT", "eq_uceed": "UCEED",
    "eq_nift": "NIFT", "eq_arts_other": "Arts Exam - Other",
    # college streams
    "college_engg": "College - Engineering", "college_medical": "College - Medical",
    "college_mgmt": "College - Management", "college_law": "College - Law",
    "college_other": "College - Other",
}

# Readable interest labels for button selections
BUTTON_LABELS = {
    "exam_appearing": "Exams (12th Appearing)",
    "exam_completed": "Exams (12th Completed)",
    "college_yes": "College (has one in mind)",
    "college_no": "College (needs help)",
}


async def log_lead(phone, session, query=""):
    if not SHEETS_WEBHOOK_URL:
        print("LEAD SKIPPED: SHEETS_WEBHOOK_URL not set")
        return
    payload = {
        "secret": SHEETS_SECRET,
        "phone": phone,
        "name": session.get("name", ""),
        "city": session.get("city", ""),
        "interest": session.get("interest", ""),
        "query": query,
    }
    print(f"LEAD SENDING: {payload}")
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            r = await client.post(SHEETS_WEBHOOK_URL, json=payload, timeout=10)
            print(f"LEAD RESPONSE: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"lead log error: {e}")


@app.get("/webhook")
async def verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge")
):
    if hub_mode == "subscribe" and hub_token == VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)
    return PlainTextResponse("Forbidden", status_code=403)

@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                for message in messages:
                    from_number = message["from"]
                    msg_type = message["type"]
                    if msg_type == "text":
                        user_text = message["text"]["body"]
                        await handle_text(from_number, user_text)
                    elif msg_type == "interactive":
                        interactive = message["interactive"]
                        if interactive["type"] == "button_reply":
                            await handle_button(from_number, interactive["button_reply"]["id"])
                        elif interactive["type"] == "list_reply":
                            await handle_list_reply(from_number, interactive["list_reply"]["id"])
    except Exception as e:
        print(f"Error: {e}")
    return {"status": "ok"}


async def handle_text(phone: str, text: str):
    text_clean = text.strip()
    session = user_sessions.get(phone, {"step": "start"})
    step = session.get("step", "start")

    if text_clean.lower() in ["hi", "hello", "hey", "start", "menu"]:
        new_session = {"step": "awaiting_name_city"}
        user_sessions[phone] = new_session
        await log_lead(phone, new_session)
        await send_text(phone,
            "👋 Welcome to *Collegedunia* — India's leading college discovery platform!\n\n"
            "To help you better, please share your name and city.\n\n"
            "📝 Example: Rahul, Delhi"
        )

    elif step == "awaiting_name_city":
        parts = [p.strip() for p in text_clean.split(",")]
        name = parts[0] if parts else text_clean
        city = parts[1] if len(parts) > 1 else ""
        new_session = {"step": "main_menu", "name": name, "city": city}
        user_sessions[phone] = new_session
        await log_lead(phone, new_session)
        await send_text(phone, f"Great, {name}! 🎓 Let's find what you're looking for.")
        await send_main_menu(phone)

    elif step == "awaiting_college_name":
        user_sessions[phone] = {**session, "step": "awaiting_college_budget", "college_name": text_clean}
        await send_text(phone, "💰 What is your budget for the *entire course duration*?\n\n_Type 'menu' to go back._")

    elif step == "awaiting_college_budget":
        user_sessions[phone] = {**session, "step": "awaiting_college_stream", "budget": text_clean}
        await send_college_stream_list(phone)

    elif step in [
        "awaiting_exam_appearing_query",
        "awaiting_exam_stream_query",
        "awaiting_course_query",
        "awaiting_college_query",
        "awaiting_class10_query",
        "awaiting_class12_query",
        "awaiting_studyabroad_query",
        "awaiting_other_query",
    ]:
        await log_lead(phone, session, text_clean)
        await send_text(phone,
            f"✅ Got it! We've noted your query:\n\n_{text_clean}_\n\n"
            "Our team will get back to you shortly. You can also visit *collegedunia.com* for more info."
        )
        # keep name/city/interest so a follow-up still maps to the same lead row
        user_sessions[phone] = {**session, "step": "start"}
        await send_text(phone, "Type *hi* to go back to the main menu. 😊")

    else:
        await send_text(phone, "Type *hi* to see the main menu. 😊")


async def handle_list_reply(phone: str, list_id: str):
    session = user_sessions.get(phone, {})

    # --- MAIN MENU ---
    if list_id == "exams":
        user_sessions[phone] = {**session, "step": "awaiting_exam_status"}
        await send_buttons(phone,
            "📚 Are you currently appearing for 12th or have you completed it?",
            [("12th Appearing 📖", "exam_appearing"), ("12th Completed ✅", "exam_completed")]
        )

    elif list_id == "courses":
        user_sessions[phone] = {**session, "step": "awaiting_course_level"}
        await send_list(phone,
            "🎓 Courses & Programs",
            "Select your level of study:",
            "Select",
            [
                {"id": "course_ug", "title": "🎓 Undergraduate", "description": "B.Tech, MBBS, BBA, B.Com & more"},
                {"id": "course_pg", "title": "📚 Postgraduate", "description": "MBA, M.Tech, MCA, M.Sc & more"},
                {"id": "course_diploma", "title": "📋 Diploma", "description": "Polytechnic, Design, IT & more"},
                {"id": "course_other", "title": "🔍 Something Else", "description": "Any other course query"},
            ]
        )

    elif list_id == "colleges":
        user_sessions[phone] = {**session, "step": "awaiting_college_mind"}
        await send_buttons(phone,
            "🏫 Do you have a college in mind?",
            [("Yes, I do 👍", "college_yes"), ("No, help me 🔍", "college_no")]
        )

    elif list_id == "class10":
        user_sessions[phone] = {**session, "step": "awaiting_class10_query"}
        await send_text(phone,
            "📘 *Class 10th*\n\nPlease type your query below.\n\n"
            "Example: Stream selection, best schools, scholarships\n\n_Type 'menu' to go back._"
        )

    elif list_id == "class12":
        user_sessions[phone] = {**session, "step": "awaiting_class12_query"}
        await send_text(phone,
            "📗 *Class 12th*\n\nPlease type your query below.\n\n"
            "Example: Colleges accepting 12th marks, direct admission, cutoffs\n\n_Type 'menu' to go back._"
        )

    elif list_id == "studyabroad":
        user_sessions[phone] = {**session, "step": "awaiting_studyabroad_query"}
        await send_text(phone,
            "✈️ *Study Abroad*\n\nPlease type your query below.\n\n"
            "Example: MS in USA, MBA in UK, scholarships for Indian students\n\n_Type 'menu' to go back._"
        )

    elif list_id == "other":
        user_sessions[phone] = {**session, "step": "awaiting_other_query"}
        await send_text(phone,
            "🔍 *Something Else*\n\nPlease type your query and our team will help you out!\n\n_Type 'menu' to go back._"
        )

    # --- COURSES: UG ---
    elif list_id == "course_ug":
        await send_list(phone,
            "🎓 Undergraduate",
            "Select a stream:",
            "Select",
            [
                {"id": "ug_engg", "title": "⚙️ Engineering", "description": "B.Tech, B.E & more"},
                {"id": "ug_medical", "title": "🏥 Medical", "description": "MBBS, BDS, BAMS & more"},
                {"id": "ug_mgmt", "title": "💼 Management", "description": "BBA, BMS & more"},
                {"id": "ug_law", "title": "⚖️ Law", "description": "BA LLB, BBA LLB & more"},
                {"id": "ug_arts", "title": "🎨 Arts & Science", "description": "BA, B.Sc & more"},
                {"id": "ug_commerce", "title": "📊 Commerce", "description": "B.Com, CA & more"},
            ]
        )

    # --- COURSES: PG ---
    elif list_id == "course_pg":
        await send_list(phone,
            "📚 Postgraduate",
            "Select a program:",
            "Select",
            [
                {"id": "pg_mba", "title": "💼 MBA", "description": "MBA & PGDM programs"},
                {"id": "pg_mtech", "title": "⚙️ M.Tech", "description": "M.Tech, M.E programs"},
                {"id": "pg_mca", "title": "💻 MCA", "description": "Master of Computer Applications"},
                {"id": "pg_msc", "title": "🔬 M.Sc", "description": "M.Sc programs"},
                {"id": "pg_mcom", "title": "📊 M.Com", "description": "Master of Commerce"},
                {"id": "pg_llm", "title": "⚖️ LLM", "description": "Master of Law"},
                {"id": "pg_other", "title": "🔍 Something Else", "description": "Any other PG program"},
            ]
        )

    # --- COURSES: DIPLOMA ---
    elif list_id == "course_diploma":
        await send_list(phone,
            "📋 Diploma",
            "Select a category:",
            "Select",
            [
                {"id": "dip_engg", "title": "⚙️ Engineering & Polytechnic", "description": "Polytechnic diploma programs"},
                {"id": "dip_design", "title": "🎨 Creative & Design", "description": "Design, animation & arts"},
                {"id": "dip_mgmt", "title": "💼 Management & Business", "description": "Business diploma programs"},
                {"id": "dip_it", "title": "💻 IT & Tech", "description": "Computer & tech programs"},
            ]
        )

    elif list_id == "course_other":
        user_sessions[phone] = {**session, "step": "awaiting_course_query"}
        await send_text(phone, "🔍 Please type your course-related query below.\n\n_Type 'menu' to go back._")

    elif list_id in ["ug_engg", "ug_medical", "ug_mgmt", "ug_law", "ug_arts", "ug_commerce",
                     "pg_mba", "pg_mtech", "pg_mca", "pg_msc", "pg_mcom", "pg_llm", "pg_other",
                     "dip_engg", "dip_design", "dip_mgmt", "dip_it"]:
        user_sessions[phone] = {**session, "step": "awaiting_course_query"}
        await send_text(phone, "📝 Please type your query below.\n\n_Type 'menu' to go back._")

    # --- EXAMS: 12TH COMPLETED STREAM ---
    elif list_id == "exam_mgmt":
        await send_list(phone,
            "💼 Management Exams",
            "Select an exam:",
            "Select",
            [
                {"id": "eq_cat", "title": "CAT", "description": "Common Admission Test"},
                {"id": "eq_cuet_mgmt", "title": "CUET", "description": "Common University Entrance Test"},
                {"id": "eq_xat", "title": "XAT", "description": "Xavier Aptitude Test"},
                {"id": "eq_snap", "title": "SNAP", "description": "Symbiosis National Aptitude Test"},
                {"id": "eq_cmat", "title": "CMAT", "description": "Common Management Admission Test"},
                {"id": "eq_mgmt_other", "title": "🔍 Something Else", "description": "Any other management exam"},
            ]
        )

    elif list_id == "exam_law":
        await send_list(phone,
            "⚖️ Law Exams",
            "Select an exam:",
            "Select",
            [
                {"id": "eq_clat", "title": "CLAT", "description": "Common Law Admission Test"},
                {"id": "eq_ailet", "title": "AILET", "description": "All India Law Entrance Test"},
                {"id": "eq_lsat", "title": "LSAT", "description": "Law School Admission Test"},
                {"id": "eq_mhcet_law", "title": "MH CET Law", "description": "Maharashtra Law CET"},
                {"id": "eq_law_other", "title": "🔍 Something Else", "description": "Any other law exam"},
            ]
        )

    elif list_id == "exam_engg":
        await send_list(phone,
            "⚙️ Engineering Exams",
            "Select an exam:",
            "Select",
            [
                {"id": "eq_jee_main", "title": "JEE Main", "description": "Joint Entrance Exam Main"},
                {"id": "eq_jee_adv", "title": "JEE Advanced", "description": "Joint Entrance Exam Advanced"},
                {"id": "eq_bitsat", "title": "BITSAT", "description": "BITS Pilani Admission Test"},
                {"id": "eq_viteee", "title": "VITEEE", "description": "VIT Engineering Entrance"},
                {"id": "eq_comedk", "title": "COMEDK", "description": "Karnataka Engineering Exam"},
                {"id": "eq_mhtcet", "title": "MHTCET", "description": "Maharashtra CET"},
                {"id": "eq_wbjee", "title": "WBJEE", "description": "West Bengal JEE"},
                {"id": "eq_kcet", "title": "KCET", "description": "Karnataka CET"},
                {"id": "eq_engg_other", "title": "🔍 Something Else", "description": "Any other engineering exam"},
            ]
        )

    elif list_id == "exam_medical":
        await send_list(phone,
            "🏥 Medical Exams",
            "Select an exam:",
            "Select",
            [
                {"id": "eq_neet_ug", "title": "NEET-UG", "description": "National Eligibility cum Entrance Test UG"},
                {"id": "eq_neet_pg", "title": "NEET-PG", "description": "National Eligibility cum Entrance Test PG"},
                {"id": "eq_aiims_nursing", "title": "AIIMS B.Sc Nursing", "description": "AIIMS Nursing Entrance"},
                {"id": "eq_ini_cet", "title": "INI-CET", "description": "Institute of National Importance CET"},
                {"id": "eq_neet_ss", "title": "NEET-SS", "description": "NEET Super Speciality"},
                {"id": "eq_medical_other", "title": "🔍 Something Else", "description": "Any other medical exam"},
            ]
        )

    elif list_id == "exam_finance":
        await send_list(phone,
            "📊 Finance Exams",
            "Select an exam:",
            "Select",
            [
                {"id": "eq_ca", "title": "CA", "description": "Chartered Accountancy"},
                {"id": "eq_cfa", "title": "CFA", "description": "Chartered Financial Analyst"},
                {"id": "eq_cs", "title": "CS", "description": "Company Secretary"},
                {"id": "eq_cma", "title": "CMA", "description": "Cost Management Accountant"},
                {"id": "eq_finance_other", "title": "🔍 Something Else", "description": "Any other finance exam"},
            ]
        )

    elif list_id == "exam_arts":
        await send_list(phone,
            "🎨 Arts Exams",
            "Select an exam:",
            "Select",
            [
                {"id": "eq_cuet_arts", "title": "CUET", "description": "Common University Entrance Test"},
                {"id": "eq_nid", "title": "NID DAT", "description": "National Institute of Design"},
                {"id": "eq_uceed", "title": "UCEED", "description": "Undergraduate Common Entrance Exam for Design"},
                {"id": "eq_nift", "title": "NIFT Entrance", "description": "National Institute of Fashion Technology"},
                {"id": "eq_arts_other", "title": "🔍 Something Else", "description": "Any other arts exam"},
            ]
        )

    elif list_id == "exam_stream_other":
        user_sessions[phone] = {**session, "step": "awaiting_exam_stream_query"}
        await send_text(phone, "📝 Please type your exam-related query below.\n\n_Type 'menu' to go back._")

    # --- ALL EXAM LEAF NODES → free text ---
    elif list_id in [
        "eq_cat", "eq_cuet_mgmt", "eq_xat", "eq_snap", "eq_cmat", "eq_mgmt_other",
        "eq_clat", "eq_ailet", "eq_lsat", "eq_mhcet_law", "eq_law_other",
        "eq_jee_main", "eq_jee_adv", "eq_bitsat", "eq_viteee", "eq_comedk",
        "eq_mhtcet", "eq_wbjee", "eq_kcet", "eq_engg_other",
        "eq_neet_ug", "eq_neet_pg", "eq_aiims_nursing", "eq_ini_cet", "eq_neet_ss", "eq_medical_other",
        "eq_ca", "eq_cfa", "eq_cs", "eq_cma", "eq_finance_other",
        "eq_cuet_arts", "eq_nid", "eq_uceed", "eq_nift", "eq_arts_other",
    ]:
        user_sessions[phone] = {**session, "step": "awaiting_exam_stream_query"}
        await send_text(phone, "📝 Please type your query below.\n\n_Type 'menu' to go back._")

    # --- COLLEGES STREAM (after budget) ---
    elif list_id in ["college_engg", "college_medical", "college_mgmt", "college_law", "college_other"]:
        user_sessions[phone] = {**session, "step": "awaiting_college_query"}
        await send_text(phone, "📝 Please type your query below.\n\n_Type 'menu' to go back._")

    # --- record interest for EVERY recognised selection ---
    label = INTEREST_LABELS.get(list_id)
    if label:
        sess = user_sessions.get(phone, {})
        sess["interest"] = label
        user_sessions[phone] = sess
        await log_lead(phone, sess)


async def handle_button(phone: str, button_id: str):
    session = user_sessions.get(phone, {})

    if button_id == "exam_appearing":
        user_sessions[phone] = {**session, "step": "awaiting_exam_appearing_query"}
        await send_text(phone,
            "📖 *Exams — 12th Appearing*\n\nPlease type your exam-related query below.\n\n"
            "Example: JEE Main 2025 registration, NEET eligibility, exam dates\n\n_Type 'menu' to go back._"
        )

    elif button_id == "exam_completed":
        user_sessions[phone] = {**session, "step": "awaiting_exam_stream"}
        await send_list(phone,
            "✅ Exams — 12th Completed",
            "Select an exam category:",
            "Select",
            [
                {"id": "exam_medical", "title": "🏥 Medical", "description": "NEET-UG, NEET-PG & more"},
                {"id": "exam_engg", "title": "⚙️ Engineering", "description": "JEE Main, Advanced, BITSAT & more"},
                {"id": "exam_mgmt", "title": "💼 Management", "description": "CAT, XAT, SNAP & more"},
                {"id": "exam_law", "title": "⚖️ Law", "description": "CLAT, AILET & more"},
                {"id": "exam_finance", "title": "📊 Finance", "description": "CA, CFA, CS, CMA & more"},
                {"id": "exam_arts", "title": "🎨 Arts", "description": "CUET, NID DAT, NIFT & more"},
                {"id": "exam_stream_other", "title": "🔍 Something Else", "description": "Any other exam"},
            ]
        )

    elif button_id == "college_yes":
        user_sessions[phone] = {**session, "step": "awaiting_college_name"}
        await send_text(phone, "🏫 Please type the name of the college.\n\n_Type 'menu' to go back._")

    elif button_id == "college_no":
        user_sessions[phone] = {**session, "step": "awaiting_college_budget"}
        await send_text(phone, "💰 What is your budget for the *entire course duration*?\n\n_Type 'menu' to go back._")

    else:
        await send_text(phone, "Type *hi* to see the main menu. 😊")

    # --- record interest for recognised button selections ---
    label = BUTTON_LABELS.get(button_id)
    if label:
        sess = user_sessions.get(phone, {})
        sess["interest"] = label
        user_sessions[phone] = sess
        await log_lead(phone, sess)


async def send_college_stream_list(phone: str):
    await send_list(phone,
        "🏫 Colleges",
        "Select a stream:",
        "Select",
        [
            {"id": "college_engg", "title": "⚙️ Engineering", "description": "B.Tech, B.E colleges"},
            {"id": "college_medical", "title": "🏥 Medical", "description": "MBBS, BDS, BAMS colleges"},
            {"id": "college_mgmt", "title": "💼 Management", "description": "MBA, BBA colleges"},
            {"id": "college_law", "title": "⚖️ Law", "description": "LLB, BA LLB colleges"},
            {"id": "college_other", "title": "🔍 Something Else", "description": "Any other stream"},
        ]
    )


BASE_URL = "https://graph.facebook.com/v19.0"

async def send_text(phone: str, message: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/{PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": message}
            }
        )
        print(f"send_text response: {response.status_code} - {response.text}")


async def send_buttons(phone: str, body_text: str, buttons: list):
    button_list = [
        {"type": "reply", "reply": {"id": btn_id, "title": btn_label}}
        for btn_label, btn_id in buttons
    ]
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/{PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": body_text},
                    "action": {"buttons": button_list}
                }
            }
        )
        print(f"send_buttons response: {response.status_code} - {response.text}")


async def send_list(phone: str, header: str, body_text: str, button_label: str, rows: list):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/{PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "header": {"type": "text", "text": header},
                    "body": {"text": body_text},
                    "footer": {"text": "Type 'menu' to go back anytime"},
                    "action": {
                        "button": button_label,
                        "sections": [{"title": "Options", "rows": rows}]
                    }
                }
            }
        )
        print(f"send_list response: {response.status_code} - {response.text}")


async def send_main_menu(phone: str):
    await send_list(phone,
        "🎓 Collegedunia Assistant",
        "What are you looking for today?",
        "View Options",
        [
            {"id": "exams", "title": "📝 Exams", "description": "JEE, NEET, CAT, CLAT & more"},
            {"id": "courses", "title": "🎓 Courses & Programs", "description": "B.Tech, MBA, MBBS, B.Com"},
            {"id": "colleges", "title": "🏫 Colleges", "description": "Find colleges by stream & budget"},
            {"id": "class10", "title": "📘 Class 10th", "description": "Stream selection, schools & more"},
            {"id": "class12", "title": "📗 Class 12th", "description": "Admissions, cutoffs & colleges"},
            {"id": "studyabroad", "title": "✈️ Study Abroad", "description": "USA, UK, Canada, Australia"},
            {"id": "other", "title": "🔍 Something Else", "description": "Any other query"},
        ]
    )
