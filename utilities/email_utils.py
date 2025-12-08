
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

SENDER_EMAIL = "saminathan@innoboon.com"
SENDER_PASSWORD = "niqr cubm ztko mshp"   # smtp password (app password)


def send_welcome_email(to_email: str, username: str):
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = "Welcome to Our Platform!"

        body = f"""
        <h3>Hello {username},</h3>
        <p>Your account was successfully created.</p>
        """

        msg.attach(MIMEText(body, "html"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()

        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()

    except Exception as e:
        print("Email sending failed:", e)
        raise Exception("Email sending failed")

# sending status email from routers once place_order executed
def send_order_status_email(to_email: str, username: str, order_id: int, status: str):
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = f"Order #{order_id} Status Update"

        body = f"""
        <h3>Hello {username},</h3>
        <p>Your order with Order ID: <strong>{order_id}</strong> is now <strong>{status}</strong>.</p>
        <p>Nandri meendum varuga! {username}, Ungal varugai engaluku perumai.</p>
        """

        msg.attach(MIMEText(body, "html"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()

        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()

    except Exception as e:
        print("Email sending failed:", e)
        raise Exception("Email sending failed") 
    
# order status admin mathina inga call panunga
def send_order_change_status_email(to_email: str, username: str, order_id: int, new_status: str):
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = f"Order #{order_id} Status Update"

        body = f"""
        <h3>Hello {username},</h3>
        <p>Your order with Order ID: <strong>{order_id}</strong> is changed to <strong>{new_status}</strong>.</p>
        <p> Status maariruchungo.</p>
        """

        msg.attach(MIMEText(body, "html"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()

        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()

    except Exception as e:
        print("Email sending failed:", e)
        raise Exception("Email sending failed") 
    
    