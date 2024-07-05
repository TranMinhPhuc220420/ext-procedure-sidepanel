# coding: utf-8

#import logging
import sateraito_logger as logging
from ucf.utils.validates import BaseValidator
from ucf.utils.models import *
from ucf.utils.helpers import *
from ucf.utils.models import *
import sateraito_inc
import sateraito_func


############################################################
## ファイルテーブル用メソッド
############################################################
class FileUtils():
	# 初期値用：データ加工
	def editVoForDefault(cls, helper, vo):
		pass
	editVoForDefault = classmethod(editVoForDefault)

	# チェックボックス値補正（TODO 本来はフロントからPOSTするようにExtJsなどで処理すべきが取り急ぎ）
	def setNotPostValue(cls, helper, req):
		# チェックボックス項目
		cbx_fields = [
		]
		for field in cbx_fields:
			if field[0] not in req:
				req[field[0]] = field[1]
	setNotPostValue = classmethod(setNotPostValue)

	# 取得用：データ加工
	def editVoForSelect(cls, helper, vo):
		pass
	editVoForSelect = classmethod(editVoForSelect)

	# 更新用：データ加工
	def editVoForRegist(cls, helper, vo, edit_type):

		if edit_type == UcfConfig.EDIT_TYPE_NEW:
			vo['dept_id'] = UcfUtil.getHashStr(helper.getDeptInfo(), 'dept_id')

	editVoForRegist = classmethod(editVoForRegist)

	# 既存データを取得
	def getData(cls, helper, unique_id):
		query = UCFMDLFile.gql("where unique_id = :1", UcfUtil.escapeGql(unique_id))
		entry = query.get()
		return entry
	getData = classmethod(getData)

	# キーに使用する値を取得
	def getKey(cls, helper, vo):
		# 最新ものを上に出したいので. ※TODO BigTableのInsertパフォーマンス大丈夫かなー？
		return UcfUtil.nvl(int(''.ljust(10, '9')) - int(UcfUtil.nvl(int(time.time())).ljust(10, '0')))  + UcfConfig.KEY_PREFIX + UcfUtil.getHashStr(vo, 'unique_id')
	getKey = classmethod(getKey)

	# コピー新規用に不要なデータをvoから削除
	def removeFromVoForCopyRegist(cls, helper, vo):
		vo['unique_id'] = ''
		vo['date_created'] = ''
		vo['date_changed'] = ''
		vo['creator_name'] = ''
		vo['updater_name'] = ''
		vo['updater_name'] = ''
	removeFromVoForCopyRegist = classmethod(removeFromVoForCopyRegist)


	# 既存データVoを取得 By DataKey
	def getDataVoByDataKey(cls, helper, data_key):
		vo = None
		entry = None
		if data_key and data_key != '':
			query = UCFMDLFile.gql("where data_key = :1", UcfUtil.escapeGql(data_key))
			entry = query.get()
			if entry is not None:
				vo = entry.exchangeVo(helper._timezone)
				FileUtils.editVoForSelect(helper, vo)
				# FileItemテーブル対応
				if entry.is_use_item is not None and entry.is_use_item:
					csv_text = ''
					item_query = UCFMDLFileItem.all()
					item_query.filter('data_key =', data_key)
					for item_entry in item_query.fetch(1000, 0):
						if item_entry.text_data is not None:
							csv_text += item_entry.text_data
					vo['text_data'] = csv_text

		return vo, entry
	getDataVoByDataKey = classmethod(getDataVoByDataKey)

	# 既存データを取得 By DataKey
	def getDataEntryByDataKey(cls, helper, data_key):
		entry = None
		if data_key and data_key != '':
			query = UCFMDLFile.gql("where data_key = :1", UcfUtil.escapeGql(data_key))
			entry = query.get()
		return entry
	getDataEntryByDataKey = classmethod(getDataEntryByDataKey)

	# ステータス=CREATING にて 1レコード追加しておく（フロントからの判定制御などのため）
	def insertNewCreatingRecord(cls, helper, data_key, data_kind, operator_id=''):
		unique_id = UcfUtil.guid()
		file_vo = {}
		file_vo['unique_id'] = unique_id
		file_vo['data_key'] = data_key
		file_vo['data_kind'] = data_kind
		file_vo['deal_status'] = 'CREATING'
		file_vo['status'] = ''
		FileUtils.editVoForRegist(helper, file_vo, UcfConfig.EDIT_TYPE_NEW)
		file_entry = UCFMDLFile(unique_id=unique_id,key_name=FileUtils.getKey(helper, file_vo))
		file_entry.margeFromVo(file_vo, helper._timezone)
		file_entry.updater_name = operator_id if operator_id != '' else helper.getLoginID()
		file_entry.date_changed = UcfUtil.getNow()
		file_entry.creator_name = operator_id if operator_id != '' else helper.getLoginID()
		file_entry.date_created = UcfUtil.getNow()
		file_entry.put()
		return file_entry
	insertNewCreatingRecord = classmethod(insertNewCreatingRecord)

	# キーに使用する値を取得（item_order順に並ぶように）
	def getItemKey(cls, helper, data_key, item_order):
		# 登録順にASC
		return UcfConfig.KEY_PREFIX + data_key + ('%03d' % item_order)
	getItemKey = classmethod(getItemKey)
