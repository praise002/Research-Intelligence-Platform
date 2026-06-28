from dataclasses import dataclass

import jinja2
import resend
from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, MessageType
from mjml import mjml2html

from src.auth.config import conf
from src.config import settings

# NOTE: MOVE TO CELERY IF I REQUIRE RELIABILITY & SCALING

# Initialize Jinja2 environment for MJML templates
templates_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
    autoescape=True,
)

resend.api_key = settings.RESEND_API_KEY

def get_email_template_data(email_type: str) -> dict:
    """
    Returns the appropriate template file and subject based on email type.

    Args:
        email_type: Type of email ('welcome', 'test')

    Returns:
        dict: Contains 'template_name' and 'subject'
    """
    email_templates = {
        "welcome": {
            "template_name": "welcome_message.mjml",
            "subject": "Account Verified",
        },
        "test": {
            "template_name": "test_email.mjml",
            "subject": "Test Email",
        },
    }

    return email_templates.get(email_type, email_templates["welcome"])


def render_mjml_template(template_name: str, context: dict) -> str:
    """
    Renders an MJML template with Jinja2 and compiles it to HTML.
    """
    template = templates_env.get_template(template_name)
    mjml_content = template.render(**context)
    return mjml2html(mjml_content)


def  _send_via_fastmail(
    background_tasks: BackgroundTasks,
    subject: str,
    email_to: str,
    template_context: dict,
    template_name: str,
):
    """
    Send an email using FastMail after rendering MJML with Jinja2.

    Args:
        background_tasks: FastAPI BackgroundTasks instance
        subject: Email subject line
        email_to: Recipient email address
        template_context: Dictionary of variables for the template
        template_name: Name of the MJML template file
    """
    # 1-3. Render and compile MJML to HTML
    compiled_html = render_mjml_template(template_name, template_context)

    message = MessageSchema(
        subject=subject,
        recipients=[email_to],  # type: ignore
        body=compiled_html,
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    background_tasks.add_task(
        fm.send_message,
        message,
    )

def _send_via_resend(
    subject: str,
    email_to: str,
    html: str,
) -> None:
    """
    Sends via Resend API — used in production.
    Resend handles delivery, retries, and bounce tracking.
    FROM address must be a verified domain on your Resend account.
    """
    resend.Emails.send({
        "from": settings.RESEND_FROM_EMAIL,
        "to": email_to,
        "subject": subject,
        "html": html,
    })
    
def send_email(
    background_tasks: BackgroundTasks,
    subject: str,
    email_to: str,
    template_context: dict,
    template_name: str,
) -> None:
    """
    Renders the template and routes to the right provider based on environment.
 
    Production  → Resend (runs in background task to avoid blocking the request)
    Local/dev   → FastMail SMTP
    """
    compiled_html = render_mjml_template(template_name, template_context)
 
    if settings.ENVIRONMENT == "production":
        # Run Resend in a background task so it doesn't block the response
        background_tasks.add_task(_send_via_resend, subject, email_to, compiled_html)
    else:
        _send_via_fastmail(background_tasks, subject, email_to, compiled_html)

def send_email_by_type(
    background_tasks: BackgroundTasks,
    email_type: str,
    email_to: str,
    name: str,
    otp: str | None = None,
):
    """
    Simplified email sending function that uses email type to determine template and subject.

    Args:
        background_tasks: FastAPI BackgroundTasks instance
        email_type: Type of email ('activate', 'reset', 'reset-success', 'welcome')
        email_to: Recipient email address
        name: Recipient's first name
        otp: Optional OTP code for verification emails
    """
    email_data = get_email_template_data(email_type)

    # Build template context
    template_context = {
        "name": name,
        "project_name": settings.PROJECT_NAME,
        "frontend_host": settings.FRONTEND_HOST,
    }
    if otp:
        template_context["otp"] = str(otp)

    send_email(
        background_tasks,
        email_data["subject"],
        email_to,
        template_context,
        email_data["template_name"],
    )


@dataclass
class EmailData:
    html_content: str
    subject: str


def generate_test_email(email_to: str) -> EmailData:
    email_data = get_email_template_data("test")
    template_context = {
        "project_name": settings.PROJECT_NAME,
        "email": email_to,
    }

    html_content = render_mjml_template(email_data["template_name"], template_context)

    return EmailData(html_content=html_content, subject=email_data["subject"])
