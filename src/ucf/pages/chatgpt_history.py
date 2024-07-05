# coding: utf-8

import gc
#import logging
import sateraito_logger as logging
import unicodedata
import json
import urllib
import datetime
from google.appengine.api import taskqueue
from google.appengine.api import urlfetch
# GAEGEN2対応:検索API移行
# SearchAPIに戻す対応
from google.appengine.api import search
## from search_alt import search_auto
#from search_alt import search_replace as search
from ucf.utils.validates import BaseValidator
from ucf.utils.models import *
from ucf.utils.helpers import *
from ucf.utils.ucfutil import UcfUtil
from ucf.pages.operator import OperatorUtils
import sateraito_inc
import sateraito_func

############################################################
## チャットGPT検索履歴関連
############################################################
class ChatGPTHistoryUtils():

	# 文書検索
	@classmethod
	def searchDocsByFullText(cls, helper, search_keyword, access_date_from_epoch, access_date_to_epoch, result_code, user_id, is_login_delegate_operator, list_management_group, max_search_count, offset=0):

		# フルテキスト検索でソート対象とするデータの最大件数（デフォルト1000、最大10000）
		MAX_SORT_LIMIT_FULLTEXT = 10000

		# go fulltext search
		# GAEGEN2対応:検索API移行
		# search = search_auto.get_module()
		index = search.Index(name='chatgpt_history_index')

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
		if is_login_delegate_operator and list_management_group is not None and len(list_management_group) > 0:
			query_string += (' AND ' if query_string != '' else '') + '(management_group:['
			for i in range(len(list_management_group)):
				if i > 0:
					query_string += ' OR '
				query_string += '#' + unicodedata.normalize('NFKC', list_management_group[i].replace('"', '')) + '#'
			query_string += '])'

		if user_id != '':
			query_string += (' AND ' if query_string != '' else '') + '(user_id:' + unicodedata.normalize('NFKC', user_id.replace('"', '')) + ')'
		if result_code != '':
			query_string += (' AND ' if query_string != '' else '') + '(result_code:' + unicodedata.normalize('NFKC', result_code.replace('"', '')) + ')'

		if access_date_from_epoch != 0:
			# GAEGEN2対応：Elastic SearchのQuery対応. スペース削除、:追加　※Amazon Searchとの兼ね合いもあるので search_altライブラリ側で吸収を検討中
			#query_string += (' AND ' if query_string != '' else '') + '(access_date_epoch >= ' + str(access_date_from_epoch) + ')'
			query_string += (' AND ' if query_string != '' else '') + '(access_date_epoch:>=' + str(access_date_from_epoch) + ')'
		if access_date_to_epoch != 0:
			# GAEGEN2対応：Elastic SearchのQuery対応. スペース削除、:追加　※Amazon Searchとの兼ね合いもあるので search_altライブラリ側で吸収を検討中
			#query_string += (' AND ' if query_string != '' else '') + '(access_date_epoch < ' + str(access_date_to_epoch) + ')'
			query_string += (' AND ' if query_string != '' else '') + '(access_date_epoch:<' + str(access_date_to_epoch) + ')'

		logging.info('query_string=' + query_string)
		
		# sort option
		sort_expression1 = search.SortExpression(
	          expression='date_created_epoch',
	          direction=search.SortExpression.DESCENDING)
		sort = search.SortOptions(expressions=[sort_expression1], limit=MAX_SORT_LIMIT_FULLTEXT)
		returned_fields = UCFMDLChatHistory.getReturnedFieldsForTextSearch()
		# Go query (using page parameter)
		q_ft = search.Query(query_string=query_string, options=search.QueryOptions(sort_options=sort, limit=max_search_count, offset=offset, returned_fields=returned_fields))
		results = index.search(q_ft)
		logging.info('topic.number_found=' + str(results.number_found))

		ret_results = []
		for result in results:
			ret_results.append(UCFMDLChatHistory.getDictFromTextSearchIndex(result, timezone=helper._timezone))
		logging.info('result_cnt=' + str(len(ret_results)))
		return ret_results, results.number_found


	# 検索ボックス対応：フロント用QA検索
	@classmethod
	def searchQA(cls, helper, search_keyword, user_unique_id, user_id, session_id, max_search_count, offset=0):

		# フルテキスト検索でソート対象とするデータの最大件数（デフォルト1000、最大10000）
		MAX_SORT_LIMIT_FULLTEXT = 10000

		index = search.Index(name='chatgpt_history_index')

		#
		# Build query string
		#
		# step1. keyword
		query_string = ''
		if search_keyword != '':
			search_keyword = search_keyword.replace('"', '\\"')
			#  検索キーワード
			keyword = unicodedata.normalize('NFKC', search_keyword)
			keyword_splited = keyword.split(' ')
			keyword2 = ''
			for k in keyword_splited:
				keyword2 += ' "' + k + '"'
			keyword2 = keyword2.strip()
			query_string = keyword2 + ' '

		# ユーザーID
		if user_unique_id != '':
			query_string += (' AND ' if query_string != '' else '') + '(user_unique_id:' + unicodedata.normalize('NFKC', user_unique_id.replace('"', '')) + ')'
		elif user_id != '':
			query_string += (' AND ' if query_string != '' else '') + '(user_id:' + unicodedata.normalize('NFKC', user_id.replace('"', '')) + ')'
		elif session_id != '':
			query_string += (' AND ' if query_string != '' else '') + '(session_id:' + unicodedata.normalize('NFKC', session_id.replace('"', '')) + ')'

		# 削除フラグ
		query_string += (' AND ' if query_string != '' else '') + '(del_flag:0)'

		logging.info('query_string=' + query_string)
		
		# sort option
		sort_expression1 = search.SortExpression(
	          expression='date_created_epoch',
	          direction=search.SortExpression.DESCENDING)
		sort = search.SortOptions(expressions=[sort_expression1], limit=MAX_SORT_LIMIT_FULLTEXT)
		returned_fields = UCFMDLChatHistory.getReturnedFieldsForTextSearch()
		# Go query (using page parameter)
		q_ft = search.Query(query_string=query_string, options=search.QueryOptions(sort_options=sort, limit=max_search_count, offset=offset, returned_fields=returned_fields))
		results = index.search(q_ft)
		logging.info('topic.number_found=' + str(results.number_found))

		ret_results = []
		for result in results:
			ret_results.append(UCFMDLChatHistory.getDictFromTextSearchIndex(result, timezone=helper._timezone))
		logging.info('result_cnt=' + str(len(ret_results)))
		return ret_results, results.number_found


	@classmethod
	def _createOneCsvRecord(cls, vo):
		data = []
		data.append('IU')	# command
		data.append(UcfUtil.getHashStr(vo, 'access_date')) # access_date
		data.append(UcfUtil.getHashStr(vo, 'user_id')) # user_id
		data.append(UcfUtil.getHashStr(vo, 'client_ip')) # ipaddress
		data.append(UcfUtil.getHashStr(vo, 'result_code')) # result_code
		data.append(UcfUtil.getHashStr(vo, 'error_info')) # error_info
		data.append(UcfUtil.getHashStr(vo, 'model')) # model
		data.append(UcfUtil.getHashStr(vo, 'response_time')) # response_time
		data.append(UcfUtil.getHashStr(vo, 'action_type')) # action_type
		#data.append(UcfUtil.getHashStr(vo, 'like_status')) # like_status
		data.append(UcfUtil.getHashStr(vo, 'like_num')) # like_num
		data.append(UcfUtil.getHashStr(vo, 'unlike_num')) # unlike_num
		data.append(UcfUtil.getHashStr(vo, 'input_text_length')) # input_text_length
		data.append(UcfUtil.getHashStr(vo, 'input_text')) # input_text
		data.append(UcfUtil.getHashStr(vo, 'output_text_length')) # output_text_length
		data.append(UcfUtil.getHashStr(vo, 'output_text')) # output_text
		return data

	# エクスポート用CSVを作成
	def createCsv(cls, helper, login_operator_entry=None, optional_scond=None):

		sk_access_date_date_from = UcfUtil.getHashStr(optional_scond, 'sk_access_date_date_from') if optional_scond is not None else ''
		sk_access_date_date_to = UcfUtil.getHashStr(optional_scond, 'sk_access_date_date_to') if optional_scond is not None else ''
		sk_result_code = UcfUtil.getHashStr(optional_scond, 'sk_result_code') if optional_scond is not None else ''
		sk_user_id = UcfUtil.getHashStr(optional_scond, 'sk_user_id') if optional_scond is not None else ''
		sk_keyword = UcfUtil.getHashStr(optional_scond, 'sk_keyword') if optional_scond is not None else ''

		if sk_keyword == '' and sk_user_id == '' and sk_result_code == '' and sk_access_date_date_from == '' and sk_access_date_date_to == '':
			sk_search_type = ''
		else:
			sk_search_type = 'fulltext'

		csv_records = []
		# タイトル
		titles = ChatGPTHistoryUtils.getCsvTitles(helper)
		csv_records.append(UcfUtil.createCsvRecordEx(titles))

		# フルテキスト検索
		if sk_search_type == 'fulltext':

			sk_access_date_date_from_epoch = 0
			sk_access_date_date_to_epoch = 0

			if sk_access_date_date_from != '':
				logging.info('sk_access_date_date_from=%s' % (UcfUtil.getUTCTime(UcfUtil.getDateTime(sk_access_date_date_from + ' 00:00:00'), helper._timezone)))
				sk_access_date_date_from_epoch = sateraito_func.datetimeToEpoch(UcfUtil.getUTCTime(UcfUtil.getDateTime(sk_access_date_date_from + ' 00:00:00'), helper._timezone))

			if sk_access_date_date_to != '':
				logging.info('sk_access_date_date_to=%s' % (UcfUtil.getUTCTime(UcfUtil.add_days(UcfUtil.getDateTime(sk_access_date_date_to + ' 00:00:00'), 1), helper._timezone)))
				sk_access_date_date_to_epoch = sateraito_func.datetimeToEpoch(UcfUtil.getUTCTime(UcfUtil.add_days(UcfUtil.getDateTime(sk_access_date_date_to + ' 00:00:00'), 1), helper._timezone))

			result_list, count = ChatGPTHistoryUtils.searchDocsByFullText(helper, sk_keyword, sk_access_date_date_from_epoch, sk_access_date_date_to_epoch, sk_result_code, sk_user_id, ucffunc.isDelegateOperator(login_operator_entry), login_operator_entry.delegate_management_groups, 1000, offset=0)
			for vo in result_list:
				vo['access_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(sateraito_func.epochTodatetime(float(vo.get('access_date_epoch'))), helper._timezone)) if 'access_date_epoch' in vo and vo['access_date_epoch'] != '0.0' else ''
				vo['date_created'] = UcfUtil.nvl(UcfUtil.getLocalTime(sateraito_func.epochTodatetime(float(vo.get('date_created_epoch'))), helper._timezone)) if 'date_created_epoch' in vo and vo['date_created_epoch'] != '0.0' else ''

				ChatGPTHistoryUtils.editVoForCsv(helper, vo)
				data = ChatGPTHistoryUtils._createOneCsvRecord(vo)
				csv_records.append(UcfUtil.createCsvRecordEx(data))


		# 通常検索
		else:

			with_cursor = True

			# データ一覧取得
			q = UCFMDLChatHistory.query()
			# 委託管理者なら自分が触れるデータのみ対象
			if ucffunc.isDelegateOperator(login_operator_entry) and login_operator_entry.delegate_management_groups is not None and len(login_operator_entry.delegate_management_groups) > 0:
				q = q.filter(UCFMDLChatHistory.management_group.IN(login_operator_entry.delegate_management_groups))
				# 管理グループが複数ある場合はカーソル使えないので
				if len(login_operator_entry.delegate_management_groups) >= 2:
					with_cursor = False
			logging.info('with_cursor=' + str(with_cursor))
			q = q.order(-UCFMDLChatHistory.access_date)

			cnt = 0
			limit = 1000
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
					ChatGPTHistoryUtils.editVoForCsv(helper, vo)
					data = ChatGPTHistoryUtils._createOneCsvRecord(vo)
					csv_records.append(UcfUtil.createCsvRecordEx(data))
					each_cnt += 1

					vo = None
					entry = None
					if each_cnt % 100 == 0:
						gc.collect()

				cnt += each_cnt

				# 件数上限
				if with_cursor:
					if not more:
						break
				else:
					if each_cnt < limit:
						break

		csv_text = '\r\n'.join(csv_records)

		gc.collect()

		return csv_text
	createCsv = classmethod(createCsv)

	def getCsvTitles(cls, helper):
		#return ['command','access_date','user_id','ipaddress','result_code','error_info','model','response_time','action_type','like_status','input_text_length','input_text']
		return ['command','access_date','user_id','ipaddress','result_code','error_info','model','response_time','action_type','like_num','unlike_num','input_text_length','input_text','output_text_length','output_text']
	getCsvTitles = classmethod(getCsvTitles)

	# 取得用：データ加工（CSV用）
	def editVoForCsv(cls, helper, vo):
		pass
	editVoForCsv = classmethod(editVoForCsv)

	# 取得用：データ加工
	def editVoForSelect(cls, helper, vo):
		pass
	editVoForSelect = classmethod(editVoForSelect)

	# 既存データを取得
	def getData(cls, helper, unique_id):
		q = UCFMDLChatHistory.query()
		q = q.filter(UCFMDLChatHistory.unique_id == unique_id)
		key = q.get(keys_only=True)
		entry = key.get() if key is not None else None
		return entry
	getData = classmethod(getData)

	# キーに使用する値を取得
	def getKey(cls, helper, unique_id):
		return UcfUtil.nvl(int(''.ljust(10, '9')) - int(UcfUtil.nvl(int(time.time())).ljust(10, '0')))  + UcfConfig.KEY_PREFIX + unique_id
	getKey = classmethod(getKey)


