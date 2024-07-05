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
class UserChaptersUtils():
	# キーに使用する値を取得
	def getKey(cls, helper, unique_id=None):
		if unique_id is not None:
			return UcfUtil.nvl(int(''.ljust(10, '9')) - int(UcfUtil.nvl(int(time.time())).ljust(10, '0')))  + UcfConfig.KEY_PREFIX + unique_id
		else:
			return UcfUtil.nvl(int(''.ljust(10, '9')) - int(UcfUtil.nvl(int(time.time())).ljust(10, '0')))
	getKey = classmethod(getKey)

	def countChapter(cls, book_id, user_story_id):
		query = UCFMDLUserChapters.query()
		query = query.filter(UCFMDLUserChapters.book_id == book_id)
		query = query.filter(UCFMDLUserChapters.user_story_id == user_story_id)
		results = query.fetch()

		return len(results)
	countChapter = classmethod(countChapter)

	def getChaptersByIdStory(cls, book_id, user_story_id, to_dict=False, timezone=sateraito_inc.DEFAULT_TIMEZONE):
		query = UCFMDLUserChapters.query()
		query = query.filter(UCFMDLUserChapters.book_id == book_id)
		query = query.filter(UCFMDLUserChapters.user_story_id == user_story_id)
		query = query.order(UCFMDLUserChapters.updated_date)
		results = query.fetch()

		user_chapters = []
		for user_chapter_row in results:
			user_chapters.append(user_chapter_row.exchangeVo(timezone))

		return user_chapters
	getChaptersByIdStory = classmethod(getChaptersByIdStory)