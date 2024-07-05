#!/usr/bin/python
# coding: utf-8

__author__ = 'T.ASAO <asao@sateraito.co.jp>'

import re
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
import datetime
import random
import json
import time
from dateutil import zoneinfo, tz
import hashlib
#import unicodedata
import pytz
import bcrypt

import apiclient
import google_auth_httplib2
import google.oauth2

from google.appengine.ext import ndb
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.api import namespace_manager

from googleapiclient.discovery import build

import sateraito_inc
import sateraito_black_list
from ucf.utils.ucfutil import *
import base64
#import httplib, urllib
from ucf.utils.ucfxml import UcfXml

LIST_LANGUAGE = [sateraito_inc.DEFAULT_LANGUAGE, 'en', 'vi', 'fr', 'ko', 'cn', 'th']

# 言語一覧
ACTIVE_LANGUAGES = ['ja', 'en']

# 言語メッセージID（key:言語ID、value:メッセージID）
LANGUAGES_MSGID = {
	'ja':'VMSG_LANG_JAPANESE',
	'en':'VMSG_LANG_ENGLISH',
	'zh-cn':'VMSG_LANG_CHINESE',
	'zh-tw':'VMSG_LANG_CHINESE_TRADITIONAL',
	'ko':'VMSG_LANG_KOREAN',
	'pt':'VMSG_LANG_PORTUGUESE',
	'fr':'VMSG_LANG_FRENCH',
	'de':'VMSG_LANG_GERMAN',
	'es':'VMSG_LANG_SPANISH',
	'hi':'VMSG_LANG_HINDI',
	'sv':'VMSG_LANG_SWEDISH',
	'fi':'VMSG_LANG_FINNISH',
	'it':'VMSG_LANG_ITALIAN',
	'id':'VMSG_LANG_INDONESIAN',
	'ru':'VMSG_LANG_RUSSIAN',
	'tl':'VMSG_LANG_TAGALOG',
	'mn':'VMSG_LANG_MONGOLIAN',
	'my':'VMSG_LANG_MYANMAR',
	'vi':'VMSG_LANG_VIETNAMESE',
	'ms':'VMSG_LANG_MALAYSIAN',
	'no':'VMSG_LANG_NORWEGIAN',
	'da':'VMSG_LANG_DANISH',
	'lo':'VMSG_LANG_LAO',
	'cs':'VMSG_LANG_CZECH',
	'tr':'VMSG_LANG_TURKISH',
}

# 有効なタイムゾーンリスト（長いので末尾に）
ACTIVE_TIMEZONES = [
		'Pacific/Midway',
		'Pacific/Niue',
		'Pacific/Pago_Pago',
		'Pacific/Honolulu',
		'Pacific/Rarotonga',
		'Pacific/Tahiti',
		'Pacific/Marquesas',
		'America/Anchorage',
		'Pacific/Gambier',
		'America/Los_Angeles',
		'America/Tijuana',
		'America/Vancouver',
		'America/Whitehorse',
		'Pacific/Pitcairn',
		'America/Dawson_Creek',
		'America/Denver',
		'America/Edmonton',
		'America/Hermosillo',
		'America/Mazatlan',
		'America/Phoenix',
		'America/Yellowknife',
		'America/Belize',
		'America/Chicago',
		'America/Costa_Rica',
		'America/El_Salvador',
		'America/Guatemala',
		'America/Managua',
		'America/Mexico_City',
		'America/Regina',
		'America/Tegucigalpa',
		'America/Winnipeg',
		'Pacific/Easter',
		'Pacific/Galapagos',
		'America/Bogota',
		'America/Cayman',
		'America/Grand_Turk',
		'America/Guayaquil',
		'America/Havana',
		'America/Iqaluit',
		'America/Jamaica',
		'America/Lima',
		'America/Montreal',
		'America/Nassau',
		'America/New_York',
		'America/Panama',
		'America/Port-au-Prince',
		'America/Rio_Branco',
		'America/Toronto',
		'America/Caracas',
		'America/Antigua',
		'America/Asuncion',
		'America/Barbados',
		'America/Boa_Vista',
		'America/Campo_Grande',
		'America/Cuiaba',
		'America/Curacao',
		'America/Guyana',
		'America/Halifax',
		'America/Manaus',
		'America/Martinique',
		'America/Port_of_Spain',
		'America/Porto_Velho',
		'America/Puerto_Rico',
		'America/Santiago',
		'America/Santo_Domingo',
		'America/Thule',
		'Antarctica/Palmer',
		'Atlantic/Bermuda',
		'America/St_Johns',
		'America/Araguaina',
		'America/Bahia',
		'America/Belem',
		'America/Cayenne',
		'America/Fortaleza',
		'America/Godthab',
		'America/Maceio',
		'America/Miquelon',
		'America/Montevideo',
		'America/Paramaribo',
		'America/Recife',
		'America/Sao_Paulo',
		'Antarctica/Rothera',
		'Atlantic/Stanley',
		'America/Noronha',
		'Atlantic/South_Georgia',
		'America/Scoresbysund',
		'Atlantic/Azores',
		'Atlantic/Cape_Verde',
		'Africa/Abidjan',
		'Africa/Accra',
		'Africa/Bamako',
		'Africa/Banjul',
		'Africa/Bissau',
		'Africa/Casablanca',
		'Africa/Conakry',
		'Africa/Dakar',
		'Africa/El_Aaiun',
		'Africa/Freetown',
		'Africa/Lome',
		'Africa/Monrovia',
		'Africa/Nouakchott',
		'Africa/Ouagadougou',
		'Africa/Sao_Tome',
		'America/Danmarkshavn',
		'Atlantic/Canary',
		'Atlantic/Faroe',
		'Atlantic/Reykjavik',
		'Atlantic/St_Helena',
		'Etc/UTC',
		'Europe/Lisbon',
		'Africa/Algiers',
		'Africa/Bangui',
		'Africa/Brazzaville',
		'Africa/Ceuta',
		'Africa/Douala',
		'Africa/Kinshasa',
		'Africa/Lagos',
		'Africa/Libreville',
		'Africa/Luanda',
		'Africa/Malabo',
		'Africa/Ndjamena',
		'Africa/Niamey',
		'Africa/Porto-Novo',
		'Africa/Tunis',
		'Africa/Windhoek',
		'Europe/Amsterdam',
		'Europe/Andorra',
		'Europe/Belgrade',
		'Europe/Berlin',
		'Europe/Brussels',
		'Europe/Budapest',
		'Europe/Copenhagen',
		'Europe/Gibraltar',
		'Europe/Luxembourg',
		'Europe/Madrid',
		'Europe/Malta',
		'Europe/Monaco',
		'Europe/Oslo',
		'Europe/Paris',
		'Europe/Prague',
		'Europe/Rome',
		'Europe/Stockholm',
		'Europe/Tirane',
		'Europe/Vienna',
		'Europe/Zurich',
		'Africa/Blantyre',
		'Africa/Bujumbura',
		'Africa/Cairo',
		'Africa/Gaborone',
		'Africa/Harare',
		'Africa/Johannesburg',
		'Africa/Kigali',
		'Africa/Lubumbashi',
		'Africa/Lusaka',
		'Africa/Maputo',
		'Africa/Maseru',
		'Africa/Mbabane',
		'Africa/Tripoli',
		'Asia/Amman',
		'Asia/Beirut',
		'Asia/Damascus',
		'Asia/Gaza',
		'Asia/Jerusalem',
		'Asia/Nicosia',
		'Europe/Athens',
		'Europe/Bucharest',
		'Europe/Chisinau',
		'Europe/Helsinki',
		'Europe/Istanbul',
		'Europe/Riga',
		'Europe/Sofia',
		'Europe/Tallinn',
		'Europe/Vilnius',
		'Africa/Addis_Ababa',
		'Africa/Asmara',
		'Africa/Dar_es_Salaam',
		'Africa/Djibouti',
		'Africa/Kampala',
		'Africa/Khartoum',
		'Africa/Mogadishu',
		'Africa/Nairobi',
		'Antarctica/Syowa',
		'Asia/Aden',
		'Asia/Baghdad',
		'Asia/Bahrain',
		'Asia/Kuwait',
		'Asia/Qatar',
		'Asia/Riyadh',
		'Europe/Kaliningrad',
		'Europe/Minsk',
		'Indian/Antananarivo',
		'Indian/Comoro',
		'Indian/Mayotte',
		'Asia/Tehran',
		'Asia/Baku',
		'Asia/Dubai',
		'Asia/Muscat',
		'Asia/Tbilisi',
		'Europe/Moscow',
		'Europe/Samara',
		'Indian/Mahe',
		'Indian/Mauritius',
		'Indian/Reunion',
		'Antarctica/Mawson',
		'Asia/Aqtau',
		'Asia/Aqtobe',
		'Asia/Ashgabat',
		'Asia/Dushanbe',
		'Asia/Karachi',
		'Asia/Tashkent',
		'Indian/Kerguelen',
		'Indian/Maldives',
		'Asia/Colombo',
		'Asia/Katmandu',
		'Antarctica/Vostok',
		'Asia/Almaty',
		'Asia/Bishkek',
		'Asia/Dhaka',
		'Asia/Thimphu',
		'Asia/Yekaterinburg',
		'Indian/Chagos',
		'Asia/Rangoon',
		'Indian/Cocos',
		'Antarctica/Davis',
		'Asia/Bangkok',
		'Asia/Hovd',
		'Asia/Jakarta',
		'Asia/Omsk',
		'Asia/Phnom_Penh',
		'Asia/Vientiane',
		'Indian/Christmas',
		'Antarctica/Casey',
		'Asia/Brunei',
		'Asia/Choibalsan',
		'Asia/Hong_Kong',
		'Asia/Krasnoyarsk',
		'Asia/Kuala_Lumpur',
		'Asia/Macau',
		'Asia/Makassar',
		'Asia/Manila',
		'Asia/Shanghai',
		'Asia/Singapore',
		'Asia/Taipei',
		'Asia/Ulaanbaatar',
		'Australia/Perth',
		'Asia/Dili',
		'Asia/Irkutsk',
		'Asia/Jayapura',
		'Asia/Pyongyang',
		'Asia/Seoul',
		'Asia/Tokyo',
		'Pacific/Palau',
		'Australia/Adelaide',
		'Australia/Darwin',
		'Antarctica/DumontDUrville',
		'Asia/Yakutsk',
		'Australia/Brisbane',
		'Australia/Hobart',
		'Australia/Sydney',
		'Pacific/Guam',
		'Pacific/Port_Moresby',
		'Pacific/Saipan',
		'Asia/Vladivostok',
		'Pacific/Efate',
		'Pacific/Guadalcanal',
		'Pacific/Kosrae',
		'Pacific/Noumea',
		'Pacific/Norfolk',
		'Asia/Kamchatka',
		'Asia/Magadan',
		'Pacific/Auckland',
		'Pacific/Fiji',
		'Pacific/Funafuti',
		'Pacific/Kwajalein',
		'Pacific/Majuro',
		'Pacific/Nauru',
		'Pacific/Tarawa',
		'Pacific/Wake',
		'Pacific/Wallis',
		'Pacific/Apia',
		'Pacific/Enderbury',
		'Pacific/Fakaofo',
		'Pacific/Tongatapu',
		'Pacific/Kiritimati'
	]

def datetimeToEpoch(d):
	return int(time.mktime(d.timetuple()))

def datetimeToUnixtime(datetime_param):
	return time.mktime(datetime_param.timetuple())

def epochTodatetime(epoch):
	return datetime.datetime(*time.localtime(epoch)[:6])

def toLocalTime(date_utc, timezone=sateraito_inc.DEFAULT_TIMEZONE):
	"""
	Args: data_utc ... datetime
	Returns: datetime
	"""
	if date_utc is None:
		return None
	tz_user_local = zoneinfo.gettz(timezone)
	return date_utc.replace(tzinfo=tz.tzutc()).astimezone(tz_user_local)

def toShortLocalTime(date_utc, timezone='Asia/Tokyo'):
	"""
	Args: date_utc ... datetime
	Returns: string YYYY-MM-DD HH:MI:SS
	"""
	local_time = toLocalTime(date_utc, timezone)
	# return (str(local_time).split('.'))[0]
	return (local_time.strftime('%Y-%m-%d %H:%M:%S.%f').split('.') if local_time is not None else str(local_time))[0]

# Bot Service addeed

def dateString():
	# create date string
	# GAEGEN2対応
	#dt_now = datetime.datetime.now()
	dt_now = datetime.datetime.utcnow()
	return dt_now.strftime('%Y%m%d%H%M%S')

def randomString(string_length=16):
	# create 16-length random string
	s = 'abcdefghijkmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
	random_string = ''
	for j in range(string_length):
		random_string += random.choice(s)
	return random_string

def randomShortString(string_length=6):
	# create 16-length random string
	s = 'abcdefghijkmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
	random_string = ''
	for j in range(string_length):
		random_string += random.choice(s)
	return random_string


def stringToDateTime(datetime_string):
	return datetime.datetime.strptime(datetime_string, "%Y/%m/%d %H:%M")

def stringToDateTimeLineRemind(datetime_string):
	return datetime.datetime.strptime(datetime_string, "%Y-%m-%d %H:%M:%S")

def dateTimeToString(_datetime):
	if _datetime is None:
		return None

	return _datetime.strftime("%Y/%m/%d %H:%M")

def dateTimeToStringFull(_datetime):
	if _datetime is None:
		return None

	return _datetime.strftime("%Y/%m/%d %H:%M:%S")

def dateTimeToString2(_datetime):
	if _datetime is None:
		return None

	return _datetime.strftime('%Y/%m/%d %H:%M')

def stringToDate(date_string):
	return datetime.datetime.strptime(date_string, "%Y/%m/%d")

def stringToDateMonth(date_string):
	return datetime.datetime.strptime(date_string, "%m/%d")

def strToBool(str_param):
	if str(str_param).lower() == 'true' or str(str_param).lower() == '1':
		return True
	return False

def generateConfirmationCode(string_length=32):
	random_string = randomString(string_length=string_length)
	return random_string

def timedeltaToTimeString(timedelta):
	timedelta_seconds = timedelta.seconds

	hours = timedelta_seconds // 3600

	remains = timedelta_seconds - (hours * 3600)

	minutes = remains / 60

	time_string = str(hours) + ":" + str(minutes)

	return time_string

def datetimeToYearMonthString(_datetime):
	return _datetime.strftime("%Y/%m")

def datetimeToYearMonthDayString(_datetime):
	return _datetime.strftime("%Y/%m/%d")

def dateToString(_date):
	if _date is not None:
		return _date.strftime("%Y/%m/%d")
	else:
		return ""

def boolToNumber(check):
	if check:
		return 1
	else:
		return 0

def timeToString(_time):
	return _time.strftime("%H:%M")

def datetimeStringtoDateString(datetimeString):
	datetime = stringToDateTime(datetimeString)
	date = datetime.strftime("%Y/%m/%d")
	return date

def datetimeStringtoDateString2(datetimeString):
	datetime = stringToDateTime(datetimeString)
	date = datetime.strftime("%Y-%m-%d")
	return date

def noneToEmptyString(obj):
	if obj is not None:
		return obj
	else:
		return ""

# タスクキューの追加自体がエラーする場合があるのでリトライ対応関数 2018.09.12
def addTaskQueue(t_q, task, max_retry_cnt=3):
	num_retry = 0
	while True:
		try:
			t_q.add(task)
			break
		except BaseException as e:
			logging.exception(e)
			if num_retry >= max_retry_cnt:
				raise e
			num_retry += 1
			# FrontEndsモジュールの場合もあるので控えめにスリープ...
			#sleep_time = timeToSleep(num_retry)
			sleep_time = num_retry * 1
			logging.info('num_retry is:%s sleeping %s...' % (num_retry, sleep_time))
			time.sleep(sleep_time)

# GAEGEN2対応:検索API移行
def getDomainFromNamespace(namespace_name):
	return namespace_name

# class to handle language wording
class MyLang():
	root_node = None

	def __init__(self, language):
		file_name = self.getFileName(language)
		folder_path = os.path.normpath(os.path.join(os.path.dirname(__file__), 'params'))
		xml_file_name = os.path.normpath(os.path.join(folder_path, 'lang', file_name))
		self.root_node = UcfXml.load(xml_file_name)

	def getFileName(self, language):
		file_name = 'ALL_ALL.xml'
		if language == 'en':
			file_name = 'ALL_ALL.xml'
		elif language == 'ja':
			file_name = 'ja_ALL.xml'

		return file_name

	def getMsgs(self):
		if self.root_node is None:
			return {}
		nodes = self.root_node.selectNodes('msg')
		dict = {}
		for node in nodes:
			name = node.getAttribute('name')
			message = node.getInnerText()
			if name is not None and name != '':
				dict[name] = message
		return dict

	def getMsg(self, code):
		if self.root_node is None:
			return ''
		node = self.root_node.selectSingleNode('msg[@name="' + code + '"]')
		message = ''
		if node is not None:
			message = node.getInnerText()
		return message

def toUtcTime(date_localtime, timezone=None):
	""" Args: date_localtime ... datetime
												timezone ... timezone name
				Return: datetime
		"""
	if date_localtime is None:
		return None
	if timezone is None:
		timezone = sateraito_inc.DEFAULT_TIMEZONE
		#  tz_user_local = zoneinfo.gettz('Asia/Tokyo')
	tz_user_local = zoneinfo.gettz(timezone)
	tz_utc = tz.tzutc()
	return date_localtime.replace(tzinfo=tz_user_local).astimezone(tz_utc)

def UtcToLocal(utc):
	if utc is None:
		return ""

	local_tz = pytz.timezone(sateraito_inc.DEFAULT_TIMEZONE)
	local_datetime = utc.replace(tzinfo=pytz.UTC).astimezone(local_tz)

	return dateTimeToString(local_datetime)

def TextShortent(string,char_number):
	remind_item_title_string = ""

	for item in string:
		remind_item_title_string += item

		if len(remind_item_title_string) > char_number:
			remind_item_title_string += "..."
			break

	return remind_item_title_string

# Check time with format 09:20
def checkTime(strtime):
	regexp = re.compile("(24:00|2?[0-3]:[0-5]?[0-9]|[0-1]?[0-9]:[0-5]?[0-9])")
	result = regexp.search(strtime)

	matched_result = None
	if result:
		matched_result = result.groups()
		matched_result = matched_result[0]

	return matched_result

def isSameList(list1, list2):
	if list1 is None:
		list1 = []
	if list2 is None:
		list2 = []
	return set(list1) == set(list2)

def isSameMembers(list_1, list_2):
	""" Args:
		list_1: list
		list_2: list
	Returns:
		boolean
	"""
	#set_1 = set(list_1)
	#set_2 = set(list_2)
	#if len(set_1 - set_2) == 0 and len(set_2 - set_1) == 0:
	#	return True
	#return False
	return isSameList(list_1, list_2)

# HTML文字列からリンクを判別しアンカータグに変換
def exchangeToHyperLinkHtml(html_text):
	result = html_text
	ptn_link = re.compile(r"(https?://[-_.!~*'()a-zA-Z0-9;/?:@&=+$,%#]+)")
	result = ptn_link.sub(r'!#!a href=!%!\1!%! target=!%!_blank!%! !$!\1!#!/a!$!', result)
	result = result.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
	result = result.replace('\n', '<br />\n')
	result = result.replace('!#!', '<').replace('!$!', '>').replace('!%!', '"')
	return result

# XMLエスケープ
def encodeXMLText(text):
	if text is None:
		return ''
	else:
		#return saxutils.escape(value)
		text = text.replace('&', '&amp;')
		text = text.replace('"', '&quot;')
		text = text.replace('\'', '&apos;')
		text = text.replace('<', '&lt;')
		text = text.replace('>', '&gt;')
		return text

def addUpdateUserEntryTaskQueue(tenant, operator_entry):

	try:

		# token作成
		token = UcfUtil.guid()
		params = {
				'user_email': operator_entry.operator_id_lower,
				'is_admin': 'ADMIN' in operator_entry.access_authority if operator_entry.access_authority is not None else False,
		}
		# taskに追加 まるごと
		import_q = taskqueue.Queue('userentry-set-queue')
		import_t = taskqueue.Task(
				url='/a/' + tenant + '/openid/' + token + '/regist_user_entry',
				params=params,
				target='default',
				countdown='0'
		)
		import_q.add(import_t)
		logging.info('add task queue userentry-set-queue')

	except Exception as e:
		logging.info('failed add update user entry taskqueue. tenant=' + tenant + ' user=' + operator_entry.operator_id)
		logging.exception(e)

def checkCsrf(request):
	'''
		AJax の Post で呼び出されたリクエストの CSRF（クロスサイトリクエストフォージェリ）をチェック。
		問題がない場合は True を返す
	'''

	if sateraito_inc.developer_mode:
		return True

	headers = request.headers

	strHost = headers.get('Host')
	strOrigin = headers.get('Origin')
	strXRequestedWith = headers.get('X-Requested-With') 

	#if (strHost != sateraito_inc.site_fqdn):
	if (strHost != sateraito_inc.site_fqdn):
		logging.error('Invalid Request Header : Host : ' + str(strHost))
		return False

	#if ((strOrigin is not None) and (strOrigin != sateraito_inc.my_site_url)):
	if ((strOrigin is not None) and (strOrigin != sateraito_inc.my_site_url)):
		logging.error('Invalid Request Header : Origin : ' + str(strOrigin))
		return False

	if (strXRequestedWith != 'XMLHttpRequest'):
		logging.error('Invalid Request Header : X-Requested-With : ' + str(strXRequestedWith))
		return False

	logging.info('csrf check is ok.')
	return True

def get_all_tenant_entry():
	results = []
	start = 0
	limit = 100

	#q = Namespace.all()
	#domain_list = []
	#for row in q:
	#	if row.namespace_name != '':
	#		domain_list.append(row.namespace_name)

	q = TenantEntry.all()
	fetch_data = None
	if q:
		each_entrys = None
		while each_entrys is None or len(each_entrys) > 0:
			each_entrys = []
			fetch_data = q.fetch(limit, start)
			for entry in fetch_data:
				each_entrys.append(entry)
			results.extend(each_entrys)
			start += limit
	return results

# ユーザエントリの登録、更新
def registUserEntry(user_email, is_admin, is_disable_user, sign_with='', email_verified=False):
	strOldNamespace = namespace_manager.get_namespace()
	namespace_manager.set_namespace('')

	logging.info('registUserEntry...')
	logging.info('user_email=' + user_email)
	logging.info('is_admin=' + str(is_admin))
	user_email = user_email.lower()
	try:
		# check user entry in datastore
		user_entry = UserEntry.getInstance(user_email)
		if user_entry is None:
			# create user entry on Datastore
			new_user_entry = UserEntry(id=user_email)
			new_user_entry.user_email = user_email
			new_user_entry.sign_with = sign_with
			new_user_entry.disable_user = False

			if is_admin:
				new_user_entry.is_admin = True
			else:
				new_user_entry.is_admin = False
			new_user_entry.put()
		else:
			if user_entry.user_email == user_email and user_entry.sign_with != sign_with:
				return False, 'Email with other registered users'

			# update user entry on Datastore
			if is_admin:
				user_entry.is_admin = True
			else:
				user_entry.is_admin = False
			user_entry.put()

		namespace_manager.set_namespace(strOldNamespace)
		return True, ''
	except Exception as error:
		namespace_manager.set_namespace(strOldNamespace)
		raise error

def getDomainPart(p_email_address):
	a_email_address = p_email_address.split('@')
	return a_email_address[1] if len(a_email_address) > 1 else ''

def getUserIDPart(p_email_address):
	a_email_address = p_email_address.split('@')
	return a_email_address[0]

# TenantEntryに1件登録（存在しない場合だけ.以降はタスクで処理）
def insertTenantEntry(tenant, is_free_mode=True):
	tenant = tenant.lower()
	q = TenantEntry.gql("where tenant = :1", tenant.lower())
	tenant_entry = q.get()
	if tenant_entry is None:
		tenant_entry = TenantEntry()
		tenant_entry.tenant = tenant
		tenant_entry.num_users = 0
		tenant_entry.max_users = 0
		tenant_entry.available_users = sateraito_inc.DEFAULT_AVAILABLE_USERS
		tenant_entry.is_free_mode = is_free_mode
		tenant_entry.is_disable = False

		# インストールセット公開に伴い30日利用制限をかける対応 2014.03.10
		# GAEGEN2対応
		#dt_now = datetime.datetime.now()
		dt_now = datetime.datetime.utcnow()
		dt_expire = UcfUtil.add_days(dt_now, 30)		# 当日を入れて31日（厳密でなくてもよいとは思うが...）
		tenant_entry.available_start_date = dt_now.strftime('%Y/%m/%d')
		tenant_entry.charge_start_date = dt_expire.strftime('%Y/%m/%d')
		tenant_entry.cancel_date = dt_expire.strftime('%Y/%m/%d')

		tenant_entry.put()
	return tenant_entry

def setNumTenantUser(tenant, tenant_entry, num_users, max_users=None):
	'''
	Set number of domain users
	'''

	old_namespace = namespace_manager.get_namespace()
	namespace_manager.set_namespace('')

	if tenant_entry is None:
		tenant = tenant.lower()
		q = TenantEntry.all()
		q.filter('tenant =', tenant)
		tenant_entry = q.get()
	if tenant_entry is not None:
		is_need_edit = False
		if tenant_entry.num_users is None or tenant_entry.num_users < num_users:
			tenant_entry.num_users = num_users
			is_need_edit = True
		if max_users is not None and (tenant_entry.max_users is not None or tenant_entry.max_users < max_users):
			tenant_entry.max_users = max_users
			is_need_edit = True
		if is_need_edit:
			tenant_entry.updated_date = UcfUtil.getNow()
			tenant_entry.put()
	namespace_manager.set_namespace(old_namespace)

# 最終利用月を更新
def updateDomainLastLoginMonth(tenant):
	strOldNamespace = namespace_manager.get_namespace()
	namespace_manager.set_namespace('')
	try:
		q = TenantEntry.all()
		q.filter('tenant =', tenant.lower())
		tenant_entry = q.get()
		is_updated = False
		if tenant_entry is not None:
			is_updated = tenant_entry.updateLastLoginMonth()
		namespace_manager.set_namespace(strOldNamespace)
		return is_updated
	except Exception as error:
		namespace_manager.set_namespace(strOldNamespace)
		raise error
	return False

# テナントエントリーを取得
def getTenantEntry(tenant):
	strOldNamespace = namespace_manager.get_namespace()
	namespace_manager.set_namespace('')

	tenant_entry = None
	try:

		q = TenantEntry.all(keys_only=True)
		q.filter('tenant =', tenant.lower())
		tenant_entry = TenantEntry.getByKey(q.get())

		namespace_manager.set_namespace(strOldNamespace)
		return tenant_entry
	except Exception as error:
		namespace_manager.set_namespace(strOldNamespace)
		raise error

# フリーモードかどうかを取得
def isFreeMode(tenant, is_with_cache=True):
	tenant = tenant.lower()
	strOldNamespace = namespace_manager.get_namespace()
	namespace_manager.set_namespace('')
	try:
		memcache_key = 'isfreemode?tenant=' + tenant.lower()

		is_free_mode = None
		if is_with_cache:
			is_free_mode = memcache.get(memcache_key)

		if is_free_mode is None:
			entry = getTenantEntry(tenant)
			if entry is not None:
				is_free_mode = entry.is_free_mode

		if is_free_mode is not None:
			memcache.set(key=memcache_key, value=is_free_mode, time=300)

		namespace_manager.set_namespace(strOldNamespace)

		if is_free_mode is None:
			is_free_mode = True

		return is_free_mode
	except Exception as error:
		namespace_manager.set_namespace(strOldNamespace)
		raise error

# 無効テナントかどうかを取得
def isTenantDisabled(tenant):

	row = TenantEntry.getInstance(tenant, cache_ok=True)
	if row is None:
		return True

	is_need_update = False
	if row.is_disable is None:
		row.is_disable = False
		is_need_update = True
	if row.available_start_date is None:
		row.available_start_date = ''
		is_need_update = True
	if row.charge_start_date is None:
		row.charge_start_date = ''
		is_need_update = True
	if row.cancel_date is None:
		row.cancel_date = ''
		is_need_update = True
	if is_need_update:
		row.put()

	if row.is_disable == True:
		return True

	# 解約日をチェックするように対応 2013/11/13
	if row is not None and row.cancel_date != '':
		#now = UcfUtil.getNow()	# 標準時
		#cancel_date = UcfUtil.add_days(UcfUtil.getDateTime(row.cancel_date), 1)	# 解約日は利用可とするため1日たしておく
		#return now >= cancel_date
		return isExpireAvailableTerm(row)

	return False

# 解約日が過ぎていないかをチェック
def isExpireAvailableTerm(tenant_entry):
	# 解約日をチェックするように対応 2013/11/13
	if tenant_entry.cancel_date is not None and tenant_entry.cancel_date != '':
		now = UcfUtil.getNow()	# 標準時
		cancel_date = UcfUtil.add_days(UcfUtil.getDateTime(tenant_entry.cancel_date), 1)	# 解約日は利用可とするため1日たしておく
		return now >= cancel_date
	return False

# トライアル期間内かを判定
def isInTrialTerm(tenant_entry):
	if tenant_entry.charge_start_date is not None and tenant_entry.charge_start_date != '':
		now = UcfUtil.getNow()	# 標準時
		charge_start_date = UcfUtil.getDateTime(tenant_entry.charge_start_date)
		return now < charge_start_date
	return False

def exchangeLanguageCode(lang):
	return lang

def getActiveLanguage(language, hl=sateraito_inc.DEFAULT_LANGUAGE):
	language = exchangeLanguageCode(language)
	return language if language in ACTIVE_LANGUAGES else hl

def getActiveTimeZone(timezone, default_timezone=sateraito_inc.DEFAULT_TIMEZONE):
	return timezone if timezone in ACTIVE_TIMEZONES else default_timezone

# 使用するExtJsのlocaleファイル名をファイル名を決定
def getExtJsLocaleFileName(lang):

	lang = lang.lower()

	logging.info('getExtJsLocaleFileName....')
	logging.info('lang=' + lang)

	locale_file = 'ext-lang-en.js'
	if lang == 'en':
		locale_file = 'ext-lang-en.js'
	elif lang == 'en_bg':
		locale_file = 'ext-lang-en_GB.js'
	elif lang == 'cn' or lang == 'zh-cn' or lang == 'zh_cn':
		locale_file = 'ext-lang-zh_CN.js'
	elif lang == 'zh-tw' or lang == 'zh_tw':
		locale_file = 'ext-lang-zh_TW.js'
	elif lang == 'ja' or lang == 'ja-jp' or lang == 'ja_jp':
		locale_file = 'ext-lang-ja.js'
	elif lang == 'ko' or lang == 'ko-kr' or lang == 'ko_kr':
		locale_file = 'ext-lang-ko.js'
	elif lang == 'pt':
		locale_file = 'ext-lang-pt.js'
	elif lang == 'pt-br' or lang == 'pt_br':
		locale_file = 'ext-lang-pt_BR.js'
	elif lang == 'fr' or lang == 'fr-be' or lang == 'fr-lu' or lang == 'fr-ch':
		locale_file = 'ext-lang-fr.js'
	elif lang == 'fr-ca':
		locale_file = 'ext-lang-fr_CA.js'
	elif lang == 'sv' or lang == 'sv_se':
		locale_file = 'ext-lang-sv_SE.js'
	elif lang == 'fi':
		locale_file = 'ext-lang-fi.js'
	elif lang == 'de':
		locale_file = 'ext-lang-de.js'
	#elif lang == 'hi':
	#	locale_file = 'ext-lang-.js'
	elif lang == 'es':
		locale_file = 'ext-lang-es.js'
	elif lang == 'it':
		locale_file = 'ext-lang-it.js'
	# ext-lang-th.js はタイ語ではないようなのでコメントアウト 2019.09.27
	#elif lang == 'th':
	#	locale_file = 'ext-lang-th.js'
	elif lang == 'ru':
		locale_file = 'ext-lang-ru.js'
	elif lang == 'id':
		locale_file = 'ext-lang-id.js'
	elif lang == 'vi':
		locale_file = 'ext-lang-vn.js'
	elif lang == 'cs':
		locale_file = 'ext-lang-cs.js'
	elif lang == 'da':
		locale_file = 'ext-lang-da.js'
	elif lang == 'no':
		locale_file = 'ext-lang-no_NN.js'
	elif lang == 'tr':
		locale_file = 'ext-lang-tr.js'


	logging.info('locale_file=' + locale_file)

	return locale_file

# 旧タイムゾーン設定値から新タイムゾーン設定値への補正用
def exchangeTimeZoneCode(timezone):
	if timezone == '-12':
		timezone = 'Pacific/Midway'		# -12がないので
	elif timezone == '-11':
		timezone = 'Pacific/Niue'		#
	elif timezone == '-10':
		timezone = 'Pacific/Honolulu'		#
	elif timezone == '-9':
		timezone = 'America/Anchorage'		#
	elif timezone == '-8':
		timezone = 'America/Los_Angeles'		#
	elif timezone == '-7':
		timezone = 'America/Denver'		#
	elif timezone == '-6':
		timezone = 'America/Chicago'		#
	elif timezone == '-5':
		timezone = 'America/New_York'		#
	elif timezone == '-4':
		timezone = 'America/Santiago'		#
	elif timezone == '-3':
		timezone = 'America/Sao_Paulo'		#
	elif timezone == '-2':
		timezone = 'America/Noronha'		#
	elif timezone == '-1':
		timezone = 'Atlantic/Azores'		#
	elif timezone == '0':
		timezone = 'Etc/UTC'		#
	elif timezone == '+1':
		timezone = 'Europe/Prague'		#
	elif timezone == '+2':
		timezone = 'Europe/Athens'		#
	elif timezone == '+3':
		timezone = 'Asia/Qatar'		#
	elif timezone == '+4':
		timezone = 'Europe/Moscow'		#
	elif timezone == '+5':
		timezone = 'Asia/Karachi'		#
	elif timezone == '+6':
		timezone = 'Asia/Dhaka'		#
	elif timezone == '+7':
		timezone = 'Asia/Bangkok'		#
	elif timezone == '+8':
		timezone = 'Asia/Kuala_Lumpur'		#
	elif timezone == '+9':
		timezone = 'Asia/Tokyo'		#
	elif timezone == '+10':
		timezone = 'Australia/Sydney'		#
	elif timezone == '+11':
		timezone = 'Pacific/Guadalcanal'		#
	elif timezone == '+12':
		timezone = 'Pacific/Auckland'		#
	elif timezone == '+13':
		timezone = 'Pacific/Tongatapu'		#
	elif timezone == '+14':
		timezone = 'Pacific/Kiritimati'		#
	#else:
	#	timezone = sateraito_inc.DEFAULT_TIMEZONE		#
	return timezone

def getDomainPart(email_address):
	a_email_address = email_address.split('@')
	if len(a_email_address) > 1:
		return a_email_address[1]
	else:
		return ''

def logoutIfUserDisabled(helper, viewer_email, user_entry=None):

	if user_entry is None:
		logging.info("logoutIfUserDisabled viewer_email=%s" % str(viewer_email))
		user_entry = UserEntry.getInstance(viewer_email)

	need_logout = False
	if user_entry is None:
		logging.info("logoutIfUserDisabled user_entry=%s" % str(user_entry))
		need_logout = True
	
	elif user_entry.disable_user:
		logging.info("logoutIfUserDisabled user_entry.disable_user=%s" % str(user_entry.disable_user))
		need_logout = True

	logging.info("logoutIfUserDisabled=%s" % str(need_logout))
	
	if need_logout:
		# clear session value
		helper.setSession('viewer_email', '')
		helper.setSession('loggedin_timestamp', None)  # G Suiteのマルチログイン時にiframe内でOIDC認証ができなくなったので強制で少しだけ高速化オプションする対応＆SameSite対応 2019.10.28
		helper.setSession('opensocial_viewer_id', '')
		helper.setSession('is_oidc_loggedin', False)
		helper.setSession('is_oidc_need_show_signin_link', False)

		# clear openid connect session
		helper.removeAppsCookie()

		return True
	
	return False

# SameSiteをU/Aで判別して自動付与する対応
# SameSite対応…SameSite=NoneをつけるかどうかをU/Aで判断
def isSameSiteCookieSupportedUA(strAgent):

	# エクセルビルダーを開いた場合に strAgent=AppEngine-Google; (+http://code.google.com/appengine) のような値が入る
	# デフォルトをTrueにしてiOS12の場合だけFalseになるよう変更 2023-06-22
	# is_supported = False
	is_supported = True

	if strAgent is None:
		strAgent = ''

	strAgent = strAgent.lower()

	# iOS12の場合はセットしない
	if strAgent.find('AppleWebKit'.lower())>=0 and (strAgent.find('iPhone'.lower()) >= 0 or strAgent.find('iPad'.lower()) >= 0) and strAgent.find('OS 12_'.lower()) >= 0:
		is_supported = False
	## それ以外のiOSは対象にしてみる 2020.11.10
	#elif strAgent.find('AppleWebKit'.lower())>=0 and (strAgent.find('iPhone'.lower()) >= 0 or strAgent.find('iPad'.lower()) >= 0):
	#		is_supported = True
	# まずはスモールスタートで Chromeのみセットしてみる
	# セキュリティブラウザ、Teamsアプリを除外 2019.12.12
	#elif (strAgent.find('Chrome'.lower())>=0 or strAgent.find('CriOS'.lower())>=0) and strAgent.find('Edge'.lower())<0 and strAgent.find('Edg/'.lower())<0:
	# Chromeの旧バージョンをざっくり除外（Ver 63などでSameSite=NoneがついているとNGなことが分かったので） 2019.12.13
	#elif (strAgent.find('Chrome'.lower())>=0 or strAgent.find('CriOS'.lower())>=0) and strAgent.find('Edge'.lower())<0 and strAgent.find('Edg/'.lower())<0 and strAgent.find('/SateraitoSecurityBrowser'.lower())<0 and strAgent.find('Teams/'.lower())<0:
	#elif (strAgent.find('Chrome'.lower())>=0 or strAgent.find('CriOS'.lower())>=0) and strAgent.find('Edge'.lower())<0 and strAgent.find('Edg/'.lower())<0 and strAgent.find('/SateraitoSecurityBrowser'.lower())<0 and strAgent.find('Teams/'.lower())<0 and (strAgent.find('Chrome/6'.lower())<0 and strAgent.find('Chrome/5'.lower())<0):
	# セキュリティブラウザの判定を除外 2021.02.10
	#elif (strAgent.find('Chrome'.lower())>=0 or strAgent.find('CriOS'.lower())>=0) and strAgent.find('/SateraitoSecurityBrowser'.lower())<0 and strAgent.find('Teams/'.lower())<0 and (strAgent.find('Chrome/6'.lower())<0 and strAgent.find('Chrome/5'.lower())<0):
	elif (strAgent.find('Chrome'.lower())>=0 or strAgent.find('CriOS'.lower())>=0) and strAgent.find('Teams/'.lower())<0 and (strAgent.find('Chrome/6'.lower())<0 and strAgent.find('Chrome/5'.lower())<0):
		is_supported = True
	elif (strAgent.find('firefox')>=0): # Firefox を追加
		is_supported = True

	## どのブラウザもSameSite=Noneつけても大丈夫そうなのでオールTrueに変更 2019.12.09
	#if not is_supported:
	#	is_supported = True
	#	logging.info('forced set to true.')


	logging.debug('isSameSiteCookieSupportedUA=%s' % (is_supported))
	return is_supported


API_TIMEOUT_SECONDS = 10
API_TIMEOUT_SECONDS_DRIVE = (60 * 60 * 1)

def get_authorized_http(viewer_email, google_apps_domain, scope=sateraito_inc.OAUTH2_SCOPES, timeout_seconds=API_TIMEOUT_SECONDS, is_sub=False):
	logging.info('get_authorized_http')
	if is_sub is True:
		logging.debug('is_sub:True')

	logging.debug('=========get_authorized_http:scope===============')
	logging.debug(scope)

	old_namespace = namespace_manager.get_namespace()
	logging.debug(old_namespace)
	try:
		namespace_manager.set_namespace(google_apps_domain)
		memcache_expire_secs = 60 * 60 * 1
		memcache_key = 'script=getauthorizedhttp&v=2&google_apps_domain=' + google_apps_domain + '&email_to_check=' + viewer_email + '&scope=' + str(scope) + '&g=2'

		# （参考）https://developers.google.com/identity/protocols/oauth2/service-account
		service_account_info = sateraito_inc.service_account_info
		credentials = google.oauth2.service_account.Credentials.from_service_account_info(
			service_account_info,
			scopes=scope,
		)
		credentials = credentials.with_subject(viewer_email)
		dict_token_info = memcache.get(memcache_key)
		# @UndefinedVariable
		bool_token_is_valid = False
		if dict_token_info:
			logging.debug('get_authorized_http: cache found.')
			credentials.token = dict_token_info.get('token')
			credentials.expiry = dict_token_info.get('expiry')
			bool_token_is_valid = credentials.valid

		if not bool_token_is_valid:
			http = apiclient.http.build_http()
			request = google_auth_httplib2.Request(http)
			credentials.refresh(request)
			if credentials.valid:
				dict_token_info = {
					'token': credentials.token,
					'expiry': credentials.expiry,
				}
				if not memcache.set(key=memcache_key, value=dict_token_info, time=memcache_expire_secs):  # @UndefinedVariable
					logging.warning("get_authorized_http: Memcache set failed.")
				else:
					logging.warning('get_authorized_http: credentials.refresh')

			logging.debug('credentials.token	= ' + str(credentials.token))
			logging.debug('credentials.expiry = ' + str(credentials.expiry))

		# return http
		return credentials
	except Exception as e:
		logging.exception(e)
	finally:
		# set old namespace
		namespace_manager.set_namespace(old_namespace)

def get_gmail_service(viewer_email, google_apps_domain):
	# http = get_authorized_http(viewer_email, google_apps_domain, sateraito_inc.OAUTH2_SCOPES_GMAIL)
	credentials = get_authorized_http(viewer_email, google_apps_domain, sateraito_inc.OAUTH2_SCOPES_GMAIL)
	return build('gmail', 'v1', credentials=credentials)

def getBodyInPart(item_part):
  body = None
  try:
    # item_partid = item_part['partId']
    item_file_name = item_part['filename']
    item_mime_type = item_part['mimeType']
    item_body = item_part['body']
    if item_mime_type == 'text/plain' and item_file_name == '' and item_body:
      if 'data' in item_body and item_body['data']:
        body = base64.urlsafe_b64decode(item_body['data'].encode('UTF-8'))

    if body is None:
      if 'parts' in item_part:
        sub_parts = item_part['parts']
        for item in sub_parts:
          body = getBodyInPart(item)
          if body:
            break

  except Exception as e:
    logging.error(e)

  return body

def parseEmail(data):
  email = ''
  if data is None:
    return email
  # data_decode = data.decode('unicode-escape')
  list = re.findall(r'[\w\.-]+@[\w\.-]+', data)
  if len(list) > 0:
    email = sateraito_inc.KEY_SPLIT_RAW.join(list)
  return email

def getEmailMessage(google_apps_domain, email, message_id, is_draft=False):
    logging.info('=======getEmailMessage==========')
    # logging.info(message_id)
    # logging.info(email)
	
    data = {
      'msg_id': message_id,
      'subject': '',
      'body': '',
      'from': '',
      'to': ''
    }
	
    try:
      gmail_service = get_gmail_service(email, google_apps_domain)
      if gmail_service:
        if is_draft:
          result = gmail_service.users().drafts().get(userId=email, id=message_id).execute()
          payload = result['message']['payload']
        else:
          result = gmail_service.users().messages().get(userId=email, id=message_id).execute()
          payload = result['payload']

        logging.info(str(result))
        logging.info(str(payload))

        if payload:
          # HEADER
          headers = payload.get('headers')
          for item in headers:
            if item['name'] == 'From':
              data['from'] = parseEmail(item['value'])
            if item['name'] == 'To':
              data['to'] = parseEmail(item['value'])
            if item['name'] == 'Cc':
              data['cc'] = parseEmail(item['value'])
            if item['name'] == 'Bcc':
              data['bcc'] = parseEmail(item['value'])
            if item['name'] == 'Subject':
              data['subject'] = item['value']

          # PARTS
          parts = payload.get('parts')
          for item2 in parts:
            body = getBodyInPart(item2)
            if body:
              data['body'] = str(body.decode())
              break
    except Exception as e:
      logging.error(e)

    return data