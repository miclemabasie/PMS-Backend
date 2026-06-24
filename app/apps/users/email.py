import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from djoser import email as djoser_email

logger = logging.getLogger(__name__)


class BaseDjoserEmail:
    """
    Base class for all Djoser emails using multipart (HTML + plain text).
    """

    template_name = None  # Must be overridden in subclasses

    def send(self, to, *args, **kwargs):
        if not self.template_name:
            raise ValueError("template_name must be set in subclass")

        # 1. Get context from Djoser (user, domain, protocol, url, etc.)
        context = self.get_context_data()

        # 2. Fix the URL if needed (add leading slash)
        url = context.get("url", "")
        if url and not url.startswith("/"):
            url = "/" + url
        context["url"] = url

        # 3. Build full link for plain text
        full_link = f"{context['protocol']}://{context['domain']}{url}"

        # 4. Render HTML template
        html_content = render_to_string(self.template_name, context)

        # 5. Create plain‑text version
        plain_text = strip_tags(html_content)
        plain_text += f"\n\nLink: {full_link}"

        # 6. Send email
        subject = self.get_subject()
        from_email = None  # uses DEFAULT_FROM_EMAIL
        to_email = to if isinstance(to, list) else [to]

        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_text,
            from_email=from_email,
            to=to_email,
        )
        msg.attach_alternative(html_content, "text/html")
        print("Context: ", context)
        try:
            msg.send(fail_silently=False)
            logger.info(f"{self.__class__.__name__} sent to {to}")
        except Exception as e:
            logger.error(f"{self.__class__.__name__} failed: {e}", exc_info=True)
            raise

    def get_subject(self):
        """
        Override to provide a subject. Djoser uses a default; we can define here.
        """
        return "Action required"


# ---- Djoser Email Subclasses ----


class CustomActivationEmail(BaseDjoserEmail, djoser_email.ActivationEmail):
    template_name = "emails/activation.html"

    def get_subject(self):
        return "Activate your account"


class CustomConfirmationEmail(BaseDjoserEmail, djoser_email.ConfirmationEmail):
    template_name = "emails/confirmation.html"

    def get_subject(self):
        return "Email confirmed"


class CustomPasswordResetEmail(BaseDjoserEmail, djoser_email.PasswordResetEmail):
    template_name = "emails/password_reset.html"

    def get_subject(self):
        return "Reset your password"


class CustomPasswordResetConfirmationEmail(
    BaseDjoserEmail, djoser_email.PasswordChangedConfirmationEmail
):
    template_name = "emails/password_reset_confirm.html"

    def get_subject(self):
        return "Password reset successful"


class CustomUsernameResetEmail(BaseDjoserEmail, djoser_email.UsernameResetEmail):
    template_name = "emails/username_reset.html"

    def get_subject(self):
        return "Reset your username"


class CustomUsernameResetConfirmationEmail(
    BaseDjoserEmail, djoser_email.UsernameChangedConfirmationEmail
):
    template_name = "emails/username_reset_confirm.html"

    def get_subject(self):
        return "Username reset successful"
