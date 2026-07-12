# sender.py
# Sends the queued emails from outputs/queue.csv via Gmail.
# SAFETY: dry-run by default. It only sends for real with --send, skips
# test/dummy addresses and opt-outs, and throttles between sends.

import argparse
import csv
import os
import smtplib
import time
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

QUEUE_FILE = "outputs/queue.csv"
SUPPRESSION_FILE = "suppression.csv"          # opt-outs: emails we must never contact
BLOCKED_DOMAINS = {"example.com", "example.org", "example.net", "test.com"}
SEND_DELAY_SECONDS = 30                        # gap between real sends

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def load_suppression():
    """Load the opt-out list (emails we must never email)."""
    if not os.path.exists(SUPPRESSION_FILE):
        return set()
    with open(SUPPRESSION_FILE, newline="", encoding="utf-8") as f:
        return {r["email"].strip().lower() for r in csv.DictReader(f) if r.get("email")}


def split_subject_body(text):
    """Pull a 'Subject:' line out of the email text; the rest is the body."""
    lines = (text or "").strip().splitlines()
    for i, line in enumerate(lines):
        clean = line.strip().lstrip("*").strip()
        if clean.lower().startswith("subject:"):
            subject = clean.split(":", 1)[1].strip()
            body = "\n".join(lines[i + 1:]).strip()
            return subject or "Quick question", body
    return "Quick question", (text or "").strip()


def check_sendable(email, suppression):
    """Our safety gate before any send. Returns (ok, reason)."""
    email = (email or "").strip().lower()
    if "@" not in email:
        return False, "not a valid email"
    if email.split("@")[1] in BLOCKED_DOMAINS:
        return False, "test/dummy address (blocked)"
    if email in suppression:
        return False, "on opt-out list"
    return True, "ok"


def read_queue(limit=None):
    if not os.path.exists(QUEUE_FILE):
        return []
    with open(QUEUE_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


def send_from_queue(rows, send=False, log=print):
    """Core sender. send=False is a safe dry run. log() gets progress lines.
    Returns (count_sent, count_skipped)."""
    suppression = load_suppression()

    server = None
    if send:
        if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
            log("Missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD in .env. Stopping.")
            return 0, 0
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)

    sent = skipped = 0
    for i, row in enumerate(rows, start=1):
        to_email = row.get("email", "")
        name = row.get("name", "")
        ok, reason = check_sendable(to_email, suppression)
        if not ok:
            log(f"[{i}] SKIP {name} <{to_email}> - {reason}")
            skipped += 1
            continue

        subject, body = split_subject_body(row.get("email_text", ""))

        if not send:
            log(f"[{i}] WOULD SEND to {name} <{to_email}>  |  Subject: {subject}")
            sent += 1
            continue

        msg = EmailMessage()
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)
        try:
            server.send_message(msg)
            log(f"[{i}] SENT to {name} <{to_email}>")
            sent += 1
            time.sleep(SEND_DELAY_SECONDS)
        except Exception as e:
            log(f"[{i}] FAILED {name} <{to_email}>: {e}")
            skipped += 1

    if server:
        server.quit()
    return sent, skipped


def run(send=False, limit=None):
    rows = read_queue(limit)
    if not rows:
        print(f"No queue found at {QUEUE_FILE}. Run main.py first.")
        return
    print(f"Mode: {'SEND (real emails)' if send else 'DRY RUN (nothing sent)'}")
    print(f"{len(rows)} email(s) in the queue.\n")
    sent, skipped = send_from_queue(rows, send=send, log=print)
    print(f"\nDone. {sent} {'sent' if send else 'would send'}, {skipped} skipped.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Send queued outreach emails.")
    p.add_argument("--send", action="store_true", help="Actually send (default: dry run).")
    p.add_argument("--limit", type=int, default=None, help="Only the first N emails.")
    args = p.parse_args()
    run(send=args.send, limit=args.limit)