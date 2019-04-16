import os
from datetime import datetime
import json
import urllib.request
import urllib.parse
import re
import event_sender
from pyaml import yaml


with open("credentials.yaml", "r") as creds_file:
	config = yaml.load(creds_file)

WITH_PROXY = False  # on/off proxy. Default is off

API_URL = config["group-ib"]["api_url"]
API_USER = config["group-ib"]["api_user"]  # your user
API_KEY = config["group-ib"]["api_key"]  # your API KEY

DATA_DIR = 'data/'  # directory for saving data

LIMIT = config["group-ib"]["api_limit"]  # limit for most data
BIG_DATA_LIMIT = config["group-ib"]["api_big_limit"]  # limit for big data

LANG_DEF = 1
LANG_RUS = 2
LANG_ENG = 3

# Send request to API
def send(action, last, lang):

	url = API_URL
	user = API_USER
	api_key = API_KEY

	if action == 'sample' or action == 'leaks':
		limit = BIG_DATA_LIMIT
	else :
		limit = LIMIT

	headers = {
		'Accept': 'application/json',
		'X-Auth-Login': user,
		'X-Auth-Key': api_key,
		'Connection': 'Keep-Alive',
		'Keep-Alive': 30
	}

	request_params = {
		"module": "get",
		"action": action,
		"limit": limit,
		"last": last
	}

	if lang is not None:
		request_params["lang"] = lang

	url = urllib.parse.urljoin(url, '?' + urllib.parse.urlencode(request_params))

	log('>>Request: ' + url)

	if WITH_PROXY:
		proxy_handler = '{"https": "https://127.0.0.1:3005"}'
		proxy_handler = json.loads(proxy_handler)
		proxy = urllib.request.ProxyHandler(proxy_handler)
		opener = urllib.request.build_opener(proxy)
		urllib.request.install_opener(opener)

	request = urllib.request.Request(url)

	for key, value in headers.items():
		request.add_header(key, value)

	handle = urllib.request.urlopen(request)
	response = handle.read().decode('utf-8')

	result = json.loads(response)

	try:
		error = result['error']
		raise Exception(error)
	except KeyError:
		pass

	try:
		count = result["data"]['count']
		last = result["data"]['last']
		limit = result["data"]['limit']
		count_new = len(result["data"]["new"])
		count_del = len(result["data"]["del"])
		log('<<Response param: count = {0}, last = {1}, limit = {2}, count new = {3}, count del = {4}'.format(count, last, limit, count_new, count_del))
	except KeyError:
		print('Bad response:' + response)

	return result


# Console loging
def log(str):
	now = datetime.now()
	str = "{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S}\t".format(now) + str
	print(str)


# Saving last value "last"
def set_last(action, last):
	hd = open(DATA_DIR + action + '.last', 'w')
	hd.write(str(last))


# Getting last value "last"
def get_last(action):
	try:
		hd = open(DATA_DIR + action + '.last', 'r')
	except OSError:
		return 0

	try:
		result = int(hd.read())
	except ValueError:
		result = 0
	return result


# Getting new data for section
def get_data(action, lang=None):
	log('Start load ' + action)

	dir = DATA_DIR + action

	if not os.path.exists(DATA_DIR):
		os.makedirs(DATA_DIR)

	last = get_last(action)
	total_new = 0

	while True:
		result = send(action, last, lang)

		if last == result["data"]["last"]:
			break

		last = result["data"]["last"]

		total_new += len(result["data"]["new"])

		if len(result["data"]["new"]) or len(result["data"]["del"]):
			event_sender.create_events(result, action)

		set_last(action, last)

	log('Total new: {0}'.format(total_new))
	log('=====================================================================')

if __name__ == "__main__":
	# compromised data
	get_data('accs')
	get_data('cards')
	get_data('imei')
	get_data('mules')

	# attacks
	get_data('ddos')

	# brand abuse
	get_data('domain')
	get_data('ssl')
	get_data('phishing')
	get_data('advert')
	get_data('mobileapp')
	get_data('phishingkit')

	# suspicious ip
	get_data('tornodes')
	get_data('proxy')
	get_data('socks')

	# leaks
	get_data('leaks')

	# hacktivism
	get_data('hacktivism', LANG_ENG)

	# targeted malware
	get_data('sample')

	# threats
	get_data('threats', LANG_ENG)
