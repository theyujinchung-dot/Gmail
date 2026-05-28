import os
import json

if os.path.exists('token.json'):
    with open('token.json', 'r') as f:
        print("\n=== COPY EVERYTHING BELOW FOR GMAIL_TOKEN ===")
        print(f.read())
        print("=== END OF GMAIL_TOKEN ===\n")

if os.path.exists('credentials.json'):
    with open('credentials.json', 'r') as f:
        print("=== COPY EVERYTHING BELOW FOR GMAIL_CREDENTIALS ===")
        print(f.read())
        print("=== END OF GMAIL_CREDENTIALS ===\n")