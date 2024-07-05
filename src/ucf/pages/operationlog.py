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
## 管理画面のオペレーションログ関連
############################################################
class OperationLogUtils():

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

	# 取得用：データ加工
	def editVoForList(cls, helper, vo):
		# ログ詳細を作成
		vo['log_text'] = OperationLogUtils._formatLogText(helper, vo)
	editVoForList = classmethod(editVoForList)

	# 取得用：データ加工（CSV用）
	def editVoForCsv(cls, helper, vo):
		pass
	editVoForCsv = classmethod(editVoForCsv)

	# 更新用：データ加工
	def editVoForRegist(cls, helper, vo, entry_vo, edit_type):
		pass
	editVoForRegist = classmethod(editVoForRegist)

	# 既存データを取得
	def getData(cls, helper, unique_id):
		query = UCFMDLOperationLog.gql("where unique_id = :1", UcfUtil.escapeGql(unique_id))
		entry = query.get()
		return entry
	getData = classmethod(getData)

	# コピー新規用に不要なデータをvoから削除
	def removeFromVoForCopyRegist(cls, helper, vo):
		vo['unique_id'] = ''
		vo['date_created'] = ''
		vo['date_changed'] = ''
	removeFromVoForCopyRegist = classmethod(removeFromVoForCopyRegist)

	# エクスポート用CSVを作成
	def createCsv(cls, helper, login_operator_entry=None, sk_operator_unique_id=''):

		logging.info('start create csv...')

		csv_records = []
		# タイトル
		titles = OperationLogUtils.getCsvTitles(helper)
		csv_records.append(UcfUtil.createCsvRecordEx(titles))
		# データ一覧取得
		q = UCFMDLOperationLog.query()
		if sk_operator_unique_id != '':
			q = q.filter(UCFMDLOperationLog.operator_unique_id == sk_operator_unique_id)

			# ユーザーごとのログイン履歴は従来通り1000件固定
			max_export_cnt = 1000		# 最大出力件数

		# 全件取得の場合は、fecthのメモリ使用量が大きいため、過去ヶ月分の制約を設けてみる 2013.10.01
		else:

			login_history_max_export_cnt = helper.getDeptInfo().get('login_history_max_export_cnt')		# ログイン履歴の設定を流用
			max_export_cnt = UcfUtil.toInt(login_history_max_export_cnt)		# 最大出力件数
			if max_export_cnt <= 0:
				max_export_cnt = 1000

		q = q.order(-UCFMDLOperationLog.operation_date)

		logging.info('max_export_cnt=' + str(max_export_cnt))

		cnt = 0
		#start = 0
		limit = 100
		#limit = 1000					# 通常の、max_export_cnt == 1000 のドメインは1発で取れたほうがいいはずなので 1000 とする
		start_cursor = None
		while True:

			if start_cursor is not None:
				each_rows, start_cursor, more = q.fetch_page(limit, start_cursor=start_cursor)
			else:
				each_rows, start_cursor, more = q.fetch_page(limit)

			each_cnt = 0
			for entry in each_rows:

				vo = entry.exchangeVo(helper._timezone)
				OperationLogUtils.editVoForCsv(helper, vo)

				data = []
				data.append('IU')																						# command
				data.append(UcfUtil.getHashStr(vo, 'operation_date'))					# operation_date
				data.append(UcfUtil.getHashStr(vo, 'operator_id'))					# operator_id
				data.append(UcfUtil.getHashStr(vo, 'operation'))					# operation
				data.append(UcfUtil.getHashStr(vo, 'target_data'))					# target_data
				data.append(UcfUtil.getHashStr(vo, 'client_ip'))					# ipaddress

				csv_records.append(UcfUtil.createCsvRecordEx(data))
				each_cnt += 1

				vo = None
				entry = None
				if each_cnt % 100 == 0:
					gc.collect()

			cnt += each_cnt
			logging.info(cnt)

			# 件数上限
			if cnt >= max_export_cnt or not more:
				break

		csv_text = '\r\n'.join(csv_records)
		return csv_text
	createCsv = classmethod(createCsv)

	def getCsvTitles(cls, helper):
		return ['command','operation_date','operator_id','operation','target_data','ipaddress']
	getCsvTitles = classmethod(getCsvTitles)

	# オペレーションログ詳細画面に表示するログテキストを生成
	@classmethod
	def _formatLogText(cls, helper, vo):

		screen = vo.get('screen', '')
		operation = vo.get('operation', '')

		log_records = []
		#if screen not in [UcfConfig.SCREEN_TASK, UcfConfig.SCREEN_PROFILE, UcfConfig.SCREEN_GENERALSSO]:
		if screen not in []:
			if screen not in [UcfConfig.SCREEN_DASHBOARD]:
				log_records.append(helper.getMsg('OPERATIONLOG_DETAIL_TARGET_DATA') + vo.get('target_data', ''))

		if operation == 'account_changeid':
			log_records.append(helper.getMsg('OPERATIONLOG_DETAIL_IS_UPDATE_GW_DATA') + vo.get('is_update_apps_data', ''))
		if vo.get('detail', '') != '':
			detail = json.JSONDecoder().decode(vo.get('detail', ''))

			if operation in ['group_addmembers', 'orgunit_addmembers']:
				if 'members' in detail:
					members = detail['members']
					for member in members:
						log_records.append('[email]' + member.get('email', '') + '[type]' + member.get('type', ''))

			if operation in ['group_removemembers', 'orgunit_removemembers']:
				if 'members' in detail:
					members = detail['members']
					for member in members:
						log_records.append('[email]' + member.get('email', ''))

			if 'fields' in detail:
				log_records.append(helper.getMsg('OPERATIONLOG_DETAIL_FIELDS'))
				diff_for_operation_log = detail['fields']
				for item in diff_for_operation_log:
					log_records.append('[field]' + item.get('key', '') + '[before]' + item.get('before', '') + '[after]' + item.get('after', ''))
			if 'add_groups' in detail:
				log_records.append(helper.getMsg('OPERATIONLOG_DETAIL_ADD_GROUPS') + UcfUtil.listToCsv(detail['add_groups']))
			if 'del_groups' in detail:
				log_records.append(helper.getMsg('OPERATIONLOG_DETAIL_REMOVE_GROUPS') + UcfUtil.listToCsv(detail['del_groups']))
		return '\n'.join(log_records)

