#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:     weixind.py

import os
import web
import time
import json
import types
import hashlib
import base64
import memcache
import threading
from lxml import etree
from datetime import datetime, timedelta
from multiprocessing import Process, Manager

from weixin import WeiXinClient
from weixin import APIError
from weixin import AccessTokenError
from sakshat import SAKSHAT
#import raspberry


#Declare the SAKS Board
SAKS = SAKSHAT()

# 在这里设定闹钟定时时间
__alarm_time = [07, 30, 00]
__alarm_beep_status = False


#在检测到轻触开关触发时自动执行此函数
def tact_event_handler(pin, status):
    '''
    called while the status of tacts changed
    :param pin: pin number which stauts of tact is changed
    :param status: current status
    :return: void
    '''
    global __alarm_beep_status
    # 停止闹钟响铃（按下任何轻触开关均可触发）
    __alarm_beep_status = False


def display_time():
    global __alarm_time
    global __alarm_beep_status
    __dp = True
    __alarm_beep_times = 0

    #设定轻触开关回调函数
    SAKS.tact_event_handler = tact_event_handler
    while True:
        # 以下代码获取系统时间、时、分、秒、星期的数值
        t = time.localtime()
        curTime = [t.tm_hour, t.tm_min, t.tm_sec]

        if curTime == __alarm_time:
            __alarm_beep_status = True
            __alarm_beep_times = 0

        if __dp:
            # 数码管显示小时和分，最后一位的小点每秒闪烁一次
            SAKS.digital_display.show(("%02d%02d." % (t.tm_hour, t.tm_min)))
        else:
            SAKS.digital_display.show(("%02d%02d" % (t.tm_hour, t.tm_min)))

        if __alarm_beep_status == True:
            __alarm_beep_times = __alarm_beep_times + 1
            if __dp:
                #SAKS.buzzer.on()
                SAKS.ledrow.on()
            else:
                #SAKS.buzzer.off()
                SAKS.ledrow.off()

                if __alarm_beep_times > 20:
                    __alarm_beep_status = False

        __dp = not __dp
        time.sleep(0.5)


def set_alarm_time(strTime):
    global __alarm_time

    try:
        temp = time.strptime(strTime, "%H:%M")

        __alarm_time[0] = temp.tm_hour
        __alarm_time[1] = temp.tm_min
        __alarm_time[2] = 0
        return True
    except:
        return False


def calc_remain_time(strTime):
    curTime = time.localtime()
    alarm_time = time.strptime(strTime, "%H:%M")

    rTime = [alarm_time.tm_hour - curTime.tm_hour, alarm_time.tm_min - curTime.tm_min]

    if rTime[1] < 0:
        rTime[0] = rTime[0] - 1
        rTime[1] = rTime[1] + 60

    if rTime[0] < 0:
        rTime[0] = rTime[0] + 24

    return rTime


def get_room_temp():
    #从 ds18b20 读取温度（摄氏度为单位）
    #返回值为 -128.0 表示读取失败
    temp = SAKS.ds18b20.temperature

    #数码管显示温度数值，5位(含小数点)、精确到小数点1后1位
    #SAKS.digital_display.show(("%5.1f" % temp).replace(' ','#'))

    return temp


def __HW_PROC__():
    display_time()


##########################################################################


###############################################################################

_TOKEN = 'dreamtale90'

#URL路径，处理类
_URLS = (
    '/weixin', 'weixinserver',
    '/heartbeat', 'checkserver',
)

root = 'oWB27wAZB7_ITyqO8ML_CafFfvgc'

class checkserver:

    def GET(self):
        return 'OK4LIVE'


def my_print(data):
    curTime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    print '[%s] %s' %(curTime, data)


def _check_hash(data):
    signature = data.signature
    timestamp = data.timestamp
    nonce = data.nonce
    list = [_TOKEN, timestamp, nonce]
    list.sort()
    sha1 = hashlib.sha1()
    map(sha1.update, list)
    hashcode = sha1.hexdigest()
    if hashcode == signature: return True
    return False


def _check_user(user_id):
    user_list = [root, 'oWB27wHY_yeuDG27iJ91MudguUks', 'oWB27wEjytw9wY6_3o4W8tKrHtRA']
    if user_id in user_list:
        return True
    return False


user_cache = dict()
def get_user_name(userInfo, user_id):
    if user_id in user_cache:
        return user_cache[user_id]
    user_info = userInfo.info.dget(openid=user_id, lang='zh_CN')
    user_cache[user_id] = user_info.nickname
    return user_info.nickname


def _punctuation_clear(ostr):
    '''Clear XML or dict using special punctuation'''
    return str(ostr).translate(None, '\'\"<>&')


def _cpu_and_gpu_temp():
    '''Get from pi'''
    import commands
    try:
        fd = open('/sys/class/thermal/thermal_zone0/temp')
        ctemp = fd.read()
        fd.close()
        gtemp = commands.getoutput('/opt/vc/bin/vcgencmd measure_temp').replace('temp=', '').replace('\'C', '')
    except Exception, e:
        return (0, 0)
    return (float(ctemp) / 1000, float(gtemp))


def _udp_client(addr, data):
    import select
    import socket
    mm = '{"errno":1, "msg":"d2FpdCByZXNwb25zZSB0aW1lb3V0"}'
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c.setblocking(False)
    inputs = [c]
    c.connect(addr)
    c.sendall(data)
    readable, writeable, exceptional = select.select(inputs, [], [], 3)
    try:
        if readable: mm = c.recv(2000)
    except Exception, e:
        mm = '{"errno":1, "msg":"%s"}' %(base64.b64encode(_punctuation_clear(e)))
    finally:
        c.close()
    return mm


def _take_snapshot(client, curTime):
    import picamera
    camera = None
    save_file = './../send_to_user/image/' + curTime + '.jpg'

    try:
        camera = picamera.PiCamera()

        #camera.led = False
        camera.annotate_text_size = 20
        camera.annotate_foreground = picamera.Color('#FFFF00')
        camera.annotate_text = '                                         ' + curTime
        camera.resolution = (720, 480)
        #camera.sharpness = 0
        #camera.contrast = 0
        #camera.brightness = 50
        #camera.saturation = 0
        #camera.ISO = 0
        #camera.video_stabilization = False
        #camera.exposure_compensation = 0
        #camera.exposure_mode = 'auto'
        #camera.meter_mode = 'average'
        #camera.awb_mode = 'auto'
        #camera.image_effect = 'none'
        #camera.color_effects = None
        #camera.rotation = 0
        #camera.hflip = False
        #camera.vflip = False
        #camera.crop = (0.0, 0.0, 1.0, 1.0)

        time.sleep(0.5)
        camera.capture(save_file)
    finally:
        camera.close()

    return client.media.upload.file(type='image', jpg=open(save_file, 'rb'))


def _take_video(client, curTime):
    import picamera
    import commands
    camera = None
    temp_file = '/tmp/input_raw.h264'
    image_file = './../send_to_user/video/' + curTime + '.jpg'
    video_file = './../send_to_user/video/' + curTime + '.mp4'

    try:
        camera = picamera.PiCamera()
        camera.resolution = (720, 480)

        camera.start_recording(temp_file)
        camera.capture(image_file, resize = (160, 120))
        camera.wait_recording(9)
        camera.stop_recording()

        #need to convert h264 to mp4
        shell_cmd = 'MP4Box -add %s %s' %(temp_file, video_file)
        commands.getoutput(shell_cmd)

    finally:
        camera.close()

    thumb = client.media.upload.file(type='image', jpg=open(image_file, 'rb'))
    video = client.media.upload.file(type='video', mpeg4=open(video_file, 'rb'))
    return [video.media_id, thumb.media_id]


def _talk_with_simsimi(topic):
    import urllib2
    topic = topic.encode('UTF-8')
    entopic = urllib2.quote(topic)
    send_headers = {
    'Cookie':'Filtering=0.0; Filtering=0.0; isFirst=1; isFirst=1; simsimi_uid=50840753; simsimi_uid=50840753; teach_btn_url=talk; teach_btn_url=talk; sid=s%3AzwUdofEDCGbrhxyE0sxhKEkF.1wDJhD%2BASBfDiZdvI%2F16VvgTJO7xJb3ZZYT8yLIHVxw; selected_nc=zh; selected_nc=zh; menuType=web; menuType=web; __utma=119922954.2139724797.1396516513.1396516513.1396703679.3; __utmc=119922954; __utmz=119922954.1396516513.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)'
    }
    baseurl = r'http://www.simsimi.com/func/reqN?lc=zh&ft=0.0&req='
    url = baseurl+entopic
    req = urllib2.Request(url,headers=send_headers)
    resp = urllib2.urlopen(req)
    answer = json.loads(resp.read())
    return answer


def _do_event_subscribe(server, fromUser, toUser, doc):
    send_info_to_root(server.client, fromUser, 'text', 'subscribe' + ' (' + fromUser + ')')
    return server._reply_text(fromUser, toUser, u'hello!')


def _do_event_unsubscribe(server, fromUser, toUser, doc):
    return server._reply_text(fromUser, toUser, u'bye!')


def _do_event_SCAN(server, fromUser, toUser, doc):
    pass


def _do_event_LOCATION(server, fromUser, toUser, doc):
    pass


def _do_event_CLICK(server, fromUser, toUser, doc):
    key = doc.find('EventKey').text
    send_info_to_root(server.client, fromUser, 'text', key)
    try:
        return _weixin_click_table[key](server, fromUser, toUser, doc)
    except KeyError, e:
        #print '_do_event_CLICK: %s' %e
        return server._reply_text(fromUser, toUser, u'Unknow click: '+key)


_weixin_event_table = {
    'subscribe'     :   _do_event_subscribe,
    'unsbscribe'    :   _do_event_unsubscribe,
    'SCAN'          :   _do_event_SCAN,
    'LOCATION'      :   _do_event_LOCATION,
    'CLICK'         :   _do_event_CLICK,
}


def _do_click_V1001_TEMPERATURE(server, fromUser, toUser, doc):
    thread = threading.Thread(target = assistant, args = (fromUser, 'temp', None))
    thread.start()
    return 'success'

def _do_click_V1002_PICTURES(server, fromUser, toUser, doc):
    if not _check_user(fromUser):
        return server._reply_text(fromUser, toUser, u'Permission denied…')
    thread = threading.Thread(target = assistant, args = (fromUser, 'image', None))
    thread.start()
    return 'success'

def _do_click_V1003_VOICE(server, fromUser, toUser, doc):
    if not _check_user(fromUser):
        return server._reply_text(fromUser, toUser, u'Permission denied…')
    return server._reply_text(fromUser, toUser, u'This feature is still under development. Stay tuned !')


def _do_click_V1004_VIDEO(server, fromUser, toUser, doc):
    if not _check_user(fromUser):
        return server._reply_text(fromUser, toUser, u'Permission denied…')
    thread = threading.Thread(target = assistant, args = (fromUser, 'video', None))
    thread.start()
    return 'success'


def _do_click_V2001_FUNC(server, fromUser, toUser, doc):
    return server._reply_text(fromUser, toUser, u'This feature is still under development. Stay tuned !')


def _do_click_V2002_FUNC(server, fromUser, toUser, doc):
    return server._reply_text(fromUser, toUser, u'This feature is still under development. Stay tuned !')


def _do_click_V3001_FUNC(server, fromUser, toUser, doc):
    return server._reply_text(fromUser, toUser, u'This feature is still under development. Stay tuned !')


def _do_click_V3002_FUNC(server, fromUser, toUser, doc):
    return server._reply_text(fromUser, toUser, u'This feature is still under development. Stay tuned !')


_weixin_click_table = {
    'V1001_TEMPERATURE'     :   _do_click_V1001_TEMPERATURE,
    'V1002_PICTURES'        :   _do_click_V1002_PICTURES,
    'V1003_VOICE'           :   _do_click_V1003_VOICE,
    'V1004_VIDEO'           :   _do_click_V1004_VIDEO,
    'V2001_FUNC'            :   _do_click_V2001_FUNC,
    'V2002_FUNC'            :   _do_click_V2002_FUNC,
    'V3001_FUNC'            :   _do_click_V3001_FUNC,
    'V3002_FUNC'            :   _do_click_V3002_FUNC,
}


def _do_get_temp():
    c, g = _cpu_and_gpu_temp()
    t = get_room_temp()
    reply_msg = 'CPU : %.02f℃\nGPU : %.02f℃\nRoom : %.02f℃' %(c, g, t)
    return reply_msg


def _do_text_command(server, fromUser, toUser, content):
    temp = content.split(' ')
    try:
        return _weixin_text_command_table[temp[0]](server, fromUser, toUser, content[len(temp[0]) + 1:])
    except KeyError, e:
        return server._reply_text(fromUser, toUser, u'Unknow command: '+temp[0])


def _do_exec_command(server, fromUser, toUser, cmd):
    import commands
    save_file = '/tmp/wx_command.txt'

    if not _check_user(fromUser):
        return server._reply_text(fromUser, toUser, u'Permission denied…')

    err_msg = 'exec cmd fail: '
    try:
        shell_cmd = cmd + ' > ' + save_file + ' 2>&1'
        commands.getoutput(shell_cmd)

        result = ''
        fd = open(save_file, 'rb')

        for line in fd:
            text = line.rstrip()
            if len(text) == 0:
                continue
            #Max Text Message Length 2048 bytes(UTF-8)
            if len(result) + len(text) > 2000:
                break
            result += text + '\n'

        fd.close()

        if result == '':
            result = u'No Output'
        return server._reply_text(fromUser, toUser, result)
    except Exception, e:
        err_msg += _punctuation_clear(str(e))
        my_print(err_msg)
        return server._reply_text(fromUser, toUser, err_msg)


def _do_set_alarm(server, fromUser, toUser, content):

    #check content and set alarm
    if set_alarm_time(content) == True:
        rTime = calc_remain_time(content)
        reply_msg = u'Alarm set for %s hours and %s minutes from now' %(rTime[0], rTime[1])
        return server._reply_text(fromUser, toUser, reply_msg)
    else:
        return server._reply_text(fromUser, toUser, u'set alarm failed(e.g. 06:30)')


def _do_print_help(server, fromUser, toUser, para):
    data = "commands:\n"
    for (k, v) in _weixin_text_command_table.items():
        data += "\t%s\n" %(k)
    return server._reply_text(fromUser, toUser, data)


_weixin_text_command_table = {
    'help'                  :   _do_print_help,
    'cmd'                   :   _do_exec_command,
    'alarm'                 :   _do_set_alarm,
    #'image'                 :   _do_set_camera,
}


menu = '''{
     "button":[
       {
           "name":"监 控",
           "sub_button":[
            {
               "type":"click",
               "name":"  温    度  ",
               "key":"V1001_TEMPERATURE"
            },
            {
               "type":"click",
               "name":"  拍    照  ",
               "key":"V1002_PICTURES"
            },
            {
               "type":"click",
               "name":"  录    音  ",
               "key":"V1003_VOICE"
            },
            {
               "type":"click",
               "name":"  录    像  ",
               "key":"V1004_VIDEO"
            }]
       }]
           ,
     "button":[
       {
           "name":"Menu2",
           "sub_button":[
            {
               "type":"click",
               "name":"Func3",
               "key":"V2001_FUNC"
            },
            {
               "type":"click",
               "name":"Func4",
               "key":"V2002_FUNC"
            }]
       }]
           ,
     "button":[
       {
           "name":"Menu3",
           "sub_button":[
            {
               "type":"click",
               "name":"Func5",
               "key":"V3001_FUNC"
            },
            {
               "type":"click",
               "name":"Func6",
               "key":"V3002_FUNC"
            }]
       }]
}'''


def assistant(toUser, msgType, content):

    ret = None
    wx = weixinserver()

    if msgType == 'text':
        ret = wx._send_text(toUser, content)
    if msgType == 'image':
        ret = wx._send_image(toUser)
    if msgType == 'voice':
        ret = wx._send_voice(toUser)
    if msgType == 'video':
        ret = wx._send_video(toUser)
    if msgType == 'temp':
        ret = wx._send_text(toUser, _do_get_temp())


def send_info_to_root(server, fromUser, msgType, content):
    curTime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')

    if server is None or fromUser is None:
        message = '[%s] %s' %(curTime, content)
    else:
        message = '[%s] %s -> %s' %(curTime, get_user_name(server.user, fromUser), content)

    print (message)

    if fromUser == root:
        return

    thread = threading.Thread(target = assistant, args = (root, msgType, message))
    thread.start()


class weixinserver:

    def __init__(self):
        #获取执行文件路径
        self.app_root = os.path.dirname(__file__)
        #设置回复模板路径
        self.templates_root = os.path.join(self.app_root, 'templates')
        #初始化回复模板
        self.render = web.template.render(self.templates_root)

        #微信测试公众号
        self.client = WeiXinClient('wxaece866e46e9d4a6', 'c104ddad7eef2e369acb1aee01bf8341')
        try:
            self.client.request_access_token()
            #self.client.menu.delete.post()
            #self.client.menu.create.post(body=menu)

        except Exception, e:
            self.client.set_access_token('ThisIsAFakeToken', 1800, persistence=True)

    def _recv_text(self, fromUser, toUser, doc):
        content = doc.find('Content').text
        send_info_to_root(self.client, fromUser, 'text', content)
        if content[0] == '.':
            return _do_text_command(self, fromUser, toUser, content[1:])
        reply_msg = content
        #reply_msg = _talk_with_simsimi(content)
        return self._reply_text(fromUser, toUser, reply_msg)

    def _recv_event(self, fromUser, toUser, doc):
        event = doc.find('Event').text
        try:
            return _weixin_event_table[event](self, fromUser, toUser, doc)
        except KeyError, e:
            return self._reply_text(fromUser, toUser, u'Unknow event:%s' %event)

    def _recv_image(self, fromUser, toUser, doc):
        url = doc.find('PicUrl').text
        mid = doc.find('MediaId').text
        rm = self.client.media.get.file(media_id=mid)
        fname = '/home/pi/Downloads/wx/wx_%s.jpg' %(time.strftime("%Y_%m_%dT%H_%M_%S", time.localtime()))
        fd = open(fname, 'wb'); fd.write(rm.read()); fd.close(); rm.close()
        return self._reply_text(fromUser, toUser, u'upload to:%s' %url)

    def _recv_voice(self, fromUser, toUser, doc):
        #import subprocess
        cmd = doc.find('Recognition').text
        mid = doc.find('MediaId').text
        rm = self.client.media.get.file(media_id=mid)
        fname = '/home/pi/Downloads/wx/wx_%s.amr' %(time.strftime("%Y_%m_%dT%H_%M_%S", time.localtime()))
        fd = open(fname, 'wb'); fd.write(rm.read()); fd.close(); rm.close()
        #subprocess.call(['omxplayer', '-o', 'local', fname])
        if cmd is None:
            return self._reply_text(fromUser, toUser, u'no Recognition, no command');
        return self._reply_text(fromUser, toUser, u'Unknow recognition:%s' %cmd);

    def _recv_video(self, fromUser, toUser, doc):
        pass

    def _recv_shortvideo(self, fromUser, toUser, doc):
        mid = doc.find('MediaId').text
        rm = self.client.media.get.file(media_id=mid)
        fname = '/home/pi/Downloads/wx/wx_%s.mp4' %(time.strftime("%Y_%m_%dT%H_%M_%S", time.localtime()))
        fd = open(fname, 'wb'); fd.write(rm.read()); fd.close(); rm.close()
        return self._reply_text(fromUser, toUser, u'shortvideo:%s' %fname);

    def _recv_location(self, fromUser, toUser, doc):
        pass

    def _recv_link(self, fromUser, toUser, doc):
        pass

    def _reply_text(self, toUser, fromUser, msg):
        return self.render.reply_text(toUser, fromUser, int(time.time()), msg)

    def _reply_image(self, toUser, fromUser, media_id):
        return self.render.reply_image(toUser, fromUser, int(time.time()), media_id)

    def _reply_news(self, toUser, fromUser, title, descrip, picUrl, hqUrl):
        return self.render.reply_news(toUser, fromUser, int(time.time()), title, descrip, picUrl, hqUrl)

    def _send_text(self, toUser, content):
        data = '{"touser":"%s", "msgtype":"text", "text":{"content":"%s"}}' %(toUser, content)
        return self.client.message.custom.send.post(body = data)

    def _send_image(self, toUser):
        image = None
        curTime = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        send_info_to_root(self.client, toUser, 'text', 'image:' + curTime)

        try:
            image = _take_snapshot(self.client, curTime)
        except Exception, e:
            err_msg = 'take snapshot fail: ' + _punctuation_clear(str(e))
            my_print(err_msg)
            return None
        data = '{"touser":"%s", "msgtype":"image", "image":{"media_id":"%s"}}' %(toUser, image.media_id)
        return self.client.message.custom.send.post(body = data)

    def _send_voice(self, toUser):
        return

    def _send_video(self, toUser):
        mediaID = [0, 0]
        curTime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        send_info_to_root(self.client, toUser, 'text', 'video:' + curTime)
        try:
            mediaID = _take_video(self.client, curTime)
        except Exception, e:
            err_msg = 'take snapshot fail: ' + _punctuation_clear(str(e))
            my_print(err_msg)
        data = '{"touser":"%s", "msgtype":"video", "video":{"media_id":"%s", "thumb_media_id":"%s", "title":"%s", "description":"%s"}}' %(toUser, mediaID[0], mediaID[1], 'provide by dreamtale90', curTime)
        return self.client.message.custom.send.post(body = data)

    def GET(self):
        data = web.input()
        try:
            if _check_hash(data):
                return data.echostr
        except Exception, e:
            return None

    def POST(self):
        str_xml = web.data()
        doc = etree.fromstring(str_xml)
        msgType = doc.find('MsgType').text
        fromUser = doc.find('FromUserName').text
        toUser = doc.find('ToUserName').text

        if msgType == 'text':
            return self._recv_text(fromUser, toUser, doc)
        if msgType == 'event':
            return self._recv_event(fromUser, toUser, doc)
        if msgType == 'image':
            return self._recv_image(fromUser, toUser, doc)
        if msgType == 'voice':
            return self._recv_voice(fromUser, toUser, doc)
        if msgType == 'video':
            return self._recv_video(fromUser, toUser, doc)
        if msgType == 'shortvideo':
            return self._recv_shortvideo(fromUser, toUser, doc)
        if msgType == 'location':
            return self._recv_location(fromUser, toUser, doc)
        if msgType == 'link':
            return self._recv_link(fromUser, toUser, doc)
        else:
            return self._reply_text(fromUser, toUser, u'Unknow msg:' + msgType)

raspberry = Process(target = __HW_PROC__)
application = web.application(_URLS, globals())

if __name__ == "__main__":
    send_info_to_root(None, None, 'text', 'WeChat Start !')

    raspberry.start()
    application.run()
