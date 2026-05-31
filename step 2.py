import os
import base64
import pandas as pd
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# --- PHASE 0: AUTHENTICATION (ENVIRONMENT VARIABLES) ---
token_data = os.environ.get('GMAIL_TOKEN')
creds_data = os.environ.get('GMAIL_CREDENTIALS')

if token_data and creds_data:
    # Recreate the json files temporarily inside GitHub's cloud container
    print("Cloud keys detected. Authenticating...")
    with open('token.json', 'w') as f:
        f.write(token_data)
    with open('credentials.json', 'w') as f:
        f.write(creds_data)
    creds = Credentials.from_authorized_user_file('token.json')
else:
    # Local PC fallback rule
    print("No cloud keys found. Falling back to local files...")
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')
    else:
        from google_auth_oauthlib.flow import InstalledAppFlow
        SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0, prompt='consent')

service = build('gmail', 'v1', credentials=creds)

# --- PHASE 1: RETRIEVAL ---
print("Searching for the warehouse email...")
query = 'subject:"Warehouse"'
results = service.users().messages().list(userId='me', q=query).execute()
messages = results.get('messages', [])

if not messages:
    print("No matching emails found.")
else:
    msg = service.users().messages().get(userId='me', id=messages[0]['id']).execute()
    parts = msg['payload'].get('parts', [])
    for part in parts:
        if part['filename']:
            attachment_id = part['body'].get('attachmentId')
            attachment = service.users().messages().attachments().get(
                userId='me', messageId=msg['id'], id=attachment_id).execute()
            
            file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
            with open('raw_report.csv', 'wb') as f:
                f.write(file_data)
            print(f"Successfully downloaded: {part['filename']}")

# --- PHASE 2: DATA TRANSFORMATION ---
if os.path.exists('raw_report.csv'):
    print("\nApplying Multipliers...")
    df = pd.read_csv('raw_report.csv')

    df['AD_UNIT_ID'] = pd.to_numeric(df['AD_UNIT_ID'], errors='coerce')
    df = df[df['AD_UNIT_ID'].notna()]
    df = df[df['AD_UNIT_NAME_ALL_LEVEL'] != 'TOTAL']

    cols_to_fix = ['IMPRESSIONS', 'CODE_SERVED_COUNT', 'CLICKS', 'AD_EXCHANGE_REVENUE']
    for col in cols_to_fix:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace('[$,]', '', regex=True), errors='coerce').fillna(0)

    df['IMPRESSIONS'] = df['IMPRESSIONS'] * 0.40
    df['CODE_SERVED_COUNT'] = df['CODE_SERVED_COUNT'] * 0.40
    df['CLICKS'] = df['CLICKS'] * 0.25
    df['AD_EXCHANGE_REVENUE'] = df['AD_EXCHANGE_REVENUE'] * 0.65

    df.to_csv('modified_report.csv', index=False)

    # --- PHASE 4: AUTOMATED SENDING ---
    print("\nSending email to James...")
    recipient = "jamesjch@gmail.com"
    message = MIMEMultipart()
    message['to'] = recipient
    message['subject'] = 'Modified Warehouse Report - Cloud Automated'
    message.attach(MIMEText("Please find the modified warehouse report attached.", 'plain'))

    with open("modified_report.csv", "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment; filename= modified_report.csv")
        message.attach(part)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
    print(f"Email successfully sent to {recipient}!")
else:
    print("Error: Could not find raw_report.csv.")

print("\nDone!")
