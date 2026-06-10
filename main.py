from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse
import httpx
import os

app = FastAPI()

VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
WHATSAPP_TOKEN = os.environ["WHATSAPP_TOKEN"]
PHONE_NUMBER_ID = os.environ["PHONE_NUMBER_ID"]

user_sessions = {}

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

    if text_clean.lower() in ["hi", "hello", "hey", "start"]:
        user_sessions[phone] = {"step": "awaiting_name_city"}
        await send_text(phone,
            "Welcome to Collegedunia - India's leading college discovery platform!\n\n"
            "To help you better, please share your name and city.\n\n"
            "Example: Rahul, Delhi"
        )

    elif step == "awaiting_name_city":
        name = text_clean.split(",")[0].strip()
        user_sessions[phone] = {"step": "main_menu", "name": name}
        await send_text(phone, f"Thanks, {name}!")
        await send_main_menu(phone)

    elif step in [
        "awaiting_exam_appearing_query",
        "awaiting_class10_query",
        "awaiting_class12_query",
        "awaiting_studyabroad_query",
        "awaiting_other_query",
        "awaiting_exam_stream_query",
        "awaiting_course_query",
        "awaiting_college_query",
    ]:
        await send_text(phone,
            f"Got it! For your query: \"{text_clean}\"\n\n"
            "Our team will get back to you shortly, or visit collegedunia.com"
        )
        user_sessions[phone] = {"step": "start"}
        await send_text(phone, "Type hi to go back to the main menu.")

    else:
        await send_text(phone, "Type hi to see the main menu.")


async def handle_list_reply(phone: str, list_id: str):

    # --- MAIN MENU ---
    if list_id == "exams":
        user_sessions[phone] = {"step": "awaiting_exam_status"}
        await send_buttons(phone,
            "Are you currently appearing for 12th or have you completed it?",
            [("12th Appearing", "exam_appearing"), ("12th Completed", "exam_completed")]
        )

    elif list_id == "courses":
        user_sessions[phone] = {"step": "awaiting_course_level"}
        await send_list(phone,
            "Courses and Programs",
            "Please select your level of study:",
            "Select",
            [
                {"id": "course_ug", "title": "Undergraduate", "description": "B.Tech, MBBS, BBA, B.Com & more"},
                {"id": "course_pg", "title": "Postgraduate", "description": "MBA, M.Tech, MCA, M.Sc & more"},
                {"id": "course_diploma", "title": "Diploma", "description": "Polytechnic, ITI & more"},
                {"id": "course_other", "title": "Something Else", "description": "Any other course query"},
            ]
        )

    elif list_id == "colleges":
        user_sessions[phone] = {"step": "awaiting_college_stream"}
        await send_list(phone,
            "Colleges",
            "Please select your stream:",
            "Select",
            [
                {"id": "college_engg", "title": "Engineering", "description": "B.Tech, B.E colleges"},
                {"id": "college_medical", "title": "Medical", "description": "MBBS, BDS, BAMS colleges"},
                {"id": "college_mgmt", "title": "Management", "description": "MBA, BBA colleges"},
                {"id": "college_law", "title": "Law", "description": "LLB, BA LLB colleges"},
                {"id": "college_other", "title": "Something Else", "description": "Any other stream"},
            ]
        )

    elif list_id == "class10":
        user_sessions[phone] = {"step": "awaiting_class10_query"}
        await send_text(phone,
            "Class 10th\n\nPlease type your query below.\n\n"
            "Example: Best schools after 10th, stream selection, scholarship options"
        )

    elif list_id == "class12":
        user_sessions[phone] = {"step": "awaiting_class12_query"}
        await send_text(phone,
            "Class 12th\n\nPlease type your query below.\n\n"
            "Example: Colleges accepting 12th marks, direct admission, cutoffs"
        )

    elif list_id == "studyabroad":
        user_sessions[phone] = {"step": "awaiting_studyabroad_query"}
        await send_text(phone,
            "Study Abroad\n\nPlease type your query below.\n\n"
            "Example: MS in USA, MBA in UK, scholarships for Indian students"
        )

    elif list_id == "other":
        user_sessions[phone] = {"step": "awaiting_other_query"}
        await send_text(phone,
            "Something Else\n\nPlease type your query below and our team will help you out!"
        )

    # --- COURSES SUB-MENU ---
    elif list_id in ["course_ug", "course_pg", "course_diploma", "course_other"]:
        labels = {
            "course_ug": "Undergraduate",
            "course_pg": "Postgraduate",
            "course_diploma": "Diploma",
            "course_other": "Courses",
        }
        user_sessions[phone] = {"step": "awaiting_course_query"}
        await send_text(phone,
            f"{labels[list_id]}\n\nPlease type your course-related query below.\n\n"
            "Example: B.Tech CSE fees, MBA colleges in Mumbai, MBBS admission"
        )

    # --- COLLEGES SUB-MENU ---
    elif list_id in ["college_engg", "college_medical", "college_mgmt", "college_law", "college_other"]:
        labels = {
            "college_engg": "Engineering Colleges",
            "college_medical": "Medical Colleges",
            "college_mgmt": "Management Colleges",
            "college_law": "Law Colleges",
            "college_other": "Colleges",
        }
        user_sessions[phone] = {"step": "awaiting_college_query"}
        await send_text(phone,
            f"{labels[list_id]}\n\nPlease type your query below.\n\n"
            "Example: Top colleges in Delhi, fees, cutoffs, reviews"
        )

    # --- EXAMS STREAM SUB-MENU (after 12th completed) ---
    elif list_id in ["exam_medical", "exam_engg", "exam_mgmt", "exam_law", "exam_finance", "exam_stream_other"]:
        labels = {
            "exam_medical": "Medical Exams",
            "exam_engg": "Engineering Exams",
            "exam_mgmt": "Management Exams",
            "exam_law": "Law Exams",
            "exam_finance": "Finance Exams",
            "exam_stream_other": "Exams",
        }
        user_sessions[phone] = {"step": "awaiting_exam_stream_query"}
        await send_text(phone,
            f"{labels[list_id]}\n\nPlease type your query below.\n\n"
            "Example: NEET cutoffs, JEE Main dates, CAT eligibility"
        )


async def handle_button(phone: str, button_id: str):

    if button_id == "exam_appearing":
        user_sessions[phone] = {"step": "awaiting_exam_appearing_query"}
        await send_text(phone,
            "Exams - 12th Appearing\n\nPlease type your exam-related query below.\n\n"
            "Example: JEE Main 2025 registration, NEET eligibility, exam dates"
        )

    elif button_id == "exam_completed":
        user_sessions[phone] = {"step": "awaiting_exam_stream"}
        await send_list(phone,
            "Exams - 12th Completed",
            "Please select your stream:",
            "Select Stream",
            [
                {"id": "exam_medical", "title": "Medical", "description": "NEET, AIIMS & more"},
                {"id": "exam_engg", "title": "Engineering", "description": "JEE Main, Advanced, BITSAT & more"},
                {"id": "exam_mgmt", "title": "Management", "description": "CAT, XAT, MAT, SNAP & more"},
                {"id": "exam_law", "title": "Law", "description": "CLAT, AILET & more"},
                {"id": "exam_finance", "title": "Finance", "description": "CA, CFA, CS & more"},
                {"id": "exam_stream_other", "title": "Something Else", "description": "Any other exam query"},
            ]
        )

    else:
        await send_text(phone, "Type hi to see the main menu.")


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
                    "footer": {"text": "Powered by Collegedunia"},
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
        "Collegedunia Assistant",
        "Kindly select your desired option below",
        "View Options",
        [
            {"id": "exams", "title": "Exams", "description": "JEE, NEET, CAT, GUJCET & more"},
            {"id": "courses", "title": "Courses and Programs", "description": "B.Tech, MBA, MBBS, B.Com"},
            {"id": "colleges", "title": "Colleges", "description": "Find colleges by state and stream"},
            {"id": "class10", "title": "Class 10th", "description": "Stream selection, schools and more"},
            {"id": "class12", "title": "Class 12th", "description": "Admissions, cutoffs and colleges"},
            {"id": "studyabroad", "title": "Study Abroad", "description": "USA, UK, Canada, Australia"},
            {"id": "other", "title": "Something Else", "description": "Any other query"},
        ]
    )
