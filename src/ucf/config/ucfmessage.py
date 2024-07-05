# coding: utf-8
import os,sys,datetime,time
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
from ucf.config.ucfconfig import *
from ucf.utils.ucfxml import *

import sateraito_message

############################################
## メッセージ管理クラス
############################################
class UcfMessage():

	MSG_FAILED_UPDATE_DB = u'failed update database:%s'

	def getMessage(message_template, ls_param=None):
		u'''メッセージを作成'''
		result = message_template
		#GAEGEN2対応:Python3文法対応. <> はNG.
		#if ls_param <> None and len(ls_param) > 0:
		if ls_param is not None and len(ls_param) > 0:
			try:
				result = result % ls_param
			except BaseException as instance:
				logging.warning(instance)
				logging.warning(message_template)
				result = result.replace('%s', '')
		return result
	getMessage = staticmethod(getMessage)

	# jslang.py が未使用になったためこのメソッドも未使用 2012/06/04
	# メッセージファイルの更新日時を取得（指定言語のファイルがなければ空）
	def getLangFileLastModified(approot_path,language):
		last_modified = ''
		msg_file_path = os.path.join(approot_path, 'lang', UcfConfig.MESSAGE_DEFAULT_FILE + '.xml')
		if os.path.exists(msg_file_path) == True:
			last_modified = time.ctime(os.path.getmtime(msg_file_path))
		return last_modified
	getLangFileLastModified = staticmethod(getLangFileLastModified)

	# 指定言語のメッセージ一覧を返す（sateraito_message.py 使用版）
	def getMessageListEx(language):
		msgs = None
		#GAEGEN2対応:Python3文法対応. has_key廃止.辞書型のキー存在チェックは in で行う
		#if sateraito_message.LANGUAGES.has_key(language):
		if language in sateraito_message.LANGUAGES:
			msgs = sateraito_message.LANGUAGES.get(language)
		else:
			msgs = sateraito_message.LANGUAGES.get(UcfConfig.MESSAGE_DEFAULT_LANGUAGE)
		return msgs
	getMessageListEx = staticmethod(getMessageListEx)


