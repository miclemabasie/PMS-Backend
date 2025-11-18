import os
from django.core.management.base import BaseCommand
from django.conf import settings

from apps.notifications.models import (
    EmailConfiguration,
    NotificationTemplate,
    TemplateType,
)


class Command(BaseCommand):
    help = "Set up default email configuration and templates from environment variables or defaults."

    def handle(self, *args, **options):
        self.stdout.write("Setting up default email configuration...")

        # --- Email Configuration from environment ---
        host = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
        port = int(os.environ.get("EMAIL_PORT", 587))
        username = os.environ.get("EMAIL_HOST_USER", "")
        password = os.environ.get("EMAIL_HOST_PASSWORD", "")
        from_email = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@example.com")
        use_tls = os.environ.get("EMAIL_USE_TLS", "True").lower() == "true"

        # Deactivate any existing config and create new one
        EmailConfiguration.objects.update(is_active=False)
        config = EmailConfiguration.objects.create(
            name="Default SMTP",
            host=host,
            port=port,
            username=username,
            password=password,
            from_email=from_email,
            use_tls=use_tls,
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS(f"Created email configuration: {config}"))

        # --- Default Email Templates ---
        self.stdout.write("Creating default notification templates...")

        # 1. Welcome Email
        welcome_template, created = NotificationTemplate.objects.get_or_create(
            name="welcome_email",
            defaults={
                "description": "Welcome email sent to new users upon registration.",
                "type": TemplateType.EMAIL,
                "subject": "Welcome to {{ site_name }}!",
                "template": """
Hello {{ user.first_name }},

Welcome to {{ site_name }}! We're thrilled to have you on board.

You can log in with your email: {{ user.email }}

Best regards,
The {{ site_name }} Team
                """.strip(),
                "html_template": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Welcome to {{ site_name }}</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
        <h2 style="color: #4CAF50;">Welcome, {{ user.first_name }}!</h2>
        <p>Thank you for joining <strong>{{ site_name }}</strong>. We're thrilled to have you on board.</p>
        <p>You can log in with your email: <strong>{{ user.email }}</strong></p>
        <p>If you have any questions, feel free to reply to this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #777; font-size: 12px;">&copy; {{ year }} {{ site_name }}. All rights reserved.</p>
    </div>
</body>
</html>
                """.strip(),
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Created template: {welcome_template.name}")
            )
        else:
            self.stdout.write(
                f"Template '{welcome_template.name}' already exists, skipping."
            )

        # 2. Password Reset Email
        reset_template, created = NotificationTemplate.objects.get_or_create(
            name="password_reset",
            defaults={
                "description": "Password reset email.",
                "type": TemplateType.EMAIL,
                "subject": "Password Reset Request",
                "template": """
Hello {{ user.first_name }},

You requested a password reset for your account at {{ site_name }}.

Please click the link below to reset your password:
{{ reset_link }}

If you did not request this, please ignore this email.

Thanks,
The {{ site_name }} Team
                """.strip(),
                "html_template": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Password Reset</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
        <h2 style="color: #333;">Password Reset Request</h2>
        <p>Hello {{ user.first_name }},</p>
        <p>You requested a password reset for your account at <strong>{{ site_name }}</strong>.</p>
        <p style="margin: 30px 0;">
            <a href="{{ reset_link }}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">Reset Password</a>
        </p>
        <p>If the button above doesn't work, copy and paste this link into your browser:</p>
        <p style="word-break: break-all;"><a href="{{ reset_link }}">{{ reset_link }}</a></p>
        <p>If you did not request this, please ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #777; font-size: 12px;">&copy; {{ year }} {{ site_name }}. All rights reserved.</p>
    </div>
</body>
</html>
                """.strip(),
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Created template: {reset_template.name}")
            )
        else:
            self.stdout.write(
                f"Template '{reset_template.name}' already exists, skipping."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Email configuration and default templates setup complete."
            )
        )
