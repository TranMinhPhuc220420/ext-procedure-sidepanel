# coding: utf-8

import binascii
# GAEGEN2対応:未使用なのでついでにコメントアウト
#import StringIO
import os,sys,math,urllib,base64,datetime,time,hashlib,random,zlib
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
from dateutil import zoneinfo, tz
# GAEGEN2対応:未使用なのでついでにコメントアウト
#from google.appengine.api import users
# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行
#from google.appengine.ext import webapp
#from google.appengine.ext.webapp import template

from ucf.config.ucfconfig import UcfConfig
#from utilities.pyDes import pyDes
import Crypto
from Crypto.Cipher import DES, AES

#GAEGEN2対応…「222.92.143.86/24」などがInvalid扱いになってしまうので最新版をカスタマイズして使用（従来のバージョンはPython3対応されていないのでNG）
#import IPy
from utilities import IPy
#from ucf.utils.validates import *

#GAEGEN2対応…requirments.txtで定義
#from utilities import pkcs7
import pkcs7	
import sateraito_inc

############################################################
## キーと値のセットクラス
############################################################
class UcfData():
	u'''キーと値のセットクラス'''
	name = None
	value = None
	value2 = None
	checked = None

	def __init__(self, k, v, v2=None, ck=False):
		# クラス変数の初期化（コンストラクタで明示的に行わないとインスタンス生成時に初期化されないため）
		self.name = k
		self.value = v
		self.value2 = v2
		self.checked = ck



############################################################
## ユーティリティクラス
############################################################
class UcfUtil():
	u'''ユーティリティクラス'''

	####################################################
	### 一般
	####################################################

	
	def datetimeToEpoch(d):
		return int(time.mktime(d.timetuple()))
	datetimeToEpoch = staticmethod(datetimeToEpoch)

	def nvl(value):
		if value is None:
			return ''
		#TODO 各クラスの文字列変換
		else:
			try:
				if isinstance(value, str):
					return value
				# GAEGEN2対応:Python3でlong型は廃止
				#elif isinstance(value, long) or isinstance(value, int) or isinstance(value, float):
				elif isinstance(value, int) or isinstance(value, float):
					return str(value)
				elif isinstance(value, datetime.datetime):
					# 307/11/11 のように、1900年未満の情報がセットされるケースがあり、復元時にエラーするのでここで対応 2020.03.05
					#return value.strftime('%Y/%m/%d %H:%M:%S')
					try:
						return value.strftime('%Y/%m/%d %H:%M:%S')
					except ValueError as e:
						if str(e).find('is before 1900') >= 0:
							return '1900/01/01 00:00:00'
						else:
							raise e
				#elif isinstance(value, unicode):
				#	return str(value)
				elif isinstance(value, Exception):
					return str(value)
				else:
					return value
			except BaseException as e:
				logging.exception(e)
				return value
	nvl = staticmethod(nvl)
	
	def toBool(value):
		if value and value.lower() == 'true':
			return True
		return False
	toBool = staticmethod(toBool)

	def toInt(value):
		return int(value) if UcfUtil.nvl(value).isdigit() else 0
	toInt = staticmethod(toInt)

	def exchangeEncoding(value):
		u''' データを出力用に文字コードを変換  2011/06/01 現在この処理は不要 '''
		# Django1.2バージョンアップ時、日本語の文字化けを防ぐ 2011/05/31
		#return unicode(UcfUtil.nvl(value)).encode(UcfConfig.ENCODING)
		return UcfUtil.nvl(value)
	exchangeEncoding = staticmethod(exchangeEncoding)

	# リストの内容が一致するかを比較
	def isSameList(list1, list2):
		is_diff = False

		if len(list1) != len(list2):
			is_diff = True
		else:
			sort_list1 = sorted(list1, reverse=False)
			sort_list2 = sorted(list2, reverse=False)
			for i in range(len(sort_list1)):
				if sort_list1[i] != sort_list2[i]:
					is_diff = True
					break

		return not is_diff
	isSameList = staticmethod(isSameList)

	def md5(value):
		m = hashlib.md5()
		# GAEGEN2対応：Python3ではstrとbyte配列を明確に区別するので encode、decode処理が必要
		#m.update(value)
		m.update(value.encode())
		return m.hexdigest()
	md5 = staticmethod(md5)

	def sha1(value):
		m = hashlib.sha1()
		# GAEGEN2対応：Python3ではstrとbyte配列を明確に区別するので encode、decode処理が必要
		#m.update(value)
		m.update(value.encode())
		return m.hexdigest()
	sha1 = staticmethod(sha1)

	def sha224(value):
		m = hashlib.sha224()
		# GAEGEN2対応：Python3ではstrとbyte配列を明確に区別するので encode、decode処理が必要
		#m.update(value)
		m.update(value.encode())
		return m.hexdigest()
	sha224 = staticmethod(sha224)

	def sha256(value):
		m = hashlib.sha256()
		# GAEGEN2対応：Python3ではstrとbyte配列を明確に区別するので encode、decode処理が必要
		#m.update(value)
		m.update(value.encode())
		return m.hexdigest()
	sha256 = staticmethod(sha256)

	def sha384(value):
		m = hashlib.sha384()
		# GAEGEN2対応：Python3ではstrとbyte配列を明確に区別するので encode、decode処理が必要
		#m.update(value)
		m.update(value.encode())
		return m.hexdigest()
	sha384 = staticmethod(sha384)

	def sha512(value):
		m = hashlib.sha512()
		# GAEGEN2対応：Python3ではstrとbyte配列を明確に区別するので encode、decode処理が必要
		#m.update(value)
		m.update(value.encode())
		return m.hexdigest()
	sha512 = staticmethod(sha512)

	def guid():
		u'''GUID生成（微妙）'''
		return UcfUtil.md5(str(time.time()) + str(random.randint(1, 10000)))
	guid = staticmethod(guid)

	#--------------------------------------
	def enCrypto(value, key, encrypto_mode=None):
		u''' DESにて暗号化
			value:暗号化したい文字列（unicodeには未対応.only ASCII.なので日本語も u'ああ'ではNG）
			key:暗号化用のキー（8byte固定）
			result:BASE64にて変換した文字列
		 '''
		result = ''
		if value != None and value != '':
			value = UcfUtil.paddingWithPKCS5(value, 8)
			key = UcfUtil.resizeBytesArray(key)
			iv = key
			cbc_or_ecb = Crypto.Cipher.DES.MODE_CBC
			if encrypto_mode is not None and encrypto_mode.lower() == 'ecb':
				cbc_or_ecb = Crypto.Cipher.DES.MODE_ECB
			# GAEGEN2対応
			#cipher = Crypto.Cipher.DES.new(key, cbc_or_ecb, iv)    # これで暗号化/復号するためのモノを作成。
			#d = cipher.encrypt(value)    # 戻り値は暗号化されたデータ。
			#result = base64.encodestring(d)
			#result = result.strip()		# 改行が入ることがあるのでトリム
			cipher = Crypto.Cipher.DES.new(key.encode(), cbc_or_ecb, iv.encode())    # これで暗号化/復号するためのモノを作成。
			d = cipher.encrypt(value.encode())    # 戻り値は暗号化されたデータ。
			result = base64.encodebytes(d)
			result = result.decode().strip()		# 改行が入ることがあるのでトリム
		else:
			result = ''
		# BASE64の仕様により改行が入る場合があるので変換
		result = result.replace('\r', '').replace('\n', '')
		return result

	enCrypto = staticmethod(enCrypto)

	#--------------------------------------
	def deCrypto(value, key, encrypto_mode=None):
		u''' DESにて復号化
			value:復号化したいBASE64文字列
			key:復号化用のキー（8byte固定）
			result:平文文字列
		 '''
		result = ''
		if value != None and value != '':
			# GAEGEN2対応
			#dec_base64 = base64.decodestring(value)
			dec_base64 = base64.decodebytes(value.encode())
			key = UcfUtil.resizeBytesArray(key)
			iv = key
			cbc_or_ecb = Crypto.Cipher.DES.MODE_CBC
			if encrypto_mode is not None and encrypto_mode.lower() == 'ecb':
				cbc_or_ecb = Crypto.Cipher.DES.MODE_ECB
			# GAEGEN2対応
			#cipher = Crypto.Cipher.DES.new(key, cbc_or_ecb, iv)    # これで暗号化/復号するためのモノを作成。
			cipher = Crypto.Cipher.DES.new(key.encode(), cbc_or_ecb, iv.encode())    # これで暗号化/復号するためのモノを作成。
			# GAEGEN2対応
			#result = cipher.decrypt(dec_base64)    # 戻り値は暗号化されたデータ。
			result = cipher.decrypt(dec_base64).decode()    # 戻り値は暗号化されたデータ。
			# 16byteの倍数にすべく終端文字でpaddingされているのでTRIM
			result = UcfUtil.unPaddingWithPKCS5(result)
		else:
			result = ''
		return result
	deCrypto = staticmethod(deCrypto)

	@classmethod
	def paddingWithPKCS5(cls, value, byte_digit):
		BYTE_DIGIT = byte_digit
		pad = lambda s: s + (BYTE_DIGIT - len(s) % BYTE_DIGIT) * chr(BYTE_DIGIT - len(s) % BYTE_DIGIT)
		value = pad(value)
		return value

	# 8byteの倍数にすべく終端文字でpaddingされているのでTRIM
	@classmethod
	def unPaddingWithPKCS5(cls, enc_value):
		unpad = lambda s: s[0:-ord(s[-1])]
		return unpad(enc_value)
				
	#--------------------------------------
	def enCryptoAESWithPKCS5(value, key, iv=None, mode=AES.MODE_CBC):
		u''' AESにて暗号化
			value:暗号化したい文字列（unicodeには未対応.only ASCII.なので日本語も u'ああ'ではNG）
			key:暗号化用のキー（32byte固定）
			result:BASE64にて変換した文字列
		 '''

		BS = 16
		pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS) 

		result = ''
		if value != None and value != '':
			raw = pad(value)
			# GAEGEN2対応
			#cipher = Crypto.Cipher.AES.new(key, mode, iv )
			#result = base64.b64encode(cipher.encrypt(raw))
			cipher = Crypto.Cipher.AES.new(key.encode(), mode, iv.encode() if iv is not None else None)
			result = base64.b64encode(cipher.encrypt(raw.encode())).decode()
		else:
			result = ''
		# BASE64の仕様により改行が入る場合があるので変換
		result = result.replace('\r', '').replace('\n', '')
		return result
	enCryptoAESWithPKCS5 = staticmethod(enCryptoAESWithPKCS5)
		
		
	#--------------------------------------
	def deCryptoAESWithPKCS5(value, key, iv=None, mode=AES.MODE_CBC):
		u''' AESにて復号化
			value:復号化したいBASE64文字列
			key:復号化用のキー（32byte固定）
			result:平文文字列
		 '''

		#unpad = lambda s : s[0:-ord(s[-1])]
		#key = '\x' + '\x'.join([key[i:i+2] for i in range(0, len(key), 2)])

		result = ''
		if value != None and value != '':
			## URLクエリーで渡される場合などに稀にスペースのままになっていることがあるのでここで「+」に変換 2020.11.26
			#value = value.replace(' ', '+')
			dec_base64 = base64.b64decode(value)
			# GAEGEN2対応
			#crypt_object = Crypto.Cipher.AES.new(key, mode, iv)
			#result = unpad(crypt_object.decrypt(dec_base64))
			cipher = Crypto.Cipher.AES.new(key.encode(), mode, iv.encode() if iv is not None else None)
			result = cipher.decrypt(dec_base64).decode()    # 戻り値は暗号化されたデータ。
			# 16byteの倍数にすべく終端文字でpaddingされているのでTRIM
			result = UcfUtil.unPaddingWithPKCS5(result)

		else:
			result = ''
		return result
	deCryptoAESWithPKCS5 = staticmethod(deCryptoAESWithPKCS5)

	#--------------------------------------
	def enCryptoAESWithPKCS7(value, key, iv=None, mode=AES.MODE_CBC):
		u''' AESにて暗号化
			value:暗号化したい文字列（unicodeには未対応.only ASCII.なので日本語も u'ああ'ではNG）
			key:暗号化用のキー（32byte固定）
			result:BASE64にて変換した文字列
		 '''

		result = ''
		if value != None and value != '':
			#encoder = PKCS7Encoder()
			#raw = encoder.encode(value)
			# GAEGEN2対応
			#if isinstance(value, unicode):
			#	value = value.encode('utf-8')
			# GAEGEN2対応
			#raw = pkcs7.encode(value).decode()
			raw = pkcs7.PKCS7Encoder().encode(value)
			# GAEGEN2対応
			#cipher = Crypto.Cipher.AES.new(key, mode, iv )
			#result = base64.b64encode(cipher.encrypt(raw))
			cipher = Crypto.Cipher.AES.new(key.encode(), mode, iv.encode() if iv is not None else None)
			result = base64.b64encode(cipher.encrypt(raw.encode())).decode()
		else:
			result = ''
		# BASE64の仕様により改行が入る場合があるので変換
		result = result.replace('\r', '').replace('\n', '')
		return result
	enCryptoAESWithPKCS7 = staticmethod(enCryptoAESWithPKCS7)
		
		
	#--------------------------------------
	def deCryptoAESWithPKCS7(value, key, iv=None, mode=AES.MODE_CBC):
		u''' AESにて復号化
			value:復号化したいBASE64文字列
			key:復号化用のキー（32byte固定）
			result:平文文字列
		 '''

		result = ''
		if value != None and value != '':
			## URLクエリーで渡される場合などに稀にスペースのままになっていることがあるのでここで「+」に変換 2020.11.26
			#value = value.replace(' ', '+')
			# GAEGEN2対応
			dec_base64 = base64.b64decode(value)
			#crypt_object = Crypto.Cipher.AES.new(key, mode, iv)
			#result = pkcs7.decode(bytearray(crypt_object.decrypt(dec_base64).encode()))
			crypt_object = Crypto.Cipher.AES.new(key.encode(), mode, iv.encode() if iv is not None else None)
			result = pkcs7.PKCS7Encoder().decode(crypt_object.decrypt(dec_base64).decode())
		else:
			result = ''
		return result
	deCryptoAESWithPKCS7 = staticmethod(deCryptoAESWithPKCS7)

	#--------------------------------------
	def enCryptoAES(value, key):
		u''' AESにて暗号化
			value:暗号化したい文字列（unicodeには未対応.only ASCII.なので日本語も u'ああ'ではNG）
			key:暗号化用のキー（32byte固定）
			result:BASE64にて変換した文字列
		 '''

		result = ''
		if value != None and value != '':

			# value は16byteの倍数でなければならないので終端文字で埋める
			value = UcfUtil._paddingValueForAESEncrypto(value)
			key = UcfUtil.resizeBytesArray(key, length=32)
			# GAEGEN2対応
			#cipher = Crypto.Cipher.AES.new(key)    # これで暗号化/復号するためのモノを作成。
			#d = cipher.encrypt(value)    # 戻り値は暗号化されたデータ。
			#result = base64.encodestring(d)
			#result = result.strip()		# 改行が入ることがあるのでトリム
			# GAEGEN2対応…モードは必須
			#cipher = Crypto.Cipher.AES.new(key.encode())    # これで暗号化/復号するためのモノを作成。
			cipher = Crypto.Cipher.AES.new(key.encode(), mode=AES.MODE_ECB)    # これで暗号化/復号するためのモノを作成。
			d = cipher.encrypt(value.encode())    # 戻り値は暗号化されたデータ。
			result = base64.encodebytes(d)
			result = result.decode().strip()		# 改行が入ることがあるのでトリム
		else:
			result = ''
		# BASE64の仕様により改行が入る場合があるので変換
		result = result.replace('\r', '').replace('\n', '')
		return result
	enCryptoAES = staticmethod(enCryptoAES)
		
		
	#--------------------------------------
	def deCryptoAES(value, key, is_with_trim=False):
		u''' AESにて復号化
			value:復号化したいBASE64文字列
			key:復号化用のキー（32byte固定）
			result:平文文字列
		 '''
		result = ''
		if value != None and value != '':
			# URLクエリーで渡される場合などに稀にスペースのままになっていることがあるのでここで「+」に変換 2020.11.26
			value = value.replace(' ', '+')
			# GAEGEN2対応
			#dec_base64 = base64.decodestring(value)
			dec_base64 = base64.decodebytes(value.encode())
			key = UcfUtil.resizeBytesArray(key, length=32)
			# GAEGEN2対応
			#cipher = Crypto.Cipher.AES.new(key)    # これで暗号化/復号するためのモノを作成。
			#result = cipher.decrypt(dec_base64)    # 戻り値は暗号化されたデータ。
			# GAEGEN2対応…モードは必須
			#cipher = Crypto.Cipher.AES.new(key.encode())    # これで暗号化/復号するためのモノを作成。
			cipher = Crypto.Cipher.AES.new(key.encode(), mode=AES.MODE_ECB)    # これで暗号化/復号するためのモノを作成。
			result = cipher.decrypt(dec_base64).decode()    # 戻り値は暗号化されたデータ。
			# 16byteの倍数にすべく終端文字でpaddingされているのでTRIM
			result = UcfUtil._trimValueForAESEncrypto(result)
		else:
			result = ''
		if is_with_trim:
			result = result.strip()
		return result
	deCryptoAES = staticmethod(deCryptoAES)

	# は16byteの倍数でなければならないので終端文字で埋める
	@classmethod
	def _paddingValueForAESEncrypto(cls, value):
		BYTE_DIGIT = 16
		value_length = len(value)
		padding_digit = value_length % BYTE_DIGIT
		if value_length == 0 or padding_digit == 0:
			return value
		# GAEGEN2対応…python3の除算は切り捨てではないため明示的にintにcast
		#return value.ljust(BYTE_DIGIT * ((value_length - 1) / BYTE_DIGIT + 1), '\0')
		return value.ljust(BYTE_DIGIT * (int((value_length - 1) / BYTE_DIGIT) + 1), '\0')

	# 16byteの倍数にすべく終端文字でpaddingされているのでTRIM
	@classmethod
	def _trimValueForAESEncrypto(cls, enc_value):
		return enc_value.rstrip('\0')


	def resizeBytesArray(key, length=8):
		u'''
		TITLE:暗号化・復号化のキーを作成
		ABSTRACT:enCrypto,deCryptoメソッド内でのみ使用するプライベートメソッド
		PARAMETER:
			key:キーとして使用する文字列
		RETURN:作成した実際のキー
		'''
		#newBytes = [0,0,0,0,0,0,0,0]
		newBytes = [0 for i in range(length)]
		#logging.info(newBytes)
		if len(key) <= length:
			for i in range(len(key)):
				newBytes[i] = ord(key[i])
		else:
			pos = 0
			for i in range(len(key)):
				if i >= length:
					c = key[i]
					int_1 = ord(c)
					int_2 = newBytes[pos]

					int_new = int_1 ^ int_2
					newBytes[pos] = int_new
					pos += 1
					if pos >= length:
						pos = 0

		# 文字列に戻す
		result = ''
		for i in range(len(newBytes)):
			result += chr(newBytes[i])

		return result
	resizeBytesArray = staticmethod(resizeBytesArray)


	#--------------------------------------
	def htmlEncode(value):
		u'''ＨＴＭＬエンコード（TODO なんちゃってメソッド）'''
		if value == None:
			return ''
		else:
			return value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

	htmlEncode = staticmethod(htmlEncode)


	#--------------------------------------
	def htmlDecode(value):
		u'''ＨＴＭＬデコード（TODO なんちゃってメソッド）'''
		if value == None:
			return ''
		else:
			return value.replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')

	htmlDecode = staticmethod(htmlDecode)

	#--------------------------------------
	def urlEncode(value, encoding=UcfConfig.ENCODING):
		if value == None:
			return ''
		else:
			#GAEGEN2対応
			#result = urllib.quote_plus(unicode(value).encode(encoding))
			result = urllib.parse.quote_plus(value.encode(encoding))
			
			return result

	urlEncode = staticmethod(urlEncode)

	def urlDecode(value):
		if value == None:
			return ''
		else:
			#GAEGEN2対応
			#result = urllib.unquote_plus(value)
			result = urllib.parse.unquote_plus(value)
			return result

	urlDecode = staticmethod(urlDecode)

	def base64Encode(value):
		if value == None:
			value = ''
		
		# SAMLマルチバイト文字列対応 edit at 2018.05.31
		#return base64.b64encode(unicode(value).encode(UcfConfig.ENCODING))
		# GAEGEN2対応
		#return base64.b64encode(value)
		return base64.b64encode(value.encode()).decode()
	base64Encode = staticmethod(base64Encode)

	def base64Decode(value):
		if value == None or value == '':
			return ''
		else:
			# GAEGEN2対応
			#return base64.b64decode(value)
			return base64.b64decode(value.encode()).decode()
	base64Decode = staticmethod(base64Decode)

	#--------------------------------------
	# deflate展開
	# Parameters:data…圧縮バイト配列
	# Result:展開後文字列
	#--------------------------------------
	def deflateDecompress(data):
		result = None
		try:
			# .NETのIO.Compression.DeflateStream で圧縮されたデータは「zlib.decompress」では解凍できないので、decompressobjを使用
			#result = zlib.decompress(data, -zlib.MAX_WBITS)
			do = zlib.decompressobj(-zlib.MAX_WBITS)
			result = do.decompress(data)
		#except zlib.error:
		# GAEGEN2対応:Python3文法対応. Exceptionの書式変更（他にも同様箇所多数あり）
		#except Exception as e:
		except Exception as e:
			logging.warning(e)
			# 一応保険的に従来の解凍方式も行うことにしておく
			result = zlib.decompress(data, -zlib.MAX_WBITS)
		return result
	deflateDecompress = staticmethod(deflateDecompress)

	def exchangeUcfURL(url):
		result = url
		return result
	exchangeUcfURL = staticmethod(exchangeUcfURL)

	def escapeForJs(value, delimiter="'"):
		u''' 文字列をJavaScript埋め込みようにエスケープする '''
		if delimiter == "'":
			return value.replace("'", "''").replace('"', '&quot;')
		elif delimiter == '"':
			return value.replace('"', '&quot;')
		else:
			return value
	escapeForJs = staticmethod(escapeForJs)

	def getHashStr(hash, key):
		u''' ハッシュから指定キーのデータを取得して返す（なければ空文字を返す） '''
		# hash.get(key, '') でいけるかも。ってことで↓
		return hash.get(key, '')

#		if hash.has_key(key):
#			return UcfUtil.nvl(hash[key]);
#		else:
#			return '';
	getHashStr = staticmethod(getHashStr)

	def removeHash(hash, key):
		u''' ハッシュから指定キーを削除（キーがなくても大丈夫） '''
		#GAEGEN2対応:Python3文法対応. has_key廃止.辞書型のキー存在チェックは in で行う
		#if hash.has_key(key):
		if key in hash:
			del hash[key];
	removeHash = staticmethod(removeHash)

	def margeHash(source, target, isOverWrite=True):
		u'''ハッシュをマージします (sourceにtargetをマージして返す)'''
		#GAEGEN2対応:Python3文法対応. iteritems廃止
		#for k,v in target.iteritems():
		for k,v in target.items():
			#GAEGEN2対応:Python3文法対応. has_key廃止.辞書型のキー存在チェックは in で行う
			#if source.has_key(k):
			if k in source:
				if isOverWrite:
					source[k] = v
			else:
					source[k] = v
	margeHash = staticmethod(margeHash)

	def keyPairToUcfDataList(pairs, encoding=False):
		u'''KeyPair一覧からUcfDataリストを生成'''
		result = []
		#GAEGEN2対応:Python3文法対応. <>はNG
		#if pairs <> None:
		if pairs is not None:
			for pair in pairs:
				if encoding == True:
					result.append( UcfData(UcfUtil.nvl(pair[0]), UcfUtil.nvl(pair[1])) )
				else:
					result.append( UcfData(pair[0], pair[1]) )
		return result
	keyPairToUcfDataList = staticmethod(keyPairToUcfDataList)

	def getNumberFormat(value):
		u'''文字列を数値型として適切なフォーマットに変換'''
		value = UcfUtil.nvl(value).strip()
		value = value.replace(',', '')
		if value == '':
			return ''
			
		# 先頭が記号なら外す
		mark = ''
		if value[0] in ['+', '-']:
			mark = value[0]
			value = value[1:]

		# 小数点があれば外す
		after_decimal_point = ''
		decimal_point_index = value.find('.')
		if decimal_point_index >= 0:
			after_decimal_point = value[decimal_point_index+1:].strip('.')
			value = value[0:decimal_point_index]

		value2 = UcfUtil.leftToRight(value)		# reverse でループすればいいような...
		result = ''
		idx = 0
		for c in value2:
			result = c + result
			idx += 1
			if idx % 3 == 0 and idx != len(value2):
				result = ',' + result

		if mark != '':
			result = mark + result
		if after_decimal_point != '':
			result = result + '.' + after_decimal_point

		return result
	getNumberFormat = staticmethod(getNumberFormat)


	def editInsertTag(target, data, start_tag, end_tag, with_html_escape=False, except_html_escape_keys=None):
		u''' データを差し込む(mailutilから移動) 2011/05/18 '''

		if data == None or (start_tag == None or start_tag == '') or (end_tag == None or end_tag == ''):
			return target

		result = target

		start_idx = result.find(start_tag)
		end_idx = result.find(end_tag)

		while start_idx >= 0 and end_idx >= 0 and start_idx < end_idx:
			
			part1 = UcfUtil.subString(result, 0, start_idx)
			part2 = UcfUtil.subString(result, end_idx + len(end_tag))
			key = UcfUtil.subString(result, start_idx + len(start_tag), end_idx - (start_idx + len(start_tag)))
			key = key.strip(' ')

			insert_data = UcfUtil.getHashStr(data, key)
			if with_html_escape and (except_html_escape_keys is None or key not in except_html_escape_keys):
				insert_data = UcfUtil.htmlEncode(insert_data)
			result = part1 + insert_data + part2
						
			start_idx = result.find(start_tag)
			end_idx = result.find(end_tag)

		return result

	editInsertTag = staticmethod(editInsertTag)



	####################################################
	### 日付関連
	####################################################

	def getNow():
		u'''UTC標準時間での現在の日時を取得'''
		# GAEGEN2対応:そのままでもUTCで取得されそうだが明示的にタイムゾーンを指定
		#return datetime.datetime.now()
		#return datetime.datetime.now(datetime.timezone.utc)
		return datetime.datetime.utcnow()
	getNow = staticmethod(getNow)

	def getNowLocalTime(timezone=sateraito_inc.DEFAULT_TIMEZONE):
		u'''ローカル時間での現在の日時を取得'''
		return UcfUtil.getLocalTime(UcfUtil.getNow(), timezone)
	getNowLocalTime = staticmethod(getNowLocalTime)

	def getLocalTime(date_utc, timezone):
		u'''UTC時間をローカル時間に変換'''
		if date_utc is not None:
			#return UcfUtil.getDateTime(date_utc, tz_hour=UcfConfig.TIME_ZONE_HOUR)
			if not isinstance(date_utc, datetime.datetime):
				date_utc = UcfUtil.getDateTime(date_utc)
			#tz_user_local = zoneinfo.gettz(UcfConfig.TIMEZONE)
			tz_user_local = zoneinfo.gettz(timezone)
			return date_utc.replace(tzinfo=tz.tzutc()).astimezone(tz_user_local).replace(tzinfo=None)
			#date_localtime_str = str(date_utc.replace(tzinfo=tz.tzutc()).astimezone(tz_user_local))
			#logging.info(date_localtime_str)
			#return UcfUtil.getDateTime(date_localtime_str)
		else:
			return datetime.datetime(1900,1,1,0,0,0)
	getLocalTime = staticmethod(getLocalTime)

	def getUTCTime(date_localtime, timezone):
		u'''ローカル時間をUTC時間に変換'''
		if date_localtime is not None:
			#return date_localtime + datetime.timedelta(hours=(UcfConfig.TIME_ZONE_HOUR * -1))
			#tz_user_local = zoneinfo.gettz(UcfConfig.TIMEZONE)
			tz_user_local = zoneinfo.gettz(timezone)
			tz_utc = tz.tzutc()
			return date_localtime.replace(tzinfo=tz_user_local).astimezone(tz_utc).replace(tzinfo=None)
			#date_utc_str = str(date_localtime.replace(tzinfo=tz_user_local).astimezone(tz_utc))
			#logging.info(date_utc_str)
			#return UcfUtil.getDateTime(date_utc_str)
		else:
			return None
	getUTCTime = staticmethod(getUTCTime)

	def getDateTime(value, tz_hour=0):
		u'''文字列や日付型を日付型に変換'''
		result = None
		if isinstance(value, datetime.datetime):
			result = value + datetime.timedelta(hours=tz_hour)
		elif value != '':
			try:
				dt = ''
				ms = ''
				temp = value.split('.')
				if len(temp) > 0:
					dt = temp[0]
				if len(temp) > 1:
					ms = temp[1]
				prtDate = ''
				prtTime = ''
				temp = dt.split(' ')
				if len(temp) > 0:
					prtDate = temp[0]
				if len(temp) > 1:
					prtTime = temp[1]

				try:
					year,month,day = [int(token) for token in prtDate.split('-')]
				except:
					year,month,day = [int(token) for token in prtDate.split('/')]
				if prtTime != '':
					hh,mm,ss = [int(token) for token in prtTime.split(':')]
				else:
					hh,mm,ss = 0, 0, 0
				result = datetime.datetime(year,month,day,hh,mm,ss)

				if prtTime != '':
					result = result + datetime.timedelta(hours=tz_hour)
			finally:
				pass
		else:
				pass
		return result
	getDateTime = staticmethod(getDateTime)


	def first_day(date):
		u"""月初を返す"""
		return datetime.date(date.year,date.month,1)
	first_day = staticmethod(first_day)

	def is_last_day(date):
		u"""月末日付ならTrueを返す"""
		return UcfUtil.days_of_month(date.year,date.month)==date.day
	is_last_day = staticmethod(is_last_day)

	def days_of_month(year,month):
		u"""年,月の日数を返す"""
		from calendar import monthrange
		return monthrange(year,month)[1]
	days_of_month = staticmethod(days_of_month)

	def last_day(date):
		u"""月末を返す"""
		return datetime.date(year=date.year,month=date.month,day=UcfUtil.days_of_month(date.year,date.month))
	last_day = staticmethod(last_day)

	def add_seconds(date,seconds):
		u'''秒を加減する。'''
		return date + datetime.timedelta(seconds=seconds)
	add_seconds = staticmethod(add_seconds)

	def add_minutes(date,minutes):
		u'''分を加減する。'''
		return date + datetime.timedelta(minutes=minutes)
	add_minutes = staticmethod(add_minutes)

	def add_hours(date,hours):
		u'''時間を加減する。'''
		return date + datetime.timedelta(hours=hours)
	add_hours = staticmethod(add_hours)

	def add_days(date,days):
		u'''日にちを加減する。'''
		return date + datetime.timedelta(days=days)
	add_days = staticmethod(add_days)

	def add_months(date,months):
		u"""月を加減する。
		dateにはdatetime.dateクラスのオブジェクト
		monthsには整数で月数を指定する。
		月末をOracleのadd_months互換の方法で処理する。
		例えば、
		2007年2月28日（月末）に1ヶ月足すと3月31日（月末）。
		2008年2月29日（月末）に1ヶ月足すと2008年3月31日（月末）。
		2008年2月28日（月末ではない）に1ヶ月足すと2008年3月28日（同じ日）。
		"""
		if months==0:return date
		year,month = divmod(date.month+months,12)
		year = year + date.year
		#ちょうど割り切れたら12月で、マイナス1年。
		if month==0:
			month = 12
			year = year - 1
		#入力日付がその月の月末なら、加算後月の日数を。
		#そうじゃなければ入力日付の日。
		day = date.day
		if date.day > UcfUtil.days_of_month(year,month):
			day = UcfUtil.days_of_month(year,month)
		return datetime.datetime(year=year,month=month,day=day,hour=date.hour,minute=date.minute,second=date.second)
	add_months = staticmethod(add_months)

	def set_time(date,hour,minute,second):
		u'''時分秒を上書きする'''
		return datetime.datetime(year=date.year,month=date.month,day=date.day,hour=hour,minute=minute,second=second)
	set_time = staticmethod(set_time)

	# 日付型の文字列が時分までの場合に秒をつける補正（Excel対策）
	def reviseSecondOfDateStr(value, original_value):
		#logging.info('value=' + str(value) + ' original_value=' + str(original_value))

		result = value
		if value is not None and value != '':
			sp1 = value.split(':')
			if len(sp1) == 2:
				# オリジナルの秒があればそれをつける。なければ00
				add_second_str = '00'
				if original_value is not None and original_value != '' and UcfUtil.startsWith(original_value, value + ':'):
					sp2 = original_value.split(':')
					if len(sp2) == 3:
						add_second_str = sp2[2]
				result = value + ':' + add_second_str

		#logging.info('src=' + str(value) + ' dst=' + str(result))
		return result
	reviseSecondOfDateStr = staticmethod(reviseSecondOfDateStr)

	####################################################
	### ＤＢ関連
	####################################################

	def escapeGql(query):
		u''' gqlに使うクエリー部品をエスケープ '''
		return query.replace("'", "''")
	escapeGql = staticmethod(escapeGql)

	def listToGqlInQuery(list):
		u'''リストからGQLのinクエリを作成'''
		result = ''
		for v in list:
			result += "'" + UcfUtil.escapeGql(v) + "'" + ","
		result = result.strip(',')
		return result
	listToGqlInQuery = staticmethod(listToGqlInQuery)

	def getToGqlWhereQuery(wheres):
		where_query = ''
		u'''リストからGQLのWHEREクエリを作成'''
		if len(wheres) > 0:
			where_query += "WHERE "
			idx = 0
			for where in wheres:
				if idx > 0:
					where_query += " AND "
				where_query += where
				idx += 1
		return where_query
	getToGqlWhereQuery = staticmethod(getToGqlWhereQuery)



	####################################################
	### ＣＳＶ関連
	####################################################

	def createCsvRecord(data, delimiter=',', crlf='\n'):
		u'''リストをＣＳＶ出力用の１レコード文字列に変換'''

		result = ''

		for i in range(len(data)):
			value = UcfUtil.nvl(data[i])
			if i > 0:
				result += delimiter
			result += UcfUtil.convertCsvField(value, delimiter)

		result += crlf
		return result
	createCsvRecord = staticmethod(createCsvRecord)

	def createCsvRecordEx(data, delimiter=','):
		u'''リストをＣＳＶ出力用の１レコード文字列に変換'''

		result = []

		for i in range(len(data)):
			value = UcfUtil.nvl(data[i])
			result.append(UcfUtil.convertCsvField(value, delimiter))

		return delimiter.join(result)
	createCsvRecordEx = staticmethod(createCsvRecordEx)


	def convertCsvField(value, delimiter=','):
		u'''文字列をＣＳＶの項目として適切にエスケープする'''

		result = ''
		
		if delimiter != '':
			# デリミタ、ダブルコーテーション、改行が含まれていればエスケープ
			if value.find(delimiter) >= 0 or value.find('"') >= 0 or value.find("\n") >= 0 or value.find("\r") >= 0:
				result = '"'  + value.replace('"', '""') + '"' 
			else:
				result = value

		else:
			# デリミタが空ならエスケープしない
			result = value

		return result
	convertCsvField = staticmethod(convertCsvField)

	def csvToList(data, delimiter=','):
		u'''指定デリミタ文字列からリストを生成'''
		result = []
		if data != "":
			result = data.split(delimiter)
		return result
	csvToList = staticmethod(csvToList)

	def listToCsv(data, delimiter=','):
		u'''リストを指定デリミタ区切り文字列に変換'''

		if data is None:
			return ''

		try:
			result = delimiter.join(data)
		except BaseException as e:
			logging.exception(e)
			logging.info('[listToCsv]retry by regacy method...')
			result = ''
			for i in range(len(data)):
				value = UcfUtil.nvl(data[i])
				if i > 0:
					result += delimiter
				result += value
		return result
	listToCsv = staticmethod(listToCsv)

	def isContainCsv(data, csv, isTrimSpace=True):
		u'''CSV文字列内に該当データが存在するかを判定'''
		if isTrimSpace:
			data = data.replace(' ', '')
			csv = csv.replace(' ', '')
		if data != "" and (',' + data + ',') in ',' + csv + ',':
			return True
		else:
			return False
	isContainCsv = staticmethod(isContainCsv)


	####################################################
	### 文字列操作関連
	####################################################
	def leftToRight(value):
		u''' 文字列を左右逆にして返す '''

		result = ''
		for c in value:
			result = c + result

		return result

	leftToRight = staticmethod(leftToRight)

	def subString(value, start_index, length=-1):
		u''' 文字列から部分文字列を抜き出す '''
		result = ''
		
		# マイナスなら最後まで
		if length < 0:
			result = value[start_index : len(value)]
		else:
			result = value[start_index : length + start_index]
		return result

	subString = staticmethod(subString)


	#+++++++++++++++++++++++++++++++++++++++
	#+++ URLにクエリーを追加
	#+++ ・ページ内リンクの考慮を追加 2016.12.02
	#+++++++++++++++++++++++++++++++++++++++
	def appendQueryString(url, query_key, query_value):
		u'''
		TITLE:URLを作成
		ABSTRACT:URLエンコードは行う
		PARAMETER:
			url:元のURL
			query_key:追加するクエリーキー
			query_value:追加するクエリーの値
		'''

		# ページ内リンクがあればまず分離
		internal_link = ''
		is_exist_internal_link = False
		if url.find('#') >= 0:
			ary_li = url.split('#')
			url = ary_li[0]
			internal_link = ary_li[1]
			is_exist_internal_link = True

		result = url
		if result.find('?') >= 0:
			result += '&' + query_key + '=' + UcfUtil.urlEncode(query_value)
		else:
			result += '?' + query_key + '=' + UcfUtil.urlEncode(query_value)

		if is_exist_internal_link:
			result += '#' + internal_link
		return result
	appendQueryString = staticmethod(appendQueryString)

	#+++++++++++++++++++++++++++++++++++++++++
	# 文字列が指定文字列から始まるかどうか
	#+++++++++++++++++++++++++++++++++++++++++
	def startsWith(str_data, check_str):
		is_start = False
		if str_data is not None and str_data != '' and check_str is not None and check_str != '':
			if len(str_data) >= len(check_str):
				start_str = str_data[0:len(check_str)]
				if start_str == check_str:
					is_start = True
		return is_start
	startsWith = staticmethod(startsWith)


	####################################################
	### メールアドレス関連
	####################################################
	def getMailDomain(mail_address):
		u'''
		TITLE:メールアドレスからドメインの取得
		PARAMETER:
			mail_address:切り出し元のメールアドレス
		'''
		# メールアドレスが空欄の時、処理終了
		if not mail_address:
			return ''

		LoginId = mail_address.split("@")
		# 文字列内に@が含まれない場合、処理終了
		if len(LoginId) <= 1:
			return mail_address
		# '@'より後ろの部分を返す
		return LoginId[1]
	getMailDomain = staticmethod(getMailDomain)


	####################################################
	### ネットワーク関連
	####################################################
	def isCheckIPAddressRange(ip, checkiplist, denyiplist=None):
		u'''
		TITLE:指定IPアドレスが対象範囲に入っているかを判定
		PARAMETER:
			ip:チェックするIPアドレス…IPv4形式（例：127.0.0.1）
			checkiplist:対象範囲とするIPアドレス一覧…（127.0.0.1、127.0.0.1/32 ）などの一覧
			※checkiplistが空なら判定はFalse
			denyiplist:対象範囲外とするIPアドレス一覧…（127.0.0.1、127.0.0.1/32 ）などの一覧　（denyが優先）

		'''
		is_in_range = False
		is_in_denyrange = False
		ip_cidr = IPy.IP(ip)

		# 拒否IPリストをまずチェック
		if denyiplist is not None:
			if isinstance(denyiplist, str):
				denyiplist = (denyiplist, '')
			ipranges = []
			for checkip in denyiplist:
				if checkip and checkip != '':
					# 0.0.0.0/0 とかだと、IPyがエラーするので、しょうがなく個別対応 → IPy.pyをバージョンアップしてエラーはしなくなったが厳密に判定されるため互換性のために残しておく（やむなく） 2022.03.23
					# IPy.pyをバージョンアップすると「222.92.143.86/24」のような正しくない指定がエラーしてしまうのでやむなく元バージョンに戻す... 2022.03.23
					# GAEGEN2対応…最新のIPPyをカスタマイズしたため「222.92.143.86/24」でエラーはしなくなったがこの処理は残しておく 2023/02/17
					#if checkip == '0.0.0.0/0' or checkip == '0.0.0.0' or checkip == '000.000.000.000/0' or checkip == '000.000.000.000':
					if UcfUtil.startsWith(checkip, '0.0.0.0/') or checkip == '0.0.0.0' or UcfUtil.startsWith(checkip, '000.000.000.000/') or checkip == '000.000.000.000':
						is_in_denyrange = True
						break
					else:
						try:
							ipranges.append(IPy.IP(checkip))
						except Exception as e:
							logging.error('No use "' + checkip + '" because of invalid iprange!')
							logging.error(str(e))


			if is_in_denyrange == False:
				# CIDRで範囲指定されたIP群の中に含まれているかを判断します
				for iprange in ipranges:
					if ip_cidr in iprange:
						is_in_denyrange = True
						break

		if not is_in_denyrange:			# 拒否リストにいなければ許可リストをチェック
			if checkiplist is not None:
				if isinstance(checkiplist, str):
					checkiplist = (checkiplist, '')
				ipranges = []
				for checkip in checkiplist:
	#				checkip = checkip.replace(',', '').replace('\r', '').replace('\n', '').replace(' ', '')
					if checkip and checkip != '':
						# 0.0.0.0/0 とかだと、IPyがエラーするので、しょうがなく個別対応 → IPy.pyをバージョンアップしてエラーはしなくなったが厳密に判定されるため互換性のために残しておく（やむなく） 2022.03.23
						# IPy.pyをバージョンアップすると「222.92.143.86/24」のような正しくない指定がエラーしてしまうのでやむなく元バージョンに戻す... 2022.03.23
						#if checkip == '0.0.0.0/0' or checkip == '0.0.0.0' or checkip == '000.000.000.000/0' or checkip == '000.000.000.000':
						if UcfUtil.startsWith(checkip, '0.0.0.0/') or checkip == '0.0.0.0' or UcfUtil.startsWith(checkip, '000.000.000.000/') or checkip == '000.000.000.000':
							#logging.info('is_in_range:' + checkip)
							is_in_range = True
							break
						else:
							try:
								ipranges.append(IPy.IP(checkip))
							except Exception as e:
								logging.error('No use "' + checkip + '" because of invalid iprange!')
								logging.error(str(e))


				if is_in_range == False:
					# CIDRで範囲指定されたIP群の中に含まれているかを判断します
					for iprange in ipranges:
						if ip_cidr in iprange:
							is_in_range = True
							break

		return is_in_range
	isCheckIPAddressRange = staticmethod(isCheckIPAddressRange)




