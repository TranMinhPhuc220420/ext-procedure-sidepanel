#!/usr/bin/python
# coding: utf-8
# GAEGEN2�Ή�:����coding�͖{���͔񐄏��炵��. �t�@�C���G���R�[�h��UTF-8�iShift_JIS��NG�j�ł���K�v����B

import os
# GAEGEN2�Ή�:Logger���J�X�^�}�C�Y
#import logging
import sateraito_logger as logging
# GAEGEN2�Ή�:webapp2���C�u�����p�~��Flask�ڍs
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

		# ���������iCookie�̒l���l���j
		hl_from_cookie = self.getCookie('hl')
		logging.info('hl_from_cookie=' + str(hl_from_cookie))
		if hl_from_cookie is not None and hl_from_cookie in sateraito_func.ACTIVE_LANGUAGES:
			self._language = hl_from_cookie
		# ����ꗗ
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


