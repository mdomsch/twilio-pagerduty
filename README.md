This is a simple application that uses Twilio to receive a phone call,
prompts the user to select the service for which this error report is
about, record a message from the user, and then raise an alert in
PagerDuty with this information. This is a python 3.6 application,
using Flask as the web framework. This application uses Zappa to
deploy into AWS Lambda & API Gateway.

Inspired by https://www.pagerduty.com/blog/triggering-an-alert-from-a-phone-call-code-sample/

This assumes you have a ~/.aws/credentials file with a [dev] section.

After initial git clone, you must initialize a Python 3.6 virtual
environment, then use Zappa to do the deployment.

```
$ git checkout <path>
$ virtualenv-3.6 twilio-pagerduty
$ cd twilio-pagerduty
$ . bin/activate
$ pip install -r requirements.txt
[edit zappa_settings.json]
$ zappa deploy dev
```
Copy the resulting deployment URL into Twilio phone number web hook configuration.

Twilio calls our application at each step of the process.  Our
application calls out to the PagerDuty REST API to create a new
incident.

There are low-value secrets as plaintext in the zappa_settings.json file.

1.  FLASK_SECRET_KEY is a "random" string used to protect the HTTP
cookie stored between REST calls.  This needs to be the same between
all AWS Lambda function instances in a single deployment, but can be
changed, and the app redeployed, at any time.  Twilio stores the
cookies, and automatically expires the cookies after 4 hours.

2.  APP#_PAGERDUTY_SERVICE_KEY application integration keys.  These are created in
the PagerDuty configuration for each application.  These can be
deleted in PagerDuty and re-created at any time.
