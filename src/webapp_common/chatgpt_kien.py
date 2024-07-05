#!/usr/bin/python
# coding: utf-8

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
#from google.appengine.api.apiproxy_stub_map import UserRPC
import sateraito_inc
from ucf.utils.ucfutil import *
from nltk.tokenize import RegexpTokenizer

from google.appengine.ext import db
from google.appengine.ext import ndb

from webapp_common.base_helper import *

CHAT_GPT_QUEUE_NAME = 'default'
CHAT_GPT_QUEUE_TARGET = 'commonprocess'

jp_sent_tokenizer = RegexpTokenizer(u'[^！？。.?]*[！？。.?]')

ChatGPTSummarizeInit = "INIT"
ChatGPTSummarizing = "SUMMARIZING"
ChatGPTSummarizeEnd = "END"
ChatGPTSummarizeError = "ERROR"

class ChatGPTSummarizeRequest(ndb.Model):
	content = ndb.TextProperty()
	checksum = ndb.StringProperty()
	lang = ndb.StringProperty()
	sentences = ndb.StringProperty(repeated=True)
	status = ndb.StringProperty(default=ChatGPTSummarizeInit)
	page_id = ndb.StringProperty()
	created_date = ndb.DateTimeProperty(auto_now_add=True)
	updated_date = ndb.DateTimeProperty(auto_now=True)

class ChatGPTSummarizeResult(ndb.Model):
	content = ndb.TextProperty(default="")
	page_id = ndb.StringProperty()
	completion_tokens = ndb.IntegerProperty(default=0)
	index = ndb.IntegerProperty(default=0)
	created_date = ndb.DateTimeProperty(auto_now_add=True)
	updated_date = ndb.DateTimeProperty(auto_now=True)

class Chat(WebappHelper):

	def post(self, tenant):
		if not self.setNamespace(tenant, ''):
			return
		# row = sateraito_db.GoogleAppsDomainEntry.getInstanceByDomainMemcache(tenant)
		# if row.enable_chat_gpt is not True:
		# 	return
		# chat_gpt_api = row.chat_gpt_api
		# if chat_gpt_api is None or chat_gpt_api == '':
		# 	chat_gpt_api = sateraito_inc.CHAT_GPT_API_KEY
		chat_gpt_api = sateraito_inc.CHAT_GPT_API_KEY
		messages =  self.request.get('messages',None)
		sessionId = self.request.get('sessionId',None)
		messages = json.loads(messages)
		post_data = {"model": "gpt-3.5-turbo","messages":messages}
		post_data = json.dumps(post_data).encode()
		headers ={'Content-Type':'application/json','Authorization':'Bearer '+chat_gpt_api.strip()}
		
		req = urllib2.Request('https://api.openai.com/v1/chat/completions', post_data, headers)
		try: 
			res = urllib2.urlopen(req,timeout=120)
			result = json.loads(res.read())
			
			self.send_success_response({'sessionId':sessionId,'chatGPT':result})

			return
		except urllib2.HTTPError as e:
			logging.error('HTTPError = ' + str(e.code))
		except urllib2.URLError as e:
			logging.error('URLError = ' + str(e.reason))
		
		except Exception:
			import traceback
			logging.error('generic exception: ' + traceback.format_exc())
		self.send_error_response()


class Summarize(WebappHelper):

	def post(self, tenant):
		if not self.setNamespace(tenant, ''):
			return
		content = self.request.get('content',None)
		hl = self.request.get('hl',None)
		sessionId = self.request.get('sessionId',None)
		checksum = hashlib.md5(content+hl).hexdigest()
		query = ChatGPTSummarizeRequest.query()
		query = query.filter(ChatGPTSummarizeRequest.checksum == checksum)
		row = query.get()
		if row is None:
			row = ChatGPTSummarizeRequest()
			row.content = content
			row.checksum = checksum
			row.put()
			start_summarize(tenant,row.key.id())
		self.send_success_response({'request_id':row.key.id(),'sessionId':sessionId})

class GetSummarize(WebappHelper):

	def get(self, tenant):
		if not self.setNamespace(tenant, ''):
			return
		request_id = int(self.getRequest('request_id'))
		sessionId = self.request.get('sessionId',None)
		row = ChatGPTSummarizeRequest.get_by_id(request_id)
		if row is None:
			self.send_error_response()
			return
		status =row.status
		content =''
		if status == ChatGPTSummarizeEnd:
			result = ChatGPTSummarizeResult.get_by_id(request_id)
			if result is not None:
				content = result.content
		self.send_success_response({'status':status,'content':content,'sessionId':sessionId})

def start_summarize(tenant,request_id):
	queue = taskqueue.Queue(CHAT_GPT_QUEUE_NAME)
	params = {
		'tenant':tenant,
		'request_id':request_id,
	}
	
	task = taskqueue.Task(
		url='/'+tenant+'/chatgpt/queue_summarize',
		params=params,
		target=CHAT_GPT_QUEUE_TARGET,
		countdown=2
	)
	# queue.add(task)
	sateraito_func.addTaskQueue(queue, task)

class Summarizing(APIResponse):

	def chatgpt_summarize(self,tenant, lang,conent):
		# row = sateraito_db.GoogleAppsDomainEntry.getInstanceByDomainMemcache(tenant)
		# if row.enable_chat_gpt is not True:
		# 	return
		# chat_gpt_api = row.chat_gpt_api
		# if chat_gpt_api is None or chat_gpt_api == '':
		# 	chat_gpt_api = sateraito_inc.CHAT_GPT_API_KEY
		chat_gpt_api = sateraito_inc.CHAT_GPT_API_KEY
		lang  ='japanese'
		# lang = 'vietnamese'
		if lang == 'en':
			lang = 'english'
		messages = [{"role": "user", "content": 'Summarize this in '+lang+' with maximum 500 words: "'+conent+'"'}]
		post_data = {"model": "gpt-3.5-turbo","messages":messages}
		post_data = json.dumps(post_data).encode()
		headers ={'Content-Type':'application/json','Authorization':'Bearer '+chat_gpt_api.strip()}
		req = urllib2.Request('https://api.openai.com/v1/chat/completions', post_data, headers)
		res = urllib2.urlopen(req,timeout=5*60)
		result = json.loads(res.read())
		completion_tokens  = result['usage']['completion_tokens']
		content  = result['choices'][0]['message']['content']
		return content,completion_tokens
	
	def post(self, tenant):
		retry_cnt = self.request.headers.environ['HTTP_X_APPENGINE_TASKRETRYCOUNT']
		if not self.setNamespace(tenant, ''):
			return
		request_id = int(self.getRequest('request_id'))
		logging.debug(request_id)
		request_sync = ChatGPTSummarizeRequest.get_by_id(request_id)
		if request_sync is None:
			logging.error('Summarizing error')
			
			return
		if retry_cnt is not None:
			if (int(retry_cnt) > 5):
				request_sync.status = ChatGPTSummarizeError
				request_sync.put()
				return
	
		if request_sync.status == ChatGPTSummarizeInit:
			sentences = jp_sent_tokenizer.tokenize(request_sync.content)
			request_sync.sentences = sentences
			request_sync.content = ''
			request_sync.status = ChatGPTSummarizing
			request_sync.put()
			# start queue 
			start_summarize(tenant,request_id)
			return
		sentences = request_sync.sentences
		
		if request_sync.status == ChatGPTSummarizing:
			result = ChatGPTSummarizeResult.get_by_id(request_id)
			index = 0
			completion_tokens = 0
			summarize_result = ''
			if result is not None:
				index = result.index
				summarize_result = result.content
				completion_tokens = result.completion_tokens
			else:
				result = ChatGPTSummarizeResult(id=request_id)	
			max = len(sentences)
			
			while index < max:
				
				
				logging.debug('completion_tokens:'+str(completion_tokens))
				try:
				
					if len(summarize_result) == 0 or completion_tokens == 0:
						completion_tokens = completion_tokens +len(sentences[index])
					else:
						completion_tokens = completion_tokens +len(sentences[index])/(float(len(summarize_result)/completion_tokens))
				except Exception:
					completion_tokens = completion_tokens +len(sentences[index])
				summarize_result = summarize_result+ sentences[index]
				logging.debug('len sentences :'+str(len(sentences[index])))
				logging.debug('new completion_tokens:'+str(completion_tokens))
				index += 1
				if completion_tokens > 1000:
					break
			content,completion_tokens =	self.chatgpt_summarize(tenant,request_sync.lang,summarize_result)
			result.content = content
			result.completion_tokens = completion_tokens
			result.index = index
			result.put()
			if index >= max:
				request_sync.status = ChatGPTSummarizeEnd
				request_sync.put()
				return
			start_summarize(tenant,request_id)




# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行. URLはwerkzeugの正規表現書式を使用可能. 従来の末尾の「$」は使用不可. as_view('XXX') はプロダクトを通して一意である必要あり
# app = ndb.toplevel(webapp2.WSGIApplication([
# 	('/([^/]*)/chatgpt/chat$',Chat),
# 	('/([^/]*)/chatgpt/summarize$',Summarize),
# 	('/([^/]*)/chatgpt/get_summarize$',GetSummarize),
# 	('/([^/]*)/chatgpt/queue_summarize$',Summarizing),
# ], debug=sateraito_inc.debug_mode, config=sateraito_page.config))

def add_url_rules(app):
	app.add_url_rule('/v2_api/<tenant>/chatgpt/chat',  view_func=Chat.as_view(__name__ + '.Chat'))
	app.add_url_rule('/v2_api/<tenant>/chatgpt/summarize',  view_func=Summarize.as_view(__name__ + '.Summarize'))
	app.add_url_rule('/v2_api/<tenant>/chatgpt/get_summarize',  view_func=GetSummarize.as_view(__name__ + '.GetSummarize'))
	app.add_url_rule('/v2_api/<tenant>/chatgpt/queue_summarize',  view_func=GetSummarize.as_view(__name__ + '.Summarizing'))