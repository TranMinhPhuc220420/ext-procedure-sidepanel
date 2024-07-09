#!/usr/bin/python
# coding: utf-8

# GAEGEN2対応:Loggerをカスタマイズ
#import logging
# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行
#import webapp2
from flask import Flask, Response, render_template, request, make_response, session, redirect
import json
import bcrypt

#from google.appengine.api import users
from ucf.utils.models import *
from ucf.utils.helpers import *
from webapp_common.base_helper import *
from ucf.utils.validates import BaseValidator
from ucf.utils import loginfunc

import sateraito_logger as logging

import sateraito_inc
import sateraito_func

############################################################
## LoginPage
############################################################
class LoginPage(WebappHelper):

	def processOfRequest(self):
		try:
			self._approot_path = os.path.dirname(__file__)

			# check login
			is_ok, body_for_not_ok = self.oidAutoLogin()
			logging.info("check login=" + str(is_ok))

			if not is_ok:
				return body_for_not_ok

			return self.render_template('after_login.html', self._design_type, vals={
				'viewer_email': self.viewer_email,
				'viewer_id': self.viewer_id,
			})

		except BaseException as e:
			self.outputErrorLog(e)
			self.redirectError(UcfMessage.getMessage(self.getMsg('MSG_SYSTEM_ERROR'), ()))
			return


############################################################
## ログアウト処理
############################################################
class LogoutPage(WebappHelper):

	def processOfRequest(self):
		try:
			self._approot_path = os.path.dirname(__file__)
			# if self.isValidTenant() == False:
			# 	return

			# 権限チェック 2011/04/08 不要な為、削除
			#if not self.checkAccessAuthority(_MENU_ID): return

			# RURLを取得
			strRURL = UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_RURL))

			# RURLが空のとき、リファラから取得
			if strRURL == '':
				strRURL = UcfUtil.nvl(UcfUtil.getHashStr(os.environ, 'HTTP_REFERER'))

			loginfunc.logout(self)

			# clear session value
			self.setSession('viewer_email', '')
			self.setSession('loggedin_timestamp', None)  # G Suiteのマルチログイン時にiframe内でOIDC認証ができなくなったので強制で少しだけ高速化オプションする対応＆SameSite対応 2019.10.28
			self.setSession('opensocial_viewer_id', '')
			self.setSession('is_oidc_loggedin', False)
			self.setSession('is_oidc_need_show_signin_link', False)
			# clear openid connect session
			self.removeAppsCookie()

			return self.render_template('after_logout.html', self._design_type, vals={
				'viewer_email': self.viewer_email,
				'viewer_id': self.viewer_id,
			})

		except BaseException as e:
			self.outputErrorLog(e)
			self.redirectError(UcfMessage.getMessage(self.getMsg('MSG_SYSTEM_ERROR'), ()))
			return


# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行. URLはwerkzeugの正規表現書式を使用可能. 従来の末尾の「$」は使用不可. as_view('XXX') はプロダクトを通して一意である必要あり
def add_url_rules(app):
	app.add_url_rule('/a/login',  view_func=LoginPage.as_view(__name__ + '.LoginPage'))

	app.add_url_rule('/a/logout',  view_func=LogoutPage.as_view(__name__ + '.LogoutPage'))
