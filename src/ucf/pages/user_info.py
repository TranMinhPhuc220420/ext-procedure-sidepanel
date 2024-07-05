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
from google.appengine.api import search
# from search_alt import search_auto
# from search_alt import search_replace as search
from ucf.utils.validates import BaseValidator
from ucf.utils.models import *
from ucf.utils.helpers import *
from ucf.utils.ucfutil import UcfUtil
from ucf.pages.operator import OperatorUtils
import sateraito_inc
import sateraito_func

class UserInfoUtils():

	KEY_INDEX_SEARCH = 'index_user_info_stories_ai'

	# キーに使用する値を取得
	@classmethod
	def getKey(cls, helper, unique_id=None):
		if unique_id is not None:
			return UcfUtil.nvl(int(''.ljust(10, '9')) - int(UcfUtil.nvl(int(time.time())).ljust(10, '0'))) + UcfConfig.KEY_PREFIX + unique_id
		else:
			return UcfUtil.nvl(int(''.ljust(10, '9')) - int(UcfUtil.nvl(int(time.time())).ljust(10, '0')))

	@classmethod
	def rebuildTextSearchIndex(cls, entry):
		try:
			cls.removeFromIndex(entry)
		except Exception as e:
			pass

		cls.addToTextSearchIndex(entry)

	@classmethod
	def removeFromIndex(cls, entry):
		logging.info('removeFromIndex user_info_id=' + str(entry.key.id()))

		index = search.Index(name=cls.KEY_INDEX_SEARCH)
		index.delete(entry.key.id())

	@classmethod
	def removeFromIndexById(cls, user_info_id):
		logging.info('removeFromIndex user_info_id=' + str(user_info_id))

		index = search.Index(name=cls.KEY_INDEX_SEARCH)
		index.delete(user_info_id)

	@classmethod
	def addToTextSearchIndex(cls, entry):
		logging.info('addToTextSearchIndex user_info_id=' + str(entry.key.id()))

		vo = entry.exchangeVo(sateraito_inc.DEFAULT_TIMEZONE)

		# 検索用のキーワードをセット
		keyword = ''
		keyword += ' ' + vo.get('email', '')
		keyword += ' ' + vo.get('nickname', '')
		keyword += ' ' + vo.get('fullname', '')
		keyword += ' ' + vo.get('family_name', '')
		keyword += ' ' + vo.get('given_name', '')

		logging.info(entry.created_date)
		logging.info(sateraito_func.datetimeToEpoch(entry.created_date) if entry.created_date is not None else 0)

		# GAEGEN2対応:検索API移行
		search_document = search.Document(
			doc_id=str(entry.key.id()),
			fields=[
				search.TextField(name='user_info_id', value=str(entry.key.id())),
				search.TextField(name='user_entry_id', value=vo.get('user_entry_id', '')),
				search.TextField(name='email', value=vo.get('email', '')),
				search.TextField(name='nickname', value=vo.get('nickname', '')),
				search.TextField(name='fullname', value=vo.get('fullname', '')),
				search.TextField(name='family_name', value=vo.get('family_name', '')),
				search.TextField(name='given_name', value=vo.get('given_name', '')),
				search.TextField(name='avatar_url', value=vo.get('avatar_url', '')),
				search.TextField(name='text', value=keyword),

				search.NumberField(name='created_date', value=sateraito_func.datetimeToEpoch(entry.created_date) if entry.created_date is not None else 0),
				search.NumberField(name='updated_date', value=sateraito_func.datetimeToEpoch(entry.updated_date) if entry.updated_date is not None else 0),
			])

		# GAEGEN2対応:検索API移行
		index = search.Index(name=cls.KEY_INDEX_SEARCH)
		logging.info(str(search_document))
		index.put(search_document)

		logging.info('Add success document=' + str(search_document))

	@classmethod
	def searchDocsByFullText(cls, helper, viewer_email, user_name, limit, page, offset=0):
		# フルテキスト検索でソート対象とするデータの最大件数（デフォルト1000、最大10000）
		MAX_SORT_LIMIT_FULLTEXT = 10000

		# go fulltext search
		# GAEGEN2対応:検索API移行
		# search = search_auto.get_module()
		index = search.Index(name=cls.KEY_INDEX_SEARCH)

		query_string = ''

		if user_name and user_name != '':
			query_string += ' text=~"%s"' % user_name

		# sort_expression1 = search.SortExpression(expression='created_date', direction=search.SortExpression.DESCENDING)
		# sort = search.SortOptions(expressions=[sort_expression1], limit=MAX_SORT_LIMIT_FULLTEXT)

		# Go query (using page parameter)
		logging.info('limit=' + str(limit))
		logging.info('type limit=' + str(type(limit)))
		logging.info('query_string=' + query_string)
		q_ft = search.Query(query_string=query_string, options=search.QueryOptions(
			limit=limit + 1,
			offset=((page - 1) * limit),
			sort_options=search.SortOptions(
				expressions=[
					search.SortExpression(expression='created_date', direction=search.SortExpression.DESCENDING)],
			),
		))
		results = index.search(q_ft)

		ret_results = []
		for result in results:
			item_result = cls.getDictFromTextSearchIndex(result, timezone=helper._timezone)
			ret_results.append(item_result)

		have_more_rows = False
		if len(ret_results) > limit:
			ret_results.pop()
			have_more_rows = True

		# if sateraito_inc.developer_mode:
		# 	logging.info('ret_results=' + str(ret_results))
		logging.info('result_cnt=' + str(len(ret_results)))
		return ret_results, results.number_found, have_more_rows

	# フルテキストインデックスからハッシュデータ化して返す
	@classmethod
	def getDictFromTextSearchIndex(cls, ft_result, timezone=None):
		if timezone is None:
			timezone = sateraito_inc.DEFAULT_TIMEZONE
		dict = {}
		for field in ft_result.fields:
			# if field.name in cls.getReturnedFieldsForTextSearch():
			if isinstance(field.value, str):
				dict[field.name] = field.value.strip('#')
			elif isinstance(field.value, datetime.datetime):
				dict[field.name] = UcfUtil.nvl(UcfUtil.getLocalTime(field.value, timezone))
			else:
				dict[field.name] = str(field.value)

		dict['id'] = ft_result.doc_id

		return dict

	@classmethod
	def clearAllInTextSearch(cls, helper):

		index = search.Index(name=cls.KEY_INDEX_SEARCH)

		query_string = ''
		q_ft = search.Query(query_string=query_string)
		results = index.search(q_ft)

		ret_results = []
		for result in results:
			cls.removeFromIndexById(result.doc_id)
