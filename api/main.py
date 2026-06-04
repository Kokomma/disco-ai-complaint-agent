"""
main.py
=======
FastAPI application — AI DisCo Customer Complaint Agent.
Author: Ella | Portfolio AI-001
"""

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import json
import uuid
import httpx
from datetime import datetime, timezone
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

app = FastAPI(
    title="NSERC AI DisCo Complaint Agent",
    description="AI-powered WhatsApp complaint handler for Nigerian DisCos",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY      = os.getenv("ANTHROPIC_API_KEY")
TWILIO_ACCOUNT_SID     = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN      = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
SUPABASE_URL           = os.getenv("SUPABASE_URL")
SUPABASE_KEY           = os.getenv("SUPABASE_ANON_KEY")
DATABASE_URL           = os.getenv("DATABASE_URL")

CATEGORIES = {
    "outage_report":     "Power Outage",
    "billing_dispute":   "Billing & Metering",
    "meter_fault":       "Meter Issues",
    "reconnection":      "Reconnection Request",
    "high_bill":         "Estimated Billing",
    "transformer_fault": "Transformer / Infrastructure",
    "poor_service":      "Service Quality",
    "new_connection":    "New Connection Request",
    "other":             "General Enquiry",
}

SLA_HOURS = {
    "outage_report": 4,     "transformer_fault": 8,
    "reconnection": 24,     "meter_fault": 48,
    "poor_service": 48,     "billing_dispute": 72,
    "high_bill": 72,        "other": 72,
    "new_connection": 120,
}

PRIORITY = {
    "outage_report": "CRITICAL",  "transformer_fault": "HIGH",
    "reconnection": "HIGH",       "meter_fault": "MEDIUM",
    "billing_dispute": "MEDIUM",  "high_bill": "MEDIUM",
    "poor_service": "LOW",        "new_connection": "LOW",
    "other": "LOW",
}

DISCO_KEYWORDS = {
    "Abuja DisCo":         ["abuja", "fct", "gwagwalada", "kuje", "kwali"],
    "Ikeja DisCo":         ["ikeja", "agege", "ikorodu", "lagos north"],
    "Eko DisCo":           ["eko", "vi", "victoria island", "surulere", "apapa"],
    "Ibadan DisCo":        ["ibadan", "oyo", "ogun", "abeokuta", "osun"],
    "Enugu DisCo":         ["enugu", "anambra", "onitsha", "awka", "ebonyi"],
    "Kano DisCo":          ["kano", "jigawa", "katsina"],
    "Port Harcourt DisCo": ["port harcourt", "ph city", "rivers", "bayelsa"],
    "Benin DisCo":         ["benin", "edo", "delta", "ondo"],
    "Kaduna DisCo":        ["kaduna", "sokoto", "kebbi", "zamfara"],
    "Jos DisCo":           ["jos", "plateau", "benue"],
    "Yola DisCo":          ["yola", "adamawa", "taraba", "borno", "gombe"],
}


class ClassifyRequest(BaseModel):
    message: str
    phone: Optional[str] = "+2340000000000"


def infer_disco(message: str) -> str:
    msg = message.lower()
    for disco, keywords in DISCO_KEYWORDS.items():
        if any(k in msg for k in keywords):
            return disco
    return "Unknown DisCo"


async def classify_complaint(message: str, phone: str) -> dict:
    system_prompt = """You are an AI assistant for a Nigerian electricity Distribution Company (DisCo).
Classify customer complaints received via WhatsApp with empathy and professionalism.
Customers may write in English, Pidgin English, or a mix.
Common Pidgin: "NEPA don take light" = outage, "light don go" = outage,
"meter no dey work" = meter fault, "bill too much" = high bill.

Respond ONLY with valid JSON, no markdown, no extra text:
{
  "category": "<outage_report|billing_dispute|meter_fault|reconnection|high_bill|transformer_fault|poor_service|new_connection|other>",
  "summary": "<1-2 sentence professional summary for ops team>",
  "sentiment": "<frustrated|angry|neutral|urgent|confused>",
  "language_detected": "<English|Pidgin|Mixed>",
  "response_message": "<empathetic WhatsApp reply in customer language, 2-4 sentences, include {TICKET_ID}>",
  "escalate": <true if safety risk or fire or sparking; false otherwise>,
  "escalation_reason": "<reason if escalate true, else null>"
}"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-5",
                "max_tokens": 800,
                "system": system_prompt,
                "messages": [{"role": "user",
                               "content": f"Customer: {phone}\nMessage: {message}"}],
            }
        )

    if r.status_code != 200:
        logger.error(f"Claude API error: {r.status_code}")
        raise Exception("Classification service unavailable")

    text = r.json()["content"][0]["text"].strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


async def save_ticket(ticket: dict):
    if DATABASE_URL:
        try:
            import asyncpg
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.execute("""
                INSERT INTO complaint_tickets
                    (ticket_id, customer_phone, message, category,
                     category_label, priority, sla_hours, ai_summary,
                     ai_response, sentiment, disco_assigned, status, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                ON CONFLICT (ticket_id) DO NOTHING
            """,
                ticket["ticket_id"], ticket["customer_phone"],
                ticket["message"], ticket["category"],
                ticket["category_label"], ticket["priority"],
                ticket["sla_hours"], ticket["ai_summary"],
                ticket["ai_response"], ticket["sentiment"],
                ticket["disco_assigned"], ticket["status"],
                datetime.now(timezone.utc),
            )
            await conn.close()
            logger.success(f"Ticket {ticket['ticket_id']} saved to Postgres")
            return
        except Exception as e:
            logger.error(f"Postgres save failed: {e}")
            return

    if SUPABASE_URL and SUPABASE_KEY:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{SUPABASE_URL}/rest/v1/complaint_tickets",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                json=ticket,
            )
            if r.status_code in (200, 201):
                logger.success(f"Ticket {ticket['ticket_id']} saved to Supabase")
            else:
                logger.error(f"Supabase error: {r.status_code}")
        return

    logger.warning("No database configured — ticket not saved")


async def send_reply(to: str, message: str):
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.warning("Twilio not configured — reply not sent")
        return
    to_number = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{TWILIO_ACCOUNT_SID}/Messages.json",
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            data={"From": TWILIO_WHATSAPP_NUMBER, "To": to_number, "Body": message},
        )
        if r.status_code == 201:
            logger.success(f"Reply sent to {to}")
        else:
            logger.error(f"Twilio error: {r.status_code}")


@app.get("/")
async def root():
    return {
        "service": "NSERC AI DisCo Complaint Agent",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request, tasks: BackgroundTasks):
    form = await request.form()
    body        = form.get("Body", "").strip()
    from_number = form.get("From", "")

    if not body:
        return PlainTextResponse("", status_code=200)

    logger.info(f"Message from {from_number}: {body[:80]}")

    try:
        result = await classify_complaint(body, from_number)
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        fallback = ("Sorry, we are experiencing a technical issue. "
                    "Please call our customer care line for assistance.")
        tasks.add_task(send_reply, from_number, fallback)
        return PlainTextResponse("", status_code=200)

    ticket_id    = f"TKT-{uuid.uuid4().hex[:8].upper()}"
    category     = result.get("category", "other")
    response_msg = result.get("response_message", "").replace("{TICKET_ID}", ticket_id)

    ticket = {
        "ticket_id":      ticket_id,
        "customer_phone": from_number,
        "message":        body,
        "category":       category,
        "category_label": CATEGORIES.get(category, "General Enquiry"),
        "priority":       PRIORITY.get(category, "LOW"),
        "sla_hours":      SLA_HOURS.get(category, 72),
        "ai_summary":     result.get("summary", ""),
        "ai_response":    response_msg,
        "sentiment":      result.get("sentiment", "neutral"),
        "disco_assigned": infer_disco(body),
        "status":         "ESCALATED" if result.get("escalate") else "OPEN",
        "created_at":     datetime.now(timezone.utc).isoformat(),
    }

    tasks.add_task(save_ticket, ticket)
    tasks.add_task(send_reply, from_number, response_msg)

    if result.get("escalate"):
        logger.warning(f"ESCALATION [{ticket_id}]: {result.get('escalation_reason')}")

    return PlainTextResponse("", status_code=200)


@app.post("/api/classify")
async def classify_direct(req: ClassifyRequest):
    result    = await classify_complaint(req.message, req.phone)
    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
    category  = result.get("category", "other")
    return {
        "ticket_id":          ticket_id,
        "category":           category,
        "category_label":     CATEGORIES.get(category),
        "priority":           PRIORITY.get(category),
        "sla_hours":          SLA_HOURS.get(category),
        "summary":            result.get("summary"),
        "sentiment":          result.get("sentiment"),
        "language":           result.get("language_detected"),
        "escalate":           result.get("escalate"),
        "escalation_reason":  result.get("escalation_reason"),
        "response_preview":   result.get("response_message", "").replace(
                                  "{TICKET_ID}", ticket_id),
    }


@app.get("/api/tickets")
async def get_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"error": "Supabase not configured", "tickets": []}

    params = {"order": "created_at.desc", "limit": limit}
    if status:
        params["status"] = f"eq.{status}"
    if priority:
        params["priority"] = f"eq.{priority}"

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/complaint_tickets",
            headers={"apikey": SUPABASE_KEY,
                     "Authorization": f"Bearer {SUPABASE_KEY}"},
            params=params,
        )
    return r.json()
