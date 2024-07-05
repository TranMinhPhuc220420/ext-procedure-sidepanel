#!/usr/bin/python
# coding: utf-8

import os
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行
#import webapp2
from flask import Flask, Response, render_template, request, make_response, session, redirect
from google.appengine.api import users
from ucf.utils.helpers import *
import sateraito_inc
import sateraito_func

############################################################
## エラーページ
############################################################
class Page(TenantAppHelper):

	def processOfRequest(self, tenant):
		try:
			self._approot_path = os.path.dirname(__file__)
			#if self.isValidTenant() == False:
			#	return

			# 権限チェック 2011/04/08 不要な為、削除
			#if not self.checkAccessAuthority(_MENU_ID): return

			error_info = self.getSession(UcfConfig.SESSIONKEY_ERROR_INFO)
			ucfp = UcfTenantParameter(self)
			template_vals = {
				'ucfp' : ucfp,
				'error_info' : error_info,
				'footer_message':self.getMsg('EXPLAIN_LOGINPAGE_DEFAULT', ()),
				'is_hide_backstretch':self._career_type == UcfConfig.VALUE_CAREER_TYPE_TABLET,		# アクセス申請用ログイン画面でタブレットの場合はそもそも出さない
			}
			self.appendBasicInfoToTemplateVals(template_vals)

			# 強制デザイン変更対応 2017.02.20
			if self.request.get('dtp') != '':
				self._design_type = self.request.get('dtp')
			self.render('error.html', self._design_type, template_vals)
		except BaseException as e:
			self.outputErrorLog(e)
			return

# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行. URLはwerkzeugの正規表現書式を使用可能. 従来の末尾の「$」は使用不可. as_view('XXX') はプロダクトを通して一意である必要あり
#app = webapp2.WSGIApplication([('/a/([^/]*)/error', Page)], debug=sateraito_inc.debug_mode, config=sateraito_func.wsgi_config)
def add_url_rules(app):
	app.add_url_rule('/a/<tenant>/error',  view_func=Page.as_view(__name__ + '.Page'))
