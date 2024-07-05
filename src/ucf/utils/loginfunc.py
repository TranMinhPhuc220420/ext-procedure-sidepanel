# coding: utf-8

import os,sys,datetime,logging,random,json
import re,sre_constants
from ucf.utils.models import UCFMDLLoginHistory,UCFMDLLoginHistoryDetail
from ucf.utils.ucfutil import *
from ucf.config.ucfconfig import *
from ucf.utils.helpers import *
from ucf.pages.operator import OperatorUtils
from ucf.pages.login_history import LoginHistoryUtils
import sateraito_func
import sateraito_inc
import oem_func
from google.appengine.api import taskqueue
import jwt_custom

#+++++++++++++++++++++++++++++++++++++++
#+++ ログイン認証
#+++++++++++++++++++++++++++++++++++++++
def authLogin(helper, login_user_domain, login_id, login_password, is_set_next_auto_login=False, is_auto_login=False, is_not_update_login_history=False, is_nocheck_password=False, is_nocheck_two_factor_auth=False, two_factor_auth_code=''):
	isLogin = False
	login_result = {}
	isAuthSuccess = False

	login_id = UcfUtil.nvl(login_id)
	login_id = login_id.strip()
	login_password = UcfUtil.nvl(login_password)
	login_password = login_password.strip()
	# Androidなどから円マークが入った場合にバックスラッシュに変換する対応 2019.09.03
	login_password = login_password.replace(u'\xa5', u'\x5c').replace(u'\uffe5', u'\x5c')
	login_email = ''
	login_name = ''
	login_access_authority = ''
	login_delegate_function = ''
	login_delegate_management_groups = ''

	login_id_split = login_id.split('@')
	if len(login_id_split) < 2 and login_user_domain != '':
		login_id_withdomain = login_id + '@' + login_user_domain
	else:
		login_id_withdomain = login_id
	login_id_withoutdomain = login_id_split[0]

	###########################################################

	##################################################
	user_vo = None

	user_vo = OperatorUtils.getUserByOperatorID(helper, login_id_withdomain)

	if user_vo is None:
		login_result['error_code'] = 'ID_FAILED'
		isLogin = False
		# ログイン履歴インサート
		insertLoginHistoryAsync(helper, isLogin, isAuthSuccess, login_result, user_vo, is_auto_login, login_id, login_name, login_access_authority, login_email, login_password, is_set_next_auto_login)
		return isLogin, login_result

	isLogin = False
	isUserStatusNG = False

	# ユーザマスタ設定に基づくチェック （パスワード認証後からここに移動 2014.02.16）
	# アカウント停止フラグ
	if UcfUtil.getHashStr(user_vo, 'account_stop_flag') == 'STOP':
		login_result['error_code'] = 'ACCOUNT_STOP'
		isUserStatusNG = True

	# ログインロック
	elif UcfUtil.getHashStr(user_vo, 'login_lock_flag') == 'LOCK':
		if UcfUtil.getHashStr(user_vo, 'login_lock_expire') != '' and UcfUtil.getDateTime(UcfUtil.getHashStr(user_vo, 'login_lock_expire')) >= UcfUtil.getNowLocalTime(helper._timezone): 
			login_result['error_code'] = 'LOGIN_LOCK'
			isUserStatusNG = True


	# これまでのチェックがOKならパスワードなどの認証
	if not isUserStatusNG:
		# パスワードチェック
		if not is_nocheck_password and UcfUtil.getHashStr(user_vo, 'password') != login_password:
			login_result['error_code'] = 'PASSWORD_FAILED'
			isLogin = False
		else:
			login_email = UcfUtil.getHashStr(user_vo, 'operator_id')
			login_immutable_id = UcfUtil.getHashStr(user_vo, 'immutable_id')
			login_name = helper.getUserNameDisp(UcfUtil.getHashStr(user_vo, 'last_name'), UcfUtil.getHashStr(user_vo, 'first_name'))
			login_access_authority = UcfUtil.getHashStr(user_vo, 'access_authority')
			login_delegate_function = UcfUtil.getHashStr(user_vo, 'delegate_function')
			login_delegate_management_groups = UcfUtil.getHashStr(user_vo, 'delegate_management_groups')
			isLogin = True

	# 二要素認証のチェック
	is_nooutput_log = False
	isSuccessTwoFactorAuth = False
	if isLogin:
		isAuthSuccess = True		# アクセス制御でNGになったとしても、ID、パスワード認証だけは通ったフラグを立てておく（ログイン失敗回数を更新しないため）
		if not is_nocheck_two_factor_auth and isActiveTwoFactorAuth(helper) and UcfUtil.getHashStr(user_vo, 'sub_mail_address') != '':
			
			# 二要素認証コードを必要に応じて発行＆メール送信
			ucffunc.publishAndSendTwoFactorAuthCode(helper, user_vo)
			# 二要素認証コード入力ボックスを不必要に表示しないように、ここを通った場合だけ表示するようにする 2015.06.24
			login_result['is_disp_two_factor_auth_code'] = True

			if two_factor_auth_code is None or two_factor_auth_code == '':
				login_result['error_code'] = 'TWO_FACTOR_AUTH_REQUIRED'
				isLogin = False
				#is_nooutput_log = not helper._is_api		# これはログインエラーではないので何もログを取らずにリターン（APIの場合はログ取っていい）
				is_nooutput_log = True
			elif not ucffunc.isValidTwoFactorAuthCode(helper, two_factor_auth_code, user_vo):
				login_result['error_code'] = 'TWO_FACTOR_AUTH_FAILED'
				isLogin = False
			else:
				isSuccessTwoFactorAuth = True


	if isLogin:
		logout(helper, without_clear_cookie=True)
		#ログイン認証IDを新規発行
		setNewLoginAuthID(helper)

#		# マルチドメイン対応：ログイン時のドメインを親ドメインをキーとしてCookieにセット
#		setLoginDomainNameToCookie(helper)
		setLoginInfo(helper, is_set_next_auto_login, login_id, login_name, login_access_authority, login_delegate_function, login_delegate_management_groups, login_email, login_password, user_vo)

	if not is_nooutput_log:
		# ユーザ更新…ログイン回数、ログイン失敗回数、最終ログイン日時、ログインロックフラグ＆期限を更新
		isClearTwoFactorAuthInfo = isLogin and isSuccessTwoFactorAuth	# ログイン成功したら二要素認証コードをクリア
		updateUserForLoginAsync(helper, isLogin, isAuthSuccess, isClearTwoFactorAuthInfo, user_vo, is_auto_login, login_id, login_name, login_access_authority, login_email, login_password, is_set_next_auto_login, is_not_update_login_history)

		# ログイン履歴に1件インサート
		insertLoginHistoryAsync(helper, isLogin, isAuthSuccess, login_result, user_vo, is_auto_login, login_id, login_name, login_access_authority, login_email, login_password, is_set_next_auto_login)

	if user_vo is not None:
		login_result['user_vo'] = user_vo

	return isLogin, login_result

# ログインエラーコードからパスワードリマインダを表示するかどうかを判断する
def isDispPasswordReminderLink(helper, error_code):
	return error_code in ['ID_FAILED', 'PASSWORD_FAILED', 'LOGIN_LOCK']


# 二要素認証が有効かどうか
def isActiveTwoFactorAuth(helper):
	return True

# エラーコードからログインのエラーメッセージを返す
def getMessageByErrorCode(helper, error_code, is_lock_indefinitely=False):
	msg = ''
	if error_code == 'ID_FAILED':
		msg = helper.getMsg('MSG_FAILED_LOGIN_BY_ID')
	elif error_code == 'PASSWORD_FAILED':
		msg = helper.getMsg('MSG_FAILED_LOGIN_BY_PASSWORD')
	elif error_code == 'LOGIN_LOCK':
		# 無期限ロックの場合にメッセージ変える対応 2016.12.16
		if is_lock_indefinitely:
			msg = helper.getMsg('MSG_FAILED_LOGIN_BY_LOCK_INDEFINITELY')
		else:
			msg = helper.getMsg('MSG_FAILED_LOGIN_BY_LOCK')
	elif error_code == 'ACCOUNT_STOP':
		msg = helper.getMsg('MSG_FAILED_LOGIN_BY_ACCOUNT_STOP')
	elif error_code == 'TWO_FACTOR_AUTH_REQUIRED':
		msg = helper.getMsg('MSG_FAILED_LOGIN_BY_TWO_FACTOR_AUTH_REQUIRED')
	elif error_code == 'TWO_FACTOR_AUTH_FAILED':
		msg = helper.getMsg('MSG_FAILED_LOGIN_BY_TWO_FACTOR_AUTH_FAILED')
	else:
		msg = helper.getMsg('MSG_FAILED_LOGIN')
	return msg

# ユーザ更新（非同期）…ログイン回数、ログイン失敗回数、最終ログイン日時、ログインロックフラグ＆期限を更新
def updateUserForLoginAsync(helper, isLogin, isAuthSuccess, isClearTwoFactorAuthInfo, user_vo, is_auto_login, login_id, login_name, login_access_authority, login_email, login_password, is_set_next_auto_login, is_not_update_login_history):

	user_unique_id = UcfUtil.getHashStr(user_vo, 'unique_id') if user_vo is not None else ''

	# Save Number of GoogleApps domain user
	params = {
			'isLogin': isLogin,
			'user_unique_id': user_unique_id,
			'is_auto_login': is_auto_login,
			'login_id': login_id,
			'login_name': login_name,
			'login_access_authority': login_access_authority,
			'login_email': login_email,
			'login_password': login_password,
			'is_set_next_auto_login': is_set_next_auto_login,
			'is_not_update_login_history': is_not_update_login_history,
			'isAuthSuccess':isAuthSuccess,
			'isClearTwoFactorAuthInfo':isClearTwoFactorAuthInfo,
	}

	token = UcfUtil.guid()
	# taskに追加 まるごと
	import_q = taskqueue.Queue('process-login')
	import_t = taskqueue.Task(
			url='/a/' + helper._tenant + '/openid/' + token + '/update_user_for_login',
			params=params,
			countdown='0'
	)
	import_q.add(import_t)

# ユーザ更新…ログイン回数、ログイン失敗回数、最終ログイン日時、ログインロックフラグ＆期限を更新
def updateUserForLogin(helper, isLogin, isAuthSuccess, user_unique_id, is_auto_login, login_id, login_name, login_access_authority, login_email, login_password, is_set_next_auto_login, is_not_update_login_history):
	if user_unique_id is not None and user_unique_id != '':
		if is_not_update_login_history == False:
			entry = OperatorUtils.getData(helper, user_unique_id)
			if entry is not None:
				# ログイン認証に成功したら
				if isLogin:
					entry.login_count = 1 if entry.login_count is None else entry.login_count + 1		# ログイン回数
					entry.last_login_date = UcfUtil.getNow()		# 最終ログイン日時（UTC）
					entry.login_lock_flag = ''		# ログインロックフラグクリア
		#			entry.login_lock_expire = ''		# ログインロック期限（は一応残しておく）
					entry.login_failed_count = 0		# 連続ログイン失敗回数（クリア）
					entry.login_password_length = len(login_password)		# 最終ログイン時のパスワード長
				# ID、パスワード認証には成功したが、アクセス制御ではじかれた場合、ログイン回数などの更新はしない
				elif isAuthSuccess:
					pass
				# 完全に失敗したら
				else:

					# 現在、ステータスとロック期限的にロック中かどうか
					is_current_lock_status = False
					if entry.login_lock_flag == 'LOCK' and entry.login_lock_expire is not None and entry.login_lock_expire >= UcfUtil.getNow():
						is_current_lock_status = True

					# プロファイルでログインロック機能が有効かとその場合の許容連続失敗回数
					is_lock_func_available = False
					login_lock_max_failed_count = 0
					# ログインロック機能はほしいのでとりあえず固定で設定
					#if profile_vo is not None and UcfUtil.getHashStr(profile_vo, 'login_lock_available_flag') == 'AVAILABLE':
					#	is_lock_func_available = True
					#	login_lock_max_failed_count = 0 if profile_vo['login_lock_max_failed_count'] == '' else int(profile_vo['login_lock_max_failed_count'])
					is_lock_func_available = True
					login_lock_max_failed_count = 5

					# 現在のログイン失敗回数
					current_login_failed_count = 0 if entry.login_failed_count is None else entry.login_failed_count

					logging.info('is_current_lock_status=' + str(is_current_lock_status))
					logging.info('is_lock_func_available=' + str(is_lock_func_available))
					logging.info('login_lock_max_failed_count=' + str(login_lock_max_failed_count))
					logging.info('current_login_failed_count=' + str(current_login_failed_count))
	
					# セットするログイン失敗回数を決定
					login_failed_count = current_login_failed_count + 1
					# ログイン失敗回数が既にプロファイルで指定された最大失敗回数以上（すなわち前回のログイン施行時ロックされたあるいはされている状態だった）でかつ現状、ロックフラグがOFFあるいは期限が過ぎている場合、
					# ここでは再度１から回数を振りなおす対応 2014.02.17
					if not is_current_lock_status and is_lock_func_available:
						if current_login_failed_count >= login_lock_max_failed_count:
							login_failed_count = 1
					# 連続ログイン失敗回数をセット
					entry.login_failed_count = login_failed_count

					# 連続ログイン失敗がプロファイルによる設定回数を超えたらロックフラグと期限を設定（既にロックフラグがたっていれば期限を更新することはとりあえずしない）
					if is_lock_func_available and entry.login_lock_flag != 'LOCK' and login_failed_count >= login_lock_max_failed_count:
						entry.login_lock_flag = 'LOCK'		# ログインロックフラグセット
						# ログインロック機能はほしいのでとりあえず固定で設定
						#entry.login_lock_expire = calculateLoginLockExpire(helper, profile_vo['login_lock_expire_info'])		# ログインロック期限セット（UTC算出）
						entry.login_lock_expire = calculateLoginLockExpire(helper)		# ログインロック期限セット（UTC算出）
					elif login_failed_count < login_lock_max_failed_count:
						# ログイン失敗時にロックフラグを解除することはないので変更（プロファイルの設定にかかわらず、ユーザ管理で直接ロックさせているケースもあるので） 2016.12.16
						#entry.login_lock_flag = ''
						pass

				# 更新日時、更新者の更新
				entry.updater_name = 'SYSTEM(LoginProcess)'	# 決め打ち...
				entry.date_changed = UcfUtil.getNow()
				entry.put()



# ログイン時の端末・環境情報を作成
def createLoginEnvInfo(helper):

	client_ip = helper.getClientIPAddress()
	logging.info('[createLoginEnvInfo]')
	access_env_info = ''
	#access_env_info += '[ipaddress]' + str(client_ip) + '[x-forwarded-for-ipaddress]' + helper.getSessionHttpHeaderXForwardedForIPAddress() + '\n'
	access_env_info += '[ipaddress]' + str(client_ip) + '\n'
	access_env_info += '[useragent]' + helper.getUserAgent() + '\n'
	for k,v in helper.request.environ.items():
		if k == 'HTTP_COOKIE' or k == 'REQUEST_METHOD' or k == 'PATH_INFO' or k == 'QUERY_STRING' or k == 'HTTP_REFERER' or k == 'HTTP_ACCEPT' or k == 'HTTP_ACCEPT_LANGUAGE' or k == 'AUTH_DOMAIN':
			access_env_info += '[' + str(k) + ']' + str(v) + '\n'
	return '---------------------------------------\n' + access_env_info if access_env_info != '' else access_env_info

# ログイン履歴に1件インサート（非同期）
def insertLoginHistoryAsync(helper, isLogin, isAuthSuccess, login_result, user_vo, is_auto_login, login_id, login_name, login_access_authority, login_email, login_password, is_set_next_auto_login):

	error_code = UcfUtil.getHashStr(login_result, 'error_code')

	# str + unicode になるとエラーするので
	#log_text = UcfUtil.getHashStr(login_result, 'log_text') + '\n' + createLoginEnvInfo(helper) if UcfUtil.getHashStr(login_result, 'log_text') != '' else createLoginEnvInfo(helper)
	str1 = UcfUtil.getHashStr(login_result, 'log_text')
	str2 = createLoginEnvInfo(helper)
	#if isinstance(str1, str):
	#	str1 = unicode(str1, 'utf-8')
	#if isinstance(str2, str):
	#	str2 = unicode(str2, 'utf-8')
	log_text = str1 + '\n' + str2

	career_type = helper._career_type
	user_agent = helper.getUserAgent()
	client_ipaddress = helper.getClientIPAddress()
	user_unique_id = UcfUtil.getHashStr(user_vo, 'unique_id') if user_vo is not None else ''
	user_operator_id = UcfUtil.getHashStr(user_vo, 'operator_id') if user_vo is not None else ''
	management_group = UcfUtil.getHashStr(user_vo, 'management_group') if user_vo is not None else ''

	try:

		# Save Number of GoogleApps domain user
		params = {
				'isLogin': isLogin,
				'isAuthSuccess': isAuthSuccess,
				'user_unique_id': user_unique_id,
				'user_operator_id': user_operator_id,
				'management_group': management_group,
				'error_code': error_code,
				'log_text': log_text,
				'career_type': career_type,
				'user_agent': user_agent,
				'client_ipaddress': client_ipaddress,
				'is_auto_login': is_auto_login,
				'login_id': login_id,
				'login_name': login_name,
				'login_access_authority': login_access_authority,
				'login_email': login_email,
				'login_password': login_password,
				'is_set_next_auto_login': is_set_next_auto_login,
		}

		token = UcfUtil.guid()
		# taskに追加 まるごと
		import_q = taskqueue.Queue('process-login')
		import_t = taskqueue.Task(
				url='/a/' + helper._tenant + '/openid/' + token + '/insert_login_history',
				params=params,
	#			target='b1process',				# BackEndsの使用リソース軽減のためFrontEndsに変更 2013.06.05
				countdown='0'
		)
		#logging.info('run task')
		import_q.add(import_t)

	# TaskToolLargeError が出ることがあるので、エラーした場合は同期処理でインサート
	# ログイン履歴取得でエラーしたからといってログインできないのも嫌なので
	except BaseException as e:
	#except taskqueue.TaskToolLargeError, e:
		logging.warning(e)
		insertLoginHistory(helper, isLogin, isAuthSuccess, error_code, log_text, career_type, user_agent, client_ipaddress, user_unique_id, user_operator_id, is_auto_login, login_id, login_name, login_access_authority, login_email, login_password, is_set_next_auto_login, management_group)


# ログイン履歴に1件インサート
def insertLoginHistory(helper, isLogin, isAuthSuccess, error_code, log_text, career_type, user_agent, client_ipaddress, user_unique_id, user_operator_id, is_auto_login, login_id, login_name, login_access_authority, login_email, login_password, is_set_next_auto_login, management_group):

	# log_text に証明書情報を追加（先頭に）
	if log_text is None:
		log_text = ''

	access_date = UcfUtil.nvl(UcfUtil.getNowLocalTime(helper._timezone))

	#############################################################
	# ログテキストの先頭に追加情報をセット（下のほうが上に来る）
	log_text = '[login_id]' + login_id + '\n' + log_text
	log_text = '[error_code]' + error_code + '\n' + log_text
	log_text = '[access_date]' + access_date + '\n' + log_text
	#############################################################

	#vo = {}
	unique_id = UcfUtil.guid()

	entry = UCFMDLLoginHistory(unique_id=unique_id,id=LoginHistoryUtils.getKey(helper, unique_id))

	entry.unique_id = unique_id
	entry.access_date = UcfUtil.getUTCTime(UcfUtil.getDateTime(access_date), helper._timezone)
	entry.dept_id = helper.getDeptInfo()['dept_id']
	entry.operator_unique_id = user_unique_id
	entry.operator_id = user_operator_id
	entry.operator_id_lower = user_operator_id.lower()
	entry.login_id = login_id
	entry.login_id_lower = login_id.lower()
	try:
		entry.login_password = helper.encryptoData(login_password, enctype='AES')		# パスワード暗号化
		entry.login_password_enctype = 'AES'
	except UnicodeEncodeError as e:
		entry.login_password = helper.encryptoData(UcfUtil.urlEncode(login_password), enctype='AES')		# パスワード暗号化（全角とかの場合はエラーしちゃうのでURLエンコードしてから暗号化）
		entry.login_password_enctype = 'AES'
	entry.login_password_length = len(login_password)

	#entry.login_type = login_auth_type
	entry.login_result = 'SUCCESS' if isLogin else 'FAILED'
	entry.log_code = error_code
	# ログテキストは詳細テーブルに逃がす 2013.10.01
	#entry.log_text = log_text
	entry.is_exist_log_detail = log_text != ''
	entry.user_agent = user_agent
	entry.session_id = ''
	entry.cookie_auth_id = ''
	entry.client_ip = client_ipaddress
	entry.target_career = career_type
	entry.management_group = management_group
	entry.is_auto_login = 'AUTO' if is_auto_login else ''

	entry.updater_name = 'SYSTEM(LoginProcess)'	# 決め打ち...
	entry.date_changed = UcfUtil.getNow()
	entry.creator_name = 'SYSTEM(LoginProcess)'	# 決め打ち...
	entry.date_created = UcfUtil.getNow()
	entry.put()

	# ログテキストは詳細テーブルに逃がす 2013.10.01
	if log_text != '':
		detail_unique_id = UcfUtil.guid()
		detail_entry = UCFMDLLoginHistoryDetail(unique_id=detail_unique_id)
		detail_entry.log_text = log_text
		detail_entry.history_unique_id = unique_id
		detail_entry.put()
	

# ログインロック期限を算出（UTCで算出）
# ログインロック機能はほしいのでとりあえず固定で設定
#def calculateLoginLockExpire(helper, login_lock_expire_info):
def calculateLoginLockExpire(helper):
	login_lock_expire_info = '15MIN'
	login_lock_expire = UcfUtil.getNow()
	if login_lock_expire_info == '15MIN':
		login_lock_expire = UcfUtil.add_minutes(login_lock_expire, 15)
	elif login_lock_expire_info == '1HOUR':
		login_lock_expire = UcfUtil.add_hours(login_lock_expire, 1)
	elif login_lock_expire_info == '3HOUR':
		login_lock_expire = UcfUtil.add_hours(login_lock_expire, 3)
	elif login_lock_expire_info == '6HOUR':
		login_lock_expire = UcfUtil.add_hours(login_lock_expire, 6)
	elif login_lock_expire_info == '12HOUR':
		login_lock_expire = UcfUtil.add_hours(login_lock_expire, 12)
	elif login_lock_expire_info == '1DAY':
		login_lock_expire = UcfUtil.add_days(login_lock_expire, 1)
	elif login_lock_expire_info == '7DAY':
		login_lock_expire = UcfUtil.add_days(login_lock_expire, 7)
	elif login_lock_expire_info == 'PERMANENCE':
		login_lock_expire = UcfUtil.getDateTime('2999/12/31')
	return login_lock_expire



#+++++++++++++++++++++++++++++++++++++++
#+++ ログイン情報をセッションにセット
#+++++++++++++++++++++++++++++++++++++++
def setLoginInfo(helper, is_set_next_auto_login, login_id, login_name, access_authority, delegate_function, delegate_management_groups, mail_address, login_password, user_vo, without_clear_cookie=False):

	# ログインＩＤをセッションにセット
	helper.setSession(UcfConfig.SESSIONKEY_LOGIN_ID, UcfUtil.getHashStr(user_vo, 'operator_id') if user_vo is not None else login_id)
	# ログインオペレータＩＤをセッションにセット
	helper.setSession(UcfConfig.SESSIONKEY_LOGIN_OPERATOR_ID, UcfUtil.getHashStr(user_vo, 'operator_id') if user_vo is not None else '')
	# ログインオペレータユニークＩＤをセッションにセット（user_voがない場合は空もあり得るので注意）
	helper.setSession(UcfConfig.SESSIONKEY_LOGIN_UNIQUE_ID, UcfUtil.getHashStr(user_vo, 'unique_id') if user_vo is not None else '')
	# ログインオペレータ名称をセッションにセット
	helper.setSession(UcfConfig.SESSIONKEY_LOGIN_NAME, login_name)
	# ログインオペレータ権限をセッションにセット
	helper.setSession(UcfConfig.SESSIONKEY_ACCESS_AUTHORITY, access_authority)
	# ログインオペレータの委託管理機能をセッションにセット
	helper.setSession(UcfConfig.SESSIONKEY_DELEGATE_FUNCTION, delegate_function)
	# ログインオペレータの委託管理する管理グループをセッションにセット
	helper.setSession(UcfConfig.SESSIONKEY_DELEGATE_MANAGEMENT_GROUPS, delegate_management_groups)
	# ログインオペレータメールアドレスをセッションにセット
	helper.setSession(UcfConfig.SESSIONKEY_LOGIN_MAIL_ADDRESS, mail_address)

	# ログインユーザにパスワード変更を強制するフラグをセッションにセット
	is_password_change_force = False
	if user_vo is not None:
		# 次回変更フラグと期限を見て決定
		if UcfUtil.getHashStr(user_vo, 'next_password_change_flag') == 'ACTIVE':
			is_password_change_force = True
		elif UcfUtil.getHashStr(user_vo, 'password_expire') != '' and UcfUtil.getNowLocalTime(helper._timezone) > UcfUtil.getDateTime(UcfUtil.getHashStr(user_vo, 'password_expire')):
			is_password_change_force = True

	if is_password_change_force:
		helper.setLoginOperatorForcePasswordChangeFlag('FORCE')
		helper.setLoginOperatorRURLKey(helper.request.get('rurl_key'))
	else:
		helper.setLoginOperatorForcePasswordChangeFlag('')

	if without_clear_cookie == False:
		# 自動ログイン対応 2009/07/28 T.ASAO
		# クッキーに自動ログインＦとログイン情報をセット
		if is_set_next_auto_login:
			setCookieLoginInfo(helper, True, UcfUtil.getHashStr(user_vo, 'operator_id') if user_vo is not None else login_id)
		# クッキーから自動ログインＦとログイン情報をクリア
		else:
			setCookieLoginInfo(helper, False, '')


#+++++++++++++++++++++++++++++++++++++++
#+++ ログイン時の各種情報を取得＆チェック
#+++++++++++++++++++++++++++++++++++++++
def checkLoginInfo(helper, not_redirect=False, not_check_target_env=False):
	is_select_ok = False
	user_vo = None
	# ログイン時のユーザユニークID
	unique_id = helper.getLoginOperatorUniqueID()
	# ユニークIDがあればユーザデータを取得
	if unique_id != '':
		user_entry = OperatorUtils.getData(helper, unique_id)
		if user_entry is None:
			if not not_redirect:
				helper.redirectError(UcfMessage.getMessage(helper.getMsg('MSG_NOT_EXIST_LOGIN_ACCOUNT_DATA')))
			return is_select_ok, user_vo, UcfMessage.getMessage(helper.getMsg('MSG_NOT_EXIST_LOGIN_ACCOUNT_DATA'))
		user_vo = user_entry.exchangeVo(helper._timezone)	
		# ユーザー単位の言語設定を反映
		if user_vo.get('language', '') != '':
			helper._language = user_vo.get('language', '')
	
	is_select_ok = True
	return is_select_ok, user_vo, ''

#+++++++++++++++++++++++++++++++++++++++
#+++ 自動ログインＦを取得
#+++++++++++++++++++++++++++++++++++++++
def isAutoLogin(helper):
	return helper.getCookie(UcfConfig.COOKIE_KEY_AUTO_LOGIN) == UcfConfig.VALUE_AUTO_LOGIN

#+++++++++++++++++++++++++++++++++++++++
#+++ クッキーログインＩＤを取得
#+++++++++++++++++++++++++++++++++++++++
def getCookieLoginID(helper):
	return helper.getCookie(UcfConfig.COOKIE_KEY_LOGIN_ID)

#+++++++++++++++++++++++++++++++++++++++
#+++ クッキーログインパスワードを取得
#+++++++++++++++++++++++++++++++++++++++
def getCookiePassword(helper):
	return helper.getCookie(UcfConfig.COOKIE_KEY_LOGIN_PASSWORD)

#+++++++++++++++++++++++++++++++++++++++
#+++ クッキーログインメールアドレスを取得
#+++++++++++++++++++++++++++++++++++++++
def getCookieMailAddress(helper):
	return helper.getCookie(UcfConfig.COOKIE_KEY_LOGIN_MAIL_ADDRESS)


#+++++++++++++++++++++++++++++++++++++++
#+++ クッキー用にログイン用データをセット
#+++++++++++++++++++++++++++++++++++++++
def setCookieLoginInfo(helper, auto_login_flag, login_id):
	# 自動ログインＦ
	#helper.setCookie(UcfConfig.COOKIE_KEY_AUTO_LOGIN, UcfConfig.VALUE_AUTO_LOGIN if auto_login_flag else '', is_secure=True)
	helper.setCookie(UcfConfig.COOKIE_KEY_AUTO_LOGIN, UcfConfig.VALUE_AUTO_LOGIN if auto_login_flag else '')

	if login_id is not None and login_id != '':
		now = UcfUtil.getNow()
		expireTime = now + datetime.timedelta(days=10000)  # 実質無期限
		payload = {
			"user": login_id,
			"iss": UcfConfig.JWT_ISSUER,
			"aud": helper._tenant,
			"exp": expireTime,
			"iat": now
		}
		token = jwt_custom.encode(payload=payload, key=UcfConfig.JWT_SIGNATURE)
		logging.info('type=%s token=%s' % (type(token), token))
		helper.setCookie(UcfConfig.COOKIE_KEY_LOGIN_TOKEN, token)
	else:
		helper.setCookie(UcfConfig.COOKIE_KEY_LOGIN_TOKEN, '')

#+++++++++++++++++++++++++++++++++++++++
#+++ クッキートークンを取得
#+++++++++++++++++++++++++++++++++++++++
def getCookieLoginToken(helper):
	token = helper.getCookie(UcfConfig.COOKIE_KEY_LOGIN_TOKEN)
	logging.info('getCookieLoginToken:token:%s' % (token))
	return token

#+++++++++++++++++++++++++++++++++++++++
#+++ クッキートークンを解析
#+++++++++++++++++++++++++++++++++++++++
def analysisLoginToken(helper, token):
	payload = None
	try:
		#　token チェック、time(iat=issue at time/exp= expire date ) issuer/ tenant validation
		payload = jwt_custom.decode(str(token), UcfConfig.JWT_SIGNATURE, aud=helper._tenant, iss=UcfConfig.JWT_ISSUER)
		status = "ok"
	except jwt_custom.InvalidTokenError as invt:
		logging.exception(invt)
		status = 'Invalid token'
	except jwt_custom.ExpiredTokenError as et:
		logging.exception(et)
		status = str(et)
	except jwt_custom.ImmatureTokenError as imt:
		logging.exception(imt)
		status = str(imt)
	except BaseException as bx:
		logging.exception(bx)
		status = 'Error associated with token has occurred.'
	logging.info('analysisLoginToken:status:%s' % (status))
	logging.info(payload)
	return status, payload

#+++++++++++++++++++++++++++++++++++++++
#+++ ログアウト
#+++++++++++++++++++++++++++++++++++++++
def logout(helper, without_clear_cookie=False):

	setLoginInfo(helper, False, '', '', '', '', '', '', '', None, without_clear_cookie=without_clear_cookie)
	helper.setSession(UcfConfig.SESSIONKEY_ALREADY_DEAL_AUTO_REDIRECT_URL, '')

	if without_clear_cookie == False:
		setCookieLoginInfo(helper, False, '')
		# 認証IDをクリア
		clearLoginAuthID(helper)

#+++++++++++++++++++++++++++++++++++++++


# ログインチェック
def checkLogin(helper, add_querys=None, isStaticLogin=False, not_redirect=False, not_check_authid=False, isRURLUseSession=False, isForceHttpMethodGet=False, add_querys_for_rurl=None):
	u'''
	TITLE:アプリ用ログインチェック（GoogleMarketPlaceのOpenID認証などではなくアプリのセッション管理ログイン認証）
	PARAMETER:
		add_querys:ログイン画面に追加するクエリーのハッシュ
		isStaticLogin:静的なログインをするならTrue
	'''

	is_exist_login_session = UcfUtil.nvl(helper.getLoginID()) != ''
	logging.info('login_id=' + UcfUtil.nvl(helper.getLoginID()))
	# セッション判定でログインしていなければ（認証IDも見るように変更）
	if not is_exist_login_session or (not_check_authid == False and checkLoginAuthID(helper) == False):

		# 自動ログインフラグがたっていればクッキーの値によってログインを試みる
		if isAutoLogin(helper):			
			login_id = ''
			login_password = ''
			is_nocheck_password = False
			login_token = getCookieLoginToken(helper)
			is_nocheck_two_factor_auth = False
			if login_token is not None and login_token != '':
				status, payload = analysisLoginToken(helper, login_token)
				if status == 'ok':
					login_id = payload.get('user', '')
					is_nocheck_password = True
					is_nocheck_two_factor_auth = True
			single_federated_domain = ''

			# ログイン認証
			isLogin, login_result = authLogin(helper, single_federated_domain, login_id, login_password, is_set_next_auto_login=True, is_auto_login=True, is_nocheck_password=is_nocheck_password, is_nocheck_two_factor_auth=is_nocheck_two_factor_auth)

		else:
			isLogin = False

		# ログインしていなければ
		if not isLogin:
			if not not_redirect:

				# RURLの取得を行うか判定用 2011/04/08
				rurl_flag = False

				# 静的ログインなら
				url = ''
				if isStaticLogin:
					url = '/a/' + helper._tenant + '/login'
					# 静的ログインの場合、RURLの追加を行わない
					rurl_flag = True
				# 動的ログインなら
				else:
					# POST なら トップページに戻るように
					if not isForceHttpMethodGet and helper._request_type == UcfConfig.REQUEST_TYPE_POST:
						url = '/a/' + helper._tenant + '/login'
					# GET ならこのページ自体に戻るように
					else:
						url = '/a/' + helper._tenant + '/login'
						rurl = helper.request.url
						if add_querys_for_rurl is not None:
							for k,v in add_querys_for_rurl.items():
								rurl = UcfUtil.appendQueryString(rurl, k, v)
						if isRURLUseSession:
							helper.setSession(UcfConfig.SESSIONKEY_RURL, rurl)
						else:
							helper.setSession(UcfConfig.SESSIONKEY_RURL, '')
							url = UcfUtil.appendQueryString(url, UcfConfig.REQUESTKEY_RURL, rurl)
						rurl_flag = True

				# クエリーを追加
				if add_querys != None:
					for k,v in add_querys.items():
						url = UcfUtil.appendQueryString(url, k, v)
						if k == UcfConfig.REQUESTKEY_RURL:
							rurl_flag = True
				# RURLを追加していない場合、追加 2011/04/08
				if not rurl_flag:
					# RURLを取得
					rurl = UcfUtil.nvl(helper.getSession(UcfConfig.SESSIONKEY_RURL))
					# RURLが空のとき、リファラから取得
					if rurl == '' and UcfUtil.nvl(UcfUtil.getHashStr(os.environ, 'HTTP_REFERER')) != '':
						 rurl = UcfUtil.nvl(UcfUtil.getHashStr(os.environ, 'HTTP_REFERER'))
					if rurl != '' and add_querys_for_rurl is not None:
						for k,v in add_querys_for_rurl.items():
							rurl = UcfUtil.appendQueryString(rurl, k, v)

					url = UcfUtil.appendQueryString(url, UcfConfig.REQUESTKEY_RURL, rurl)

				helper.redirect(url)

				return False

	else:
		isLogin = True

	return isLogin

#+++++++++++++++++++++++++++++++++++++++



#+++++++++++++++++++++++++++++++++++++++
# ログイン認証IDを新規発行
def setNewLoginAuthID(helper):
	# Cookieに認証IDをセット
	# 認証IDをセッションにもセット
	auth_id = UcfUtil.guid()
	helper.setCookie(UcfConfig.COOKIEKEY_AUTHID, auth_id, is_secure=True)
	helper.setSession(UcfConfig.SESSIONKEY_AUTHID, auth_id)

#+++++++++++++++++++++++++++++++++++++++
# ログイン認証IDをチェック
def checkLoginAuthID(helper):
	strCookieAuthID = UcfUtil.nvl(helper.getCookie(UcfConfig.COOKIEKEY_AUTHID))
	strSessionAuthID = UcfUtil.nvl(helper.getSession(UcfConfig.SESSIONKEY_AUTHID))
	logging.info('checkLoginAuthID:strCookieAuthID=%s strSessionAuthID=%s' % (strCookieAuthID, strSessionAuthID))
	return helper.isSSLPage() == False or strCookieAuthID == strSessionAuthID		# sslの時は必ずチェックとする

#+++++++++++++++++++++++++++++++++++++++
# ログイン認証IDをクリア
def clearLoginAuthID(helper):
	helper.clearCookie(UcfConfig.COOKIEKEY_AUTHID)
	helper.setSession(UcfConfig.SESSIONKEY_AUTHID, '')

