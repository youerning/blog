# -*- coding: UTF-8 -*-
# @author youerning
# @email 673125641@qq.com
import os
from config import Config

import yaml
from motor.motor_asyncio import AsyncIOMotorClient


host, port = Config["MONGODB"]["HOST"], Config["MONGODB"]["PORT"]
db, collection = Config["MONGODB"]["DB"], Config["MONGODB"]["COLLECTION"]
client = AsyncIOMotorClient(host, port)
database = client[db]
collection = database[collection]