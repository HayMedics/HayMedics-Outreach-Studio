# app.py
# HayMedics Outreach Studio - branded Streamlit UI tying together
# research_agent + outreach_crew + sender.

import asyncio
import base64
import csv
import html
import io
import os

# Ensure this thread has an event loop (Streamlit + the Agents SDK need one)
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import streamlit as st

from research_agent import research_lead
from outreach_crew import write_outreach_email
from sender import send_from_queue

# ----------------------------------------------------------------------
# HayMedics branding
# ----------------------------------------------------------------------
NAVY, BLUE, ORANGE = "#16276C", "#2E5EAA", "#F5A623"

st.set_page_config(page_title="HayMedics Outreach Studio",
                   page_icon="🩺", layout="wide")


def logo_data_uri(path):
    """Read a local image and return it as an embeddable data URI (or None)."""
    if not os.path.exists(path):
        return None
    ext = "png" if path.lower().endswith(".png") else "jpeg"
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    return f"data:image/{ext};base64,{encoded}"


LOGO = logo_data_uri("assets/haymedics_logo.png")

BRAND_CSS = """
<style>
.hm-header { display:flex; align-items:center; gap:22px; background:#ffffff;
    border-top:4px solid #F5A623; border-radius:14px; padding:18px 30px;
    margin-bottom:22px; box-shadow:0 4px 18px rgba(22,39,108,0.10); }
.hm-logo { height:56px; }
.hm-title { font-size:24px; font-weight:800; color:#16276C; line-height:1.1; }
.hm-subtitle { font-size:14px; color:#2E5EAA; margin-top:4px; }
.hm-card { background:#fff; border:1px solid #E4E9F2; border-left:5px solid #2E5EAA;
    border-radius:12px; padding:18px 20px; margin-bottom:16px;
    box-shadow:0 2px 10px rgba(22,39,108,0.06); }
.hm-card h4 { margin:0 0 2px 0; color:#16276C; font-size:17px; }
.hm-sub { color:#64748B; font-size:13px; margin-bottom:12px; }
.hm-research { color:#475569; font-size:13px; }
.hm-email { background:#F6F8FC; border-left:3px solid #F5A623; border-radius:8px;
    padding:14px; font-size:14px; color:#16276C; margin-top:10px; }
div.stButton > button { background:#2E5EAA; color:#fff; border:none;
    border-radius:8px; padding:8px 18px; font-weight:600; }
div.stButton > button:hover { background:#16276C; color:#fff; }
</style>
"""
st.markdown(BRAND_CSS, unsafe_allow_html=True)

logo_html = (f'<img src="{LOGO}" class="hm-logo"/>' if LOGO
             else '<div style="font-size:34px">🩺</div>')
st.markdown(
    f'<div class="hm-header">{logo_html}'
    f'<div><div class="hm-title">Outreach Studio</div>'
    f'<div class="hm-subtitle">AI agents research each lead, write a personalised '
    f'email, and prepare it to send.</div></div></div>',
    unsafe_allow_html=True)

# Keep results across Streamlit's automatic re-runs
if "results" not in st.session_state:
    st.session_state.results = []

# ----------------------------------------------------------------------
# Sidebar - campaign settings
# ----------------------------------------------------------------------
with st.sidebar:
    if LOGO:
        st.image("assets/haymedics_logo.png", use_container_width=True)
    st.header("Campaign settings")
    goal = st.text_input("Goal of the email", "Book a 15-minute intro call")
    sender_name = st.text_input("Your name", "Dr. Awal")
    sender_company = st.text_input("Your company", "HayMedics Academy")
    sender_offer = st.text_area("What you offer",
                                "an AI service that automates repetitive admin work")
    st.caption("Used to personalise every email.")

SAMPLE_LEADS = [
    {"name": "Amara Okafor", "role": "Head of Partnerships",
     "company": "Flutterwave", "email": "amara.test@example.com"},
    {"name": "Kwame Boateng", "role": "Head of Talent",
     "company": "Andela", "email": "kwame.test@example.com"},
]

tab_gen, tab_send = st.tabs(["📋  Leads & Draft", "📧  Review & Send"])

# ================= TAB 1: leads + generate =================
with tab_gen:
    st.subheader("1. Your leads")
    uploaded = st.file_uploader(
        "Upload a leads CSV (columns: name, role, company, email)", type="csv")
    if uploaded:
        leads = list(csv.DictReader(io.StringIO(uploaded.getvalue().decode("utf-8"))))
        st.success(f"Loaded {len(leads)} lead(s) from your file.")
    else:
        leads = SAMPLE_LEADS
        st.info("No file uploaded - using 2 sample leads (dummy emails).")

    st.dataframe(leads, use_container_width=True)

    st.subheader("2. Generate drafts")
    st.caption("Each lead runs research -> copywriter -> reviewer. "
               "Free models are slow, so start with a few leads.")

    if st.button("✨ Generate outreach drafts"):
        st.session_state.results = []
        progress = st.progress(0.0)
        status = st.container()
        for idx, lead in enumerate(leads, start=1):
            name, company = lead.get("name", ""), lead.get("company", "")
            role = lead.get("role", "")
            with status:
                st.write(f"🔎 [{idx}/{len(leads)}] Researching **{name}** at **{company}** ...")
            try:
                research = research_lead(name, role, company)
                email_text = write_outreach_email(
                    research=research, name=name, company=company, goal=goal,
                    sender_name=sender_name, sender_company=sender_company,
                    sender_offer=sender_offer)
                st.session_state.results.append({
                    "name": name, "company": company,
                    "email": lead.get("email", ""),
                    "research": research, "email_text": email_text})
            except Exception as e:
                with status:
                    st.error(f"Failed for {name}: {e}")
            progress.progress(idx / len(leads))
        st.success(f"Done. {len(st.session_state.results)} draft(s) ready.")

    if st.session_state.results:
        st.subheader("3. Drafts")
        for r in st.session_state.results:
            name = html.escape(r["name"])
            company = html.escape(r["company"])
            email = html.escape(r["email"])
            research = html.escape(r["research"]).replace("\n", "<br>")
            email_text = html.escape(r["email_text"]).replace("\n", "<br>")
            st.markdown(
                f'<div class="hm-card">'
                f'<h4>{name} — {company}</h4>'
                f'<div class="hm-sub">✉ {email}</div>'
                f'<div class="hm-research"><b>Research brief</b><br>{research}</div>'
                f'<div class="hm-email"><b>Email</b><br>{email_text}</div>'
                f'</div>',
                unsafe_allow_html=True)

# ================= TAB 2: review + send =================
with tab_send:
    st.subheader("Review the send queue")
    if not st.session_state.results:
        st.info("No drafts yet - generate them in the first tab.")
    else:
        rows = [{"name": r["name"], "email": r["email"],
                 "company": r["company"], "email_text": r["email_text"]}
                for r in st.session_state.results]

        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=["name", "email", "company", "email_text"])
        w.writeheader(); w.writerows(rows)
        st.download_button("⬇ Download queue.csv", buf.getvalue(),
                           file_name="queue.csv", mime="text/csv")

        st.divider()
        st.subheader("Send")
        st.warning("Only email people who expect to hear from you. Dummy "
                   "(@example.com) addresses and opt-outs are skipped automatically.")

        if st.button("👀 Preview (dry run - sends nothing)"):
            logs = []
            send_from_queue(rows, send=False, log=lambda m: logs.append(m))
            st.code("\n".join(logs) or "Nothing to preview.")

        st.markdown("**Send for real**")
        confirm = st.checkbox("I confirm I have permission to email these recipients.")
        really = st.checkbox("Yes, actually send now (uncheck = dry run).")
        if st.button("📨 Send emails"):
            if not confirm:
                st.error("Please confirm you have permission first.")
            else:
                logs = []
                sent, skipped = send_from_queue(rows, send=really,
                                                log=lambda m: logs.append(m))
                st.code("\n".join(logs))
                st.success(f"{sent} {'sent' if really else 'would send (dry run)'}, "
                           f"{skipped} skipped.")