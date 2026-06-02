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
    hub_mode: str = Query(default=None, alias="hub.mode"),
    hub_token: str = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str = Query(default=None, alias="hub.challenge")
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
    text = text.strip().lower()
    session = user_sessions.get(phone, {"step": "start"})

    if text in ["hi", "hello", "hey", "start"]:
        user_sessions[phone] = {"step": "main_menu"}
        await send_list_message(phone)
    elif session.get("step") == "course_query":
        await send_text(phone,
            f"For courses like '{text}', visit collegedunia.com and search directly for the most updated listings, fees and cutoffs."
        )
        user_sessions[phone] = {"step": "start"}
        await send_text(phone, "Type 'hi' to go back to the main menu.")
    else:
        await send_text(phone,
            "Sorry, I didn't understand that. Type 'hi' to see the main menu."
        )

async def handle_list_reply(phone: str, list_id: str):
    if list_id == "colleges":
        user_sessions[phone] = {"step": "college_state"}
        await send_buttons(phone, "Which state?", [
            ("Delhi", "state_delhi"),
            ("Maharashtra", "state_mh"),
            ("Gujarat", "state_gj")
        ])
    elif list_id == "exams":
        user_sessions[phone] = {"step": "exam_type"}
        await send_buttons(phone, "Which exam type?", [
            ("Engineering", "exam_engg"),
            ("Medical", "exam_med"),
            ("Management", "exam_mgmt")
        ])
    elif list_id == "courses":
        await send_text(phone, "Which course are you looking for? (e.g. B.Tech CSE, MBA, MBBS)")
        user_sessions[phone] = {"step": "course_query"}
    elif list_id == "cutoffs":
        await send_buttons(phone, "Cutoffs for which exam?", [
            ("JEE Main", "cutoff_jee"),
            ("NEET", "cutoff_neet"),
            ("CAT", "cutoff_cat")
        ])
    elif list_id == "studyabroad":
        await send_text(phone,
            "For Study Abroad guidance, visit:\n\ncollegedunia.com/study-abroad\n\nCovers USA, UK, Canada, Australia, Germany & more."
        )
        user_sessions[phone] = {"step": "start"}
        await send_text(phone, "Type 'hi' to go back to the main menu.")

async def handle_button(phone: str, button_id: str):
    responses = {
        "state_delhi": (
            "Top colleges in Delhi:\n\n"
            "1. IIT Delhi\n2. DTU\n3. NSIT\n4. IP University\n5. Jamia Millia\n\n"
            "collegedunia.com for reviews, cutoffs & fees."
        ),
        "state_mh": (
            "Top colleges in Maharashtra:\n\n"
            "1. IIT Bombay\n2. COEP Pune\n3. VJTI Mumbai\n4. ICT Mumbai\n5. SPPU\n\n"
            "collegedunia.com for reviews, cutoffs & fees."
        ),
        "state_gj": (
            "Top colleges in Gujarat:\n\n"
            "1. NIT Surat\n2. DAIICT\n3. MS University\n4. LDCE Ahmedabad\n5. GCET\n\n"
            "collegedunia.com for reviews, cutoffs & fees."
        ),
        "exam_engg": (
            "Engineering Exams:\n\n"
            "1. JEE Main\n2. JEE Advanced\n3. GUJCET\n4. MHT CET\n5. BITSAT\n\n"
            "collegedunia.com for dates, syllabus & cutoffs."
        ),
        "exam_med": (
            "Medical Exams:\n\n"
            "1. NEET UG\n2. NEET PG\n3. AIIMS\n4. JIPMER\n\n"
            "collegedunia.com for dates, syllabus & cutoffs."
        ),
        "exam_mgmt": (
            "Management Exams:\n\n"
            "1. CAT\n2. XAT\n3. MAT\n4. SNAP\n5. NMAT\n\n"
            "collegedunia.com for dates, syllabus & cutoffs."
        ),
        "cutoff_jee": (
            "JEE Main 2024 Cutoffs (General):\n\n"
            "NIT Trichy CSE: 97.5+\nDTU: 96+\nNSIT: 97+\nNIT Warangal CSE: 97+\n\n"
            "collegedunia.com for full cutoff lists."
        ),
        "cutoff_neet": (
            "NEET 2024 Cutoffs (General):\n\n"
            "AIIMS Delhi: 715+\nMaulana Azad: 650+\nGrant Medical: 620+\n\n"
            "collegedunia.com for full cutoff lists."
        ),
        "cutoff_cat": (
            "CAT 2024 Cutoffs (General):\n\n"
            "IIM Ahmedabad: 99.5+\nIIM Bangalore: 99+\nIIM Calcutta: 99+\nIIM Lucknow: 97+\n\n"
            "collegedunia.com for full cutoff lists."
        ),
    }

    if button_id in responses:
        await send_text(phone, responses[button_id])
        user_sessions[phone] = {"step": "start"}
        await send_text(phone, "Type 'hi' to go back to the main menu.")
    else:
        await send_text(phone, "Type 'hi' to see the main menu.")

BASE_URL = "https://graph.facebook.com/v19.0"

async def send_text(phone: str, message: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{BASE_URL}/{PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": message}
            }
        )

async def send_list_message(phone: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{BASE_URL}/{PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "header": {"type": "text", "text": "Collegedunia Assistant"},
                    "body": {"text": "Hi! What are you looking for today?"},
                    "footer": {"text": "Powered by Collegedunia"},
                    "action": {
                        "button": "Browse Options",
                        "sections": [{
                            "title": "Categories",
                            "rows": [
                                {"id": "colleges", "title": "Colleges", "description": "Find colleges by state, stream"},
                                {"id": "exams", "title": "Exams", "description": "JEE, NEET, CAT, GUJCET & more"},
                                {"id": "courses", "title": "Courses", "description": "B.Tech, MBA, MBBS, B.Com..."},
                                {"id": "cutoffs", "title": "Cutoffs", "description": "Latest cutoff data"},
                                {"id": "studyabroad", "title": "Study Abroad", "description": "International college info"}
                            ]
                        }]
                    }
                }
            }
        )

async def send_buttons(phone: str, body_text: str, buttons: list):
    button_list = [
        {"type": "reply", "reply": {"id": btn_id, "title": btn_label}}
        for btn_label, btn_id in buttons
    ]
    async with httpx.AsyncClient() as client:
        await client.post(
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
        
        
