import urllib.request
import time
import json
import Crawler
import xlwt
import xlrd
from pymongo import MongoClient
from datetime import date   

#Configuration for database
dbAddr = 'mongodb://localhost'
portNo = 27017
dbName = "SteamDB"
appList = "GameList20170627"
raw_collection = "SteamSpyDB06"

def getGameList():
	#get the name and appid of a list of games in Steam
	try:
		url = 'http://api.steampowered.com/ISteamApps/GetAppList/v2'
		fp = urllib.request.urlopen(url)
		myList = fp.read().decode("utf8")
		fp.close()
		print("Retrieved data from Steam")
		myList = json.loads(myList)
	except:
		print("error occured when loading Steam's game list please try again!")
	return myList

def writeDataToFile(data,fileName):
	#Write string to file
	try:
		file_object = open(fileName,'w',encoding='utf-8')
		file_object.write(data)
		file_object.close()
	except:
		print("File name not found!")

def getLocalTime():
	#get local time
	timestamp = time.localtime(time.time())
	day = (str(timestamp.tm_mday) if timestamp.tm_mday>=10 else '0'+str(timestamp.tm_mday))
	month = (str(timestamp.tm_mon) if timestamp.tm_mon>=10 else '0'+str(timestamp.tm_mon))
	return str(timestamp.tm_year)+month+day

def readDataFromFile(fileName):
	#read str from file
	try:
		file_object = open(fileName,'r',encoding='utf-8')
		lines = file_object.read()
		file_object.close()
		print("Read data from local file: "+fileName)
	except:
		print("File not Found!")
	return lines

def connectToDB():
	client = MongoClient(dbAddr+":"+str(portNo)+"/")
	return client

def insertToDB(documents,collectionName):
	print("Inserting documents to collection: "+collectionName+"...")
	#Connect to the database
	client = connectToDB()
	db = client[dbName]
	collection = db[collectionName]
	for element in documents:
		try:
			result = collection.insert_one(element)
		except Exception as e:
			print("Unable to insert document")
	print("Done inserting!")
	client.close()

def insertSingleToDB(document,collection):
	print("Inserting documents to collection...")
	#Connect to the database.
	try:
		result = collection.insert_one(document)
	except Exception as e:
		print("Unable to insert document")
		print(e)
	print("Done inserting!")

def convertListToDict(applist):
	res = {}
	for app in applist:
		res[app['appid']] = app['name']
	return res

def compareDicts(dict_new,dict_old):
	result = {}
	for key in dict_new.keys():
		if key not in dict_old.keys():
			result.setdefault(key,dict_new[key])
	return result

def getGamesInCertainRange(date_range,game_dict,data_collection,owner):
	start_date = time.strptime(date_range.split("-")[0],"%Y/%m/%d")
	end_date = time.strptime(date_range.split("-")[1],"%Y/%m/%d")
	res = {}
	rep = {}	#contain games that do not have enough owner
	print("start searching for the existing data...")
	raw_data_list = data_collection.find()
	for data in raw_data_list:
		if "release_date" in data and data["release_date"] != "Not released":
			release_date = time.strptime(str(data["release_date"][0])+"/"+str(data["release_date"][1])+"/"+str(data["release_date"][2]),"%Y/%m/%d")
			if time.mktime(release_date) >= time.mktime(start_date) and time.mktime(release_date) <= time.mktime(end_date):
				print("Found desired game!")
				app_data = Crawler.checkSteamSpy(data["appid"])
				if app_data is None or app_data["owners"] < int(owner):
					print("Owners of game id "+str(data["appid"])+" is not enough! Deleting...")
					rep[data["appid"]] = data["name"]
					continue
				res[data["appid"]] = data["name"]
	print("start checking newly added games")
	for k in game_dict.keys():
		if k in res or k in rep:
			#data already existed
			continue
		result = data_collection.find_one({"appid":k})
		if data_collection.count({"appid":k})!=0 and "release_date" in result and result["release_date"] != "Not released":
			release_date = time.strptime(str(result["release_date"][0])+"/"+str(result["release_date"][1])+"/"+str(result["release_date"][2]),"%Y/%m/%d")
		else:
			#Not in raw database
			bsObj = Crawler.connectToSteamSpy(k)
			release_date = Crawler.getReleaseDateFromSteamSpy(bsObj)
			if release_date == "Not released":
				print("Appid: "+str(k)+" has not been recorded on SteamSpy")
				continue
		if time.mktime(release_date) >= time.mktime(start_date) and time.mktime(release_date) <= time.mktime(end_date):
			print("Found desired game!")
			app_data = Crawler.checkSteamSpy(k)
			if app_data is None or app_data["owners"] < int(owner):
				print("Owners of game id "+str(k)+" is not enough! Deleting...")
				continue
			res[k] = game_dict[k]
	return res

def save2Excel(fileName,game_dict):
	try:
		output = xlwt.Workbook()
		output_table = output.add_sheet("SteamDB",cell_overwrite_ok=True)
		output_table.write(0,0,"Appid")
		output_table.write(0,1,"Name")
		for i,key in enumerate(game_dict.keys()):
			output_table.write(i+1,0,key)
			output_table.write(i+1,1,game_dict[key])
		output.save(fileName+".xls")
		print("Data saved to file "+fileName+".xls")
	except Exception as err:
		print("Unable to save data to excel file, please try again later!")

def readFromExcel(fileName,tableNo,col):
	data = xlrd.open_workbook(fileName+".xls")
	table = data.sheets()[tableNo]
	result = []
	for r in range(1,table.nrows):
		result.append(table.cell(r,col).value)
	return result

def parseUserInput(user_input):
	if int(user_input.strip())==1:
		print("Start retriving game list from Steam!")
		game_list = getGameList()
		print("Data retrieved! Start inserting them to database....")
		insertToDB(game_list["applist"]["apps"],"GameList"+getLocalTime())
	elif int(user_input.strip())==0:
		print("Bye...")
		return 0
	elif int(user_input.strip())==2:
		client = connectToDB()
		db = client[dbName]
		print("The collections in the current database are as follows:")
		collections = sorted(db.collection_names())
		raw_data_collection = db[raw_collection]
		for collection_name in collections:
			print(collection_name)
		start_date = input("Please specify the starting date(format:yyyymmdd)")
		end_date = input("Please specify the ending date(format:yyyymmdd)")
		collectionName_old = "GameList" + start_date
		collectionName_new = "GameList" + end_date
		if collectionName_new not in collections or collectionName_old not in collections:
			print("Invalid date")
			return
		documents_new = convertListToDict(db[collectionName_new].find())
		documents_old = convertListToDict(db[collectionName_old].find())
		res = compareDicts(documents_new,documents_old)
		print("New games founded!")
		date_range = input("Please specify a certain range:(format:yyyy/mm/dd-yyyy/mm/dd)")
		owner = input("Owner:")
		res = getGamesInCertainRange(date_range,res,raw_data_collection,owner)
		client.close()
		user_choice = input("Do you wanna save the results to file?(Y or N)")
		if user_choice.lower()=="y":
			fileName = input("Please specify a file name: ")
			save2Excel(fileName,res)
	elif int(user_input.strip())==3:
		file_name = input("Please specify the name of the file that contains games you wish to monitor on Twitter:")
		game_list = readFromExcel(file_name,0,1)
		print(game_list)
	elif int(user_input.strip())==4:
		confirm = input("Are you sure you want to update this form?("+raw_collection+".Its gonna take a while)")
		if confirm.strip().upper() == "Y":
			client = connectToDB()
			db = client[dbName]
			game_list = convertListToDict(db[appList].find())
			sorted_game_list = sorted(game_list.items(),key=lambda item:item[0])
			target_collection = db[raw_collection]
			i = 0
			driver = Crawler.loginToSteamSpy()
			for game in sorted_game_list:
				if target_collection.count({"appid":game[0]})>0:
					print("Data already existed!")
					continue
				game_data = Crawler.getFormattedData(game[0],driver)
				print("Data retrieved(Appid: "+str(game[0])+")")
				insertSingleToDB(game_data,target_collection)
				print("Count: "+str(i))
				i += 1
                        driver.close()
	else:
		print("Invalid command! Please try again!")

if __name__ == "__main__":
	while True:
		print("------------------------New Game on Steam------------------------")
		print("1. Get the game list from Steam")
		print("2. Get games released in a certain time period")
		print("3. Monitoring Twitter Trends")
		print("4. Update SteamSpyDB")
		print("0. Exit")
		user_input = input("Please specify the number of the functionaility you wish to use:")
		res = parseUserInput(user_input)
		if res == 0:
			break
