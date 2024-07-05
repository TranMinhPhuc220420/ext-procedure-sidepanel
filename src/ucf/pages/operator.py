# coding: utf-8

import time
#import logging
import sateraito_logger as logging
import gc
import json
import unicodedata
# GAEGEN2対応:検索API移行
from google.appengine.api import search
# from search_alt import search_auto
# from search_alt import search_replace as search
from google.appengine.api import runtime
from ucf.utils.validates import BaseValidator
from ucf.utils.helpers import *
from ucf.utils.models import *
from ucf.pages.task import TaskChangeIDUtils
import sateraito_inc
import sateraito_func
import oem_func

############################################################
## オペレータテーブル用メソッド
############################################################
class OperatorUtils():


	# 文書検索
	@classmethod
	def searchDocsByFullText(cls, helper, search_keyword, max_search_count, offset=0):

		# フルテキスト検索でソート対象とするデータの最大件数（デフォルト1000、最大10000）
		MAX_SORT_LIMIT_FULLTEXT = 10000

		# go fulltext search
		# GAEGEN2対応:検索API移行
		# search = search_auto.get_module()
		index = search.Index(name='operator_index')

		#
		# Build query string
		#
		# step1. keyword
		query_string = ''
		if search_keyword != '':
			search_keyword = search_keyword.replace('"', '\\"')
			# 1. 検索キーワード
			keyword = unicodedata.normalize('NFKC', search_keyword)
			keyword_splited = keyword.split(' ')
			keyword2 = ''
			for k in keyword_splited:
				keyword2 += ' "' + k + '"'
			keyword2 = keyword2.strip()
			query_string = keyword2 + ' '

		# 2.委託管理者なら自分が触れるデータのみ対象
		operator_delegate_management_groups = helper.getLoginOperatorDelegateManagementGroups()
		if helper.isOperator() and operator_delegate_management_groups != '':
			list_management_group = UcfUtil.csvToList(operator_delegate_management_groups)
			query_string += (' AND ' if search_keyword != '' else '') + '(management_group:['
			for i in range(len(list_management_group)):
				if i > 0:
					query_string += ' OR '
				query_string += '#' + unicodedata.normalize('NFKC', list_management_group[i].replace('"', '')) + '#'
			query_string += '])'

		logging.info('query_string=' + query_string)
		
		# sort option
		sort_expression = search.SortExpression(
	          expression='operator_id_lower',
	          direction=search.SortExpression.ASCENDING,
	          default_value='')
		sort = search.SortOptions(expressions=[sort_expression], limit=MAX_SORT_LIMIT_FULLTEXT)
		returned_fields = UCFMDLOperator.getReturnedFieldsForTextSearch()
		# Go query (using page parameter)
		q_ft = search.Query(query_string=query_string, options=search.QueryOptions(sort_options=sort, limit=max_search_count, offset=offset, returned_fields=returned_fields))
		results = index.search(q_ft)
		logging.info('operator.number_found=' + str(results.number_found))

		ret_results = []
		for result in results:
			ret_results.append(UCFMDLOperator.getDictFromTextSearchIndex(result))
		logging.info('result_cnt=' + str(len(ret_results)))
		return ret_results


	# チェックボックス値補正（TODO 本来はフロントからPOSTするようにExtJsなどで処理すべきが取り急ぎ）
	def setNotPostValue(cls, helper, req):
		# チェックボックス項目
		cbx_fields = [
			('login_lock_flag', '')
			,('next_password_change_flag', '')
			,('delegate_function', '')
		]
		for field in cbx_fields:
			if field[0] not in req:
				req[field[0]] = field[1]
	setNotPostValue = classmethod(setNotPostValue)

	# 初期値用：データ加工
	def editVoForDefault(cls, helper, vo):
		#vo['access_authority'] = 'MANAGER'
		vo['access_authority'] = 'ADMIN'
	editVoForDefault = classmethod(editVoForDefault)

	# 取得用：データ加工
	def editVoForSelect(cls, helper, vo):

		vo['name'] = helper.getUserNameDisp(UcfUtil.getHashStr(vo, 'last_name'), UcfUtil.getHashStr(vo, 'first_name')) # ユーザ名称（表示専用）
		vo['password'] = helper.decryptoData(UcfUtil.getHashStr(vo, 'password'), enctype=UcfUtil.getHashStr(vo, 'password_enctype'))		# パスワード復号化
		#vo['operator_id_localpart'] = UcfUtil.getHashStr(vo, 'operator_id').split('@')[0]

	editVoForSelect = classmethod(editVoForSelect)

	# 取得用：データ加工（一覧用）
	def editVoForList(cls, helper, vo):
		vo['display_name'] = helper.getUserNameDisp(UcfUtil.getHashStr(vo, 'last_name'), UcfUtil.getHashStr(vo, 'first_name')) # ユーザ名称（表示専用）
		vo['password'] = helper.decryptoData(UcfUtil.getHashStr(vo, 'password'), enctype=UcfUtil.getHashStr(vo, 'password_enctype'))		# パスワード復号化
		#vo['operator_id_localpart'] = UcfUtil.getHashStr(vo, 'operator_id').split('@')[0]

	editVoForList = classmethod(editVoForList)

	# 取得用：データ加工（CSV用）
	def editVoForCsv(cls, helper, vo):
		vo['password'] = helper.decryptoData(UcfUtil.getHashStr(vo, 'password'), enctype=UcfUtil.getHashStr(vo, 'password_enctype'))		# パスワード復号化
	editVoForCsv = classmethod(editVoForCsv)

	# 取得用：データ加工（CSVインポート時の取得）
	def editVoForSelectCsvImport(cls, helper, vo):
		OperatorUtils.editVoForCsv(helper, vo)
	editVoForSelectCsvImport = classmethod(editVoForSelectCsvImport)


	# 更新用：データ加工
	def editVoForRegist(cls, helper, vo, entry_vo, edit_type, is_noupdate_password_change_date_for_sync=False):
		if edit_type == UcfConfig.EDIT_TYPE_NEW:
			vo['dept_id'] = helper.getDeptInfo()['dept_id']
		vo['operator_id_lower'] = UcfUtil.getHashStr(vo, 'operator_id').lower()									# 小文字（検索、重複チェック用）
		#vo['main_group_id'] = UcfUtil.getHashStr(vo, 'main_group_id').lower()									# 小文字
		# 日付系フィールドで時分までで切れていた場合の補正（Excel対策）
		if entry_vo is not None:
			vo['last_login_date'] = UcfUtil.reviseSecondOfDateStr(UcfUtil.getHashStr(vo, 'last_login_date'), UcfUtil.getHashStr(entry_vo, 'last_login_date'))
			vo['login_lock_expire'] = UcfUtil.reviseSecondOfDateStr(UcfUtil.getHashStr(vo, 'login_lock_expire'), UcfUtil.getHashStr(entry_vo, 'login_lock_expire'))
			vo['password_expire'] = UcfUtil.reviseSecondOfDateStr(UcfUtil.getHashStr(vo, 'password_expire'), UcfUtil.getHashStr(entry_vo, 'password_expire'))
		else:
			vo['last_login_date'] = UcfUtil.reviseSecondOfDateStr(UcfUtil.getHashStr(vo, 'last_login_date'), '')
			vo['login_lock_expire'] = UcfUtil.reviseSecondOfDateStr(UcfUtil.getHashStr(vo, 'login_lock_expire'), '')
			vo['password_expire'] = UcfUtil.reviseSecondOfDateStr(UcfUtil.getHashStr(vo, 'password_expire'), '')

		# オペレータタイプ（権限から算出）

		# パスワード履歴に追加…既存データと変更されていれば
		if (entry_vo is None and UcfUtil.getHashStr(vo, 'password') != '') or (entry_vo is not None and UcfUtil.getHashStr(entry_vo, 'password') != UcfUtil.getHashStr(vo, 'password')):
			OperatorUtils.appendPasswordHistory(helper, vo, UcfUtil.getHashStr(vo, 'password'))
			# SSOパスワード変更日時を更新（連携ツール用）
			if not is_noupdate_password_change_date_for_sync:
				OperatorUtils.updatePasswordChangeDate(helper, vo)
			# ユーザーのパスワード変更日時を更新（CSV出力用）
			OperatorUtils.updateUserPasswordChangeDate(helper, vo)

		vo['password'] = helper.encryptoData(UcfUtil.getHashStr(vo, 'password'), enctype='AES')		# パスワード暗号化
		vo['password_enctype'] = 'AES'
		if UcfUtil.getHashStr(vo, 'access_authority') == '':
			#vo['access_authority'] = 'MANAGER'
			vo['access_authority'] = 'ADMIN'

	editVoForRegist = classmethod(editVoForRegist)

	# パスワード履歴に必要に応じて1件追加
	def appendPasswordHistory(cls, helper, vo, append_password):
		password_history_csv = UcfUtil.getHashStr(vo, 'password_history')
		if password_history_csv != '':
			password_history = password_history_csv.split(',')
		else:
			password_history = []
		# 末尾に追加…暗号化してセット
		password_history[len(password_history):] = [helper.encryptoData(append_password, enctype='AES')]
		# 最大件数を超えていたら先頭から削除
		if len(password_history) > sateraito_inc.max_password_history_count:
			password_history[0:len(password_history)-sateraito_inc.max_password_history_count] = []
		vo['password_history'] = UcfUtil.listToCsv(password_history, ',')
	appendPasswordHistory = classmethod(appendPasswordHistory)

	# パスワード変更日時を更新（連携ツール用）
	def updatePasswordChangeDate(cls, helper, vo):
		# パスワード更新時のフラグ
		vo['password_change_date'] = UcfUtil.nvl(UcfUtil.getNowLocalTime(helper._timezone))
	updatePasswordChangeDate = classmethod(updatePasswordChangeDate)

	# パスワード変更日時を更新（CSV出力用）
	def updateUserPasswordChangeDate(cls, helper, vo):
		# パスワード更新時のフラグ
		vo['password_change_date2'] = UcfUtil.nvl(UcfUtil.getNowLocalTime(helper._timezone))
	updateUserPasswordChangeDate = classmethod(updateUserPasswordChangeDate)

	# 既存データを取得
	def getData(cls, helper, unique_id):
		return OperatorUtils.getUserEntryByUniqueID(helper, unique_id)
	getData = classmethod(getData)

	# キーに使用する値を取得
	def getKey(cls, helper, vo):
		# キーをユニークIDに変更 2017.03.08
		#return (UcfUtil.getHashStr(vo, 'operator_id_lower') if UcfUtil.getHashStr(vo, 'operator_id_lower') != '' else UcfUtil.getHashStr(vo, 'operator_id').lower()) + UcfConfig.KEY_PREFIX + UcfUtil.getHashStr(vo, 'unique_id')
		return UcfConfig.KEY_PREFIX + UcfUtil.getHashStr(vo, 'unique_id')
	getKey = classmethod(getKey)


	# コピー新規用に不要なデータをvoから削除
	def removeFromVoForCopyRegist(cls, helper, vo):
		vo['unique_id'] = ''
		vo['password'] = ''
		vo['password_change_date'] = ''
		vo['password_change_date2'] = ''
		vo['date_created'] = ''
		vo['date_changed'] = ''
		vo['creator_name'] = ''
		vo['updater_name'] = ''
		vo['login_failed_count'] = ''
		vo['login_count'] = ''
		vo['last_login_date'] = ''
		vo['login_password_length'] = ''

	removeFromVoForCopyRegist = classmethod(removeFromVoForCopyRegist)

	# ユニークIDからユーザVoを取得
	def getUserByUniqueID(cls, helper, operator_unique_id):
		user_vo = None
		if operator_unique_id and operator_unique_id != '':
			entry = OperatorUtils.getUserEntryByUniqueID(helper, operator_unique_id)
			if entry is not None:
				user_vo = entry.exchangeVo(helper._timezone)
				OperatorUtils.editVoForSelect(helper, user_vo)
		return user_vo
	getUserByUniqueID = classmethod(getUserByUniqueID)

	# ユニークIDからユーザEntryを取得
	def getUserEntryByUniqueID(cls, helper, operator_unique_id):
		entry = None
		if operator_unique_id and operator_unique_id != '':
			#query = UCFMDLOperator.all(keys_only=True)
			#query.filter('unique_id =', operator_unique_id)
			#key = query.get()
			#if key is not None:
			#	entry = UCFMDLOperator.getByKey(key)
			query = UCFMDLOperator.query()
			query = query.filter(UCFMDLOperator.unique_id == operator_unique_id)
			key = query.get(keys_only=True)
			entry = key.get() if key is not None else None
		return entry
	getUserEntryByUniqueID = classmethod(getUserEntryByUniqueID)


	# ユーザIDからユーザVoを取得
	def getUserByOperatorID(cls, helper, operator_id):
		user_vo = None
		if operator_id and operator_id != '':
			entry = OperatorUtils.getUserEntryByOperatorID(helper, operator_id)
			if entry is not None:
				user_vo = entry.exchangeVo(helper._timezone)
				OperatorUtils.editVoForSelect(helper, user_vo)
		return user_vo
	getUserByOperatorID = classmethod(getUserByOperatorID)

	# ユーザIDからユーザEntryを取得
	def getUserEntryByOperatorID(cls, helper, operator_id):
		entry = None
		if operator_id and operator_id != '':
			#query = UCFMDLOperator.all(keys_only=True)
			#query.filter('operator_id_lower =', operator_id.lower())
			#key = query.get()
			#if key is not None:
			#	entry = UCFMDLOperator.getByKey(key)
			query = UCFMDLOperator.query()
			query = query.filter(UCFMDLOperator.operator_id_lower == operator_id.lower())
			key = query.get(keys_only=True)
			entry = key.get() if key is not None else None
		return entry
	getUserEntryByOperatorID = classmethod(getUserEntryByOperatorID)

	# ２つのVOに変更点があるかどうかを判定
	def isDiff(cls, helper, vo1, vo2):
		is_diff = False
		diff_for_operation_log = []	# オペレーションログに出力する情報のため、keyはユーザーライクにCSV項目と合わせる（出力不要項目の場合はセットしない）

		key = 'comment'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			diff_for_operation_log.append({'key':'comment', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
			is_diff = True
		key = 'operator_id'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			diff_for_operation_log.append({'key':'email', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
			is_diff = True
		key = 'password'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			diff_for_operation_log.append({'key':'password', 'before':'********' if vo2.get(key, '') != '' else '', 'after':'********' if vo1.get(key, '') != '' else ''})
			is_diff = True
		#key = 'employee_id'		# 
		#if vo1.get(key, '') != vo2.get(key, ''):
		#	diff_for_operation_log.append({'key':'employee_id', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
		#	is_diff = True
		key = 'mail_address'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			is_diff = True
		key = 'sub_mail_address'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			diff_for_operation_log.append({'key':'sub_email', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
			is_diff = True
		key = 'last_name'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			diff_for_operation_log.append({'key':'last_name', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
			is_diff = True
		key = 'first_name'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			diff_for_operation_log.append({'key':'first_name', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
			is_diff = True
		key = 'last_name_kana'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			diff_for_operation_log.append({'key':'last_name_kana', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
			is_diff = True
		key = 'first_name_kana'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			diff_for_operation_log.append({'key':'first_name_kana', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
			is_diff = True
		key = 'account_stop_flag'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			diff_for_operation_log.append({'key':'account_stop', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
			is_diff = True
		key = 'access_authority'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			diff_for_operation_log.append({'key':'access_authority', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
			is_diff = True
		#key = 'delegate_function'		# 
		#if vo1.get(key, '') != vo2.get(key, ''):
		#	diff_for_operation_log.append({'key':'delegate_function', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
		#	is_diff = True
		#key = 'delegate_management_groups'		# 
		#if vo1.get(key, '') != vo2.get(key, ''):
		#	diff_for_operation_log.append({'key':'delegate_management_groups', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
		#	is_diff = True
		#key = 'management_group'		# 
		#if vo1.get(key, '') != vo2.get(key, ''):
		#	diff_for_operation_log.append({'key':'management_group', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
		#	is_diff = True
		key = 'language'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			diff_for_operation_log.append({'key':'language', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
			is_diff = True
		key = 'password_reminder_key'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			is_diff = True
		key = 'password_reminder_expire'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			is_diff = True
		key = 'next_password_change_flag'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			diff_for_operation_log.append({'key':'password_change', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
			is_diff = True
		key = 'password_expire'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			diff_for_operation_log.append({'key':'password_expire', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
			is_diff = True
		key = 'login_lock_flag'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			diff_for_operation_log.append({'key':'login_lock', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
			is_diff = True
		key = 'login_lock_expire'		# 
		if vo1.get(key, '') != vo2.get(key, ''):
			diff_for_operation_log.append({'key':'login_lock_expire', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
			is_diff = True
#		key = 'contact_company'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'company', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_company_office'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'company_office', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_company_department'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'company_department', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_company_department2'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'company_department2', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_company_post'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'job_title', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_email1'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'email_work', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_email2'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'email_work_phone', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_tel_no1'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'phone_work', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_tel_no2'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'fax_work', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_tel_no3'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'mobile_phone', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_tel_no4'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'extension_number', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_tel_no5'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'pocketbell', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_postal_country'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'postal_country', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_postal_code'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'postal_code', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_postal_prefecture'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'postal_prefecture', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_postal_city'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'postal_city', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'contact_postal_street_address'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'postal_street_address', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'custom_attribute1'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'custom_attribute1', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'custom_attribute2'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'custom_attribute2', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'custom_attribute3'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'custom_attribute3', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'custom_attribute4'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'custom_attribute4', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'custom_attribute5'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'custom_attribute5', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'custom_attribute6'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'custom_attribute6', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'custom_attribute7'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'custom_attribute7', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'custom_attribute8'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'custom_attribute8', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'custom_attribute9'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'custom_attribute9', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True
#		key = 'custom_attribute10'		# 
#		if vo1.get(key, '') != vo2.get(key, ''):
#			diff_for_operation_log.append({'key':'custom_attribute10', 'before':vo2.get(key, ''), 'after':vo1.get(key, '')})
#			is_diff = True

		return is_diff, diff_for_operation_log
	isDiff = classmethod(isDiff)

	# エクスポート用CSVを作成
	def createCsv(cls, helper, login_operator_entry=None):
		with_cursor = True
		csv_records = []
		# タイトル
		titles = OperatorUtils.getCsvTitles(helper)
		csv_records.append(UcfUtil.createCsvRecordEx(titles))

		# データ一覧取得
		q = UCFMDLOperator.query()
		# 委託管理者なら自分が触れるデータのみ対象
		if ucffunc.isDelegateOperator(login_operator_entry) and login_operator_entry.delegate_management_groups is not None and len(login_operator_entry.delegate_management_groups) > 0:
			q = q.filter(UCFMDLOperator.management_group.IN(login_operator_entry.delegate_management_groups))
			# 管理グループが複数ある場合はカーソル使えないので
			if len(login_operator_entry.delegate_management_groups) >= 2:
				with_cursor = False
		q = q.order(UCFMDLOperator.operator_id_lower)
		logging.info('with_cursor=' + str(with_cursor))

		max_export_cnt = -1
		cnt = 0
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
				OperatorUtils.editVoForCsv(helper, vo)

				data = []
				data.append('IU')	# command
				data.append(UcfUtil.getHashStr(vo, 'operator_id')) # user_id
				#data.append(UcfUtil.getHashStr(vo, 'employee_id')) # employee_id
				data.append(UcfUtil.getHashStr(vo, 'mail_address')) # email
				data.append(UcfUtil.getHashStr(vo, 'last_name')) # last_name
				data.append(UcfUtil.getHashStr(vo, 'first_name')) # first_name
				data.append(UcfUtil.getHashStr(vo, 'last_name_kana')) # last_name_kana
				data.append(UcfUtil.getHashStr(vo, 'first_name_kana')) # first_name_kana
				data.append(UcfUtil.getHashStr(vo, 'sub_mail_address')) # sub_email
				data.append(UcfUtil.getHashStr(vo, 'access_authority')) # access_authority
				#data.append(UcfUtil.getHashStr(vo, 'delegate_function')) # delegate_function
				#data.append(UcfUtil.getHashStr(vo, 'delegate_management_groups')) # delegate_management_groups
				#data.append(UcfUtil.getHashStr(vo, 'main_group_id')) # main_group
				#data.append(UcfUtil.getHashStr(vo, 'profile_infos')) # profile_id
				data.append(UcfUtil.getHashStr(vo, 'language')) # language
				#data.append(UcfUtil.getHashStr(vo, 'management_group')) # management_group
				data.append(UcfUtil.getHashStr(vo, 'account_stop_flag')) # account_stop
				data.append(UcfUtil.getHashStr(vo, 'next_password_change_flag')) # password_change
				data.append(UcfUtil.getHashStr(vo, 'password_expire')) # password_expire
				if UcfUtil.getHashStr(vo, 'password_change_date2') != '':
					data.append(UcfUtil.getHashStr(vo, 'password_change_date2')) # password_change_date
				else:
					data.append(UcfUtil.getHashStr(vo, 'password_change_date')) # password_change_date
				data.append(UcfUtil.getHashStr(vo, 'login_lock_flag')) # login_lock
				data.append(UcfUtil.getHashStr(vo, 'login_lock_expire')) # login_lock_expire
				data.append(UcfUtil.nvl(UcfUtil.toInt(UcfUtil.getHashStr(vo, 'login_count')))) # login_count
				data.append(UcfUtil.nvl(UcfUtil.toInt(UcfUtil.getHashStr(vo, 'login_failed_count')))) # login_failed_count
				data.append(UcfUtil.getHashStr(vo, 'last_login_date')) # last_login_date
				data.append(UcfUtil.nvl(UcfUtil.toInt(UcfUtil.getHashStr(vo, 'login_password_length')))) # last_login_password_length
				data.append('') # password
				data.append('') # password_update_flag
				#data.append(UcfUtil.getHashStr(vo, 'contact_company')) # company
				#data.append(UcfUtil.getHashStr(vo, 'contact_company_office')) # company_office
				#data.append(UcfUtil.getHashStr(vo, 'contact_company_department')) # company_department
				#data.append(UcfUtil.getHashStr(vo, 'contact_company_department2')) # company_department2
				#data.append(UcfUtil.getHashStr(vo, 'contact_company_post')) # job_title
				#data.append(UcfUtil.getHashStr(vo, 'contact_email1')) # email_work
				#data.append(UcfUtil.getHashStr(vo, 'contact_email2')) # email_work_phone
				#data.append(UcfUtil.getHashStr(vo, 'contact_tel_no1')) # phone_work
				#data.append(UcfUtil.getHashStr(vo, 'contact_tel_no2')) # fax_work
				#data.append(UcfUtil.getHashStr(vo, 'contact_tel_no3')) # mobile_phone
				#data.append(UcfUtil.getHashStr(vo, 'contact_tel_no4')) # extension_number
				#data.append(UcfUtil.getHashStr(vo, 'contact_tel_no5')) # pocketbell
				#data.append(UcfUtil.getHashStr(vo, 'contact_postal_country')) # postal_country
				#data.append(UcfUtil.getHashStr(vo, 'contact_postal_code')) # postal_code
				#data.append(UcfUtil.getHashStr(vo, 'contact_postal_prefecture')) # postal_prefecture
				#data.append(UcfUtil.getHashStr(vo, 'contact_postal_city')) # postal_city
				#data.append(UcfUtil.getHashStr(vo, 'contact_postal_street_address')) # postal_street_address
				#data.append(UcfUtil.getHashStr(vo, 'custom_attribute1')) # custom_attribute1
				#data.append(UcfUtil.getHashStr(vo, 'custom_attribute2')) # custom_attribute2
				#data.append(UcfUtil.getHashStr(vo, 'custom_attribute3')) # custom_attribute3
				#data.append(UcfUtil.getHashStr(vo, 'custom_attribute4')) # custom_attribute4
				#data.append(UcfUtil.getHashStr(vo, 'custom_attribute5')) # custom_attribute5
				#data.append(UcfUtil.getHashStr(vo, 'custom_attribute6')) # custom_attribute6
				#data.append(UcfUtil.getHashStr(vo, 'custom_attribute7')) # custom_attribute7
				#data.append(UcfUtil.getHashStr(vo, 'custom_attribute8')) # custom_attribute8
				#data.append(UcfUtil.getHashStr(vo, 'custom_attribute9')) # custom_attribute9
				#data.append(UcfUtil.getHashStr(vo, 'custom_attribute10')) # custom_attribute10
				data.append(UcfUtil.getHashStr(vo, 'comment')) # comment

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

		logging.info('Start join csv records...')
		csv_text = '\r\n'.join(csv_records)
		logging.info('End join csv records.')

		current_memory_usage = runtime.memory_usage().current()
		gc.collect()
		current_memory_usage_after_collect = runtime.memory_usage().current()
		logging.info('current_memory_usage=' + str(current_memory_usage) + ' after_collect=' + str(current_memory_usage_after_collect))

		return csv_text
	createCsv = classmethod(createCsv)

	# csv_dataからマージ＆整備（editVoForSelectしてない生のvoにマージ）
	def margeVoFromCsvRecord(cls, helper, vo, csv_record, login_operator_entry):
		if 'user_id' in csv_record:
			vo['operator_id'] = csv_record['user_id']
			#operator_id_split = csv_record['user_id'].strip().split('@')
			#vo['operator_id_localpart'] = operator_id_split[0]
			#vo['federated_domain'] = operator_id_split[1] if len(operator_id_split) >= 2 else ''
		if 'email' in csv_record:
			vo['mail_address'] = csv_record['email']
		#if csv_record.has_key('employee_id'):
		#	vo['employee_id'] = csv_record['employee_id'].strip()
		if 'last_name' in csv_record:
			vo['last_name'] = csv_record['last_name'].strip()
		if 'first_name' in csv_record:
			vo['first_name'] = csv_record['first_name'].strip()
		if 'last_name_kana' in csv_record:
			vo['last_name_kana'] = csv_record['last_name_kana'].strip()
		if 'first_name_kana' in csv_record:
			vo['first_name_kana'] = csv_record['first_name_kana'].strip()
		if 'sub_email' in csv_record:
			vo['sub_mail_address'] = csv_record['sub_email'].strip()
		# 委託管理者なら権限系は触れないようにする
		if not ucffunc.isDelegateOperator(login_operator_entry):
			if 'access_authority' in csv_record:
				vo['access_authority'] = csv_record['access_authority'].strip()
			#if csv_record.has_key('delegate_function'):
			#	vo['delegate_function'] = csv_record['delegate_function'].strip()
			#if csv_record.has_key('delegate_management_groups'):
			#	vo['delegate_management_groups'] = csv_record['delegate_management_groups'].strip()
		#if csv_record.has_key('main_group'):
		#	vo['main_group_id'] = csv_record['main_group'].strip().lower()
		#if csv_record.has_key('profile_id'):
		#	vo['profile_infos'] = csv_record['profile_id'].strip()
		if 'language' in csv_record:
			vo['language'] = csv_record['language'].strip()
		#if csv_record.has_key('management_group'):
		#	vo['management_group'] = csv_record['management_group'].strip()
		if 'account_stop' in csv_record:
			vo['account_stop_flag'] = csv_record['account_stop'].strip()
		if 'password_change' in csv_record:
			vo['next_password_change_flag'] = csv_record['password_change'].strip()
		if 'password_expire' in csv_record:
			vo['password_expire'] = csv_record['password_expire'].strip()
		if 'login_lock' in csv_record:
			vo['login_lock_flag'] = csv_record['login_lock'].strip()
		if 'login_lock_expire' in csv_record:
			vo['login_lock_expire'] = csv_record['login_lock_expire'].strip()
		if 'password' in csv_record and 'password_update_flag' in csv_record and csv_record['password_update_flag'] == 'UPDATE':
			vo['password'] = helper.encryptoData(csv_record['password'].strip(), enctype='AES')		# パスワード暗号化
			vo['password_enctype'] = 'AES'
		#if csv_record.has_key('company'):
		#	vo['contact_company'] = csv_record['company'].strip()
		#if csv_record.has_key('company_office'):
		#	vo['contact_company_office'] = csv_record['company_office'].strip()
		#if csv_record.has_key('company_department'):
		#	vo['contact_company_department'] = csv_record['company_department'].strip()
		#if csv_record.has_key('company_department2'):
		#	vo['contact_company_department2'] = csv_record['company_department2'].strip()
		#if csv_record.has_key('job_title'):
		#	vo['contact_company_post'] = csv_record['job_title'].strip()
		#if csv_record.has_key('email_work'):
		#	vo['contact_email1'] = csv_record['email_work'].strip()
		#if csv_record.has_key('email_work_phone'):
		#	vo['contact_email2'] = csv_record['email_work_phone'].strip()
		#if csv_record.has_key('phone_work'):
		#	vo['contact_tel_no1'] = csv_record['phone_work'].strip()
		#if csv_record.has_key('fax_work'):
		#	vo['contact_tel_no2'] = csv_record['fax_work'].strip()
		#if csv_record.has_key('mobile_phone'):
		#	vo['contact_tel_no3'] = csv_record['mobile_phone'].strip()
		#if csv_record.has_key('extension_number'):
		#	vo['contact_tel_no4'] = csv_record['extension_number'].strip()
		#if csv_record.has_key('pocketbell'):
		#	vo['contact_tel_no5'] = csv_record['pocketbell'].strip()
		#if csv_record.has_key('postal_country'):
		#	vo['contact_postal_country'] = csv_record['postal_country'].strip()
		#if csv_record.has_key('postal_code'):
		#	vo['contact_postal_code'] = csv_record['postal_code'].strip()
		#if csv_record.has_key('postal_prefecture'):
		#	vo['contact_postal_prefecture'] = csv_record['postal_prefecture'].strip()
		#if csv_record.has_key('postal_city'):
		#	vo['contact_postal_city'] = csv_record['postal_city'].strip()
		#if csv_record.has_key('postal_street_address'):
		#	vo['contact_postal_street_address'] = csv_record['postal_street_address'].strip()
		#if csv_record.has_key('custom_attribute1'):
		#	vo['custom_attribute1'] = csv_record['custom_attribute1'].strip()
		#if csv_record.has_key('custom_attribute2'):
		#	vo['custom_attribute2'] = csv_record['custom_attribute2'].strip()
		#if csv_record.has_key('custom_attribute3'):
		#	vo['custom_attribute3'] = csv_record['custom_attribute3'].strip()
		#if csv_record.has_key('custom_attribute4'):
		#	vo['custom_attribute4'] = csv_record['custom_attribute4'].strip()
		#if csv_record.has_key('custom_attribute5'):
		#	vo['custom_attribute5'] = csv_record['custom_attribute5'].strip()
		#if csv_record.has_key('custom_attribute6'):
		#	vo['custom_attribute6'] = csv_record['custom_attribute6'].strip()
		#if csv_record.has_key('custom_attribute7'):
		#	vo['custom_attribute7'] = csv_record['custom_attribute7'].strip()
		#if csv_record.has_key('custom_attribute8'):
		#	vo['custom_attribute8'] = csv_record['custom_attribute8'].strip()
		#if csv_record.has_key('custom_attribute9'):
		#	vo['custom_attribute9'] = csv_record['custom_attribute9'].strip()
		#if csv_record.has_key('custom_attribute10'):
		#	vo['custom_attribute10'] = csv_record['custom_attribute10'].strip()
		if 'comment' in csv_record:
			vo['comment'] = csv_record['comment']

	margeVoFromCsvRecord = classmethod(margeVoFromCsvRecord)

	def getCsvTitles(cls, helper):
		#return ['command','user_id','email','last_name','first_name','last_name_kana','first_name_kana','sub_email','access_authority','delegate_function','delegate_management_groups','language','management_group','account_stop','password_change','password_expire','password_change_date','login_lock','login_lock_expire','login_count','login_failed_count','last_login_date','last_login_password_length','password','password_update_flag','company','company_office','company_department','company_department2','job_title','email_work','email_work_phone','phone_work','fax_work','mobile_phone','extension_number','pocketbell','postal_country','postal_code','postal_prefecture','postal_city','postal_street_address','custom_attribute1','custom_attribute2','custom_attribute3','custom_attribute4','custom_attribute5','custom_attribute6','custom_attribute7','custom_attribute8','custom_attribute9','custom_attribute10','comment']
		return ['command','user_id','email','last_name','first_name','last_name_kana','first_name_kana','sub_email','access_authority','language','account_stop','password_change','password_expire','password_change_date','login_lock','login_lock_expire','login_count','login_failed_count','last_login_date','last_login_password_length','password','password_update_flag','comment']
	getCsvTitles = classmethod(getCsvTitles)

	def getChangeAccountIDCsvTitles(cls, helper):
		return ['command','email','new_email']
	getChangeAccountIDCsvTitles = classmethod(getChangeAccountIDCsvTitles)


	# オペレータIDを変更（１アカウント）
	def changeOneOperatorID(cls, helper, src_email, dst_email, entry, is_operator, delegate_management_groups, record_cnt=0, is_direct_taskprocess=False, login_operator_id=''):

		MAX_RETRY_CNT = 3
		code = 0
		msg = ''
		vcmsg = None

		tenant = helper._tenant

		vc = OperatorChangeIDValidator()

		# アカウントＩＤ更新
		vo = {}
		entry_vo = {}
		entry_vo = entry.exchangeVo(helper._timezone)										# 既存データをVoに変換
		OperatorUtils.editVoForSelect(helper, entry_vo)		# データ加工（取得用）

		# 委託管理者の場合は自分がアクセスできる管理グループかをチェック
		if is_operator and not ucffunc.isDelegateTargetManagementGroup(UcfUtil.getHashStr(entry_vo, 'management_group'), delegate_management_groups):
			code = 403
			msg = helper.getMsg('MSG_INVALID_ACCESS_BY_DELEGATE_MANAGEMENT_GROUPS')
			return code, msg, vcmsg, vo


		# GAEデータベース更新

		UcfUtil.margeHash(vo, entry_vo)									# 既存データをVoにコピー
		#UcfUtil.margeHash(vo, req)										# Requestからの情報をVoにマージ
		#vo['operator_id_localpart'] = dst_email.split('@')[0]
		#vo['federated_domain'] = dst_email.split('@')[1]
		vo['operator_id'] = dst_email
		OperatorUtils.editVoForRegist(helper, vo, entry_vo, UcfConfig.EDIT_TYPE_RENEW)
		# Voからモデルにマージ
		entry.margeFromVo(vo, helper._timezone)
		# 更新日時、更新者の更新
		entry.updater_name = login_operator_id
		entry.date_changed = UcfUtil.getNow()
		## key_nameを変更（key_nameがメールアドレスになってしまっているので、やむを得ずDELETE&INSERT）
		#entry = UCFMDLOperator.changeKeyName(entry, OperatorUtils.getKey(helper, vo))
		entry.put()
		# UserEntryにレコード追加
		sateraito_func.addUpdateUserEntryTaskQueue(tenant, entry)

		# 他のテーブルの情報を更新するタスク登録＆キュー登録
		# 一括更新の場合はタスク処理部分も非同期ではなくインポートタスク内で直列に実施（デプリケーションを防ぐため）
		sync_result = {}
		sync_result['log_text'] = ''
		sync_result['execute_operator_id'] = login_operator_id
		sync_result['error_count'] = 0
		code, msg = TaskChangeIDUtils.insertTask(helper, 'change_operator_id', entry.unique_id, src_email, dst_email, sync_result, queue_name='default', is_direct_taskprocess=is_direct_taskprocess)
		# ログテーブルのサイズオーバーでエラーするので詳細はCSVインポートのログには出さない
		#if code == 0:
		#	msg = sync_result.get('log_text', '')
		return code, msg, vcmsg, vo

	changeOneOperatorID = classmethod(changeOneOperatorID)



############################################################
## バリデーションチェッククラス 
############################################################
class OperatorValidator(BaseValidator):

	# AD連携パスワード桁数制御撤廃対応の一環でパスワード更新時以外はパスワードチェックしないように対応 2017.03.17
	#def validate(self, helper, vo, operator_mail_address):
	def validate(self, helper, vo, operator_mail_address, is_without_password_check=False):

		# 初期化
		self.init()
		# チェック TODO 未対応項目に対応

		check_name = ''
		check_key = ''
		check_value = ''

		########################
		# ユーザID
		check_name = helper.getMsg('FLD_OPERATORID')
		#check_key = 'operator_id_localpart'
		check_key = 'operator_id'
		check_value = UcfUtil.getHashStr(vo, check_key)
		# 必須チェック
		if not self.needValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
		## 半角英数字チェック
		#if not self.alphabetNumberValidator(check_value, except_str=['-','_','.','@']):
		#	self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_ALPHABETNUMBER'), (check_name)))
		# 半角チェック
		if not self.hankakuValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_HANKAKU'), (check_name)))
		# 半角スペースもはじく 2017.01.23
		if check_value.find(' ') >= 0:
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_INVALID_SPACE'), (check_name)))
		# 最大長チェック
		if not self.maxLengthValidator(check_value, 255):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAXLENGTH'), (check_name, 255)))

#		########################
#		# ユーザID（ドメイン部分）
#		check_name = helper.getMsg('FLD_DOMAIN')
#		check_key = 'federated_domain'
#		check_value = UcfUtil.getHashStr(vo, check_key)
#		# 必須チェック
#		if not self.needValidator(check_value):
#			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
#		# 半角英数字チェック
#		if not self.alphabetNumberValidator(check_value, except_str=['-','_','.']):
#			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_ALPHABETNUMBER'), (check_name)))
#		## 最大長チェック：256文字（なんとなく）
#		#if not self.maxLengthValidator(check_value, 256):
#		#	self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAXLENGTH'), (check_name, 256)))

#		# ユーザーIDとドメインの長さはメールアドレス形式でまとめてチェック
#		check_value = UcfUtil.getHashStr(vo, 'operator_id_localpart') + '@' + UcfUtil.getHashStr(vo, 'federated_domain')		# メールアドレス
#		check_name = helper.getMsg('FLD_OPERATORID')
#		check_key = 'operator_id_localpart'
#		# 最大長チェック：（Salesforce：80文字）
#		if not self.maxLengthValidator(check_value, 80):
#			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAXLENGTH'), (check_name, 80)))

		########################
		# メールアドレス
		check_name = helper.getMsg('FLD_MAILADDRESS')
		check_key = 'mail_address'
		check_value = UcfUtil.getHashStr(vo, check_key)
		## 必須チェック
		#if not self.needValidator(check_value):
		#	self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
		# メールアドレス形式チェック
		if not self.mailAddressValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAILADDRESS')))
		# 最大長チェック
		if not self.maxLengthValidator(check_value, 255):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAXLENGTH'), (check_name, 255)))

		#########################
		## 社員ID
		#check_name = helper.getMsg('FLD_EMPLOYEEID')
		#check_key = 'employee_id'
		#check_value = UcfUtil.getHashStr(vo, check_key)
		## 半角チェック
		#if not self.hankakuValidator(check_value):
		#	self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_HANKAKU'), (check_name)))
		## 最大長チェック
		#if not self.maxLengthValidator(check_value, 50):
		#	self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAXLENGTH'), (check_name, 50)))


		########################
		# 姓
		check_name = helper.getMsg('FLD_LASTNAME')
		check_key = 'last_name'
		check_value = UcfUtil.getHashStr(vo, check_key)
		## 必須チェック
		#if not self.needValidator(check_value):
		#	self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
		# 最大長チェック：80文字
		if not self.maxLengthValidator(check_value, 80):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAXLENGTH'), (check_name, 80)))

		########################
		# 名
		check_name = helper.getMsg('FLD_FIRSTNAME')
		check_key = 'first_name'
		check_value = UcfUtil.getHashStr(vo, check_key)
		## 必須チェック
		#if not self.needValidator(check_value):
		#	self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
		# 最大長チェック：80文字
		if not self.maxLengthValidator(check_value, 80):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAXLENGTH'), (check_name, 80)))

		########################
		# 予備のメールアドレス
		check_name = helper.getMsg('FLD_SUBMAILADDRESS')
		check_key = 'sub_mail_address'
		check_value = UcfUtil.getHashStr(vo, check_key)
		# メールアドレス形式チェック
		if not self.mailAddressValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAILADDRESS')))
		# 最大長チェック
		if not self.maxLengthValidator(check_value, 255):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAXLENGTH'), (check_name, 255)))

		########################
		# パスワード ※管理では、強度設定に伴うチェックはしない

		# AD連携パスワード桁数制御撤廃対応：一環でパスワード更新時以外はパスワードチェックしないように対応 2017.03.17
		if not is_without_password_check:
			check_name = helper.getMsg('FLD_PASSWORD')
			check_key = 'password'
			check_value = UcfUtil.getHashStr(vo, check_key)
			# ログインしないユーザーデータも同じテーブルなので必須にはしない
			## 必須チェック
			#if not self.needValidator(check_value):
			#	self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
			# 半角チェック
			if not self.hankakuValidator(check_value):
				self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_HANKAKU'), (check_name)))
			# 半角スペースもはじく 2017.01.23
			if check_value.find(' ') >= 0:
				self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_INVALID_SPACE'), (check_name)))
			# バックスラッシュとして「a5」が使われている場合ははじく（Appsパスワードとして使えないので）
			if check_value.find(u'\xa5') >= 0:
				self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_INVALID_BACKSLASH_A5'), (check_name)))
			# 最大長チェック：100文字
			if not self.maxLengthValidator(check_value, 100):
				self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAXLENGTH'), (check_name, 100)))
			# 最小長チェック：8文字
			if not self.minLengthValidator(check_value, 8):
				self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MINLENGTH'), (check_name, 8)))

		####################################
		# パスワード期限
		check_name = helper.getMsg('FLD_PASSWORDEXPIRE')
		check_key = 'password_expire'
		check_value = UcfUtil.getHashStr(vo, check_key)
		# 日付型チェック
		if not self.dateValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_DATE'), (check_name)))

		####################################
		# ロック期日
		check_name = helper.getMsg('FLD_LOGINLOCKEXPIRE')
		check_key = 'login_lock_expire'
		check_value = UcfUtil.getHashStr(vo, check_key)
		# 日付型チェック
		if not self.dateValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_DATE'), (check_name)))

		####################################
		# 言語
		check_name = helper.getMsg('VMSG_LANGUAGE')
		check_key = 'language'
		check_value = UcfUtil.getHashStr(vo, check_key)
		# パターンチェック
		if not self.listPatternValidator(check_value, sateraito_func.ACTIVE_LANGUAGES):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MATCHING'), (check_name, UcfUtil.listToCsv(sateraito_func.ACTIVE_LANGUAGES))))

		#########################
		## 管理グループ
		#check_name = helper.getMsg('FLD_MANAGEMENT_GROUP')
		#check_key = 'management_group'
		#check_value = UcfUtil.getHashStr(vo, check_key)
		#if self.is_check_management_group and (self.delegate_management_groups is not None and len(self.delegate_management_groups) > 0) and (check_value == '' or not self.listPatternValidator(check_value, self.delegate_management_groups)):
		#	self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_OUTOF_DELEGATE_MANAGEMENT_GROUPS'), (check_name,UcfUtil.listToCsv(self.delegate_management_groups))))


		########################
		# 権限
		record_mail_address = ''
		#if vo.has_key('operator_id_localpart'):
		#	record_mail_address = UcfUtil.getHashStr(vo, 'operator_id_localpart') + '@' + UcfUtil.getHashStr(vo, 'federated_domain')		# メールアドレス
		#else:
		#	record_mail_address = UcfUtil.getHashStr(vo, 'operator_id')
		record_mail_address = UcfUtil.getHashStr(vo, 'operator_id')

		check_name = helper.getMsg('FLD_ACCESS_AUTHORITY')
		check_key = 'access_authority'
		check_value = UcfUtil.getHashStr(vo, check_key)
		if not self.listPatternValidator(check_value, [UcfConfig.ACCESS_AUTHORITY_ADMIN,UcfConfig.ACCESS_AUTHORITY_OPERATOR,UcfConfig.ACCESS_AUTHORITY_MANAGER]):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MATCHING'), (check_name,UcfConfig.ACCESS_AUTHORITY_ADMIN + ',' + UcfConfig.ACCESS_AUTHORITY_OPERATOR + ',' + UcfConfig.ACCESS_AUTHORITY_MANAGER)))
		# ログインユーザー自身のレコードの場合、一般ユーザーにセットされないようにチェック
		elif operator_mail_address != '' and operator_mail_address.lower() == record_mail_address.lower() and not self.listPatternValidator(check_value, [UcfConfig.ACCESS_AUTHORITY_ADMIN,UcfConfig.ACCESS_AUTHORITY_OPERATOR]):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NOTCHANGE_OPERATOR_ACCESS_AUTHORITY')))

		#########################
		## 委任管理機能
		#check_name = helper.getMsg('FLD_DELEGATE_FUNCTION')
		#check_key = 'delegate_function'
		#check_values = UcfUtil.csvToList(UcfUtil.getHashStr(vo, check_key))
		#if not self.listPatternValidator(check_values, [UcfConfig.DELEGATE_FUNCTION_OPERATOR_CONFIG]):
		#	self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MATCHING'), (check_name,UcfConfig.DELEGATE_FUNCTION_OPERATOR_CONFIG)))

		#########################
		## 委任管理する管理グループ
		#check_name = helper.getMsg('FLD_DELEGATE_MANAGEMENT_GROUPS')
		#check_key = 'delegate_management_groups'
		#check_values = UcfUtil.csvToList(UcfUtil.getHashStr(vo, check_key))
		#if len(check_values) > 30:
		#	self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAXITEMS'), (check_name, '30')))

		# 重複チェック （ユーザID、社員ID）
		if self.total_count == 0:
			unique_id = UcfUtil.getHashStr(vo, 'unique_id')

			###############################################
			# ユーザＩＤ
			operator_id = ''
			operator_id = UcfUtil.getHashStr(vo, 'operator_id')
			q = UCFMDLOperator.query()
			q = q.filter(UCFMDLOperator.operator_id_lower == operator_id.lower())
			for model in q:
				# 新規以外の場合は対象のユニークＩＤ以外の場合のみエラーとする(GQLがノットイコールに対応していないため)
				if self.edit_type == UcfConfig.EDIT_TYPE_NEW or model.unique_id != unique_id:
					self.appendValidate('operator_id', UcfMessage.getMessage(helper.getMsg('MSG_VC_ALREADY_EXIST'), ()))
					break

############################################################
## バリデーションチェッククラス：CSV用（レコードとしてのチェックはその後行う）
############################################################
class OperatorCsvValidator(BaseValidator):

	def validate(self, helper, vo):

		# 初期化
		self.init()

		check_name = ''
		check_key = ''
		check_value = ''

		########################
		# まず必須項目チェック
		# command
		check_key = 'command'
		check_name = check_key
		check_value = UcfUtil.getHashStr(vo, check_key)
		if not self.needValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
		# email
		check_key = 'user_id'
		check_name = check_key
		check_value = UcfUtil.getHashStr(vo, check_key)
		if not self.needValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))

		#######################
		# 項目チェック（CSVカラムがある場合のみ）
		# command
		check_key = 'command'
		check_name = check_key
		if check_key in vo:
			# 候補
			check_value = UcfUtil.getHashStr(vo, check_key)
			if not self.listPatternValidator(check_value, ['I','U','D','IU']):
				self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MATCHING'), (check_name,'I,U,D,IU')))

		# user_id
		check_key = 'user_id'
		check_name = check_key
		if check_key in vo:
			check_value = UcfUtil.getHashStr(vo, check_key)
			#if not self.mailAddressValidator(check_value):
			#	self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAILADDRESS')))
			#else:
			#email_domain = ''
			#if len(check_value.split('@')) >= 2:
			#	email_domain = check_value.split('@')[1].lower()
			#	#federated_domains = UcfUtil.csvToList(helper.getDeptInfo()['federated_domains'])
			#	federated_domains = sateraito_func.getFederatedDomainList(helper._tenant, is_with_cache=True)
			#	if email_domain not in federated_domains:
			#		self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_INVALID_DOMAIN')))
			pass

		# email
		check_key = 'email'
		check_name = check_key
		if check_key in vo:
			check_value = UcfUtil.getHashStr(vo, check_key)
			if not self.mailAddressValidator(check_value):
				self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAILADDRESS')))
			else:
				#email_domain = ''
				#if len(check_value.split('@')) >= 2:
				#	email_domain = check_value.split('@')[1].lower()
				#	#federated_domains = UcfUtil.csvToList(helper.getDeptInfo()['federated_domains'])
				#	federated_domains = sateraito_func.getFederatedDomainList(helper._tenant, is_with_cache=True)
				#	if email_domain not in federated_domains:
				#		self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_INVALID_DOMAIN')))
				pass

		# password
		check_key = 'password'
		check_name = check_key
		if check_key in vo:
			check_value = UcfUtil.getHashStr(vo, check_key)
			# 半角チェック（全角だとこの後の暗号化処理でシステムエラーとなるので）
			if not self.hankakuValidator(check_value):
				self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_HANKAKU'), (check_name)))

		# password_update_flag
		check_key = 'password_update_flag'
		check_name = check_key
		if check_key in vo:
			# 候補
			check_value = UcfUtil.getHashStr(vo, check_key)
			if not self.listPatternValidator(check_value, ['UPDATE']):
				self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MATCHING'), (check_name,'UPDATE')))


############################################################
## バリデーションチェッククラス （アカウントID変更）※1件用
############################################################
class OperatorChangeIDValidator(BaseValidator):

	def validate(self, helper, vo):

		# 初期化
		self.init()

		check_name = ''
		check_key = ''
		check_value = ''

		########################
		# ユーザID
		check_name = helper.getMsg('FLD_OPERATORID')
		#check_key = 'dst_accountid_localpart'
		check_key = 'dst_accountid'
		check_value = UcfUtil.getHashStr(vo, check_key)
		# 必須チェック
		if not self.needValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
		# 半角チェック
		if not self.hankakuValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_HANKAKU'), (check_name)))
		# 最大長チェック：
		if not self.maxLengthValidator(check_value, 255):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAXLENGTH'), (check_name, 255)))

#		########################
#		# ユーザID（ドメイン部分）
#		check_name = helper.getMsg('FLD_DOMAIN')
#		check_key = 'federated_domain'
#		check_value = UcfUtil.getHashStr(vo, check_key)
#		# 必須チェック
#		if not self.needValidator(check_value):
#			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))
#		# 半角英数字チェック
#		if not self.alphabetNumberValidator(check_value, except_str=['-','_','.']):
#			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_ALPHABETNUMBER'), (check_name)))
#		# 最大長チェック：255文字
#		if not self.maxLengthValidator(check_value, 255):
#			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAXLENGTH'), (check_name, 255)))

		# ユーザＩＤ（変更前）
		src_operator_id = UcfUtil.getHashStr(vo, 'src_accountid')
		# ユーザＩＤ（変更後）
		#operator_id = UcfUtil.getHashStr(vo, 'dst_accountid_localpart') + '@' + UcfUtil.getHashStr(vo, 'federated_domain')
		operator_id = UcfUtil.getHashStr(vo, 'dst_accountid')

		# 変更前と変更後が同じかどうか
		if operator_id.lower() == src_operator_id.lower():
			#self.appendValidate('dst_accountid_localpart', UcfMessage.getMessage(helper.getMsg('MSG_VC_SAMEACCOUNTID')))
			self.appendValidate('dst_accountid', UcfMessage.getMessage(helper.getMsg('MSG_VC_SAMEACCOUNTID')))

		# 重複チェック （変更後のユーザID）
		if self.total_count == 0:
			unique_id = UcfUtil.getHashStr(vo, UcfConfig.QSTRING_UNIQUEID)

			q = UCFMDLOperator.query()
			q = q.filter(UCFMDLOperator.operator_id_lower == operator_id.lower())
			for model in q:
				# 新規以外の場合は対象のユニークＩＤ以外の場合のみエラーとする(GQLがノットイコールに対応していないため)
				if self.edit_type == UcfConfig.EDIT_TYPE_NEW or model.unique_id != unique_id:
					#self.appendValidate('dst_accountid_localpart', UcfMessage.getMessage(helper.getMsg('MSG_VC_ALREADY_EXIST'), ()))
					self.appendValidate('dst_accountid', UcfMessage.getMessage(helper.getMsg('MSG_VC_ALREADY_EXIST'), ()))
					break



############################################################
## バリデーションチェッククラス：アカウントID一括変更CSV用
############################################################
class ChangeAccountIDCsvValidator(BaseValidator):

	def validate(self, helper, vo):

		# 初期化
		self.init()

		check_name = ''
		check_key = ''
		check_value = ''

		# email
		check_key = 'email'
		check_name = check_key
		check_value = UcfUtil.getHashStr(vo, check_key)
		if not self.needValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))

		# new_email
		check_key = 'new_email'
		check_name = check_key
		check_value = UcfUtil.getHashStr(vo, check_key)
		if not self.needValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))

		email = ''
		new_email = ''
		o365_sync = ''

		#######################
		# 項目チェック（CSVカラムがある場合のみ）
		# email
		check_key = 'email'
		check_name = check_key
		if check_key in vo:
			check_value = UcfUtil.getHashStr(vo, check_key)
			email = check_value
			if not self.mailAddressValidator(check_value):
				self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAILADDRESS')))
			else:
				#email_domain = ''
				#if len(check_value.split('@')) >= 2:
				#	email_domain = check_value.split('@')[1].lower()
				#	federated_domains = sateraito_func.getFederatedDomainList(helper._tenant, is_with_cache=True)
				#	if email_domain not in federated_domains:
				#		self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_INVALID_DOMAIN')))
				pass

		# new_email
		check_key = 'new_email'
		check_name = check_key
		if check_key in vo:
			check_value = UcfUtil.getHashStr(vo, check_key)
			new_email = check_value
			if not self.mailAddressValidator(check_value):
				self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAILADDRESS')))
			else:
				#email_domain = ''
				#if len(check_value.split('@')) >= 2:
				#	email_domain = check_value.split('@')[1].lower()
				#	federated_domains = sateraito_func.getFederatedDomainList(helper._tenant, is_with_cache=True)
				#	if email_domain not in federated_domains:
				#		self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_INVALID_DOMAIN')))
				pass

		# 変更前と変更後が同じかどうか
		if email.lower() == new_email.lower():
			self.appendValidate('new_email', UcfMessage.getMessage(helper.getMsg('MSG_VC_SAMEACCOUNTID')))

		# 重複チェック （変更後のユーザID）
		if self.total_count == 0:
			q = UCFMDLOperator.query()
			q = q.filter(UCFMDLOperator.operator_id_lower == new_email.lower())
			key = q.get(keys_only=True)
			if key is not None:
				self.appendValidate('new_email', UcfMessage.getMessage(helper.getMsg('MSG_VC_ALREADY_EXIST'), ()))



############################################################
## バリデーションチェッククラス （パスワード同期）
############################################################
class OperatorValidatorForPasswordSync(BaseValidator):

	def validate(self, helper, vo):

		# 初期化
		self.init()

		check_name = ''
		check_key = ''
		check_value = ''

		########################
		# パスワード ※同期APIではとりあえず強度設定に伴うチェックはしない
		check_name = helper.getMsg('FLD_PASSWORD')
		check_key = 'password'
		check_value = UcfUtil.getHashStr(vo, check_key)
		# 半角チェック
		if not self.hankakuValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_HANKAKU'), (check_name)))
		# 半角スペースもはじく 2017.01.23
		if check_value.find(' ') >= 0:
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_INVALID_SPACE'), (check_name)))
		# バックスラッシュとして「a5」が使われている場合ははじく（Appsパスワードとして使えないので.Salesforceは不明だが）
		if check_value.find(u'\xa5') >= 0:
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_INVALID_BACKSLASH_A5'), (check_name)))
		# 最大長チェック：100文字（Salesforceの要件が不明だがAppsに合わせて）
		if not self.maxLengthValidator(check_value, 100):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MAXLENGTH'), (check_name, 100)))
		# AD連携パスワード桁数制御撤廃対応：AD連携でパスワード桁数制御をしないように変更（代わりに必須チェック） 2017.03.17
		## 最小長チェック：8文字（Appsに合わせて）
		#if not self.minLengthValidator(check_value, 8):
		#	self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_MINLENGTH'), (check_name, 8)))
		# 必須チェック
		if not self.needValidator(check_value):
			self.appendValidate(check_key, UcfMessage.getMessage(helper.getMsg('MSG_VC_NEED'), (check_name)))



############################################################
## ビューヘルパー
############################################################
class OperatorViewHelper(ViewHelper):

	def applicate(self, vo, helper):
		voVH = {}

		# ここで表示用変換を必要に応じて行うが、原則Djangoテンプレートのフィルタ機能を使う
		for k,v in vo.items():
			if k == 'language':
				voVH[k] = helper.getMsg(sateraito_func.LANGUAGES_MSGID.get(v, 'VMSG_LANG_DEFAULT'))
			else:
				voVH[k] = v	
			#voVH[k] = v	

		return voVH
