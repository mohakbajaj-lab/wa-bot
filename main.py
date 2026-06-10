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

    # Always restart on greeting keywords
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

    elif step == "awaiting_exam_query":
        await send_text(phone,
            f"Got it! For your query: \"{text_clean}\"\n\n"
            "Our team will get back to you shortly, or visit collegedunia.com/exams"
        )
        user_sessions[phone] = {"step": "start"}
        await send_text(phone, "Type hi to go back to the main menu.")

    elif step == "awaiting_course_query":
        await send_text(phone,
            f"Got it! For your query: \"{text_clean}\"\n\n"
            "Our team will get back to you shortly, or visit collegedunia.com/courses"
        )
        user_sessions[phone] = {"step": "start"}
        await send_text(phone, "Type hi to go back to the main menu.")

    elif step == "awaiting_college_query":
        await send_text(phone,
            f"Got it! For your query: \"{text_clean}\"\n\n"
            "Our team will get back to you shortly, or visit collegedunia.com"
        )
        user_sessions[phone] = {"step": "start"}
        await send_text(phone, "Type hi to go back to the main menu.")

    elif step == "awaiting_class10_query":
        await send_text(phone,
            f"Got it! For your query: \"{text_clean}\"\n\n"
            "Our team will get back to you shortly, or visit collegedunia.com"
        )
        user_sessions[phone] = {"step": "start"}
        await send_text(phone, "Type hi to go back to the main menu.")

    elif step == "awaiting_class12_query":
        await send_text(phone,
            f"Got it! For your query: \"{text_clean}\"\n\n"
            "Our team will get back to you shortly, or visit collegedunia.com"
        )
        user_sessions[phone] = {"step": "start"}
        await send_text(phone, "Type hi to go back to the main menu.")

    elif step == "awaiting_studyabroad_query":
        await send_text(phone,
            f"Got it! For your query: \"{text_clean}\"\n\n"
            "Our team will get back to you shortly, or visit collegedunia.com/study-abroad"
        )
        user_sessions[phone] = {"step": "start"}
        await send_text(phone, "Type hi to go back to the main menu.")

    elif step == "awaiting_other_query":
        await send_text(phone,
            f"Got it! For your query: \"{text_clean}\"\n\n"
            "Our team will get back to you shortly."
        )
        user_sessions[phone] = {"step": "start"}
        await send_text(phone, "Type hi to go back to the main menu.")

    else:
        await send_text(phone, "Type hi to see the main menu.")


async def handle_list_reply(phone: str, list_id: str):
    if list_id == "exams":
        user_sessions[phone] = {"step": "awaiting_exam_query"}
        await send_text(phone,
            "Exams\n\nPlease type your exam-related query below.\n\n"
            "Example: JEE Main 2025 dates, NEET cutoffs, CAT eligibility"
        )

    elif list_id == "courses":
        user_sessions[phone] = {"step": "awaiting_course_query"}
        await send_text(phone,
            "Courses and Programs\n\nPlease type your course-related query below.\n\n"
            "Example: B.Tech CSE fees, MBA colleges in Mumbai, MBBS admission"
        )

    elif list_id == "colleges":
        user_sessions[phone] = {"step": "awaiting_college_query"}
        await send_text(phone,
            "Colleges\n\nPlease type your college-related query below.\n\n"
            "Example: Top engineering colleges in Delhi, NIT Trichy reviews"
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


async def handle_button(phone: str, button_id: str):
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

async def send_main_menu(phone: str):
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
                    "header": {"type": "text", "text": "Collegedunia Assistant"},
                    "body": {"text": "Kindly select your desired option below"},
                    "footer": {"text": "Powered by Collegedunia"},
                    "action": {
                        "button": "View Options",
                        "sections": [{
                            "title": "What are you looking for?",
                            "rows": [
                                {"id": "exams", "title": "Exams", "description": "JEE, NEET, CAT, GUJCET & more"},
                                {"id": "courses", "title": "Courses and Programs", "description": "B.Tech, MBA, MBBS, B.Com"},
                                {"id": "colleges", "title": "Colleges", "description": "Find colleges by state and stream"},
                                {"id": "class10", "title": "Class 10th", "description": "Stream selection, schools and more"},
                                {"id": "class12", "title": "Class 12th", "description": "Admissions, cutoffs and colleges"},
                                {"id": "studyabroad", "title": "Study Abroad", "description": "USA, UK, Canada, Australia"},
                                {"id": "other", "title": "Something Else", "description": "Any other query"}
                            ]
                        }]
                    }
                }
            }
        )
        print(f"send_main_menu response: {response.status_code} - {response.text}")
