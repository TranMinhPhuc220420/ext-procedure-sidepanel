#!/usr/bin/python
# coding: utf-8

import sys

# GAEGEN2対応:実装の意図が不明だが取り急ぎコメントアウト
#stdin = sys.stdin
#stdout = sys.stdout
#reload(sys)
#sys.setdefaultencoding('utf-8')
#sys.stdin = stdin
#sys.stdout = stdout

import json
import hashlib
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging

import time
import datetime

from google.appengine.ext import ndb
from google.appengine.api import memcache
from google.appengine.api import namespace_manager

import public_api_db


# check key will valid in current server time +- 5 minus
MARGIN_MINUTES_BEFORE = 5
MARGIN_MINUTES_AFTER = 5


def get_memcached_api_key_list():
	key_name = "PUBLIC_API_KEYS"
	api_keys = memcache.get(key_name)
	return api_keys


def set_memcached_api_key_list(api_keys):
	key_name = "PUBLIC_API_KEYS"
	memcache.set(key_name, api_keys)


def delete_memcached_api_key_list():
	key_name = "PUBLIC_API_KEYS"
	memcache.delete(key_name)


def api_key_create(creator_email):
	api_key_info = public_api_db.PublicApiKey.create_api_key(creator_email)
	delete_memcached_api_key_list()
	return api_key_info


def api_key_delete(unique_id):
	result = public_api_db.PublicApiKey.delete_api_key(unique_id)
	delete_memcached_api_key_list()
	return result


def api_key_list():
	api_keys = get_memcached_api_key_list()
	if api_keys is None:
		api_keys = public_api_db.PublicApiKey.list_api_key()
		set_memcached_api_key_list(api_keys)

	return api_keys


def api_key_only_list():
	api_keys = api_key_list()
	if not api_keys:
		return []

	only_api_keys = [api_key_info['api_key'] for api_key_info in api_keys]

	return only_api_keys


def api_key_safe_list():
	api_keys = api_key_list()
	if not api_keys:
		return []

	for api_key_info in api_keys:
		api_key = api_key_info['api_key']
		api_key_hidden = api_key_hide(api_key)
		api_key_info['api_key'] = api_key_hidden

	return api_keys


def api_key_hide(api_key):
	api_key_hidden = api_key[0:16] + '*' * 16
	return api_key_hidden


def api_create_check_key(tenant, api_key, check_time=None):
	if check_time is None:
		# now = datetime.datetime.now()
		now = datetime.datetime.utcnow()
		check_time = now

	check_key_string = tenant + check_time.strftime('%Y%m%d%H%M') + api_key
	md5_value = hashlib.md5()
	md5_value.update(check_key_string)
	check_key = md5_value.hexdigest()

	return check_key


def api_verify_check_key(check_key, tenant, api_key, check_time=None, minutes_before=MARGIN_MINUTES_BEFORE, minutes_after=MARGIN_MINUTES_AFTER):
	if check_time is None:
		# now = datetime.datetime.now()
		now = datetime.datetime.utcnow()
		check_time = now

	check_key_generated = api_create_check_key(tenant, api_key, check_time=check_time)
	if check_key == check_key_generated:
		return True

	# if minutes_before > 0:
	# 	for i in range(0, minutes_before):
	# 		minutes_before_sub = i + 1
	# 		time_before = datetime.timedelta(minutes=minutes_before_sub)
	# 		check_time_before = check_time - time_before
	# 		check_key_generated_before = api_create_check_key(tenant, api_key, check_time=check_time_before)
	# 		if check_key == check_key_generated_before:
	# 			return True
	#
	# if minutes_after > 0:
	# 	for i in range(0, minutes_after):
	# 		minutes_after_add = i + 1
	# 		time_after = datetime.timedelta(minutes=minutes_after_add)
	# 		check_time_after = check_time + time_after
	# 		check_key_generated_after = api_create_check_key(tenant, api_key, check_time=check_time_after)
	# 		if check_key == check_key_generated_after:
	# 			return True

	# check both this way we can do it faster
	minutes_margin = max(minutes_before, minutes_after)
	if minutes_margin > 0:
		for i in range(0, minutes_margin):
			if i < minutes_before:
				minutes_before_sub = i + 1
				time_before = datetime.timedelta(minutes=minutes_before_sub)
				check_time_before = check_time - time_before
				check_key_generated_before = api_create_check_key(tenant, api_key, check_time=check_time_before)
				if check_key == check_key_generated_before:
					return True

			if i < minutes_after:
				minutes_after_add = i + 1
				time_after = datetime.timedelta(minutes=minutes_after_add)
				check_time_after = check_time + time_after
				check_key_generated_after = api_create_check_key(tenant, api_key, check_time=check_time_after)
				if check_key == check_key_generated_after:
					return True

	return False


def api_create_access_token(expire_seconds):
	access_token = public_api_db.PublicAccessToken.create_access_token(expire_seconds)

	return access_token


def api_refresh_access_token(access_token, expire_seconds):
	result = public_api_db.PublicAccessToken.refresh_access_token(access_token, expire_seconds)

	return result


def api_revoke_access_token(access_token):
	result = public_api_db.PublicAccessToken.revoke_access_token(access_token)

	return result


def api_verify_access_token(access_token):
	is_valid = public_api_db.PublicAccessToken.check_access_token(access_token)

	return is_valid
