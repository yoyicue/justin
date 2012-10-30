#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Manager flexget crontab for JustinLee
$ tar zxvf justin.tar.gz
$ /usr/bin/python /root/justin/run.py > /root/justin.log 2>&1 &
"""

from crontab import CronTab
from bottle import route, run, redirect

cmd = "/usr/local/bin/flexget > /root/flexget.log 2>&1"
minutes = 2

@route('/')
def index():
    "homepage"

    return """
<html> 
<head><title>403 Forbidden</title></head> 
<body bgcolor="white"> 
<center><h1>403 Forbidden</h1></center> 
<hr><center>nginx/0.8.21</center> 
</body> 
</html> 
    """

@route('/start')
def start():
    "start command"

    global cmd, minutes
    tab = CronTab()
    job = tab.find_command(cmd)

    if len(job) == 0:
        job = tab.new(cmd)
        job.minute.every(minutes)
        tab.write()

    redirect("/flexget")

@route('/stop')
def stop():
    "stop command"

    global cmd
    tab = CronTab()
    job = tab.find_command(cmd)

    if len(job) > 0:
        tab.remove_all(cmd)
        tab.write()

    redirect("/flexget")

@route('/flexget')
def flexget():
    "flexget status"

    global cmd
    tab = CronTab()
    job = tab.find_command(cmd)

    if len(job) > 0:
        return """
status: <span style="color:green">running<span>
<br/>
<a href="/stop">stop flexget!</a>"""
    else:
        return """
status: <span style="color:red">stopping<span>
<br/>
<a href="/start">start flexget!</a>"""

run(host='0.0.0.0', port=8118)