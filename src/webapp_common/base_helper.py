# coding: utf-8

# GAEGEN2対応:Loggerをカスタマイズ
# import logging
import sateraito_logger as logging
# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行
# import webapp2
import json, urllib, time, datetime
import dateutil.parser  # GAE Gen2対応

from oauthlib.oauth2 import WebApplicationClient
from google.appengine.api import namespace_manager

from ucf.utils.helpers import *
# GAEGEN2対応:Flaskやrequestsライブラリで実装しStreamにも対応
import requests
import sseclient
import hashlib

import sateraito_inc
import sateraito_func

OPENID_COOKIE_NAME = 'SATEID'

############################################################
## WebappHelper
############################################################
class WebappHelper(FrontHelper):

	# GAEGEN2対応
	viewer_email = ''
	viewer_id = ''

	_dept = None
	_is_dept_selected = False
	_is_enable_cors = False

	@property
	def _viewer_email(self):
		return g._viewer_email

	@_viewer_email.setter
	def _viewer_email(self, value):
		g._viewer_email = value

	def init(self):
		u''' 抽象メソッドイメージ '''
		if sateraito_inc.developer_mode:
			self.viewer_email = 'admin@vn2.sateraito.co.jp'
			self.viewer_id = '100663400214546478628'
		
	@convert_result_none_to_empty_str
	def get(self, *args, **keywords):
		self.request.charset = UcfConfig.ENCODING
		self.response.charset = UcfConfig.ENCODING
		self._request_type = UcfConfig.REQUEST_TYPE_GET
		self.init()
		self.onLoad()
		return self.processOfRequest(*args, **keywords)

	@convert_result_none_to_empty_str
	def post(self, *args, **keywords):
		self.request.charset = UcfConfig.ENCODING
		self.response.charset = UcfConfig.ENCODING
		self._request_type = UcfConfig.REQUEST_TYPE_POST
		self.init()
		self.onLoad()
		return self.processOfRequest(*args, **keywords)
	
	def setTenant(self, tenant):
		namespace_manager.set_namespace(tenant.lower())
		self._tenant = tenant
		self._dept = None
		self._is_dept_selected = False
		self._is_enable_cors = True
		#self._error_page = '/a/' + self._tenant + UcfConfig.URL_ERROR

	def getDeptInfo(self, no_memcache=False, is_force_select=False):
		memcache_key = 'deptinfo'
		if is_force_select or (no_memcache and not self._is_dept_selected):
			self._dept = ucffunc.getDeptVo(self)
			self._is_dept_selected = True
			if self._dept is not None:
				DeptUtils.editVoForSelect(self, self._dept)
				memcache.set(key=memcache_key, value=self._dept, time=300)
		elif self._dept is None:
			self._dept = memcache.get(memcache_key)
			if self._dept is None:
				self._dept = ucffunc.getDeptVo(self)
				self._is_dept_selected = True
				if self._dept is not None:
					DeptUtils.editVoForSelect(self, self._dept)
					memcache.set(key=memcache_key, value=self._dept, time=300)
		return self._dept

	def getDeptValue(self, key):
		return self.getDeptInfo().get(key)

	# ユーザーのID、ドメインチェック
	def checkAvailableDomainsOrUsers(self, uid, not_redirect=False):
		# 個人利用、トライアル用の特別テナントについてはノーチェックとする
		is_available_ok = False
		if self._tenant == sateraito_inc.TENANT_ID_FOR_PERSONALUSER:
			is_available_ok = True
		else:
			available_domains_or_users = self.getDeptValue('available_domains_or_users')
			if uid != '':
				if uid.lower() in available_domains_or_users:
					is_available_ok = True
				else:
					uid_sp = uid.split('@')
					if len(uid_sp) > 1 and uid_sp[1].lower() in available_domains_or_users:
						is_available_ok = True
		if not is_available_ok:
			if not_redirect == False:
				self.redirectError(self.getMsg('MSG_INVALID_ACCESS_AUTHORITY'))
			return False, self.getMsg('MSG_INVALID_ACCESS_AUTHORITY')
		return is_available_ok, ''

	def enableCORS(self):
		# set header
		self.response.headers['Access-Control-Allow-Origin' ] = '*'
		# self.response.headers['Access-Control-Allow-Headers'] = 'Origin, X-Requested-With, Content-Type, Accept'
		# self.response.headers['Access-Control-Allow-Methods'] = 'GET, POST'
		self.response.headers['Access-Control-Allow-Headers'] = '*'
		self.response.headers['Access-Control-Allow-Methods'] = '*'

	def isValidTenant(self, tenant, not_redirect=False):
		# 無効テナントかどうかをチェック
		tenant_entry = sateraito_func.TenantEntry.getInstance(tenant, cache_ok=True)
		if tenant_entry is None:
			if not_redirect == False:
				self.redirectError(self.getMsg('MSG_THIS_APPRICATION_IS_NOTINSTALLED_FOR_YOUR_TENANT'))
			return False, self.getMsg('MSG_THIS_APPRICATION_IS_NOTINSTALLED_FOR_YOUR_TENANT')

		if tenant_entry.is_disable == True:
			if not_redirect == False:
				self.redirectError(self.getMsg('MSG_THIS_APPRICATION_IS_STOPPED_FOR_YOUR_TENANT'))
			return False, self.getMsg('MSG_THIS_APPRICATION_IS_STOPPED_FOR_YOUR_TENANT')

		if sateraito_func.isExpireAvailableTerm(tenant_entry):
			if not_redirect == False:
				self.redirectError(self.getMsg('MSG_THIS_APPRICATION_IS_EXPIRE_FOR_YOUR_TENANT'))
			return False, self.getMsg('MSG_THIS_APPRICATION_IS_EXPIRE_FOR_YOUR_TENANT')

		return True, ''

	@classmethod
	def ClearAllSession(self):
		session.clear()

	# セッション取得
	@classmethod
	def getSession(self, key, default=None):
		# flask_sessionライブラリをカスタマイズしてnamespaceをセットするようにしたのでここでのnamespace処理は不要
		# → gaesessionsを使ったDB版の場合は必要
		# strOldNamespace = namespace_manager.get_namespace()
		# logging.info('strOldNamespace=%s' % (strOldNamespace))
		# namespace_manager.set_namespace('')				# namespace指定しているとセットはできるがGETできないので必ずセッション処理の前に空指定！
		# logging.info('emptyNamespace=%s' % (namespace_manager.get_namespace()))
		value = session.get(key, default)
		logging.debug('getsession key=%s value=%s' % (key, value))
		# namespace_manager.set_namespace(strOldNamespace)
		return value

	# セッションに値セット
	@classmethod
	def setSession(cls, key, value):
		# flask_sessionライブラリをカスタマイズしてnamespaceをセットするようにしたのでここでのnamespace処理は不要
		# → gaesessionsを使ったDB版の場合は必要
		# strOldNamespace = namespace_manager.get_namespace()
		# logging.info('strOldNamespace=%s' % (strOldNamespace))
		# namespace_manager.set_namespace('')				# namespace指定しているとセットはできるがGETできないので必ずセッション処理の前に空指定！
		# logging.info('emptyNamespace=%s' % (namespace_manager.get_namespace()))
		# session.permanent = True
		session[key] = value
		logging.debug('setsession key=%s value=%s' % (key, value))

	# namespace_manager.set_namespace(strOldNamespace)

	@classmethod
	def _decryptoForCookie(cls, enc_value):
		try:
			return UcfUtil.deCrypto(enc_value, UcfConfig.COOKIE_CRYPTOGRAPIC_KEY)
		except Exception as e:
			logging.warning('enc_value=' + enc_value)
			logging.warning(e)
			return enc_value

	@classmethod
	def _encryptoForCookie(cls, value):
		return UcfUtil.enCrypto(str(value), UcfConfig.COOKIE_CRYPTOGRAPIC_KEY)

	# クッキーの値を取得（なければNone）
	@classmethod
	def getCookie(cls, name, with_enc=False):
		raw_value = request.cookies.get(name, None)
		if with_enc and raw_value is not None:
			# 復号化
			try:
				value = cls._decryptoForCookie(UcfUtil.urlDecode(raw_value))
			except Exception as e:
				logging.exception(e)
				value = raw_value
			return value
		else:
			return raw_value

	# クッキーの値をセット（期限指定無しの場合は無期限）
	@classmethod
	def setCookie(cls, name, value, expires=None, path='/', secure='secure', domain='', httpOnly=False, living_sec=None,
	              samesite='None'):
		if (sateraito_inc.developer_mode):
			secure = ''
			samesite = ''

		if (not expires):
			if (living_sec) and (living_sec > 0):
				expires = UcfUtil.add_seconds(UcfUtil.getNow(), living_sec).strftime('%a, %d-%b-%Y %H:%M:%S GMT')
			else:
				expires = None

		@after_this_request
		def _setCookie(response):
			dictParam = {
				'secure': (secure == 'secure'),
				'httponly': httpOnly,
			}

			if (expires): dictParam['expires'] = expires
			if (path): dictParam['path'] = path
			if (domain): dictParam['domain'] = domain
			if (samesite): dictParam['samesite'] = samesite

			response.set_cookie(
				name,
				value=value,
				**dictParam
			)
			return response

	# クッキーの値をクリア
	# def clearCookie(self, resp, name, path=None, domain=None):
	#	resp.set_cookie(name, '', expires=0, path=path, domain=domain)
	@classmethod
	def clearCookie(cls, name, path=None, domain=None):
		cls.setCookie(name, '', expires=0, path=path, domain=domain)

	@classmethod
	def removeCookie(cls, name, path=None, domain=None):
		cls.setCookie(name, '', expires=0, path=path, domain=domain)

	@classmethod
	def removeAppsCookie(cls):
		cls.removeCookie('GAPS')
		cls.removeCookie('ACSID')
		cls.removeCookie('SACSID')
		cls.removeCookie('APISID')
		cls.removeCookie('SAPISID')
		cls.removeCookie('HSID')
		cls.removeCookie('SSID')
		cls.removeCookie('PREF')
		cls.removeCookie('_utma')
		cls.removeCookie('_utmb')
		cls.removeCookie('_utmc')
		cls.removeCookie('_utmz')
		# openid connect session
		cls.removeCookie(OPENID_COOKIE_NAME)

	def removeOpenIDConnectCookie(self):
		self.removeCookie(OPENID_COOKIE_NAME)

	@classmethod
	def setNamespace(cls, tenant, app_id=''):
		"""
		Args: tenant
					app_id
		Return: True is app_id is correct, false is not
		"""
		# logging.debug('setNamespace tenant=' + tenant)
		# namespace_name = tenant
		# logging.debug('set namespace:' + namespace_name)
		# namespace_manager.set_namespace(namespace_name)
		# return True
		return sateraito_func.setNamespace(tenant, app_id)

	# Responseヘッダーセット
	@classmethod
	def setResponseHeader(cls, name, value):
		@after_this_request
		def _setResponseHeader(response):
			response.headers[name] = value
			return response

	@classmethod
	def myRedirect(cls, redirect_url):
		return redirect(redirect_url)

	@classmethod
	def responseError403(cls, msg=''):
		# 実際の処理
		return make_response(msg, 403)

	@classmethod
	def returnValue(cls, status, response=None, is_oidc_need_show_signin_link=False):
		return {
			'status': status,
			'is_oidc_need_show_signin_link': is_oidc_need_show_signin_link,
			'response': response
		}

	def getRequestAuthLogin(self, with_error_page=False, with_none_prompt=False,
	                        with_admin_consent=False, with_regist_user_entry=False, url_to_go_after_oidc_login=None,
	                        is_force_auth=False, error_page_url='', add_querys=None, hl=None, prompt_type=None):
		info = ''
		if with_error_page:
			info += '&wep=1&hl=' + sateraito_func.getActiveLanguage('', hl=hl)
		if with_admin_consent:
			info += '&wac=1'
		if with_regist_user_entry:
			info += '&wrue=1'

		# iOS13サードパーティーCookieブロック対策…テナント、ドメインを渡す 2019.09.26
		# info += '&t=' + tenant

		info = info.lstrip('&')
		state = 'state-' + ((UcfUtil.base64Encode(
			info) + '-') if info != '' else '') + sateraito_func.dateString() + sateraito_func.randomString()

		logging.debug('state=' + state)
		self.setSession('state', state)
		expires = UcfUtil.add_hours(UcfUtil.getNow(), 1).strftime('%a, %d-%b-%Y %H:%M:%S GMT')
		self.setCookie('oidc_state', str(state), expires=expires)

		# 認証後にもどってくる用URLを設定	※ガジェット外での新規申請機能対応　2016.03.04
		# G Suite 版申込ページ対応…戻りURL指定対応 2017.06.05
		# url_to_go_after_oidc_login = request.url
		if url_to_go_after_oidc_login is None or url_to_go_after_oidc_login == '':
			url_to_go_after_oidc_login = request.url
		if add_querys is not None:
			for add_query in add_querys:
				url_to_go_after_oidc_login = UcfUtil.appendQueryString(url_to_go_after_oidc_login, add_query[0], add_query[1])
		self.setSession('url_to_go_after_oidc_login', url_to_go_after_oidc_login)
		self.setCookie(urllib.parse.quote(state), str(url_to_go_after_oidc_login), living_sec=30)

		# G Suite 版申込ページ対応…エラーページ対応 2017.06.05
		if with_error_page:
			self.setCookie(urllib.parse.quote(state + '-ep'), str(error_page_url), living_sec=300)
		# self.setCookie(urllib.quote(state + '-ep'), str(error_page_url), expires=expires)

		dictParam = dict(
			scope=sateraito_inc.OAUTH2_SCOPES,  # G Suite 版申込ページ対応 2017.06.05
			redirect_uri=sateraito_inc.my_site_url + '/oidccallback',
			state=state,
			openid_realm=sateraito_inc.my_site_url,
			access_type='online',
			# hd=tenant
		)

		# SameSite 対応 2019/12/24
		if with_none_prompt:
			self.setSession('with_ui', False)
			dictParam['prompt'] = 'none'
		else:
			self.setSession('with_ui', True)
			# set more
			# self.setSession('tenant', tenant)
		# self.setCookie(urllib.parse.quote(state), urllib.parse.quote(str(redirect_url)), living_sec=30,

		# fix google login select_account - edited by tan@vn.sateraito.co.jp 2021-03-12
		# if prompt_type:
		# 	dictParam['prompt'] = prompt_type # 'select_account'

		client = WebApplicationClient(sateraito_inc.WEBAPP_CLIENT_ID)
		auth_uri = client.prepare_request_uri(
			'https://accounts.google.com/o/oauth2/auth',
			**dictParam
		)
		# logging.debug(auth_uri)
		# redirect(auth_uri)
		return auth_uri

	def oidAutoLogin(self, is_multi_domain=False, true_redirecting=False, kozukasan_method=False,
									kozukasan_redirect_to=None, skip_domain_compatibility=False, with_error_page=False,
									with_none_prompt=False, with_select_account_prompt=False, is_force_auth=False, hl=None,
									add_querys=None):
		logging.debug('===========oidAutoLogin============')


		return self._OIDCAutoLogin(skip_domain_compatibility=skip_domain_compatibility,
																with_error_page=with_error_page, with_none_prompt=with_none_prompt,
																with_select_account_prompt=with_select_account_prompt, is_force_auth=is_force_auth,
																hl=hl, add_querys=add_querys)

	# ログインチェック処理
	def checkLogin(self):

		logging.debug('_OidBasePage.checkLogin...')
		# tenant param check
		# if str(tenant).find('.') == -1:
		# 	# if tenant contains no '.', it is wrong
		# 	logging.info('wrong domain name:' + str(tenant))
		# 	return self.responseError403('wrong domain name:' + str(tenant))

		# if domain_dict.get('no_auto_logout', False):
		# 	is_force_auth = False
		# else:
		# 	is_force_auth = self.request.get('oidc') != 'cb'
		# is_force_auth = self.request.get('oidc') != 'cb'

		if sateraito_inc.developer_mode:
			self.viewer_email = 'admin@vn2.sateraito.co.jp'
			self.viewer_id = '100663400214546478628'
			return True

		# check session login
		self.viewer_email = self.session.get('viewer_email')
		logging.info('viewer_email=' + str(self.viewer_email))
		self.viewer_id = self.session.get('opensocial_viewer_id')
		logging.info('opensocial_viewer_id=' + str(self.viewer_id))

		return (self.viewer_email is not None) and (str(self.viewer_email).strip() != '')

	def checkOidRequest(self, tenant, is_without_check_csrf_token=False,
	                    is_without_error_response_status=False, domain_dict=None):
		mode = self.request.get('mode', '')
		logging.debug('mode=' + mode)

		logging.debug('========checkOidRequest===============')

		return self._checkOIDCRequest(tenant, is_without_check_csrf_token)

	def _checkOIDCRequest(self, tenant, is_without_check_csrf_token=False,
	                      is_without_error_response_status=False, skip_domain_compatibility=False):

		if sateraito_inc.developer_mode:
			skip_domain_compatibility = True

		# CSRFトークンチェック
		if not is_without_check_csrf_token and sateraito_func.checkCsrf(request) == False:
			logging.exception('Invalid token')
			# if not is_without_error_response_status:
			# 	self.response.set_status(403)
			return False

		# check if openid connect login
		viewer_email = self.getSession('viewer_email')
		logging.debug('viewer_email=' + str(viewer_email))
		is_oidc_loggedin = self.getSession('is_oidc_loggedin')
		logging.debug('is_oidc_loggedin=' + str(is_oidc_loggedin))
		if is_oidc_loggedin is None or not is_oidc_loggedin or viewer_email is None:
			logging.debug('_checkOIDCRequest:user not logged in')
			# self.response.set_status(403)
			return False

		viewer_email_domain = sateraito_func.getDomainPart(viewer_email)
		if viewer_email_domain != tenant:
			if not skip_domain_compatibility:
				logging.error('unmatched google apps domain and login user')
				return False
				# if not sateraito_func.isCompatibleDomain(tenant, viewer_email_domain):
				# 	logging.error('unmatched google apps domain and login user')
				# 	# self.response.out.write('unmatched google apps domain and login user')
				# 	# self.response.set_status(403)
				# 	return False
		self.viewer_email = viewer_email.lower()
		self.viewer_user_id = user.user_id()
		return True

	
	# OpenIDConnect用
	# ※ ガジェット外での新規申請機能対応：add_querys引数追加 2016.03.04
	# G Suite 版申込ページ対応…引数いくつか追加 2017.06.05
	def _OIDCAutoLogin(self, skip_domain_compatibility=False, with_error_page=False,
										error_page_url='', with_none_prompt=False, with_select_account_prompt=False,
										with_admin_consent=False, with_regist_user_entry=False, is_force_auth=False, hl=None,
										url_to_go_after_oidc_login=None, add_querys=None, prompt_type=None):
		"""
		Returns
			is_ok: boolean
				True .. user already logged in
				False .. user not logged in, processing oid login
			body_for_not_ok: str
				html or plain text data to respond if not ok case
		"""
		# fix google login select_account - edited by tan@vn.sateraito.co.jp 2021-03-12
		if prompt_type == 'select_account':
			logging.info('force remove auth sessions...')
			self.session['viewer_email'] = ''
			self.session['loggedin_timestamp'] = None  # G Suiteのマルチログイン時にiframe内でOIDC認証ができなくなったので強制で少しだけ高速化オプションする対応＆SameSite対応 2019.10.28
			self.session['opensocial_viewer_id'] = ''
			self.session['is_oidc_loggedin'] = False
			self.session['is_oidc_need_show_signin_link'] = False
			self.removeAppsCookie()

		# 強制的に再認証をさせるためセッションを破棄（CookieのセッションIDの破棄ではなくセッションの値をそれぞれ個別に破棄） 2016.05.27
		if is_force_auth:
			# G Suiteのマルチログイン時にiframe内でOIDC認証ができなくなったので強制で少しだけ高速化オプションする対応 2019.10.28
			# SameSite対応…SameSite対応でもどっちにしてもこの対応は必要　→　強制高速化オプションを強制するようになったのでSameSite対応のためには不要
			loggedin_timestamp = self.session.get('loggedin_timestamp')
			# GAE Gen2対応
			if isinstance(loggedin_timestamp, str):
				loggedin_timestamp = dateutil.parser.parse(loggedin_timestamp)

			if loggedin_timestamp is None or loggedin_timestamp < UcfUtil.add_minutes(datetime.datetime.now(), -5):
				logging.info('force remove auth sessions...')
				self.session['viewer_email'] = ''
				self.session['loggedin_timestamp'] = None  # G Suiteのマルチログイン時にiframe内でOIDC認証ができなくなったので強制で少しだけ高速化オプションする対応＆SameSite対応 2019.10.28
				self.session['opensocial_viewer_id'] = ''
				self.session['is_oidc_loggedin'] = False
				self.session['is_oidc_need_show_signin_link'] = False

		# check openid connect login
		viewer_email = self.session.get('viewer_email')
		logging.info('viewer_email=' + str(viewer_email))
		opensocial_viewer_id = self.session.get('opensocial_viewer_id')
		logging.info('opensocial_viewer_id=' + str(opensocial_viewer_id))
		is_oidc_loggedin = self.session.get('is_oidc_loggedin')
		logging.info('is_oidc_loggedin=' + str(is_oidc_loggedin))
		is_oidc_need_show_signin_link = self.session.get('is_oidc_need_show_signin_link')
		logging.info('is_oidc_need_show_signin_link=' + str(is_oidc_need_show_signin_link))

		# if sateraito_inc.developer_mode:
		# 	viewer_email = 'admin@satelaito.jp'
		# 	opensocial_viewer_id = 'viewer_id_xxx'
		# 	is_oidc_loggedin = True
		# 	is_oidc_need_show_signin_link = False

		# エラーが返る場合は画面上に「認証する」を出すためにFalseを返す 2016.04.03
		if with_none_prompt and is_oidc_need_show_signin_link:
			return False, ''

		logging.info('_OIDCAutoLogin viewer_email=' + str(viewer_email))
		# if is_oidc_loggedin is None or not is_oidc_loggedin or viewer_email is None:
		if is_oidc_loggedin is None or not is_oidc_loggedin or viewer_email is None or viewer_email == '':

			# iOSのX-Frame-Options:Deny対策…iOS、iPadOS、MacのSafari、FireFox、セキュリティブラウザの場合は認証するリンクからポップアップで認証する（Chromeは今のところ一応除外） 2021.04.15
			# strAgent = self.request.headers.get('User-Agent').lower()  # g2対応
			strAgent = self.request.headers.get('User-Agent', '').lower()
			logging.info('strAgent=' + str(strAgent))
			# if with_none_prompt and (strAgent.find('AppleWebKit'.lower()) >= 0 and (strAgent.find('iPhone'.lower()) >= 0 or strAgent.find('iPad'.lower()) >= 0) and not (strAgent.find('Chrome'.lower()) >= 0 or strAgent.find('CriOS'.lower()) >= 0)):
			# iOS：セキュリティブラウザ、Safari　Mac：Safari で事象解消を確認のため変更（Mac版セキュリティブラウザはNG） 2022/07/07
			# if with_none_prompt and ((strAgent.find('iPhone'.lower()) >= 0 or strAgent.find('iPad'.lower()) >= 0 or strAgent.find('Macintosh;'.lower()) >= 0) and not (strAgent.find('Chrome'.lower()) >= 0 or strAgent.find('CriOS'.lower()) >= 0)):
			if with_none_prompt and strAgent.find('Macintosh;'.lower()) >= 0 and strAgent.find('/SateraitoSecurityBrowser'.lower()) >= 0:
				self.session['is_oidc_need_show_signin_link'] = True
				return False, ''
			# その他OSのFireFoxも追加（FireFoxESRという特殊なブラウザでブロックされるようになったため） 2021.04.28
			elif with_none_prompt and strAgent.find('FireFox'.lower()) >= 0:
				self.session['is_oidc_need_show_signin_link'] = True
				return False, ''

			# go login

			# サードパーティCookie無効時に403ではなくメッセージを出す対応（stateに情報を含めてoidccallback側で制御）
			# G Suite 版申込ページ対応 2017.06.05
			# if with_error_page:
			#	info = 'wep=1&hl=' + sateraito_func.getActiveLanguage('', hl=hl)
			#	info_base64 = UcfUtil.base64Encode(info)
			#	state = 'state-' + info_base64 +  '-' + sateraito_func.dateString() + sateraito_func.randomString()
			# else:
			#	state = 'state-' + sateraito_func.dateString() + sateraito_func.randomString()
			info = ''
			if with_error_page:
				info += '&wep=1&hl=' + sateraito_func.getActiveLanguage('', hl=hl)
			if with_admin_consent:
				info += '&wac=1'
			if with_regist_user_entry:
				info += '&wrue=1'

			# # iOS13サードパーティーCookieブロック対策…テナント、ドメインを渡す 2019.09.26
			# info += '&t=' + google_apps_domain

			info = info.lstrip('&')
			state = 'state-' + ((UcfUtil.base64Encode(info) + '-') if info != '' else '') + sateraito_func.dateString() + sateraito_func.randomString()

			logging.info('state=' + state)
			self.session['state'] = state
			# セッションでもいいのだがタイムラグが気になるのでCookieにする
			expires = UcfUtil.add_hours(UcfUtil.getNow(), 1).strftime('%a, %d-%b-%Y %H:%M:%S GMT')
			self.setCookie('oidc_state', str(state), expires=expires)

			# 認証後にもどってくる用URLを設定	※ガジェット外での新規申請機能対応　2016.03.04
			# G Suite 版申込ページ対応…戻りURL指定対応 2017.06.05
			# url_to_go_after_oidc_login = self.request.url
			if url_to_go_after_oidc_login is None or url_to_go_after_oidc_login == '':
				url_to_go_after_oidc_login = self.request.url
			if add_querys is not None:
				for add_query in add_querys:
					url_to_go_after_oidc_login = UcfUtil.appendQueryString(url_to_go_after_oidc_login, add_query[0], add_query[1])
			self.session['url_to_go_after_oidc_login'] = url_to_go_after_oidc_login

			# for 'multiple iframe gadget in a page' case login
			# self.setCookie(urllib.quote(state), str(self.request.url), living_sec=30)
			# self.setCookie(urllib.quote(state), str(url_to_go_after_oidc_login), living_sec=30)  # g2対応
			self.setCookie(urllib.parse.quote(state), str(url_to_go_after_oidc_login), living_sec=30)

			# G Suite 版申込ページ対応…エラーページ対応 2017.06.05
			if with_error_page:
				# self.setCookie(urllib.quote(state + '-ep'), str(error_page_url), living_sec=300)  # g2対応
				self.setCookie(urllib.parse.quote(state + '-ep'), str(error_page_url), living_sec=300)

			# G Suite 版申込ページ対応…管理者チェック時はAdminSDKを含むスコープを指定 2017.06.05
			# Google+API、Scope廃止対応 2019.02.01
			# scope = ['https://www.googleapis.com/auth/plus.me', 'https://www.googleapis.com/auth/plus.profile.emails.read']
			scope = sateraito_inc.OAUTH2_SCOPES
			if with_admin_consent:
				# scope.extend(['https://www.googleapis.com/auth/admin.directory.user.readonly', 'https://www.googleapis.com/auth/admin.directory.group.readonly'])
				scope = sateraito_inc.ADMIN_CONSENT_OAUTH2_SCOPES
			# GAE Gen2対応
			# flow = OAuth2WebServerFlow(
			# 						client_id=sateraito_inc.WEBAPP_CLIENT_ID,
			# 						client_secret=sateraito_inc.WEBAPP_CLIENT_SECRET,  # client_secret を渡すとエラーになる
			dictParam = dict(
				scope=scope,  # G Suite 版申込ページ対応 2017.06.05
				redirect_uri=sateraito_inc.my_site_url + '/oidccallback',
				state=state,
				# openid_realm=sateraito_inc.my_site_url,
				# login_hint='@'+google_apps_domain,
				# hd=google_apps_domain,				# セカンダリドメインのユーザーが認証できない....
				access_type='online'
				# prompt='none' if with_none_prompt else None,						# 参考：https://developers.google.com/identity/protocols/OpenIDConnect#authenticationuriparameters
			)

			if with_none_prompt:
				# GAE Gen2対応
				# flow.params['prompt'] ='none'						# 参考：https://developers.google.com/identity/protocols/OpenIDConnect#authenticationuriparameters
				dictParam['prompt'] = 'none'
			elif with_select_account_prompt:
				# GAE Gen2対応
				# flow.params['prompt'] ='select_account'
				dictParam['prompt'] = 'select_account'
			else:
				# if google_apps_domain == 'satelaito.jp':
				#	flow.params['prompt'] ='select_account'
				pass

			# GAE Gen2対応
			# auth_uri = flow.step1_get_authorize_url()
			client = WebApplicationClient(sateraito_inc.WEBAPP_CLIENT_ID)
			auth_uri = client.prepare_request_uri('https://accounts.google.com/o/oauth2/auth', **dictParam)

			logging.info('auth_uri=' + str(auth_uri))

			# Microsoft Office文書内に「メールに張り付けられるリンク」を張った場合の動作対応（ワークフローでは今のところこの機能はないが実装しておく） 2015.09.02
			# 参考）
			#   ■ Office製品のハイパーリンクとログイン認証画面
			#     http://hajimesan.net/blog/?p=875
			#   ■ Office 文書内のハイパーリンクを開くと Cookie が紛失する - Microsoftサポート
			#     https://support.microsoft.com/ja-jp/kb/811929/ja

			# self.redirect(auth_uri)

			# check user-agent(Office)
			# sample)
			#   Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET CLR 1.1.4322; .NET4.0E; InfoPath.1; ms-office)
			# user_agent = str(self.request.user_agent)  # g2対応
			user_agent = str(self.request.headers.get('User-Agent'))
			logging.debug('** _OIDCAutoLogin user_agent=' + str(user_agent))
			is_opened_from_msoffice = False
			if 'ms-office' in user_agent and 'MSIE' in user_agent:
				is_opened_from_msoffice = True

			# go jump or redirect
			if is_opened_from_msoffice:
				logging.info('url opened by msoffice link click. jumping by html meta tag...')
				ret_datas = []
				ret_datas.append('<html><head>')
				ret_datas.append('<meta http-equiv="refresh" content="1;URL=' + str(auth_uri) + '">')
				ret_datas.append('</head><body></body></html>')
				return False, ''.join(ret_datas)
			else:
				self.redirect(auth_uri)
				return False, ''

		# # check domain
		# viewer_email_domain = sateraito_func.getDomainPart(viewer_email)
		# if viewer_email_domain != google_apps_domain:
		# 	if not skip_domain_compatibility:
		# 		# if not sateraito_func.isCompatibleDomain(google_apps_domain, viewer_email_domain):
		# 		if not sateraito_func.isCompatibleDomain(google_apps_domain, viewer_email_domain):
		# 			# logging.error('unmatched google apps domain and login user')
		# 			logging.warning('unmatched google apps domain and login user')
		# 			# self.response.out.write('wrong request:login user is ' + str(self.viewer_email) + '.')
		# 			self.response.set_status(403)
		# 			return False, 'wrong request'

		self.viewer_email = str(viewer_email).lower()
		self.viewer_id = str(opensocial_viewer_id)
		logging.info('self.viewer_email=' + self.viewer_email)
		logging.info('auth result=True')
		return True, ''

	def send_error_response(self, error=None):
		data_reponse = {
			'status': 'ng',
		}

		if error is not None:
			data_reponse['data'] = error

		if self._is_enable_cors:
			self.enableCORS()
		self.response.headers['Content-Type'] = 'application/json'
		return self.response.out.write(json.JSONEncoder().encode(data_reponse))

	def send_success_response(self, data=None):
		data_reponse = {
			'status': 'ok',
		}
		if data is not None:
			data_reponse['data'] = data

		if self._is_enable_cors:
			self.enableCORS()
		self.response.headers['Content-Type'] = 'application/json'
		return self.response.out.write(json.JSONEncoder().encode(data_reponse))

	def responseAjaxResult(self, ret_value={}):
		if ret_value is None:
			ret_value = {}
		ret_value['msg'] = self._msg
		ret_value['code']= self._code

		logging.info(ret_value)

		if self._is_enable_cors:
			self.enableCORS()
		self.response.headers['Content-Type'] = 'application/json'
		return self.response.out.write(json.JSONEncoder().encode(ret_value))

	def render_template(self, template_name, design_type, vals, content_type=None):

		# 文字コード指定：これをやらないとmetaタグだけでは文字コードをブラウザが認識してくれないため。
		#self.response.headers['Content-Type'] = 'text/html; charset=' + UcfConfig.ENCODING + ';'
		#encodeとcharsetのマッピング対応 2009.5.20 Osamu Kurihara
		if UcfConfig.ENCODING=='cp932':
			charset_string='Shift_JIS'
			#charset_string = UcfConfig.FILE_CHARSET
		#マッピング定義がないものはUcfConfig.ENCODING
		else:
			charset_string=UcfConfig.ENCODING

		if content_type is None or content_type == '':
			content_type = 'text/html'
		self.response.headers['Content-Type'] = content_type + '; charset=' + charset_string + ';'

		# レンダリング
		jinja_environment = sateraito_jinja2_environment.getEnvironmentObj(design_type)
		template = jinja_environment.get_template(template_name)
		return template.render(vals)
	
	# ログインユーザにパスワード変更を強制するフラグをセッションにセット
	def setLoginOperatorForcePasswordChangeFlag(self, force_type):
		self.setSession(UcfConfig.SESSIONKEY_LOGIN_FORCE_PASSWORD_CHANGE, force_type)

	# 「rurl_key」をセッションにセット　…パスワード変更ページなどから「元の認証ページに戻る」ためのキー
	def setLoginOperatorRURLKey(self, rurl_key):
		key = UcfConfig.SESSIONKEY_RURL_KEY
		self.setSession(key, rurl_key)

# =============Handler========================

# /healthなど一般的なページのベースクラス（多重継承して使います）
class Handler_Basic_Request(FrontHelper):

	def get(self, *args, **keywords):
		logging.debug('Handler_Basic_Request:get...')
		# 実際の処理
		return self.doAction(*args, **keywords)

	def post(self, *args, **keywords):
		logging.debug('Handler_Basic_Request:post...')
		# 実際の処理
		return self.doAction(*args, **keywords)

	# GAEGEN2対応：Responseヘッダーセット用（本来はResponseをReturnする直前で行う必要があるが任意の場所でResponseヘッダーをセットするためのMethod）
	@classmethod
	def setResponseHeader(cls, name, value):
		@after_this_request
		def _setResponseHeader(response):
			response.headers[name] = value
			return response


class Handler_Basic_APIRequest(FrontHelper):

	def get(self, tenant, *args, **keywords):
		logging.debug('Handler_Basic_Request:get...')
		# 実際の処理
		return self.doAction(tenant, *args, **keywords)

	def post(self, tenant, *args, **keywords):
		logging.debug('Handler_Basic_Request:post...')
		# 実際の処理
		return self.doAction(tenant, *args, **keywords)

	# GAEGEN2対応：Responseヘッダーセット用（本来はResponseをReturnする直前で行う必要があるが任意の場所でResponseヘッダーをセットするためのMethod）
	@classmethod
	def setResponseHeader(cls, name, value):
		@after_this_request
		def _setResponseHeader(response):
			response.headers[name] = value
			return response


# タスクキュー認証用のPost処理を行うベースクラス（多重継承して使います）
class Handler_TaskQueue_Post(MethodView):
	def post(self, task_id, *args, **keywords):
		logging.debug('Handler_TaskQueue_Post:post...')
		# タスクキュー用の認証チェック（必要なら）
		# if (not self._checkGadgetRequest()):
		#	return Response('', 403)
		# 実際の処理
		return self.doAction(task_id, *args, **keywords)


# テナント用各ページの処理を行うベースクラス（多重継承して使います）
class Handler_Tenant_Request(WebappHelper):

	#	# 共通処理：Pythonデコレータ方式
	#	@classmethod
	#	def base_decorator(cls, func):
	#		@wraps(func)
	#		def _wrapper(*args, **keywords):

	def _common_processing(sef):
		# ヘッダーの出力
		for k, v in request.headers:
			logging.debug('[header]key=%s value=%s' % (k, v))
		# GET,POSTデータの出力
		for value in request.args:
			logging.debug('[get]key=%s value=%s' % (value, request.args[value]))
		for value in request.form:
			logging.debug('[post]key=%s value=%s' % (value, request.form[value]))

	# @Handler_Tenant_Request.base_decorator
	def get(self, tenant, token=None, *args, **keywords):
		logging.debug('Handler_Tenant_Request:get...')
		logging.debug('tenant:%s' % (tenant))
		self._common_processing()

		# 実際の処理
		if token:
			# run with token
			return self.doAction(tenant, token, *args, **keywords)
		else:
			return self.doAction(tenant, *args, **keywords)

	# @Handler_Tenant_Request.base_decorator
	def post(self, tenant, token=None, *args, **keywords):
		logging.debug('Handler_Tenant_Request:post...')
		logging.debug('tenant:%s' % (tenant))
		self._common_processing()

		# 実際の処理
		if token:
			# run with token
			return self.doAction(tenant, token, *args, **keywords)
		else:
			return self.doAction(tenant, *args, **keywords)
