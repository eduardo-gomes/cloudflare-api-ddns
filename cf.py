#%%
import requests
import json

import configparser

APIURL="https://api.cloudflare.com/client/v4/"

class authObj:
	APIKey = ""
	APIEmail = ""
	APIToken = ""
	AuthType = 0
	def getAuthHeader(self):
		header = dict()
		header["Content-Type"] = "application/json"
		if self.AuthType&1: #APIToken
			header["Authorization"] = "Bearer " + self.APIToken
		elif self.AuthType&2: #APIKey
			header["X-Auth-Key"] = self.APIKey
			header["X-Auth-Email"] = self.APIEmail
		else:
			print("Authentication not defined")
			raise RuntimeError
		return header
	def __init__(self, configAuth):
		self.AuthType = checkConfigAuthIsSet(configAuth)
		self.APIKey = configAuth.get('APIKey', '')
		self.APIEmail = configAuth.get('APIEmail', '')
		self.APIToken = configAuth.get('APIToken', '')

class address:
	ipv4 = requests.get('https://api.ipify.org').text
	ipv6 = requests.get('https://api6.ipify.org').text

class Record:
	A = False
	AAAA = False
	name = ""
	Id = ""
	Idv6 = ""
	ZoneId = ""
	ttl = 120
	def __init__(self, name:str, types):
		self.A = bool('A' in types)
		self.AAAA = bool('AAAA' in types)
		self.name = name
	def updateDNSRecord(self):
		URL = APIURL + "zones/" + self.ZoneId + "/dns_records/"
		if self.A:
			data = {"type": "A", "name":self.name, "content":address.ipv4, "ttl":self.ttl}
			response = requests.put(URL + self.Id, data=json.dumps(data), headers=headers)
			print("ipv4 " + str(response.status_code))
		if self.AAAA:
			data = {"type": "AAAA", "name":self.name, "content":address.ipv6, "ttl":self.ttl}
			response = requests.put(URL + self.Idv6, data=json.dumps(data), headers=headers)
			print("ipv6 " + str(response.status_code))

class Zone:
	Name = str()
	Id = str()
	def __init__(self, json):
		self.Name = json.get('name')
		self.Id = json.get('id')
	def CheckIfIsSubAddress(self, record:Record):
		RecordName = record.name
		isSubAddress = RecordName.find(self.Name) != -1
		return isSubAddress
	def GetIdToRecord(self, record:Record):
		URL = APIURL + "zones/" + self.Id + "/dns_records?name=" + record.name
		if record.A:
			recordv4 = requests.get(URL + "&type=A", headers=headers)
			recordv4 = json.loads(recordv4.text)
			if not int(recordv4.get("result_info").get("count")):
				raise RuntimeError("Record not found")
			record.Id = recordv4.get("result")[0].get("id")
		if record.AAAA:
			print(URL)
			recordv6 = requests.get(URL + "&type=AAAA", headers=headers)
			recordv6 = json.loads(recordv6.text)
			if not int(recordv6.get("result_info").get("count")):
				raise RuntimeError("Record not found")
			record.Idv6 = recordv6.get("result")[0].get("id")
		record.ZoneId = self.Id
		print(record.name, record.Id, record.Idv6)



def interactiveConfig(config_obj):
	print("interactive configuration")
	if not config_obj.has_section('AUTH'):
		config_obj.add_section('AUTH')
	configAuth = config['AUTH']
	if 'APIToken' not in configAuth:
		configAuth['APIToken'] = input("Enter APIToken: ")
	
def checkConfigAuthIsSet(config_auth):
	APIKeyAuthIsSet = ('APIKey' in config_auth) and ('APIEmail' in config_auth)
	APITokenAuthIsSet = ('APIToken' in config_auth)
	authenticationIsSet = (APIKeyAuthIsSet << 1) + APITokenAuthIsSet
	return authenticationIsSet

def checkConfig(config_obj):
	print("Verify config")
	sections = config_obj.sections()
	if 'AUTH' not in sections:
		print("AUTH section doesen't exist")
		raise RuntimeError
	else:
		if not checkConfigAuthIsSet(config_obj['AUTH']):
			print("No authentication is set")
			raise RuntimeError


config = configparser.ConfigParser()
try:
	with open('conf.ini') as file:
		config.read_file(file)
except IOError:
	print("Could't open conf.ini")
	interactiveConfig(config)
	checkConfig(config)

with open('conf.ini', 'w') as configfile:
   config.write(configfile)
auth = config['AUTH']
authHeader = authObj(auth)

## getZones

headers = authHeader.getAuthHeader()
zonesListStr = requests.get('https://api.cloudflare.com/client/v4/zones', headers=headers)

jsonzonesListStr = json.loads(zonesListStr.text)
#print(json.dumps(jsonzonesListStr, sort_keys=True, indent=4))
recordsList = list()
recordsList.append(Record("example.com", list(['A', 'AAAA'])))
zoneObjList = list()
for zoneJSON in jsonzonesListStr.get('result'):
	zone = Zone(zoneJSON)
	zoneObjList.append(zone)
	print(zone.Name, zone.Id, zone.CheckIfIsSubAddress(recordsList[0]))
#%%
for zone in zoneObjList:
	for record in recordsList:
		if zone.CheckIfIsSubAddress(record):
			zone.GetIdToRecord(record)
			record.updateDNSRecord()

# %%
