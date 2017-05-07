#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import web
import time
import types
import hashlib
import base64
import memcache
from lxml import etree
from datetime import datetime, timedelta


REQUEST_URLS = 'http://dreamtale90.ngrok.cc/heartbeat'


    time.sleep(0.5)

application = web.application(_URLS, globals())

if __name__ == "__main__":
    application.run()
