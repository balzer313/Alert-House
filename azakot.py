
import random
import math
import requests
import json
import time

class RedAlert():

    def __init__(self):

        # cookies
        self.cookies = ""
        # initialize user agent for web requests
        self.headers = {
           "Host":"www.oref.org.il",
           "Connection":"keep-alive",
           "Content-Type":"application/json",
           "charset":"utf-8",
           "X-Requested-With":"XMLHttpRequest",
           "sec-ch-ua-mobile":"?0",
           "User-Agent":"",
           "sec-ch-ua-platform":"macOS",
           "Accept":"*/*",
           "sec-ch-ua": '".Not/A)Brand"v="99", "Google Chrome";v="103", "Chromium";v="103"',
           "Sec-Fetch-Site":"same-origin",
           "Sec-Fetch-Mode":"cors",
           "Sec-Fetch-Dest":"empty",
           "Referer":"https://www.oref.org.il/12481-he/Pakar.aspx",
           "Accept-Encoding":"gzip, deflate, br",
           "Accept-Language":"en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        }
        # intiiate cokies
        self.get_cookies()


    def get_cookies(self):
        HOST = "https://www.oref.org.il/"
        r = requests.get(HOST,headers=self.headers)
        self.cookies = r.cookies

    def get_red_alerts(self):
        # get red alerts
        HOST = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
        r = requests.get(HOST, headers=self.headers, cookies=self.cookies)
        alerts = r.content.decode("UTF-8").replace("\n","").replace("\r","")
        if(len(alerts) <= 1):
            return None
        # parse the json response
        j = json.loads(r.content)
        # check if there is no alerts - if so, return null.
        if(len(j["data"]) == 0):
            return None
        # initialize the current timestamp to know when the rocket alert started
        j["timestamp"] = time.time()
        # parse data
        return j

def main(city):
    alert = RedAlert()
    red_alerts = alert.get_red_alerts()
    if red_alerts != None:
        if red_alerts["title"] == "ירי רקטות וטילים":
            for alert_city in red_alerts["data"]:
                if alert_city == city: return True
        return False
    else:
        return False

# {
# 	"id": "133042579090000000",
# 	"cat": "1",
# 	"title": "ירי רקטות וטילים",
# 	"data": [
# 		"שדרות, איבים, ניר עם"],
# 	"desc": "היכנסו למרחב המוגן ושהו בו 10 דקות"
# }

