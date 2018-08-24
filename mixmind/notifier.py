#!/usr/bin/env python
"""
This implements a notification system via email
"""
import json
import smtplib
from email.mime.text import MIMEText

from flask import render_template
from flask_mail import Mail, Message
mail = Mail()

from . import app

def send_mail(subject, recipient, template, **context):
    """Send an email via the Flask-Mail extension.

    :param subject: Email subject
    :param recipient: Email recipient
    :param template: The name of the email template
    :param context: The context to render the template with
    """
    msg = Message(subject, sender=app.config.get('MAIL_USERNAME'), recipients=[recipient])

    ctx = ('email', template)
    msg.html = render_template('%s/%s.html' % ctx, **context)
    mail.send(msg)


# note this requires a secrets file to work
required = ['sender_email', 'sender_pass', 'sender_name', 'target_email']

class Notifier():
    def __init__(self, secrets_json, message_template):
        with open(secrets_json) as fp:
            self.secrets = json.load(fp)
        for req in required:
            if req not in self.secrets:
                raise ValueError("Missing required secrets")

        self.sender_email = self.secrets['sender_email']
        self.sender_pass = self.secrets['sender_pass']
        self.sender_name = self.secrets['sender_name']
        self.target_email = self.secrets['target_email']

        with open(message_template) as fp:
            self.message_template = fp.read()

    def send(self, subject_line, message_fill, alt_target=None):
        """ message_fill should be a dict with keys
        matching fill fields in the base html template
        """
        target_email = alt_target if alt_target else self.target_email
        # assemble from template
        msg = MIMEText(self.message_template, 'html')
        msg['Subject'] = subject_line
        msg['From'] = self.sender_name
        msg['To'] = target_email

        body = msg.get_payload()
        for key, value in message_fill.iteritems():
            body = body.replace(key, value)
        msg.set_payload(body)

        # send via gmail
        server = smtplib.SMTP('smtp.gmail.com',587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(self.sender_email, self.sender_pass)
        server.sendmail(self.sender_email, [target_email], msg.as_string())
        server.close()
        return msg

def test_main():
    n = Notifier('secrets.json', 'simpler_email_template.html')
    n.send("A customer has ordered - Martini",
            {
                '_GREETING_': 'Hi',
                '_SUMMARY_': "Person has ordered a Martini",
                '_RECIPE_': "Martini Recipe.\n.\n.\n.",
                '_EXTRA_': """<table>
    <tr>
        <td style="background-color: #4ecdc4;border-color: #4c5764;border: 2px solid #45b7af;padding: 10px;text-align: center;">
            <a style="display: block;color: #ffffff;font-size: 12px;text-decoration: none;text-transform: uppercase;" href="http://localhost:8888">
                Click me
            </a>
        </td>
    </tr>
</table>"""
            })

if __name__ == "__main__":
    test_main()
