# coding: utf-8

import os,sys,random,datetime
import traceback
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
import jinja2
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import blobstore

import flask
from flask import Flask, Response, render_template, request, make_response, session, redirect, jsonify, after_this_request, g
from flask.views import MethodView
from functools import wraps

from ucf.utils.ucfutil import *
from ucf.config.ucfconfig import *
from ucf.config.ucfmessage import *
from ucf.utils.ucfxml import *
from google.appengine.api import namespace_manager
from ucf.utils import ucffunc,jinjacustomfilters
import json
from ucf.pages.dept import *

import sateraito_inc
import sateraito_func
import oem_func
#import sateraito_black_list
import sateraito_jinja2_environment


# GAEGEN2対応
# ビューメソッド（get, post など）戻り値が None のときに b'' に変換するデコレーター
def convert_result_none_to_empty_str(func):
	@wraps(func)
	def _wrapper(*args, **keywords):
		oResult = func(*args, **keywords)
		if (oResult is None):
			oResult = b''
		return oResult
	return _wrapper


# GAEGEN2対応
class DummyClass():
	pass


# GAEGEN2対応
# request.headers を処理するためのクラス
class HeadersWrapperClass(dict):
	def __init__(self):
		dict.__init__(self)

	def add_header(self, strKey, strValue):
		self[strKey] = strValue


############################################################
## ヘルパー（共通）
############################################################
class Helper(MethodView):

	# oem_company_code
	_oem_company_code = oem_func.OEM_COMPANY_CODE_DEFAULT
	# sp_codes
	_sp_codes = []
	# タイムゾーン
	_timezone = sateraito_inc.DEFAULT_TIMEZONE
	# 多言語対応
	_language = sateraito_inc.DEFAULT_LANGUAGE
	# エラーページＵＲＬ（デフォルトから変更したい場合は各Pageにてセット）
	_error_page = ''
	_approot_path = ''
	# ルートフォルダパス
	_root_folder_path = ''
	# キャリアタイプ（PC,MB,SP,API）
	_career_type = ''
	# キャリア（PC,DOCOMO,AU,SOFTBANK）
	_career = ''
	# Androidフラグ
	_is_android = False
	# iOSフラグ
	_is_ios = False
	# デザインタイプ（pc,m,sp）
	_design_type = ''
	# Requestタイプ（GET or POST）
	_request_type = ''
	_is_api = False
	_application_id = ''

	def __init__(self, *args, **kwargs):
		logging.debug(self.__class__.__name__ + '_BasePage.init() start.')

		super().__init__(*args, **kwargs)
		self.session = flask.session

		self.request = flask.request
		self.request.get = self._requestGet

		self._response_text = []
		self._response_status_code = -1
		self._redirect_url = None

		self.response = DummyClass()
		self.response.set_status = self._response_set_status
		self.response.headers = HeadersWrapperClass()
		self.response.status = None  # self.response.status = 403 のような記述に対応

		self.response.out = DummyClass()
		self.response.out.write  = self._response_write
		self.response.write  = self._response_write


		# GAEGEN2対応
		@after_this_request
		def _updateResponseStatus(response):
			if (len(self._response_text) > 0):
				if (response.calculate_content_length()):
					# 念のため既にレスポンステキストが設定されている場合は例外を発生させる
					# 実装によってはこのチェックは無い方が良いかも。。
					logging.error('response.calculate_content_length() = ' + str(response.calculate_content_length()))
					logging.error('response.get_data() = ' + str(response.get_data()))
					raise Exception('_updateResponseStatus: content is not empty.')
				response.set_data(b''.join(self._response_text))

			if (self.response.status is not None):
				response.status = str(self.response.status)

			if (self._response_status_code > 0):
				response.status_code = self._response_status_code

			response.headers.update(self.response.headers)

			if (self._redirect_url):
				response = flask.redirect(self._redirect_url)

			return response

	def _requestGet(self, strName, defaultValue=''):
		result = self.request.args.get(strName, None)
		if (result is None) and (not isinstance(self, blobstore.BlobstoreUploadHandler)):
			# BlobstoreUploadHandler では request.form, request.files にアクセスするとアップロードしたファイルを取得できなくなるので注意が必要
			result = self.request.form.get(strName, None)

			if (result is None):
				result = self.request.files.get(strName, None)

		if (result is None):
			result = defaultValue

		return result


	# GAEGEN2対応
	def _response_write(self, output_text):
		if (isinstance(output_text, str)):
			output_text = output_text.encode()

		self._response_text.append(output_text)

	# GAEGEN2対応
	def _response_set_status(self, status_code):
		self._response_status_code = status_code

	# GAEGEN2対応
	def error(self, status_code):
		self._response_text.clear()
		self._response_status_code = status_code

	# GAEGEN2対応
	def redirect(self, redirect_rul):
		self._redirect_url = redirect_rul

	def init(self):
		u''' 抽象メソッドイメージ '''
		pass

	def onLoad(self):
		u''' オンロード（抽象メソッドイメージ）
			Helperを継承する一番子供のクラスで必要に応じてオーバーロードするためのメソッド
			先頭で初期化しておきたい処理などに使用
		 '''

		## X-Forwarded-ForIPアドレスを取得しておく
		#self.getSessionHttpHeaderXForwardedForIPAddress()
		pass

	def getMsgs(self):
		#if self.msgs == None or self._msgs_language != self._language:
		#	self.msgs = UcfMessage.getMessageList(self._approot_path, self._language)
		#	self._msgs_language = self._language
		#return self.msgs
		return UcfMessage.getMessageListEx(self._language)

	def getMsg(self, msgid, ls_param=()):
		msgid = oem_func.exchangeMessageID(msgid, self._oem_company_code)
		return UcfMessage.getMessage(UcfUtil.getHashStr(self.getMsgs(), msgid), ls_param)

	def getRootPath(self):
		u'''ルートパスを取得'''
		return self._root_folder_path

	def getAppRootFolderPath(self):
		return self._approot_path

	# 現在のURLをHTTPSに変換
	def exchangeToHttpsUrl(self):
		current_url = self.request.url
		current_url_lower = current_url.lower()
		https_url = ''
		# ＵＲＬのドメイン部分を除く（例：manager/xxxx、manager/）
		if current_url_lower.startswith("http://"):
			https_url = 'https://' + UcfUtil.subString(current_url, len("http://"))
		elif current_url_lower.startswith("https://"):
			https_url = 'https://' + UcfUtil.subString(current_url, len("https://"))
		else:
			https_url = self.request.url
		return https_url

	# 現在のページがSSLかどうかを判定
	def isSSLPage(self):
		current_url = self.request.url.lower()
		return current_url.startswith("https://")

	def getTemplateFolderPath(self):
		u'''テンプレートフォルダパスを取得'''
		return os.path.join(self.getAppRootFolderPath(), UcfConfig.TEMPLATES_FOLDER_PATH)

	def getTemplateFilePath(self, filename):
		u'''テンプレートファイルパスを取得'''
		return os.path.join(self.getTemplateFolderPath(), filename)

	def getLocalTemplateFolderPath(self):
		u'''ローカルテンプレートフォルダパスを取得(絶対パス)'''
		return os.path.normpath(os.path.join(os.getcwd(), UcfConfig.TEMPLATES_FOLDER_PATH))

	def getLocalTemplateFilePath(self, filename):
		u'''ローカルテンプレートファイルパスを取得(相対パス)'''
		return os.path.normpath(os.path.join(UcfConfig.TEMPLATES_FOLDER_PATH, filename))

	def getParamFolderPath(self):
		u'''パラメーターフォルダパスを取得'''
		return os.path.normpath(os.path.join(self.getAppRootFolderPath(), UcfConfig.PARAM_FOLDER_PATH))

	def getParamFilePath(self, filename):
		u'''パラメーターファイルパスを取得'''
		return os.path.normpath(os.path.join(self.getParamFolderPath(), filename))

	def getLocalParamFolderPath(self):
		u'''ローカルパラメーターフォルダパスを取得(絶対パス)'''
		return os.path.normpath(os.path.join(os.getcwd(), UcfConfig.PARAM_FOLDER_PATH))

	def getLocalParamFilePath(self, filename):
		u'''ローカルパラメーターファイルパスを取得(相対パス)'''
		return os.path.normpath(os.path.join(UcfConfig.PARAM_FOLDER_PATH, filename))

	def judgeTargetCareer(self):
		u'''UserAgentからキャリアタイプを自動判定'''
		strTargetCareer, strTargetCareerType, strDesignType, is_android, is_ios = self.getTargetCareer()
		#内部変数にセット
		self._career = strTargetCareer
		self._career_type = strTargetCareerType
		self._design_type = strDesignType
		self._is_android = is_android
		self._is_ios = is_ios

	def getTargetCareer(self, is_disable_fp=False):
		u'''UserAgentからキャリアタイプを自動判定'''
		# ※ProfileUtilsの_judgeUserAgentToMatchUserAgentIDメソッドとも連動したい
		#環境変数の取得
		strAgent =  self.getUserAgent().lower()
		strJphone = self.getServerVariables("HTTP_X_JPHONE_MSNAME").lower()
		strAccept = self.getServerVariables("HTTP_ACCEPT").lower()

		# 海外展開対応：ガラ携帯の制御をしないフラグをみる （2015.07.09）
		# ※せめてスマホ判定をしたほうがよい気もするが、海外のガラ携帯（？）との統一性を保つためあえて考慮しない
		#logging.info('is_disable_fp=' + str(is_disable_fp))

		# ユーザエージェント判定
		strTargetCareer = None
		strTargetCareerType = None
		strDesignType = None
		is_android = False
		is_ios = False

		# WS-Federation対応：個別にスマホ判定すべきものだけ優先的に処理（ここではPC or スマホ or 、、、くらいが判別できればOKなため） 2015.09.11
		# iPhone版Lyncアプリ
		if strAgent.find('Lync Mobile'.lower())>=0:
			strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
			is_ios = True
		# Android版Lyncアプリ
		elif strAgent.find('ACOMO'.lower())>=0:
			strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
			is_android = True

		# Orkney Upward というモバイルアプリ（セールスフォース関連アプリとしてメジャーらしいのでスマホ版デザイン対応） 2015.12.11
		elif strAgent.find('Orkney Upward for iOS'.lower())>=0:
			strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
			is_ios = True

		# CACHATTOセキュアブラウザ 2016/02/21（DOCOMO の文字があるのでガラ携帯より前で処理） 追加
		elif strAgent.find('Cachatto'.lower())>=0:
			# iPhone（SecureBrowser for iPhone）
			# 例：Mozilla/5.0 (iPhone; CPU iPhone OS 8_2 like Mac OS X)AppleWebKit/600.1.4 (KHTML, like Gecko) Mobile/12D508 Model/iPhone6,1Cachatto/3.18.0
			if strAgent.find('iPhone'.lower())>=0:
				strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
				is_ios = True
			# iPod
			elif strAgent.find('iPod'.lower())>=0:
				strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
				is_ios = True
			# iPad
			# 例：Mozilla/5.0 (iPad; CPU OS 9_2_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Mobile/13D15 Model/iPad4,1 Cachatto-iPad/3.18.0
			elif strAgent.find('iPad'.lower())>=0:
				strTargetCareer = UcfConfig.VALUE_CAREER_PC
				#strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_PC
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_TABLET
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_PC
				is_ios = True
			# Android
			# [WebView UA] Cachatto-Android/[x.y.z] (CACHATTO SecureBrowser V[x.y.z] B[build]; [キャリア名]; [キャリアコード])
			# [WebView UA] Cachatto-Android/[x.y.z] (CACHATTO SecureBrowser V[x.y.z] B[build]; [キャリア名]; [キャリアコード])
			elif strAgent.find('Android'.lower())>=0 and strAgent.find('Mobile'.lower())>=0:
				strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
				is_android = True
			# Android（タブレット）
			elif strAgent.find('Android'.lower())>=0 and strAgent.find('Mobile'.lower())<0:
				strTargetCareer = UcfConfig.VALUE_CAREER_PC
				#strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_PC
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_TABLET
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_PC
				is_android = True
			# その他はPC扱い（SecureBrowser for Windows、CACHATTO Desktop）
			# Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; Trident/6.0; SLCC2)Cachatto-Agent/3.5.0 (B2013070700)
			# Mozilla/5.0 (Windows NT 6.2; WOW64; Trident/7.0; rv:11.0) like Gecko CACHATTO Desktop/1.8.48; Cachatto-Agent/3.10.3 (B2015121700)
			else:
				strTargetCareer = UcfConfig.VALUE_CAREER_PC
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_PC
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_PC

		# Blackberry
		elif strAgent.find('BlackBerry'.lower())>=0:
			strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
		# WindowsPhone
		elif strAgent.find('IEMobile'.lower())>=0 or strAgent.find('Windows Phone'.lower())>=0:
			strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
		# WILLCOM
		elif not is_disable_fp and (strAgent.find('WILLCOM'.lower())>=0 or strAgent.find('DDIPOCKET'.lower())>=0):
			strTargetCareer = UcfConfig.VALUE_CAREER_WILLCOM
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_MOBILE
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_MOBILE
		# SoftBank
		elif not is_disable_fp and (strJphone!='' or strAgent.find('j-phone'.lower())>=0 or strAgent.find('softbank'.lower())>=0 or strAgent.find('vodafone'.lower())>=0 or strAgent.find('mot-'.lower())>=0):
			strTargetCareer = UcfConfig.VALUE_CAREER_SOFTBANK
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_MOBILE
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_MOBILE
		# au
		elif not is_disable_fp and (strAgent.find('kddi'.lower())>=0 or strAgent.find('up.browser'.lower())>=0 or strAccept.find('hdml'.lower())>=0):
			strTargetCareer = UcfConfig.VALUE_CAREER_EZWEB
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_MOBILE
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_MOBILE
		# Docomo
		elif not is_disable_fp and (strAgent.find('docomo'.lower())>=0):
			strTargetCareer = UcfConfig.VALUE_CAREER_IMODE
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_MOBILE
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_MOBILE
		# KAITO
		elif strAgent.find('KAITO'.lower())>=0:
			strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
		# CLOMOセキュリティブラウザ 2013/10/16 追加	※ここではPCなのかとかを決めるだけなので不要なのでは？？？
		elif strAgent.find('SecuredBrowser'.lower())>=0 and strAgent.find('.securedbrowser'.lower())>=0:
			# iPhone
			if strAgent.find('iPhone OS 2_0'.lower())>=0 or strAgent.find('iPhone'.lower())>=0:
				strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
				is_ios = True
			# iPod
			elif strAgent.find('iPod'.lower())>=0:
				strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
				is_ios = True
			# Android
			elif strAgent.find('Android '.lower())>=0 and strAgent.find('Mobile '.lower())>=0:
				strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
				is_android = True
			# Android（タブレット）
			elif strAgent.find('Android '.lower())>=0 and strAgent.find('Mobile '.lower())<0:
				strTargetCareer = UcfConfig.VALUE_CAREER_PC
				#strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_PC
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_TABLET
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_PC
				is_android = True
			# iPad
			elif strAgent.find('iPad'.lower())>=0:
				strTargetCareer = UcfConfig.VALUE_CAREER_PC
				#strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_PC
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_TABLET
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_PC
				is_ios = True
			# その他はPC扱い
			else:
				strTargetCareer = UcfConfig.VALUE_CAREER_PC
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_PC
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_PC
		# IIJセキュリティブラウザ 2013/12/05 追加	※ここではPCなのかとかを決めるだけなので不要なのでは？？？
		#elif strAgent.find('IIJsmb/'.lower())>=0:
		elif strAgent.find('IIJsmb'.lower())>=0:
			# iPhone
			if strAgent.find('iPhone'.lower())>=0:
				strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
				is_ios = True
			# iPod
			elif strAgent.find('iPod'.lower())>=0:
				strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
				is_ios = True
			# Android
			#elif strAgent.find('Android '.lower())>=0 and strAgent.find('Mobile '.lower())>=0:
			elif strAgent.find('Android'.lower())>=0 and strAgent.find('Mobile'.lower())>=0:
				strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
				is_android = True
			# Android（タブレット）
			#elif strAgent.find('Android '.lower())>=0 and strAgent.find('Mobile '.lower())<0:
			elif strAgent.find('Android'.lower())>=0 and strAgent.find('Mobile'.lower())<0:
				strTargetCareer = UcfConfig.VALUE_CAREER_PC
				#strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_PC
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_TABLET
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_PC
				is_android = True
			# iPad
			elif strAgent.find('iPad'.lower())>=0:
				strTargetCareer = UcfConfig.VALUE_CAREER_PC
				#strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_PC
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_TABLET
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_PC
				is_ios = True
			# その他はPC扱い
			else:
				strTargetCareer = UcfConfig.VALUE_CAREER_PC
				strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_PC
				strDesignType = UcfConfig.VALUE_DESIGN_TYPE_PC
		# iPhone
		# WindowsMobileにもiPhoneと含まれるケースがあるので除外 2015.12.24
		#elif (strAgent.find('iPhone OS 2_0'.lower())>=0 or strAgent.find('iPhone'.lower())>=0) and not strAgent.find('iPad'.lower())>=0:
		elif strAgent.find('iPhone'.lower())>=0 and not strAgent.find('iPad'.lower())>=0 and not strAgent.find('Windows Phone'.lower())>=0:
			strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
			is_ios = True
		# iPod
		elif strAgent.find('iPod'.lower())>=0:
			strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
			is_ios = True
		# Android
		elif strAgent.find('Android '.lower())>=0 and strAgent.find('Mobile '.lower())>=0:
			strTargetCareer = UcfConfig.VALUE_CAREER_MOBILE
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_SP
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP
			is_android = True
		# Android（タブレット）
		elif strAgent.find('Android '.lower())>=0 and strAgent.find('Mobile '.lower())<0:
			strTargetCareer = UcfConfig.VALUE_CAREER_PC
			#strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_PC
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_TABLET
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_PC
			is_android = True
		# iPad
		elif strAgent.find('iPad'.lower())>=0:
			strTargetCareer = UcfConfig.VALUE_CAREER_PC
			#strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_PC
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_TABLET
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_PC
			is_ios = True
		## SSOCLIENT
		#elif strAgent.find('UcfSSOClient'.lower())>=0:
		#	strTargetCareer = UcfConfig.VALUE_CAREER_PC
		#	strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_PC
		#	strDesignType = UcfConfig.VALUE_DESIGN_TYPE_PC
		#デフォルトは、PC
		else:
			strTargetCareer = UcfConfig.VALUE_CAREER_PC
			strTargetCareerType = UcfConfig.VALUE_CAREER_TYPE_PC
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_PC

		# WorksMobile関連アプリ 2016/01/19 追加	※WorksMobileアプリは、PC、Mac、スマホ全て小さい画面なのでスマホ版として表示
		if strAgent.find('WorksMobile'.lower())>=0:
			strDesignType = UcfConfig.VALUE_DESIGN_TYPE_SP

		return strTargetCareer, strTargetCareerType, strDesignType, is_android, is_ios

	@convert_result_none_to_empty_str
	def get(self, *args, **keywords):
		self.request.charset = UcfConfig.ENCODING
		self.response.charset = UcfConfig.ENCODING
		self._request_type = UcfConfig.REQUEST_TYPE_GET
		self.init()
		self.onLoad()
		return self.processOfRequest(*args, **keywords)

	@convert_result_none_to_empty_str
	def post(self, *args, **keywords):
		self.request.charset = UcfConfig.ENCODING
		self.response.charset = UcfConfig.ENCODING
		self._request_type = UcfConfig.REQUEST_TYPE_POST
		self.init()
		self.onLoad()
		return self.processOfRequest(*args, **keywords)

	def processOfRequest(self, *args, **keywords):
		u'''Requestがきた場合の処理（抽象メソッドイメージ）'''
		pass

	def render(self, template_name, design_type, vals, content_type=None):

		# 文字コード指定：これをやらないとmetaタグだけでは文字コードをブラウザが認識してくれないため。
		# self.response.headers['Content-Type'] = 'text/html; charset=' + UcfConfig.ENCODING + ';'
		# encodeとcharsetのマッピング対応 2009.5.20 Osamu Kurihara
		if UcfConfig.ENCODING == 'cp932':
			charset_string = 'Shift_JIS'
		# charset_string = UcfConfig.FILE_CHARSET
		# マッピング定義がないものはUcfConfig.ENCODING
		else:
			charset_string = UcfConfig.ENCODING

		if content_type is None or content_type == '':
			content_type = 'text/html'
		self.response.headers['Content-Type'] = content_type + '; charset=' + charset_string + ';'

		# レンダリング
		jinja_environment = sateraito_jinja2_environment.getEnvironmentObj(design_type)
		template = jinja_environment.get_template(template_name)
		self.response.out.write(template.render(vals))

	def setResponseHeaderForDownload(self, file_name, enc=UcfConfig.ENCODING):
		u'''CSVダウンロード用のレスポンスヘッダを設定'''

		#TODO 本番環境で日本語ファイル名がうまくいかない.エンコードの問題っぽいけど。→今ならいけるかも
		# Content-Disposition にマルチバイト文字を埋め込むときはUTF-8でよさそう Osamu Kurihara
		# Edge でページ内でCSVが表示されてしまうので修正 2019.11.05
		#self.response.headers['Content-Disposition'] = 'inline;filename=' + unicode(file_name).encode(enc)
		self.response.headers['Content-Disposition'] = 'attachment;filename=' + file_name
#		self.response.headers['Content-Type'] = 'application/Octet-Stream-Dummy'
		self.response.headers['Content-Type'] = 'application/octet-stream'


	def redirectError(self, error_info):
		u'''エラーページに遷移'''
		self.setSession(UcfConfig.SESSIONKEY_ERROR_INFO, error_info)
		self.redirect(self._error_page)

	def decryptoForCookie(self, enc_value):
		try:
			return UcfUtil.deCrypto(enc_value, UcfConfig.COOKIE_CRYPTOGRAPIC_KEY)
		except Exception as e:
			logging.warning('enc_value=' + enc_value)
			logging.warning(e)
			return enc_value

	def encryptoForCookie(self, value):
		return UcfUtil.enCrypto(str(value), UcfConfig.COOKIE_CRYPTOGRAPIC_KEY)

	def decryptoData(self, enc_value, enctype=''):
		try:
			if enctype == 'AES':
				return UcfUtil.deCryptoAES(enc_value, UcfConfig.COOKIE_CRYPTOGRAPIC_KEY)
			else:
				return UcfUtil.deCrypto(enc_value, UcfConfig.COOKIE_CRYPTOGRAPIC_KEY)
		except Exception as e:
			logging.warning('enc_value=' + enc_value)
			logging.warning(e)
			return enc_value

	def encryptoData(self, value, enctype=''):
		if enctype == 'AES':
			return UcfUtil.enCryptoAES(str(value), UcfConfig.COOKIE_CRYPTOGRAPIC_KEY)
		else:
			return UcfUtil.enCrypto(str(value), UcfConfig.COOKIE_CRYPTOGRAPIC_KEY)


	############################################################
	## クッキー
	############################################################
	# クッキーの値を取得（なければNone）
	def getCookie(self, name):
		raw_value = request.cookies.get(name, None)
		if raw_value is not None:
			# 復号化
			try:
				value = self.decryptoForCookie(UcfUtil.urlDecode(raw_value))
			except Exception as e:
				logging.exception(e)
				value = raw_value
			return value
		else:
			return raw_value


	# クッキーの値をセット（期限指定無しの場合は無期限）
	def setCookie(self, name, value, expires=None, is_secure=True, path='/', domain='', samesite='None', living_sec=None):

		if expires is None or expires == '':
			expires = UcfUtil.getDateTime('2037/12/31').strftime(UcfConfig.COOKIE_DATE_FMT)

		# GAEGEN2対応
		#value = UcfUtil.urlEncode(self.encryptoForCookie(unicode(value)))
		value = UcfUtil.urlEncode(self.encryptoForCookie(value))

		if (sateraito_inc.developer_mode):
			is_secure = False
			samesite = ''

		httpOnly = False

		#if (not expires):
		#	if (living_sec) and (living_sec > 0):
		#		expires = UcfUtil.add_seconds(UcfUtil.getNow(), living_sec).strftime('%a, %d-%b-%Y %H:%M:%S GMT')
		#	else:
		#		expires = None

		@after_this_request
		def _setCookie(response):
			dictParam = {
					'secure'	 : is_secure,
					'httponly' : httpOnly,
			}

			if (expires) : dictParam['expires'] = expires
			if (path) : dictParam['path'] = path
			if (domain) : dictParam['domain'] = domain
			if (samesite) : dictParam['samesite'] = samesite

			response.set_cookie(
					name,
					value=value,
					**dictParam
			)
			return response

	def clearCookie(self, name, path=None, domain=None):
		self.setCookie(name, '', expires=0, path=path, domain=domain)

	############################################################
	## セッション
	############################################################
	# セッション取得
	def getSession(self, key):
		value = session.get(key, None)
		logging.debug('getsession key=%s value=%s' % (key, value))
		return value

	# セッションに値セット
	def setSession(self, key, value):
		session[key] = value
		logging.debug('setsession key=%s value=%s' % (key, value))

	############################################################
	## リクエスト値
	############################################################
	def getRequest(self, key):
		u'''Requestデータの取得'''
		# 同一名の複数POSTに対応
		list = request.values.getlist(key)
		value = ','.join(list) if list is not None else ''
		return value

	def getRequests(self, key):
		u'''Requestデータの取得(リスト形式で返す)'''
		# 同一名の複数POSTに対応
		list = request.values.getlist(key)
		return list

	# クライアントのIPアドレスを取得
	def getClientIPAddress(self):
		return UcfUtil.getHashStr(os.environ, 'REMOTE_ADDR')

	def getUserAgent(self):
		u'''UserAgentの取得'''

		# ActiveSync対応…ActiveSync接続時にはUserAgentではなくこちらがセットされてくるので 2015.09.10
		if self.getRequestHeaders('X-Ms-Client-User-Agent').strip() != '':
			return self.getRequestHeaders('X-Ms-Client-User-Agent').strip()
		# SSOログインアプリからマルチバイト文字列がURLエンコードされてくる場合があるので一応デコードを試みる
		#return str(self.request.user_agent)
		try:
			return str(UcfUtil.urlDecode(self.request.user_agent))
		except BaseException as ex:
			return str(self.request.user_agent)

	def getRequestHeaders(self, key=None):
		u'''HTTPリクエストヘッダー値の取得'''
		if key:
			return self.request.headers.get(key, '')
		else:
			#TODO できればCloneして返したい
			return self.request.headers

	def getServerVariables(self, key):
		u'''サーバー環境変数値Request.environの取得'''
		if key:
			return self.request.environ.get(key, '')
		else:
			#TODO できればCloneして返したい
			return self.request.environ

	def outputErrorLog(self, e):
		logging.exception(e)
		#u''' 例外をログ出力する （抽象メソッドイメージ）'''
		#try:
		#	exc_type, exc_value, exc_traceback = sys.exc_info()
		#	logging.error(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
		#except BaseException as ex:
		#	logging.exception(ex)
		#	pass

	def _createConfigForTemplate(self):
		return {}



############################################################
## ヘルパー…cron用
############################################################
class CronHelper(Helper):

	def init(self):
		pass

	@convert_result_none_to_empty_str
	def get(self):
		self.request.charset = UcfConfig.ENCODING
		self.response.charset = UcfConfig.ENCODING
		self._request_type = UcfConfig.REQUEST_TYPE_GET
		self.init()
		return self.processOfRequest()

	@convert_result_none_to_empty_str
	def post(self):
		self.request.charset = UcfConfig.ENCODING
		self.response.charset = UcfConfig.ENCODING
		self._request_type = UcfConfig.REQUEST_TYPE_POST
		self.init()
		self.onLoad()
		return self.processOfRequest()

	def processOfRequest(self):
		u'''Requestがきた場合の処理（抽象メソッドイメージ）'''
		pass



############################################################
## サイトルートヘルパー
############################################################
class FrontHelper(Helper):
#	def __init__(self):
#		# 親のコンストラクタをコール
#		Helper.__init__(self)

	def init(self):

		u'''フロントサイト用の初期化'''
		self._root_folder_path = ''
		# エラーページＵＲＬ
		if self._error_page == None or self._error_page == '':
			self._error_page = UcfConfig.URL_ERROR

		#キャリア判定
		self.judgeTargetCareer()

	def _createConfigForTemplate(self):
		config = {}

		config['QSTRING_STATUS'] = UcfConfig.QSTRING_STATUS
		config['VC_CHECK'] = UcfConfig.VC_CHECK
		config['QSTRING_TYPE'] = UcfConfig.QSTRING_TYPE
		config['EDIT_TYPE_RENEW'] = UcfConfig.EDIT_TYPE_RENEW
		config['EDIT_TYPE_NEW'] = UcfConfig.EDIT_TYPE_NEW
		config['EDIT_TYPE_COPYNEWREGIST'] = UcfConfig.EDIT_TYPE_COPYNEWREGIST
		config['QSTRING_TYPE2'] = UcfConfig.QSTRING_TYPE2
		config['EDIT_TYPE_DELETE'] = UcfConfig.EDIT_TYPE_DELETE
		config['EDIT_TYPE_REFER'] = UcfConfig.EDIT_TYPE_REFER

		return config


	# テンプレートに渡す基本情報をセット
	def appendBasicInfoToTemplateVals(self, template_vals):
#		template_vals['my_site_url'] = sateraito_inc.my_site_url
		template_vals['config'] = self._createConfigForTemplate()
		template_vals['version'] = UcfUtil.md5(sateraito_inc.version)
		template_vals['vurl'] = '/'
		template_vals['vscripturl'] = '/script/' if not sateraito_inc.debug_mode else '/script/debug/' 
		#template_vals['language'] = sateraito_inc.DEFAULT_LANGUAGE
		template_vals['language'] = self._language if self._language is not None and self._language != '' else sateraito_inc.DEFAULT_LANGUAGE
		template_vals['extjs_locale_file'] = sateraito_func.getExtJsLocaleFileName(sateraito_inc.DEFAULT_LANGUAGE)
		template_vals['lang'] = self.getMsgs()
		template_vals['FREE_MODE'] = True	# 無償バージョンかどうか


############################################################
## 契約用ヘルパー
############################################################
class ContractFrontHelper(FrontHelper):

	@convert_result_none_to_empty_str
	def get(self, oem_company_code):
		self.request.charset = UcfConfig.ENCODING
		self.response.charset = UcfConfig.ENCODING
		self._request_type = UcfConfig.REQUEST_TYPE_GET
		self._oem_company_code = oem_company_code
		self.init()
		self.onLoad()
		return self.processOfRequest(oem_company_code)

	@convert_result_none_to_empty_str
	def post(self, oem_company_code):
		self.request.charset = UcfConfig.ENCODING
		self.response.charset = UcfConfig.ENCODING
		self._request_type = UcfConfig.REQUEST_TYPE_POST
		self._oem_company_code = oem_company_code
		self.init()
		self.onLoad()
		return self.processOfRequest(oem_company_code)

############################################################
## 契約用ヘルパー（SP限定用）
############################################################
class ContractSPFrontHelper(FrontHelper):

	@convert_result_none_to_empty_str
	def get(self, oem_company_code, sp_code):
		self.request.charset = UcfConfig.ENCODING
		self.response.charset = UcfConfig.ENCODING
		self._request_type = UcfConfig.REQUEST_TYPE_GET
		self._oem_company_code = oem_company_code
		self.init()
		self.onLoad()
		return self.processOfRequest(oem_company_code, sp_code)

	@convert_result_none_to_empty_str
	def post(self, oem_company_code, sp_code):
		self.request.charset = UcfConfig.ENCODING
		self.response.charset = UcfConfig.ENCODING
		self._request_type = UcfConfig.REQUEST_TYPE_POST
		self._oem_company_code = oem_company_code
		self.init()
		self.onLoad()
		return self.processOfRequest(oem_company_code, sp_code)


############################################################
## 契約用ヘルパー（SP+ボット限定用）
############################################################
class ContractSPBOTFrontHelper(FrontHelper):

	@convert_result_none_to_empty_str
	def get(self, oem_company_code, sp_code, bot_id):
		self.request.charset = UcfConfig.ENCODING
		self.response.charset = UcfConfig.ENCODING
		self._request_type = UcfConfig.REQUEST_TYPE_GET
		self._oem_company_code = oem_company_code
		self.init()
		self.onLoad()
		return self.processOfRequest(oem_company_code, sp_code, bot_id)

	@convert_result_none_to_empty_str
	def post(self, oem_company_code, sp_code, bot_id):
		self.request.charset = UcfConfig.ENCODING
		self.response.charset = UcfConfig.ENCODING
		self._request_type = UcfConfig.REQUEST_TYPE_POST
		self._oem_company_code = oem_company_code
		self.init()
		self.onLoad()
		return self.processOfRequest(oem_company_code, sp_code, bot_id)


############################################################
## テナントヘルパー…基本機能
############################################################
class TenantHelper(Helper):

#	def __init__(self):
#		# 親のコンストラクタをコール
#		Helper.__init__(self)

	_tenant = ''
	_dept = None
	_is_dept_selected = False	# このページ内で最新の情報を取得したかどうか

	def judgeTargetCareer(self):
		is_disable_fp = self.getDeptInfo() is not None and self.getDeptValue('is_disable_fp') == 'True'
		u'''UserAgentからキャリアタイプを自動判定'''
		strTargetCareer, strTargetCareerType, strDesignType, is_android, is_ios = self.getTargetCareer(is_disable_fp=is_disable_fp)
		#内部変数にセット
		self._career = strTargetCareer
		self._career_type = strTargetCareerType
		self._design_type = strDesignType
		self._is_android = is_android
		self._is_ios = is_ios

	def init(self):

		self._root_folder_path = ''
		# エラーページＵＲＬ
		if self._error_page is None or self._error_page == '':
			self._error_page = '/a/' + self._tenant + UcfConfig.URL_ERROR
		# タイムゾーン設定
		dept = self.getDeptInfo()
		if dept is not None and UcfUtil.nvl(dept['timezone']) != '':
			try:
				#UcfConfig.TIME_ZONE_HOUR = int(UcfUtil.nvl(dept['timezone']))
				#UcfConfig.TIMEZONE = sateraito_func.getActiveTimeZone(UcfUtil.nvl(dept['timezone']))
				self._timezone = sateraito_func.getActiveTimeZone(UcfUtil.nvl(dept['timezone']))
			except:
				#UcfConfig.TIME_ZONE_HOUR = 0
				#UcfConfig.TIMEZONE = sateraito_inc.DEFAULT_TIMEZONE
				self._timezone = sateraito_inc.DEFAULT_TIMEZONE
				pass
		# OEMコード設定
		self._oem_company_code = oem_func.getValidOEMCompanyCode(dept.get('oem_company_code', '') if dept is not None else '')
		# サービスコード
		if dept is not None and dept.get('sp_codes', '') != '':
			self._sp_codes = UcfUtil.csvToList(dept.get('sp_codes'))
		else:
			self._sp_codes = []

		#キャリア判定
		self.judgeTargetCareer()

	def setTenant(self, tenant):
		#namespace_manager.set_namespace(tenant)
		namespace_manager.set_namespace(tenant.lower())
		self._tenant = tenant
		self._dept = None
		self._is_dept_selected = False
		self._error_page = '/a/' + self._tenant + UcfConfig.URL_ERROR

	def getDeptInfo(self, no_memcache=False, is_force_select=False):

		memcache_key = 'deptinfo?tenant=' + self._tenant

		if is_force_select or (no_memcache and not self._is_dept_selected):
			#logging.info('get dept info start...')
			self._dept = ucffunc.getDeptVo(self)
			self._is_dept_selected = True
			#logging.info('get dept info end.')
			if self._dept is not None:
				DeptUtils.editVoForSelect(self, self._dept)
				memcache.set(key=memcache_key, value=self._dept, time=300)

		elif self._dept is None:
			self._dept = memcache.get(memcache_key)
			if self._dept is None:
				#logging.info('get dept info start...')
				self._dept = ucffunc.getDeptVo(self)
				self._is_dept_selected = True
				#logging.info('get dept info end.')
				if self._dept is not None:
					DeptUtils.editVoForSelect(self, self._dept)
					memcache.set(key=memcache_key, value=self._dept, time=300)

		return self._dept

	def getDeptValue(self, key):
		return self.getDeptInfo().get(key)

	def _createConfigForTemplate(self):
		config = {}

		config['QSTRING_STATUS'] = UcfConfig.QSTRING_STATUS
		config['VC_CHECK'] = UcfConfig.VC_CHECK
		config['QSTRING_TYPE'] = UcfConfig.QSTRING_TYPE
		config['EDIT_TYPE_RENEW'] = UcfConfig.EDIT_TYPE_RENEW
		config['EDIT_TYPE_NEW'] = UcfConfig.EDIT_TYPE_NEW
		config['EDIT_TYPE_COPYNEWREGIST'] = UcfConfig.EDIT_TYPE_COPYNEWREGIST
		config['QSTRING_TYPE2'] = UcfConfig.QSTRING_TYPE2
		config['REQUESTKEY_SESSION_SCID'] = UcfConfig.REQUESTKEY_SESSION_SCID
		config['SESSIONKEY_SCOND_OPERATOR_LIST'] = UcfConfig.SESSIONKEY_SCOND_OPERATOR_LIST
		config['EDIT_TYPE_DELETE'] = UcfConfig.EDIT_TYPE_DELETE
		config['EDIT_TYPE_REFER'] = UcfConfig.EDIT_TYPE_REFER
		config['SESSIONKEY_SCOND_LOGIN_HISTORY'] = UcfConfig.SESSIONKEY_SCOND_LOGIN_HISTORY
		config['REQUESTKEY_TASK_TYPE'] = UcfConfig.REQUESTKEY_TASK_TYPE


		return config

	# ※外部からコールされる場合あり
	def process_of_get(self, *args, **keywords):
		# self.setTenant(tenant)
		self._request_type = UcfConfig.REQUEST_TYPE_GET
		self._language = sateraito_func.getActiveLanguage(self.getDeptInfo()['language']) if self.getDeptInfo() is not None else sateraito_inc.DEFAULT_LANGUAGE
		self.init()
		self.onLoad()

	# ※外部からコールされる場合あり
	def process_of_post(self, *args, **keywords):
		# self.setTenant(tenant)
		self._request_type = UcfConfig.REQUEST_TYPE_POST
		self._language = sateraito_func.getActiveLanguage(self.getDeptInfo()['language']) if self.getDeptInfo() is not None else sateraito_inc.DEFAULT_LANGUAGE
		self.init()
		self.onLoad()

	@convert_result_none_to_empty_str
	def get(self, *args, **keywords):
		self.process_of_get(*args, **keywords)
		return self.processOfRequest(*args, **keywords)

	@convert_result_none_to_empty_str
	def post(self, *args, **keywords):
		self.process_of_post(*args, **keywords)
		return self.processOfRequest(*args, **keywords)

	# def processOfRequest(*args, **keywords):
	# 	u'''Requestがきた場合の処理（抽象メソッドイメージ）'''
	# 	pass

	def getMsgs(self):
		return UcfMessage.getMessageListEx(self._language)

#	def getMsgs(self):
#		memcache_key = 'msgs?language=' + self._language
#		is_debug = sateraito_inc.debug_mode
#		if is_debug == False and self._tenant:
#			# 取得していないか言語が違う場合はまずmemcacheから取得
#			if self.msgs is None or self._msgs_language != self._language:
#				self.msgs = memcache.get(memcache_key)
#				if self.msgs is not None:
#					self._msgs_language = self._language
#
#		# 次に、ファイルから取得
#		if self.msgs is None or self._msgs_language != self._language:
#			#logging.info('load message list...ln=' + str(self._language))
#			#self.msgs = UcfMessage.getMessageList(self._approot_path, self._language)
#			self.msgs = UcfMessage.getMessageListEx(self._language)
#			#logging.info('load message list end.')
#			self._msgs_language = self._language
#			if self.msgs is not None:
#				# memcacheにセットしておく（3600秒）
#				memcache.set(key=memcache_key, value=self.msgs, time=3600)
#		return self.msgs


	############################################################
	## セッション
	############################################################

	# セッション取得
	def getSession(self, key):
		# keyにドメイン情報（unique_id）を付与（path指定が動的にできなそう＆BigTableではなくmemcacheに保持を考慮してnamespace_managerは使わないため）
		key = self.createTenantSessionKeyPrefix() + key
		value = session.get(key, None)
		logging.debug('getsession key=%s value=%s' % (key, value))
		return value

	# セッションに値セット
	def setSession(self, key, value):
		# keyにドメイン情報（unique_id）を付与（path指定が動的にできなそう＆BigTableではなくmemcacheに保持を考慮してnamespace_managerは使わないため）
		key = self.createTenantSessionKeyPrefix() + key
		session[key] = value
		logging.debug('setsession key=%s value=%s' % (key, value))


## webapp2_extras用
#	def clearSession(self):
#		sessionkey_prefix = self.createTenantSessionKeyPrefix()
#		session_keys = []
#		for k,v in self.session().items():
#			if UcfUtil.startsWith(k, sessionkey_prefix):
#				session_keys.append(k)
#		for session_key in session_keys:
#			self.session()[session_key] = None
		
	def createTenantSessionKeyPrefix(self):
		return UcfUtil.md5(self._tenant)

	############################################################
	## Cookie
	############################################################
	def setCookie(self, name, value, expires=None, is_secure=False, path=None, samesite='none'):
		u'''クッキーの値をセット（期限指定無しの場合は無期限）'''
		if expires is None or expires == '':
			expires = UcfUtil.getDateTime('2037/12/31').strftime(UcfConfig.COOKIE_DATE_FMT)

		httpOnly = False

		if path is None:
			path = '/a/' + self._tenant + '/'	# 最後の「/」いるのかなー
		domain = sateraito_inc.cookie_domain
		# 暗号化
		value = UcfUtil.urlEncode(self.encryptoForCookie(str(value)))

		@after_this_request
		def _setCookie(response):
			dictParam = {
					'secure'	 : is_secure,
					'httponly' : httpOnly,
			}

			if (expires) : dictParam['expires'] = expires
			if (path) : dictParam['path'] = path
			if (domain) : dictParam['domain'] = domain
			if (samesite) : dictParam['samesite'] = samesite

			response.set_cookie(
					name,
					value=value,
					**dictParam
			)
			return response


	def clearCookie(self, name, path=None):
		u'''クッキークリア'''
		if path is None:
			path = '/a/' + self._tenant + '/'
		#domain = ''
		domain = sateraito_inc.cookie_domain
		self.response.headers.add_header('Set-Cookie', str(name) + '=;' + 'expires=' + 'Wed, 01-Jan-1970 00:00:00 GMT' + ';' + 'Path=' + str(path) + ((';' + 'domain=' + str(domain) + ';') if domain != '' else ''))


	def isValidTenant(self, not_redirect=False):
		# 無効テナントかどうかをチェック

		# G Suite 版以外はブラックリストを見ない対応 2017.08.28
		## OEM以外はブラックリストチェックする 2017.01.30
		#without_check_black_list = False
		#dept = self.getDeptInfo()
		#if dept is not None and dept.get('oem_company_code', '') not in oem_func.getBlackListTargetOEMCompanyCodes():
		#	without_check_black_list = True
		#if sateraito_func.isTenantDisabled(self._tenant, without_check_black_list=without_check_black_list):
		# メッセージ分離対応
		#if sateraito_func.isTenantDisabled(self._tenant):
		#	if not_redirect == False:
		#		self.redirectError(self.getMsg('MSG_THIS_APPRICATION_IS_STOPPED_FOR_YOUR_TENANT'))
		#	return False

		tenant_entry = sateraito_func.TenantEntry.getInstance(self._tenant, cache_ok=True)
		if tenant_entry is None:
			if not_redirect == False:
				self.redirectError(self.getMsg('MSG_THIS_APPRICATION_IS_NOTINSTALLED_FOR_YOUR_TENANT'))
			return False

		if tenant_entry.is_disable == True:
			if not_redirect == False:
				self.redirectError(self.getMsg('MSG_THIS_APPRICATION_IS_STOPPED_FOR_YOUR_TENANT'))
			return False

		if sateraito_func.isExpireAvailableTerm(tenant_entry):
			if not_redirect == False:
				self.redirectError(self.getMsg('MSG_THIS_APPRICATION_IS_EXPIRE_FOR_YOUR_TENANT'))
			return False


		return True

	def render(self, template_name, design_type, vals):
		if UcfConfig.ENCODING=='cp932':
			charset_string='Shift_JIS'
			#charset_string = UcfConfig.FILE_CHARSET
		else:
			charset_string=UcfConfig.ENCODING
		self.response.headers['Content-Type'] = 'text/html; charset=' + charset_string + ';'

		# レンダリング
		jinja_environment = sateraito_jinja2_environment.getEnvironmentObjForTenant(design_type)
		template = jinja_environment.get_template(template_name)
		self.response.out.write(template.render(vals))

	

	# テンプレートに渡す基本情報をセット
	def appendBasicInfoToTemplateVals(self, template_vals):
		pass

############################################################
## TenantAppヘルパー…アプリ用
############################################################
class TenantAppHelper(TenantHelper):

	_temporary_login_action_key = None

	# CSRF対策：トークンを発行しセッションにセット
	def createCSRFToken(self, key):
		token = UcfUtil.guid()
		# sessionではなくmemcacheのみでチェックする施策 2016.12.27
		#logging.info('createCSRFToken[key]' + key + '[create_token]' + token + '[session_token]' + UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_CSRF_TOKEN_PREFIX + key)))
		# sessionに戻してみる 2020.08.10
		#memcache_key = self._tenant + UcfConfig.SESSIONKEY_CSRF_TOKEN_PREFIX + key + self.getLoginOperatorUniqueID()
		#memcache.set(key=memcache_key, value=token, time=86400)		# セッションと同じ24時間程度にしてみる（自動延長がないとはいえ長すぎ？）
		self.setSession(UcfConfig.SESSIONKEY_CSRF_TOKEN_PREFIX + key, token)
		logging.info(self.getSession(UcfConfig.SESSIONKEY_CSRF_TOKEN_PREFIX + key))
		return token

	# CSRF対策：トークンをチェック
	def checkCSRFToken(self, key, token, without_refresh_token=False):
		# sessionではなくmemcacheのみでチェックする施策 2016.12.27
		#logging.info('checkCSRFToken[key]' + key + '[request_token]' + token + '[session_token]' + UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_CSRF_TOKEN_PREFIX + key)))
		#return UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_CSRF_TOKEN_PREFIX + key)) == token

		# sessionに戻してみる 2020.08.10
		#memcache_key = self._tenant + UcfConfig.SESSIONKEY_CSRF_TOKEN_PREFIX + key + self.getLoginOperatorUniqueID()
		#is_ok = False
		#token_from_memcache = memcache.get(memcache_key)
		#if token_from_memcache is not None:
		#	is_ok = token_from_memcache == token
		#	if not without_refresh_token:
		#		memcache.delete(memcache_key)
		#if not is_ok:
		#	logging.warning('checkCSRFToken=' + str(is_ok) + '[token_from_memcache]' + str(token_from_memcache) + '[token]' + str(token))

		if sateraito_inc.developer_mode:
			return True

		logging.debug('getsession key=%s value=%s' % (key, token))
		logging.debug('full_key=' + str((UcfConfig.SESSIONKEY_CSRF_TOKEN_PREFIX + key)))
		logging.debug('full_key=' + str((token + UcfConfig.SESSIONKEY_CSRF_TOKEN_PREFIX + key)))
		is_ok = False
		token_from_memcache = self.getSession(UcfConfig.SESSIONKEY_CSRF_TOKEN_PREFIX + key)
		logging.debug('token_from_memcache=%s' % str(token_from_memcache))
		if token_from_memcache is not None:
			is_ok = token_from_memcache == token
		if not is_ok:
			logging.warning('checkCSRFToken=' + str(is_ok) + '[token_from_memcache]' + str(token_from_memcache) + '[token]' + str(token))
		return is_ok


	# 背景画像を使用しないか、またその場合の設定を取得
	def isNoUseBgPictures(self):
		#if self._tenant in ['nextsetdemo']:
		#	return True, '#FFFFFF'
		return False, ''

	# デフォルト背景画像のインデックスを返す（最低10個）
	def _getBgDefaultIdx(self):
		demo_tenants = ['sateraito.jp', 'sateraitooffice.personal']
		idx_ary = []
		if self._tenant in demo_tenants:
			idx_ary = ['01','02','04','03','05','09','06','10','07','11','08','12','13','15','16','18','14','19','17','21','20','22','24','23','25','27','26','28','29','31','30','32','33','34','35','36']
		else:
			idx_ary = ['01','02','04','03','05','09','06','10','07','11']
		return idx_ary

	# 1～10 のランダム数字をセット.背景画像用 ⇒ オリジナル画像が設定されていたらその範囲でセット
	def _createBgTypeIdx(self):

		idx_ary = []

		# オリジナル画像
		dept = self.getDeptInfo()
		if dept is not None:
			for i in range(10):
				if UcfUtil.getHashStr(dept, 'login_background_pc' + str(i + 1) + '_data_key') != '':
					idx_ary.append(str(i + 1).rjust(2, '0'))

		# カスタム画像があるかどうか
		is_exist_custom = len(idx_ary) > 0

		demo_tenants = ['sateraito.jp', 'sateraitooffice.personal']

		# カスタム画像がない場合は標準画像をセット
		if not is_exist_custom:
			idx_ary = self._getBgDefaultIdx()

		# 日付によって先頭画像を決定（デモテナント以外）
		if is_exist_custom or self._tenant not in demo_tenants:
			start_idx = (datetime.datetime.utcnow() - datetime.datetime(1900, 1, 1)).days % len(idx_ary)
			#logging.info('start_idx=' + str(start_idx))
			new_idx_ary = []
			for i in range(len(idx_ary)):
				idx = (i + start_idx) % len(idx_ary)
				#idx = (len(idx_ary) - start_idx + i) if start_idx > i else (i - start_idx)
				new_idx_ary.append(idx_ary[idx])
			idx_ary = new_idx_ary

		return idx_ary, is_exist_custom

	# テンプレートに渡す基本情報をセット
	def appendBasicInfoToTemplateVals(self, template_vals):
#		logging.info('appendBasicInfoToTemplateVals start...')
		dept = self.getDeptInfo()
		template_vals['config'] = self._createConfigForTemplate()
		template_vals['dept'] = dept
		template_vals['my_site_url'] = oem_func.getMySiteUrl(self._oem_company_code)
		template_vals['version'] = UcfUtil.md5(sateraito_inc.version)
		template_vals['vurl'] = '/a/' + self._tenant + '/'
		template_vals['vscripturl'] = '/script/' if not sateraito_inc.debug_mode else '/script/debug/' 
		template_vals['tenant'] = self._tenant
		template_vals['language'] = self._language if self._language is not None and self._language != '' else sateraito_inc.DEFAULT_LANGUAGE
		template_vals['extjs_locale_file'] = sateraito_func.getExtJsLocaleFileName(self._language if self._language is not None and self._language != '' else sateraito_inc.DEFAULT_LANGUAGE)
		template_vals['lang'] = self.getMsgs()
		template_vals['FREE_MODE'] = sateraito_func.isFreeMode(self._tenant)	# 無償バージョンかどうか
		# 教育機関モードでの制御廃止 2016.02.12
		#template_vals['EDUCATION_MODE'] = (dept.get('is_education_mode') == 'True') if (dept is not None and dept.get('is_education_mode') is not None) else False	# 教育機関モードかどうか
		login_mail_address = self.getLoginOperatorMailAddress()
		login_id = self.getLoginID()
		login_name = self.getLoginOperatorName()
		login_access_authority = self.getLoginOperatorAccessAuthority().split(',')
		login_delegate_function = self.getLoginOperatorDelegateFunction().split(',')
		login_delegate_management_groups = self.getLoginOperatorDelegateManagementGroups().split(',')
		template_vals['login'] = {'mail_address':login_mail_address, 'id':login_id, 'name':login_name, 'access_authority':login_access_authority, 'delegate_function':login_delegate_function, 'delegate_management_groups':login_delegate_management_groups}

		if self._design_type == UcfConfig.VALUE_DESIGN_TYPE_PC:
			isBgNoUse, BgColor = self.isNoUseBgPictures()
			template_vals['BgNoUse'] = isBgNoUse
			template_vals['BgColor'] = BgColor
			idx_ary, is_exist_custom = self._createBgTypeIdx()
			template_vals['BgTypeIdxAry'] = idx_ary
			template_vals['BgIsExistCustom'] = is_exist_custom
			template_vals['leftmenu_class'] = UcfUtil.nvl(self.getCookie(UcfConfig.COOKIEKEY_LEFTMENUCLASS)) if UcfUtil.nvl(self.getCookie(UcfConfig.COOKIEKEY_LEFTMENUCLASS)) != '' else 'on'

		elif self._design_type == UcfConfig.VALUE_DESIGN_TYPE_SP:
			template_vals['BgIsExistCustom'] = dept.get('login_background_sp1_data_key', '') != '' if dept is not None else False

		template_vals['BgIsExistCustomLogo'] = dept.get('logo_data_key', '') != '' if dept is not None else False
		template_vals['BgIsDispCustomLogo'] = dept.get('is_disp_login_custom_logo', '') == 'ACTIVE' if dept is not None else False

		# OEM会社コード
		template_vals['oem_company_code'] = oem_func.getValidOEMCompanyCode(dept.get('oem_company_code', '') if dept is not None else '')
		# サービスコード
		template_vals['sp_codes'] = self._sp_codes

#		user = users.get_current_user()
#		template_vals['user_email'] = user.email() if user != None else ''
#		logging.info('appendBasicInfoToTemplateVals end.')

	# 一時ログインキーをセット…これでこのページ内では通常のログインとは別のログイン認証が行われる
	def setTemporaryLoginActionKey(self, temporary_login_action_key):
		self._temporary_login_action_key = temporary_login_action_key

	def isAdmin(self):
		u'''管理者かどうか'''
		temp = ',' + self.getLoginOperatorAccessAuthority().replace(' ', '') + ','

		result = None
		if ',' + UcfConfig.ACCESS_AUTHORITY_ADMIN + ',' in temp:
			result = True
		else:
			result = False
		return result

	def isOperator(self, target_function=None):
		u'''委託管理者かどうか'''
		access_authority = UcfUtil.csvToList(self.getLoginOperatorAccessAuthority())
		delegate_function = UcfUtil.csvToList(self.getLoginOperatorDelegateFunction())
		result = False
		if UcfConfig.ACCESS_AUTHORITY_OPERATOR in access_authority:
			if target_function is None:
				result = True
			elif isinstance(target_function, str):
				if target_function == '' or target_function in delegate_function:
					result = True
			elif isinstance(target_function, list):
				for target_function_item in target_function:
					if target_function_item in delegate_function:
						result = True
						break
		return result

	def checkDateChanged(self, model):
		u'''更新日時チェック'''
		model_vo = model.exchangeVo(self._timezone)
		req_date_changed = UcfUtil.nvl(self.getRequest('date_changed'))
		if req_date_changed != '' and req_date_changed != UcfUtil.getHashStr(model_vo, 'date_changed'):
			return False
		else:
			return True

	def checkCheckKey(self, check_key, application_id, uid=''):
		is_ok = False
		if check_key != '':
			uid_check_keys = []
			# クライアント証明書チェック機能
			if application_id == UcfConfig.APPLICATIONID_CHECKCLIENTCERTFICATION:
				now = UcfUtil.getNow()	# 標準時
				md5_suffix_key = UcfConfig.MD5_SUFFIX_KEY_CHECKCLIENTCERTFICATION	# キー固定
				uid_check_keys.append(UcfUtil.md5(uid + UcfUtil.add_minutes(now, -5).strftime('%Y%m%d%H%M') + md5_suffix_key))
				uid_check_keys.append(UcfUtil.md5(uid + UcfUtil.add_minutes(now, -4).strftime('%Y%m%d%H%M') + md5_suffix_key))
				uid_check_keys.append(UcfUtil.md5(uid + UcfUtil.add_minutes(now, -3).strftime('%Y%m%d%H%M') + md5_suffix_key))
				uid_check_keys.append(UcfUtil.md5(uid + UcfUtil.add_minutes(now, -2).strftime('%Y%m%d%H%M') + md5_suffix_key))
				uid_check_keys.append(UcfUtil.md5(uid + UcfUtil.add_minutes(now, -1).strftime('%Y%m%d%H%M') + md5_suffix_key))
				uid_check_keys.append(UcfUtil.md5(uid + now.strftime('%Y%m%d%H%M') + md5_suffix_key))
				uid_check_keys.append(UcfUtil.md5(uid + UcfUtil.add_minutes(now, 1).strftime('%Y%m%d%H%M') + md5_suffix_key))
				uid_check_keys.append(UcfUtil.md5(uid + UcfUtil.add_minutes(now, 2).strftime('%Y%m%d%H%M') + md5_suffix_key))
				uid_check_keys.append(UcfUtil.md5(uid + UcfUtil.add_minutes(now, 3).strftime('%Y%m%d%H%M') + md5_suffix_key))
				uid_check_keys.append(UcfUtil.md5(uid + UcfUtil.add_minutes(now, 4).strftime('%Y%m%d%H%M') + md5_suffix_key))
			
			
			is_ok = False
			for uid_check_key in uid_check_keys:
				if uid_check_key.lower() == check_key.lower():
					is_ok = True
					break
		return is_ok

	# 設定に基づいてユーザ名の表示名を取得
	def getUserNameDisp(self, last_name, first_name, middle_name=''):
		return ucffunc.getUserNameDisp(self, self.getDeptInfo(), last_name, first_name, middle_name)


	def getLoginID(self):
		return UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_LOGIN_ID))

	def getLoginOperatorID(self):
		return UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_LOGIN_OPERATOR_ID))

	def getLoginOperatorName(self):
		return UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_LOGIN_NAME))

	def getLoginOperatorMailAddress(self):
		return UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_LOGIN_MAIL_ADDRESS))

	def getLoginOperatorAccessAuthority(self):
		return UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_ACCESS_AUTHORITY))

	# ログインユーザの委託管理機能一覧を取得
	def getLoginOperatorDelegateFunction(self):
		return UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_DELEGATE_FUNCTION))

	# ログインユーザの委託管理する管理グループ一覧を取得
	def getLoginOperatorDelegateManagementGroups(self):
		return UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_DELEGATE_MANAGEMENT_GROUPS))

	# ログインオペレータユニークＩＤを取得（空もあり得るので注意）
	def getLoginOperatorUniqueID(self):
		return UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_LOGIN_UNIQUE_ID))

	# ログイン時の適用プロファイルユニークIDを取得（空もあり得るので注意）
	def getLoginOperatorProfileUniqueID(self):
		return UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_LOGIN_PROFILE_UNIQUE_ID))

	# ログイン時の適用対象環境種別を取得（空もあり得るので注意）
	def getLoginOperatorTargetEnv(self):
		return UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_LOGIN_TARGET_ENV))

	# ログインユーザにパスワード変更を強制するフラグをセッションから取得
	def getLoginOperatorForcePasswordChangeFlag(self):
		return UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_LOGIN_FORCE_PASSWORD_CHANGE))

	# ログインユーザにパスワード変更を強制するフラグをセッションにセット
	def setLoginOperatorForcePasswordChangeFlag(self, force_type):
		self.setSession(UcfConfig.SESSIONKEY_LOGIN_FORCE_PASSWORD_CHANGE, force_type)

	# ログインユーザが次回パスワード変更フラグあるいはパスワード期限のため、パスワード変更ページにしか遷移できないかどうかをセッションから取得し必要ならリダイレクト
	def checkForcePasswordChange(self):
		force_password_change_type = self.getLoginOperatorForcePasswordChangeFlag()
		if force_password_change_type == 'FORCE':
			self.redirect('/a/' + self._tenant + '/personal/password/')
			return False
		elif force_password_change_type == 'FORCE2':
			self.redirect('/a/' + self._tenant + '/personal/otp/')
			return False
		else:
			return True

	# 「rurl_key」をセッションから取得　…パスワード変更ページなどから「元の認証ページに戻る」ためのキー
	def getLoginOperatorRURLKey(self):
		key = UcfConfig.SESSIONKEY_RURL_KEY
		rurl_key = UcfUtil.nvl(self.getSession(key))
		return rurl_key

	# 「rurl_key」をセッションにセット　…パスワード変更ページなどから「元の認証ページに戻る」ためのキー
	def setLoginOperatorRURLKey(self, rurl_key):
		key = UcfConfig.SESSIONKEY_RURL_KEY
		self.setSession(key, rurl_key)

	# アクセス申請ページの「元の認証ページに戻る」リンク用のRURLをセッションにセット
	# ※クエリーにURLを丸ごとセットするのは環境によってURLが長すぎて動作不備となるのでセッションで受け渡す方法に変更 2013.08.06
	def setOriginalProcessLinkToSession(self, rurl_key, rurl):
		if rurl_key != '':
			# セッションではなく別のmemcacheで管理するように変更（キーにguidが付いているせいか複数の情報がセッションにセットされるパターンがあり、結果としてmemcacheの上限１ＭＢを超えることがあるため） 2015.05.07
			#self.setSession(UcfConfig.SESSIONKEY_ORIGINAL_PROCESS_LINK_PREFIX + rurl_key, rurl)
			memcache_key = UcfConfig.SESSIONKEY_ORIGINAL_PROCESS_LINK_PREFIX + rurl_key + '_' + self._tenant
			memcache.set(key=memcache_key, value=rurl, time=86400)		# セッションと同じ24時間程度にしてみる

	# アクセス申請ページの「元の認証ページに戻る」リンク用のRURLをセッションから取得
	def getOriginalProcessLinkFromSession(self, rurl_key):
		rurl = ''
		if rurl_key != '':
			# セッションではなく別のmemcacheで管理するように変更（キーにguidが付いているせいか複数の情報がセッションにセットされるパターンがあり、結果としてmemcacheの上限１ＭＢを超えることがあるため） 2015.05.07
			#rurl = UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_ORIGINAL_PROCESS_LINK_PREFIX + rurl_key))
			memcache_key = UcfConfig.SESSIONKEY_ORIGINAL_PROCESS_LINK_PREFIX + rurl_key + '_' + self._tenant
			rurl = UcfUtil.nvl(memcache.get(memcache_key))
		return rurl

	def send_success_response(self, data=None):
		data_reponse = {
			'status': 'ok',
		}
		if data is not None:
			data_reponse['data'] = data

		self.response.headers['Content-Type'] = 'application/json'
		return self.response.out.write(json.JSONEncoder().encode(data_reponse))

############################################################
## TenantAppヘルパー…キュー用
############################################################
class TenantTaskHelper(TenantHelper):

	def getLoginID(self):
		return ''

	@convert_result_none_to_empty_str
	def get(self, *args, **keywords):
		# self.setTenant(tenant)
		self._request_type = UcfConfig.REQUEST_TYPE_GET
		self._language = sateraito_func.getActiveLanguage(self.getDeptInfo()['language']) if self.getDeptInfo() is not None else sateraito_inc.DEFAULT_LANGUAGE
		self.init()
		self.onLoad()
		# ドメインが'/'で開始している場合の対策（実際ないけど念のため）
		return self.processOfRequest(*args, **keywords)

	@convert_result_none_to_empty_str
	def post(self, *args, **keywords):
		# self.setTenant(tenant)
		self._request_type = UcfConfig.REQUEST_TYPE_POST
		self._language = sateraito_func.getActiveLanguage(self.getDeptInfo()['language']) if self.getDeptInfo() is not None else sateraito_inc.DEFAULT_LANGUAGE
		self.init()
		self.onLoad()
		return self.processOfRequest(*args, **keywords)

	def processOfRequest(self, *args, **keywords):
		u'''Requestがきた場合の処理（抽象メソッドイメージ）'''
		pass

	# 設定に基づいてユーザ名の表示名を取得
	def getUserNameDisp(self, last_name, first_name, middle_name=''):
		return ucffunc.getUserNameDisp(self, self.getDeptInfo(), last_name, first_name, middle_name)



############################################################
## TenantAPIヘルパー…外部からコールされるAPI用
############################################################
class TenantAPIHelper(TenantHelper):

	def getLoginID(self):
		return ''

	@convert_result_none_to_empty_str
	def get(self, tenant):
		self.setTenant(tenant)
		self._request_type = UcfConfig.REQUEST_TYPE_GET
		self._language = sateraito_func.getActiveLanguage(self.getDeptInfo()['language']) if self.getDeptInfo() is not None else sateraito_inc.DEFAULT_LANGUAGE
		self.init()
		self.onLoad()
		self._is_api = True
		self._application_id = ''
		self._career_type = UcfConfig.VALUE_CAREER_TYPE_API
		return self.processOfRequest(tenant)

	@convert_result_none_to_empty_str
	def post(self, tenant):
		self.setTenant(tenant)
		self._request_type = UcfConfig.REQUEST_TYPE_POST
		self._language = sateraito_func.getActiveLanguage(self.getDeptInfo()['language']) if self.getDeptInfo() is not None else sateraito_inc.DEFAULT_LANGUAGE
		self.init()
		self.onLoad()
		self._is_api = True
		self._application_id = ''
		self._career_type = UcfConfig.VALUE_CAREER_TYPE_API
		self.processOfRequest(tenant)

	def processOfRequest(self, tenant, token):
		u'''Requestがきた場合の処理（抽象メソッドイメージ）'''
		pass

	def checkAccessIPAddress(self, accept_ip_address_list, deny_ip_address_list=None):
		u''' アクセスIPアドレスをチェック '''
		return UcfUtil.isCheckIPAddressRange(self.getClientIPAddress(), accept_ip_address_list, deny_ip_address_list)

	def render(self, template_name, vals):
		design_type = UcfConfig.VALUE_DESIGN_TYPE_API

		self.response.headers['Content-Type'] = 'text/xml; charset=' + 'UTF-8' + ';'

		# レンダリング
		jinja_environment = sateraito_jinja2_environment.getEnvironmentObjForTenant(design_type)
		template = jinja_environment.get_template(template_name)
		self.response.out.write(template.render(vals))

	# 設定に基づいてユーザ名の表示名を取得
	def getUserNameDisp(self, last_name, first_name, middle_name=''):
		return ucffunc.getUserNameDisp(self, self.getDeptInfo(), last_name, first_name, middle_name)



############################################################
## Ajaxヘルパー
############################################################
class AjaxHelper(Helper):

	@convert_result_none_to_empty_str
	def get(self):
		self._code = 999
		self._msg = ''
		self._request_type = UcfConfig.REQUEST_TYPE_GET
		# ファイルアップロードのところはこれを指定するとNGなのでページ側で行う
#		self.response.headers['Content-Type'] = 'application/json'
#		FrontHelper.get(self)
		return self.processOfRequest()

	@convert_result_none_to_empty_str
	def post(self):
		self._code = 999
		self._msg = ''
		self._request_type = UcfConfig.REQUEST_TYPE_POST
		# ファイルアップロードのところはこれを指定するとNGなのでページ側で行う
#		self.response.headers['Content-Type'] = 'application/json'
#		FrontHelper.post(self)
		self.processOfRequest()

	def processOfRequest(self):
		u'''Requestがきた場合の処理（抽象メソッドイメージ）'''
		pass

	def responseAjaxResult(self, ret_value={}):
		if ret_value is None:
			ret_value = {}
		ret_value['msg'] = self._msg
		ret_value['code']= self._code
		return self.response.out.write(json.JSONEncoder().encode(ret_value))


############################################################
## Ajaxヘルパー
############################################################
class TenantAjaxHelper(TenantAppHelper):


	@convert_result_none_to_empty_str
	def get(self, *args, **keywords):
		self._code = 999
		self._msg = ''
		self._request_type = UcfConfig.REQUEST_TYPE_GET
		self._language = sateraito_func.getActiveLanguage(self.getDeptInfo()['language']) if self.getDeptInfo() is not None else sateraito_inc.DEFAULT_LANGUAGE
		if sateraito_func.checkCsrf(self.request) == False:
			self.response.set_status(403)
			return

		self.response.headers['Content-Type'] = 'application/json'
		return TenantAppHelper.get(self, *args, **keywords)

	@convert_result_none_to_empty_str
	def post(self, *args, **keywords):
		self._code = 999
		self._msg = ''
		self._request_type = UcfConfig.REQUEST_TYPE_POST
		self._language = sateraito_func.getActiveLanguage(self.getDeptInfo()['language']) if self.getDeptInfo() is not None else sateraito_inc.DEFAULT_LANGUAGE
		if sateraito_func.checkCsrf(self.request) == False:
			self.response.set_status(403)
			return

		self.response.headers['Content-Type'] = 'application/json'
		return TenantAppHelper.post(self, *args, **keywords)

	# def processOfRequest(self, tenant):
	# 	u'''Requestがきた場合の処理（抽象メソッドイメージ）'''
	# 	pass

	def responseAjaxResult(self, ret_value={}):
		if ret_value is None:
			ret_value = {}
		ret_value['msg'] = self._msg
		ret_value['code']= self._code
		return self.response.out.write(json.JSONEncoder().encode(ret_value))

############################################################
## Ajaxヘルパー（ファイルアップロード用）
############################################################
class TenantAjaxHelperWithFileUpload(TenantAppHelper):

	@convert_result_none_to_empty_str
	def get(self, *args, **keywords):
		self._code = 999
		self._msg = ''
		self._request_type = UcfConfig.REQUEST_TYPE_GET
		self._language = sateraito_func.getActiveLanguage(self.getDeptInfo()['language']) if self.getDeptInfo() is not None else sateraito_inc.DEFAULT_LANGUAGE
		return TenantAppHelper.get(self, *args, **keywords)

	@convert_result_none_to_empty_str
	def post(self, *args, **keywords):
		self._code = 999
		self._msg = ''
		self._request_type = UcfConfig.REQUEST_TYPE_POST
		self._language = sateraito_func.getActiveLanguage(self.getDeptInfo()['language']) if self.getDeptInfo() is not None else sateraito_inc.DEFAULT_LANGUAGE
		return TenantAppHelper.post(self, *args, **keywords)

	def processOfRequest(self, *args, **keywords):
		u'''Requestがきた場合の処理（抽象メソッドイメージ）'''
		pass

	def responseAjaxResult(self, ret_value={}):
		if ret_value is None:
			ret_value = {}
		ret_value['msg'] = self._msg
		ret_value['code']= self._code
		return self.response.out.write(json.JSONEncoder().encode(ret_value))


############################################################
## 画像ヘルパー
############################################################
class TenantImageHelper(TenantAppHelper):


	@convert_result_none_to_empty_str
	def get(self, tenant=None, picture_id=None, data_key=None):
		self.setTenant(tenant)
		self._request_type = UcfConfig.REQUEST_TYPE_GET
		self._language = sateraito_func.getActiveLanguage(self.getDeptInfo()['language']) if self.getDeptInfo() is not None else sateraito_inc.DEFAULT_LANGUAGE
		self.init()
		self.onLoad()
		return self.processOfRequest(tenant, picture_id, data_key)

	def processOfRequest(self, tenant, picture_id, data_key):
		u'''Requestがきた場合の処理（抽象メソッドイメージ）'''
		pass

	def responseIsLastModified(self, last_modified=None, is_force_response=False):
		is_last_modified = False
		if is_force_response == False and 'If-Modified-Since' in self.request.headers and last_modified is not None and self.request.headers['If-Modified-Since'] == str(last_modified):
#			logging.info('If-Modified-Since=' + self.request.headers['If-Modified-Since'])
#			logging.info('last_modified=' + str(last_modified))
			self.response.set_status(304)
			is_last_modified = True
		return is_last_modified

	def responseImage(self, binarydata, content_type=None, file_name=None, last_modified=None, is_force_response=False):
		if content_type is None or content_type == '':
			# 変更 2018.05.08
			#content_type = 'image'
			content_type = 'image/png'
		if content_type is not None and content_type != '':
			# 変更…ユニコードだとヘッダセットでエラーするので 2018.05.08
			#self.response.headers['Content-Type'] = content_type
			self.response.headers['Content-Type'] = str(content_type)
		if file_name is not None and file_name != '':
			self.response.headers['Content-Disposition'] = 'inline;filename=' + file_name
		# Edge cache にちょっと乗せてみる 2016.06.09
		#self.response.headers['Cache-Control'] = ''
		self.response.headers['cache-control'] = 'public, max-age=60'			# 60秒
		if is_force_response == False and last_modified is not None and last_modified != '':
#			logging.info('[last_modified]' + str(last_modified))
			self.response.headers['Last-Modified'] = str(last_modified)	# Wed, 21 Jun 2006 07:00:25 GMT
		bin_length = len(binarydata)
		if bin_length > 500000:	# over 500kb.
			logging.warning('picture size is too large [' + str(bin_length) + ']')
		self.response.write(binarydata)

############################################################
## ビューヘルパーの親クラス
############################################################
class ViewHelper():

	def applicate(self, vo, model, helper):
		return None

	#def formatDateTime(self, dat):
	#	u'''日付を表示に適切な文字列に変換（日付型エンティティには不要.文字列フィールドで日付型の場合などに使用）'''
	#	result = ''
	#	if dat <> None:
	#		dat = UcfUtil.getLocalTime(dat)
	#		if dat <> None:
	#			result = dat.strftime('%Y/%m/%d %H:%M:%S')
	#
	#	return result
	

############################################################
## １レコード分のVo情報をまとめて保持するクラス
############################################################
class UcfVoInfo():
	u'''１レコード分のVo情報をまとめて保持するクラス'''
	# Vo
	vo = None
	# 表示用Vo
	voVH = None
	# バリデーションチェック結果
	validator = None

	def __init__(self):
		# クラス変数の初期化（コンストラクタで明示的に行わないとインスタンス生成時に初期化されないため）
		self.index = 0
		# Vo
		self.vo = None
		# 表示用Vo
		self.voVH = None
		# バリデーションチェック結果
		self.validator = None

	def exchangeEncoding(vo):
		u''' voデータを表示用に文字コードを変換  2011/06/01 現在この処理は不要'''
		for k,v in vo.items():
			# ファイルオブジェクトなどをスルーするために変換できないものは無視（微妙？） 2009/11/19 T.ASAO
			try:
				vo[k] = v
			except:
				pass
		return vo
	exchangeEncoding = staticmethod(exchangeEncoding)


	def setVo(self, vo, view_helper, model, helper, isWithoutExchangeEncode=False):
		u''' voをセットし同時にvoVHも作成するメソッド
			※エンコードを同時にする場合は必ずテンプレートに渡す直前で行うこと
		'''
		# vo自体をセット
		self.vo = vo

		# VHを作成
		if view_helper != None:
			self.voVH = view_helper.applicate(vo, helper)
		else:
			self.voVH = vo

	def setRequestToVo(helper):
		u'''Requestデータをハッシュにセット. '''
		vo = {}
		# GAEGEN2対応
		#for argument in helper.request.arguments():
		for argument in helper.request.values:
			vo[argument] = helper.getRequest(argument)
		return vo
	setRequestToVo = staticmethod(setRequestToVo)


	def margeRequestToVo(helper, vo, isKeyAppend=False):
		u'''Requestデータを指定VOにマージ '''
		# GAEGEN2対応
		#for argument in helper.request.arguments():
		for argument in helper.request.values:
			if argument in vo or isKeyAppend:
				vo[argument] = helper.getRequest(argument)
	margeRequestToVo = staticmethod(margeRequestToVo)


############################################################
## 各ページでテンプレートに渡すための共通変数群を管理するクラス
############################################################
class UcfParameter():
	u'''各ページでテンプレートに渡すための共通変数群を管理するクラス'''
	# 詳細系ページ用
	voinfo = None
	# 一覧系ページ用（UcfVoInfoリスト）
	voinfos = None
	# Requestパラメータ用
	request = None
	# それ以外のパラメータ用
	data = None

	def __init__(self):
		u'''コンストラクタ'''
		# クラス変数の初期化（コンストラクタで明示的に行わないとインスタンス生成時に初期化されないため）
		self.voinfo = UcfVoInfo()
		self.voinfos = []
		self.all_count = 0
		self.request = {}
		self.data = {}

	def setRequestData(self, helper):
		# Requestパラメータをそのままセット
		# GAEGEN2対応
		#for argument in helper.request.arguments():
		for argument in helper.request.values:
			value = helper.getRequest(argument)
			self.request[argument] = value


############################################################
## フロント用：各ページでテンプレートに渡すためのパラメータクラス
############################################################
class UcfFrontParameter(UcfParameter):
	u'''フロント用：各ページでテンプレートに渡すためのパラメータクラス'''
	
	def __init__(self, helper):
		u'''フロント用の一般的なパラメータをUcfParameterにセット'''

		# 親のコンストラクタをコール
		UcfParameter.__init__(self)

		# Requestパラメータをそのままセット
		self.setRequestData(helper)

############################################################
## テナントアプリ用：各ページでテンプレートに渡すためのパラメータクラス
############################################################
class UcfTenantParameter(UcfParameter):
	u'''各ページでテンプレートに渡すためのパラメータクラス'''
	
	def __init__(self, helper):
		u'''一般的なパラメータをUcfParameterにセット'''

		# 親のコンストラクタをコール
		UcfParameter.__init__(self)

		# Requestパラメータをそのままセット
		self.setRequestData(helper)

############################################################
## Chrome拡張用共通ヘルパー
############################################################
class _ChromeExtentionHelper(FrontHelper):

	def setTenant(self, tenant):
		namespace_manager.set_namespace(tenant.lower())
		self._tenant = tenant
		self._dept = None
		self._is_dept_selected = False
		self._is_enable_cors = False
		#self._error_page = '/a/' + self._tenant + UcfConfig.URL_ERROR

	def getDeptInfo(self, no_memcache=False, is_force_select=False):
		memcache_key = 'deptinfo?tenant=' + self._tenant
		if is_force_select or (no_memcache and not self._is_dept_selected):
			self._dept = ucffunc.getDeptVo(self)
			self._is_dept_selected = True
			if self._dept is not None:
				DeptUtils.editVoForSelect(self, self._dept)
				memcache.set(key=memcache_key, value=self._dept, time=300)
		elif self._dept is None:
			self._dept = memcache.get(memcache_key)
			if self._dept is None:
				self._dept = ucffunc.getDeptVo(self)
				self._is_dept_selected = True
				if self._dept is not None:
					DeptUtils.editVoForSelect(self, self._dept)
					memcache.set(key=memcache_key, value=self._dept, time=300)
		return self._dept

	def getDeptValue(self, key):
		return self.getDeptInfo().get(key)

	# ユーザーのID、ドメインチェック
	def checkAvailableDomainsOrUsers(self, uid, not_redirect=False):
		# 個人利用、トライアル用の特別テナントについてはノーチェックとする
		is_available_ok = False
		if self._tenant == sateraito_inc.TENANT_ID_FOR_PERSONALUSER:
			is_available_ok = True
		else:
			available_domains_or_users = self.getDeptValue('available_domains_or_users')
			if uid != '':
				if uid.lower() in available_domains_or_users:
					is_available_ok = True
				else:
					uid_sp = uid.split('@')
					if len(uid_sp) > 1 and uid_sp[1].lower() in available_domains_or_users:
						is_available_ok = True
		if not is_available_ok:
			if not_redirect == False:
				self.redirectError(self.getMsg('MSG_INVALID_ACCESS_AUTHORITY'))
			return False, self.getMsg('MSG_INVALID_ACCESS_AUTHORITY')
		return is_available_ok, ''

	def enableCORS(self):
		# set header
		self.response.headers['Access-Control-Allow-Origin' ] = '*'
		self.response.headers['Access-Control-Allow-Headers'] = 'Origin, X-Requested-With, Content-Type, Accept'
		self.response.headers['Access-Control-Allow-Methods'] = 'GET, POST'

	def isValidTenant(self, tenant, not_redirect=False):
		# 無効テナントかどうかをチェック
		tenant_entry = sateraito_func.TenantEntry.getInstance(tenant, cache_ok=True)
		if tenant_entry is None:
			if not_redirect == False:
				self.redirectError(self.getMsg('MSG_THIS_APPRICATION_IS_NOTINSTALLED_FOR_YOUR_TENANT'))
			return False, self.getMsg('MSG_THIS_APPRICATION_IS_NOTINSTALLED_FOR_YOUR_TENANT')

		if tenant_entry.is_disable == True:
			if not_redirect == False:
				self.redirectError(self.getMsg('MSG_THIS_APPRICATION_IS_STOPPED_FOR_YOUR_TENANT'))
			return False, self.getMsg('MSG_THIS_APPRICATION_IS_STOPPED_FOR_YOUR_TENANT')

		if sateraito_func.isExpireAvailableTerm(tenant_entry):
			if not_redirect == False:
				self.redirectError(self.getMsg('MSG_THIS_APPRICATION_IS_EXPIRE_FOR_YOUR_TENANT'))
			return False, self.getMsg('MSG_THIS_APPRICATION_IS_EXPIRE_FOR_YOUR_TENANT')

		return True, ''


#############################################################
### Ajaxヘルパー（Chrome拡張用）
#############################################################
#class ChromeExtentionAjaxHelper(_ChromeExtentionHelper):
#
#	_is_enable_cors = False
#
#	@convert_result_none_to_empty_str
#	def get(self, *args, **keywords):
#		self._code = 999
#		self._msg = ''
#		self._request_type = UcfConfig.REQUEST_TYPE_GET
#		#if sateraito_func.checkCsrf(self.request) == False:
#		#	self.response.set_status(403)
#		#	return
#		return FrontHelper.get(self, *args, **keywords)
#
#	@convert_result_none_to_empty_str
#	def post(self, *args, **keywords):
#		self._code = 999
#		self._msg = ''
#		self._request_type = UcfConfig.REQUEST_TYPE_POST
#		#if sateraito_func.checkCsrf(self.request) == False:
#		#	self.response.set_status(403)
#		#	return
#		return FrontHelper.post(self, *args, **keywords)
#
#	def processOfRequest(self, *args, **keywords):
#		u'''Requestがきた場合の処理（抽象メソッドイメージ）'''
#		pass
#
#	def responseAjaxResult(self, ret_value={}):
#		if ret_value is None:
#			ret_value = {}
#		ret_value['msg'] = self._msg
#		ret_value['code']= self._code
#
#		logging.info(ret_value)
#
#		if self._is_enable_cors:
#			self.enableCORS()
#		self.response.headers['Content-Type'] = 'application/json'
#		return self.response.out.write(json.JSONEncoder().encode(ret_value))
#
#
#	# テンプレートに渡す基本情報をセット
#	def appendBasicInfoToTemplateVals(self, template_vals):
#		dept = self.getDeptInfo()
#		template_vals['config'] = self._createConfigForTemplate()
#		template_vals['dept'] = dept
#		template_vals['my_site_url'] = oem_func.getMySiteUrl(self._oem_company_code)
#		template_vals['version'] = UcfUtil.md5(sateraito_inc.version)
#		#template_vals['vurl'] = '/a/' + self._tenant + '/'
#		template_vals['vscripturl'] = '/script/' if not sateraito_inc.debug_mode else '/script/debug/' 
#		#template_vals['tenant'] = self._tenant
#		template_vals['language'] = self._language if self._language is not None and self._language != '' else sateraito_inc.DEFAULT_LANGUAGE
#		template_vals['extjs_locale_file'] = sateraito_func.getExtJsLocaleFileName(self._language if self._language is not None and self._language != '' else sateraito_inc.DEFAULT_LANGUAGE)
#		template_vals['lang'] = self.getMsgs()
#		# OEM会社コード
#		template_vals['oem_company_code'] = oem_func.getValidOEMCompanyCode(dept.get('oem_company_code', '') if dept is not None else '')
#		# サービスコード
#		template_vals['sp_codes'] = self._sp_codes



############################################################
## Chrome拡張用アプリページヘルパー
############################################################
class ChromeExtentionAppHelper(_ChromeExtentionHelper):

	# テンプレートに渡す基本情報をセット
	def appendBasicInfoToTemplateVals(self, template_vals):
		dept = self.getDeptInfo()
		template_vals['config'] = self._createConfigForTemplate()
		template_vals['dept'] = dept
		template_vals['my_site_url'] = oem_func.getMySiteUrl(self._oem_company_code)
		template_vals['version'] = UcfUtil.md5(sateraito_inc.version)
		#template_vals['vurl'] = '/a/' + self._tenant + '/'
		template_vals['vscripturl'] = '/script/' if not sateraito_inc.debug_mode else '/script/debug/' 
		#template_vals['tenant'] = self._tenant
		template_vals['language'] = self._language if self._language is not None and self._language != '' else sateraito_inc.DEFAULT_LANGUAGE
		template_vals['extjs_locale_file'] = sateraito_func.getExtJsLocaleFileName(self._language if self._language is not None and self._language != '' else sateraito_inc.DEFAULT_LANGUAGE)
		template_vals['lang'] = self.getMsgs()
		# OEM会社コード
		template_vals['oem_company_code'] = oem_func.getValidOEMCompanyCode(dept.get('oem_company_code', '') if dept is not None else '')
		# サービスコード
		template_vals['sp_codes'] = self._sp_codes

	# 認証や初期処理
	def onLoad(self):
		# 言語を決定（Cookieの値を考慮）
		hl_from_cookie = self.getCookie('hl')
		logging.info('hl_from_cookie=' + str(hl_from_cookie))
		if hl_from_cookie is None or hl_from_cookie == '':
			hl_from_cookie = sateraito_inc.DEFAULT_LANGUAGE
		if hl_from_cookie is not None and hl_from_cookie in sateraito_func.ACTIVE_LANGUAGES:
			self._language = hl_from_cookie

	# 認証や初期処理
	def authAndInitialize(self, input_tenant=None, nocheck_uid_exists=False):
		is_ok = True
		tenant = ''
		uid = ''
		session_id = ''
		user_unique_id =''

		#if sateraito_func.checkCsrf(self.request) == False:
		#	self.response.set_status(403)
		#	return

		# 認証方式変更対応.初回でもいきなりアクセスできるようにデフォルトテナントIDを使いつつ、さらにセッションではなくCookieにテナントIDをセット（セッション切れ防止）
		## ログインチェック（UIDは空のこともあるのでテナントIDで行う）
		#if UcfUtil.nvl(self.getSession(UcfConfig.SESSIONKEY_TENANT_ID)) == '':
		#	return Response(self.getMsg('MSG_NOT_LOGINED_FOR_EXT'), status=403)
		#tenant = self.getSession(UcfConfig.SESSIONKEY_TENANT_ID)
		#if input_tenant is None or input_tenant == '':
		if input_tenant is None:
			tenant = UcfUtil.nvl(self.getCookie(UcfConfig.COOKIE_KEY_TENANT_ID))
		else:
			tenant = input_tenant
		if tenant == '':
			tenant = sateraito_inc.TENANT_ID_FOR_PERSONALUSER

		# 認証方式変更対応
		#uid = self.getSession(UcfConfig.SESSIONKEY_LOGIN_ID)
		uid = UcfUtil.nvl(self.getCookie(UcfConfig.COOKIE_KEY_UID))
		logging.info('uid=%s' % (uid))
		logging.info('tenant=%s' % (tenant))

		is_valid_tenant, error_msg = self.isValidTenant(tenant, not_redirect=True)
		if is_valid_tenant == False:
			return False, 400, error_msg, tenant, uid, session_id, user_unique_id

		self.setTenant(tenant)

		# 利用可能な機能かどうかを判定
		if 'GPTAPP' not in self.getDeptInfo().get('chatgpt_available_functions', []):
			return False, 400, self.getMsg('MSG_NOAVAILABLE_FUNCTION'), tenant, uid, session_id, user_unique_id

		# ユーザーのID、ドメインチェック
		is_available_ok, error_msg = self.checkAvailableDomainsOrUsers(uid, not_redirect=True)
		if not is_available_ok:
			return False, 400, error_msg, tenant, uid, session_id, user_unique_id

		if not nocheck_uid_exists:
			# ユーザーID、セッションID全て空ならエラー
			# 本当のセッションIDではなくCookieに保存した擬似的なユーザーIDに変更
			#session_id = UcfUtil.nvl(self.session.sid)
			session_id = UcfUtil.nvl(self.getCookie(UcfConfig.COOKIE_KEY_USER_ID))
			user_unique_id = ''
			if uid == '' and user_unique_id == '' and session_id == '':
				return False, 400, self.getMsg('INVALID_USER'), tenant, uid, session_id, user_unique_id

		return True, 200, '', tenant, uid, session_id, user_unique_id

