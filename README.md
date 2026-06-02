# 🤖 AI Customer Complaint Agent for DisCos — AI-001

> **WhatsApp-based AI complaint handler for Nigerian Distribution Companies — intelligent triage, Pidgin/English support, Supabase ticket logging, and real-time SLA tracking.**

![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)
![Claude](https://img.shields.io/badge/Claude_API-Sonnet-orange)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase)
![Twilio](https://img.shields.io/badge/Twilio-WhatsApp-F22F46?logo=twilio)

---

## 🎯 Problem Statement

Nigerian DisCo customer service is overwhelmed:
- Eko DisCo alone receives **2,000+ complaints daily** across phone, walk-in, and social media
- Average resolution time: **72–96 hours** for billing disputes, **8–24 hours** for outages
- No intelligent triage — all complaints hit the same queue regardless of urgency
- Zero support for Pidgin English — the most common language Nigerian customers actually use

**This project builds a production-ready AI complaint agent that:**
- Receives complaints via WhatsApp (Nigeria's dominant messenger platform)
- Classifies into 9 NERC-aligned categories using Claude Sonnet
- Understands English, Pidgin English, and mixed language naturally
- Responds empathetically within seconds with a reference ticket number
- Logs structured tickets to Supabase with SLA tracking and escalation logic
- Flags safety-critical events (transformer fires, sparking) for immediate escalation

---

## 🏗️ Architecture

Customer (WhatsApp)
│
▼ HTTP POST webhook
Twilio WhatsApp API
│
▼
FastAPI Application (main.py)
├── POST /webhook/whatsapp   ← receives Twilio events
├── POST /api/classify        ← direct test endpoint
└── GET  /api/tickets         ← ops dashboard feed
│
├──► Claude API (Sonnet)
│    • 9-category classification
│    • Pidgin / English detection
│    • Sentiment analysis
│    • Escalation flag
│
├──► Supabase (PostgreSQL)
│    • complaint_tickets table
│    • SLA breach view
│    • RLS policies
│
└──► Twilio (reply)
• Empathetic response in customer's language
• Ticket reference number
---

## 💬 Sample Exchange

**Customer (Pidgin):**
> "NEPA don take our light since yesterday 6pm. E don do like 18 hours now."

**AI Agent (60 seconds later):**
> "We don receive your complaint o! Ticket TKT-A3F1C2D4 don open. Our team dey investigate the outage for your area and we go restore light within 4 hours. If matter urgent, call 0800-IKEJA-HELP."

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [Anthropic API key](https://console.anthropic.com) (free tier works)
- [Twilio account](https://twilio.com) (free trial works)
- [Supabase project](https://supabase.com) (free tier works)

### Step 1 — Clone & Install
```bash
git clone https://github.com/Kokomma/disco-ai-complaint-agent
cd disco-ai-complaint-agent
pip install -r requirements.txt
```

### Step 2 — Configure Environment
```bash
cp .env.example .env
# Fill in your API keys
```

### Step 3 — Set up Supabase
1. Create project at supabase.com
2. SQL Editor → New Query
3. Paste contents of database/schema.sql → Run

### Step 4 — Start the API
```bash
uvicorn api.main:app --reload --port 8000
```

### Step 5 — Test without WhatsApp
```bash
python bot/test_agent.py
# Runs 7 Nigerian complaint scenarios and shows AI output
```

### Step 6 — Connect WhatsApp (Twilio Sandbox)

1. Install ngrok: https://ngrok.com
2. Run: ngrok http 8000
3. Copy the https URL (e.g. https://abc123.ngrok.io)
4. In Twilio Console: Messaging → Try it out → Send a WhatsApp message Sandbox settings → When a message comes in: https://abc123.ngrok.io/webhook/whatsapp
5. Send "join <your-keyword>" to +1 415 523 8886
6. Then send any complaint message

---

## 📊 Complaint Categories & SLA

| Category | Label | Priority | SLA |
|----------|-------|---------|-----|
| outage_report | Power Outage | CRITICAL | 4 hrs |
| transformer_fault | Transformer / Infrastructure | HIGH | 8 hrs |
| reconnection | Reconnection Request | HIGH | 24 hrs |
| meter_fault | Meter Issues | MEDIUM | 48 hrs |
| billing_dispute | Billing & Metering | MEDIUM | 72 hrs |
| high_bill | Estimated Billing | MEDIUM | 72 hrs |
| poor_service | Service Quality | LOW | 48 hrs |
| new_connection | New Connection Request | LOW | 120 hrs |
| other | General Enquiry | LOW | 72 hrs |

---

## 💼 Business Impact

> *"Reduces DisCo complaint response time from 72 hours to under 60 seconds for initial acknowledgement. AI triage routes critical issues 4x faster than manual dispatch. Conservative revenue estimate: ₦5–10M/year per DisCo as a licensed SaaS — across all 11 DisCos = ₦55–110M ARR potential."*

---

## 🛠️ Tools Used

| Tool | Purpose |
|------|---------|
| FastAPI | REST API + WhatsApp webhook |
| Claude API (Sonnet) | Complaint classification + response |
| Twilio WhatsApp | Incoming/outgoing WhatsApp messages |
| Supabase | PostgreSQL + REST API + RLS |
| Python 3.11 | Backend logic |
| httpx | Async HTTP client |
| uvicorn | ASGI server |

---

*Built by Ella — Portfolio | [LinkedIn](https://linkedin.com/in/emmanuella-samuel/) | [GitHub](https://github.com/Kokomma)*
