# coding: utf-8

import re,datetime
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
from ucf.config.ucfconfig import *
from ucf.config.ucfmessage import *
from ucf.utils.ucfutil import *
from utilities import IPy
#from simplejson.encoder import JSONEncoder

############################################################
## バリデーションチェック用親クラス
############################################################
class BaseValidator():

	# 入力チェック結果のトータル数
	total_count = None

	edit_type = None
	is_check_management_group = False
	delegate_management_groups = None	# 委託管理者の場合の委託管理

	# メッセージのリストのハッシュ（KEY：項目ＩＤ VALUE:メッセージリスト）
	msg = None

	def __init__(self, etp=None, is_check_management_group=False, delegate_management_groups=None):
		# クラス変数の初期化（コンストラクタで明示的に行わないとインスタンス生成時に初期化されないため）
		self.edit_type = etp
		self.is_check_management_group = is_check_management_group
		self.delegate_management_groups = delegate_management_groups
		self.init()

	def init(self):
		u'''初期化'''
		self.total_count = 0
		self.msg = {}

	def validate(self, helper, vo):
		u''' 実際に入力チェックを行うメソッド（抽象メソッドイメージ） '''
		return None

#	def msgToJson(self):
#		return JSONEncoder().encode(self.msg)
#	JsonMsg = property(msgToJson, None)

	def applicateAutoCmd(self, check_value, check_key, check_name, cmd, hashMsg=None):
		u''' 
		～AutoCmdを適用～
			[AutoCmd一覧]
　　　・N：必須チェック
			・L(xx)：最大文字列長チェック（xx:文字列長）
			・m(xx)：最小文字列長チェック（xx:文字列長）
			・l(xx)：文字列長チェック（xx:文字列長）
			・A[xx]：半角英数字チェック（xx:除外文字一覧）
			・a[xx]：半角英字チェック（xx:除外文字一覧）
			・0：半角数字チェック
			・Z：全角チェック
			・z：半角チェック
			・j：全角カタカナチェック(正規表現での実装)
			・J：全角カタカナチェック(正規表現での実装)
			・d：日付型チェック
			・M：メールアドレス型チェック
			・R(xx)：正規表現チェック（xx:正規表現パターン文字列）

			hashMsg：特別なメッセージを使用したい場合にここに指定しておくとそれを使う（TODO 未対応）

		'''


		idx = 0
		while(idx < len(cmd)):
			c = cmd[idx]

			# TODO switchしたい。switch自作しようかな。
			# 必須チェック
			if c=='N':
				if not self.needValidator(check_value):
					self.appendValidate(check_key, UcfMessage.getMessage(UcfMessage.MSG_VC_NEED, (check_name)))

			# 長さが指定長以下かチェック
			elif c=='L':
				m = re.search(r'^\((\d+)\)', cmd[idx+1:])

				if m != None:
					strLen = m.group(1)
					length = int(strLen)	# 指定長
					idx += len(strLen) + 2	# 2…()の長さ

					if not self.maxLengthValidator(check_value, length):
						self.appendValidate(check_key, UcfMessage.getMessage(UcfMessage.MSG_VC_MAXLENGTH, (check_name, UcfUtil.nvl(length))))

			# 長さが指定長以上かチェック
			elif c=='m':
				m = re.search(r'^\((\d+)\)', cmd[idx+1:])

				if m != None:
					strLen = m.group(1)
					length = int(strLen)	# 指定長
					idx += len(strLen) + 2	# 2…()の長さ

					if not self.minLengthValidator(check_value, length):
						self.appendValidate(check_key, UcfMessage.getMessage(UcfMessage.MSG_VC_MINLENGTH, (check_name, UcfUtil.nvl(length))))

			# 長さが指定長かチェック
			elif c=='l':
				m = re.search(r'^\((\d+)\)', cmd[idx+1:])

				if m != None:
					strLen = m.group(1)
					length = int(strLen)	# 指定長
					idx += len(strLen) + 2	# 2…()の長さ

					if not self.lengthValidator(check_value, length):
						self.appendValidate(check_key, UcfMessage.getMessage(UcfMessage.MSG_VC_LENGTH, (check_name, UcfUtil.nvl(length))))

			# 半角英数字チェック
			elif c=='A':
				except_str = None
				m = re.search(r'^\[([^\(\)]+)\]', cmd[idx+1:])
				if m != None:
					strExcept = m.group(1)
					idx += len(strExcept) + 2	# 2…[]の長さ

					except_str = []
					# GAEGEN2対応
					#for i in xrange(0, len(strExcept)):
					for i in range(0, len(strExcept)):
						except_str.append(strExcept[i])

				if not self.alphabetNumberValidator(check_value, except_str):
					self.appendValidate(check_key, UcfMessage.getMessage(UcfMessage.MSG_VC_ALPHABETNUMBER, (check_name)))

			# 半角英字チェック
			elif c=='a':
				except_str = None
				m = re.search(r'^\[([^\[\]]+)\]', cmd[idx+1:])
				if m != None:
					strExcept = m.group(1)
					idx += len(strExcept) + 2	# 2…[]の長さ

					except_str = []
					# GAEGEN2対応
					#for i in xrange(0, len(strExcept)):
					for i in range(0, len(strExcept)):
						except_str.append(strExcept[i])

				if not self.alphabetValidator(check_value, except_str):
					self.appendValidate(check_key, UcfMessage.getMessage(UcfMessage.MSG_VC_ALPHABET, (check_name)))

			# 半角英字チェック
			elif c=='0':
				if not self.numberValidator(check_value):
					self.appendValidate(check_key, UcfMessage.getMessage(UcfMessage.MSG_VC_NUMERIC, (check_name)))

			# 全角チェック
			elif c=='Z':
				if not self.zenkakuValidator(check_value):
					self.appendValidate(check_key, UcfMessage.getMessage(UcfMessage.MSG_VC_ZENKAKU, (check_name)))

			# 半角チェック
			elif c=='z':
				if not self.hankakuValidator(check_value):
					self.appendValidate(check_key, UcfMessage.getMessage(UcfMessage.MSG_VC_HANKAKU, (check_name)))

			#j：全角ひらがなチェック(正規表現での実装)
			elif c=='j':
				if not self.zenkakuHiraganaValidator(check_value):
					self.appendValidate(check_key, UcfMessage.getMessage(UcfMessage.MSG_VC_ZENKAKU_HIRAGANA, (check_name)))

			#J：全角カタカナチェック(正規表現での実装)
			elif c=='J':
				if not self.zenkakuKatakanaValidator(check_value):
					self.appendValidate(check_key, UcfMessage.getMessage(UcfMessage.MSG_VC_ZENKAKU_KATAKANA, (check_name)))

			# 日付型チェック
			elif c=='d':
				if not self.dateValidator(check_value):
					self.appendValidate(check_key, UcfMessage.getMessage(UcfMessage.MSG_VC_DATE, (check_name)))

			# メールアドレス型チェック
			elif c=='M':
				if not self.mailAddressValidator(check_value):
					self.appendValidate(check_key, UcfMessage.getMessage(UcfMessage.MSG_VC_MAILADDRESS_EX, (check_name)))

			# 正規表現チェック
			elif c=='R':
				m = re.search(r'^\(([^\(\)]+)\)', cmd[idx+1:])
				if m != None:
					pattern = m.group(1)
					idx += len(pattern) + 2	# 2…()の長さ

					if not self.patternValidator(check_value, pattern):
						self.appendValidate(check_key, UcfMessage.getMessage(UcfMessage.MSG_VC_REG_PATTERN, (check_name)))


			idx += 1
		

	def appendValidate(self, target_id, value):
		u''' エラーメッセージを１つ追加するメソッド '''
		if target_id not in self.msg:
			self.msg[target_id] = []
#		self.msg[target_id].append(value)
		# Django1.2バージョンアップ時、エラーメッセージが日本語の場合、文字化けするのでそれを防ぐ 2011/05/31
		self.msg[target_id].append(value)
		logging.debug(value)
		self.total_count+=1


	def needValidator(self, value):
		u'''必須チェック'''
		if not value or value == '':
			return False
		else:
			return True

	def lengthValidator(self, value, check_length):
		u'''文字列長チェック'''
		length = len(value)
		if length > 0 and length != check_length:
			return False
		else:
			return True

	def maxLengthValidator(self, value, max_length):
		u'''最大文字列長チェック'''
		length = len(value)
		if length > 0 and length > max_length:
			return False
		else:
			return True

	def minLengthValidator(self, value, min_length):
		u'''最小文字列長チェック'''
		length = len(value)
		if length > 0 and length < min_length:
			return False
		else:
			return True

	def alphabetNumberValidator(self, value, except_str=None):
		u'''半角英数字チェック'''
		# 全角文字が無視されるため変更
#		if value != '' and not value.isalnum():
		# 除外文字列対応
		if except_str != None:
			for v in except_str:
			 	value = value.replace(v, '')
		if value != '':
			if not re.match(r"[a-zA-Z0-9]+$", value):
				return False

		return True

	def alphabetValidator(self, value, except_str=None):
		u'''半角英字チェック'''
		# 全角文字が無視されるため変更
#		if value != '' and not value.isalpha():
		# 除外文字列対応
		if except_str != None:
			for v in except_str:
			 value = value.replace(v, '')
		if value != '':
			if not re.match(r"[a-zA-Z]+$", value):
				return False

		return True

	def numberValidator(self, value):
		u'''半角数字チェック'''
		# 全角文字が無視されるため変更
#		if value != '' and not value.isdigit():
		if value != '' and not re.match(r"[0-9]+$", value):
			return False
		else:
			return True

	def zenkakuValidator(self, value):
		u'''全角チェック'''
		if value != '' and not re.match(r"^[^ -~｡-ﾟ]+$", value):
			return False
		else:
			return True

	def hankakuValidator(self, value):
		u'''半角チェック'''
		if value != '' and not re.match(r"^[ -~｡-ﾟ]+$", value):
			return False
		else:
			return True

	def zenkakuHiraganaValidator(self, value):
		u'''全角ひらがなチェック'''
		if value != '' and not re.match(r"^[ぁ-ん゛゜ゝゞ]+$", value):
			return False
		else:
			return True

	def zenkakuKatakanaValidator(self, value):
		u'''全角カタカナチェック'''
		if value != '' and not re.match(r"^[ァ-ンヴーヵヶ゛゜・ヽヾ]+$", value):
			return False
		else:
			return True

	def upperValidator(self, value):
		u'''大文字チェック'''
		if value != '' and not value.isupper():
			return False
		else:
			return True

	def lowerValidator(self, value):
		u'''小文字チェック'''
		if value != '' and not value.islower():
			return False
		else:
			return True

	def alphabetUpperIncludeValidator(self, value):
		u'''大文字の半角英字が「ふくまれる」かどうかチェック'''
		if value != '':
			if not re.match(r".*[A-Z].*", value):
				return False
		return True

	def alphabetLowerIncludeValidator(self, value):
		u'''小文字の半角英字が「ふくまれる」かどうかチェック'''
		if value != '':
			if not re.match(r".*[a-z].*", value):
				return False
		return True

	def numberIncludeValidator(self, value):
		u'''半角数字が「ふくまれる」かどうかチェック'''
		if value != '':
			if not re.match(r".*[0-9].*", value):
				return False
		return True

	def markIncludeValidator(self, value):
		u'''記号が「ふくまれる」かどうかチェック'''
		if value != '':
			# 記号として( ) が含まれていなかったので追加 2016.09.01
			#if not re.match(r".*[-@/[\]^_{|}~!#$%'=`*+?,.;:\\><&].*", value):
			# ダブルコーテーションが漏れていたので追加 2017.10.23
			#if not re.match(r".*[-@/[\]^_{|}~!#$%'=`*+?,.;:\\><&\(\)].*", value):
			if not re.match(r".*[-@/[\]^_{|}~!#$%'=`*+?,.;:\\><&\(\)\"].*", value):
				return False
		return True

	def dateValidator(self, value):
		u'''日付型チェック'''
		if value != '':
			try:
				datetime.datetime.strptime(value, "%Y/%m/%d")
			except:
				try:
					datetime.datetime.strptime(value, "%Y/%m/%d %H:%M:%S")
				except:
					return False

		return True


	def mailAddressValidator(self, value):
		u'''メールアドレスチェック'''
		if value != '' and not re.match(r"^[!-Z^-~]+@[!-Z^-~]+\.[!-Z^-~]+$", value):
			return False
		else:
			# StringListPropertyに入れたりするので、カンマははじこう
			if ',' in value:
				return False
			else:
				return True

	def patternValidator(self, value, pattern):
		u'''正規表現チェック'''
		if value != '' and not re.match(pattern, value):
			return False
		else:
			return True

	def listPatternValidator(self, value, listPattern):
		u'''パターンリストチェック'''

		if isinstance(value, list):
			for list_item in value:
				if list_item not in listPattern:
					return False
			return True
		else:
			if value != '' and value not in listPattern:
				return False
			else:
				return True


	def ipAddressValidator(self, checkiplist):
		u'''
		TITLE:一覧がCIDR形式の一覧かどうかを判定
		PARAMETER:
			checkiplist:チェックするIPアドレス一覧…CIDR形式（127.0.0.1、127.0.0.1/32 ）などの一覧
			※各アイテムの前後の空白は許容される
		'''
		is_valid = False
		if checkiplist is not None:
			is_valid = True
			for checkip in checkiplist:
				checkip = checkip.strip()	# ※どっちにしてもIPy.IP では前後のスペースなどは許容されるっぽいのでここでもトリム
				if checkip is None or checkip == '':
					is_valid = False
					break
				# 0.0.0.0/0 とかだと、IPyがエラーするので、しょうがなく個別対応
				if checkip == '0.0.0.0/0' or checkip == '0.0.0.0':
					pass
				else:
#					if len(checkip.split('/')) < 2:
#						checkip = checkip + '/32'
#					logging.info(checkip)
					try:
						IPy.IP(checkip)
					except BaseException as e:
						is_valid = False
						break

		return is_valid
