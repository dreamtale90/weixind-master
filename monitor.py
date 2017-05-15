#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import urllib2
import subprocess, signal
from datetime import datetime, timedelta


REQUEST_URLS = 'http://dreamtale90.ngrok.cc/heartbeat'


def my_print(data):
    curTime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    print '[%s] %s' %(curTime, data)


def send_request():
    req = urllib2.Request(REQUEST_URLS)

    for i in range(3):
        try:
            response = urllib2.urlopen(req)
            result = response.read()

        except urllib2.URLError, e:
            my_print(e.reason)

        #check result
        if result == 'OK4LIVE':
            return True

    return False


def kill_proc_by_name(ProcName):
    p = subprocess.Popen(['ps', '-A'], stdout = subprocess.PIPE)
    out, err = p.communicate()

    for line in out.splitlines():
        if ProcName in line:
            pid = int(line.split(None, 1)[0])
            os.kill(pid, signal.SIGKILL)
            return True

    my_print(ProcName + ' process is not exist !')
    return False


def check_loop():
    while True:

        time.sleep(60)

        #send a request
        send_ret = send_request()

        if send_ret == False:
            my_print('http server not respond !')
            #kill ngrok process
            kill_ret = kill_proc_by_name('sunny')

            if kill_ret == False:
                #reboot
                os.system('reboot')


if __name__ == '__main__':
    check_loop()
