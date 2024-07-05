# coding: utf-8

# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
#from ucf.utils.models import *
from ucf.utils.ucfutil import *
from ucf.utils.mailutil import UcfMailUtil
from ucf.utils.ucfxml import UcfXml
from ucf.utils.numbering import *
from ucf.config.ucfconfig import *
import sateraito_inc
import sateraito_func
import oem_func
from google.appengine.api import memcache
from ucf.pages.dept import DeptUtils

# UCFMDLDeptMasterに1件登録（存在しない場合だけ）
def registDeptMaster(helper, tenant, company_name, tanto_name, contact_mail_address, contact_tel_no, oem_company_code, sp_code, default_language='', default_timezone='', default_encoding=''):
	tenant = tenant.lower()
	query_dept = UCFMDLDeptMaster.gql("where tenant = :1", tenant)
	dept_entry = query_dept.get()
	dept_vo = None
	if dept_entry is None:
		numbers = Numbering(_dept_id=UcfConfig.NUMBERING_NUMBER_ID_DEPT ,_number_id=UcfConfig.NUMBERING_NUMBER_ID_DEPT, _number_sub_id=UcfConfig.NUMBERING_NUMBER_SUB_ID_DEPT, _prefix=UcfConfig.NUMBERING_PREFIX_DEPT, _sequence_no_digit=UcfConfig.NUMBERING_SEQUENCE_NO_DIGIT_DEPT)
		number = numbers.countup()

		unique_id = UcfUtil.guid()
		dept_vo = {}
		DeptUtils.editVoForDefault(helper, dept_vo)
		dept_vo['tenant'] = tenant
		dept_vo['unique_id'] = unique_id
		dept_vo['dept_id'] = number
		dept_vo['md5_suffix_key'] = UcfUtil.guid()
		dept_vo['deptinfo_encode_key'] = UcfUtil.guid()[0:8]

		dept_vo['tenant'] = tenant
		dept_vo['company_name'] = company_name
		dept_vo['tanto_name'] = tanto_name
		dept_vo['contact_mail_address'] = contact_mail_address
		dept_vo['contact_tel_no'] = contact_tel_no

		#dept_vo['is_disable_fp'] = UcfUtil.nvl(True)		# 海外展開対応：ガラ携帯設定を無効に 2015.07.09
		dept_vo['is_disp_login_language_combobox'] = 'ACTIVE'		# ログイン画面の言語選択ボックスのデフォルトをONに 2015.07.10

		dept_vo['language'] = default_language
		dept_vo['file_encoding'] = default_encoding
		dept_vo['timezone'] = default_timezone
		#dept_vo['username_disp_type'] = '' if default_language == 'ja' else 'ENGLISH'
		dept_vo['login_message'] = helper.getMsg('EXPLAIN_LOGINPAGE_DEFAULT', ())
		dept_vo['oem_company_code'] = oem_company_code.lower()
		if sp_code is not None and sp_code != '':
			dept_vo['sp_codes'] = sp_code.lower()

		new_dept_entry = UCFMDLDeptMaster(unique_id=unique_id,key_name=DeptUtils.getKey(helper, dept_vo))
		new_dept_entry.margeFromVo(dept_vo, helper._timezone)
		new_dept_entry.chatgpt_available_functions = ['GPTAPP']
		new_dept_entry.creator_name = 'SYSTEM'
		new_dept_entry.updater_name = 'SYSTEM'
		new_dept_entry.put()

	else:
		_editDeptMaster(dept_entry)
		dept_vo = dept_entry.exchangeVo(helper._timezone)
	return dept_vo

def getDeptVo(helper):
	dept = None
	query_dept = UCFMDLDeptMaster.all(keys_only=True)
	# query_dept.filter('tenant = ', tenant.lower())
	dept_entry = UCFMDLDeptMaster.getByKey(query_dept.get())
	if dept_entry is not None:
		# if dept_entry.sp_codes is None:
		# 	dept_entry.sp_codes = []
		# if dept_entry.oem_company_code is None:
		# 	dept_entry.oem_company_code = ''
		_editDeptMaster(dept_entry)
		dept = dept_entry.exchangeVo(helper._timezone)
	return dept

## 有効なドメインかどうか
#def isValidDomain(helper, domain, is_with_cache=False):
#	validdomainlist = sateraito_func.getFederatedDomainList(helper._tenant, is_with_cache)
#	return domain.lower() in validdomainlist

def _editDeptMaster(dept_entry):
	is_put = False
	#if dept_entry.hide_access_apply_link_flag is None:
	#	dept_entry.hide_access_apply_link_flag = ''
	#	is_put = True
	if is_put:
		dept_entry.put()


def getUserNameDisp(helper, dept, last_name, first_name, middle_name=''):
	disp_name = ''
	username_disp_type = UcfUtil.getHashStr(dept, 'username_disp_type')
	# 名、姓の順
	if username_disp_type == 'ENGLISH':
		disp_name = first_name + ' ' + last_name
	# デフォルト：姓、名の順
	else:
		disp_name = last_name + ' ' + first_name
	return disp_name

# ログレコード作成：通常
def createLogRecord(helper, log_message):
	logging.info(log_message)
	return '[' + UcfUtil.nvl(UcfUtil.getNowLocalTime(helper._timezone)) + ']' + log_message + '\n'

# ログレコード作成：エラー
def createErrorLogRecord(helper, log_message, code, data_key):
	logging.info(log_message)
	return '[' + UcfUtil.nvl(UcfUtil.getNowLocalTime(helper._timezone)) + ']' + '[ERROR' + (':' if code != '' else '') + code + ']' + (('[' + data_key + ']') if data_key != '' else '') + log_message + '\n'

# ログレコード作成：警告
def createWarningLogRecord(helper, log_message, code, data_key):
	logging.info(log_message)
	return '[' + UcfUtil.nvl(UcfUtil.getNowLocalTime(helper._timezone)) + ']' + '[WARNING' + (':' if code != '' else '') + code + ']' + (('[' + data_key + ']') if data_key != '' else '') + log_message + '\n'


# 管理対象のデータかどうか
def isDelegateTargetManagementGroup(data_management_group, user_delegate_management_groups):
	if user_delegate_management_groups is None or len(user_delegate_management_groups) <= 0:
		# 「委託管理する管理グループ」が空の委託管理者は委託管理機能の全データにアクセス可能とする 2013.04.22
		return True
	if data_management_group is None or data_management_group == '':
		return False
	return data_management_group in user_delegate_management_groups

# 委任管理者かどうか
# login_operator_entry…オペレータEntitiy
def isDelegateOperator(login_operator_entry):
	return login_operator_entry is not None and UcfConfig.ACCESS_AUTHORITY_OPERATOR in login_operator_entry.access_authority

# 現在有効な二要素認証コードを取得
def getActiveTwoFactorAuthEntry(user_vo):
	if user_vo is not None:
		q = UCFMDLTwoFactorAuth.all()
		q.filter('operator_unique_id =', UcfUtil.getHashStr(user_vo, 'unique_id'))
		entry = q.get()
		# レコードがあって有効期限が切れていたら削除
		if entry is not None and entry.auth_code_expire < UcfUtil.getNow():
			entry.delete()
			entry = None
		return entry
	else:
		return None

# 指定ユーザの二要素認証コードをクリア（１ユーザ1レコード前提なので、該当ユーザのものを全て消せばOK）
def clearActiveTwoFactorAuthEntry(user_unique_id):
	if user_unique_id is not None and user_unique_id != '':
		q = UCFMDLTwoFactorAuth.all()
		q.filter('operator_unique_id =', user_unique_id)
		for entry in q:
			entry.delete()

# 二要素認証コードを必要に応じて発行＆メール送信（二要素認証が必要な場合で、セッションに認証コードがセットされていない場合は、メールも送られていないと判断して送信）
def publishAndSendTwoFactorAuthCode(helper, user_vo):

	expire_minutes = 10	# 認証コードの有効期限は10分
	# 現在有効な二要素認証コードを取得
	entry = getActiveTwoFactorAuthEntry(user_vo)

	if entry is not None:
		logging.info(str(entry.two_factor_auth_code) + ':' + str(entry.auth_code_expire))

	# 未発行なら発行＆メール送信
	if entry is None:
		two_factor_auth_code = createNewTwoFactorAuthCode()
		unique_id = UcfUtil.guid()
		key = UcfUtil.getHashStr(user_vo, 'unique_id') + UcfConfig.KEY_PREFIX + unique_id
		entry = UCFMDLTwoFactorAuth(unique_id=unique_id, key_name=key)
		entry.operator_unique_id = UcfUtil.getHashStr(user_vo, 'unique_id')
		entry.date_created = UcfUtil.getNow()
		entry.dept_id = UcfUtil.getHashStr(user_vo, 'dept_id')
		entry.two_factor_auth_code = two_factor_auth_code
		entry.auth_code_expire = UcfUtil.add_minutes(UcfUtil.getNow(), expire_minutes)
		entry.date_changed = UcfUtil.getNow()
#	else:
#		two_factor_auth_code = createNewTwoFactorAuthCode()
#		entry.two_factor_auth_code = two_factor_auth_code
#		entry.auth_code_expire = UcfUtil.add_minutes(UcfUtil.getNow(), expire_minutes)
#		entry.date_changed = UcfUtil.getNow()

		# 更新処理
		entry.put()
		# 二要素認証コードの通知メール送信
		sendTwoFactorAuthCodeNotificationMail(helper, user_vo, two_factor_auth_code, expire_minutes)

	logging.info(UcfUtil.getHashStr(user_vo, 'mail_address') + ':' + UcfUtil.getHashStr(user_vo, 'sub_mail_address') + ':' + str(entry.two_factor_auth_code))

# 二要素認証の認証コードをチェック
def isValidTwoFactorAuthCode(helper, two_factor_auth_code, user_vo):
	is_valid = False
	entry = getActiveTwoFactorAuthEntry(user_vo)
	if entry is not None and str(entry.two_factor_auth_code) == two_factor_auth_code:
		is_valid = True
	return is_valid

# 二要素認証コードを新規発行
def createNewTwoFactorAuthCode():
	s = '1234567890'
	token = ''
	for j in range(6):
		token += random.choice(s)
	return token

# 二要素認証の認証コードをメールでご案内
def sendTwoFactorAuthCodeNotificationMail(helper, user_vo, current_two_factor_auth_code, expire_minutes):

	# メール文書情報取得
	oem_company_code = oem_func.getValidOEMCompanyCode(helper.getDeptValue('oem_company_code'))
	mail_template_id = 'two_factor_auth_code_notification'

	if mail_template_id != '' and UcfUtil.getHashStr(user_vo, 'sub_mail_address') != '':

		#mail_info = UcfMailUtil.getMailTemplateInfo(helper, mail_template_id)
		mail_info = UcfMailUtil.getMailTemplateInfoByLanguageDef(helper, mail_template_id)

		# 差出人をセット
		mail_info['Sender'] = sateraito_inc.SENDER_EMAIL

		# 宛先を追加
		mail_info['To'] = UcfUtil.getHashStr(user_vo, 'sub_mail_address')
		mail_info['To'] = UcfUtil.getHashStr(mail_info, 'To').strip(',')
		mail_info['Cc'] = UcfUtil.getHashStr(mail_info, 'Cc').strip(',')
		mail_info['Bcc'] = UcfUtil.getHashStr(mail_info, 'Bcc').strip(',')

		# Reply-Toに管理者の連絡先アドレスを追加
		mail_info['ReplyTo'] = UcfUtil.getHashStr(mail_info, 'ReplyTo').strip(',') + ',' + helper.getDeptValue('contact_mail_address')
		mail_info['ReplyTo'] = mail_info['ReplyTo'].strip(',')

		if UcfUtil.getHashStr(mail_info, 'To') != '' or UcfUtil.getHashStr(mail_info, 'Cc') != '' or UcfUtil.getHashStr(mail_info, 'Bcc') != '':
			# 差し込み情報作成
			insert_vo = {}
			now = UcfUtil.getNowLocalTime(helper._timezone)
			insert_vo['DATETIME'] = UcfUtil.nvl(now)
			insert_vo['DATE'] = now.strftime('%Y/%m/%d')
			insert_vo['TIME'] = now.strftime('%H:%M:%S')
			insert_vo['USER_NAME'] = helper.getUserNameDisp(UcfUtil.getHashStr(user_vo, 'last_name'), UcfUtil.getHashStr(user_vo, 'first_name'))
			insert_vo['MAIL_ADDRESS'] = UcfUtil.getHashStr(user_vo, 'operator_id')
			insert_vo['SUB_MAIL_ADDRESS'] = UcfUtil.getHashStr(user_vo, 'sub_mail_address')
			insert_vo['TWO_FACTOR_AUTH_CODE'] = current_two_factor_auth_code
			insert_vo['TWO_FACTOR_AUTH_CODE_EXPIRE_MINUTS'] = str(expire_minutes)

			#メール送信
			try:
				UcfMailUtil.sendOneMail(to=UcfUtil.getHashStr(mail_info, 'To'), cc=UcfUtil.getHashStr(mail_info, 'Cc'), bcc=UcfUtil.getHashStr(mail_info, 'Bcc'), reply_to=UcfUtil.getHashStr(mail_info, 'ReplyTo'), sender=UcfUtil.getHashStr(mail_info, 'Sender'), subject=UcfUtil.getHashStr(mail_info, 'Subject'), body=UcfUtil.getHashStr(mail_info, 'Body'), body_html=UcfUtil.getHashStr(mail_info, 'BodyHtml'), data=insert_vo)
			#ログだけ、エラーにしない
			except BaseException as e:
				helper.outputErrorLog(e)

