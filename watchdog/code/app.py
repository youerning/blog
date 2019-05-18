from flask import Flask
import subprocess as sp
from datetime import datetime
from PIL import Image
from os import path
from flask import render_template
app = Flask(__name__)


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/watch")
def watch():
    cwd = path.dirname(path.abspath("__file__"))
    static_dir = path.join(cwd, "static")
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d-%H-%M-%S")
    # 拍摄的照片保存位置
    img_path = path.join(static_dir, "{}.jpeg".format(date_str))
    print(img_path)
    # 拼凑出latest.png文件路径
    latest_img_path = path.join(static_dir, "latest.jpeg")
    print(latest_img_path)
    cmd = "termux-camera-photo -c 0 {}".format(img_path)
    retcode = sp.call(cmd, shell=True)

    if retcode != 0:
        return "failed"

    img = Image.open(img_path)
    # 根据实际图片压缩，自己测试
    new_img = img.resize((int(img.size[0] * 0.4), int(img.size[1] * 0.4)))
    try:
        new_img.save(latest_img_path)
    except Exception as e:
        print(e)
        return "failed"
    return "ok"


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
