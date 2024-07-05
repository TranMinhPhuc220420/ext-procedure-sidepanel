# coding: utf-8

# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行
#import webapp2
from flask import Flask, Response, render_template, request, make_response, session, redirect
from ucf.utils.helpers import *
from ucf.utils.models import *
from ucf.utils import loginfunc
# GAEGEN2対応:blobstore_handlers廃止
#from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import blobstore
from google.appengine.api import app_identity
from ucf.pages.file import *
from ucf.pages.user_info import *
import sateraito_inc
import sateraito_func
from datetime import datetime, timedelta
import io
import cgi

MAX_SIZE_AVATAR_UPLOAD = 5368709120

#############
# CSRF対策トークンを発行…JavaScriptでPOSTする機能のうち、ファイルアップロード系の部分で使用
class CreateCsrfTokenPage(TenantAjaxHelper):
	def processOfRequest(self):

		CSRF_TOKEN_KEY = 'GENERAL'

		try:
			# CSRF対策:トークン発行
			token = self.createCSRFToken(CSRF_TOKEN_KEY)
			# オペレーションログのためにトークンをキーにIPアドレスを保存しておく（若干苦肉の策）2015.07.31
			self.setSession(UcfConfig.SESSIONKEY_CLIENTIP + '_' + token, self.getClientIPAddress())

			ret_value = {
				'token':token
			}

			self._code = 0
			self.responseAjaxResult(ret_value)

		except BaseException as e:
			self.outputErrorLog(e)
			self._code = 999
			self.responseAjaxResult()


class CreateUploadURLPage(TenantAjaxHelper):
	def processOfRequest(self):
		try:
			# set response header
			self.response.headers['Content-Type'] = 'application/json'

			upload_url = self.getRequest('upload_url')
			bucket_name = self.getRequest('bucket_name')

			gcs_bucket_name = app_identity.get_default_gcs_bucket_name()
			gcs_filename_sub = gcs_bucket_name + '/' + bucket_name

			# create upload url
			upload_url_res = blobstore.create_upload_url(upload_url, gs_bucket_name=gcs_filename_sub)

			ret_value = {
				'url':upload_url_res
			}

			self._code = 0
			self.responseAjaxResult(ret_value)

		except BaseException as e:
			self.outputErrorLog(e)
			self._code = 999
			self.responseAjaxResult()


# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行. URLはwerkzeugの正規表現書式を使用可能. 従来の末尾の「$」は使用不可. as_view('XXX') はプロダクトを通して一意である必要あり
#app = webapp2.WSGIApplication([('/a/([^/]*)/file/blob', Page)], debug=sateraito_inc.debug_mode, config=sateraito_func.wsgi_config)
def add_url_rules(app):
	app.add_url_rule('/api/create-csrf-token',  view_func=CreateCsrfTokenPage.as_view(__name__ + '.CreateCsrfTokenPage'))
	app.add_url_rule('/api/create-upload-url',  view_func=CreateUploadURLPage.as_view(__name__ + '.CreateUploadURLPage'))
