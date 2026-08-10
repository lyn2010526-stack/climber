"""Email sending and management tools.

Provides tools for composing, sending, and managing emails via SMTP.
Supports HTML content, attachments, CC/BCC, and multiple providers.
"""

from __future__ import annotations

import json
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from app.tools import tool

logger = structlog.get_logger()


@tool(description="Send an email via SMTP. Supports plain text, HTML content, attachments, CC, and BCC. Configure SMTP via environment variables or tool parameters.")
async def send_email(
    to: str,
    subject: str,
    body: str,
    body_type: str = "plain",
    cc: str = "",
    bcc: str = "",
    attachments: str = "",
    smtp_host: str = "",
    smtp_port: int = 587,
    smtp_user: str = "",
    smtp_password: str = "",
    from_addr: str = "",
) -> str:
    """Send an email.

    Args:
        to: Recipient email address (comma-separated for multiple).
        subject: Email subject line.
        body: Email body content.
        body_type: Content type - plain or html.
        cc: CC recipients (comma-separated).
        bcc: BCC recipients (comma-separated).
        attachments: Comma-separated file paths to attach.
        smtp_host: SMTP server host (defaults to env SMTP_HOST).
        smtp_port: SMTP server port (defaults to env SMTP_PORT or 587).
        smtp_user: SMTP username (defaults to env SMTP_USER).
        smtp_password: SMTP password (defaults to env SMTP_PASSWORD).
        from_addr: From address (defaults to env FROM_EMAIL).
    """
    try:
        # Resolve SMTP settings
        host = smtp_host or os.environ.get("SMTP_HOST", "smtp.gmail.com")
        port = smtp_port or int(os.environ.get("SMTP_PORT", "587"))
        user = smtp_user or os.environ.get("SMTP_USER", "")
        password = smtp_password or os.environ.get("SMTP_PASSWORD", "")
        sender = from_addr or os.environ.get("FROM_EMAIL", user)

        if not user or not password:
            return (
                "Error: SMTP credentials not configured. Set SMTP_USER and SMTP_PASSWORD "
                "environment variables, or pass smtp_user and smtp_password parameters.\n\n"
                "For Gmail: Use an App Password (not your regular password). "
                "Enable 2FA and generate at: https://myaccount.google.com/apppasswords"
            )

        if not sender:
            sender = user

        # Build message
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = to
        msg["Subject"] = subject

        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc

        # Body
        content_type = "html" if body_type == "html" else "plain"
        msg.attach(MIMEText(body, content_type, "utf-8"))

        # Attachments
        attached_files = []
        if attachments:
            for filepath in attachments.split(","):
                filepath = filepath.strip()
                if not os.path.exists(filepath):
                    return f"Error: Attachment not found: {filepath}"
                with open(filepath, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(filepath)}",
                )
                msg.attach(part)
                attached_files.append(os.path.basename(filepath))

        # Recipients
        recipients = [addr.strip() for addr in to.split(",")]
        if cc:
            recipients += [addr.strip() for addr in cc.split(",")]
        if bcc:
            recipients += [addr.strip() for addr in bcc.split(",")]

        # Send
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, password)
            server.sendmail(sender, recipients, msg.as_string())

        result = f"Email sent successfully to {to}"
        if cc:
            result += f" (CC: {cc})"
        if attached_files:
            result += f"\nAttachments: {', '.join(attached_files)}"
        return result

    except smtplib.SMTPAuthenticationError:
        return "Error: SMTP authentication failed. Check your username and password. For Gmail, use an App Password."
    except smtplib.SMTPException as e:
        return f"SMTP error: {e!s}"
    except Exception as e:
        return f"Error sending email: {e!s}"


@tool(description="Send a batch of personalized emails using a template and data file. Each row in the data file generates one email.")
async def send_batch_emails(
    data_file: str,
    subject_template: str,
    body_template: str,
    to_column: str = "email",
    body_type: str = "plain",
    file_type: str = "auto",
    smtp_host: str = "",
    smtp_port: int = 587,
    smtp_user: str = "",
    smtp_password: str = "",
    from_addr: str = "",
    delay_seconds: float = 1.0,
) -> str:
    """Send batch emails using a template.

    Args:
        data_file: Path to CSV/JSON file with recipient data.
        subject_template: Subject line template (use {column_name} for placeholders).
        body_template: Body template with {column_name} placeholders.
        to_column: Column name containing email addresses.
        body_type: plain or html.
        file_type: csv, json, auto.
        smtp_host: SMTP host.
        smtp_port: SMTP port.
        smtp_user: SMTP user.
        smtp_password: SMTP password.
        from_addr: From address.
        delay_seconds: Delay between sends.
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas not installed."

    try:
        if file_type == "auto":
            ext = os.path.splitext(data_file)[1].lower()
            file_type = "json" if ext == ".json" else "csv"

        if file_type == "json":
            df = pd.read_json(data_file)
        else:
            df = pd.read_csv(data_file)

        if to_column not in df.columns:
            return f"Error: Column '{to_column}' not found. Available: {', '.join(df.columns)}"

        # Resolve SMTP
        host = smtp_host or os.environ.get("SMTP_HOST", "smtp.gmail.com")
        port = smtp_port or int(os.environ.get("SMTP_PORT", "587"))
        user = smtp_user or os.environ.get("SMTP_USER", "")
        password = smtp_password or os.environ.get("SMTP_PASSWORD", "")
        sender = from_addr or os.environ.get("FROM_EMAIL", user)

        if not user or not password:
            return "Error: SMTP credentials not configured."

        sent = 0
        failed = 0
        errors = []

        import time

        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, password)

            for _, row in df.iterrows():
                try:
                    row_dict = row.to_dict()
                    to_addr = row_dict[to_column]
                    subject = subject_template.format(**row_dict)
                    body = body_template.format(**row_dict)

                    msg = MIMEMultipart()
                    msg["From"] = sender
                    msg["To"] = to_addr
                    msg["Subject"] = subject
                    msg.attach(MIMEText(body, body_type, "utf-8"))

                    server.sendmail(sender, [to_addr], msg.as_string())
                    sent += 1
                    time.sleep(delay_seconds)
                except Exception as e:
                    failed += 1
                    errors.append(f"  {row.get(to_column, '?')}: {e!s}")

        result = f"Batch email complete: {sent} sent, {failed} failed"
        if errors:
            result += "\nErrors:\n" + "\n".join(errors[:10])
        return result

    except Exception as e:
        return f"Error in batch email: {e!s}"


@tool(description="Preview how a templated email will look with data substitutions applied.")
async def preview_email(
    subject_template: str,
    body_template: str,
    data_file: str = "",
    sample_data: str = "",
    file_type: str = "auto",
) -> str:
    """Preview a templated email with sample data.

    Args:
        subject_template: Subject template with {placeholders}.
        body_template: Body template with {placeholders}.
        data_file: Path to data file for filling placeholders.
        sample_data: JSON string with sample values.
        file_type: csv, json, auto.
    """
    try:
        if data_file:
            pd = _load_pandas()
            if pd is None:
                return "Error: pandas not installed."
            if file_type == "auto":
                ext = os.path.splitext(data_file)[1].lower()
                file_type = "json" if ext == ".json" else "csv"
            df = pd.read_json(data_file) if file_type == "json" else pd.read_csv(data_file)
            row = df.iloc[0].to_dict()
        elif sample_data:
            row = json.loads(sample_data)
        else:
            row = {"name": "John Doe", "email": "john@example.com", "company": "Acme Corp"}

        subject = subject_template.format(**row)
        body = body_template.format(**row)

        return (
            f"=== EMAIL PREVIEW ===\n\n"
            f"Subject: {subject}\n\n"
            f"Body:\n{body}\n\n"
            f"======================"
        )
    except KeyError as e:
        return f"Error: Missing placeholder {e}. Available: {list(row.keys())}"
    except Exception as e:
        return f"Error previewing email: {e!s}"


@tool(description="Validate email address format and check if domain has valid MX records.")
async def validate_email(
    email: str,
    check_mx: bool = True,
) -> str:
    """Validate email address format and MX records.

    Args:
        email: Email address to validate.
        check_mx: Check DNS MX records for domain.
    """
    try:
        import re

        # Format validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return f"Invalid email format: {email}"

        domain = email.split("@")[1]

        if check_mx:
            try:
                import dns.resolver
                mx_records = dns.resolver.resolve(domain, "MX")
                mx_list = [str(r.exchange) for r in mx_records]
                return f"Valid email: {email}\nDomain: {domain}\nMX Records: {', '.join(mx_list)}"
            except ImportError:
                return f"Valid format: {email}\n(MX check requires dnspython: pip install dnspython)"
            except Exception:
                return f"Valid format: {email}\nWarning: No MX records found for {domain}"

        return f"Valid email format: {email}"
    except Exception as e:
        return f"Validation error: {e!s}"


@tool(description="Compose an email with a professional template. Generates a complete email from a brief description.")
async def compose_email(
    purpose: str,
    recipient_name: str = "",
    sender_name: str = "",
    tone: str = "professional",
    key_points: str = "",
    language: str = "en",
) -> str:
    """Compose an email using a template structure.

    Args:
        purpose: What the email is about (e.g., 'meeting request', 'follow up', 'thank you').
        recipient_name: Name of the recipient.
        sender_name: Name of the sender.
        tone: Tone of the email - professional, friendly, formal, casual.
        key_points: Bullet points to include (one per line).
        language: Output language (en, zh).
    """
    try:
        greetings = {
            "professional": f"Dear {recipient_name or 'Sir/Madam'},",
            "friendly": f"Hi {recipient_name or 'there'}!",
            "formal": f"Dear {recipient_name or 'Sir/Madam'},",
            "casual": f"Hey {recipient_name or 'there'}!",
        }

        closings = {
            "professional": f"Best regards,\n{sender_name or '[Your Name]'}",
            "friendly": f"Cheers,\n{sender_name or '[Your Name]'}",
            "formal": f"Sincerely,\n{sender_name or '[Your Name]'}",
            "casual": f"Later,\n{sender_name or '[Your Name]'}",
        }

        greeting = greetings.get(tone, greetings["professional"])
        closing = closings.get(tone, closings["professional"])

        body_parts = []
        if key_points:
            for point in key_points.split("\n"):
                point = point.strip()
                if point:
                    body_parts.append(f"- {point}")

        body_text = "\n".join(body_parts) if body_parts else f"[Add your message about: {purpose}]"

        email = f"Subject: {purpose.title()}\n\n{greeting}\n\n{body_text}\n\n{closing}"

        return f"=== Composed Email ===\n\n{email}"
    except Exception as e:
        return f"Error composing email: {e!s}"


@tool(description="Create an email signature with contact information, social links, and branding.")
async def create_email_signature(
    name: str,
    title: str = "",
    company: str = "",
    email: str = "",
    phone: str = "",
    website: str = "",
    linkedin: str = "",
    twitter: str = "",
    style: str = "simple",
) -> str:
    """Create a professional email signature.

    Args:
        name: Full name.
        title: Job title.
        company: Company name.
        email: Email address.
        phone: Phone number.
        website: Website URL.
        linkedin: LinkedIn profile URL.
        twitter: Twitter handle.
        style: Signature style - simple, professional, minimal.
    """
    try:
        if style == "simple":
            lines = [name]
            if title:
                lines.append(title)
            if company:
                lines.append(company)
            if email:
                lines.append(email)
            if phone:
                lines.append(phone)
            if website:
                lines.append(website)
            signature = "\n".join(lines)

        elif style == "minimal":
            parts = [name]
            if title and company:
                parts.append(f"{title} | {company}")
            elif title:
                parts.append(title)
            elif company:
                parts.append(company)
            contact = []
            if email:
                contact.append(email)
            if phone:
                contact.append(phone)
            if contact:
                parts.append(" | ".join(contact))
            if website:
                parts.append(website)
            signature = "\n".join(parts)

        else:  # professional
            lines = [
                "--",
                f"{name}",
            ]
            if title:
                lines.append(title)
            if company:
                lines.append(company)
            lines.append("")
            if email:
                lines.append(f"Email: {email}")
            if phone:
                lines.append(f"Phone: {phone}")
            if website:
                lines.append(f"Web: {website}")
            if linkedin:
                lines.append(f"LinkedIn: {linkedin}")
            if twitter:
                lines.append(f"Twitter: {twitter}")
            signature = "\n".join(lines)

        return f"=== Email Signature ({style}) ===\n\n{signature}"
    except Exception as e:
        return f"Error creating signature: {e!s}"


def _load_pandas():
    """Lazy-load pandas."""
    try:
        import pandas as pd
        return pd
    except ImportError:
        return None
