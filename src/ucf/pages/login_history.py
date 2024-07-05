# coding: utf-8

import datetime,time,gc
#import logging
import sateraito_logger as logging
import json
from ucf.utils.validates import BaseValidator
from ucf.utils.helpers import *
from ucf.utils.models import *
import sateraito_inc
import sateraito_func


############################################################
## ログイン履歴テーブル用メソッド
############################################################
class LoginHistoryUtils():

	# チェックボックス値補正（TODO 本来はフロントからPOSTするようにExtJsなどで処理すべきが取り急ぎ）
	def setNotPostValue(cls, helper, req):
		# チェックボックス項目
		cbx_fields = []
		for field in cbx_fields:
			if field[0] not in req:
				req[field[0]] = field[1]
	setNotPostValue = classmethod(setNotPostValue)

	# 初期値用：データ加工
	def editVoForDefault(cls, helper, vo):
		pass
	editVoForDefault = classmethod(editVoForDefault)

	# 取得用：データ加工
	def editVoForSelect(cls, helper, vo):
		pass
	editVoForSelect = classmethod(editVoForSelect)

	# 取得用：データ加工（CSV用）
	def editVoForCsv(cls, helper, vo):
		pass
	editVoForCsv = classmethod(editVoForCsv)

	# 既存データを取得
	def getData(cls, helper, unique_id):
		query = UCFMDLLoginHistory.gql("where unique_id = :1", UcfUtil.escapeGql(unique_id))
		entry = query.get()
		return entry
	getData = classmethod(getData)

	# キーに使用する値を取得
	def getKey(cls, helper, unique_id):
		# 最新ものを上に出したいので. ※TODO BigTableのInsertパフォーマンス大丈夫かなー？
		return UcfUtil.nvl(int(''.ljust(10, '9')) - int(UcfUtil.nvl(int(time.time())).ljust(10, '0')))  + UcfConfig.KEY_PREFIX + unique_id

	getKey = classmethod(getKey)

	# コピー新規用に不要なデータをvoから削除
	def removeFromVoForCopyRegist(cls, helper, vo):
		vo['unique_id'] = ''
		vo['login_password'] = ''
		vo['login_password_enctype'] = ''
		vo['login_password_length'] = ''
		vo['date_created'] = ''
		vo['date_changed'] = ''
		vo['creator_name'] = ''
		vo['updater_name'] = ''
		vo['updater_name'] = ''
	removeFromVoForCopyRegist = classmethod(removeFromVoForCopyRegist)

	# エクスポート用CSVを作成
	def createCsv(cls, helper, login_operator_entry=None, sk_operator_unique_id='', optional_scond=None):

		logging.info('start create csv...')

		with_cursor = True
		csv_records = []
		# タイトル
		titles = LoginHistoryUtils.getCsvTitles(helper)
		csv_records.append(UcfUtil.createCsvRecordEx(titles))
		# データ一覧取得
		q = UCFMDLLoginHistory.query()
		if sk_operator_unique_id != '':
			q = q.filter(UCFMDLLoginHistory.operator_unique_id == sk_operator_unique_id)

			## ユーザーごとのログイン履歴は従来通り1000件固定
			#max_export_cnt = 1000		# 最大出力件数

		else:


			sk_search_type = UcfUtil.getHashStr(optional_scond, 'sk_search_type') if optional_scond is not None else ''
			sk_login_id = UcfUtil.getHashStr(optional_scond, 'sk_login_id').lower() if optional_scond is not None else ''
			#sk_operator_unique_id = UcfUtil.getHashStr(optional_scond, 'sk_operator_unique_id') if optional_scond is not None else ''
			sk_access_date_date_from = UcfUtil.getHashStr(optional_scond, 'sk_access_date_date_from') if optional_scond is not None else ''
			sk_access_date_time_from = UcfUtil.getHashStr(optional_scond, 'sk_access_date_time_from') if optional_scond is not None else ''
			sk_access_date_date_to = UcfUtil.getHashStr(optional_scond, 'sk_access_date_date_to') if optional_scond is not None else ''
			sk_access_date_time_to = UcfUtil.getHashStr(optional_scond, 'sk_access_date_time_to') if optional_scond is not None else ''

			if sk_search_type == '':
				sk_search_type = 'login_id'


			# 委託管理者なら自分が触れるデータのみ対象
			if ucffunc.isDelegateOperator(login_operator_entry) and login_operator_entry.delegate_management_groups is not None and len(login_operator_entry.delegate_management_groups) > 0:
				q = q.filter(UCFMDLLoginHistory.management_group.IN(login_operator_entry.delegate_management_groups))
				# 管理グループが複数ある場合はカーソル使えないので
				if len(login_operator_entry.delegate_management_groups) >= 2:
					with_cursor = False

			# ログインIDで検索
			if sk_search_type == 'login_id' and sk_login_id != '':
				q = q.filter(UCFMDLLoginHistory.login_id_lower >= sk_login_id)
				q = q.filter(UCFMDLLoginHistory.login_id_lower < sk_login_id + u'\uFFFD')

			# アクセス日時で検索
			elif sk_search_type == 'access_date' and (sk_access_date_date_from != '' or sk_access_date_date_to != ''):
				if sk_access_date_date_from != '':
					if sk_access_date_time_from != '':
						time_ary = sk_access_date_time_from.split(':')
						sk_access_date_from = sk_access_date_date_from + ' ' + time_ary[0] + ':' + time_ary[1] + ':00'
						sk_access_date_from_utc = UcfUtil.getUTCTime(UcfUtil.getDateTime(sk_access_date_from), helper._timezone)
					else:
						sk_access_date_from = sk_access_date_date_from + ' 00:00:00'
						sk_access_date_from_utc = UcfUtil.getUTCTime(UcfUtil.getDateTime(sk_access_date_from), helper._timezone)
					q = q.filter(UCFMDLLoginHistory.access_date >= sk_access_date_from_utc)
				if sk_access_date_date_to != '':
					if sk_access_date_time_to != '':
						time_ary = sk_access_date_time_to.split(':')
						sk_access_date_to = sk_access_date_date_to + ' ' + time_ary[0] + ':' + time_ary[1] + ':00'
						sk_access_date_to_utc = UcfUtil.getUTCTime(UcfUtil.getDateTime(sk_access_date_to), helper._timezone)
					else:
						sk_access_date_to = sk_access_date_date_to + ' 00:00:00'
						sk_access_date_to_utc = UcfUtil.getUTCTime(UcfUtil.add_days(UcfUtil.getDateTime(sk_access_date_to), 1), helper._timezone)
					q = q.filter(UCFMDLLoginHistory.access_date < sk_access_date_to_utc)
				q = q.order(-UCFMDLLoginHistory.access_date)


		# ユーザーごとも全体も上限を統一 2016.02.01
		login_history_max_export_cnt = helper.getDeptInfo().get('login_history_max_export_cnt')
		max_export_cnt = UcfUtil.toInt(login_history_max_export_cnt)		# 最大出力件数
		if max_export_cnt <= 0:
			max_export_cnt = 1000
		logging.info('max_export_cnt=' + str(max_export_cnt))

		cnt = 0
		#start = 0
		#limit = 100
		limit = 1000					# 通常の、max_export_cnt == 1000 のドメインは1発で取れたほうがいいはずなので 1000 とする
		start_cursor = None
		while True:

			if with_cursor:
				if start_cursor is not None:
					each_rows, start_cursor, more = q.fetch_page(limit, start_cursor=start_cursor)
				else:
					each_rows, start_cursor, more = q.fetch_page(limit)
			else:
				each_rows = q.iter(limit=limit, offset=cnt)

			each_cnt = 0
			for entry in each_rows:

				vo = entry.exchangeVo(helper._timezone)
				LoginHistoryUtils.editVoForCsv(helper, vo)

				data = []
				data.append('IU')																						# command
				data.append(UcfUtil.getHashStr(vo, 'access_date'))					# access_date
				data.append(UcfUtil.getHashStr(vo, 'login_id'))					# login_id
				data.append(UcfUtil.getHashStr(vo, 'login_password_length'))					# login_password_length
				data.append(UcfUtil.getHashStr(vo, 'operator_id'))					# email
				#data.append(UcfUtil.getHashStr(vo, 'login_type'))					# login_type
				data.append(UcfUtil.getHashStr(vo, 'login_result'))					# login_result
				data.append(UcfUtil.getHashStr(vo, 'log_code'))					# log_code
				data.append(UcfUtil.getHashStr(vo, 'client_ip'))					# ipaddress
				data.append(UcfUtil.getHashStr(vo, 'target_career'))					# target_career
				data.append(UcfUtil.getHashStr(vo, 'is_auto_login'))					# is_auto_login
				data.append(UcfUtil.getHashStr(vo, 'user_agent'))					# user_agent
				# 負荷対策のためログ詳細はCSVには出さないように変更 2013.10.01
				#data.append(UcfUtil.getHashStr(vo, 'log_text'))					# log_text

				csv_records.append(UcfUtil.createCsvRecordEx(data))
				each_cnt += 1

				vo = None
				entry = None
				if each_cnt % 100 == 0:
					gc.collect()

			cnt += each_cnt
			logging.info(cnt)

			# 件数上限
			if with_cursor:
				if cnt >= max_export_cnt or not more:
					break
			else:
				if (max_export_cnt > 0 and cnt >= max_export_cnt) or each_cnt < limit:
					break

		csv_text = '\r\n'.join(csv_records)
		return csv_text
	createCsv = classmethod(createCsv)

	def getCsvTitles(cls, helper):
		# 負荷対策のためログ詳細はCSVには出さないように変更 2013.10.01
		#return ['command','access_date','login_id','login_password_length','email','login_type','login_result','ipaddress','ipaddress_xff','use_profile_id','target_career','target_env','is_auto_login','mobile_device_id','user_agent','log_code','log_text']
		return ['command','access_date','login_id','login_password_length','email','login_result','log_code','ipaddress','target_career','is_auto_login','user_agent']
	getCsvTitles = classmethod(getCsvTitles)

	# 遅延登録用のログイン履歴をセット
	def putLoginHistoryForDelay(cls, helper, operator_unique_id, operator_mail_address, params):
		unique_id = UcfUtil.guid()
		key_name = UcfUtil.nvl(int(UcfUtil.nvl(int(time.time())).ljust(10, '0')))  + UcfConfig.KEY_PREFIX + unique_id		# 古いの順
		entry = UCFMDLLoginHistoryForDelay(unique_id=unique_id,id=key_name)
		entry.operator_unique_id = operator_unique_id
		entry.operator_id_lower = operator_mail_address.lower()
		entry.params = json.JSONEncoder().encode(params)
		entry.date_changed = UcfUtil.getNow()
		entry.put()

		return entry

	putLoginHistoryForDelay = classmethod(putLoginHistoryForDelay)

	# 遅延登録用のログイン履歴情報を取得
	def getLoginHistoryForDelay(cls, helper, unique_id):
		q = UCFMDLLoginHistoryForDelay.query()
		q = q.filter(UCFMDLLoginHistoryForDelay.unique_id == unique_id)
		entry = q.get()
		return entry
	getLoginHistoryForDelay = classmethod(getLoginHistoryForDelay)

	# 遅延登録用のログイン情報をセット
	def putLoginInfoForDelay(cls, helper, operator_unique_id, operator_mail_address, params):
		unique_id = UcfUtil.guid()
		key_name = UcfUtil.nvl(int(UcfUtil.nvl(int(time.time())).ljust(10, '0')))  + UcfConfig.KEY_PREFIX + unique_id		# 古いの順
		entry = UCFMDLLoginInfoForDelay(unique_id=unique_id,id=key_name)
		entry.operator_unique_id = operator_unique_id
		entry.operator_id_lower = operator_mail_address.lower()
		entry.params = json.JSONEncoder().encode(params)
		entry.date_changed = UcfUtil.getNow()
		entry.put()

		return entry
	putLoginInfoForDelay = classmethod(putLoginInfoForDelay)

	# 遅延登録用のログイン情報情報を取得
	def getLoginInfoForDelay(cls, helper, unique_id):
		q = UCFMDLLoginInfoForDelay.query()
		q = q.filter(UCFMDLLoginInfoForDelay.unique_id == unique_id)
		entry = q.get()
		return entry
	getLoginInfoForDelay = classmethod(getLoginInfoForDelay)


############################################################
## バリデーションチェッククラス 
############################################################
class LoginHistoryValidator(BaseValidator):
	def validate(self, helper, vo):
		# 初期化
		self.init()

############################################################
## ビューヘルパー
############################################################
class LoginHistoryHelper(ViewHelper):

	def applicate(self, vo, helper):
		voVH = {}

		# ここで表示用変換を必要に応じて行うが、原則Djangoテンプレートのフィルタ機能を使う
		for k,v in vo.items():
			voVH[k] = v	

		return voVH
