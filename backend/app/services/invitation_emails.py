from __future__ import annotations

from app.services.email import EmailMessage


def build_invitation_email(
    *,
    to_email: str,
    inviter_name: str,
    tenant_name: str,
    accept_url: str,
) -> EmailMessage:
    subject = f"You've been invited to join {tenant_name} on POSTIKA"

    text = (
        "Hello,\n\n"
        f"{inviter_name} invited you to join {tenant_name} on POSTIKA.\n\n"
        f"Accept invitation: {accept_url}\n\n"
        "If you did not expect this invitation, you can ignore this email.\n"
    )

    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.5;">
      <h2>You're invited to join <b>{tenant_name}</b> on POSTIKA</h2>
      <p><b>{inviter_name}</b> invited you to join their workspace.</p>
      <p>
        <a href="{accept_url}" style="display:inline-block;padding:10px 14px;text-decoration:none;border:1px solid #111;border-radius:8px;">
          Accept invitation
        </a>
      </p>
      <p style="color:#555;">If you did not expect this invitation, you can ignore this email.</p>
    </div>
    """

    return EmailMessage(
        to=to_email,
        subject=subject,
        html=html,
        text=text,
    )
