from google_auth_oauthlib.flow import InstalledAppFlow
import os

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        'gmail_credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)

    with open('gmail_token.json', 'w') as token:
        token.write(creds.to_json())
    print("✅ Token saved to gmail_token.json")

if __name__ == '__main__':
    main()
