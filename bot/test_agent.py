"""
test_agent.py
=============
Tests the AI complaint agent locally without WhatsApp.
Runs 7 real Nigerian complaint scenarios through the classifier.

Usage:
  1. Start API: uvicorn api.main:app --reload --port 8000
  2. Run tests: python bot/test_agent.py

Author: Ella | NSERC Portfolio AI-001
"""

import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

TEST_COMPLAINTS = [
    {
        "label": "Power Outage — Pidgin",
        "message": "NEPA don take our light since yesterday 6pm. E don do like 18 hours now. Our whole street get darkness. Abuja DisCo no dey do anything!",
        "phone": "+2348011111001",
    },
    {
        "label": "Estimated Bill — Angry English",
        "message": "I am very angry! My bill is N68,000 this month and I know I don't use up to N10,000 worth of electricity. You people never read my meter in 3 months. This is fraud!",
        "phone": "+2348022222002",
    },
    {
        "label": "Prepaid Meter Fault — Mixed Language",
        "message": "Good morning, my prepaid meter don spoil. Every time I load my unit, e dey show TAMPER and cut off. I dey Port Harcourt. Please help.",
        "phone": "+2348033333003",
    },
    {
        "label": "Transformer Emergency — Safety Critical",
        "message": "Emergency! Our transformer at Wuse Zone 5 junction is sparking and on fire! Please come now it is very dangerous!",
        "phone": "+2348044444004",
    },
    {
        "label": "Reconnection Request — English",
        "message": "I was disconnected last week but I have now paid my outstanding balance of N28,500. My account number is 1234567890. Please reconnect my line in Lekki Phase 1.",
        "phone": "+2348055555005",
    },
    {
        "label": "New Connection — English",
        "message": "Hello, I just moved into a new apartment in Bodija, Ibadan and I need a new electricity meter. What are the requirements and how much will it cost?",
        "phone": "+2348066666006",
    },
    {
        "label": "Service Quality — Hausa-Pidgin Mix",
        "message": "Wallahi this DisCo don tire me. Every day light dey go every hour. We dey pay bill but we no dey get light. Kano people suffer too much.",
        "phone": "+2348077777007",
    },
]


async def run_test(complaint: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{BASE_URL}/api/classify",
            json={"message": complaint["message"], "phone": complaint["phone"]},
        )
        return r.json()


def print_result(label: str, complaint: dict, result: dict):
    print(f"\n{'='*60}")
    print(f"  TEST: {label}")
    print(f"{'='*60}")
    print(f"  Message:   {complaint['message'][:75]}...")
    print(f"  Ticket:    {result.get('ticket_id', 'N/A')}")
    print(f"  Category:  {result.get('category_label')} [{result.get('category')}]")
    print(f"  Priority:  {result.get('priority')}")
    print(f"  SLA:       {result.get('sla_hours')} hours")
    print(f"  Sentiment: {result.get('sentiment')}")
    print(f"  Language:  {result.get('language')}")
    print(f"  Escalate:  {result.get('escalate')}")
    if result.get("escalation_reason"):
        print(f"  Reason:    {result.get('escalation_reason')}")
    print(f"\n  Summary:\n  {result.get('summary')}")
    print(f"\n  AI Response to Customer:\n  {result.get('response_preview')}")


async def main():
    print("\n🤖 NSERC AI DisCo Complaint Agent — Test Suite")
    print(f"   {len(TEST_COMPLAINTS)} scenarios\n")

    # Check server
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/health", timeout=5)
            print(f"API server: {r.json()['status']}\n")
    except Exception:
        print(f"API server not reachable at {BASE_URL}")
        print("Start it with: uvicorn api.main:app --reload")
        return

    passed = 0
    for complaint in TEST_COMPLAINTS:
        try:
            result = await run_test(complaint)
            print_result(complaint["label"], complaint, result)
            passed += 1
        except Exception as e:
            print(f"\nFAILED: {complaint['label']} — {e}")

    print(f"\n\n{'='*60}")
    print(f"  RESULTS: {passed}/{len(TEST_COMPLAINTS)} passed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
