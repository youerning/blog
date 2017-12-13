from __future__ import print_function
import falcon
from wsgiref import simple_server
from email.mime.text import MIMEText
import smtplib
import json


smtpServer = "mx.example.com"
smtpUser = "sender@example.com"
smtpPass = "password"
sender = "sender@example.com"
reciver = "reciver@example.com"


tpl = """
status: {status}
alerts: {alerts}
"""

def sendMail(reciver, subject, message):
    server = smtplib.SMTP(smtpServer, 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(smtpUser, smtpPass)
    server.set_debuglevel(1)
    msg = MIMEText(message, "plain", "utf8")
    msg["Subject"] = subject
    server.sendmail(sender, [reciver], msg.as_string())
    server.quit()


class WebHook(object):
    def on_post(self, req, resp):
        """Handles GET requests"""
        body = req.stream.read()
        postData = json.loads(body.decode('utf-8'))
        msg = tpl.format(**postData)
        print(msg)
        sendMail(reciver, "alert", msg)
        resp.status = falcon.HTTP_200  # This is the default status
        resp.body = "OK"


app = falcon.API()
app.add_route('/', WebHook())
if __name__ == '__main__':
    httpd = simple_server.make_server('0.0.0.0', 80, app)
    httpd.serve_forever()
