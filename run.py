import json
import logging
import os
import urllib3
import uuid
from flask import Flask, request, redirect, session, url_for
from twilio.twiml.voice_response import VoiceResponse, Gather
from urllib.parse import unquote

PAGERDUTY_SERVICE_KEY={"1": os.environ.get('APP1_PAGERDUTY_SERVICE_KEY'),
                       "2": os.environ.get('APP2_PAGERDUTY_SERVICE_KEY')}

app = Flask(__name__)
app.config.from_object(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'secret')

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@app.route("/", methods=['GET', 'POST'])
def greeting():

    resp = VoiceResponse()
    # Gather digits.
    g = Gather(numDigits=1, action=url_for("handle_key"), method="POST")
    g.say("""
    You have reached the alert line.
    By selecting a service and leaving a message, the on-call
    team will be alerted.
    """)
    g.say("""
    For an issue with App 1, press 1.
    For an issue with App 2, press 2.
    Press any other key to start over.
    """)
    resp.append(g)

    return str(resp)

def record_prompt():
    resp = VoiceResponse()
    resp.say("""
    Record your message after the tone.
    Please include your name, phone number, and
    description of the problem being reported.
    Press any key when finished.
    """)
    resp.record(maxLength="120", action=url_for("handle_recording"))
    return resp


@app.route("/handle-key", methods=['GET', 'POST'])
def handle_key():
    """Handle key press from a user."""
    digit_pressed = request.values.get('Digits', None)
    if digit_pressed not in ("1", "2"):
        return redirect(url_for("greeting"))
    session['digit_pressed'] = digit_pressed
    resp = record_prompt()
    return str(resp)


def pagerduty_incident(digit_pressed, details):
    message = """
    Caller Name       : %s
    Caller Phone #    : %s
    Caller City       : %s
    Caller State      : %s
    Caller Zip Code   : %s
    Caller Country    : %s
    Recording URL     : %s
    Recording Duration: %s seconds
    """ % (details.get('CallerName'),
           details.get('Caller'),
           details.get('CallerCity'),
           details.get('CallerState'),
           details.get('CallerZip'),
           details.get('CallerCountry'),
           details.get('RecordingUrl'),
           details.get('RecordingDuration')
    )

    incident = {
        "service_key": PAGERDUTY_SERVICE_KEY[digit_pressed],
        "event_type": "trigger",
        "incident_key": details.get('RecordingUrl'),
        "description": "Quest Internal Helpdesk Escalation",
        "details": {"Voicemail Details": message}
    }

    http = urllib3.PoolManager()
    try:
        r = http.request("POST", "http://events.pagerduty.com/generic/2010-04-15/create_event.json",
                         body=json.dumps(incident),
                         headers={'Content-Type': 'application/json'},
                         retries=4)
        logger.info(incident)
        return True
    except (urllib3.exceptions.HTTPError, urllib3.exceptions.URLError) as e:
        logger.warn(e)
        return False

@app.route("/handle-recording", methods=['GET', 'POST'])
def handle_recording():
    """Send recording to Pagerduty"""

    digit_pressed = session.get('digit_pressed', None)

    if digit_pressed is None:
        return redirect(url_for("greeting"))

    rc = pagerduty_incident(digit_pressed, request.values)

    resp = VoiceResponse()
    if not rc:
        resp.say("An error occurred. The team has not been alerted. Please try again.")
        return redirect(url_for("greeting"))

    resp.say("Thank you. The team has been alerted. Goodbye.")
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
