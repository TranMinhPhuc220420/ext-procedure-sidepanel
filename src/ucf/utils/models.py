# coding: utf-8

import os,sys,datetime,logging,json
import string

from google.appengine.ext import db
from google.appengine.ext import ndb
# GAEGEN2対応:検索API移行
from google.appengine.api import search
# from search_alt import search_auto
# from search_alt import search_replace as search
from google.appengine.api import namespace_manager
from google.appengine.api import memcache
from ucf.config.ucfconfig import *
from ucf.utils.ucfutil import *

import sateraito_inc
import sateraito_func

REGISTER_TOKEN_EXPIRE_SECONDS = 12 * 60 * 60
REGISTER_TOKEN_LENGTH = 64

############################################################
## モデルクラス群（モデルごとにファイル分けたほうがいいかな？import面倒？）
############################################################

############################################################
## モデル：親クラス
############################################################
class UCFModel(db.Model):

	@classmethod
	def getByKey(cls, key):
		entity = None
		if key is not None:
			if key.name() is not None:
				entity = cls.get_by_key_name(key.name())
			elif key.id() is not None:
				entity = cls.get_by_id(key.id())
		return entity

	def exchangeVo(self, timezone):
		u''' db.ModelデータをVoデータ(ハッシュ)に変換 '''
		vo = {}
		for prop in self.properties().values():
			if prop.get_value_for_datastore(self) != None:
				# リスト型
				if prop.name in self.getListTypes():
					#GAEGEN2対応
					#vo[prop.name] = unicode(UcfUtil.listToCsv(prop.get_value_for_datastore(self)))
					vo[prop.name] = UcfUtil.listToCsv(prop.get_value_for_datastore(self))
				# 日付型
				elif prop.name in self.getDateTimeTypes():
					#GAEGEN2対応
					#vo[prop.name] = unicode(prop.get_value_for_datastore(self))
					vo[prop.name] = prop.get_value_for_datastore(self)
					# LocalTime対応（標準時刻からローカル時間に戻して表示に適切な形式に変換）
					vo[prop.name] = UcfUtil.nvl(UcfUtil.getLocalTime(UcfUtil.getDateTime(vo[prop.name]), timezone))
				else:
					#GAEGEN2対応
					#vo[prop.name] = unicode(prop.get_value_for_datastore(self))
					vo[prop.name] = prop.get_value_for_datastore(self)
			else:
				vo[prop.name] = ''
		return vo

	def margeFromVo(self, vo, timezone):
		u''' db.ModelデータにVoデータ(ハッシュ)をマージ '''
		for prop in self.properties().values():
			if prop.name not in ('unique_id', 'date_created', 'date_changed'):
				if prop.name in vo:
					try:
						# 数値型
						if prop.name in self.getNumberTypes():
							prop.__set__(self, prop.make_value_from_datastore(int(vo[prop.name]) if vo[prop.name] != '' else 0))
						# Bool型
						elif prop.name in self.getBooleanTypes():
							prop.__set__(self, prop.make_value_from_datastore(True if vo[prop.name] == 'True' else False))
						# 日付型
						elif prop.name in self.getDateTimeTypes():
							if UcfUtil.nvl(vo[prop.name]) != '':
	#							prop.__set__(self, prop.make_value_from_datastore(UcfUtil.getDateTime(vo[prop.name])))
								prop.__set__(self, prop.make_value_from_datastore(UcfUtil.getUTCTime(UcfUtil.getDateTime(vo[prop.name]), timezone)))
							else:
								prop.__set__(self, prop.make_value_from_datastore(None))
						# リスト型
						elif prop.name in self.getListTypes():
							prop.__set__(self, UcfUtil.csvToList(vo[prop.name]))
						# Blob型
						elif prop.name in self.getBlobTypes():
							#prop.__set__(self, vo[prop.name])
							pass
						# References型
						elif prop.name in self.getReferencesTypes():
							pass
						else:
							#prop.__set__(self, prop.make_value_from_datastore(unicode(vo[prop.name])))
							prop.__set__(self, prop.make_value_from_datastore(vo[prop.name]))
					except BaseException as e:
						raise Exception('[' + prop.name + '=' + vo[prop.name] + ']'+ str(e))

	def getReferenceData(self):
		u''' 参照データの情報をUcfDataリストとして返す（抽象メソッド） '''
		#TODO 自動判別したい
		return []

	def getNumberTypes():
		u''' 数値型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
		#TODO 自動判別したい
		return []
	getNumberTypes = staticmethod(getNumberTypes)

	def getBooleanTypes():
		u''' Bool型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
		#TODO 自動判別したい
		return []
	getBooleanTypes = staticmethod(getBooleanTypes)

	def getListTypes():
		u''' リスト型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
		#TODO 自動判別したい
		return []
	getListTypes = staticmethod(getListTypes)

	def getDateTimeTypes():
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
		#TODO 自動判別したい
		return []
	getDateTimeTypes = staticmethod(getDateTimeTypes)

	def getBlobTypes():
		u''' Blobフィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
		#TODO 自動判別したい
		return []
	getBlobTypes = staticmethod(getBlobTypes)

	def getReferencesTypes():
		u''' 参照型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
		#TODO 自動判別したい
		return []
	getReferencesTypes = staticmethod(getReferencesTypes)


############################################################
## モデル：親クラス
############################################################
class UCFModel2(ndb.Model):

	NDB_MEMCACHE_TIMEOUT = (60 * 60 * 24 * 2)

	@classmethod
	def getByKey(cls, key):
		entity = None
		if key is not None:
			entity = key.get()
		return entity

	def exchangeVo(self, timezone):
		u''' ndb.ModelデータをVoデータ(ハッシュ)に変換 '''
		vo = self.to_dict()
		logging.debug(vo)
		for k, v in vo.items():
			if v is not None:
				# リスト型
				if k in self.getListTypes():
					#vo[k] = unicode(UcfUtil.listToCsv(v))
					vo[k] = UcfUtil.listToCsv(v)
				# 日付型
				elif k in self.getDateTimeTypes():
					# LocalTime対応（標準時刻からローカル時間に戻して表示に適切な形式に変換）
					vo[k] = UcfUtil.nvl(UcfUtil.getLocalTime(UcfUtil.getDateTime(v), timezone))
				else:
					# GAEGEN2対応
					#vo[k] = v
					vo[k] = v.decode() if isinstance(v, bytes) else v
			else:
				vo[k] = ''
		return vo

	def margeFromVo(self, vo, timezone):
		u''' ndb.ModelデータにVoデータ(ハッシュ)をマージ '''
		for prop in self._properties.values():
			# GAEGEN2対応
			#prop_name = prop._name
			prop_name = prop._name.decode()
			if prop_name not in ['unique_id', 'date_created', 'date_changed']:
				if prop_name in vo:
					try:
						# 数値型
						if isinstance(prop, ndb.IntegerProperty):
							# GAEGEN2対応:ついでにsetattrに変更
							#prop.__set__(self, int(vo[prop_name]) if vo[prop_name] != '' else 0)
							setattr(self, prop_name, int(vo[prop_name]) if vo[prop_name] != '' else 0)
						# 小数型
						elif isinstance(prop, ndb.FloatProperty):
							# GAEGEN2対応:ついでにsetattrに変更
							#prop.__set__(self, float(vo[prop_name]) if vo[prop_name] != '' else 0)
							setattr(self, prop_name, float(vo[prop_name]) if vo[prop_name] != '' else 0)
						# Bool型
						elif isinstance(prop, ndb.BooleanProperty):
							# GAEGEN2対応:ついでにsetattrに変更
							#prop.__set__(self, True if vo[prop_name] == 'True' else False)
							setattr(self, prop_name, True if vo[prop_name] == 'True' else False)
						# 日付型
						elif isinstance(prop, ndb.DateTimeProperty):
							if UcfUtil.nvl(vo[prop_name]) != '':
								# GAEGEN2対応:ついでにsetattrに変更
								#prop.__set__(self, UcfUtil.getUTCTime(UcfUtil.getDateTime(vo[prop_name]), timezone))
								setattr(self, prop_name, UcfUtil.getUTCTime(UcfUtil.getDateTime(vo[prop_name]), timezone))
							else:
								# GAEGEN2対応:ついでにsetattrに変更
								#prop.__set__(self, None)
								setattr(self, prop_name, None)
						# リスト型（String）
						elif isinstance(prop, ndb.StringProperty) and prop._repeated:
							# GAEGEN2対応:ついでにsetattrに変更
							#prop.__set__(self, UcfUtil.csvToList(vo[prop_name]))
							setattr(self, prop_name, UcfUtil.csvToList(vo[prop_name]))
						# String型
						elif isinstance(prop, ndb.StringProperty):
							# GAEGEN2対応:ついでにsetattrに変更
							#prop.__set__(self, unicode(vo[prop_name]))
							setattr(self, prop_name, vo[prop_name])
						# Text型
						elif isinstance(prop, ndb.TextProperty):
							# GAEGEN2対応:ついでにsetattrに変更
							#prop.__set__(self, unicode(vo[prop_name]))
							setattr(self, prop_name, vo[prop_name])
						# Blob型
						elif isinstance(prop, ndb.BlobProperty):
							#prop.__set__(self, vo[prop_name])
							pass
						## References型
						#elif prop_name in self.getReferencesTypes():
						#	pass
						else:
							#prop.__set__(self, unicode(vo[prop_name]))
							prop.__set__(self, vo[prop_name])
					except BaseException as e:
						raise Exception('[' + prop_name + '=' + vo[prop_name] + ']'+ str(e))

	def getReferenceData(self):
		u''' 参照データの情報をUcfDataリストとして返す（抽象メソッド） '''
		#TODO 自動判別したい
		return []

	def getNumberTypes():
		u''' 数値型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
		#TODO 自動判別したい
		return []
	getNumberTypes = staticmethod(getNumberTypes)

	def getBooleanTypes():
		u''' Bool型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
		#TODO 自動判別したい
		return []
	getBooleanTypes = staticmethod(getBooleanTypes)

	def getListTypes():
		u''' リスト型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
		#TODO 自動判別したい
		return []
	getListTypes = staticmethod(getListTypes)

	def getDateTimeTypes():
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
		#TODO 自動判別したい
		return []
	getDateTimeTypes = staticmethod(getDateTimeTypes)

	def getBlobTypes():
		u''' Blobフィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
		#TODO 自動判別したい
		return []
	getBlobTypes = staticmethod(getBlobTypes)

	def getReferencesTypes():
		u''' 参照型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
		#TODO 自動判別したい
		return []
	getReferencesTypes = staticmethod(getReferencesTypes)



############################################################
## モデル：ユーザ
############################################################
class UCFMDLOperator(UCFModel2):
	u'''オペレータマスタをイメージしたモデル'''

	unique_id = ndb.StringProperty(required=True)
	comment = ndb.TextProperty()
	dept_id = ndb.StringProperty(indexed=False)
	#federated_domain = ndb.StringProperty()					# 小文字
	operator_id = ndb.StringProperty()								# ユーザメールアドレス
	operator_id_lower = ndb.StringProperty()					# ユーザメールアドレス（小文字）
	password = ndb.StringProperty(indexed=False)
	password_enctype = ndb.StringProperty()					# 「password」の暗号化対応（AES,DES デフォルト=DES）
	#employee_id = ndb.StringProperty()
	#employee_id_lower = ndb.StringProperty()				# 小文字のみ
	#password1 = ndb.StringProperty(indexed=False)
	#password1_enctype = ndb.StringProperty()					# 「password1」の暗号化対応（AES,DES デフォルト=DES）
	mail_address = ndb.StringProperty()
	sub_mail_address = ndb.StringProperty()					# 	予備のメールアドレス（パスワードリマインダ等で使用）
	last_name = ndb.StringProperty()
	first_name = ndb.StringProperty()
	last_name_kana = ndb.StringProperty()
	first_name_kana = ndb.StringProperty()

	#is_two_factor_auth = ndb.StringProperty()						# ACTIVE：二要素認証を有効にする

	#lineworks_id = ndb.StringProperty()								# LINE WORKS ID

	#alias_name = ndb.StringProperty()								# 別名（一覧など用）
	#nickname = ndb.StringProperty()									# ニックネーム（コミュニティ用）
	#federation_identifier = ndb.StringProperty()			# 統合ID
	account_stop_flag = ndb.StringProperty(indexed=False)
	access_authority = ndb.StringProperty(repeated=True)			# ユーザ権限…ADMIN or OPERATOR or MANAGER
	delegate_function = ndb.StringProperty(repeated=True)			# 委託管理メニュー…ACCOUNT, GROUP, ORGUNIT, ACSAPPLY
	delegate_management_groups = ndb.StringProperty(repeated=True)			# 委託管理する管理グループ…委任管理者が管理できるデータ（ユーザ、グループ、OUなど）のカテゴリ
	management_group = ndb.StringProperty()			# 管理グループ（例：営業部門）…この管理グループの管理を委託された委託管理者がこのデータを管理できるようになる
	#data_federation_group = ndb.StringProperty()			# データ連携管理グループ…外部システム連携グループ. 複数のADと連携する場合など、連携ツールが複数に分かれる場合に各ツールで管理するデータを制御する
	#main_group_id = ndb.StringProperty()							# 小文字のみ
	#profile_infos = ndb.StringProperty(repeated=True)
	#profile_infos_lower = ndb.StringProperty(repeated=True)
	language = ndb.StringProperty(indexed=False)	# 言語設定 
	#matrixauth_pin_code = ndb.StringProperty()			# マトリックス認証：PINコード（数字4ケタを想定）
	#matrixauth_pin_code_enctype = ndb.StringProperty()					# 「matrixauth_pin_code」の暗号化対応（AES,DES デフォルト=DES）
	#matrixauth_place_key = ndb.StringProperty()			# マトリックス認証：プレースキー（アルファベット4ケタを想定）
	password_reminder_key = ndb.StringProperty()
	password_reminder_expire = ndb.DateTimeProperty(indexed=True)
	#secret_password_question = ndb.StringProperty(indexed=False)
	#secret_password_answer = ndb.StringProperty(indexed=False)
	next_password_change_flag = ndb.StringProperty(indexed=True)
	password_expire = ndb.DateTimeProperty()
	password_expire_current_notified = ndb.DateTimeProperty()			# 最後に通知されたパスワード期限（繰り返し通知しないための制御で使用）
	password_history = ndb.StringProperty(repeated=True)
	password_change_date = ndb.DateTimeProperty()		# 最後にSSOパスワード「password」が更新された日時（連携ツールで使用）
	password_change_date2 = ndb.DateTimeProperty()		# 最後にユーザーのパスワードが更新された日時（CSVエクスポートなどで使用）
	#mailproxy_available_flag = ndb.StringProperty(indexed=False)
	#fp_app_available_flag = ndb.StringProperty(indexed=False)
	#mobile_user_id = ndb.StringProperty()
	#mobile_device_id = ndb.StringProperty()
	#device_mac_address = ndb.StringProperty(repeated=True)		# 利用可能端末のMACアドレス.アクセス制御に使用
	#client_certificate_cn = ndb.StringProperty(repeated=True)		# ユーザーにヒモづくクライアント証明書のコモンネーム　※クライアント証明書認証で個人を特定するために使用
	#client_certificate_cn_lower = ndb.StringProperty(repeated=True)		# ユーザーにヒモづくクライアント証明書のコモンネーム（小文字）　※クライアント証明書認証で個人を特定するために使用
	login_failed_count = ndb.IntegerProperty(indexed=False)
	login_lock_flag = ndb.StringProperty()
	login_lock_expire = ndb.DateTimeProperty(indexed=True)
	last_login_date = ndb.DateTimeProperty()
	login_count = ndb.IntegerProperty(indexed=False)
	login_password_length = ndb.IntegerProperty(indexed=False)

#	# 連絡先・組織アドレス帳・ワークフロー関連項目
#	contact_company = ndb.StringProperty()								# 会社名
#	contact_company_office = ndb.StringProperty()								# 事業所
#	contact_company_department = ndb.StringProperty()								# 部署
#	contact_company_department2 = ndb.StringProperty()								# 課・グループ
#	contact_company_post = ndb.StringProperty()								# 役職
#	contact_email1 = ndb.StringProperty()								# メールアドレス（仕事）
#	contact_email2 = ndb.StringProperty()								# メールアドレス（携帯）
#	contact_tel_no1 = ndb.StringProperty()								# 電話番号
#	contact_tel_no2 = ndb.StringProperty()								# FAX番号
#	contact_tel_no3 = ndb.StringProperty()								# 携帯番号
#	contact_tel_no4 = ndb.StringProperty()								# 内線
#	contact_tel_no5 = ndb.StringProperty()								# ポケットベル
#	contact_postal_country = ndb.StringProperty()								# 国、地域
#	contact_postal_code = ndb.StringProperty()								# 郵便番号
#	contact_postal_prefecture = ndb.StringProperty()								# 住所（都道府県）
#	contact_postal_city = ndb.StringProperty()								# 住所（市区町村）
#	contact_postal_street_address = ndb.TextProperty()								# 住所（番地）
#
#	custom_attribute1 = ndb.StringProperty()								# 追加属性1 ※汎用SSOシステム等で使用する
#	custom_attribute2 = ndb.StringProperty()								# 追加属性2
#	custom_attribute3 = ndb.StringProperty()								# 追加属性3
#	custom_attribute4 = ndb.StringProperty()								# 追加属性4
#	custom_attribute5 = ndb.StringProperty()								# 追加属性5
#	custom_attribute6 = ndb.StringProperty()								# 追加属性6
#	custom_attribute7 = ndb.StringProperty()								# 追加属性7
#	custom_attribute8 = ndb.StringProperty()								# 追加属性8
#	custom_attribute9 = ndb.StringProperty()								# 追加属性9
#	custom_attribute10 = ndb.StringProperty()								# 追加属性10

	date_created = ndb.DateTimeProperty(auto_now_add=True,indexed=True)
	date_changed = ndb.DateTimeProperty(auto_now_add=True,indexed=True)
	creator_name = ndb.StringProperty(indexed=False)
	updater_name = ndb.StringProperty(indexed=False)

	def getDateTimeTypes():
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す '''
		return ['date_created', 'date_changed', 'password_reminder_expire', 'password_expire', 'password_expire_current_notified', 'password_change_date', 'password_change_date2', 'login_lock_expire', 'last_login_date']
	getDateTimeTypes = staticmethod(getDateTimeTypes)

	def getNumberTypes():
		u''' 数値型フィールドがあればここでフィールド名のリストを返す '''
		return ['login_failed_count', 'login_count', 'login_password_length']
	getNumberTypes = staticmethod(getNumberTypes)

	def getListTypes():
		u''' リスト型フィールドがあればここでフィールド名のリストを返す '''
		#return ['access_authority', 'delegate_function', 'delegate_management_groups', 'profile_infos', 'profile_infos_lower', 'password_history', 'device_mac_address', 'client_certificate_cn', 'client_certificate_cn_lower']
		return ['access_authority', 'password_history', 'delegate_function', 'delegate_management_groups']
	getListTypes = staticmethod(getListTypes)


	def put(self, without_update_fulltext_index=False):

		if not without_update_fulltext_index:
			try:
				# update full-text indexes.
				UCFMDLOperator.addOperatorToTextSearchIndex(self)
			except Exception as e:
				logging.info('failed update operator full-text index. unique_id=' + self.unique_id)
				logging.exception(e)

		#if self.client_certificate_cn is None:
		#	self.client_certificate_cn_lower = None
		#else:
		#	self.client_certificate_cn_lower = UcfUtil.csvToList(UcfUtil.listToCsv(self.client_certificate_cn).lower())

		#if self.profile_infos is not None:
		#	self.profile_infos_lower = []
		#	for profile_id in self.profile_infos:
		#		self.profile_infos_lower.append(profile_id.lower())
		#else:
		#	self.profile_infos_lower = None

		ndb.Model.put(self)

	def delete(self):
		try:
			UCFMDLOperator.removeOperatorFromIndex(self.unique_id)
		except Exception as e:
			logging.info('failed delete operator full-text index. unique_id=' + self.unique_id)
			logging.exception(e)
		#ndb.Model.delete(self)
		self.key.delete()

	# ユーザーマスターの利用数を取得
	@classmethod
	def getActiveUserAmount(cls, tenant):

		memcache_key = 'getactiveuseramount?tenant=' + tenant
		active_users = memcache.get(memcache_key)
		if active_users is not None:
			return active_users

		strOldNamespace = namespace_manager.get_namespace()
		#namespace_manager.set_namespace(tenant)
		namespace_manager.set_namespace(tenant.lower())
		try:
			# 利用ユーザー数を返す
			q = cls.query()
			active_users = q.count(limit=1000000)
			memcache.set(key=memcache_key, value=active_users, time=3600)
			return active_users
		finally:
			namespace_manager.set_namespace(strOldNamespace)

	# ユーザーマスターの利用数のキャッシュをクリア（ユーザー登録、削除時など）
	@classmethod
	def clearActiveUserAmountCache(cls, tenant):
		memcache_key = 'getactiveuseramount?tenant=' + tenant
		memcache.delete(memcache_key)

	# フルテキストカタログから一覧用の取得フィールドを返す
	@classmethod
	def getReturnedFieldsForTextSearch(cls):
		#return ['unique_id', 'mail_address', 'employee_id', 'first_name', 'last_name', 'alias_name', 'nickname', 'federation_identifier', 'access_authority', 'account_stop_flag', 'login_lock_flag', 'profile_infos']
		return ['unique_id', 'operator_id', 'first_name', 'last_name', 'access_authority', 'account_stop_flag', 'login_lock_flag']

	# フルテキストインデックスからハッシュデータ化して返す
	@classmethod
	def getDictFromTextSearchIndex(cls, ft_result):
		dict = {}
		for field in ft_result.fields:
			if field.name in cls.getReturnedFieldsForTextSearch():
				dict[field.name] = field.value.strip('#')
		return dict

	# ユーザーを全文検索用インデックスに追加する関数
	@classmethod
	def addOperatorToTextSearchIndex(cls, entry):

		vo = entry.exchangeVo(sateraito_inc.DEFAULT_TIMEZONE)	# 日付関連の項目はインデックスしないのでデフォルトタイムゾーンでOKとする

		# 検索用のキーワードをセット
		keyword = ''
		keyword += ' ' + vo.get('comment', '')
		keyword += ' ' + vo.get('operator_id', '')
		keyword += ' ' + vo.get('mail_address', '')
		keyword += ' ' + vo.get('sub_mail_address', '')
		keyword += ' ' + vo.get('last_name', '')
		keyword += ' ' + vo.get('first_name', '')
		keyword += ' ' + vo.get('last_name_kana', '')
		keyword += ' ' + vo.get('first_name_kana', '')
		keyword += ' ' + vo.get('contact_company', '')
		keyword += ' ' + vo.get('contact_company_office', '')
		keyword += ' ' + vo.get('contact_company_department', '')
		keyword += ' ' + vo.get('contact_company_department2', '')
		keyword += ' ' + vo.get('contact_company_post', '')
		keyword += ' ' + vo.get('contact_email1', '')
		keyword += ' ' + vo.get('contact_email2', '')
		keyword += ' ' + vo.get('contact_tel_no1', '')
		keyword += ' ' + vo.get('contact_tel_no2', '')
		keyword += ' ' + vo.get('contact_tel_no3', '')
		keyword += ' ' + vo.get('contact_tel_no4', '')
		keyword += ' ' + vo.get('contact_tel_no5', '')
		keyword += ' ' + vo.get('contact_postal_code', '')
		keyword += ' ' + vo.get('contact_postal_prefecture', '')
		keyword += ' ' + vo.get('contact_postal_city', '')
		keyword += ' ' + vo.get('contact_postal_street_address', '')
		keyword += ' ' + vo.get('custom_attribute1', '')
		keyword += ' ' + vo.get('custom_attribute2', '')
		keyword += ' ' + vo.get('custom_attribute3', '')
		keyword += ' ' + vo.get('custom_attribute4', '')
		keyword += ' ' + vo.get('custom_attribute5', '')
		keyword += ' ' + vo.get('custom_attribute6', '')
		keyword += ' ' + vo.get('custom_attribute7', '')
		keyword += ' ' + vo.get('custom_attribute8', '')
		keyword += ' ' + vo.get('custom_attribute9', '')
		keyword += ' ' + vo.get('custom_attribute10', '')

		# GAEGEN2対応:検索API移行
		# search = search_auto.get_module()
		search_document = search.Document(
							doc_id = entry.unique_id,
							fields=[
								search.TextField(name='unique_id', value=vo.get('unique_id', '')),												# キー
								search.TextField(name='operator_id', value=vo.get('operator_id', '')),				# 検索用
								search.TextField(name='operator_id_lower', value=vo.get('operator_id_lower', '')),				# 検索用
								search.TextField(name='management_group', value='#' + vo.get('management_group', '') + '#'),	# 検索用
								search.TextField(name='mail_address', value=vo.get('mail_address', '')),									# 表示用
								search.TextField(name='first_name', value=vo.get('first_name', '')),									# 表示用
								search.TextField(name='last_name', value=vo.get('last_name', '')),									# 表示用
								search.TextField(name='access_authority', value='#' + vo.get('access_authority', '') + '#'),									# 表示用
								search.TextField(name='account_stop_flag', value='#' + vo.get('account_stop_flag', '') + '#'),									# 表示用
								search.TextField(name='login_lock_flag', value='#' + vo.get('login_lock_flag', '') + '#'),									# 表示用
								search.TextField(name='text', value=keyword),									# 検索
								search.DateField(name='created_date', value=UcfUtil.getNow())
							])

		# GAEGEN2対応:検索API移行
		# search = search_auto.get_module()
		index = search.Index(name='operator_index')
		index.put(search_document)

	# 全文検索用インデックスより指定されたunique_idを持つインデックスを削除する関数
	@classmethod
	def removeOperatorFromIndex(cls, unique_id):
		# remove text search index
		# GAEGEN2対応:検索API移行
		# search = search_auto.get_module()
		index = search.Index(name='operator_index')
		index.delete(unique_id)


## モデル：採番マスタ
############################################################
class UCFMDLNumber(UCFModel):
	u'''採番マスタをイメージしたモデル'''

	unique_id = db.StringProperty(required=True)
	comment = db.TextProperty()
	dept_id = db.StringProperty(indexed=True)
	number_id = db.StringProperty()
	number_sub_id = db.StringProperty()
	prefix = db.StringProperty(indexed=False)
	sequence_no = db.IntegerProperty(indexed=False)
	sequence_no_digit = db.IntegerProperty(indexed=False)

	date_created = db.DateTimeProperty(auto_now_add=True,indexed=True)
	date_changed = db.DateTimeProperty(auto_now_add=True,indexed=True)
	creator_name = db.StringProperty(indexed=False)
	updater_name = db.StringProperty(indexed=False)

	def getNumberTypes():
		u''' 数値型フィールドがあればここでフィールド名のリストを返す '''
		return ['sequence_no', 'sequence_digit']
	getNumberTypes = staticmethod(getNumberTypes)

	def getDateTimeTypes():
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す '''
		return ['date_created', 'date_changed']
	getDateTimeTypes = staticmethod(getDateTimeTypes)

############################################################
## モデル：企業ドメイン
############################################################
class UCFMDLDeptMaster(UCFModel):
	u'''企業ドメインをイメージしたモデル'''

	unique_id = db.StringProperty(required=True)
	# comment = db.TextProperty()
	dept_id = db.StringProperty(indexed=False)
	# tenant = db.StringProperty()					# 小文字
	# title = db.StringProperty()
	# active_flag = db.StringProperty(indexed=False)
	date_created = db.DateTimeProperty(auto_now_add=True,indexed=True)
	date_changed = db.DateTimeProperty(auto_now_add=True,indexed=True)
	creator_name = db.StringProperty(indexed=False)
	updater_name = db.StringProperty(indexed=False)

	#office_ipaddresses = db.StringListProperty(indexed=False)			# 社内ネットワーク（各プロファイルで使用するための共通設定）
	#xforwardedfor_active_flag = db.StringProperty(indexed=False)	# アクセス制御：X-Forwarded-For を優先して使用するフラグ　ACTIVE…有効
	#xforwardedfor_whitelist = db.StringListProperty(indexed=False)	# アクセス制御：X-Forwarded-For使用時のREMOTE_ADDDR のホワイトリスト

	#profile_infos = db.StringListProperty()			# 全体設定で利用するプロファイルID
	#profile_infos_lower = db.StringListProperty()			# 全体設定で利用するプロファイルID（小文字）
	#hide_regist_sub_mail_address_link_flag = db.StringProperty(indexed=False)	# HIDDEN:マイページに予備のメールアドレス登録のリンクを表示しない
	language = db.StringProperty(indexed=False)	# 言語設定 
	timezone = db.StringProperty(indexed=False)	# タイムゾーン
	file_encoding = db.StringProperty(indexed=False)	# CSVファイルの文字コード（デフォルトはShift_JIS）
	username_disp_type = db.StringProperty(indexed=False)			# ユーザ名表示タイプ. ENGLISH…名 姓 の順にする 
	# company_name = db.StringProperty()	# 会社名
	# tanto_name = db.StringProperty()	# 担当者名
	# contact_mail_address = db.StringProperty()	# 担当者メールアドレス
	# contact_tel_no = db.StringProperty()	# 電話番号

	login_message = db.TextProperty()			# ログインページのメッセージ
	login_fontcolor = db.TextProperty()			# ログインページのフォントカラー：通常の文字列
	login_linkcolor = db.TextProperty()			# ログインページのフォントカラー：リンクカラー
	login_vccolor = db.TextProperty()			# ログインページのフォントカラー：VCメッセージなど
	login_messagecolor = db.TextProperty()			# ログインページのフォントカラー：メッセージボックス
	login_fontcolor_sp = db.TextProperty()			# ログインページのフォントカラー：通常の文字列（スマートフォンサイト）
	login_linkcolor_sp = db.TextProperty()			# ログインページのフォントカラー：リンクカラー（スマートフォンサイト）
	login_vccolor_sp = db.TextProperty()			# ログインページのフォントカラー：VCメッセージなど（スマートフォンサイト）
	login_messagecolor_sp = db.TextProperty()			# ログインページのフォントカラー：メッセージボックス（スマートフォンサイト）
	login_autocomplete_type = db.StringProperty(indexed=False)	# ログインボックスのオートコンプリートタイプ. ID:IDフィールドのみ BOTH:ID、パスワードともに. Empty:使用しない（デフォルト）
	is_disp_login_language_combobox = db.StringProperty(indexed=False)	# ログイン画面に言語設定ボックスを表示するかどうか（ACTIVE…表示する）

	md5_suffix_key = db.StringProperty(indexed=False)
	deptinfo_encode_key = db.StringProperty(indexed=False)
	login_history_max_export_cnt = db.IntegerProperty()			# ログイン履歴CSVエクスポート最大件数（0以下の場合はデフォルトの1000）
	login_history_save_term = db.IntegerProperty()			# ログイン履歴を保存する期間月数（0以下の場合はデフォルトの１２ヶ月）
	operation_log_save_term = db.IntegerProperty()			# オペレーションログを保存する期間月数（0以下の場合はデフォルトの６ヶ月）

	# oem_company_code = db.StringProperty()					# OEM提供先企業コード（例：sateraito：サテライト）
	# sp_codes = db.StringListProperty()					# 提供サービスコード. ,,,,

	# logo_data_key = db.StringProperty()
	# is_disp_login_custom_logo = db.StringProperty()	# ACTIVE…表示 ログイン画面にカスタムロゴを表示するかどうか（新デザイン時のみ）
	# login_background_pc1_data_key = db.StringProperty()
	# login_background_pc2_data_key = db.StringProperty()
	# login_background_pc3_data_key = db.StringProperty()
	# login_background_pc4_data_key = db.StringProperty()
	# login_background_pc5_data_key = db.StringProperty()
	# login_background_pc6_data_key = db.StringProperty()
	# login_background_pc7_data_key = db.StringProperty()
	# login_background_pc8_data_key = db.StringProperty()
	# login_background_pc9_data_key = db.StringProperty()
	# login_background_pc10_data_key = db.StringProperty()
	# login_background_sp1_data_key = db.StringProperty()

	# チャットGPT関連
	chatgpt_api_key = db.StringProperty()							# APIキー
	chatgpt_prohibited_keywords = db.TextProperty()			# 利用禁止キーワード
	available_domains_or_users = db.StringListProperty()			# 利用可能なドメイン、ユーザー一覧
	chatgpt_available_functions = db.StringListProperty()			# 利用可能な機能一覧（GPTAPP：Chrome拡張から右クリックでGPTに質問する機能）

	def getDateTimeTypes():
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す '''
		return ['date_created', 'date_changed']
	getDateTimeTypes = staticmethod(getDateTimeTypes)

	def getListTypes():
		u''' リスト型フィールドがあればここでフィールド名のリストを返す '''
		return ['sp_codes', 'available_domains_or_users', 'chatgpt_available_functions']
	getListTypes = staticmethod(getListTypes)

	def getBooleanTypes():
		u''' Bool型フィールドがあればここでフィールド名のリストを返す '''
		return []
	getBooleanTypes = staticmethod(getBooleanTypes)

	def getNumberTypes():
		u''' 数値型フィールドがあればここでフィールド名のリストを返す '''
		return ['login_history_max_export_cnt', 'login_history_save_term', 'operation_log_save_term']
	getNumberTypes = staticmethod(getNumberTypes)

	def put(self):
		db.Model.put(self)


############################################################
## モデル：ログイン履歴
############################################################
class UCFMDLLoginHistory(UCFModel2):
	u'''ログイン履歴をイメージしたモデル'''

	unique_id = ndb.StringProperty(required=True)
	comment = ndb.TextProperty()
	dept_id = ndb.StringProperty(indexed=False)
	operator_unique_id = ndb.StringProperty()			# ユーザＩＤ変更を考慮してユーザにヒモづく一覧を取得する際にはこれをキーとして取得
	operator_id = ndb.StringProperty()							# CSV出力時には必要だと思うので
	operator_id_lower = ndb.StringProperty()							# 小文字
	login_id = ndb.StringProperty()							# ログインで使用したＩＤ（ユーザＩＤ、社員ＩＤ）
	login_id_lower = ndb.StringProperty()							# 小文字（検索用）
	login_password = ndb.StringProperty(indexed=False)							# ログインで使用したパスワード（暗号化）※ハッキング対策などに使用するため一応保持
	login_password_enctype = ndb.StringProperty()							# ログインパスワードの暗号化タイプ（AES、DES デフォルト=DES）
	login_password_length = ndb.IntegerProperty(indexed=False)
	login_type = ndb.StringProperty(indexed=False)
	login_result = ndb.StringProperty()				# ログイン成功フラグ SUCCESS OR FAILED
	log_code = ndb.StringProperty()				# ID_FAILED など
	is_exist_log_detail = ndb.BooleanProperty()	# True…log_textを詳細テーブルに保持
	log_text = ndb.TextProperty()						# 別途詳細ログがあれば設定（is_exist_log_detail=Trueの場合は詳細テーブルに保持）
	user_agent = ndb.TextProperty()			
	session_id = ndb.StringProperty()				# セッションＩＤ（取得できるのかな）
	cookie_auth_id = ndb.StringProperty()				# 認証ＩＤ（Ｃｏｏｋｉｅ認証実装時の認証ＩＤ）
	client_ip = ndb.StringProperty(indexed=False)
	#client_x_forwarded_for_ip = ndb.StringProperty(indexed=False)
	#use_profile_id = ndb.StringProperty()									# 認証時に使用したプロファイルＩＤ
	#use_access_apply_unique_id = ndb.StringProperty()			# ログイン成功時に使用したアクセス申請データのユニークＩＤ
	target_career = ndb.StringProperty()
	#target_env = ndb.StringProperty()		# 対象環境ID（office, outside, sp, fp)
	is_auto_login = ndb.StringProperty()		# AUTO…自動ログインでのアクセス
	#mobile_user_id = ndb.StringProperty()	
	#mobile_device_id = ndb.StringProperty()
	access_date = ndb.DateTimeProperty()
	management_group = ndb.StringProperty()			# 管理グループ（例：営業部門）…この管理グループの管理を委託された委託管理者がこのデータを管理できるようになる
	date_created = ndb.DateTimeProperty(auto_now_add=True,indexed=True)
	date_changed = ndb.DateTimeProperty(auto_now_add=True,indexed=True)
	creator_name = ndb.StringProperty(indexed=False)
	updater_name = ndb.StringProperty(indexed=False)

	def getNumberTypes():
		u''' 数値型フィールドがあればここでフィールド名のリストを返す '''
		return ['login_password_length']
	getNumberTypes = staticmethod(getNumberTypes)

	def getDateTimeTypes():
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す '''
		return ['date_created', 'date_changed', 'access_date']
	getDateTimeTypes = staticmethod(getDateTimeTypes)

	def getBooleanTypes():
		u''' Bool型フィールドがあればここでフィールド名のリストを返す '''
		return ['is_exist_log_detail']
	getBooleanTypes = staticmethod(getBooleanTypes)


############################################################
## モデル：ログイン履歴詳細
############################################################
class UCFMDLLoginHistoryDetail(UCFModel2):
	u'''ログイン履歴詳細をイメージしたモデル'''

	unique_id = ndb.StringProperty(required=True)
	history_unique_id = ndb.StringProperty()
	log_text = ndb.TextProperty()
	date_created = ndb.DateTimeProperty(auto_now_add=True)

############################################################
## モデル：ログイン履歴（遅延登録用一時登録テーブル）
############################################################
class UCFMDLLoginHistoryForDelay(UCFModel2):
	u'''ログイン履歴（遅延登録用一時登録テーブル）'''

	unique_id = ndb.StringProperty(required=True)
	operator_unique_id = ndb.StringProperty()			# ユーザＩＤ変更を考慮してユーザにヒモづく一覧を取得する際にはこれをキーとして取得
	operator_id_lower = ndb.StringProperty()							# メールアドレス小文字
	params = ndb.TextProperty()				# ログイン履歴関連の情報（JSON）
	date_created = ndb.DateTimeProperty(auto_now_add=True)

	def getDateTimeTypes():
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す '''
		return ['date_created']
	getDateTimeTypes = staticmethod(getDateTimeTypes)

############################################################
## モデル：ログイン情報（成功、失敗）（遅延登録用一時登録テーブル）
############################################################
class UCFMDLLoginInfoForDelay(UCFModel2):
	u'''ログイン情報（成功、失敗）（遅延登録用一時登録テーブル）'''

	unique_id = ndb.StringProperty(required=True)
	operator_unique_id = ndb.StringProperty()			# ユーザＩＤ変更を考慮してユーザにヒモづく一覧を取得する際にはこれをキーとして取得
	operator_id_lower = ndb.StringProperty()							# メールアドレス小文字
	params = ndb.TextProperty()				# ログイン情報関連の情報（JSON）
	date_created = ndb.DateTimeProperty(auto_now_add=True)

	def getDateTimeTypes():
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す '''
		return ['date_created']
	getDateTimeTypes = staticmethod(getDateTimeTypes)



############################################################
## モデル：ファイル
############################################################
class UCFMDLFile(UCFModel):
	u'''ファイルテーブルをイメージしたモデル'''

	unique_id = db.StringProperty(required=True)
	comment = db.TextProperty()
	dept_id = db.StringProperty(indexed=False)
	data_key = db.StringProperty()			# キー：フロントからこのキーで取得
	data_kind = db.StringProperty()			# 種類（exportgroupcsv, exportaccountcsv, importgroupcsv, importaccountcsv,picture,....）
	data_type = db.StringProperty()			# データタイプ（CSV,BINARY)
	content_type = db.StringProperty()			# MIMEコンテンツタイプ
	data_name = db.StringProperty()			# ファイル名
	data_path = db.StringProperty()
	data_size = db.IntegerProperty()
	blob_key = db.StringProperty()
	data_encoding = db.StringProperty()
	upload_operator_id = db.StringProperty()
	upload_operator_unique_id = db.StringProperty()
	upload_count = db.IntegerProperty()
	last_upload_operator_id = db.StringProperty()
	last_upload_operator_unique_id = db.StringProperty()
	last_upload_date = db.DateTimeProperty()
	download_operator_id = db.StringProperty()
	download_operator_unique_id = db.StringProperty()
	download_count = db.IntegerProperty()
	last_download_operator_id = db.StringProperty()
	last_download_operator_unique_id = db.StringProperty()
	last_download_date = db.DateTimeProperty()
	access_url = db.StringProperty()			# 実体が別のところにある場合、そのURLをセット
	is_use_item = db.BooleanProperty()		# UCFMDLFileItemを使う場合、True（1MB制限対策）
	text_data = db.TextProperty()
	blob_data = db.BlobProperty()
	status = db.StringProperty()		# SUCCESS:処理成功 FAILED:処理失敗
	deal_status = db.StringProperty()					# CREATING…作成中 FIN…処理完了
	expire_date = db.DateTimeProperty()				# このデータのアクセス期限（期限失効後はタスクにより削除）
	log_text = db.TextProperty()					# インポートなどのログ
	task_token = db.StringProperty()					# ＧＡＥのプロセスが強制ＫＩＬＬされた際のチェック用
	date_created = db.DateTimeProperty(auto_now_add=True,indexed=True)
	date_changed = db.DateTimeProperty(auto_now_add=True,indexed=True)
	creator_name = db.StringProperty(indexed=False)
	updater_name = db.StringProperty(indexed=False)

	def getDateTimeTypes():
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す '''
		return ['date_created', 'date_changed', 'last_download_date', 'last_upload_date', 'expire_date']
	getDateTimeTypes = staticmethod(getDateTimeTypes)

	def getNumberTypes():
		u''' 数値型フィールドがあればここでフィールド名のリストを返す '''
		return ['data_size','upload_count','download_count']
	getNumberTypes = staticmethod(getNumberTypes)

	def getBooleanTypes():
		u''' Bool型フィールドがあればここでフィールド名のリストを返す '''
		return ['is_use_item']
	getBooleanTypes = staticmethod(getBooleanTypes)

	def getBlobTypes():
		u''' Blobフィールドがあればここでフィールド名のリストを返す '''
		return ['blob_data']
	getBlobTypes = staticmethod(getBlobTypes)

############################################################
## モデル：ファイルアイテム
############################################################
class UCFMDLFileItem(UCFModel):
	u'''ファイルテーブルをイメージしたモデル'''
	unique_id = db.StringProperty(required=True)
	data_key = db.StringProperty()
	item_order = db.IntegerProperty()
	text_data = db.TextProperty()
	blob_data = db.BlobProperty()
	date_created = db.DateTimeProperty(auto_now_add=True,indexed=True)
	date_changed = db.DateTimeProperty(auto_now_add=True,indexed=True)

	def getDateTimeTypes():
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す '''
		return ['date_created', 'date_changed']
	getDateTimeTypes = staticmethod(getDateTimeTypes)

	def getNumberTypes():
		u''' 数値型フィールドがあればここでフィールド名のリストを返す '''
		return ['item_order']
	getNumberTypes = staticmethod(getNumberTypes)

	def getBlobTypes():
		u''' Blobフィールドがあればここでフィールド名のリストを返す '''
		return ['blob_data']
	getBlobTypes = staticmethod(getBlobTypes)



############################################################
## モデル：ID変更履歴、タスク管理
############################################################
class UCFMDLTaskChangeID(UCFModel):
	unique_id = db.StringProperty(required=True)
	comment = db.TextProperty()
	dept_id = db.StringProperty(indexed=False)
	task_type = db.StringProperty()			# change_operator_id,change_user_id,change_group_id
	task_deal_status = db.StringProperty()		# (Empty：ポーリング対象) WAIT：処理開始待ち PROCESSING：処理中 STOP:停止 STOP_INDICATING:停止指示中 FIN:処理完了
	task_status = db.StringProperty()		# SUCCESS:処理成功 FAILED:処理失敗
	task_status_date = db.DateTimeProperty()	# ステータス更新日
	task_start_date = db.DateTimeProperty()				# 最終タスク開始日
	task_end_date = db.DateTimeProperty()					# 最終タスク完了日
	execute_operator_id = db.StringProperty()					# 実行ユーザ
	log_text = db.TextProperty()					# ログ
	target_unique_id = db.StringProperty()		# 対象アカウント、グループ等のユニークID
	src_data_id = db.StringProperty()					# 元のアカウント、グループID
	dst_data_id = db.StringProperty()					# 変更後のアカウント、グループID
	date_created = db.DateTimeProperty(auto_now_add=True,indexed=True)
	date_changed = db.DateTimeProperty(auto_now_add=True,indexed=True)
	creator_name = db.StringProperty(indexed=False)
	updater_name = db.StringProperty(indexed=False)

	def getDateTimeTypes():
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す '''
		return ['date_created', 'date_changed', 'task_status_date', 'task_start_date', 'task_end_date']
	getDateTimeTypes = staticmethod(getDateTimeTypes)

	def getBooleanTypes():
		u''' Bool型フィールドがあればここでフィールド名のリストを返す '''
		return []
	getBooleanTypes = staticmethod(getBooleanTypes)


############################################################
## モデル：二要素認証コード
############################################################
class UCFMDLTwoFactorAuth(UCFModel):
	u'''二要素認証のコードを管理（1ユーザ1レコード） '''
	unique_id = db.StringProperty(required=True)
	dept_id = db.StringProperty(indexed=False)
	operator_unique_id = db.StringProperty()			# ユーザＩＤ変更を考慮してユーザにヒモづく一覧を取得する際にはこれをキーとして取得
	two_factor_auth_code = db.StringProperty()		# 二要素認証コード
	auth_code_expire = db.DateTimeProperty()			# 二要素認証期限
	date_created = db.DateTimeProperty(auto_now_add=True,indexed=True)
	date_changed = db.DateTimeProperty(auto_now_add=True,indexed=True)

	def getDateTimeTypes():
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す '''
		return ['date_created', 'date_changed', 'auth_code_expire']
	getDateTimeTypes = staticmethod(getDateTimeTypes)


############################################################
## モデル：オペレーションログ
############################################################
class UCFMDLOperationLog(UCFModel2):

	unique_id = ndb.StringProperty(required=True)
	operation_date = ndb.DateTimeProperty()
	operator_id = ndb.StringProperty()
	operator_unique_id = ndb.StringProperty()
	screen = ndb.StringProperty()															# 大体のページなど。分類用？
	operation_type = ndb.StringProperty()													# 処理種別
	operation = ndb.StringProperty()																	# 検索条件に使いたいのでオペレーションに対して一意となるような値
	target_unique_id = ndb.StringProperty()												# 対象のデータの内部ID（operationによって入る値は決まってくる）
	target_data = ndb.StringProperty()												# 対象のデータの表示用ID（operationによって入る値は決まってくる）
	client_ip = ndb.StringProperty()
	is_api = ndb.BooleanProperty()														# APIからのアクセス
	detail = ndb.TextProperty()
	date_created = ndb.DateTimeProperty(auto_now_add=True)
	date_changed = ndb.DateTimeProperty(auto_now=True)

	@classmethod
	def addLog(cls, operator_id, operator_unique_id, screen, operation_type, target_data, target_unique_id, client_ip, detail, is_api=False, is_async=False):
		row = cls()
		row.unique_id = UcfUtil.guid()
		row.operator_id = operator_id
		row.operator_unique_id = operator_unique_id
		row.screen = screen
		row.operation_type = operation_type
		row.operation = screen + '_' + operation_type
		row.target_unique_id = target_unique_id
		row.target_data = target_data
		row.client_ip = client_ip
		row.is_api = is_api
		row.detail = detail
		row.operation_date = datetime.datetime.now(tz=None)
		if is_async:
			future = row.put_async()
		else:
			row.put()

	def getDateTimeTypes():
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す '''
		return ['operation_date', 'date_created', 'date_changed']
	getDateTimeTypes = staticmethod(getDateTimeTypes)

	def getBooleanTypes():
		u''' Bool型フィールドがあればここでフィールド名のリストを返す '''
		return ['is_api']
	getBooleanTypes = staticmethod(getBooleanTypes)


############################################################
## モデル：ボード
############################################################
class UCFMDLBoard(UCFModel2):

	unique_id = ndb.StringProperty(required=True)
	board_id = ndb.StringProperty()
	board_name = ndb.StringProperty()
	user_unique_id = ndb.StringProperty()		# 将来ユーザー管理作った際に使用予定
	user_id = ndb.StringProperty()	
	session_id = ndb.StringProperty()					# ログインしていない場合はセッションIDで識別するしか無いため
	last_input_text = ndb.TextProperty()
	last_output_text = ndb.TextProperty()
	count_attach = ndb.IntegerProperty(default=0)
	count_memo = ndb.IntegerProperty(default=0)
	count_question = ndb.IntegerProperty(default=0)
	groups = ndb.StringProperty(repeated=True)
	labels = ndb.StringProperty(repeated=True)
	date_created = ndb.DateTimeProperty(auto_now_add=True)
	date_changed = ndb.DateTimeProperty(auto_now=True)

	@classmethod
	def getChatRecents(cls, board_id, limit=10, timezone=None):
		# 会話履歴一覧取得
		# 会話履歴をDBから取得
		q = UCFMDLChatHistory.query()
		q = q.filter(UCFMDLChatHistory.board_id == board_id)
		q = q.order(-UCFMDLChatHistory.date_created)

		message_historys = []

		# とりあえず最新から20件程度
		now = UcfUtil.getNow()
		for history_row in q.fetch(limit=limit):
			# 今日
			is_today = False
			is_current_year = False
			if history_row.date_created.year == now.year and history_row.date_created.month == now.month and history_row.date_created.day == now.day:
				is_today = True
			elif history_row.date_created.year == now.year:
				is_current_year = True

			if history_row.output_text is not None and history_row.output_text != '':
				timestamp_for_disp = ''
				if is_today:
					timestamp_for_disp = UcfUtil.getLocalTime(
						UcfUtil.add_seconds(history_row.date_created, history_row.response_time), timezone).strftime(
						'%H:%M:%S')
				elif is_current_year:
					timestamp_for_disp = UcfUtil.getLocalTime(
						UcfUtil.add_seconds(history_row.date_created, history_row.response_time), timezone).strftime(
						'%m/%d %H:%M')
				else:
					timestamp_for_disp = UcfUtil.getLocalTime(
						UcfUtil.add_seconds(history_row.date_created, history_row.response_time), timezone).strftime(
						'%Y/%m/%d %H:%M')

				message_historys.insert(0, {
					"timestamp_for_disp": timestamp_for_disp,
					"role": "assistant",
					# "content": history_row.output_text
					"message": history_row.output_text
				})
			if history_row.input_text is not None and history_row.input_text != '':
				timestamp_for_disp = ''
				if is_today:
					timestamp_for_disp = UcfUtil.getLocalTime(history_row.date_created, timezone).strftime('%H:%M:%S')
				elif is_current_year:
					timestamp_for_disp = UcfUtil.getLocalTime(history_row.date_created, timezone).strftime('%m/%d %H:%M')
				else:
					timestamp_for_disp = UcfUtil.getLocalTime(history_row.date_created, timezone).strftime(
						'%Y/%m/%d %H:%M')
				message_historys.insert(0, {
					"timestamp_for_disp": timestamp_for_disp,
					"role": "user",
					# "content": history_row.input_text
					"message": history_row.input_text
				})
		return message_historys

############################################################
## UCFMDLGroupBoard
############################################################
class UCFMDLGroupBoard(UCFModel2):

	unique_id = ndb.StringProperty(required=True)
	group_id = ndb.StringProperty()
	group_name = ndb.StringProperty()
	group_name_lower = ndb.StringProperty()
	user_unique_id = ndb.StringProperty()		# 将来ユーザー管理作った際に使用予定
	user_id = ndb.StringProperty()
	session_id = ndb.StringProperty()
	description = ndb.TextProperty(default="")
	text_color = ndb.StringProperty(default="")
	bg_color = ndb.StringProperty(default="")
	display = ndb.BooleanProperty(default=False)
	date_created = ndb.DateTimeProperty(auto_now_add=True)
	date_changed = ndb.DateTimeProperty(auto_now=True)

############################################################
## UCFMDLLabelBoard
############################################################
class UCFMDLLabelBoard(UCFModel2):

	unique_id = ndb.StringProperty(required=True)
	label_id = ndb.StringProperty()
	label_name = ndb.StringProperty()
	label_name_lower = ndb.StringProperty()
	user_unique_id = ndb.StringProperty()		# 将来ユーザー管理作った際に使用予定
	user_id = ndb.StringProperty()
	session_id = ndb.StringProperty()
	description = ndb.TextProperty(default="")
	text_color = ndb.StringProperty(default="")
	bg_color = ndb.StringProperty(default="")
	display = ndb.BooleanProperty(default=False)
	date_created = ndb.DateTimeProperty(auto_now_add=True)
	date_changed = ndb.DateTimeProperty(auto_now=True)

############################################################
## UCFMDLSuggestionChat
############################################################
class UCFMDLSuggestionChat(UCFModel2):

	unique_id = ndb.StringProperty(required=True)
	suggest_id = ndb.StringProperty()
	user_unique_id = ndb.StringProperty()		# 将来ユーザー管理作った際に使用予定
	user_id = ndb.StringProperty()
	session_id = ndb.StringProperty()
	message = ndb.TextProperty()
	display = ndb.BooleanProperty(default=False)
	date_created = ndb.DateTimeProperty(auto_now_add=True)
	date_changed = ndb.DateTimeProperty(auto_now=True)

############################################################
## モデル：Chat履歴
############################################################
class UCFMDLChatHistory(UCFModel2):

	unique_id = ndb.StringProperty(required=True)
	user_id = ndb.StringProperty()							# ユーザーID（空の場合もあり）
	user_id_lower = ndb.StringProperty()							# ユーザーID小文字（検索用）（空の場合もあり）
	user_unique_id = ndb.StringProperty()	
	session_id = ndb.StringProperty()				# セッションＩＤ
	board_id = ndb.StringProperty()			
	user_agent = ndb.TextProperty()			
	client_ip = ndb.StringProperty()
	target_career = ndb.StringProperty()
	model = ndb.StringProperty()					# チャットGPTのモデル
	action_type = ndb.StringProperty()					# question:質問、summary:要約する
	access_date = ndb.DateTimeProperty()
	result_code = ndb.StringProperty()														# 結果コード：成功…SUCCESS、その他失敗時のエラーコード
	error_info = ndb.TextProperty()												# NGワードで引っかかった場合の具体的な文言やエラーメッセージなど
	response_time = ndb.IntegerProperty()		# 応答時間（秒）
	input_text = ndb.TextProperty()
	output_text = ndb.TextProperty()
	input_text_length = ndb.IntegerProperty()		# 入力文章文字数
	output_text_length = ndb.IntegerProperty()		# 出力文章文字数
	#like_status = ndb.StringProperty()					# 
	like_num = ndb.IntegerProperty(default=0)		# いいね数
	unlike_num = ndb.IntegerProperty(default=0)		# よくないね数
	management_group = ndb.StringProperty()
	date_created = ndb.DateTimeProperty(auto_now_add=True)
	date_changed = ndb.DateTimeProperty(auto_now=True)

	def getNumberTypes():
		u''' 数値型フィールドがあればここでフィールド名のリストを返す '''
		return ['response_time', 'input_text_length', 'output_text_length', 'like_num', 'unlike_num']
	getNumberTypes = staticmethod(getNumberTypes)

	def getDateTimeTypes():
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す '''
		return ['date_created', 'date_changed', 'access_date']
	getDateTimeTypes = staticmethod(getDateTimeTypes)

	def getBooleanTypes():
		u''' Bool型フィールドがあればここでフィールド名のリストを返す '''
		return []
	getBooleanTypes = staticmethod(getBooleanTypes)

	def put(self, without_update_fulltext_index=False):

		if not without_update_fulltext_index:
			try:
				# update full-text indexes.
				UCFMDLChatHistory.addToTextSearchIndex(self)
			except Exception as e:
				logging.info('failed update full-text index. unique_id=%s' % (self.unique_id))
				logging.exception(e)

		if self.user_id is None:
			self.user_id_lower = None
		else:
			self.user_id_lower = self.user_id.lower()

		ndb.Model.put(self)

	def delete(self):
		try:
			UCFMDLChatHistory.removeFromIndex(self.unique_id)
		except Exception as e:
			logging.info('failed delete full-text index. unique_id=%s' % (self.unique_id))
			logging.exception(e)
		self.key.delete()

	# フルテキストカタログから一覧用の取得フィールドを返す
	@classmethod
	def getReturnedFieldsForTextSearch(cls):
		return ['unique_id', 'user_id', 'access_date_epoch', 'result_code', 'error_info', 'input_text', 'input_text_length', 'model', 'action_type', 'client_ip', 'like_num', 'unlike_num', 'user_unique_id', 'board_id']

	# フルテキストインデックスからハッシュデータ化して返す
	@classmethod
	def getDictFromTextSearchIndex(cls, ft_result, timezone=None):
		if timezone is None:
			timezone = sateraito_inc.DEFAULT_TIMEZONE
		dict = {}
		for field in ft_result.fields:
			if field.name in cls.getReturnedFieldsForTextSearch():
				#if isinstance(field.value, str) or isinstance(field.value, unicode):
				if isinstance(field.value, str):
					dict[field.name] = field.value.strip('#')
				elif isinstance(field.value, datetime.datetime):
					dict[field.name] = UcfUtil.nvl(UcfUtil.getLocalTime(field.value, timezone))
				else:
					dict[field.name] = str(field.value)
		return dict

	# データを全文検索用インデックスに追加する関数
	@classmethod
	def addToTextSearchIndex(cls, entry):

		vo = entry.exchangeVo(sateraito_inc.DEFAULT_TIMEZONE)

		# 検索用のキーワードをセット
		keyword = ''
		keyword += ' ' + vo.get('user_id', '')
		keyword += ' ' + vo.get('input_text', '')
		keyword += ' ' + vo.get('output_text', '')
		keyword += ' ' + vo.get('error_info', '')

		logging.info(entry.access_date)
		logging.info(sateraito_func.datetimeToEpoch(entry.access_date) if entry.access_date is not None else 0)

		# GAEGEN2対応:検索API移行
		# search = search_auto.get_module()
		search_document = search.Document(
							doc_id = entry.unique_id,
							fields=[
								search.TextField(name='unique_id', value=vo.get('unique_id', '')),												# キー
								search.TextField(name='user_id', value=vo.get('user_id', '')),				# 検索用
								search.TextField(name='user_unique_id', value=vo.get('user_unique_id', '')),				# 検索用
								search.TextField(name='session_id', value=vo.get('session_id', '')),				# 検索用
								search.TextField(name='board_id', value=vo.get('board_id', '')),				# 検索用
								search.TextField(name='model', value=vo.get('model', '')),				# 検索用
								#search.TextField(name='like_status', value=vo.get('like_status', '')),				# 表示用
								search.TextField(name='like_num', value=vo.get('like_num', '')),									# 表示用
								search.TextField(name='unlike_num', value=vo.get('unlike_num', '')),									# 表示用
								search.TextField(name='action_type', value=vo.get('action_type', '')),				# 表示用
								search.TextField(name='input_text', value=vo.get('input_text', '')),									# 表示用
								search.TextField(name='input_text_length', value=vo.get('input_text_length', '')),									# 表示用
								search.TextField(name='error_info', value=vo.get('error_info', '')),									# 表示用
								search.TextField(name='client_ip', value=vo.get('client_ip', '')),									# 表示用
								search.TextField(name='response_time', value=vo.get('response_time', '')),									# 表示用
								search.TextField(name='text', value=keyword),									# 検索用
								search.TextField(name='management_group', value='#' + vo.get('management_group', '') + '#'),	# 検索用
								search.TextField(name='result_code', value='#' + vo.get('result_code', '') + '#'),	# 検索用
								search.NumberField(name='access_date_epoch', value=sateraito_func.datetimeToEpoch(entry.access_date) if entry.access_date is not None else 0),
								search.NumberField(name='date_created_epoch', value=sateraito_func.datetimeToEpoch(entry.date_created) if entry.date_created is not None else 0),
							])

		# GAEGEN2対応:検索API移行
		# search = search_auto.get_module()
		index = search.Index(name='chatgpt_history_index')
		index.put(search_document)

	# 全文検索用インデックスより指定されたunique_idを持つインデックスを削除する関数
	@classmethod
	def removeFromIndex(cls, unique_id):
		# remove text search index
		# GAEGEN2対応:検索API移行
		# search = search_auto.get_module()
		index = search.Index(name='chatgpt_history_index')
		index.delete(unique_id)


class UCFMDLUserChatHistory(UCFModel2):
	unique_id = ndb.StringProperty(required=True)
	user_unique_id = ndb.StringProperty()		# 将来ユーザー管理作った際に使用予定
	user_id = ndb.StringProperty()
	session_id = ndb.StringProperty()
	history_id = ndb.StringProperty()
	board_id = ndb.StringProperty()
	date_created = ndb.DateTimeProperty(auto_now_add=True)
	date_changed = ndb.DateTimeProperty(auto_now=True)

	def _post_put_hook(self, future):
		if self is not None:
			UCFMDLUserChatHistory.clearInstanceCache(self.user_id, self.board_id)

	@classmethod
	def getMemcacheKey(cls, user_id, board_id):
		return 'script=UCFMDLFavoritesList&user_id=' + str(user_id) + '&component_id=' + str(board_id)

	@classmethod
	def clearInstanceCache(cls, user_id, board_id):
		memcache.delete(cls.getMemcacheKey(user_id, board_id))

	@classmethod
	def getInstance(cls):
		return cls()

	@classmethod
	def get_dict(cls, user_id, board_id):
		# check memcache
		memcache_key = cls.getMemcacheKey(user_id, board_id)
		logging.info(memcache_key)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			logging.info('UCFMDLFavoritesList.getDict: found and respond cache')
			logging.info(cached_dict)
			return cached_dict

		q = cls.query()
		q = q.filter(cls.user_id == user_id)
		q = q.filter(cls.board_id == board_id)
		entry = q.get()
		if entry:
			# set to memcache
			row_dict = {
				'user_email_current': entry.user_email_current,
				'component_id': entry.component_id
			}
			memcache.set(memcache_key, row_dict, time=cls.NDB_MEMCACHE_TIMEOUT)
			return row_dict

		cls.clearInstanceCache(user_id, board_id)
		return None

	@classmethod
	def delete(cls, user_id, board_id):
		q = cls.all()
		q = q.filter(cls.user_id == user_id)
		q = q.filter(cls.board_id == board_id)
		entry = q.get()
		logging.info('entry:'+str(entry))
		if entry:
			logging.info('delete')
			entry.key.delete()
			cls.clearInstanceCache(user_id, board_id)
			return True
		return False

	@classmethod
	def deleteAllByBoardId(cls, board_id):
		q = cls.query()
		q = q.filter('board_id =', board_id)
		rows = q.fetch(limit=None)
		for row in rows:
			cls.clearInstanceCache(row.user_id, board_id)
			row.key.delete()
		return True

	@classmethod
	def query_all_component_id(cls, component_id):
		q = cls.all()
		q.filter('component_id =', component_id)
		return q

	@classmethod
	def query_all_email(cls, component_id, tab_id):
		q = cls.all()
		q.filter('component_id =', component_id)
		q.filter('tab_id =', tab_id)
		q.order('-created_date')
		return q

	@classmethod
	def is_Favorite(cls, component_id, email):
		row = cls.get_dict(email, component_id)
		if row is not None:
			return True
		return False

class UCFMDLFavoritesList(UCFModel2):
	unique_id = ndb.StringProperty(required=True)
	user_unique_id = ndb.StringProperty()		# 将来ユーザー管理作った際に使用予定
	user_id = ndb.StringProperty()
	session_id = ndb.StringProperty()
	board_id = ndb.StringProperty()
	date_created = ndb.DateTimeProperty(auto_now_add=True)
	date_changed = ndb.DateTimeProperty(auto_now=True)

	def _post_put_hook(self, future):
		if self is not None:
			UCFMDLFavoritesList.clearInstanceCache(self.user_id, self.board_id)

	# @classmethod
	# def _pre_delete_hook(cls, key):
	# 	row = key.get()
	# 	if row is not None:
	# 		cls.clearInstanceCache(row.file_id)

	@classmethod
	def getMemcacheKey(cls, user_id, board_id):
		return 'script=UCFMDLFavoritesList&user_id=' + str(user_id) + '&component_id=' + str(board_id)

	@classmethod
	def clearInstanceCache(cls, user_id, board_id):
		memcache.delete(cls.getMemcacheKey(user_id, board_id))

	@classmethod
	def getInstance(cls):
		return cls()

	@classmethod
	def get_dict(cls, user_id, board_id):
		# check memcache
		memcache_key = cls.getMemcacheKey(user_id, board_id)
		logging.info(memcache_key)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			logging.info('UCFMDLFavoritesList.getDict: found and respond cache')
			logging.info(cached_dict)
			return cached_dict

		q = cls.query()
		q = q.filter(cls.user_id == user_id)
		q = q.filter(cls.board_id == board_id)
		entry = q.get()
		if entry:
			# set to memcache
			row_dict = {
				'user_id': entry.user_id,
				'board_id': entry.board_id
			}
			memcache.set(memcache_key, row_dict, time=cls.NDB_MEMCACHE_TIMEOUT)
			return row_dict

		cls.clearInstanceCache(user_id, board_id)
		return None

	@classmethod
	def delete(cls, user_id, board_id):
		q = cls.query()
		q = q.filter(cls.user_id == user_id)
		q = q.filter(cls.board_id == board_id)
		entry = q.get()
		logging.info('entry:'+str(entry))
		if entry:
			logging.info('delete')
			entry.key.delete()
			cls.clearInstanceCache(user_id, board_id)
			return True
		return False

	# @classmethod
	# def deleteAllByBoardId(cls, board_id):
	# 	q = cls.query()
	# 	q = q.filter('board_id =', board_id)
	# 	rows = q.fetch(limit=None)
	# 	for row in rows:
	# 		cls.clearInstanceCache(row.user_id, board_id)
	# 		row.key.delete()
	# 	return True

	# @classmethod
	# def query_all_component_id(cls, component_id):
	# 	q = cls.all()
	# 	q.filter('component_id =', component_id)
	# 	return q

	# @classmethod
	# def query_all_email(cls, component_id, tab_id):
	# 	q = cls.all()
	# 	q.filter('component_id =', component_id)
	# 	q.filter('tab_id =', tab_id)
	# 	q.order('-created_date')
	# 	return q

	@classmethod
	def is_Favorite(cls, component_id, email):
		row = cls.get_dict(email, component_id)
		if row is not None:
			return True
		return False

class UCFMDLUserInfo(UCFModel2):
	google_apps_user_id = ndb.StringProperty()
	be_registered = ndb.BooleanProperty(default=False)
	user_entry_id = ndb.StringProperty()
	email = ndb.StringProperty()

	followers = ndb.IntegerProperty(repeated=True)
	following = ndb.IntegerProperty(repeated=True)

	avatar_url = ndb.StringProperty()
	avatar_blob_key = ndb.BlobKeyProperty()
	avatar_blob_id = ndb.StringProperty()

	skill = ndb.StringProperty()
	lives_in = ndb.StringProperty()
	come_from = ndb.StringProperty()
	works_at = ndb.StringProperty()

	website_url = ndb.StringProperty()
	twitter_url = ndb.StringProperty()
	facebook_url = ndb.StringProperty()
	instagram_url = ndb.StringProperty()
	linkedin_url = ndb.StringProperty()

	fullname = ndb.StringProperty()
	nickname = ndb.StringProperty()
	family_name = ndb.StringProperty()
	given_name = ndb.StringProperty()
	gender = ndb.StringProperty()
	description = ndb.StringProperty()
	date_of_birth = ndb.StringProperty()
	language = ndb.StringProperty(default='ja')

	created_date = ndb.DateTimeProperty(auto_now_add=True)
	updated_date = ndb.DateTimeProperty(auto_now=True)

	@classmethod
	def getUserLanguage(cls, id_or_email, hl=None):
		user_info_dict = cls.getDict(id_or_email)
		if user_info_dict is None:
			return sateraito_inc.DEFAULT_LANGUAGE
		return user_info_dict['language']

	def _post_put_hook(self, future):
		UCFMDLUserInfo.clearInstanceCache(self.user_entry_id)
		UCFMDLUserInfo.clearInstanceCache(self.key.id())

	@classmethod
	def _pre_delete_hook(cls, key):
		UCFMDLUserInfo.clearInstanceCache(cls.user_entry_id)
		UCFMDLUserInfo.clearInstanceCache(key.id())

	@classmethod
	def getMemcacheKey(cls, id_or_email):
		return 'script=UCFMDLUserInfo-getUCFMDLUserInfo&id_or_email=' + str(id_or_email)

	@classmethod
	def clearInstanceCache(cls, id_or_email):
		memcache.delete(cls.getMemcacheKey(id_or_email))

	@classmethod
	def getDict(cls, id_or_email, auto_create=False):
		# check memcache
		memcache_key = cls.getMemcacheKey(id_or_email)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			logging.info('UCFMDLUserInfo.getDict: found and respond cache')
			return cached_dict

		# get data
		row = cls.getInstance(id_or_email, auto_create)
		if row is None:
			return None

		row_dict = row.to_dict()
		row_dict['id'] = row.key.id()

		# set to memcache
		memcache.set(memcache_key, row_dict, time=cls.NDB_MEMCACHE_TIMEOUT)

		return row_dict

	@classmethod
	def getInstance(cls, id_or_entry_id, auto_create=False):
		# get data
		user_info = cls.get_by_id(id_or_entry_id, memcache_timeout=cls.NDB_MEMCACHE_TIMEOUT)

		if user_info is None:
			q = cls.query()
			q = q.filter(cls.user_entry_id == id_or_entry_id)
			row_k = q.get(keys_only=True)
			if row_k is None:
				logging.info('UCFMDLUserInfo not found| auto_create=' + str(auto_create))
				if auto_create:
					user_info = cls()
					user_info.user_entry_id = id_or_entry_id
					user_info.language = sateraito_inc.DEFAULT_LANGUAGE
					user_info.put()
					return user_info
				else:
					return None
			user_info = cls.get_by_id(row_k.id(), memcache_timeout=cls.NDB_MEMCACHE_TIMEOUT)

		return user_info

	@classmethod
	def getUserName(cls, viewer_email):
		if viewer_email == '' or viewer_email is None:
			return ''
		q = cls.query()
		q.filter(cls.email == viewer_email)
		user_info = q.get()
		if user_info is None:
			return viewer_email
		return user_info.family_name + user_info.given_name

	@classmethod
	def getUserInfo(cls, viewer_email):
		return cls.getInstance(viewer_email)

	@classmethod
	def isDuppliceEmail(cls, email, user_entry_id=None):
		strOldNamespace = namespace_manager.get_namespace()
		namespace_manager.set_namespace('')

		# get data
		q = cls.query()
		q = q.filter(cls.email == email)
		q = q.filter(cls.user_entry_id != user_entry_id)
		row = q.get()

		namespace_manager.set_namespace(strOldNamespace)
		return row is not None

	@classmethod
	def addIfInfoNone(cls, user_entry_id, viewer_email, fullname, avatar_url, given_name, family_name, lang=sateraito_inc.DEFAULT_LANGUAGE):
		u_info_row = cls.getInstance(viewer_email)
		is_new_row = False

		email_lower = str(viewer_email)
		if u_info_row is None:
			u_info_row = cls()
			u_info_row.email = email_lower
			u_info_row.user_entry_id = user_entry_id
			u_info_row.avatar_url = avatar_url
			u_info_row.fullname = fullname
			u_info_row.family_name = given_name
			u_info_row.given_name = family_name
			u_info_row.language = lang
			u_info_row.put()

			is_new_row = True
		else:
			if u_info_row.avatar_blob_id is None:
				u_info_row.avatar_url = avatar_url
			u_info_row.language = lang
			u_info_row.put()

		return u_info_row, is_new_row

	@classmethod
	def addIfInfoNoneTypeFacebook(cls, user_entry_id, fullname, avatar_url, given_name, family_name, lang=sateraito_inc.DEFAULT_LANGUAGE):
		u_info_row = cls.getInstance(user_entry_id)
		is_new_row = False

		if u_info_row is None:
			u_info_row = cls()
			u_info_row.email = ''
			u_info_row.user_entry_id = user_entry_id
			u_info_row.avatar_url = avatar_url
			u_info_row.fullname = fullname
			u_info_row.family_name = given_name
			u_info_row.given_name = family_name
			u_info_row.language = lang
			u_info_row.put()

			is_new_row = True

		else:
			if u_info_row.avatar_blob_id is None:
				u_info_row.avatar_url = avatar_url
			u_info_row.language = lang
			u_info_row.put()

		return u_info_row, is_new_row

	@classmethod
	def addIfInfoNoneTypeTwitter(cls, user_entry_id, fullname, avatar_url, lang=sateraito_inc.DEFAULT_LANGUAGE):
		u_info_row = cls.getInstance(user_entry_id)
		is_new_row = False

		if u_info_row is None:
			u_info_row = cls()
			u_info_row.email = ''
			u_info_row.user_entry_id = user_entry_id
			u_info_row.avatar_url = avatar_url
			u_info_row.fullname = fullname
			u_info_row.language = lang
			u_info_row.put()

			is_new_row = True

		else:
			if u_info_row.avatar_blob_id is None:
				u_info_row.avatar_url = avatar_url
			u_info_row.language = lang
			u_info_row.put()

		return u_info_row, is_new_row

	@classmethod
	def addIfInfoNoneTypeLine(cls, user_entry_id, fullname, avatar_url, lang=sateraito_inc.DEFAULT_LANGUAGE):
		u_info_row = cls.getInstance(user_entry_id)
		is_new_row = False

		if u_info_row is None:
			u_info_row = cls()
			u_info_row.email = ''
			u_info_row.user_entry_id = user_entry_id
			u_info_row.avatar_url = avatar_url
			u_info_row.fullname = fullname
			u_info_row.language = lang
			u_info_row.put()

			is_new_row = True

		else:
			if u_info_row.avatar_blob_id is None:
				u_info_row.avatar_url = avatar_url
			u_info_row.language = lang
			u_info_row.put()

		return u_info_row, is_new_row

	@classmethod
	def getAvatarBlobByKey(cls, blob_key):
		q = cls.query()
		q = q.filter(cls.avatar_blob_id == blob_key)
		row_k = q.get()
		logging.info(str(row_k))
		return row_k

class UCFMDLTypeBook(UCFModel2):
	name = ndb.StringProperty()
	del_flag = ndb.BooleanProperty(default=False)

	type_parent_id = ndb.IntegerProperty(default=None)

	created_date = ndb.DateTimeProperty(auto_now_add=True)
	updated_date = ndb.DateTimeProperty(auto_now=True)

	def _pre_put_hook(self):
		""" set default value if property is None
    """
		self.clearInstanceCache(self.key.id())

	@classmethod
	def getMemcacheKey(cls, type_book_id):
		return 'script=UCFMDLTypeBook-getUCFMDLTypeBook&type_book_id=' + str(type_book_id)

	@classmethod
	def getAllTypeMemcacheKey(cls, without_category, is_admin, del_flag):
		return 'script=UCFMDLTypeBook-getAllType&without_category=' + str(without_category) + '&is_admin=' + str(is_admin) + '&del_flag=' + str(del_flag)

	@classmethod
	def getAllCategoryMemcacheKey(cls, type_book_id="", is_admin=False, del_flag=False):
		return 'script=UCFMDLTypeBook-getAllCategory&type_book_id=' + str(type_book_id) + '&type_book_id=' + str(type_book_id) + '&del_flag=' + str(del_flag)

	@classmethod
	def clearInstanceCache(cls, type_book_id):
		if type_book_id is None:
			return
		memcache.delete(cls.getMemcacheKey(type_book_id))

	@classmethod
	def clearAllTypeInstanceCache(cls):
		memcache.delete(cls.getAllTypeMemcacheKey(True, True, True))

		memcache.delete(cls.getAllTypeMemcacheKey(False, True, True))
		memcache.delete(cls.getAllTypeMemcacheKey(True, False, True))
		memcache.delete(cls.getAllTypeMemcacheKey(True, True, False))

		memcache.delete(cls.getAllTypeMemcacheKey(False, False, True))
		memcache.delete(cls.getAllTypeMemcacheKey(False, True, False))
		memcache.delete(cls.getAllTypeMemcacheKey(True, False, False))

		memcache.delete(cls.getAllTypeMemcacheKey(False, False, False))

	@classmethod
	def clearAllCategoryInstanceCache(cls, type_book_id=""):
		memcache.delete(cls.getAllCategoryMemcacheKey(type_book_id, True, False))
		memcache.delete(cls.getAllCategoryMemcacheKey(type_book_id, True, True))
		memcache.delete(cls.getAllCategoryMemcacheKey(type_book_id, False, False))
		memcache.delete(cls.getAllCategoryMemcacheKey(type_book_id, False, True))

	@classmethod
	def getDict(cls, type_book_id):
		# check memcache
		memcache_key = cls.getMemcacheKey(type_book_id)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			# logging.info('Categories.getDict: found and respond cache')
			return cached_dict
		# get data
		row = cls.getInstance(type_book_id)
		if row is None:
			return None
		row_dict = row.to_dict()
		row_dict['id'] = row.key.id()
		# set to memcache
		memcache.set(memcache_key, row_dict, time=cls.NDB_MEMCACHE_TIMEOUT)
		return row_dict

	@classmethod
	def getInstance(cls, type_book_id):
		# get datastore data
		# first try: get by key
		return cls.get_by_id(type_book_id, memcache_timeout=cls.NDB_MEMCACHE_TIMEOUT)

	@classmethod
	def getKeyTypeByName(cls, name, type_parent_id=None):
		query = cls.query()
		query = query.filter(cls.name == name)
		query = query.filter(cls.type_parent_id == type_parent_id)
		query = query.filter(cls.del_flag == False)

		logging.info("getKeyTypeByName=" + str(query.get(keys_only=True)))
		return query.get(keys_only=True)

	@classmethod
	def getAll(cls):
		data = []

		query = cls.query()
		for row in query:
			data.append({
				'id': row.key.id(),
				'name': row.name,
				'type_parent_id': row.type_parent_id,
			})

		return data

	@classmethod
	def getAllType(cls, without_category=True, del_flag=False, is_admin=False, timezone=sateraito_inc.DEFAULT_TIMEZONE):
		# check memcache
		memcache_key = cls.getAllTypeMemcacheKey(without_category, is_admin, del_flag)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			logging.info('Categories.getAllType: found and respond cache')
			return cached_dict

		data = []
		query = cls.query()
		query = query.filter(cls.type_parent_id == None)
		query = query.filter(cls.del_flag == del_flag)
		query = query.order(cls.name)
		results = query.fetch()

		for row in results:
			type_book_id = row.key.id()
			param = {
				'id': type_book_id,
				'name': row.name,
				'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(row.created_date, timezone)),
				'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(row.created_date, timezone)),
			}

			# if is_admin:
			# param['created_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(row.created_date, timezone))
			# param['updated_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(row.created_date, timezone))

			query_category = cls.query()
			query_category = query_category.filter(cls.type_parent_id == type_book_id)
			query_category = query_category.filter(cls.del_flag == del_flag)
			if without_category:
				param['total_category'] = query_category.count()

			else:
				param['categories'] = []
				category_rows = query_category.fetch()
				for cat_row in category_rows:
					cat_book_id = cat_row.key.id()

					query_book = UCFMDLBook.query()
					query_book = query_book.filter(UCFMDLBook.category_book_id == cat_book_id)
					query_book = query_book.filter(UCFMDLBook.del_flag == del_flag)
					total_book = query_book.count()

					param['categories'].append({
						'id': cat_book_id,
						'total_book': total_book,
						'name': cat_row.name,
						'type_parent_id': cat_row.type_parent_id,
						'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(cat_row.created_date, timezone)),
						'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(cat_row.created_date, timezone)),
					})

			query_book = UCFMDLBook.query()
			query_book = query_book.filter(UCFMDLBook.type_book_id == type_book_id)
			query_book = query_book.filter(UCFMDLBook.del_flag == del_flag)
			param['total_book'] = query_book.count()

			data.append(param)

		# set to memcache
		memcache.set(memcache_key, data, time=cls.NDB_MEMCACHE_TIMEOUT)

		return data

	@classmethod
	def getCategories(cls, type_book_id="", del_flag=False, is_admin=False, timezone=sateraito_inc.DEFAULT_TIMEZONE):
		# check memcache
		memcache_key = cls.getAllCategoryMemcacheKey(type_book_id, is_admin, del_flag)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			logging.info('Categories.getCategories: found and respond cache')
			return cached_dict

		data = []

		query = cls.query()
		if type_book_id != "":
			query = query.filter(cls.type_parent_id == type_book_id).order(cls.type_parent_id, cls.name)
		else:
			query = query.filter(cls.type_parent_id != None).order(cls.type_parent_id, cls.name)

		if del_flag is not None:
			query = query.filter(cls.del_flag == del_flag)
		query = query.order(cls.name)

		for row in query:
			category_book_id = row.key.id()

			param = {
				'id': category_book_id,
				'name': row.name,
				'type_parent_id': row.type_parent_id,
				'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(row.created_date, timezone)),
				'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(row.created_date, timezone)),
			}

			# if is_admin:
			# param['created_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(row.created_date, timezone))
			# param['updated_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(row.created_date, timezone))

			type_book_dict = UCFMDLTypeBook.getDict(row.type_parent_id)
			param['type_parent_name'] = type_book_dict['name']

			query_book = UCFMDLBook.query()
			query_book = query_book.filter(UCFMDLBook.category_book_id == category_book_id)
			query_book = query_book.filter(UCFMDLBook.del_flag == del_flag)
			param['total_book'] = query_book.count()

			data.append(param)

		# set to memcache
		memcache.set(memcache_key, data, time=cls.NDB_MEMCACHE_TIMEOUT)

		return data

class UCFMDLBook(UCFModel2):
	creator_id = ndb.StringProperty()
	del_flag = ndb.BooleanProperty(default=False)

	total_join = ndb.IntegerProperty(default=0)
	popular = ndb.IntegerProperty(default=0)
	rate_star = ndb.IntegerProperty(default=0)
	total_comment = ndb.IntegerProperty(default=0)
	feedback_summary = ndb.StringProperty()

	status = ndb.StringProperty()
	share_for = ndb.StringProperty(repeated=True)

	type_book_id = ndb.IntegerProperty()
	type_book_name = ndb.StringProperty()
	category_book_id = ndb.IntegerProperty()
	category_book_name = ndb.StringProperty()

	title = ndb.StringProperty()
	book_cover = ndb.StringProperty()
	images = ndb.TextProperty()
	summary = ndb.StringProperty()
	characters = ndb.TextProperty()
	chapters = ndb.TextProperty()

	created_date = ndb.DateTimeProperty(auto_now_add=True)
	updated_date = ndb.DateTimeProperty(auto_now=True)

	def _pre_put_hook(self):
		""" set default value if property is None
    """
		self.clearInstanceCache(self.key.id())

	@classmethod
	def getMemcacheKey(cls, book_id):
		return 'script=UCFMDLBook-getUCFMDLBook&book_id=' + str(book_id)
	
	@classmethod
	def clearInstanceCache(cls, book_id):
		if book_id is None:
			return
		memcache.delete(cls.getMemcacheKey(book_id))

	@classmethod
	def getDict(cls, book_id):
		# check memcache
		memcache_key = cls.getMemcacheKey(book_id)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			return cached_dict
		# get data
		row = cls.getInstance(book_id)
		if row is None:
			return None
		row_dict = row.to_dict()
		row_dict['id'] = row.key.id()
		# set to memcache
		memcache.set(memcache_key, row_dict, time=cls.NDB_MEMCACHE_TIMEOUT)
		return row_dict

	@classmethod
	def getInstance(cls, book_id):
		# get datastore data
		# first try: get by key
		return cls.get_by_id(book_id, memcache_timeout=cls.NDB_MEMCACHE_TIMEOUT)

class UCFMDLUserStories(UCFModel2):
	creator_id = ndb.StringProperty()
	book_id = ndb.StringProperty()

	started_flag = ndb.BooleanProperty(default=False)
	ended_flag = ndb.BooleanProperty(default=False)
	history_flag = ndb.BooleanProperty(default=False)
	processing_flag = ndb.BooleanProperty(default=False)
	del_flag = ndb.BooleanProperty(default=False)

	join_with = ndb.TextProperty()
	summary_request_for_gpt = ndb.TextProperty()
	chapters_total = ndb.IntegerProperty(default=0)

	created_date = ndb.DateTimeProperty(auto_now_add=True)
	updated_date = ndb.DateTimeProperty(auto_now=True)

	def _pre_put_hook(self):
		""" set default value if property is None
    """
		self.clearInstanceCache(self.key.id())

	@classmethod
	def getDateTimeTypes(cls):
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す '''
		return ['created_date', 'updated_date']

	@classmethod
	def getListTypes(cls):
		u''' リスト型フィールドがあればここでフィールド名のリストを返す '''
		return []

	@classmethod
	def getMemcacheKey(cls, user_story_id):
		return 'script=UCFMDLUserStories-getUCFMDLUserStories&user_story_id=' + str(user_story_id)

	@classmethod
	def getMemcacheKey2(cls, book_id, history_flag, creator_id, del_flag=False):
		return 'script=UCFMDLUserStories-getUCFMDLUserStories2&book_id=%s&history_flag=%s&creator_id=%s&del_flag=%s' % (book_id, history_flag, creator_id, str(del_flag))

	@classmethod
	def getMemcacheListHistoryKey(cls, book_id, creator_id, del_flag=False):
		return 'script=UCFMDLUserStories-getListHistoryUserStories&book_id=%s&history_flag=%s&creator_id=%s&del_flag=%s' % (book_id, 'true', creator_id, str(del_flag))

	@classmethod
	def clearInstanceCache(cls, user_story_id):
		if user_story_id is None:
			return

		row_dict = cls.getDict(user_story_id)
		if row_dict:
			memcache.delete(cls.getMemcacheKey2(row_dict['book_id'], True, row_dict['creator_id']))
			memcache.delete(cls.getMemcacheKey2(row_dict['book_id'], False, row_dict['creator_id']))
			memcache.delete(cls.getMemcacheListHistoryKey(row_dict['book_id'], row_dict['creator_id']))

		memcache.delete(cls.getMemcacheKey(user_story_id))

	@classmethod
	def getDict(cls, user_story_id):
		# check memcache
		memcache_key = cls.getMemcacheKey(user_story_id)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			return cached_dict
		# get data
		row = cls.getInstance(user_story_id)
		if row is None:
			return None
		row_dict = row.to_dict()
		row_dict['id'] = row.key.id()
		# set to memcache
		memcache.set(memcache_key, row_dict, time=cls.NDB_MEMCACHE_TIMEOUT)
		return row_dict

	@classmethod
	def getInstance(cls, user_story_id):
		# get datastore data
		# first try: get by key
		return cls.get_by_id(user_story_id, memcache_timeout=cls.NDB_MEMCACHE_TIMEOUT)

	@classmethod
	def getInstance2(cls, book_id, history_flag, creator_id, del_flag=False):
		q = cls.query()
		q = q.filter(cls.book_id == book_id)
		q = q.filter(cls.history_flag == history_flag)
		q = q.filter(cls.creator_id == creator_id)
		if del_flag is not None:
			q = q.filter(cls.del_flag == del_flag)
		return q.get()

	@classmethod
	def getDict2(cls, book_id, history_flag, creator_id, del_flag=False):
		# check memcache
		memcache_key = cls.getMemcacheKey2(book_id, history_flag, creator_id, del_flag=del_flag)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			logging.info('UCFMDLUserStories.getDict2: found and respond cache')
			return cached_dict

		# get data
		row = cls.getInstance2(book_id, history_flag, creator_id, del_flag=del_flag)
		if row is None:
			return None

		row_dict = row.to_dict()
		row_dict['id'] = row.key.id()

		# set to memcache
		memcache.set(memcache_key, row_dict, time=cls.NDB_MEMCACHE_TIMEOUT)

		return row_dict

	@classmethod
	def getListHistoryInstance(cls, book_id, creator_id, del_flag=False):
		q = cls.query()
		q = q.filter(cls.book_id == book_id)
		q = q.filter(cls.history_flag == True)
		q = q.filter(cls.creator_id == creator_id)
		if del_flag is not None:
			q = q.filter(cls.del_flag == del_flag)
		q.order(-cls.updated_date)
		return q.fetch()

	@classmethod
	def getListHistoryDict(cls, book_id, creator_id, del_flag=False):
		# check memcache
		memcache_key = cls.getMemcacheListHistoryKey(book_id, creator_id, del_flag=del_flag)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			logging.info('UCFMDLUserStories.getListHistoryDict: found and respond cache')
			return cached_dict

		data_list = []
		# get data
		rows = cls.getListHistoryInstance(book_id, creator_id, del_flag=del_flag)
		for row in rows:
			row_dict = row.to_dict()
			row_dict['id'] = row.key.id()
			data_list.append(row_dict)

		# set to memcache
		memcache.set(memcache_key, data_list, time=cls.NDB_MEMCACHE_TIMEOUT)

		return data_list

class UCFMDLUserChapters(UCFModel2):
	creator_id = ndb.StringProperty()
	user_story_id = ndb.StringProperty()
	book_id = ndb.StringProperty()

	status = ndb.StringProperty(default='')
	del_flag = ndb.BooleanProperty(default=False)

	is_good = ndb.BooleanProperty()
	comment = ndb.StringProperty()

	title = ndb.StringProperty()
	idea = ndb.StringProperty()
	content = ndb.TextProperty()
	user_content = ndb.TextProperty()
	assistant_content = ndb.TextProperty()
	chapter_number = ndb.IntegerProperty()

	created_date = ndb.DateTimeProperty(auto_now_add=True)
	updated_date = ndb.DateTimeProperty(auto_now=True)

	def _pre_put_hook(self):
		""" set default value if property is None
    """
		self.clearInstanceCache(self.key.id())

	@classmethod
	def getDateTimeTypes(cls):
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す '''
		return ['created_date', 'updated_date']

	@classmethod
	def getListTypes(cls):
		u''' リスト型フィールドがあればここでフィールド名のリストを返す '''
		return []

	@classmethod
	def getMemcacheKey(cls, user_chapter_id):
		return 'script=UCFMDLUserChapters-getUCFMDLUserChapters&user_chapter_id=' + str(user_chapter_id)

	@classmethod
	def getMemcacheListKey(cls, book_id, user_story_id):
		logging.info('getMemcacheListKey="script=UCFMDLUserChapters-getListUCFMDLUserChapters&book_id=%s&user_story_id=%s"' % (book_id, user_story_id))
		return 'script=UCFMDLUserChapters-getListUCFMDLUserChapters&book_id=%s&user_story_id=%s' % (book_id, user_story_id)

	@classmethod
	def clearInstanceCache(cls, user_chapter_id):
		if user_chapter_id is None:
			return
		memcache.delete(cls.getMemcacheKey(user_chapter_id))

	@classmethod
	def clearListInstanceCache(cls, book_id, user_story_id):
		logging.info("clearListInstanceCache=" + str(cls.getMemcacheListKey(book_id, user_story_id)))
		memcache.delete(cls.getMemcacheListKey(book_id, user_story_id))

	@classmethod
	def getDict(cls, user_chapter_id, timezone=sateraito_inc.DEFAULT_TIMEZONE):
		# check memcache
		memcache_key = cls.getMemcacheKey(user_chapter_id)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			return cached_dict
		# get data
		row = cls.getInstance(user_chapter_id)
		if row is None:
			return None
		row_dict = row.to_dict()
		row_dict['id'] = row.key.id()
		row_dict['created_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(row_dict['created_date'], timezone))
		row_dict['updated_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(row_dict['updated_date'], timezone))

		# set to memcache
		memcache.set(memcache_key, row_dict, time=cls.NDB_MEMCACHE_TIMEOUT)
		return row_dict

	@classmethod
	def getInstance(cls, user_chapter_id):
		# get datastore data
		# first try: get by key
		return cls.get_by_id(user_chapter_id, memcache_timeout=cls.NDB_MEMCACHE_TIMEOUT)

	@classmethod
	def getInstanceList(cls, book_id, user_story_id):
		q = cls.query()
		q = q.filter(cls.book_id == book_id)
		q = q.filter(cls.user_story_id == user_story_id)
		q = q.order(cls.chapter_number)
		return q.fetch()

	@classmethod
	def getDictList(cls, book_id, user_story_id, timezone=sateraito_inc.DEFAULT_TIMEZONE):
		# check memcache
		memcache_key = cls.getMemcacheListKey(book_id, user_story_id)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			logging.info('UCFMDLUserChapters.getDictList: found and respond cache')
			return cached_dict

		data_list = []
		# get data
		rows = cls.getInstanceList(book_id, user_story_id)
		for row in rows:
			row_dict = row.to_dict()

			row_dict['id'] = row.key.id()
			row_dict['created_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(row_dict['created_date'], timezone))
			row_dict['updated_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(row_dict['updated_date'], timezone))
			data_list.append(row_dict)

		# set to memcache
		memcache.set(memcache_key, data_list, time=cls.NDB_MEMCACHE_TIMEOUT)

		return data_list

class UCFMDLStoriesUsersJoined(UCFModel2):
	user_id = ndb.StringProperty()
	book_id = ndb.StringProperty()
	count_joined = ndb.IntegerProperty(default=0)

	del_flag = ndb.BooleanProperty(default=False)

	created_date = ndb.DateTimeProperty(auto_now_add=True)
	updated_date = ndb.DateTimeProperty(auto_now=True)

	@classmethod
	def getListByBookIdMemcacheKey(cls, book_id):
		return 'script=UCFMDLFeedbackBookUsers-getListByBookId&book_id=%s' % (str(book_id))

	@classmethod
	def clearListByBookInstanceCache(cls, book_id):
		memcache.delete(cls.getListByBookIdMemcacheKey(book_id))

	@classmethod
	def getListByBookId(cls, book_id):
		q = cls.query()
		q = q.filter(cls.book_id == book_id)
		q = q.order(-cls.created_date)
		return q.fetch()

	@classmethod
	def getDictListByBookId(cls, book_id, without_user_info=False, timezone=None):
		# check memcache
		memcache_key = cls.getListByBookIdMemcacheKey(book_id)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			if not without_user_info:
				for index, row_dict in enumerate(cached_dict):
					user_dict = UCFMDLUserInfo.getDict(row_dict['user_id'])
					cached_dict[index]['user_info'] = {
                        'id': user_dict['id'],
                        'email': user_dict['email'],
                        'avatar_url': user_dict['avatar_url'],
                        'nickname': user_dict['nickname'],
                        'fullname': user_dict['fullname'],
                        'language': user_dict['language'],
                    }
			logging.info('UCFMDLStoriesUsersJoined.getDictListByBookId(%s): found and respond cache' % (str(book_id)))
			return cached_dict

		data = []
		results = cls.getListByBookId(book_id)
		for row in results:
			row_dict = row.to_dict()
			row_dict['id'] = row.key.id()
			
			if not without_user_info:
				user_dict = UCFMDLUserInfo.getDict(row_dict['user_id'])
				row_dict['user_info'] = {
                    'id': user_dict['id'],
                    'email': user_dict['email'],
                    'avatar_url': user_dict['avatar_url'],
                    'nickname': user_dict['nickname'],
                    'fullname': user_dict['fullname'],
                    'language': user_dict['language'],
                }
			
			if timezone:
				row_dict['created_date'] = UcfUtil.getLocalTime(row_dict['created_date'], timezone).strftime('%Y/%m/%d %H:%M')
				row_dict['updated_date'] = UcfUtil.getLocalTime(row_dict['updated_date'], timezone).strftime('%Y/%m/%d %H:%M')

			data.append(row_dict)
	
		# set to memcache
		memcache.set(memcache_key, data, time=cls.NDB_MEMCACHE_TIMEOUT)

		return data

class UCFMDLFavoritesBookUsers(UCFModel2):
	user_id = ndb.StringProperty()
	book_id = ndb.StringProperty()

	del_flag = ndb.BooleanProperty(default=False)

	created_date = ndb.DateTimeProperty(auto_now_add=True)
	updated_date = ndb.DateTimeProperty(auto_now=True)

	def _post_put_hook(self, future):
		if self is not None:
			UCFMDLFavoritesBookUsers.clearInstanceCache(self.user_id, self.book_id)

	@classmethod
	def getMemcacheKey(cls, user_id, book_id):
		return 'script=UCFMDLFavoritesBookUsers&user_id=' + str(user_id) + '&book_id=' + str(book_id)

	@classmethod
	def clearInstanceCache(cls, user_id, book_id):
		memcache.delete(cls.getMemcacheKey(user_id, book_id))

	@classmethod
	def getInstance(cls, favorite_id):
		return cls.get_by_id(favorite_id, memcache_timeout=cls.NDB_MEMCACHE_TIMEOUT)

	@classmethod
	def get_dict(cls, user_id, book_id):
		# check memcache
		memcache_key = cls.getMemcacheKey(user_id, book_id)
		logging.info(memcache_key)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			logging.info('UCFMDLFavoritesBookUsers.getDict: found and respond cache')
			logging.info(cached_dict)
			return cached_dict

		q = cls.query()
		q = q.filter(cls.user_id == user_id)
		q = q.filter(cls.book_id == book_id)
		entry = q.get()
		if entry:
			# set to memcache
			row_dict = {
				'user_id': entry.user_id,
				'book_id': entry.book_id
			}
			memcache.set(memcache_key, row_dict, time=cls.NDB_MEMCACHE_TIMEOUT)
			return row_dict

		cls.clearInstanceCache(user_id, book_id)
		return None

	@classmethod
	def delete(cls, user_id, book_id):
		q = cls.query()
		q = q.filter(cls.user_id == user_id)
		q = q.filter(cls.book_id == book_id)
		entry = q.get()
		logging.info('entry:'+str(entry))
		if entry:
			logging.info('delete')
			entry.key.delete()
			cls.clearInstanceCache(user_id, book_id)
			return True
		return False

	@classmethod
	def isFavorite(cls, email, book_id):
		row = cls.get_dict(email, book_id)
		if row is not None:
			return True
		return False

class UCFMDLFeedbackBookUsers(UCFModel2):
	user_id = ndb.StringProperty()
	book_id = ndb.StringProperty()
	user_story_id = ndb.StringProperty()
	type_feedback = ndb.StringProperty()

	is_good = ndb.BooleanProperty()
	chapter_id = ndb.StringProperty()

	rating = ndb.IntegerProperty()
	comment = ndb.StringProperty()

	del_flag = ndb.BooleanProperty(default=False)

	created_date = ndb.DateTimeProperty(auto_now_add=True)
	updated_date = ndb.DateTimeProperty(auto_now=True)

	@classmethod
	def getById(cls, feedback_id):
		return cls.get_by_id(feedback_id, memcache_timeout=cls.NDB_MEMCACHE_TIMEOUT)

	@classmethod
	def getMemcacheKey(cls, user_id, user_story_id, book_id, type_feedback):
		return 'script=UCFMDLFeedbackBookUsers-getUCFMDLFeedbackBookUsers&user_id=%s&user_story_id=%s&book_id=%s&type_feedback=%s' % (str(user_id), str(user_story_id), str(book_id), str(type_feedback))

	@classmethod
	def clearInstanceCache(cls, user_id, user_story_id, book_id, type_feedback):
		memcache.delete(cls.getMemcacheKey(user_id, user_story_id, book_id, type_feedback))

	@classmethod
	def getInstance(cls, user_id, user_story_id, book_id, type_feedback, chapter_id=None):
		q = cls.query()
		q = q.filter(cls.user_id == user_id)
		q = q.filter(cls.book_id == book_id)
		q = q.filter(cls.user_story_id == user_story_id)
		q = q.filter(cls.type_feedback == type_feedback)
		if chapter_id:
			q = q.filter(cls.chapter_id == chapter_id)
		return q.get()

	@classmethod
	def getDict(cls, user_id, user_story_id, book_id, type_feedback):
		# check memcache
		memcache_key = cls.getMemcacheKey(user_id, user_story_id, book_id, type_feedback)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			return cached_dict

		# get data
		row = cls.getInstance(user_id, user_story_id, book_id, type_feedback)
		if row is None:
			return None

		row_dict = row.to_dict()
		row_dict['id'] = row.key.id()

		# set to memcache
		memcache.set(memcache_key, row_dict, time=cls.NDB_MEMCACHE_TIMEOUT)

		return row_dict


	@classmethod
	def getListByBookIdMemcacheKey(cls, book_id, type_feedback, del_flag=False):
		return 'script=UCFMDLFeedbackBookUsers-getListByBookId&book_id=%s&type_feedback=%s&del_flag=%s' % (str(book_id), str(type_feedback), str(del_flag))

	@classmethod
	def clearListByBookInstanceCache(cls, book_id, type_feedback):
		memcache.delete(cls.getListByBookIdMemcacheKey(book_id, type_feedback))

	@classmethod
	def getListByBookId(cls, book_id, type_feedback, del_flag=None):
		q = cls.query()
		q = q.filter(cls.book_id == book_id)
		q = q.filter(cls.type_feedback == type_feedback)
		if del_flag is not None:
			q = q.filter(cls.del_flag == del_flag)
		q = q.order(-cls.updated_date)
		return q.fetch()

	@classmethod
	def getDictListByBookId(cls, book_id, type_feedback, del_flag=False):
		# check memcache
		memcache_key = cls.getListByBookIdMemcacheKey(book_id, type_feedback)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			logging.info('UCFMDLFeedbackBookUsers.getDictListByBookId(%s, %s): found and respond cache' % (str(book_id), str(type_feedback)))
			return cached_dict

		data = []
		results = cls.getListByBookId(book_id, type_feedback, del_flag)
		for row in results:
			row_dict = row.to_dict()
			row_dict['id'] = row.key.id()

			data.append(row_dict)
	
		# set to memcache
		memcache.set(memcache_key, data, time=cls.NDB_MEMCACHE_TIMEOUT)

		return data


	@classmethod
	def getByBookIdUserId(cls, book_id, user_id, type_feedback, del_flag=None):
		q = cls.query()
		q = q.filter(cls.book_id == book_id)
		q = q.filter(cls.user_id == user_id)
		q = q.filter(cls.type_feedback == type_feedback)
		if del_flag is not None:
			q = q.filter(cls.del_flag == del_flag)
		return q.get()

class UCFMDLUserShareStories(UCFModel2):
	user_id = ndb.StringProperty()
	message = ndb.StringProperty()
	user_id_shared = ndb.StringProperty()

	del_flag = ndb.BooleanProperty(default=False)

	type_share = ndb.StringProperty()
	book_id = ndb.StringProperty()
	user_story_id = ndb.StringProperty()
	user_chapter_id = ndb.StringProperty()
	
	created_date = ndb.DateTimeProperty(auto_now_add=True)
	updated_date = ndb.DateTimeProperty(auto_now=True)

	def _pre_put_hook(self):
		""" set default value if property is None
    """
		self.clearInstanceCache(self.key.id())

	@classmethod
	def getMemcacheKey(cls, user_share_id):
		return 'script=UCFMDLUserShareStories-getUCFMDLUserShareStories&user_share_id=' + str(user_share_id)

	@classmethod
	def clearInstanceCache(cls, user_share_id):
		if user_share_id is None:
			return
		memcache.delete(cls.getMemcacheKey(user_share_id))

	@classmethod
	def getDict(cls, user_share_id):
		# check memcache
		memcache_key = cls.getMemcacheKey(user_share_id)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			return cached_dict

		# get data
		row = cls.getInstance(user_share_id)
		if row is None:
			return None

		row_dict = row.to_dict()
		row_dict['id'] = row.key.id()

		# set to memcache
		memcache.set(memcache_key, row_dict, time=cls.NDB_MEMCACHE_TIMEOUT)
		return row_dict

	@classmethod
	def getInstance(cls, user_share_id):
		return cls.get_by_id(user_share_id, memcache_timeout=cls.NDB_MEMCACHE_TIMEOUT)

	@classmethod
	def getStoriesSharedFor(cls, viewer_id, del_flag=False, type_share=None, limit=None):
		logging.info("UCFMDLUserShareStories.getStoriesSharedFor viewer_id=" + viewer_id)
		query = cls.query()
		query = query.filter(cls.user_id_shared == viewer_id)
		if type_share:
			query = query.filter(cls.type_share == type_share)
		query = query.filter(cls.del_flag == del_flag)

		query = query.order(-cls.updated_date)

		if limit:
			results = query.fetch(limit=limit)
		else:
			results = query.fetch()

		return results

	@classmethod
	def getMemcacheKeyListUsersShared(cls, book_id, user_id, user_story_id=None, user_chapter_id=None, del_flag=False, type_share=None):
		return 'script=UCFMDLUserShareStories-getListUsersShared&book_id={0}user_id={1}user_story_id={2}user_chapter_id={3}del_flag={4}type_share={5}' \
			.format(book_id, user_id, user_story_id, user_chapter_id, del_flag, type_share)

	@classmethod
	def clearInstanceListUsersSharedCache(cls, book_id, user_id, user_story_id=None, user_chapter_id=None, del_flag=False, type_share=None):
		logging.info('clearInstanceListUsersSharedCache = "%s"' % cls.getMemcacheKeyListUsersShared(book_id, user_id, user_story_id, user_chapter_id, del_flag, type_share))
		memcache.delete(cls.getMemcacheKeyListUsersShared(book_id, user_id, user_story_id, user_chapter_id, del_flag, type_share))

	@classmethod
	def getListUsersShared(cls, book_id, user_id, user_story_id=None, user_chapter_id=None, del_flag=False, type_share=None, limit=None):
		memcache_key = cls.getMemcacheKeyListUsersShared(book_id, user_id, user_story_id, user_chapter_id, del_flag, type_share)

		if limit is None:
			# check memcache
			cached_dict = memcache.get(memcache_key)
			logging.info('getMemcacheKeyListUsersShared = "%s"' % memcache_key)
			if cached_dict is not None:
				logging.info('UCFMDLUserShareStories.getListUsersShared: found and respond cache')
				return cached_dict

		logging.info("UCFMDLUserShareStories.getListUsersShared book_id=" + book_id)
		query = cls.query()
		query = query.filter(cls.book_id == book_id)
		query = query.filter(cls.user_id == user_id)
		query = query.filter(cls.del_flag == del_flag)
		query = query.filter(cls.type_share == type_share)

		if type_share == sateraito_func.KEY_TYPE_STORY_SHARE:
			query = query.filter(cls.user_story_id == user_story_id)
		elif type_share == sateraito_func.KEY_TYPE_CHAPTER_SHARE:
			query = query.filter(cls.user_chapter_id == user_chapter_id)

		query = query.order(-cls.updated_date)

		shared_users = []

		if limit:
			results = query.fetch(limit=limit)
		else:
			results = query.fetch()

		for item in results:
			user_dict = UCFMDLUserInfo.getDict(item.user_id_shared)
			if user_dict:
				shared_users.append({
					'shared_user_id': item.key.id(),
					'id': user_dict['id'],
					'email': user_dict['email'],
					'avatar_url': user_dict['avatar_url'],
					'fullname': user_dict['fullname'],
					'nickname': user_dict['nickname'],
					'family_name': user_dict['family_name'],
					'given_name': user_dict['given_name'],
					'gender': user_dict['gender'],
				})

		if limit is None:
			# set to memcache
			memcache.set(memcache_key, shared_users, time=cls.NDB_MEMCACHE_TIMEOUT)

		return shared_users
	
class UCFMDLKeyRegisterEmail(UCFModel2):

	email = ndb.StringProperty()
	register_token = ndb.StringProperty()
	is_revoked = ndb.IntegerProperty(default=False)
	expire_date = ndb.DateTimeProperty()

	date_created = ndb.DateTimeProperty(auto_now_add=True)
	date_updated = ndb.DateTimeProperty(auto_now=True)

	@classmethod
	def create_register_token(cls, email, expire_seconds=REGISTER_TOKEN_EXPIRE_SECONDS, token_length=REGISTER_TOKEN_LENGTH):
		register_token = None
		while True:
			# register_token = UcfUtil.guid()
			# more secured method
			register_token = ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(token_length))
			entry = cls.get_by_id(register_token)
			if not entry:
				break
		
		entry = cls(id=register_token)
		entry.email = email
		entry.register_token = register_token
		entry.expire_date = datetime.datetime.utcnow().replace(tzinfo=None) + datetime.timedelta(seconds=expire_seconds)

		entry_key = entry.put()

		entry_created = entry_key.get()
		return entry_created.register_token

	@classmethod
	def refresh_register_token(cls, register_token, expire_seconds=REGISTER_TOKEN_EXPIRE_SECONDS):
		entry = cls.get_by_id(register_token)
		if not entry:
			return False
		# entry.expire_seconds = expire_seconds
		entry.expire_date = datetime.datetime.utcnow().replace(tzinfo=None) + datetime.timedelta(seconds=expire_seconds)
		# entry.is_revoked = False

		entry.put()

		return True

	@classmethod
	def revoke_register_token(cls, register_token):
		entry = cls.get_by_id(register_token)
		if not entry:
			return False
		entry.is_revoked = True

		entry.put()

		return True

	@classmethod
	def get_register_token(cls, register_token):
		entry = cls.get_by_id(register_token)
		if not entry:
			return

		entry_dict = entry.to_dict()

		return entry_dict

	@classmethod
	def check_register_token(cls, register_token):
		entry = cls.get_by_id(register_token)
		if not entry:
			return False, None

		if entry.is_revoked:
			return False, None

		if entry.expire_date <= datetime.datetime.utcnow().replace(tzinfo=None):
			return False, None

		return True, entry

	@classmethod
	def clear_expired_register_tokens(cls):
		now_date = datetime.datetime.utcnow().replace(tzinfo=None)
		q = cls.query()
		q = q.filter(cls.expire_date <= now_date)

		# keys = q.iter(keys_only=True)
		# for key in keys:
		#   key.delete()

		# keys = q.iter(keys_only=True)
		# ndb.delete_multi(keys)

		while True:
			keys = q.iter(keys_only=True, limit=200)
			if not keys:
				break
			ndb.delete_multi(keys)

class UCFMDLUserConfig(UCFModel2):
	unique_id = ndb.StringProperty(required=True)
	user_id = ndb.StringProperty()

	gpt_api_key = ndb.StringProperty()

	theme_config = ndb.TextProperty(default='{}')

	date_created = ndb.DateTimeProperty(auto_now_add=True)
	date_changed = ndb.DateTimeProperty(auto_now=True)

	def getNumberTypes():
		u''' 数値型フィールドがあればここでフィールド名のリストを返す '''
		return []
	getNumberTypes = staticmethod(getNumberTypes)

	def getDateTimeTypes():
		u''' DateTime型フィールドがあればここでフィールド名のリストを返す '''
		return ['date_created', 'date_changed']
	getDateTimeTypes = staticmethod(getDateTimeTypes)

	def getBooleanTypes():
		u''' Bool型フィールドがあればここでフィールド名のリストを返す '''
		return ['enable_typping_animation', 'show_dashboard']
	getBooleanTypes = staticmethod(getBooleanTypes)

	def put(self):
		ndb.Model.put(self)

	def _post_put_hook(self, future):
		if self is not None:
			UCFMDLUserConfig.clearInstanceCache(self.user_id)

	@classmethod
	def _pre_delete_hook(cls, key):
		row = key.get()
		if row is not None:
			cls.clearInstanceCache(row.user_id)

	@classmethod
	def getMemcacheKey(cls, user_id):
		return 'script=UCFMDLUserConfig&user_id=' + str(user_id)

	@classmethod
	def clearInstanceCache(cls, user_id):
		memcache.delete(cls.getMemcacheKey(user_id))

	@classmethod
	def getInstance(cls):
		return cls()

	@classmethod
	def get_dict(cls, uid, timezone=sateraito_inc.DEFAULT_TIMEZONE):
		# check memcache
		memcache_key = cls.getMemcacheKey(uid)
		logging.info(memcache_key)
		cached_dict = memcache.get(memcache_key)
		if cached_dict is not None:
			logging.info('UCFMDLUserConfig.getDict: found and respond cache')
			logging.info(cached_dict)
			return cached_dict

		q = cls.query()
		q = q.filter(cls.user_id == uid)
		entry = q.get()
		if entry:
			# set to memcache
			row_dict = entry.exchangeVo(timezone)
			memcache.set(memcache_key, row_dict, time=cls.NDB_MEMCACHE_TIMEOUT)
			return row_dict

		cls.clearInstanceCache(uid)
		return None
