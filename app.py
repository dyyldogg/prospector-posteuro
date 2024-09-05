from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from anthropic import Anthropic
from dotenv import load_dotenv
import os
import csv
import io
import json
from flask_session import Session
import logging

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
Session(app)

logging.basicConfig(level=logging.INFO)

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY is not set in the environment variables")

print(f"API Key loaded: {'Yes' if ANTHROPIC_API_KEY else 'No'}")
print(f"API Key: {ANTHROPIC_API_KEY[:5]}...{ANTHROPIC_API_KEY[-5:]}")

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

def analyze_csv(csv_content):
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(csv_reader)
    total_entries = len(rows)
    email_count = 0
    phone_count = 0
    both_count = 0
    neither_count = 0

    for row in rows:
        has_email = bool(row.get('Email', '').strip())
        has_phone = bool(row.get('Phone', '').strip())
        if has_email and has_phone:
            both_count += 1
        elif has_email:
            email_count += 1
        elif has_phone:
            phone_count += 1
        else:
            neither_count += 1

    first_contact = rows[0] if rows else {}

    return {
        'total_entries': total_entries,
        'email_count': email_count,
        'phone_count': phone_count,
        'both_count': both_count,
        'neither_count': neither_count,
        'first_contact': first_contact
    }

@app.route('/')
def home():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    print("Debug - Upload function called")
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    try:
        csv_content = file.read().decode('utf-8')
        print(f"Debug - CSV content (first 100 chars): {csv_content[:100]}")
        analysis = analyze_csv(csv_content)
        print(f"Debug - CSV analysis result: {analysis}")

        agent_info = {
            'name': request.form.get('agentName'),
            'phone': request.form.get('agentPhone'),
            'email': request.form.get('agentEmail'),
            'website': request.form.get('agentWebsite'),
            'address': request.form.get('agentAddress')
        }

        session['csv_analysis'] = analysis
        session['agent_info'] = agent_info
        session['csv_content'] = csv_content
        session['workflow_step'] = 0
        session['user_responses'] = {}
        session.modified = True

        print("Debug - Session data after setting:")
        print(f"csv_analysis: {session.get('csv_analysis')}")
        print(f"agent_info: {session.get('agent_info')}")
        print(f"workflow_step: {session.get('workflow_step')}")

        return jsonify({'message': 'File uploaded and analyzed successfully'})
    except Exception as e:
        print(f"Debug - Error in upload_file: {str(e)}")
        return jsonify({'error': f'Error processing file: {str(e)}'})

def chat_with_claude(user_message, context):
    system_prompt = """
    You are an AI assistant specialized in helping real estate agents craft cold emails to potential clients. Your emails must feel personal and human, as if written by the agent themselves. Each email must reflect the agent's unique voice and style, while addressing the specific homeowner in a casual and approachable tone.

    When writing emails, always incorporate the following guidelines:
    1. Personalization: Leverage any available data from the CSV file (such as the homeowner's name, property details, and address). Make the email feel personalized, addressing the homeowner by their first name and referencing their specific property.
    2. Property Address: When mentioning the homeowner's property, casually reference the street number and name, without sounding too formal or intrusive.
    3. Pain Points: Identify potential pain points or challenges relevant to the specific homeowner.
    4. Agent's Introduction: Introduce the real estate agent briefly in one sentence, mentioning their experience or specialization.
    5. Solution Offering: Describe the agent's offering in one sentence, clearly stating how the agent can help.
    6. Call to Action: End the email with a light, non-pressuring call to action.
    7. Structure: Each email must follow this structure:
       - Subject Line: Write a subject line that sounds human, friendly, and less sales-y.
       - Body of Email: The email should be a short paragraph that gets straight to the point.

    Remember:
    - Be respectful of the homeowner's time.
    - Avoid sounding too salesy or formal.
    - Keep the tone friendly, professional, and approachable.
    - Make it clear how the agent can help them with their specific property situation.
    """

    full_prompt = f"{context}\n\nUser: {user_message}"

    try:
        response = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": full_prompt}
            ]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"Error details: {str(e)}")
        return f"Error communicating with Claude API: {str(e)}"

def extract_subject_and_body(message):
    lines = message.split('\n')
    subject = lines[0].replace('Subject:', '').strip()
    body = '\n'.join(lines[1:]).strip()
    return subject, body

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/get_analysis')
def get_analysis():
    return jsonify(session.get('csv_analysis', {}))

@app.route('/edit_template')
def edit_template():
    subject = session.get('email_subject', '')
    body = session.get('email_body', '')
    agent_info = session.get('agent_info', {})

    footer = f"""Best,

{agent_info.get('name', '')}

{format_phone_number(agent_info.get('phone', ''))}

{agent_info.get('email', '')}

{agent_info.get('website', '')}

{agent_info.get('address', '')}"""

    return render_template('edit_template.html', subject=subject, body=body, footer=footer)

def format_phone_number(phone):
    phone = ''.join(filter(str.isdigit, phone))
    if len(phone) == 10:
        return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"

@app.route('/save_template', methods=['POST'])
def save_template():
    logging.info("save_template route called")
    data = request.get_json()
    last_message = data.get('last_message', '')

    logging.info(f"Received last_message: {last_message}")

    # Use Claude API to extract subject and body
    subject, body = extract_subject_and_body_with_claude(last_message)

    logging.info(f"Extracted subject: {subject}")
    logging.info(f"Extracted body: {body}")

    session['email_subject'] = subject
    session['email_body'] = body
    session.modified = True

    logging.info(f"Session after saving: email_subject: {session.get('email_subject')}, email_body: {session.get('email_body')}")

    return jsonify({'success': True, 'message': 'Template saved successfully'})

def extract_subject_and_body_with_claude(last_message):
    system_prompt = """
    You are an AI assistant tasked with extracting the subject line and body of an email from a larger message. The message contains instructions, context, and the email itself. Your job is to identify and extract ONLY the subject line and the body of the email.

    Rules:
    1. Extract ONLY the subject line and body of the email. Do not include "Subject:" in the extracted text for the subject line.
    2. Do not include any other parts of the message, such as instructions or context.
    3. The subject line typically starts with "Subject:" and is on its own line.
    4. The body of the email is everything that follows the subject line, up until any closing remarks or signatures.
    5. Do not include any closing remarks, signatures, or footer information in the body.
    6. Never include the word "Subject:" or "Body:" any other instructions in the extracted text.

    Please respond with the extracted subject line and body, separated by '---'.
    """

    try:
        response = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": last_message}
            ]
        )
        extracted_text = response.content[0].text.strip()
        subject, body = extracted_text.split('---')
        return subject.strip(), body.strip()
    except Exception as e:
        logging.error(f"Error in extract_subject_and_body_with_claude: {str(e)}")
        return "", ""
    

def generate_personalized_emails(template_subject, template_body):
    csv_content = session.get('csv_content', '')
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    personalized_emails = []
    footer = session.get('email_footer', '')
    user_responses = session.get('user_responses', {})
    agent_info = session.get('agent_info', {})

    for row in csv_reader:
        if row.get('Email'):
            context = f"""
            You are an AI assistant tasked with personalizing email templates for real estate agents.
            Your job is to take the given email template and personalize it for each lead in the CSV file.

            CSV Entry:
            {json.dumps(row)}

            Email Template Subject:
            {template_subject}

            Email Template Body:
            {template_body}

            User's original request:
            Lead information: {user_responses.get('lead_info', '')}
            Message theme: {user_responses.get('message_theme', '')}
            Agent information: {user_responses.get('agent_info', '')}

            Agent Info:
            {json.dumps(agent_info)}

            Instructions:
            1. Stay very close to the format and content of the template.
            2. Only make changes to personalize the email for the specific lead.
            3. Use the lead's information from the CSV entry to personalize the email.
            4. Keep the same tone, style, and overall message as the original template.
            5. Do not add any new sections or significantly alter the structure of the email.
            6. Ensure the personalized email reads naturally and doesn't feel forced.
            7. Do not include any signature or footer information.

            Format your response as follows:
            Subject: [Personalized subject]

            [Personalized email body]
            """
            personalized_email = chat_with_claude("Personalize this email template", context)
            subject, body = extract_subject_and_body(personalized_email)
            body += "\n\n" + footer.strip()
            personalized_emails.append({
                'to': row['Email'],
                'subject': subject,
                'body': body
            })

    return personalized_emails


@app.route('/chat', methods=['POST'])
def chat():
    print("Debug - Chat function called")
    user_message = request.json['message']
    agent_info = session.get('agent_info', {})
    csv_analysis = session.get('csv_analysis', {})
    workflow_step = session.get('workflow_step', 0)
    user_responses = session.get('user_responses', {})

    print(f"Debug - Session data in chat function:")
    print(f"agent_info: {agent_info}")
    print(f"csv_analysis: {csv_analysis}")
    print(f"workflow_step: {workflow_step}")
    print(f"user_responses: {user_responses}")

    if workflow_step == 0:
        try:
            intro_message = f"""Hello! I'm Prospector AI, here to help you craft effective cold emails.

Analysis of your CSV file:
Total entries: {csv_analysis['total_entries']}
Entries with email: {csv_analysis['email_count']}
Entries with phone: {csv_analysis['phone_count']}
Entries with both: {csv_analysis['both_count']}
Entries with neither: {csv_analysis['neither_count']}

Can you provide more information about who these leads on the CSV file are, e.g. homeowners facing pre-foreclosure, recently divorced, empty nesters, or potential seller leads for your buyer?"""
            session['workflow_step'] = 1
            session.modified = True
            return jsonify({'responses': [intro_message], 'show_proceed': False})
        except KeyError as e:
            print(f"Debug - KeyError in intro_message: {str(e)}")
            intro_message = "Error: Unable to retrieve CSV analysis data. Please try uploading your file again."
            return jsonify({'responses': [intro_message], 'show_proceed': False})

    elif workflow_step == 1:
        user_responses['lead_info'] = user_message
        next_question = "What is the general message you are trying to say to these homeowners?"
        session['workflow_step'] = 2
        session.modified = True
        return jsonify({'responses': [next_question], 'show_proceed': False})

    elif workflow_step == 2:
        user_responses['message_theme'] = user_message
        next_question = "Would you like to provide any more information about yourself that would be relevant to the message, e.g. that you have been working in this neighborhood for a long time, you specialize in pre-foreclosure cases, etc?"
        session['workflow_step'] = 3
        session.modified = True
        return jsonify({'responses': [next_question], 'show_proceed': False})

    elif workflow_step == 3:
        user_responses['agent_info'] = user_message
        session['user_responses'] = user_responses

        first_contact = csv_analysis['first_contact']

        context = f"""
        Lead information: {user_responses['lead_info']}
        Message theme: {user_responses['message_theme']}
        Agent information: {user_responses['agent_info']}
        CSV Analysis: {json.dumps(csv_analysis)}
        Agent Info: {json.dumps(agent_info)}
        First Contact:
        - First Name: {first_contact.get('First Name', 'N/A')}
        - Last Name: {first_contact.get('Last Name', 'N/A')}
        - Email: {first_contact.get('Email', 'N/A')}
        - Phone: {first_contact.get('Phone', 'N/A')}
        - Address: {first_contact.get('Property Address', 'N/A')}

        Please create an email template using the provided information. Make sure to reference the first lead's details (name, address, etc.) in the email. The email should be personalized, addressing the homeowner by their first name and mentioning their specific property address. Remember to abbreviate the address to sound more casual. Keep the tone casual and human-like.
        """

        email_template = chat_with_claude("Please write an email template based on the provided information, ensuring to reference the first lead's details.", context)

        subject, body = extract_subject_and_body(email_template)

        response = f"""Here's a template based on the first contact in your CSV file:

Subject: {subject}

{body}

To refine this template, simply continue our conversation. When you're satisfied, click the green 'Proceed' button below to move to the editing page, where you can make final adjustments before sending personalized emails to your entire lead list."""

        session['email_subject'] = subject
        session['email_body'] = body
        session['workflow_step'] = 4
        session.modified = True
        return jsonify({'responses': [response], 'show_proceed': True})

    else:
        first_contact = csv_analysis['first_contact']
        context = f"""
        Lead information: {user_responses['lead_info']}
        Message theme: {user_responses['message_theme']}
        Agent information: {user_responses['agent_info']}
        CSV Analysis: {json.dumps(csv_analysis)}
        Agent Info: {json.dumps(agent_info)}
        First Contact:
        - First Name: {first_contact.get('First Name', 'N/A')}
        - Last Name: {first_contact.get('Last Name', 'N/A')}
        - Email: {first_contact.get('Email', 'N/A')}
        - Phone: {first_contact.get('Phone', 'N/A')}
        - Address: {first_contact.get('Property Address', 'N/A')}
        Previous email template: {user_message}

        Please refine the email template based on the user's feedback. Ensure that the first lead's details are still correctly referenced in the email. Remember to only use the street number and name when referring to the address, and keep the tone casual and human-like.
        """

        email_template = chat_with_claude(user_message, context)

        subject, body = extract_subject_and_body(email_template)

        response = f"""Here's your revised template:

Subject: {subject}

{body}

If you'd like to make more changes, just let me know. When you're ready to finalize and personalize this template for each lead, click the green 'Proceed' button below."""

        session['email_subject'] = subject
        session['email_body'] = body
        session.modified = True
        return jsonify({'responses': [response], 'show_proceed': True})


@app.route('/save_template_and_proceed', methods=['POST'])
def save_template_and_proceed():
    data = request.get_json()
    session['email_subject'] = data.get('subject', '')
    session['email_body'] = data.get('body', '')
    session['email_footer'] = data.get('footer', '')
    session.modified = True

    # Generate personalized emails
    personalized_emails = generate_personalized_emails(session['email_subject'], session['email_body'])
    session['personalized_emails'] = personalized_emails

    return jsonify({'success': True})

@app.route('/preview_all_emails')
def preview_all_emails():
    print("Debug - preview_all_emails route called")
    personalized_emails = session.get('personalized_emails', [])
    print(f"Debug - Number of personalized emails: {len(personalized_emails)}")
    return render_template('preview_emails.html', emails=personalized_emails)

@app.route('/update_email', methods=['POST'])
def update_email():
    data = request.get_json()
    index = data.get('index')
    field = data.get('field')
    value = data.get('value')

    personalized_emails = session.get('personalized_emails', [])
    if 0 <= index < len(personalized_emails):
        personalized_emails[index][field] = value
        session['personalized_emails'] = personalized_emails
        session.modified = True
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})

@app.route('/save_all_emails', methods=['POST'])
def save_all_emails():
    # Here you would implement the logic to save or send all the emails
    # For now, we'll just return success
    return jsonify({'success': True})

@app.route('/debug_session')
def debug_session():
    return jsonify(dict(session))

if __name__ == '__main__':
    print("Starting Flask application...")
    app.run(debug=True)
    print("Flask application has stopped.")
