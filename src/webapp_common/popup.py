#!/usr/bin/python
# coding: utf-8

from flask import Flask, Response, render_template, request, make_response, session, redirect, after_this_request
from flask.views import View, MethodView
import requests
import json
import datetime
import random

import sateraito_logger as logging
import sateraito_inc
import sateraito_func
import sateraito_db
from ucf.utils.ucfutil import UcfUtil

from webapp_common.base_helper import *

# from oauth2client.client import OAuth2WebServerFlow
from oauthlib.oauth2 import WebApplicationClient


class BeforePopup(WebappHelper):

	def getRequestAuthLogin(self, tenant, state):
		dictParam = dict(
			scope=sateraito_inc.OAUTH2_SCOPES,  # sateraito_inc.OAUTH2_SCOPES_OIDC,  # G Suite 版申込ページ対応 2017.06.05
			redirect_uri=sateraito_inc.my_site_url + '/oidccallback',
			state=state,
			openid_realm=sateraito_inc.my_site_url,
			access_type='online',
			hd=tenant
		)
		client = WebApplicationClient(sateraito_inc.WEBAPP_CLIENT_ID)
		auth_uri = client.prepare_request_uri(
			'https://accounts.google.com/o/oauth2/auth',
			**dictParam
		)
		return auth_uri

	def _processOAuth2(self, tenant, token):
		# Check OpenID Connect login user
		is_oidc_loggedin = self.getSession('is_oidc_loggedin')
		if is_oidc_loggedin is None or not is_oidc_loggedin:
			# if user logged in, force logout
			logging.info('user id found, clearing cookie...')
			self.removeAppsCookie()
		# go login by openid connect
		state = 'state-' + sateraito_func.dateString() + sateraito_func.randomString()
		logging.info('state=' + state)
		self.setSession('state', state)
		dest_url = sateraito_inc.my_site_url + '/' + tenant + '/openid/' + token + '/popup.html'
		self.setSession('url_to_go_after_oidc_login', dest_url)
		# create web server flow and redirect to auth url
		# flow = OAuth2WebServerFlow(
		# 	client_id=sateraito_inc.WEBAPP_CLIENT_ID,
		# 	client_secret=sateraito_inc.WEBAPP_CLIENT_SECRET,
		# 	scope=['openid', 'email'],
		# 	#								scope=['https://www.googleapis.com/auth/plus.me', 'https://www.googleapis.com/auth/plus.profile.emails.read'],
		# 	redirect_uri=sateraito_inc.my_site_url + '/oidccallback',
		# 	state=state,
		# 	openid_realm=sateraito_inc.my_site_url,
		# 	access_type='online',
		# )
		# auth_uri = flow.step1_get_authorize_url()
		auth_uri = self.getRequestAuthLogin(tenant, state)
		logging.info('auth_uri=' + str(auth_uri))

		return redirect(auth_uri)

	def get(self, tenant, token):
		try:
			return self._processOAuth2(tenant, token)
		except Exception as e:
			logging.exception(e)
			return Response('System Error.', status=500)


# class Popup(Handler_Tenant_Request):
# 	def _memcache_key(self, key, tenant):
# 		return 'key=' + key + '&tenant=' + tenant

# 	def doAction(self, tenant, token):
# 		try:
# 			# 認証チェック
# 			loginCheck = self._OIDCAutoLogin(tenant, with_none_prompt=False)
# 			logging.debug(loginCheck)
# 			if not loginCheck.get('status'):
# 				# not logged in: login and go to v2 MainPage
# 				if loginCheck.get('response'):
# 					return loginCheck.get('response')
# 				return self.responseError403()

# 			# Check GoogleApps Domain
# 			user_email = self.viewer_email
# 			user_id = self.viewer_user_id
# 			tenant_from_user_email = (user_email.split('@'))[1]
# 			target_tenant = tenant
# 			#		if tenant != tenant_from_user_email:
# 			#			logging.exception('google apps domain does not match: ' + tenant + ' and ' + tenant_from_user_email)
# 			#			return
# 			if not sateraito_func.isOauth2Domain(tenant):  # ※Oauth1の場合は変更なし（動き変わると面倒なので）
# 				if tenant != tenant_from_user_email:
# 					logging.exception(
# 						'google apps domain does not match: ' + tenant + ' and ' + tenant_from_user_email)
# 					return
# 			else:  # ※Oauth2の場合は必ずtenant=target_tenantがセットされてくるのでここで置き換え（サブドメイン用の「認証する」廃止に伴い）
# 				target_tenant = tenant_from_user_email

# 			# Get opensocial_viewer_id from memcached db
# 			opensocial_info = sateraito_func.OpenSocialInfo()
# 			is_load = opensocial_info.loadInfo(token)

# 			if is_load and opensocial_info.viewer_id is not None:
# 				# これにより管理者かどうかの取得と本Apps契約内のユーザーかどうかの判定を兼ねる
# 				is_admin = False
# 				try:
# 					is_admin = sateraito_func.checkAppsAdmin(self.viewer_email,
# 					                                         tenant)  # ※ここでセットするドメインはnamespaceのドメイン（それによってOAuth2かどうかを判定するので）
# 					logging.info('is_admin=' + str(is_admin))
# 				# except sateraito_func.NotInstalledException, instance:
# 				except Exception as e:
# 					# ドメイン内ユーザーではない
# 					logging.error(e)
# 					values = {
# 						'tenant': tenant_from_user_email,
# 						'my_site_url': sateraito_inc.my_site_url,
# 						'vscripturl': sateraito_func.getScriptVirtualUrl(),
# 					}
# 					return render_template('not_installed.html', **values)

# 				try:
# 					logging.info('tenant_from_user_email=' + str(tenant_from_user_email))
# 					sateraito_db.GoogleAppsUserEntry.putNewUserEntry(user_email, user_id, tenant_from_user_email,
# 					                                                 opensocial_info.viewer_id, opensocial_info.container)
# 				except sateraito_func.NotInstalledException as e:
# 					# Application not installed to your domain
# 					values = {
# 						'tenant': tenant_from_user_email,
# 						'my_site_url': sateraito_inc.my_site_url,
# 					}
# 					return render_template('check_start_button_click.html', **values)

# 			# create GoogleAppsDomainEntry if not exists
# 			domain_entry = sateraito_db.GoogleAppsDomainEntry.getInstance(tenant, auto_create=True)

# 			# logout and go to popup2.html page(auto close script)
# 			# logout_url = users.create_logout_url('popup2.html')
# 			# self.redirect(logout_url)
# 			return render_template('popup2.html')
# 		except Exception as e:
# 			logging.exception(e)
# 			return Response('System Error.', status=500)


# class Popup2(WebappHelper):
# 	def get(self):
# 		try:
# 			return render_template('popup2.html')
# 		except Exception as e:
# 			logging.exception(e)
# 			return Response('System Error.', status=500)


# class PopupSubdomain(WebappHelper):
# 	def get(self, token):
# 		try:
# 			return render_template('popup_subdomain.html', {'token': token})
# 		except Exception as e:
# 			logging.exception(e)
# 			return Response('System Error.', status=500)

# 	def post(self, token):
# 		try:
# 			tenant = str(self.request.get('tenant', ''))
# 			return redirect(sateraito_inc.my_site_url + '/' + tenant + '/openid/' + token + '/popup.html')
# 		except Exception as e:
# 			logging.exception(e)
# 			return Response('System Error.', status=500)


# class PopupOid(sateraito_page.Handler_Tenant_Request):
# 	def doAction(self, tenant):
# 		try:
# 			hl = self.request.get('hl', sateraito_inc.DEFAULT_LANGUAGE)
# 			lang = hl
# 			logging.info('tenant=' + str(tenant))

# 			# 認証チェック
# 			loginCheck = self._OIDCAutoLogin(tenant, with_none_prompt=False)
# 			logging.debug(loginCheck)
# 			if not loginCheck.get('status'):
# 				# not logged in: login and go to v2 MainPage
# 				if loginCheck.get('response'):
# 					return loginCheck.get('response')
# 				return self.responseError403()

# 			logging.info('viewer_email=' + str(self.viewer_email))
# 			# Check GoogleApps Domain
# 			tenant_from_user_email = sateraito_func.getDomainPart(self.viewer_email)
# 			target_tenant = tenant_from_user_email

# 			# Clear session/cookie
# 			self.ClearAllSession()
# 			self.removeCookie('oidc_state')
# 			self.removeAppsCookie()

# 			# return make_response('PopupOid',200)

# 			is_admin = False
# 			if target_tenant != '':
# 				logging.info('viewer_email=' + str(self.viewer_email))
# 				# ����ɂ��Ǘ��҂��ǂ����̎擾�Ɩ{Apps�_����̃��[�U�[���ǂ����̔�������˂�
# 				try:
# 					is_admin = sateraito_func.checkAppsAdmin(self.viewer_email,
# 					                                         tenant)  # �������ŃZ�b�g����h���C����namespace�̃h���C���i����ɂ����OAuth2���ǂ����𔻒肷��̂Łj
# 					logging.info(is_admin)
# 				except Exception as e:
# 					logging.error(e)
# 					values = {
# 						'tenant': tenant_from_user_email,
# 						'my_site_url': sateraito_inc.my_site_url,
# 						'version': sateraito_func.getScriptVersionQuery(),
# 						'vscripturl': sateraito_func.getScriptVirtualUrl(),
# 						# 'vscriptliburl': sateraito_func.getScriptLibVirtualUrl(),
# 						'lang': hl,
# 					}
# 					# start http body
# 					logging.info('NOT_INSTALLED')
# 					return render_template('not_installed.html', **values)

# 				try:

# 					sateraito_db.GoogleAppsUserEntry.putNewUserEntry(self.viewer_email,
# 					                                                 self.viewer_user_id,
# 					                                                 sateraito_func.getDomainPart(self.viewer_email),
# 					                                                 self.viewer_id if self.viewer_id is not None and self.viewer_id != '' else '__not_set',
# 					                                                 sateraito_func.OPENSOCIAL_CONTAINER_GOOGLE_SITE)
# 					logging.info(
# 						'putNewUserEntry:' + self.viewer_email + ':' + tenant + ':' + self.viewer_id + ':' + '')
# 				except Exception as e:
# 					# Application not installed to your domain
# 					values = {
# 						'tenant': tenant,
# 						'my_site_url': sateraito_inc.my_site_url,
# 						'version': sateraito_func.getScriptVersionQuery(),
# 						'vscripturl': sateraito_func.getScriptVirtualUrl(),
# 						# 'vscriptliburl': sateraito_func.getScriptLibVirtualUrl(),
# 						'lang': hl,
# 					}
# 					logging.info('NOT_INSTALLED')
# 					return render_template('not_installed.html', **values)

# 			# Save Number of GoogleApps domain user
# 			if target_tenant != '':
# 				# sateraito_func.registDomainEntry(tenant, target_tenant, self.viewer_email)
# 				row = sateraito_db.GoogleAppsDomainEntry.getInstance(target_tenant, auto_create=True)

# 			# for gadget property
# 			lang_file = sateraito_func.getLangFileName(lang)

# 			# check domain_disabled
# 			domain_disabled = False
# 			if sateraito_func.isDomainDisabled(tenant):
# 				domain_disabled = True

# 			is_workflow_admin = False
# 			if self.viewer_email is not None and self.viewer_email != '':
# 				is_workflow_admin = sateraito_func.isWorkflowAdmin(self.viewer_email, tenant)

# 			values = {

# 				# 'user_lang': user_language,
# 				'tenant': tenant,
# 				'my_site_url': sateraito_inc.my_site_url,
# 				'version': sateraito_func.getScriptVersionQuery(),
# 				'vscripturl': sateraito_func.getScriptVirtualUrl(),
# 				# 'vscriptliburl': sateraito_func.getScriptLibVirtualUrl(),
# 				'lang_file': lang_file,
# 				'extjs_locale_file': sateraito_func.getExtJsLocaleFileName(lang),
# 				'is_oidc_need_show_signin_link': False,
# 				'popup': '',
# 				# 'user_info_found': user_info_found,
# 				'viewer_email': self.viewer_email,
# 				# 'user_disabled': False,				# user_entry����ق�Ƃ͎擾���邪���ێg���Ă��Ȃ��̂�..
# 				'domain_disabled': domain_disabled,
# 				'lang': hl,
# 				'is_oauth2_domain': sateraito_func.isOauth2Domain(tenant),
# 				'is_user_admin_oauth2': is_admin,
# 				'is_workflow_admin': is_workflow_admin
# 			}
# 			# start http body
# 			return render_template('popup_oidc.html', **values)

# 		except Exception as e:
# 			logging.exception(e)
# 			return Response('System Error.', status=500)


def add_url_rules(app):
	# app.add_url_rule('/Popup2.html', view_func=Popup2.as_view('Popup2'))
	app.add_url_rule('/<string:tenant>/openid/<string:token>/before_popup.html',
	                 view_func=BeforePopup.as_view('BeforePopup'))
	# app.add_url_rule('/<string:tenant>/openid/<string:token>/popup.html', view_func=Popup.as_view('Popup'))
	# app.add_url_rule('/<string:token>/popup_subdomain.html', view_func=PopupSubdomain.as_view('PopupSubdomain'))
	# app.add_url_rule('/<string:tenant>/popup_oidc.html', view_func=PopupOid.as_view('PopupOid'))
