#!/usr/bin/python3
#%%
import requests
import json
import sys

import configparser

APIURL="https://api.cloudflare.com/client/v4/"

class authObj:
	APIKey = None
	APIEmail = None
	APIToken = None
	def getAuthHeader(self):
		header = dict()
		header["Content-Type"] = "application/json"
		if self.APIToken is not None: #APIToken
			header["Authorization"] = "Bearer " + self.APIToken
		else:
			print("Authentication not defined")
			raise RuntimeError("Authentication not defined")
		return header
	def __init__(self, configAuth):
		self.APIToken = configAuth.get('APIToken', '')

class address:
	ipv4 = None
	ipv6 = None


class Record:
	A = False
	AAAA = False
	name = None
	Id = None
	Idv6 = None
	ZoneId = None
	ttl = None
	def __init__(self, record_conf:configparser.SectionProxy):
		self.A = record_conf.getboolean('A', False)
		self.AAAA = record_conf.getboolean('AAAA', False)
		self.name = record_conf.name
		self.ttl = record_conf.getint('ttl', 120)
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
				raise RecordNotFoundInZone(self, record)
			record.Id = recordv4.get("result")[0].get("id")
		if record.AAAA:
			recordv6 = requests.get(URL + "&type=AAAA", headers=headers)
			recordv6 = json.loads(recordv6.text)
			if not int(recordv6.get("result_info").get("count")):
				raise RecordNotFoundInZone(self, record)
			record.Idv6 = recordv6.get("result")[0].get("id")
		record.ZoneId = self.Id
		print(record.name, record.Id, record.Idv6)

class RecordNotFoundInZone(Exception):
	def __init__(self, zone:Zone, record:Record):
		self.ZoneName = zone.Name
		self.ZoneId = zone.Id
		self.RecordName = record.name
		self.RecordId = record.Id
		self.RecordIdv6 = record.Idv6
	
	def __str__(self):
		return "Couldn't find record (" + self.RecordName + ") at zone (" + self.ZoneName + ")\ncheck if it exists"


def interactiveConfig(config_obj):
	print("interactive configuration")
	if not config_obj.has_section('AUTH'):
		config_obj.add_section('AUTH')
	configAuth = config['AUTH']
	if 'APIToken' not in configAuth:
		configAuth['APIToken'] = input("Enter APIToken: ")
	cont = True
	while cont:
		new_record = input('Record name: ')
		ipv6 = input('Use ipv6 [y/n]: ') 
		ipv4 = input('Use ipv4 [y/n]: ')
		ttl = int(input('Input TTL in seconds, 1 is automatic: '))
		config[new_record] = {'A': (ipv4 == "y") | (ipv4 == "Y"),
							'AAAA': (ipv6 == "y") | (ipv6 == "Y"),
							'ttl': ttl
							}
		add_new_record = input('Add New Record [y/n]: ')
		cont = (add_new_record == "y") | (add_new_record == "Y")
	return config_obj
	
def checkConfigAuthIsSet(config_auth):
	APITokenAuthIsSet = ('APIToken' in config_auth)
	return APITokenAuthIsSet

def checkConfig(config_obj):
	print("Verify config")
	sections = config_obj.sections()
	if 'AUTH' not in sections:
		print("AUTH section doesen't exist")
		raise KeyError
	elif not checkConfigAuthIsSet(config_obj['AUTH']):
		print("No authentication is set")
		raise KeyError
	elif (len(sections) < 2):
		print("No domain set")
		raise KeyError

#%%
config = configparser.ConfigParser()
configPath = sys.path[0] + '/' + 'conf.ini'
if '--config' in sys.argv:
	config = interactiveConfig(config)
	with open(configPath, 'w') as configfile:
		config.write(configfile)
else:
	try:
		with open(configPath) as file:
			config.read_file(file)
		checkConfig(config)
	except IOError:
		print("Could't open conf.ini")
		raise RuntimeError('Run with --config to setup the config file')
	except KeyError:
		print("invalid config")
		raise RuntimeError('Run with --config to setup the config file')

auth = config['AUTH']
authHeader = authObj(auth)

#%%
print("Try to get ip")
try:
	address.ipv4 = requests.get('https://api.ipify.org', timeout=15).text
	print("Got ipv4: " + address.ipv4)
except:
	print("Can't get ipv4")
try:
	address.ipv6 = requests.get('https://api6.ipify.org', timeout=15).text
	print("Got ipv6: " + address.ipv6)
except:
	print("Can't get ipv6")

## record config

config_records = config.sections().copy()
config_records.remove('AUTH')

## getZones

headers = authHeader.getAuthHeader()
zonesListStr = requests.get('https://api.cloudflare.com/client/v4/zones', headers=headers)

jsonzonesListStr = json.loads(zonesListStr.text)
#%%
recordsList = list()
for record_name in config_records:
	record_conf = config[record_name]
	recordsList.append(Record(record_conf))

zoneObjList = list()
for zoneJSON in jsonzonesListStr.get('result'):
	zone = Zone(zoneJSON)
	zoneObjList.append(zone)

#%%
for zone in zoneObjList:
	for record in recordsList:
		if zone.CheckIfIsSubAddress(record):
			zone.GetIdToRecord(record)
			record.updateDNSRecord()

