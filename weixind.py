#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:     weixind.py
# Author:       Liang Cha<ckmx945@gmail.com>
# CreateDate:   2014-05-15

import os
import web
import time
import types
import hashlib
import base64
import memcache
from lxml import etree
from weixin import WeiXinClient
from weixin import APIError
from weixin import AccessTokenError


_TOKEN = 'dreamtale90'

#URL路径，处理类
_URLS = (
    '/weixin', 'weixinserver',
)


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
    user_list = ['oWB27wAZB7_ITyqO8ML_CafFfvgc', 'oWB27wHY_yeuDG27iJ91MudguUks']
    if user_id in user_list:
        return True
    return False


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


def _json_to_ditc(ostr):
    import json
    try:
        return json.loads(ostr)
    except Exception, e:
        return None


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


def _take_snapshot(client):
    import commands
    ipc_cmd = 'raspistill -t 300 -rot 180 -w 640 -h 480'
    save_path = '/tmp/wx_image.jpg'
    shell_cmd = ipc_cmd + ' ' + '-o' + ' ' + save_path
    commands.getoutput(shell_cmd);
    return client.media.upload.file(type='image', jpg=open(save_path, 'rb'))


def _do_event_subscribe(server, fromUser, toUser, doc):
    return server._reply_text(fromUser, toUser, u'hello!')


def _do_event_unsubscribe(server, fromUser, toUser, doc):
    return server._reply_text(fromUser, toUser, u'bye!')


def _do_event_SCAN(server, fromUser, toUser, doc):
    pass


def _do_event_LOCATION(server, fromUser, toUser, doc):
    pass


def _do_event_CLICK(server, fromUser, toUser, doc):
    key = doc.find('EventKey').text
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
    c, g = _cpu_and_gpu_temp()
    t = 36
    reply_msg = u'CPU : %.02f℃\nGPU : %.02f℃\n室内温度 : %02.02f℃' %(c, g, t)
    return server._reply_text(fromUser, toUser, reply_msg)


def _do_click_V1002_PICTURES(server, fromUser, toUser, doc):
    if not _check_user(fromUser):
        return server._reply_text(fromUser, toUser, u'Permission denied…')
    data = None
    err_msg = 'snapshot fail: '
    try:
        data = _take_snapshot(server.client)
    except Exception, e:
        err_msg += _punctuation_clear(str(e))
        return server._reply_text(fromUser, toUser, err_msg)
    return server._reply_image(fromUser, toUser, data.media_id)


def _do_click_V2001_FUNC(server, fromUser, toUser, doc):
    return server._reply_text(fromUser, toUser, u'2001_Func')


def _do_click_V2002_FUNC(server, fromUser, toUser, doc):
    return server._reply_text(fromUser, toUser, u'2002_Func')


def _do_click_V3001_FUNC(server, fromUser, toUser, doc):
    return server._reply_text(fromUser, toUser, u'3001_Func')


def _do_click_V3002_FUNC(server, fromUser, toUser, doc):
    return server._reply_text(fromUser, toUser, u'3002_Func')


_weixin_click_table = {
    'V1001_TEMPERATURE'     :   _do_click_V1001_TEMPERATURE,
    'V1002_PICTURES'        :   _do_click_V1002_PICTURES,
    'V2001_FUNC'            :   _do_click_V2001_FUNC,
    'V2002_FUNC'            :   _do_click_V2002_FUNC,
    'V3001_FUNC'            :   _do_click_V3001_FUNC,
    'V3002_FUNC'            :   _do_click_V3002_FUNC,
}


def _do_text_command(server, fromUser, toUser, content):
    temp = content.split(' ')
    try:
        return _weixin_text_command_table[temp[0]](server, fromUser, toUser, temp[1])
    except KeyError, e:
        return server._reply_text(fromUser, toUser, u'Unknow command: '+temp[0])


def _do_get_manual(server, fromUser, toUser, para):
    import commands
    save_path = '/tmp/wx_manual.txt'
    try:
        shell_cmd = 'man' + ' ' + para + ' ' + '>' + ' ' + save_path
        #shell_cmd = para + ' ' + '--help' + '>' + ' ' + save_path
        print '%s' %shell_cmd
        commands.getoutput(shell_cmd)

        fd = open(save_path, 'rb')
        result = fd.read()
        fd.close()

        strlen = len(result)
        #Max Text Message Length 2048 bytes(UTF-8)
        if strlen >= 2001:
            return server._reply_text(fromUser, toUser, result[:1980])
        else:
            return server._reply_text(fromUser, toUser, result[:strlen])
        '''
        begin = 0
        for end in range(2001, strlen, 2001):
            #ret = server.client.send.post(fromUser, toUser, result[begin:end])
            data = '{"touser":"oWB27wAZB7_ITyqO8ML_CafFfvgc", "msgtype":"text", "text":{ "content":"hello!"}}'
            ret = server.client.message.custom.send.post(body=data)
            begin += 2001
        '''
    except Exception, e:
        err_msg += _punctuation_clear(str(e))
        return server._reply_text(fromUser, toUser, err_msg)


def _do_text_command_help(server, fromUser, toUser, para):
    data = "commands:\n"
    for (k, v) in _weixin_text_command_table.items():
        data += "\t%s\n" %(k)
    return server._reply_text(fromUser, toUser, data)


_weixin_text_command_table = {
    'help'                  :   _do_text_command_help,
    'man'                   :   _do_get_manual,
    'image'                 :   _do_click_V1002_PICTURES,
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
               "name":"实时图像", 
               "key":"V1002_PICTURES" 
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
            #print 'access_token = %s' %(self.client.access_token)
        except Exception, e:
            self.client.set_access_token('ThisIsAFakeToken', 1800, persistence=True)

        #self.client.menu.delete.post()
        #self.client.menu.create.post(body=menu)

    def _recv_text(self, fromUser, toUser, doc):
        content = doc.find('Content').text
        if content[0] == '.':
            return _do_text_command(self, fromUser, toUser, content[1:])
        reply_msg = content
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
        print '%s->%s(%s)' %(fromUser, toUser, msgType)

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

application = web.application(_URLS, globals())

if __name__ == "__main__":
    application.run()
