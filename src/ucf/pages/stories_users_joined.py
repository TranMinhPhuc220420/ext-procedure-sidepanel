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
class StoriesUsersJoinedUtils():
	# キーに使用する値を取得
	def getKey(cls, helper, unique_id=None):
		if unique_id is not None:
			return UcfUtil.nvl(int(''.ljust(10, '9')) - int(UcfUtil.nvl(int(time.time())).ljust(10, '0')))  + UcfConfig.KEY_PREFIX + unique_id
		else:
			return UcfUtil.nvl(int(''.ljust(10, '9')) - int(UcfUtil.nvl(int(time.time())).ljust(10, '0')))
	getKey = classmethod(getKey)

	@classmethod
	def getUserJoined(cls, user_id, book_id, del_flag=False):
		query = UCFMDLStoriesUsersJoined.query()
		query = query.filter(UCFMDLStoriesUsersJoined.user_id == user_id)
		query = query.filter(UCFMDLStoriesUsersJoined.book_id == book_id)
		query = query.filter(UCFMDLStoriesUsersJoined.del_flag == del_flag)

		return query.get()
