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

CHAT_GPT_QUEUE_TARGET = 'f2process'

############################################################
## チャットGPT検索履歴関連
############################################################
class UserStoriesUtils():

	# キーに使用する値を取得
	@classmethod
	def getKey(cls, helper, unique_id=None):
		if unique_id is not None:
			return UcfUtil.nvl(int(''.ljust(10, '9')) - int(UcfUtil.nvl(int(time.time())).ljust(10, '0'))) + UcfConfig.KEY_PREFIX + unique_id
		else:
			return UcfUtil.nvl(int(''.ljust(10, '9')) - int(UcfUtil.nvl(int(time.time())).ljust(10, '0')))

	@classmethod
	def getById(cls, story_id, timezone=sateraito_inc.DEFAULT_TIMEZONE):
		row_dict = UCFMDLUserStories.getDict(story_id)
		if row_dict is None:
			return None
		
		book_id = row_dict['book_id']
		user_story_id = row_dict['id']

		creator_dict = UCFMDLUserInfo.getDict(row_dict['creator_id'])
		row_dict['creator'] = {
			'id': creator_dict['id'],
			'fullname': creator_dict['fullname'],
			'email': creator_dict['email'],
			'avatar_url': creator_dict['avatar_url'],
			'nickname': creator_dict['nickname'],
			'language': creator_dict['language'],
			'followers': creator_dict['followers'],
			'following': creator_dict['following'],
		}

		# q_user_chapter = UCFMDLUserChapters.query()
		# q_user_chapter = q_user_chapter.filter(UCFMDLUserChapters.book_id == book_id)
		# q_user_chapter = q_user_chapter.filter(UCFMDLUserChapters.user_story_id == user_story_id)
		# q_user_chapter = q_user_chapter.order(UCFMDLUserChapters.chapter_number)
		# user_chapter_rows = q_user_chapter.fetch()

		user_chapter_dicts = UCFMDLUserChapters.getDictList(book_id, user_story_id, timezone)

		user_chapters = []
		for item in user_chapter_dicts:
			item['created_date'] = UcfUtil.getLocalTime(item['created_date'], timezone).strftime('%Y/%m/%d %H:%M')
			item['updated_date'] = UcfUtil.getLocalTime(item['updated_date'], timezone).strftime('%Y/%m/%d %H:%M')
			user_chapters.append(item)

		row_dict['user_chapters'] = user_chapters
		if row_dict['join_with'] != 'character_default':
			row_dict['join_with'] = json.JSONDecoder().decode(row_dict['join_with'])

		row_dict['created_date'] = UcfUtil.getLocalTime(row_dict['created_date'], timezone).strftime('%Y/%m/%d %H:%M')
		row_dict['updated_date'] = UcfUtil.getLocalTime(row_dict['updated_date'], timezone).strftime('%Y/%m/%d %H:%M')
		return row_dict

	@classmethod
	def getByBookId(cls, book_id, creator_id, timezone=sateraito_inc.DEFAULT_TIMEZONE):
		row_dict = UCFMDLUserStories.getDict2(book_id, False, creator_id)
		if row_dict is None:
			return None

		user_story_id = row_dict['id']

		# user_chapters = []
		row_dict['user_chapters'] = UCFMDLUserChapters.getDictList(book_id, user_story_id, timezone)
		# for user_chapter_dict in user_chapters_dict:
		# 	user_chapters.append({
		# 		'id': user_chapter_dict['id'],
		# 		'creator_id': user_chapter_dict['creator_id'],
		# 		'user_story_id': user_chapter_dict['user_story_id'],
		# 		'book_id': user_chapter_dict['book_id'],
		# 		'del_flag': user_chapter_dict['del_flag'],
		# 		'is_good': user_chapter_dict['is_good'],
		# 		'comment': user_chapter_dict['comment'],
		# 		'title': user_chapter_dict['title'],
		# 		'idea': user_chapter_dict['idea'],
		# 		'content': user_chapter_dict['content'],
		# 		'created_date': UcfUtil.getLocalTime(user_chapter_dict['created_date'], timezone).strftime('%Y/%m/%d %H:%M'),
		# 		'updated_date': UcfUtil.getLocalTime(user_chapter_dict['updated_date'], timezone).strftime('%Y/%m/%d %H:%M'),
		# 	})
		# row_dict['user_chapters'] = user_chapters

		if row_dict['join_with'] != 'character_default':
			row_dict['join_with'] = json.JSONDecoder().decode(row_dict['join_with'])

		feedback_dict = UCFMDLFeedbackBookUsers.getDict(creator_id, user_story_id, book_id, sateraito_inc.KEY_FEEDBACK_TYPE_STORY)
		row_dict['rating_feedback'] = feedback_dict['rating'] if feedback_dict is not None else None
		row_dict['comment_feedback'] = feedback_dict['comment'] if feedback_dict is not None else None

		row_dict['created_date'] = UcfUtil.getLocalTime(row_dict['created_date'], timezone).strftime('%Y/%m/%d %H:%M')
		row_dict['updated_date'] = UcfUtil.getLocalTime(row_dict['updated_date'], timezone).strftime('%Y/%m/%d %H:%M')

		return row_dict

	@classmethod
	def getStorySharedById(cls, book_id, user_story_id, timezone=sateraito_inc.DEFAULT_TIMEZONE):
		row_dict = UCFMDLUserStories.getDict(user_story_id)
		if row_dict is None:
			return None

		user_chapters = []
		user_chapters_dict = UCFMDLUserChapters.getDictList(book_id, user_story_id, timezone)
		for user_chapter_dict in user_chapters_dict:
			user_chapters.append({
				'id': user_chapter_dict['id'],
				'creator_id': user_chapter_dict['creator_id'],
				'user_story_id': user_chapter_dict['user_story_id'],
				'book_id': user_chapter_dict['book_id'],
				'del_flag': user_chapter_dict['del_flag'],
				'is_good': user_chapter_dict['is_good'],
				'comment': user_chapter_dict['comment'],
				'title': user_chapter_dict['title'],
				'idea': user_chapter_dict['idea'],
				'content': user_chapter_dict['content'],
				'created_date': UcfUtil.getLocalTime(user_chapter_dict['created_date'], timezone).strftime('%Y/%m/%d %H:%M'),
				'updated_date': UcfUtil.getLocalTime(user_chapter_dict['updated_date'], timezone).strftime('%Y/%m/%d %H:%M'),
			})
		row_dict['user_chapters'] = user_chapters

		if row_dict['join_with'] != 'character_default':
			row_dict['join_with'] = json.JSONDecoder().decode(row_dict['join_with'])

		row_dict['created_date'] = UcfUtil.getLocalTime(row_dict['created_date'], timezone).strftime('%Y/%m/%d %H:%M')
		row_dict['updated_date'] = UcfUtil.getLocalTime(row_dict['updated_date'], timezone).strftime('%Y/%m/%d %H:%M')

		return row_dict

	@classmethod
	def getHistoryByBookId(cls, book_id, creator_id, to_dict=False, timezone=sateraito_inc.DEFAULT_TIMEZONE):

		list_history_dict = UCFMDLUserStories.getListHistoryDict(book_id, creator_id)

		data_history = []
		for row_dict in list_history_dict:
			user_story_id = row_dict['id']

			# user_chapters = []
			# user_chapters_dict = UCFMDLUserChapters.getDictList(book_id, user_story_id)
			# for user_chapter_dict in user_chapters_dict:
			# 	user_chapters.append({
			# 		'id': user_chapter_dict['id'],
			# 		'creator_id': user_chapter_dict['creator_id'],
			# 		'user_story_id': user_chapter_dict['user_story_id'],
			# 		'book_id': user_chapter_dict['book_id'],
			# 		'del_flag': user_chapter_dict['del_flag'],
			# 		'is_good': user_chapter_dict['is_good'],
			# 		'comment': user_chapter_dict['comment'],
			# 		'title': user_chapter_dict['title'],
			# 		'idea': user_chapter_dict['idea'],
			# 		'content': user_chapter_dict['content'],
			# 		'created_date': UcfUtil.getLocalTime(user_chapter_dict['created_date'], timezone).strftime('%Y/%m/%d %H:%M'),
			# 		'updated_date': UcfUtil.getLocalTime(user_chapter_dict['updated_date'], timezone).strftime('%Y/%m/%d %H:%M'),
			# 	})
			row_dict['user_chapters'] = UCFMDLUserChapters.getDictList(book_id, user_story_id, timezone)

			if row_dict['join_with'] != 'character_default':
				row_dict['join_with'] = json.JSONDecoder().decode(row_dict['join_with'])

			feedback_dict = UCFMDLFeedbackBookUsers.getDict(creator_id, user_story_id, book_id, sateraito_inc.KEY_FEEDBACK_TYPE_STORY)
			row_dict['rating_feedback'] = feedback_dict['rating'] if feedback_dict is not None else None
			row_dict['comment_feedback'] = feedback_dict['comment'] if feedback_dict is not None else None

			row_dict['created_date'] = UcfUtil.getLocalTime(row_dict['created_date'], timezone).strftime('%Y/%m/%d %H:%M')
			row_dict['updated_date'] = UcfUtil.getLocalTime(row_dict['updated_date'], timezone).strftime('%Y/%m/%d %H:%M')

			# Append row
			data_history.append(row_dict)

		logging.info(data_history)
		return data_history

	@classmethod
	def startAskChatgptWithStream(cls, helper, viewer_email, book_id, user_story_id, chapter_id, message_history, model, target=CHAT_GPT_QUEUE_TARGET, countdown=0):

		queue = taskqueue.Queue('default')
		params = {
			'viewer_email': viewer_email,
			'book_id': book_id,
			'user_story_id': user_story_id,
			'chapter_id': chapter_id,
			'message_history': message_history,
			'model': model,
		}
		task = taskqueue.Task(
			url='/api/tq/user-chapters/chatgpt-create-chapter-with-stream',
			params=params,
			target=target,
			countdown=countdown
		)

		queue.add(task)
		logging.info('add task queue chatgpt-create-chapter-with-stream')

	@classmethod
	def addTaskSummaryChapter(cls, helper, chapter_id, model, target=CHAT_GPT_QUEUE_TARGET, countdown=0):

		queue = taskqueue.Queue('default')
		params = {
			'chapter_id': chapter_id,
			'model': model,
		}
		task = taskqueue.Task(
			url='/api/tq/user-chapters/chatgpt-summary-chapter',
			params=params,
			target=target,
			countdown=countdown
		)

		queue.add(task)
		logging.info('add task queue chatgpt-create-chapter-with-stream')
