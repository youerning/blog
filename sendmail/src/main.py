# -*- coding: UTF-8 -*-
# @author youerning
# @email 673125641@qq.com

import sys
import base64
import smtplib 
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from collections import defaultdict
from io import BytesIO
from os import path


# 第三方库
from jinja2 import Template
from PIL import Image


# 发送邮件所需的信息
mail_to = "<收件人邮箱地址>"
smtp_host = "<邮件服务器>"
smtp_username = "<用户名>"
smtp_password = "<密码>"
subject = "演示邮件"
from_ = "邮件机器人"


# 用于发个收件人的逗号
COMMASPACE = ","

EMAIL_TEMPLATE = """<html>
<head>
    <style type="text/css">
        table
        {
            border-collapse: collapse;
            margin: 0 auto;
            text-align: center;
        }
 
        table td, table th
        {
            border: 1px solid #cad9ea;
            color: #666;
            height: 30px;
        }
 
        table thead th
        {
            background-color: #CCE8EB;
            width: 100px;
        }
 
        table tr:nth-child(odd)
        {
            background: #fff;
        }
 
        table tr:nth-child(even)
        {
            background: #F5FAFA;
        }
    </style> 
</head>
<body>
<p>一共有以下{{record_size}}条数据</p>
<table width="90%" class="table">
    <thead>
        <tr>
        {% for label in labels %}
            <th>{{label}}</th>
        {% endfor %}
        </tr>
    </thead>
    <tbody>
{% for item in items %}
    <tr>
    {% for value in item %}
        <td>{{value}}</td>
    {% endfor %}
    </tr>
{% endfor %}
    </tbody>
</table>
</html>"""


EMAIL_IMAGE_TEMPLATE = """<html>
<head>
<title>Page Title</title>
</head>
<body>
<h3>这是一张图片</h3>
<p><img src="cid:{{image_name}}" height="112" width="200" ></p>
</body>
</html>
"""

EMAIL_ONLINE_IMAGE_TEMPLATE = """<html>
<head>
<title>Page Title</title>
</head>
<body>
<h3>这是一张图片</h3>
<p><img src="cid:{{image_name}}" ></p>
</body>
</html>
"""


def create_image_eamil_contant(fp):
    tpl = Template(EMAIL_IMAGE_TEMPLATE)
    if not path.exists(fp):
        sys.exit("要发送的本地图片不存在")

    msg = MIMEMultipart("related")
    image_name = "demo"

    with open(fp, "rb") as rf:
        mime_image = MIMEImage(rf.read())
        # 注意: 一定需要<>括号
        mime_image.add_header("Content-ID", "<%s>" % image_name)
        msg.attach(mime_image)

    # 渲染邮件文本内容
    text = tpl.render(image_name=image_name)
    msg_alternative = MIMEMultipart("alternative")
    msg_alternative.attach(MIMEText(text, "html", "utf-8"))

    msg.attach(msg_alternative)

    return msg


def create_online_image_content():
    from PIL import Image

    tpl = Template(EMAIL_ONLINE_IMAGE_TEMPLATE)
    fp = "demo_base64.txt"
    if not path.exists(fp):
        sys.exit("要发送的base64编码的图片不存在")

    msg = MIMEMultipart("related")
    image_name = "demo"

    with open(fp, "rb") as rf:
        base64_data = rf.read()
        img_data = base64.b64decode(base64_data)
        # 因为open方法需要一个file-like文件对象，而我们解码后的对象类型是bytes类型
        # bytes类型没有文件对象的read, close方法，所以我们需要通过BytesIO对象包装一下，它会返回一个file-like文件对象
        img = Image.open(BytesIO(img_data))
        img_width, img_height = img.size

        repeat_times = 5
        # compose images
        ret_img  = Image.new(img.mode, (img_width, img_height * repeat_times))
        for index in range(repeat_times):
            ret_img.paste(img, box=(0, index * img_height))

        # 因为MIMEImage需要一个bytes对象，所以们需要获取图片编码后的二进制数据而不是图片的array数据
        img_bytes = BytesIO()
        # 如果不指定图片格式，会因为没有文件名而报错
        ret_img.save(img_bytes, "png")

        mime_image = MIMEImage(img_bytes.getvalue())
        # 注意: 一定需要<>括号
        mime_image.add_header("Content-ID", "<%s>" % image_name)
        msg.attach(mime_image)

    # 渲染邮件文本内容
    text = tpl.render(image_name=image_name)
    msg_alternative = MIMEMultipart("alternative")
    msg_alternative.attach(MIMEText(text, "html", "utf-8"))

    msg.attach(msg_alternative)

    return msg


def create_html_content():
    tpl = Template(EMAIL_TEMPLATE)

    record_size = 10
    label_size = 5
    labels = ["label-%s" % i for i in range(label_size)]
    items = []

    for _ in range(record_size):
        item = ["item-%s" % value_index for value_index in range(label_size)]
        items.append(item)

    text = tpl.render(record_size=record_size, items=items, labels=labels)
    msg = MIMEText(text, "html", "utf-8")
    return msg


def send_email(msg, mail_to, smtp_host, smtp_username, smtp_password, subject, from_):
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = Header(from_, "utf-8")
    if not isinstance(mail_to, list):
        mail_to = [mail_to]
    msg["To"] = COMMASPACE.join(mail_to)

    try:
        print("准备连接smtp邮件服务器: %s" % smtp_host)
        client = smtplib.SMTP(smtp_host)
        print("连接成功")
        # client = smtplib.SMTP("localhost")
        # client.set_debuglevel(1)
        # print(self.mail_user, self.mail_pass)
        client.login(smtp_username, smtp_password)
        print("登录成功")
        # print("=====>", self.mail_from, mail_to)
        print("通过邮箱[%s]发送邮件给 %s" % (smtp_username, COMMASPACE.join(mail_to)))
        client.sendmail(smtp_username, mail_to, msg.as_string())
        print("发送成功...")
        return True
    except Exception:
        print("发送邮件失败")
    finally:
        client.quit()


def send_local_image_email():
    msg = create_image_eamil_contant("demo.jpg")
    send_email(msg,mail_to, smtp_host, smtp_username, smtp_password, subject, from_)


def send_online_image_email():
    msg = create_online_image_content()
    send_email(msg,mail_to, smtp_host, smtp_username, smtp_password, subject, from_)

def send_html_content():
    msg = create_html_content()
    send_email(msg,mail_to, smtp_host, smtp_username, smtp_password, subject, from_)


def main():
    pass


if __name__ == "__main__":
    # send_local_image_email()
    # send_online_image_email()
    send_html_content()