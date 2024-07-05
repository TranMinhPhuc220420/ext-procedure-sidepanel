#!/usr/bin/python
# coding: utf-8
# GAEGEN2対応:↑のcodingは本当は非推奨らしい. ファイルエンコードはUTF-8（Shift_JISはNG）である必要あり。

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
import oem_func

class Page(FrontHelper):

	def processOfRequest(self):
		self._approot_path = os.path.dirname(__file__)
		ucfp = UcfFrontParameter(self)

		# 言語を決定（Cookieの値を考慮）
		hl_from_cookie = self.getCookie('hl')
		logging.info('hl_from_cookie=' + str(hl_from_cookie))
		if hl_from_cookie is not None and hl_from_cookie in sateraito_func.ACTIVE_LANGUAGES:
			self._language = hl_from_cookie
		# 言語一覧
		language_list = []
		for language in sateraito_func.ACTIVE_LANGUAGES:
			language_list.append([language, self.getMsg(sateraito_func.LANGUAGES_MSGID.get(language, ''))])

		template_vals = {
			'footer_message':self.getMsg('EXPLAIN_LOGINPAGE_DEFAULT', ()),
			'language_list':json.JSONEncoder().encode(language_list)
		}
		self.appendBasicInfoToTemplateVals(template_vals)
		self.render('notfound.html', self._design_type, template_vals)

def add_url_rules(app):
	app.add_url_rule('/notfound',  view_func=Page.as_view(__name__ + '.IndexPage'))


