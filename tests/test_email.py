# test_email.py
from utils.email_utils import send_error_email

if __name__ == "__main__":
    subject = "📧 Test Email from Calendar Bot"
    body    = "This is a test of the Gmail-OAuth email notification."
    send_error_email(subject, body)
    print("Sent test email (check your inbox).")
