# main.py
# Full pipeline: read leads.csv -> research each lead -> write + review the email
# -> schedule a send time -> save everything. It does NOT send emails.

import csv
import os
import time
from datetime import datetime, timedelta

from research_agent import research_lead
from outreach_crew import write_outreach_email

# ----------------------------------------------------------------------
# 1. YOUR CAMPAIGN SETTINGS  (edit these)
# ----------------------------------------------------------------------
CAMPAIGN = {
    "goal": "Book a 15-minute intro call",
    "sender_name": "Ada",
    "sender_company": "Northwind Labs",
    "sender_offer": "an AI tool that automates customer onboarding",
}

LEADS_FILE = "leads.csv"
OUTPUT_DIR = "outputs"

# ----------------------------------------------------------------------
# 2. A SIMPLE SCHEDULER  (no AI - just business-hours logic)
# ----------------------------------------------------------------------
BUSINESS_START = 9    # 9 AM
BUSINESS_END = 17     # 5 PM
SLOT_MINUTES = 30     # space each send 30 minutes apart


class Scheduler:
    """Hands out send times: weekdays only, 9am-5pm, 30 min apart."""

    def __init__(self):
        self.cursor = self._next_business_morning(datetime.now())

    def _next_business_morning(self, after):
        d = (after + timedelta(days=1)).replace(
            hour=BUSINESS_START, minute=0, second=0, microsecond=0)
        while d.weekday() >= 5:          # 5 = Saturday, 6 = Sunday
            d += timedelta(days=1)
        return d

    def next_slot(self):
        slot = self.cursor
        self.cursor += timedelta(minutes=SLOT_MINUTES)
        if self.cursor.hour >= BUSINESS_END:   # past 5 PM -> next morning
            self.cursor = self._next_business_morning(self.cursor)
        return slot


# ----------------------------------------------------------------------
# 3. HELPERS
# ----------------------------------------------------------------------
def load_leads(path):
    """Read leads.csv into a list of dictionaries."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_email(index, lead, research, email_text, send_time):
    """Save one finished email as a readable file in outputs/."""
    safe_company = lead["company"].replace(" ", "-")
    safe_name = lead["name"].replace(" ", "-")
    filename = f"{index:02d}_{safe_company}_{safe_name}.md"
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Outreach to {lead['name']} ({lead['company']})\n\n")
        f.write(f"**To:** {lead.get('email', 'N/A')}\n")
        f.write(f"**Scheduled send:** {send_time:%A %d %b %Y, %I:%M %p}\n\n")
        f.write("## Research brief\n" + research + "\n\n")
        f.write("## Email\n" + email_text + "\n")
    return path


def write_queue(rows):
    """Write the send queue as one CSV (what a sender would read later)."""
    path = os.path.join(OUTPUT_DIR, "queue.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["scheduled_send", "name", "email", "company", "email_text"])
        writer.writeheader()
        writer.writerows(rows)
    return path


# ----------------------------------------------------------------------
# 4. THE PIPELINE
# ----------------------------------------------------------------------
def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    leads = load_leads(LEADS_FILE)
    scheduler = Scheduler()
    queue_rows = []

    print(f"Loaded {len(leads)} lead(s) from {LEADS_FILE}.\n")

    for i, lead in enumerate(leads, start=1):
        name, company = lead["name"], lead["company"]
        role = lead.get("role", "")
        print(f"[{i}/{len(leads)}] Processing {name} at {company} ...")

        try:
            research = research_lead(name, role, company)              # a) research
            email_text = write_outreach_email(                         # b) write + review
                research=research, name=name, company=company,
                goal=CAMPAIGN["goal"],
                sender_name=CAMPAIGN["sender_name"],
                sender_company=CAMPAIGN["sender_company"],
                sender_offer=CAMPAIGN["sender_offer"],
            )
            send_time = scheduler.next_slot()                          # c) schedule
            saved = save_email(i, lead, research, email_text, send_time)  # d) save
            queue_rows.append({
                "scheduled_send": f"{send_time:%Y-%m-%d %H:%M}",
                "name": name,
                "email": lead.get("email", ""),
                "company": company,
                "email_text": email_text,
            })
            print(f"    saved -> {saved}  (send {send_time:%a %d %b %I:%M %p})\n")

        except Exception as e:
            print(f"    FAILED for {name}: {e}\n")   # skip this lead, keep going

        time.sleep(3)   # be gentle on the free-tier rate limit

    if queue_rows:
        q = write_queue(queue_rows)
        print(f"Done. {len(queue_rows)} email(s) queued in {q}")
        print("Nothing was sent - review the drafts in outputs/ first.")
    else:
        print("No emails were produced. Check the errors above.")


if __name__ == "__main__":
    run()