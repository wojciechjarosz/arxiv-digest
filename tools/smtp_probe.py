# tools/smtp_probe.py
from dotenv import load_dotenv
import os, smtplib, ssl, uuid
from email.message import EmailMessage

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER or "")
TO_EMAILS = [e.strip() for e in os.getenv("TO_EMAILS", "").split(",") if e.strip()]
USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() in ("1","true","yes")

assert SMTP_USER and SMTP_PASS and FROM_EMAIL and TO_EMAILS, "Missing SMTP_* or TO_EMAILS env vars"

subject = f"SMTP probe {uuid.uuid4()}"
msg = EmailMessage()
msg["Subject"] = subject
msg["From"] = FROM_EMAIL
msg["To"] = ", ".join(TO_EMAILS)
msg.set_content("Hello from smtp_probe.py")

print(f"Connecting to {SMTP_HOST}:{SMTP_PORT} as {SMTP_USER} (SSL={USE_SSL})")
if USE_SSL:
    server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30, context=ssl.create_default_context())
else:
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)

server.set_debuglevel(1)  # <- print SMTP conversation
server.ehlo()
if not USE_SSL:
    server.starttls()
    server.ehlo()

server.login(SMTP_USER, SMTP_PASS)
server.send_message(msg)
server.quit()
print(f"Sent probe with subject: {subject}")
