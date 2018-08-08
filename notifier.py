#!/usr/bin/env python
"""
This implements a notification system via email
"""
import json
import smtplib
from email.mime.text import MIMEText

# note this requires a secrets file to work
required = ['sender_email', 'sender_pass']

class Notifier():
    def __init__(self, secrets_json, target_email, subject_fmt, message_fmt, sender_name):
        self.target_email = target_email
        self.subject_fmt = subject_fmt
        self.message_fmt = message_fmt
        self.sender_name = sender_name

        with open(secrets_json) as fp:
            self.secrets = json.load(fp)

        for req in required:
            if req not in self.secrets:
                raise ValueError("Missing required secrets")

    def send(self, subject_fill, greeting, message_body):
        # assemble from template
        with open("simpler_email_template.html", 'r') as fp:
            msg = MIMEText(fp.read(), 'html')

        msg['Subject'] = self.subject_fmt.format(subject_fill)
        msg['From'] = self.sender_name
        msg['To'] = self.target_email

        body = msg.get_payload()
        #body = body.replace('_PREHEADER_',
        body = body.replace('_GREETING_', greeting)
        #body = body.replace('_P1_', self.message_fmt.format(message_body))
        body = body.replace('_HTML_BLOB_', message_body)
        #body = body.replace('_P3_',
        msg.set_payload(body)

        # send via gmail
        sender_email = self.secrets['sender_email']
        sender_pass = self.secrets['sender_pass']
        server = smtplib.SMTP('smtp.gmail.com',587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, [self.target_email], msg.as_string())
        server.close()
        return msg

def test_main():
    n = Notifier('secrets.json', '',
            'New @Schubar Order - {}',
            'A customer as ordered:\n{}',
            'Mix-Mind @Schubar')

    n.send('Martini', "Martini:\n1.5oz gin\n.5oz vermouth\n")

if __name__ == "__main__":
    test_main()
