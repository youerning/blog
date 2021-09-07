from os import path

import yaml


CONFIG_PATH = "app.yaml"
cur_dir = path.dirname(path.abspath(__file__))
with open(path.join(cur_dir, CONFIG_PATH)) as rf:
    Config = yaml.load(rf, Loader=yaml.Loader)
