from app.core.celery_app import celery
from app.services.email.email_sender import send_email


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_kwargs={"max_retries": 3})
def send_verification_code_task(self, email: str, code: str) -> None:
    send_email(
        to=email,
        subject="Verify your POSTIKA account",
        body=f"Your verification code is: {code}"
    )
