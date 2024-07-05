# coding: utf-8

#import logging
import sateraito_logger as logging
from ucf.utils.validates import BaseValidator
from ucf.utils.helpers import *
from ucf.utils.models import *
import sateraito_inc
import sateraito_func


############################################################
## 企業テーブル用メソッド
############################################################
class DeptUtils():

	# 初期値用：データ加工
	def editVoForDefault(cls, helper, dept_vo):
		dept_vo['active_flag'] = 'ACTIVE'
		dept_vo['login_message'] = helper.getMsg('EXPLAIN_LOGINPAGE_DEFAULT', ())
		dept_vo['login_autocomplete_type'] = ''
		#dept_vo['login_type'] = 'OPE'	# 初期はSSOパスワード認証
		dept_vo['language'] = sateraito_inc.DEFAULT_LANGUAGE
		dept_vo['timezone'] = sateraito_inc.DEFAULT_TIMEZONE
		dept_vo['file_encoding'] = sateraito_inc.DEFAULT_ENCODING
	editVoForDefault = classmethod(editVoForDefault)

	# 取得用：データ加工
	def editVoForSelect(cls, helper, vo):
		# 中国語を[zh-cn]中国語（簡体字）と[zh-tw]中国語（繁体字）に分けたので加工 2015.05.20
		vo['language'] = sateraito_func.exchangeLanguageCode(UcfUtil.getHashStr(vo, 'language'))
		# タイムゾーンの値を「+9」などから「Asia/Tokyo」などに変更したので加工 2015.07.08
		vo['timezone'] = sateraito_func.exchangeTimeZoneCode(UcfUtil.getHashStr(vo, 'timezone'))
	editVoForSelect = classmethod(editVoForSelect)

	# 更新用：データ加工
	def editVoForRegist(cls, helper, vo, entry_vo, edit_type):
		## X-Forwarded-For ホワイトリストを整備
		#xforwardedfor_whitelist = UcfUtil.csvToList(vo['xforwardedfor_whitelist'])
		## 改行とかスペースとかカット
		#for i in range(len(xforwardedfor_whitelist)):
		#	xforwardedfor_whitelist[i] = xforwardedfor_whitelist[i].replace('\n','').replace('\r','').replace('\t','').replace(' ','')
		#	if xforwardedfor_whitelist[i] == '':
		#		xforwardedfor_whitelist.remove(i)
		#vo['xforwardedfor_whitelist'] = UcfUtil.listToCsv(xforwardedfor_whitelist)
		pass
	editVoForRegist = classmethod(editVoForRegist)

	# キーに使用する値を取得
	def getKey(cls, helper, vo):
		return UcfUtil.getHashStr(vo, 'tenant') + UcfConfig.KEY_PREFIX + UcfUtil.getHashStr(vo, 'unique_id')
	getKey = classmethod(getKey)

	def getDeptEntryByUniqueID(cls, helper, unique_id):
		query_dept = UCFMDLDeptMaster.gql("where unique_id = :1", unique_id)
		dept_entry = query_dept.get()
		return dept_entry
	getDeptEntryByUniqueID = classmethod(getDeptEntryByUniqueID)


############################################################
## バリデーションチェッククラス 
############################################################
class DeptValidator(BaseValidator):

	def validate(self, helper, vo):

		check_name = ''
		check_key = ''
		check_value = ''

		####################################
		# 連絡先メールアドレス
		check_name = helper.getMsg('VMSG_CONTACT_MAILADDRESS')
		check_key = 'contact_mail_address'
		check_value = UcfUtil.getHashStr(vo, check_key)
		# メールアドレス形式チェック
		if not self.mailAddressValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAILADDRESS'), (check_name)))
		
		####################################
		# 言語
		check_name = helper.getMsg('VMSG_LANGUAGE')
		check_key = 'language'
		check_value = UcfUtil.getHashStr(vo, check_key)
		# 必須チェック
		if not self.needValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
		# パターンチェック
		if not self.listPatternValidator(check_value, sateraito_func.ACTIVE_LANGUAGES):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MATCHING'), (check_name, UcfUtil.listToCsv(sateraito_func.ACTIVE_LANGUAGES))))

		####################################
		# タイムゾーン
		check_name = helper.getMsg('VMSG_TIMEZONE')
		check_key = 'timezone'
		check_value = UcfUtil.getHashStr(vo, check_key)
		# 必須チェック
		if not self.needValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
		# パターンチェック
		#if not self.listPatternValidator(check_value, ['-12','-11','-10','-9','-8','-7','-6','-5','-4','-3','-2','-1','0','+1','+2','+3','+4','+5','+6','+7','+8','+9','+10','+11','+12','+13','+14']):
		#	self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MATCHING'), (check_name,'-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1,0,+1,+2,+3,+4,+5,+6,+7,+8,+9,+10,+11,+12,+13,+14')))
		if not self.listPatternValidator(check_value, sateraito_func.ACTIVE_TIMEZONES):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MATCHING'), (check_name, UcfUtil.listToCsv(sateraito_func.ACTIVE_TIMEZONES))))

		####################################
		# ファイルエンコード
		check_name = helper.getMsg('VMSG_FILEENCODING')
		check_key = 'file_encoding'
		check_value = UcfUtil.getHashStr(vo, check_key)
		# 必須チェック
		if not self.needValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
		# パターンチェック
		if not self.listPatternValidator(check_value, ['SJIS','EUC','UTF8']):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MATCHING'), (check_name,'SJIS,EUC,UTF8')))

		#####################################
		## X-Forwarded-For ホワイトリスト
		#xforwardedfor_whitelist = UcfUtil.getHashStr(vo, 'xforwardedfor_whitelist')
		#if xforwardedfor_whitelist != '':
		#	list_ip = xforwardedfor_whitelist.split(',')
		#	if self.ipAddressValidator(list_ip) == False:
		#		self.appendValidate('xforwardedfor_whitelist', UcfMessage.getMessage(helper.getMsg('MSG_VC_IPADDRESS_CIDR_LIST'), (helper.getMsg('FLD_ACSCTRL_XFORWARDEDFOR_WHITELIST'))))


	def validate_for_chatgptconfig(self, helper, vo, is_trial):

		check_name = ''
		check_key = ''
		check_value = ''

		####################################
		# APIキー
		check_name = helper.getMsg('CHATGPT_APIKEY')
		check_key = 'chatgpt_api_key'
		check_value = UcfUtil.getHashStr(vo, check_key)
		# 当面は必須ではなくてOKとする
		## 必須チェック
		#if helper._tenant != sateraito_inc.TENANT_ID_FOR_PERSONALUSER and not is_trial and not self.needValidator(check_value):
		#	self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
		
		####################################
		# 利用可能ドメイン、ユーザー
		check_name = helper.getMsg('AVAILABLE_DOMAINS_OR_USERS')
		check_key = 'available_domains_or_users'
		check_value = UcfUtil.getHashStr(vo, check_key)
		# 必須チェック
		if helper._tenant != sateraito_inc.TENANT_ID_FOR_PERSONALUSER and not self.needValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
