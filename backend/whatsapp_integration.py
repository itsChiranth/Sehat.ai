from flask import Flask, request, Response
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import requests
import os

app = Flask(__name__)

# Twilio credentials from environment variables
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Rasa chatbot REST API endpoint
RASA_WEBHOOK_URL = 'http://localhost:5005/webhooks/rest/webhook'

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    # Get incoming WhatsApp message body and sender
    user_msg = request.values.get('Body', '').strip()
    user_number = request.values.get('From')

    # Send message to Rasa REST webhook
    rasa_response = requests.post(
        RASA_WEBHOOK_URL,
        json={"message": user_msg}
    )

    # Prepare Twilio WhatsApp response
    resp = MessagingResponse()

    # Forward Rasa bot messages to WhatsApp
    for message in rasa_response.json():
        text = message.get('text')
        if text:
            resp.message(text)

    return Response(str(resp), mimetype="application/xml")

if __name__ == '__main__':
    app.run(port=5006)
