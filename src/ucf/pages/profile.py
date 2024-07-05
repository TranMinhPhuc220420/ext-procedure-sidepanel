# coding: utf-8

# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行
#import webapp2
from google.appengine.api import memcache
from ucf.utils.validates import BaseValidator
from ucf.utils.models import *
from ucf.utils.helpers import *
from ucf.pages.operator import OperatorUtils
import sateraito_inc
import sateraito_func


############################################################
## プロファイルテーブル用メソッド
############################################################
class ProfileUtils():

	# パスワードの次回有効期限を算出（ローカル時間で算出）（ユーザのパスワード変更機能で使用予定）
	def calculateNextPasswordExpire(cls, helper):
		password_expire = ''	# プロファイルが指定されていなければ無期限扱いで空を返す
		return password_expire
	calculateNextPasswordExpire = classmethod(calculateNextPasswordExpire)


	########################################
	# ユーザーのパスワード変更
	########################################
	def changeUserPassword(cls, helper, req, user_vo, updater_name='', with_reminder_key_reset=False):

		is_update_password = True

		new_password = UcfUtil.getHashStr(req, 'Password1')
		new_password_enctype = 'AES'
		enc_new_password = helper.encryptoData(new_password, enctype=new_password_enctype)		# 暗号化したパスワードを作成しておく

		# 改めてユーザデータを取得
		if user_vo is not None:
			entry = OperatorUtils.getData(helper, UcfUtil.getHashStr(user_vo, 'unique_id'))
			if entry is None:
				helper.redirectError(UcfMessage.getMessage(helper.getMsg('MSG_NOT_EXIST_LOGIN_ACCOUNT_DATA')))
				return False, 'NOT_EXIST_LOGIN_ACCOUNT_DATA'
			user_vo = entry.exchangeVo(helper._timezone)										# user_vo差し替え

			# パスワード履歴に1件追加
			OperatorUtils.appendPasswordHistory(helper, user_vo, new_password)
			# パスワード変更日時を更新
			if is_update_password:
				OperatorUtils.updatePasswordChangeDate(helper, user_vo)
			# パスワード変更日時を更新（こちらはAppsパスワードなどでも更新）
			OperatorUtils.updateUserPasswordChangeDate(helper, user_vo)

			# パスワード有効期限算出＆設定
			user_vo['password_expire'] = UcfUtil.nvl(ProfileUtils.calculateNextPasswordExpire(helper))
			# パスワード次回更新フラグを下ろす
			user_vo['next_password_change_flag'] = ''

		# パスワード更新
		if is_update_password and user_vo is not None:
			user_vo['password'] = enc_new_password		# 暗号化パスワードをセット
			user_vo['password_enctype'] = new_password_enctype
			if with_reminder_key_reset:
				user_vo['password_reminder_key'] = ''

		if user_vo is not None:
			# Voからモデルにマージ
			entry.margeFromVo(user_vo, helper._timezone)

			# 更新日時、更新者の更新
			entry.updater_name = updater_name
			entry.date_changed = UcfUtil.getNow()
			# 更新処理
			entry.put()

		return True, ''

	changeUserPassword = classmethod(changeUserPassword)



############################################################
## パスワード変更用バリデーションチェッククラス 
############################################################
class PasswordChangeValidator(BaseValidator):

	_vc_error_code = ''
	_vc_error_sub_info = ''

	def validate(self, helper, vo, user_vo):

		# 初期化
		self.init()

		check_name = ''
		check_key = ''
		check_value = ''
			

		########################
		check_name = helper.getMsg('VMSG_INPUT_PASSWORD_CHANGE')
		check_key = 'Password1'
		check_value = UcfUtil.getHashStr(vo, check_key)
		# 必須チェック
		if not self.needValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
			self._vc_error_code = 'VC_NEED'
			self._vc_error_sub_info = ''
		# 半角チェック
		if not self.hankakuValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_HANKAKU'), (check_name)))
			self._vc_error_code = 'VC_HANKAKU'
			self._vc_error_sub_info = ''
		# 半角スペースもはじく 2017.01.23
		if check_value.find(' ') >= 0:
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_INVALID_SPACE'), (check_name)))
			self._vc_error_code = 'VC_INVALID_SPACE'
			self._vc_error_sub_info = ''
		# バックスラッシュとして「a5」が使われている場合ははじく（Appsパスワードとして使えないので）
		if check_value.find(u'\xa5') >= 0:
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_INVALID_BACKSLASH_A5'), (check_name)))
			self._vc_error_code = 'VC_BACKSLASH_A5'
			self._vc_error_sub_info = ''
		# 最大長チェック：100文字（Appsに合わせて）
		if not self.maxLengthValidator(check_value, 100):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAXLENGTH'), (check_name, 100)))
			self._vc_error_code = 'VC_STRENGTH_MAXLENGTH'
			self._vc_error_sub_info = '100'
		# 最小長チェック：8文字（Appsに合わせて）
		is_already_check_min_length = False
#		if not self.minLengthValidator(check_value, 8):
#			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MINLENGTH'), (check_name, 8)))
#			is_already_check_min_length = True

		########################
		# パスワード（確認用）
		check_name = helper.getMsg('VMSG_CONFIRM_PASSWORD_CHANGE')
		check_key = 'PasswordConfirm'
		check_value = UcfUtil.getHashStr(vo, check_key)
		# 必須チェック
		if not self.needValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
			self._vc_error_code = 'VC_NEED'
			self._vc_error_sub_info = ''
		# 「パスワード」との一致チェック
		if UcfUtil.getHashStr(vo, 'Password1') != check_value:
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NOT_MATCH_CONFIRM_PASSWORD'), ()))
			self._vc_error_code = 'VC_NOT_MATCH_CONFIRM_PASSWORD'
			self._vc_error_sub_info = ''

