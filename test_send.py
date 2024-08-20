import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def send_test_email():
    # Retrieve your API key from the environment variable
    api_key = os.getenv('SENDGRID_API_KEY')
    if not api_key:
        raise Exception("SENDGRID_API_KEY is not set in the environment variables.")

    # Create a Mail object
    message = Mail(
        from_email='dylanrochex@gmail.com',  # Replace with your SendGrid verified email
        to_emails='dylanrochex@gmail.com',  # Replace with the recipient's email
        subject='Thank you for aatending our open house',
        html_content='Dear Palisades Resident, we wanted to thank you for attending our open house and we hope to see you at the next one. - Dylan'
    )

    try:
        # Create a SendGrid client and send the email
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    send_test_email()
