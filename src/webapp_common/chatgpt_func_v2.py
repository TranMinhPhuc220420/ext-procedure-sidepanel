#!/usr/bin/python
# coding: utf-8

__author__ = 'T.ASAO <asao@sateraito.co.jp>'

import os
import re
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
# GAEGEN2対応:Flaskやrequestsライブラリで実装
from flask import Flask, Response, render_template, request, make_response, session, redirect
import requests
import sseclient
import datetime
import random
import json
import time
from google.appengine.api import urlfetch
# from gdata.service import RequestError
# from google.appengine.api.urlfetch import DownloadError
#from google.appengine.api.apiproxy_stub_map import UserRPC
import sateraito_inc
from ucf.utils.ucfutil import *

def callChatGPT(helper, api_key, model, word, message_historys, with_stream):

	# if sateraito_inc.developer_mode:
	# 	# return is_success, "error_message", "output_text", [message_history]
	# 	output_text_test = """
	# 	Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.
	# 	Contrary to popular belief, Lorem Ipsum is not simply random text. It has roots in a piece of classical Latin literature from 45 BC, making it over 2000 years old. Richard McClintock, a Latin professor at Hampden-Sydney College in Virginia, looked up one of the more obscure Latin words, consectetur, from a Lorem Ipsum passage, and going through the cites of the word in classical literature, discovered the undoubtable source. Lorem Ipsum comes from sections 1.10.32 and 1.10.33 of "de Finibus Bonorum et Malorum" (The Extremes of Good and Evil) by Cicero, written in 45 BC. This book is a treatise on the theory of ethics, very popular during the Renaissance. The first line of Lorem Ipsum, "Lorem ipsum dolor sit amet..", comes from a line in section 1.10.32.
	#
	# 	The standard chunk of Lorem Ipsum used since the 1500s is reproduced below for those interested. Sections 1.10.32 and 1.10.33 from "de Finibus Bonorum et Malorum" by Cicero are also reproduced in their exact original form, accompanied by English versions from the 1914 translation by H. Rackham.
	# 	"""
	# 	return True, '', output_text_test, []

	if model == 'gpt-3.5-turbo':

		# メッセージをセット
		messages = []

		# セッションからやり取り履歴を取得してセット
		if message_historys is not None:
			messages = message_historys
		# それに今回の最新のメッセージを追加
		messages.append({
					"role": "user",
					"content": word
				})
		# APIのサイズオーバーに引っかからないように古いメッセージを削除（なんとなく3000文字くらいにしてみる）
		msg_length = 0
		over_cnt = 0
		i = 0
		for message in reversed(messages):
			#logging.info(i)
			#logging.info(message)
			msg_length += len(message.get('content', ''))
			logging.info('i=%s msg_length=%s' % (str(i), str(msg_length)))
			if msg_length >= 4096:
				logging.info('content=%s' % (message.get('content', '')))
				over_cnt = len(messages) - i
				break
			i += 1
		#logging.info('over_cnt=%s' % (over_cnt))
		if over_cnt > 0:
			for i in range(over_cnt):
				#logging.info('pop...')
				messages.pop(0)

		if len(messages) == 0:
			return False, helper.getMsg('TOO_LARGE_MESSAGE'), None, None

		payload = {
			"model": model,
			"messages": messages,
			"temperature": 1,
			"stream": with_stream
		}
		#payload["max_tokens"] = model_max_tokens

		headers = {
			"Content-Type": "application/json",
			"Authorization": "Bearer " + api_key
		}

		if with_stream:
			headers["Accept"] = "text/event-stream"

		url = 'https://api.openai.com/v1/chat/completions'
		logging.info('url=%s' % (url))
		logging.info(payload)

		# 非同期処理（にする必要は現状はないのだが、、チャットボットマネージャーをベースにしているのと将来を見据えて）

		# プリミティブ型だと本来の戻り値に反映できないのでdictに変更
		#is_success = False
		#error_msg = ''
		#response_message_text = ''
		return_obj = {
			'is_success':False,
			'error_msg':'',
			'response_message_text':'',
		}

		def handle_result(rpc):
			logging.info('handle_result...')
			result = rpc.get_result()
			# GAEGEN2対応
			#ai_response = json.JSONDecoder().decode(result.content)
			ai_response = json.JSONDecoder().decode(result.content.decode())
			if ai_response.get('object', '') != 'chat.completion':
				logging.error(result.content)
				raise Exception(helper.getMsg('INVALID_CHATBOT_RESPONSE'))
			choices = ai_response.get('choices', [])
			if len(choices) == 0:
				logging.error(result.content)
				raise Exception(helper.getMsg('INVALID_CHATBOT_RESPONSE'))
			logging.info(result.content)
			# 結果をセット（とりあえずシンプルに応答文言だけ）
			response_message = choices[0].get('message', {})
			response_message_text = response_message.get('content', '')
		
			# 会話履歴のためにセッションにやり取りをセット（最後に最新の応答をセットして）
			messages.append(response_message)

			return_obj['is_success'] = True
			return_obj['error_msg'] = ''
			return_obj['response_message_text'] = response_message_text
			return

		# Use a helper function to define the scope of the callback.
		def create_callback(rpc):
			return lambda: handle_result(rpc)
		
		# rpc = urlfetch.create_rpc(deadline=300)
		# rpc.callback = create_callback(rpc)
		# urlfetch.make_fetch_call(rpc, url=url, method=urlfetch.POST, payload=json.JSONEncoder().encode(payload), headers=headers, follow_redirects=False)
		# rpc.wait()
		# urlfetch.Fetch(
		# 	url,
		# 	payload=None,
		# 	method=GET,
		# 	headers={},
		# 	allow_truncated=False,
		# 	follow_redirects=True,
		# 	deadline=None,
		# 	validate_certificate=None
		# )
		# try:
		# result = urlfetch.fetch(url=url, method=urlfetch.POST, payload=json.JSONEncoder().encode(payload), headers=headers, follow_redirects=False)
		# logging.info(result)
		# logging.info(result.content)
		# if result.status_code == 200:
		# 	contact_groups_xml_string = result.content
		# 	if sateraito_inc.debug_mode:
		# 		logging.debug(contact_groups_xml_string)
		# else:
		# 	logging.warn('Token invalid - Invalid token')
		# 	return
		# except Exception as e:
		# 	logging.info('failed add update user entry taskqueue. tenant=' + tenant + ' user=' + operator_entry.operator_id)
		# 	logging.exception(e)
		# except DownloadError, instance:
		# 	logging.info('instance=' + str(instance))
		# 	logging.warn('Gdata request timeout')
		# 	return
		# except RequestError, instance:
		# 	logging.info('instance=' + str(instance))
		# 	return
		

		rpc = urlfetch.create_rpc(deadline=300)
		urlfetch.make_fetch_call(rpc, url=url, method=urlfetch.POST, payload=json.JSONEncoder().encode(payload), headers=headers, follow_redirects=False)
		# ... do other things ...
		try:
			result = rpc.get_result()
			# GAEGEN2対応
			# ai_response = json.JSONDecoder().decode(result.content)
			ai_response = json.JSONDecoder().decode(result.content.decode())
			if ai_response.get('object', '') != 'chat.completion':
				logging.error(result.content)
				raise Exception(helper.getMsg('INVALID_CHATBOT_RESPONSE'))
			choices = ai_response.get('choices', [])
			if len(choices) == 0:
				logging.error(result.content)
				raise Exception(helper.getMsg('INVALID_CHATBOT_RESPONSE'))
			logging.info(result.content)
			# 結果をセット（とりあえずシンプルに応答文言だけ）
			response_message = choices[0].get('message', {})
			response_message_text = response_message.get('content', '')
			
			# 会話履歴のためにセッションにやり取りをセット（最後に最新の応答をセットして）
			messages.append(response_message)
			
			return_obj['is_success'] = True
			return_obj['error_msg'] = ''
			return_obj['response_message_text'] = response_message_text
			# if result.status_code == 200:
			# 	return_obj['response_message_text'] = result.content
			# else:
			# 	# self.response.status_int = result.status_code
			# 	# self.response.write('URL returned status code {}'.format(result.status_code))
			# 	return_obj['is_success'] = False
			# 	return_obj['error_msg'] = 'URL returned status code {}'.format(result.status_code)
		except urlfetch.DownloadError:
			# self.response.status_int = 500
			# self.response.write('Error fetching URL')
			return_obj['is_success'] = False
			return_obj['error_msg'] =  'Error fetching URL'
			

		is_success = return_obj.get('is_success', False)
		error_msg = return_obj.get('error_msg', '')
		response_message_text = return_obj.get('response_message_text', '')

		return is_success, '', response_message_text, messages
