import os, logging, smtplib, ssl
from dotenv import load_dotenv
from email.message import EmailMessage
from tenacity import retry, wait_exponential, stop_after_attempt
from typing import List, Dict
from .summarize import PaperSummary

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER or "no-reply@example.com")
TO_EMAILS = [e.strip() for e in os.getenv("TO_EMAILS", "").split(",") if e.strip()]
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() in ("1","true","yes")
SMTP_DEBUG = os.getenv("SMTP_DEBUG", "false").lower() in ("1","true","yes")

def build_digest_text(selected: List[Dict], summaries: List[PaperSummary]) -> str:
    lines = ["Daily arXiv AI Digest", ""]
    for i, p in enumerate(selected):
        title, arxiv_url, summary =  p['title'], p['arxiv_url'], summaries[i].text
        lines.append(f"{i+1}) {title.strip()}")
        lines.append(f"Link: {arxiv_url}")
        lines.append(summary)
        lines.append("")
    return "\n".join(lines)

def build_digest_html(selected: List[Dict], summaries: List[PaperSummary]) -> str:
    parts = []
    parts.append('<div id="toc"><strong>Today\'s topics</strong><ul>')
    parts.append("</ul></div>")
    for i, p in enumerate(selected):
        arxiv_url, title, pdf_url, authors = p['arxiv_url'], p['title'], p['pdf_url'], p['authors']
        summary = summaries[i].text
        parts.append(f'<article><h3><a href="{arxiv_url}">{title}</a> <a href="{pdf_url}">[PDF]</a></h3>')
        parts.append(f'<p class="meta">{authors}</p>')
        parts.append(f'<div class="summary exec">{summary}</div>')
        parts.append("</article>")
    return "\n".join(parts)

@retry(wait=wait_exponential(multiplier=1, min=2, max=8), stop=stop_after_attempt(3))
def send_email(subject: str, text_body: str, html_body: str):
    if not TO_EMAILS:
        raise RuntimeError("TO_EMAILS is empty. Set env var TO_EMAILS='you@example.com[,other@example.com]'")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = ", ".join(TO_EMAILS)
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    if SMTP_DEBUG:
        # Debug mode: don’t send, just log/print the message
        logging.info("[DEBUG MODE] Would send email: subject=%s, to=%s", subject, msg["To"])
        print("----- EMAIL DEBUG OUTPUT -----")
        print("To:", msg["To"])
        print("Subject:", subject)
        print("--- TEXT ---")
        print(text_body)
        print("--- HTML ---")
        print(html_body)
        print("------------------------------")
        return

    logging.info(
        "Connecting SMTP %s:%s as %s (SSL=%s, DEBUG=%s) | From=%s | To=%s",
        SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_USE_SSL, SMTP_DEBUG, FROM_EMAIL, msg["To"]
    )

    try:
        if SMTP_USE_SSL:
            s = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30, context=ssl.create_default_context())
        else:
            s = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
        s.set_debuglevel(1 if SMTP_DEBUG else 0)
        s.ehlo()
        if not SMTP_USE_SSL:
            s.starttls()
            s.ehlo()
        s.login(SMTP_USER, SMTP_PASS)
        resp = s.send_message(msg)  # dict of failures; empty dict == success
        s.quit()
    except Exception as e:
        logging.error("SMTP send failed: %s", e)
        raise

    if resp:
        logging.warning("Partial send failures: %s", resp)
    else:
        logging.info("Email accepted by SMTP; subject=%s", subject)