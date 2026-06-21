import os
import json
import smtplib
import urllib.request
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup


def web_search_scraper(query):
    """
    Live web search utility using the updated ddgs engine
    to safely extract real-time web context.
    """
    from ddgs import DDGS
    import json

    # Clean up incoming query argument patterns if sent as JSON strings or dicts
    if isinstance(query, dict):
        query = query.get("query", "")
    elif isinstance(query, str) and query.strip().startswith("{"):
        try:
            query = json.loads(query).get("query", "")
        except:
            pass

    if not query or not str(query).strip():
        return "Error: Empty search query provided."

    query = str(query).strip()

    try:
        client = DDGS()
        results = client.text(query, max_results=3)

        if not results:
            return f"Search completed for '{query}', but no web indices were returned."

        formatted_results = []
        for index, item in enumerate(results, 1):
            title = item.get("title", "No Title")
            snippet = item.get("body", item.get("snippet", "No Text Body"))
            formatted_results.append(f"Source {index}: [{title}] - {snippet}")

        return "\n\n".join(formatted_results)

    except Exception as e:
        return f"Network Error: Unable to extract live web data. Detail: {str(e)}"


def agent_send_email(to_email, subject, body_content):
    """
    Sends a structured programmatic HTML email with plain text fallback
    using background environment variables.
    """
    # Pull secure execution keys from background workspace environment files
    sender_email = os.environ.get("EMAIL_SENDER")
    sender_password = os.environ.get("EMAIL_PASSWORD")  # Use an App Password for Gmail
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))

    if not sender_email or not sender_password:
        return "Error: SMTP email credentials are not configured in the host environment variables."

    try:
        # Build multipart alternative container pipeline for multi-client reliability
        msg = MIMEMultipart("alternative")
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject

        # Create Plain-text fallback for standard delivery security filters
        soup = BeautifulSoup(body_content, "html.parser")
        plain_text_fallback = soup.get_text(separator="\n")

        # Create MIME structural data objects
        part1 = MIMEText(plain_text_fallback, "plain")
        part2 = MIMEText(body_content, "html")

        # Attach alternative options (Plain text first, HTML second)
        msg.attach(part1)
        msg.attach(part2)

        # Establish encrypted session tunnel link
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)

        # Fire packet payload
        server.send_message(msg)
        server.quit()

        return f"Success: Email successfully dispatched to {to_email}."

    except Exception as e:
        return f"Email Delivery Error: Execution failed. Detail: {str(e)}"
