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

############################################################
## チャットGPT検索履歴関連
############################################################
class BookUtils():

	KEY_INDEX_SEARCH = 'index_book_stories_ai'

	# キーに使用する値を取得
	def __init__(self):
		pass

	@classmethod
	def getKey(cls, helper, unique_id=None):
		key_new_book = ''
		if unique_id is not None:
			key_new_book = UcfUtil.nvl(int(''.ljust(10, '9')) - int(UcfUtil.nvl(int(time.time())).ljust(10, '0'))) + UcfConfig.KEY_PREFIX + unique_id
		else:
			key_new_book = UcfUtil.nvl(int(''.ljust(10, '9')) - int(UcfUtil.nvl(int(time.time())).ljust(10, '0')))

		if UCFMDLBook.getInstance(key_new_book):
			return BookUtils.getKey(helper, unique_id)
		else:
			return key_new_book

	# 文書検索
	@classmethod
	def searchDocsByFullText(cls, helper, viewer_email, search_keyword, limit, title_book='', type_search='', type_book_id='', category_id='',
			   				sort_by='', just_my_book=False, just_book_of=False, of_viewer_email=None, offset=0):

		# フルテキスト検索でソート対象とするデータの最大件数（デフォルト1000、最大10000）
		MAX_SORT_LIMIT_FULLTEXT = 10000

		# go fulltext search
		# GAEGEN2対応:検索API移行
		# search = search_auto.get_module()
		index = search.Index(name=cls.KEY_INDEX_SEARCH)

		#
		# Build query string
		query_string = '(del_flag=0) AND '

		#
		# step1. perrmission
		query_string += '('
		query_string += '(status="{0}")'.format(sateraito_func.KEY_STATUS_BOOK_PUBLIC)
		if viewer_email != '':
			query_string += ' OR (status="{0}" AND share_for="{1}")'.format(sateraito_func.KEY_STATUS_BOOK_SHARE, str(viewer_email))
			query_string += ' OR (status="{0}" AND creator_id="{1}")'.format(sateraito_func.KEY_STATUS_BOOK_PRIVATE, str(viewer_email))
			query_string += ' OR (creator_id="{0}")'.format(str(viewer_email))
		query_string += ')'

		# step2. search keyword
		if search_keyword != '':
			search_keyword = search_keyword.replace('"', '\\"')
			# 1. 検索キーワード
			keyword = unicodedata.normalize('NFKC', search_keyword)
			keyword_splited = keyword.split(' ')
			keyword2 = ''
			for k in keyword_splited:
				keyword2 += ' "' + k + '"'
			keyword2 = keyword2.strip()

			query_string += ' AND (' + keyword2 + ')'
		
		if title_book != '':
			query_string += ' AND (title=' + str(title_book) + ')'

		if type_book_id != '':
			query_string += ' AND (type_book_id=' + str(type_book_id) + ')'
		if category_id != '':
			query_string += ' AND (category_book_id=' + str(category_id) + ')'

		# search just my book created
		if viewer_email != '' and just_my_book:
			query_string += ' AND (creator_id="' + str(viewer_email) + '")'
		# search just book of user entry created
		if just_book_of:
			query_string += ' AND (creator_id="' + str(of_viewer_email) + '")'

		# sort option
		if type_search == 'popular':
			query_string += ' AND (popular>0)'
			sort_expression1 = search.SortExpression(expression='popular', direction=search.SortExpression.DESCENDING)
		else:
			sort_expression1 = search.SortExpression(expression='updated_date', direction=search.SortExpression.DESCENDING)

		if sort_by == 'total_join':
			sort_expression1 = search.SortExpression(expression='total_join', direction=search.SortExpression.DESCENDING)
		elif sort_by == 'popular':
			sort_expression1 = search.SortExpression(expression='popular', direction=search.SortExpression.DESCENDING)
		elif sort_by == 'created_date':
			sort_expression1 = search.SortExpression(expression='created_date', direction=search.SortExpression.DESCENDING)
		
		sort = search.SortOptions(expressions=[sort_expression1], limit=MAX_SORT_LIMIT_FULLTEXT)

		# Go query (using page parameter)
		logging.info('limit=' + str(limit))
		logging.info('type limit=' + str(type(limit)))
		logging.info('query_string=' + query_string)
		q_ft = search.Query(query_string=query_string, options=search.QueryOptions(sort_options=sort, limit=limit, offset=offset))
		results = index.search(q_ft)

		ret_results = []
		for result in results:
			logging.info(str(result))
			ret_results.append(cls.getDictFromTextSearchIndex(result, timezone=helper._timezone))

		# if sateraito_inc.developer_mode:
		# 	logging.info('ret_results=' + str(ret_results))
		logging.info('result_cnt=' + str(len(ret_results)))

		return ret_results, results.number_found

	# 文書検索
	@classmethod
	def adminSearchDocsByFullText(cls, helper, viewer_email, search_keyword, limit, page, del_flag=None, type_search='',
																date_from='', date_to='', type_book_id='', category_id='', sort_by='', just_my_book=False, offset=0):

		# フルテキスト検索でソート対象とするデータの最大件数（デフォルト1000、最大10000）
		MAX_SORT_LIMIT_FULLTEXT = 10000

		# go fulltext search
		# GAEGEN2対応:検索API移行
		# search = search_auto.get_module()
		index = search.Index(name=cls.KEY_INDEX_SEARCH)

		#
		# Build query string
		if del_flag is not None:
			query_string = '(del_flag={0}) '.format(str(sateraito_func.boolToNumber(del_flag)))
		else:
			query_string = '(del_flag=0) '

		#
		# step1. perrmission
		# query_string += '('
		# query_string += '(status:"{0}")'.format(sateraito_func.KEY_STATUS_BOOK_PUBLIC)
		# if viewer_email != '':
		# 	query_string += ' OR (status:"{0}" AND share_for:"{1}")'.format(sateraito_func.KEY_STATUS_BOOK_SHARE, str(viewer_email))
		# 	query_string += ' OR (status:"{0}" AND creator_id:"{1}")'.format(sateraito_func.KEY_STATUS_BOOK_PRIVATE, str(viewer_email))
		# 	query_string += ' OR (creator_id:"{0}")'.format(str(viewer_email))
		# query_string += ')'

		# step2. search keyword
		if search_keyword != '':
			search_keyword = search_keyword.replace('"', '\\"')
			# 1. 検索キーワード
			keyword = unicodedata.normalize('NFKC', search_keyword)
			keyword_splited = keyword.split(' ')
			keyword2 = ''
			for k in keyword_splited:
				keyword2 += ' "' + k + '"'
			keyword2 = keyword2.strip()

			query_string += ' AND (' + keyword2 + ')'

		if type_book_id != '':
			query_string += ' AND (type_book_id=' + str(type_book_id) + ')'
		if category_id != '':
			query_string += ' AND (category_book_id=' + str(category_id) + ')'

		# search just my book created
		if viewer_email != '' and just_my_book:
			query_string += ' AND (creator_id="' + str(viewer_email) + '")'

		if date_from != '':
			date_from = datetime.datetime.strptime(date_from, sateraito_inc.FORMAT_TRANSACTION_DATE)
			date_from_unixtime = sateraito_func.datetimeToUnixtime(date_from)
			query_string += ' AND (created_date>=' + str(date_from_unixtime) + ')'

		if date_to != '':
			date_to = datetime.datetime.strptime(date_to, sateraito_inc.FORMAT_TRANSACTION_DATE)
			date_to_unixtime = sateraito_func.datetimeToUnixtime(date_to)
			query_string += ' AND (created_date<=' + str(date_to_unixtime) + ')'

		# sort option
		if type_search == 'popular':
			query_string += ' AND (popular>0)'
			sort_expression1 = search.SortExpression(expression='popular', direction=search.SortExpression.DESCENDING)
		elif sort_by == 'total_join':
			sort_expression1 = search.SortExpression(expression='total_join', direction=search.SortExpression.DESCENDING)
		elif sort_by == 'popular':
			sort_expression1 = search.SortExpression(expression='popular', direction=search.SortExpression.DESCENDING)
		elif sort_by == 'created_date':
			sort_expression1 = search.SortExpression(expression='created_date', direction=search.SortExpression.DESCENDING)
		else:
			sort_expression1 = search.SortExpression(expression='updated_date', direction=search.SortExpression.DESCENDING)
		sort = search.SortOptions(expressions=[sort_expression1])

		# Go query (using page parameter)
		logging.info('query_string=' + query_string)
		q_ft = search.Query(query_string=query_string, options=search.QueryOptions(
			limit=limit + 1,
			offset=((page - 1) * limit),
			sort_options=sort,
		))
		results = index.search(q_ft)

		ret_results = []
		for result in results:
			logging.info(str(result))
			ret_results.append(cls.getDictFromTextSearchIndex(result, timezone=helper._timezone))

		have_more_rows = False
		if len(ret_results) > limit:
			ret_results.pop()
			have_more_rows = True

		# if sateraito_inc.developer_mode:
		# 	logging.info('ret_results=' + str(ret_results))
		logging.info('result_cnt=' + str(len(ret_results)))

		return ret_results, results.number_found, have_more_rows

	@classmethod
	def rebuildTextSearchIndex(cls, entry):
		try:
			cls.removeFromIndex(entry)
		except Exception as e:
			pass

		cls.addToTextSearchIndex(entry)

	@classmethod
	def removeFromIndex(cls, entry):
		logging.info('removeFromIndex book_id=' + str(entry.key.id()))

		index = search.Index(name=cls.KEY_INDEX_SEARCH)
		index.delete(entry.key.id())

	@classmethod
	def removeFromIndexById(cls, book_id):
		logging.info('removeFromIndex book_id=' + str(book_id))

		index = search.Index(name=cls.KEY_INDEX_SEARCH)
		index.delete(book_id)

	@classmethod
	def addToTextSearchIndex(cls, entry):
		logging.info('addToTextSearchIndex book_id=' + str(entry.key.id()))

		vo = entry.exchangeVo(sateraito_inc.DEFAULT_TIMEZONE)

		# 検索用のキーワードをセット
		keyword = ''
		keyword += ' ' + vo.get('creator_id', '')
		keyword += ' ' + vo.get('title', '')
		keyword += ' ' + vo.get('summary', '')
		keyword += ' ' + vo.get('type_book_name', '')
		keyword += ' ' + vo.get('category_book_name', '')

		logging.info(entry.created_date)
		logging.info(sateraito_func.datetimeToEpoch(entry.created_date) if entry.created_date is not None else 0)

		# GAEGEN2対応:検索API移行
		search_document = search.Document(
			doc_id=str(entry.key.id()),
			fields=[
				search.NumberField(name='del_flag', value=sateraito_func.boolToNumber(vo.get('del_flag', 1))),
				search.NumberField(name='total_join', value=vo.get('total_join', 0)),
				search.NumberField(name='rate_star', value=vo.get('rate_star', 0)),
				search.NumberField(name='popular', value=vo.get('popular', 0)),

				search.TextField(name='creator_id', value=vo.get('creator_id', '')),
				search.TextField(name='status', value=vo.get('status', '')),
				search.TextField(name='share_for', value=' '.join(vo.get('share_for', []))),

				search.TextField(name='type_book_id', value=str(vo.get('type_book_id', ''))),
				search.TextField(name='type_book_name', value=vo.get('type_book_name', '')),
				search.TextField(name='category_book_id', value=str(vo.get('category_book_id', ''))),
				search.TextField(name='category_book_name', value=vo.get('category_book_name', '')),

				search.TextField(name='title', value=vo.get('title', '')),
				search.TextField(name='summary', value=vo.get('summary', '')),

				search.TextField(name='characters', value=str(vo.get('characters', ''))),
				search.TextField(name='chapters', value=str(vo.get('chapters', ''))),

				search.TextField(name='text', value=keyword),

				search.NumberField(name='created_date', value=sateraito_func.datetimeToEpoch(entry.created_date) if entry.created_date is not None else 0),
				search.NumberField(name='updated_date', value=sateraito_func.datetimeToEpoch(entry.updated_date) if entry.updated_date is not None else 0),
			])

		# GAEGEN2対応:検索API移行
		index = search.Index(name=cls.KEY_INDEX_SEARCH)
		index.put(search_document)

		logging.info('Add success document=' + str(search_document))

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
	def convertToResponse(cls, book_entry, is_dict, timezone=sateraito_inc.DEFAULT_TIMEZONE):

		if not is_dict:
			book_dict = book_entry.to_dict()
		else:
			book_dict = book_entry

		creator_dict = UCFMDLUserInfo.getDict(book_dict['creator_id'])

		creator_skill = []
		if creator_dict['skill']:
			creator_skill = json.JSONDecoder().decode(creator_dict['skill'])

		characters = json.JSONDecoder().decode(book_dict['characters'])
		chapters = json.JSONDecoder().decode(book_dict['chapters'])
		images = json.JSONDecoder().decode(book_dict['images'])
		book_cover = json.JSONDecoder().decode(book_dict['book_cover'])

		return {

			'id': book_dict['id'],

			'book_cover': book_cover,
			'images': images,

			'title': book_dict['title'],
			'summary': book_dict['summary'],

			'total_join': book_dict['total_join'],
			'rate_star': book_dict['rate_star'],
			'total_comment': book_dict['total_comment'],

			'characters': characters,
			'chapter_limit': len(chapters),
			'chapters': chapters,

			'created_date': UcfUtil.getLocalTime(book_dict['created_date'], timezone).strftime('%Y/%m/%d %H:%M'),
			'updated_date': UcfUtil.getLocalTime(book_dict['updated_date'], timezone).strftime('%Y/%m/%d %H:%M'),

			'my_story': None,
			'my_stories_history': [],

			'category': {
				'id': book_dict['category_book_id'],
				'name': book_dict['category_book_name'],
			},
			'type_book': {
				'id': book_dict['type_book_id'],
				'name': book_dict['type_book_name'],
			},
			'creator': {
				'id': book_dict['creator_id'],
				'skill': creator_skill,
				'email': creator_dict['email'],
				'avatar_url': creator_dict['avatar_url'],
				'nickname': creator_dict['nickname'],
				'gender': creator_dict['gender'],
				'date_of_birth': creator_dict['date_of_birth'],
				'description': creator_dict['description'],
				'lives_in': creator_dict['lives_in'],
				'come_from': creator_dict['come_from'],
				'works_at': creator_dict['works_at'],
				'website_url': creator_dict['website_url'],
				'twitter_url': creator_dict['twitter_url'],
				'facebook_url': creator_dict['facebook_url'],
				'instagram_url': creator_dict['instagram_url'],
				'linkedin_url': creator_dict['linkedin_url'],
				'fullname': creator_dict['fullname'],
				'family_name': creator_dict['family_name'],
				'given_name': creator_dict['given_name'],
				'language': creator_dict['language'],
			}
		}

	@classmethod
	def accessBookEntry(cls, book_entry):
		return BookUtils.accessBookDict(book_entry.to_dict())

	@classmethod
	def accessBookDict(cls, book_dict, viewer_email=None):
		# Book of user
		if book_dict['creator_id'] == viewer_email:
			return True

		# PUBLIC
		if book_dict['status'] == sateraito_func.KEY_STATUS_BOOK_PUBLIC:
			return True

		# SHARE
		if book_dict['status'] == sateraito_func.KEY_STATUS_BOOK_SHARE:
			return str(viewer_email) in book_dict['share_for']

		# PRIVATE
		if book_dict['status'] == sateraito_func.KEY_STATUS_BOOK_PRIVATE:
			return book_dict['creator_id'] == viewer_email

		return False

	@classmethod
	def accessShareBookDict(cls, book_dict, viewer_email=''):
		# Book of user
		if book_dict['creator_id'] == viewer_email:
			return True

		# PUBLIC
		if book_dict['status'] == sateraito_func.KEY_STATUS_BOOK_PUBLIC:
			return True

		return False

	@classmethod
	def addTaskUpdateByFeedback(cls, book_id):
		try:
			# token作成
			params = {
				'book_id': book_id,
			}
			# taskに追加 まるごと
			import_q = taskqueue.Queue('default')
			import_t = taskqueue.Task(
				url='/a/book/update-by-feedback',
				params=params,
				target='default',
				# countdown=10
			)
			import_q.add(import_t)
			logging.info('add task queue userentry-set-queue')
		except Exception as e:
			logging.info('failed add update book entry taskqueue.')
			logging.exception(e)

	@classmethod
	def addTaskAfterBookDelete(cls, book_id):
		try:
			# token作成
			params = {
				'book_id': book_id,
			}
			# taskに追加 まるごと
			import_q = taskqueue.Queue('default')
			import_t = taskqueue.Task(
				url='/a/book/process-after-book-delete',
				params=params,
				target='default',
				# countdown=10
			)
			import_q.add(import_t)
			logging.info('add task queue process-after-book-delete')
		except Exception as e:
			logging.info('failed add process-after-book-delete taskqueue.')
			logging.exception(e)

	@classmethod
	def addTaskAfterBookCreate(cls, book_id):
		try:
			# token作成
			params = {
				'book_id': book_id,
			}
			# taskに追加 まるごと
			import_q = taskqueue.Queue('default')
			import_t = taskqueue.Task(
				url='/a/book/process-after-book-create',
				params=params,
				target='default',
				countdown=10
			)
			import_q.add(import_t)
			logging.info('add task queue process-after-book-create')
		except Exception as e:
			logging.info('failed add process-after-book-create taskqueue.')
			logging.exception(e)

	@classmethod
	def addTaskAfterBookUpdate(cls, book_id):
		try:
			# token作成
			params = {
				'book_id': book_id,
			}
			# taskに追加 まるごと
			import_q = taskqueue.Queue('default')
			import_t = taskqueue.Task(
				url='/a/book/process-after-book-update',
				params=params,
				target='default',
				countdown=10
			)
			import_q.add(import_t)
			logging.info('add task queue process-after-book-update')
		except Exception as e:
			logging.info('failed add process-after-book-update taskqueue.')
			logging.exception(e)
