#!/usr/bin/python
# coding: utf-8

import os
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行
#import webapp2
from flask import Flask, Response, render_template, request, make_response, session, redirect
import json
from google.appengine.api import users
from ucf.utils.helpers import *
import sateraito_inc

class Page(FrontHelper):
	def processOfRequest(self):
		self._approot_path = os.path.dirname(__file__)

		# 言語を決定（Cookieの値を考慮）
		hl_from_cookie = self.getCookie('hl')
		logging.info('hl_from_cookie=' + str(hl_from_cookie))
		if hl_from_cookie is not None and hl_from_cookie in sateraito_func.ACTIVE_LANGUAGES:
			self._language = hl_from_cookie
		# 言語一覧
		language_list = []
		for language in sateraito_func.ACTIVE_LANGUAGES:
			language_list.append([language, self.getMsg(sateraito_func.LANGUAGES_MSGID.get(language, ''))])


		error_info = self.getSession(UcfConfig.SESSIONKEY_ERROR_INFO)

		template_vals = {
			'error_info':error_info,
			'footer_message':self.getMsg('EXPLAIN_LOGINPAGE_DEFAULT', ()),
			'language_list':json.JSONEncoder().encode(language_list)
		}
		self.appendBasicInfoToTemplateVals(template_vals)
		self.render('error.html', self._design_type, template_vals)

# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行. URLはwerkzeugの正規表現書式を使用可能. 従来の末尾の「$」は使用不可. as_view('XXX') はプロダクトを通して一意である必要あり
#app = webapp2.WSGIApplication([
#                               (r'/error', Page),
#                              ], debug=sateraito_inc.debug_mode, config=sateraito_func.wsgi_config)
def add_url_rules(app):
	app.add_url_rule('/error',  view_func=Page.as_view(__name__ + '.ErrorPage'))
