# coding: utf-8

import os,sys
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
from google.appengine.ext import db
from google.appengine.api import namespace_manager
from ucf.config.ucfconfig import *
from ucf.config.ucfmessage import *
from ucf.utils.ucfutil import *
from ucf.utils.models  import *

############################################################
## 採番：採番用クラス
############################################################
class Numbering():
	u''' 採番クラス '''

	# 採番ID
	number_id = ''
	# 採番No
	number_sub_id = ''
	# 店舗ID(必須)
	dept_id = ''
	# 接頭語
	prefix = ''
	# 数値の桁数
	sequence_no_digit = 0

	def __init__(self,_dept_id, _number_id='', _number_sub_id='001', _prefix='', _sequence_no_digit=0):
		# コンストラクタにて、使用する値を格納
		global dept_id
		global number_id
		global number_sub_id
		global prefix
		global sequence_no_digit

		dept_id = _dept_id
		number_id = _number_id
		number_sub_id = _number_sub_id
		prefix = _prefix
		sequence_no_digit = _sequence_no_digit

	def countup(self):
		strOldNamespace = namespace_manager.get_namespace()
		namespace_manager.set_namespace('')
		try:

			def getNumbering(keyNumber, number_id, number_sub_id, dept_id, prefix, sequence_no_digit):
				# 採番を行い、番号を返す。
				# また、存在しない場合は新規作成のデータを作成する。
				nextNumber = None

				datNow = UcfUtil.getNow()
				if keyNumber == None:
					# Keyが存在しない場合、新規作成
					unique_id = UcfUtil.guid()
					mdlNumber = UCFMDLNumber(unique_id=unique_id)
					# 店舗ＩＤ
					mdlNumber.dept_id = dept_id
					# コメント
					mdlNumber.comment = ''
					# 採番ＩＤ
					mdlNumber.number_id = number_id
					# 管理No
					mdlNumber.number_sub_id = number_sub_id
					# ヘッダ文字列
					mdlNumber.prefix = prefix
					# シーケンス番号
					mdlNumber.sequence_no = 1
					# シーケンス番号桁数
					mdlNumber.sequence_no_digit = sequence_no_digit
#					# 削除フラグ
#					mdlNumber.del_flag = ''
					# 作成日時、作成者の更新
					mdlNumber.creator_name = 'SYSTEM'
					mdlNumber.date_created = datNow
					mdlNumber.updater_name = 'SYSTEM'
					mdlNumber.date_changed = datNow
				else:
					# Keyが存在する場合、再取得
					mdlNumber = UCFMDLNumber.get(keyNumber)
					# シーケンス番号を増分
					mdlNumber.sequence_no = mdlNumber.sequence_no + 1
					mdlNumber.updater_name = 'SYSTEM'
					mdlNumber.date_changed = datNow
				mdlNumber.put()
				nextNumber = mdlNumber.prefix + str(mdlNumber.sequence_no).rjust(mdlNumber.sequence_no_digit ,'0')
				return nextNumber
			# gqlがトランザクション中に実行できない為、key取得用にここで実行
			gql = ""
			wheres = []
			wheres.append("dept_id='" + UcfUtil.escapeGql(dept_id) + "'")
			wheres.append("number_id='" + UcfUtil.escapeGql(number_id) + "'")
			wheres.append("number_sub_id='" + UcfUtil.escapeGql(number_sub_id) + "'")
#			wheres.append("del_flag=''")
			gql += UcfUtil.getToGqlWhereQuery(wheres)
			mdlNumber = UCFMDLNumber.gql(gql)

			keyNumber = None
			# 取得結果が存在する場合、Keyを獲得
			if mdlNumber != None:
				for model in mdlNumber:
					keyNumber= model.key()
					break
			Number = db.run_in_transaction(getNumbering,keyNumber, number_id, number_sub_id, dept_id, prefix, sequence_no_digit)
			namespace_manager.set_namespace(strOldNamespace)
			return Number
		except BaseException as e:
			msg = ''
			namespace_manager.set_namespace(strOldNamespace)
			logging.exception(e)
			raise Exception(UcfMessage.getMessage(UcfMessage.MSG_FAILED_UPDATE_DB, (msg)))

	# ロックしつつ採番データのカウントアップ、なければ新規作成を行う。
	# トランザクションから呼びだす為、記述内容に注意！

