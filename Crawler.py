from urllib.request import Request
from urllib.request import urlopen
from bs4 import BeautifulSoup
import json
import urllib
import re
import time
import requests
import selenium_ff
import ast
import user_config

empty_result = {"appid":0,"name":"null","developer":"null","publisher":"null","score_rank":"null","owners":0,"owners_variance":0,"players_forever":0,"players_forever_variance":0,"players_2weeks":0,"players_2weeks_variance":0,"average_forever":0,"average_2weeks":0,"median_forever":0,"median_2weeks":0,"ccu":0,"price":"null"}
login_url= "http://steamspy.com/login/"
username = user_config.username
password = user_config.password

def isEmptyPage(bsObj):
	#Find out if a given page is empty on SteamSpy
    x = bsObj.findAll("div",class_="p-r-30")[0].find("a",text="Store")
    if x["href"] == "http://store.steampowered.com/app/":
        print("The page is empty. Probably this game has not yet been recorded on SteamSpy!")
        return True
    else:
        return False
    
def loginToSteamSpy():
	#Login to Steamspy with username and account
	driver = selenium_ff.loginViaFirefox(login_url,username,password)
	return driver

def connectToSteamSpy(appid,owners,rule,driver):
    try:
        url = "http://steamspy.com/app/"+str(appid)
        headers = user_config.headers
        if driver and owners > rule:
        	#start crawling the page with Selenium
            print("Owners of the current app is "+str(owners)+". Start crawling geo data...")
            bsObj = BeautifulSoup(selenium_ff.connectViaFirefox(url,driver),"lxml")
        else:
        	#crawling the target page with Requests
            req = requests.get(url,headers=headers)
            bsObj = BeautifulSoup(req.text,"lxml")
        if not isEmptyPage(bsObj):
            return bsObj
    except Exception as err:
        print(err)
        print("Error happend when connecting to SteamSpy")

def purifyWord(word):
	#remove unexpected letter in game tags
    check_list = ['(',')',',']
    word = word.strip()
    while True:
        if word[0] in check_list or word[-1] in check_list:
            word = word.strip('(')
            word = word.strip(')')
            word = word.strip(',')
        else:
            return word

def getTagsFromSteamSpy(bsObj):
    #return as dictionary
    res = {}
    try:
        tags=bsObj.findAll("div",class_="p-r-30")[0].findAll("a",href=re.compile(r'/tag/'))
        for tag in tags:
            tag_name = tag.get_text().replace(".","_")
            if tag_name != None and len(tag_name)>=1:
                tag_num = purifyWord(tag.next_sibling)
                res[tag_name] = tag_num
    except:
        print("Page not found!")
    return res

def getDataViaHyperLinkFromSteamSpy(bsObj,a):
    #return as list
    res = []
    try:
        data_set=bsObj.findAll("div",class_="p-r-30")[0].findAll("a",href=re.compile('/'+a+'/'))
        for data in data_set:
            res.append(data.get_text())
    except Exception as err:
        print("err occurred")
    return res

def getReleaseDateFromSteamSpy(bsObj):
    try:
        dates=bsObj.findAll("div",class_="p-r-30")[0].findAll("strong",text="Release date")
        if(len(dates)) == 0:
            #release date not found!
            return "Not released"
        else:
             date = dates[0].next_sibling   #always use the first date
             if len(date) == 0:
                 return "Not released"
             return parseDate(date.strip().strip(":").strip())
    except:
        return "Not released"

def getUserScoreFromSteamSpy(bsObj,score_type):
    key_word = "Old userscore:"
    if score_type == "new":
        key_word = "Userscore:"
    try:
        score=bsObj.findAll("div",class_="p-r-30")[0].findAll("strong",text=key_word)
        if(len(score)) == 0:
            #release date not found!
            return "null"
        else:
             score = score[0].next_sibling   #always use the first date
             if len(score) == 0:
                 return "null"
             return score.strip().strip(":").strip("%")
    except:
        return "null"

def getCategoryFromSteamSpy(bsObj):
    category_set = []
    try:
        category = bsObj.findAll("div",class_="p-r-30")[0].findAll("strong",text="Category:") 
        for catg in category[0].next_sibling.split(","):
            category_set.append(catg.strip())
    except:
        print("Error occured when crawling category!")
    return category_set

def getGeoDataFromSteamSpy(bsObj):
    geo_set = {}
    try:
        geo_list = bsObj.findAll("div",id="geograph")[0].find("script").get_text()
        #clean the expression
        geo_dict = ast.literal_eval(geo_list.split("=")[1].strip(";"))
        return geo_dict
    except Exception as err:
        print("Error occured when crawling geodata!")
        print(err)

def parseDate(date):
    #remove the "(" at the end of the date
    date = date.split("(")[0].strip()
    if re.search(",",date):
        md = date.split(",")[0].strip()
        yy = date.split(",")[1].strip()
        mm = md.split(" ")[0].strip()
        dd = md.split(" ")[1].strip()
        return time.strptime(yy+"/"+mm+"/"+dd,"%Y/%b/%d")
    else:
        return "Not released"

def checkSteamSpy(appid):
	#Get Data via SteamSpy's API
    url = "http://steamspy.com/api.php?request=appdetails"+"&appid="+str(appid)
    try:
        req = urllib.request.Request(url,headers={'User-Agent' : "Magic Browser"})
        con = urllib.request.urlopen(req)
        myStr = con.read().decode("utf8")   
        con.close()
        return json.loads(myStr)
    except Exception as err:
        #request may be banned in a very short time
        print("Error happended when checking SteamSpy")
        empty_result["appid"] = appid
        return empty_result

def getFormattedData(appid,driver):
    steam_app = {}
    #get data via SteamSpy's API
    steamSpy = checkSteamSpy(appid)
    steam_app["appid"] = appid
    steam_app["name"] = steamSpy["name"]
    steam_app["developer"] = steamSpy["developer"]
    steam_app["publisher"] = steamSpy["publisher"]
    steam_app["owners"] = steamSpy["owners"]
    steam_app["players_forever"] = steamSpy["players_forever"]
    steam_app["players_2weeks"] = steamSpy["players_2weeks"]
    steam_app["average_play_time"] = steamSpy["average_forever"]
    steam_app["average_play_time_2weeks"] = steamSpy["average_2weeks"]
    steam_app["median_play_time"] = steamSpy["median_forever"]
    steam_app["median_play_time_2weeks"] = steamSpy["median_2weeks"]
    steam_app["ccu"] = steamSpy["ccu"]
    steam_app["price"] = steamSpy["price"]
    steam_app["score_rank"] = steamSpy["score_rank"]
    if steamSpy["owners"]:
        bsObj = connectToSteamSpy(appid,int(steamSpy["owners"]),1000,driver)
        #get data through web crawling
        if bsObj:
            steam_app["release_date"] = getReleaseDateFromSteamSpy(bsObj)
            steam_app["category"] = getCategoryFromSteamSpy(bsObj)
            steam_app["languages"] = getDataViaHyperLinkFromSteamSpy(bsObj,"language")
            steam_app["genre"] = getDataViaHyperLinkFromSteamSpy(bsObj,"genre")
            steam_app["tags"] = getTagsFromSteamSpy(bsObj)
            steam_app["userscore"] = getUserScoreFromSteamSpy(bsObj,"new")
            steam_app["old_userscore"] = getUserScoreFromSteamSpy(bsObj,"old")
            steam_app["geo_data"] = getGeoDataFromSteamSpy(bsObj)
    time.sleep(1)
    return steam_app

if __name__ == "__main__":
    driver = loginToSteamSpy()
    s = getFormattedData(2280,driver)
    print(s)
