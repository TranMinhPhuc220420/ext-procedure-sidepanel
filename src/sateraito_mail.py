#!/usr/bin/python
# coding: utf-8

__author__ = 'Akitoshi Abe <abe@baytech.co.jp>'

# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
import json
import datetime
import random

import urllib

from google.appengine.api import mail
from google.appengine.api import urlfetch

from ucf.utils.ucfutil import UcfUtil

# import sateraito_inc

'''
sateraito_mail.py Python3 version

@since: 2017-11-21
@version: 2023-06-15
@author: Akitoshi Abe
'''


# この値は利用するアドオンごとに変更してください
SENDER_ADDON_PROJECT_ID = 'sateraito-notification'

# この値は必要に応じて変更してください（サテライトメールサーバーに登録済みのアドレスである必要があります）
MESSAGE_SENDER_EMAIL = 'sateraito-service@sateraito.jp'

# 以下の値は固定
SATERAITO_MAIL_SERVER_URL = 'https://sendmail.sateraito.jp'
MD5_SUFFIX_KEY_MAIL_SERVER = 'n7ktsVazchS8NTzM0Gwuq8UCyLiuinKl'


# # SENDER_ADDON_PROJECT_ID = 'nextset-example'
# SENDER_ADDON_PROJECT_ID = sateraito_inc.SATERAITO_MAIL_SERVER_SENDER_ADDON_PROJECT_ID
# # MD5_SUFFIX_KEY_MAIL_SERVER = 'exampleKkdA9GQUgWdm1jviEUpVPg'
# MD5_SUFFIX_KEY_MAIL_SERVER = sateraito_inc.SATERAITO_MAIL_SERVER_MD5_SUFFIX_KEY
#
# # MESSAGE_SENDER_EMAIL = 'sateraito-service@sateraito.jp'
# # MESSAGE_SENDER_EMAIL = 'o365-workflow-mail@nextset.jp'
# MESSAGE_SENDER_EMAIL = sateraito_inc.SATERAITO_MAIL_SERVER_MESSAGE_SENDER_EMAIL
#
# # SATERAITO_MAIL_SERVER_URL = 'https://sendmail.sateraito.jp'
# SATERAITO_MAIL_SERVER_URL = sateraito_inc.SATERAITO_MAIL_SERVER_URL

NUM_MAX_ATTACH_FILES = 10


def sendMail(to, message_subject, message_body,
             cc='', reply_to='', is_html=False, bcc='',
             file_name=None, file_content=None,
             send_by_sendgrid=False,
             attach_files=None):
	"""
	  @param {string / list} to
	  @param {string} message_subject
	  @param {string} message_body
	  @param {string / list} cc
	  @param {string / list} reply_to
	  @param {boolean} is_html ... html形式のメールを送る場合Trueを指定
	  @param {string / list} bcc
	  @param {string} file_name ... ファイルを添付する場合、ファイル名（拡張子は必須） ---> 現在未使用、互換性のために残してある
	  @param {string} file_content ... ファイルを添付する場合、ファイルの内容  ---------> 現在未使用、互換性のために残してある
	  @param {boolean} send_by_sendgrid ... SendGridを使ってメールを送る場合Trueを指定
	  @param {dict / list} attach_files ... 送信する複数のファイル、指定した場合は「file_name」「file_content」は無視されます
	      例）[{'file_name':'attach_example.csv', 'file_content':'#doc_id..........'}]

	  @return {boolean} succeeded, {string} error_code

	  to, cc, bcc, reply_toに指定できるもの：
	    カンマ区切りの文字列での複数のメールアドレス指定可能
	    また 「"氏名" <address@example.com>」 形式でのアドレス指定も可能
	  例） akitoshiabe@gmail.com
	       akitoshiabe@gmail.com, abe@sateraito.co.jp
	       "阿部昭敏" <akitoshiabe@gmail.com>
	       "阿部昭敏" <akitoshiabe@gmail.com>, "阿部サテライト" <abe@sateraito.co.jp>

	    またlistで複数アドレスを渡すのも可
	"""
	if isinstance(to, list):
		to_str = ','.join(to)
	else:
		to_str = to
	if isinstance(cc, list):
		cc_str = ','.join(cc)
	else:
		cc_str = cc
	if isinstance(bcc, list):
		bcc_str = ','.join(bcc)
	else:
		bcc_str = bcc
	if isinstance(reply_to, list):
		reply_to_str = ','.join(reply_to)
	else:
		reply_to_str = reply_to
	return _sendMail(to_str, message_subject, message_body,
	                 cc=cc_str, reply_to=reply_to_str, is_html=is_html, bcc=bcc_str,
	                 file_name=file_name, file_content=file_content,
	                 send_by_sendgrid=send_by_sendgrid,
	                 attach_files=attach_files)


def _sendMail(to, message_subject, message_body,
              cc='', reply_to='', is_html=False, bcc='', file_name=None, file_content=None,
              send_by_sendgrid=False,
              attach_files=None):
	# check to
	if to is None or str(to).strip() == '':
		logging.error('to is None')
		return False, 'invalid_to'
	if not mail.IsEmailValid(to):
		logging.error('invalid to=' + str(to))
		return False, 'invalid_to'
	# check cc
	if cc is not None and str(cc).strip() != '':
		if not mail.IsEmailValid(cc):
			logging.error('invalid cc=' + str(cc))
			return False, 'invalid_cc'
	# check bcc
	if bcc is not None and str(bcc).strip() != '':
		if not mail.IsEmailValid(bcc):
			logging.error('invalid bcc=' + str(bcc))
			return False, 'invalid_bcc'
	# check reply_to
	if reply_to is not None and str(reply_to) != '':
		if not mail.IsEmailValid(reply_to):
			logging.error('invalid reply_to=' + str(reply_to))
			return False, 'invalid_reply_to'
	# calc check_key
	now = UcfUtil.getNow()  # 標準時
	check_key = UcfUtil.md5(now.strftime('%Y%m%d%H%M') + MD5_SUFFIX_KEY_MAIL_SERVER + SENDER_ADDON_PROJECT_ID)

	# check number of attach files
	if attach_files is not None and isinstance(attach_files, list) and len(attach_files) > NUM_MAX_ATTACH_FILES:
		return False, 'too_many_attach_files'

	# # エンコード処理 2023.02.13
	# if message_subject is not None and isinstance(message_subject, unicode):
	# 	message_subject = message_subject.encode('utf-8')
	# if message_body is not None and isinstance(message_body, unicode):
	# 	message_body = message_body.encode('utf-8')
	# if to is not None and isinstance(to, unicode):
	# 	to = to.encode('utf-8')
	# if cc is not None and isinstance(cc, unicode):
	# 	cc = cc.encode('utf-8')
	# if reply_to is not None and isinstance(reply_to, unicode):
	# 	reply_to = reply_to.encode('utf-8')
	# if bcc is not None and isinstance(bcc, unicode):
	# 	bcc = bcc.encode('utf-8')

	# create post data
	values = {
		'addon_project_id': SENDER_ADDON_PROJECT_ID,
		'sender_email': MESSAGE_SENDER_EMAIL,
		'to': to,
		'cc': cc,
		'reply_to': reply_to,
		'message_subject': message_subject,
		'message_body': message_body,
		'is_html': str(is_html),
		'send_by_sendgrid': str(send_by_sendgrid),
		'check_key': check_key,
		'bcc': bcc,
	}

	# go kick mail server api
	if attach_files is not None:
		# attach file case(using parameter attach_files)
		response = goPostWithMultipleAttach(values, attach_files, file_content)
		logging.info('attach file case response=' + str(response))
		try:
			response_dict = json.JSONDecoder().decode(response)
			if response_dict.get('status') != 'ok':
				return False, response_dict.get('error_code')
		except BaseException as e:
			logging.error('error: class name:' + e.__class__.__name__ + ' message=' + str(e))
			return False, 'unexpected_error'

		return True, ''

	elif file_name is not None and file_content is not None:
		# attach file case
		response = goPostWithAttach(values, file_name, file_content)
		logging.info('attach file case response=' + str(response))
		try:
			response_dict = json.JSONDecoder().decode(response)
			if response_dict.get('status') != 'ok':
				return False, response_dict.get('error_code')
		except BaseException as e:
			logging.error('error: class name:' + e.__class__.__name__ + ' message=' + str(e))
			return False, 'unexpected_error'

		return True, ''
	else:
		# no attach file case
		response = HttpPostAccess(values)
		logging.info('no attach file case response=' + str(response))
		try:
			response_dict = json.JSONDecoder().decode(response)
			if response_dict.get('status') != 'ok':
				return False, response_dict.get('error_code')
		except BaseException as e:
			logging.error('error: class name:' + e.__class__.__name__ + ' message=' + str(e))
			return False, 'unexpected_error'

		return True, ''


URLFETCH_TIMEOUT_SECOND = 30


def HttpPostAccess(values):
	headers = {}
	url = SATERAITO_MAIL_SERVER_URL + '/api/sendmail'
	# 値をURLエンコード
	# data = urllib.urlencode(values)  # gen2対応
	# req = urllib2.Request(url, data, headers)
	# response = urllib2.urlopen(req, timeout=URLFETCH_TIMEOUT_SECOND)
	# return response.read()
	# gen2対応
	body = None
	req = urllib.request.Request(url, urllib.parse.urlencode(values).encode(), headers)  # ２番目のdataパラメータを指定するとPOSTになる
	with urllib.request.urlopen(req) as res:
		body = res.read()
	return body


def goPostWithAttach(values, file_name, file_content):
	# post multipart/form-data
	files = [
		{
			'name': 'attach_file',
			'file_name': file_name,
			'file_content': file_content,
		}
	]
	content_type, body = encode_multipart_formdata(values, files)
	result = urlfetch.fetch(
		url=SATERAITO_MAIL_SERVER_URL + '/api/sendmail',
		payload=body,
		method=urlfetch.POST,
		headers={'Content-Type': content_type},
		deadline=URLFETCH_TIMEOUT_SECOND
	)
	if result.status_code == 200:
		logging.info('post file ' + file_name + '(multipart/form-data) is finished')
		return result.content


def goPostWithMultipleAttach(values, attach_files, file_content):
	# post multipart/form-data
	files = []
	cnt = 1
	for attach_file in attach_files:
		files.append({
			'name': 'attach_file_' + str(cnt) if cnt != 1 else 'attach_file',
			'file_name': attach_file.get('file_name'),
			'file_content': attach_file.get('file_content'),
		})
		cnt += 1
		if cnt > NUM_MAX_ATTACH_FILES:
			break
	content_type, body = encode_multipart_formdata(values, files)
	result = urlfetch.fetch(
		url=SATERAITO_MAIL_SERVER_URL + '/api/sendmail',
		payload=body,
		method=urlfetch.POST,
		headers={'Content-Type': content_type},
		deadline=URLFETCH_TIMEOUT_SECOND
	)
	if result.status_code == 200:
		logging.info('post multiple files (multipart/form-data) finished')
		return result.content


def encode_multipart_formdata(values, files):
	"""

	:param values: dict
	:param files: list of dict
	:return:
	"""
	boundary = str('sateraito___boundary-' + randomString() + '___' + dateString())
	crlf = str('\r\n').encode()
	line = []
	for key, value in values.items():
		line.append(str('--' + boundary).encode())
		line.append(str('Content-Disposition: form-data; name="%s"' % key).encode())
		line.append(str('').encode())
		line.append(str(value).encode())
	for file in files:
		line.append(str('--' + boundary).encode())
		line.append(
			str('Content-Disposition: form-data; name="%s"; filename="%s"' % (file['name'], file['file_name'])).encode())
		# line.append(str('Content-Type: %s' % file['mime_type']))
		line.append(str('Content-Transfer-Encoding: binary').encode())
		line.append(str('').encode())
		if type(file['file_content']) is str:
			line.append(file['file_content'].encode())
		elif type(file['file_content']) is bytes:
			line.append(file['file_content'])
	line.append(str('--%s--' % boundary).encode())
	line.append(str('').encode())
	body = crlf.join(line)
	content_type = str('multipart/form-data; boundary=%s' % boundary)
	return content_type, body


def dateString():
	# create date string
	dt_now = datetime.datetime.now()
	return dt_now.strftime('%Y%m%d%H%M%S')


def randomString(length=16):
	# create 16-length random string
	s = 'abcdefghijkmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
	random_string = ''
	for j in range(length):
		random_string += random.choice(s)
	return random_string

