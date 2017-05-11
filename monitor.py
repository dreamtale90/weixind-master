#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import urllib2
import subprocess, signal
from datetime import datetime, timedelta


REQUEST_URLS = 'http://dreamtale90.ngrok.cc/heartbeat'


def send_request():
    req = urllib2.Request(REQUEST_URLS)

    try:
        for i in range(3):
            response = urllib2.urlopen(req)
            result = response.read()

            #check result
            if result == 'OK4LIVE':
                return True

    except urllib2.URLError, e:
        print e.reason

    return False


def kill_proc_by_name(ProcName):
    p = subprocess.Popen(['ps', '-A'], stdout = subprocess.PIPE)
    out, err = p.communicate()

    for line in out.splitlines():
        if ProcName in line:
            pid = int(line.split(None, 1)[0])
            os.kill(pid, signal.SIGKILL)
            return True

    curTime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    print '[%s] %s process is not exist !' %(curTime, ProcName)
    return False


def check_loop():
    while True:

        time.sleep(60)

        #send a request
        send_ret = send_request()

        if send_ret == False:
            curTime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
            print '[%s] http server not respond !' %curTime
            #kill ngrok process
            kill_ret = kill_proc_by_name('sunny')

            if kill_ret == False:
                #reboot
                os.system('reboot')


if __name__ == '__main__':
    check_loop()
