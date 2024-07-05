# coding: utf-8

import random,time
#import logging
import sateraito_logger as logging
from google.appengine.api import taskqueue
from google.appengine.api import runtime
from ucf.utils.validates import BaseValidator
from ucf.utils.helpers import *
from ucf.utils.models import *
from ucf.utils.ucfutil import *
from ucf.utils.mailutil import UcfMailUtil
import sateraito_inc
import sateraito_func
#import sateraito_db


############################################################
## ID変更履歴、タスクテーブル用メソッド
############################################################
class TaskChangeIDUtils():

	# 初期値用：データ加工
	def editVoForDefault(helper, vo):
		pass
	editVoForDefault = staticmethod(editVoForDefault)

	# 更新用：データ加工
	def editVoForRegist(helper, vo, entry_vo, edit_type):
		pass
	editVoForRegist = staticmethod(editVoForRegist)

	# 取得用：データ加工
	def editVoForSelect(helper, vo):
		pass
	editVoForSelect = staticmethod(editVoForSelect)

	# 既存データを取得
	def getData(helper, unique_id):
		#query = UCFMDLTaskChangeID.gql("where unique_id = :1", UcfUtil.escapeGql(unique_id))
		#entry = query.get()
		#return entry

		query = UCFMDLTaskChangeID.all(keys_only=True)
		query.filter('unique_id =', unique_id)
		key = query.get()
		entry = None
		if key is not None:
			entry = UCFMDLTaskChangeID.getByKey(key)
		return entry

	getData = staticmethod(getData)

	# キーに使用する値を取得
	def getKey(helper, vo):
		# 最新ものを上に出したいので. ※TODO BigTableのInsertパフォーマンス大丈夫かなー？
		return UcfUtil.nvl(int(''.ljust(10, '9')) - int(UcfUtil.nvl(int(time.time())).ljust(10, '0')))  + UcfConfig.KEY_PREFIX + UcfUtil.getHashStr(vo, 'unique_id')
	getKey = staticmethod(getKey)

	# 1件追加
	def insertTask(helper, task_type, target_unique_id, src_data_id, dst_data_id, sync_result, queue_name='default', is_direct_taskprocess=False):
		msg = ''
		vo = {}
		unique_id = UcfUtil.guid()
		vo['unique_id'] = unique_id
		vo['comment'] = ''
		vo['dept_id'] = helper.getDeptInfo()['dept_id']
		vo['task_type'] = task_type
		vo['task_deal_status'] = 'WAIT'
		vo['task_status'] = ''
		vo['task_status_date'] = ''
		vo['task_start_date'] = UcfUtil.nvl(UcfUtil.getNowLocalTime(helper._timezone))
		vo['task_end_date'] = ''
		vo['log_text'] = UcfUtil.getHashStr(sync_result, 'log_text')
		vo['execute_operator_id'] = UcfUtil.getHashStr(sync_result, 'execute_operator_id')
		vo['target_unique_id'] = target_unique_id
		vo['src_data_id'] = src_data_id
		vo['dst_data_id'] = dst_data_id

		# Voからモデルにマージ
		entry = UCFMDLTaskChangeID(unique_id=unique_id,key_name=TaskChangeIDUtils.getKey(helper, vo))
		entry.margeFromVo(vo, helper._timezone)
		entry.creator_name = UcfUtil.getHashStr(sync_result, 'execute_operator_id')
		entry.date_created = UcfUtil.getNow()
		entry.updater_name = UcfUtil.getHashStr(sync_result, 'execute_operator_id')
		entry.date_changed = UcfUtil.getNow()
		entry.put()

		if not is_direct_taskprocess:
			token = UcfUtil.guid()
			params = {
				'task_unique_id':unique_id
				,'execute_operator_id':UcfUtil.getHashStr(sync_result, 'execute_operator_id')
			}
			task_url = '/a/' + helper._tenant + '/' + token + '/queue_changeid'

			#logging.info('add_taskqueue:token=' + token + ' countdown=' + str(countdown))
			# キュー追加
			import_q = taskqueue.Queue(queue_name)
			import_t = taskqueue.Task(url=task_url,	params=params, target=sateraito_func.getBackEndsModuleName(helper._tenant), countdown=0)
			import_q.add(import_t)

			return 0, msg

		else:

			task_unique_id = unique_id
			# 一括更新の場合はタスク処理部分も非同期ではなくインポートタスク内で直列に実施（デプリケーションを防ぐため）
			try:

				if TaskChangeIDUtils.updateTaskStatusWithCancelIndicate(helper, task_unique_id, sync_result, is_afterprocess=True):	# タスクステータス、ログ更新（with キャンセル指示チェック）
					return 0, msg

			except Exception as e:
				helper.outputErrorLog(e)
				# 少し具体的な内容を出力
				#sync_result['log_text'] += ucffunc.createErrorLogRecord(helper, 'A system error occured.', '', src_data_id)
				error_msg = ucffunc.createErrorLogRecord(helper, 'A system error occured. (' + str(e) + ')', '', src_data_id)
				sync_result['log_text'] += error_msg
				msg = error_msg
				if TaskChangeIDUtils.updateTaskStatusWithCancelIndicate(helper, task_unique_id, sync_result, is_afterprocess=True, is_error=True):	# タスクステータス、ログ更新（with キャンセル指示チェック）
					return 0, msg
				return 999, msg
			return 0, msg
	insertTask = staticmethod(insertTask)

	# タスク一件取得
	def getTaskByUniqueID(cls, helper, task_unique_id):
		task_entry = None
		task_vo = None

		if task_unique_id != '':
			task_entry = TaskChangeIDUtils.getData(helper, task_unique_id)
		if task_entry is not None:
			task_vo = task_entry.exchangeVo(helper._timezone)
			TaskChangeIDUtils.editVoForSelect(helper, task_vo)
		return task_entry, task_vo
	getTaskByUniqueID = classmethod(getTaskByUniqueID)

	# タスク一件処理の前処理
	def beforeTaskProcess(cls, helper, task_unique_id, sync_result):
		is_valid = False
		task_entry = None
		task_vo = None

		if task_unique_id == '':
			raise Exception(helper.getMsg('MSG_NOTEXIST_WAIT_TASK', (task_unique_id)))
			return is_valid, task_entry, task_vo

		# タスクデータを取得
		task_entry = TaskChangeIDUtils.getData(helper, task_unique_id)
		if task_entry is None:
			raise Exception(helper.getMsg('MSG_NOT_EXIST_DATA'))
			return is_valid, task_entry, task_vo
		# ステータスをチェック
		if task_entry.task_deal_status != 'WAIT':
			raise Exception(helper.getMsg('MSG_NOTEXIST_WAIT_TASK', (task_unique_id)))
			return is_valid, task_entry, task_vo

		# 処理中ステータス更新
		task_entry.task_deal_status = 'PROCESSING'
		task_entry.task_status_date = UcfUtil.getNow()
		task_entry.task_start_date = UcfUtil.getNow()
		task_entry.date_changed = UcfUtil.getNow()
		task_entry.updater_name = 'queue_changeid'
		task_entry.execute_operator_id = UcfUtil.getHashStr(sync_result, 'execute_operator_id')
		task_entry.put()

		task_vo = task_entry.exchangeVo(helper._timezone)
		TaskChangeIDUtils.editVoForSelect(helper, task_vo)

		is_valid = True

		return is_valid, task_entry, task_vo

	beforeTaskProcess = classmethod(beforeTaskProcess)

	# 後処理
	def _afterTaskProcess(cls, helper, task_entry, task_status, sync_result):
		if task_entry is not None:
			if task_status == 'SUCCESS':
				task_entry.task_deal_status = 'FIN'
			elif task_status == 'FAILED':
				task_entry.task_deal_status = 'STOP'
			if task_status == 'SUCCESS' or task_status == 'FAILED':
				task_entry.task_status = task_status
			task_entry.task_status_date = UcfUtil.getNow()
			task_entry.log_text = UcfUtil.nvl(task_entry.log_text) + UcfUtil.getHashStr(sync_result, 'log_text')
			task_entry.task_end_date = UcfUtil.getNow()
			task_entry.date_changed = UcfUtil.getNow()
			task_entry.updater_name = 'queue_changeid'
			task_entry.execute_operator_id = UcfUtil.getHashStr(sync_result, 'execute_operator_id')
			task_entry.put()

	_afterTaskProcess = classmethod(_afterTaskProcess)

	# タスクステータス、ログを更新
	def _updateTaskStatus(cls, helper, task_entry, task_status, sync_result):
		if task_entry is not None:
			if task_status == 'SUCCESS' or task_status == 'FAILED':
				task_entry.task_status = task_status
			task_entry.task_status_date = UcfUtil.getNow()
			task_entry.log_text = UcfUtil.nvl(task_entry.log_text) + UcfUtil.getHashStr(sync_result, 'log_text')
			task_entry.date_changed = UcfUtil.getNow()
			task_entry.updater_name = 'queue_changeid'
			task_entry.put()
	_updateTaskStatus = classmethod(_updateTaskStatus)

	# タスクステータス、ログ更新（with キャンセル指示チェック）
	def updateTaskStatusWithCancelIndicate(cls, helper, task_unique_id, sync_result, is_afterprocess=False, is_error=False):
		task_entry, task_vo = TaskChangeIDUtils.getTaskByUniqueID(helper, task_unique_id)
		is_cancel_indicate = False
		if task_vo is not None:
			if UcfUtil.getHashStr(task_vo, 'task_deal_status') == 'STOP_INDICATING':
				sync_result['log_text'] += ucffunc.createLogRecord(helper, UcfMessage.getMessage(helper.getMsg('LOG_STOP_TASK')))
				is_cancel_indicate = True
				TaskChangeIDUtils._afterTaskProcess(helper, task_entry, 'FAILED' if is_error or sync_result.get('error_count', 0) > 0 else '', sync_result)
			elif is_afterprocess:
				TaskChangeIDUtils._afterTaskProcess(helper, task_entry, 'FAILED' if is_error or sync_result.get('error_count', 0) > 0 else 'SUCCESS', sync_result)
			else:
				TaskChangeIDUtils._updateTaskStatus(helper, task_entry, 'FAILED' if is_error or sync_result.get('error_count', 0) > 0 else '', sync_result)
			# TaskHistoryテーブルに移動
			#sync_result['log_text'] = ''
		return is_cancel_indicate
	updateTaskStatusWithCancelIndicate = classmethod(updateTaskStatusWithCancelIndicate)



############################################################
## ビューヘルパー
############################################################
class TaskViewHelper(ViewHelper):

	def applicate(self, vo, helper):
		voVH = {}

		# ここで表示用変換を必要に応じて行うが、原則Djangoテンプレートのフィルタ機能を使う
		for k,v in vo.items():
			voVH[k] = v	

		return voVH
