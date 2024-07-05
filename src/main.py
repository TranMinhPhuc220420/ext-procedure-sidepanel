#!/usr/bin/env python
#!-*- coding:utf-8 -*-
import time

# GAEGEN2対応:独自ロガー
#import logging
import sateraito_logger as logging
import sateraito_inc

from flask import Flask, Response, render_template, request, session	#GAEGEN2対応:WebフレームワークとしてFlaskを使用
from google.appengine.api import wrap_wsgi_app					# GAEGEN2対応:AppEngine API SDKを使用する際に必要（yamlの　app_engine_apis: true　指定も必要）
from werkzeug.routing import BaseConverter								# GAEGEN2対応:routingで正規表現を使うために使う
# from google.appengine.ext import ndb

import os
import datetime

# GAEGEN2対応：セッション管理
# from utilities.flask_session.sessions import MemcachedSessionInterface							# セッション管理：Memcache版（namespace対応などカスタマイズするのでソースコード直接参照）
from utilities.gaesession import GaeNdbSessionInterface											# セッション管理：DB版（SameSite対応などカスタマイズするのでソースコード直接参照）

_TIME_START = time.time()

app = Flask(__name__)
app.wsgi_app = wrap_wsgi_app(app.wsgi_app)		# GAEGEN2対応:AppEngine API SDK対応


'''
main.py

@since: 2023-07-21
@version: 2023-08-29
@updated: Akitoshi Abe
'''


# セッション管理:セッションインタフェースを上書き
# 参考）https://flask.palletsprojects.com/en/2.2.x/api/#sessions
# permanent=True…ブラウザを閉じてもセッションが残るオプション
#app.session_interface = MemcachedSessionInterface(client=memcache, key_prefix='sateraitosession', use_signer=True, permanent=False)		#Memcache版
app.session_interface = GaeNdbSessionInterface(app, permanent=True)  # DataStore版
app.config.update(
	SESSION_COOKIE_NAME='SATEID2',  # g2版はSATEIDからSATEID2に変更
	SESSION_COOKIE_SECURE=True,
	SESSION_COOKIE_HTTPONLY=True,
	SESSION_COOKIE_SAMESITE='None',
	# SESSION_TYPE='memcached',
	SESSION_USE_SIGNER=True,
	SESSION_REFRESH_EACH_REQUEST=True,
)
app.secret_key = 'a3f5c2e07e69c7b8d4e7f9e8f5a7c3d4e1f7b2c9a8b7c6d4e3f2c1b9a8e7f6d5'
# セッション有効期限：permanent=Falseでも使用する
app.permanent_session_lifetime = datetime.timedelta(hours=24*31)  # ワークフローは31日セッションが継続
#app.permanent_session_lifetime = datetime.timedelta(minutes=10) 				# gaesessionsで5分以下だとexpires_onが更新されないので10分で検証(gaesessions.should_slide_expiryの実装により)


# GAEGEN2対応：URLマッピングを正規表現で行うためのクラス
class RegexConverter(BaseConverter):
	def __init__(self, url_map, *items):
		super(RegexConverter, self).__init__(url_map)
		self.regex = items[0]
app.url_map.converters['regex'] = RegexConverter


# add_url_rules
import health
health.add_url_rules(app)

# トップページ
import index
index.add_url_rules(app)

# GAEGEN2対応：サブモジュール化対応（各python側で定義した add_url_rulesをコール）
# エラーページ
import error
error.add_url_rules(app)

# NotFound
import notfound
notfound.add_url_rules(app)

import tenant_file
tenant_file.add_url_rules(app)


# GAEGEN2対応：View関数方式でページを定義（本来はflask.views.MethodViewクラス方式を採用だが簡単な処理はView関数でもOK）
@app.route('/_ah/warmup', methods=['GET', 'POST'])
def warmup():
	logging.info('warmup instance.')
	return Response(__name__, status=200)

@app.route('/_ah/start', methods=['GET'])
def start():
	return Response(__name__, status=200)

@app.route('/_ah/stop', methods=['GET'])
def stop():
	return Response(__name__, status=200)

# GAEGEN2対応：エラーハンドリング処理（各ページで処理できなかったエラーを大本のここでハンドリング可能）
@app.errorhandler(400)
def handle_bad_request(e):
	logging.exception(e)
	return 'Bad Request', 400
@app.errorhandler(502)
def handle_bad_gateway(e):
	logging.exception(e)
	return 'Bad Gateway', 502
@app.errorhandler(404)
def handle_notfound(e):
	# logging.exception(e)  # 他のシステムエラーのように調査対象としないようwarningに変更する
	logging.warning(e)
	return 'Not Found', 404
@app.errorhandler(500)
def handle_internalservererror(e):
	logging.exception(e)
	return 'Internal Server Error', 500

import logging as py_logging
py_logging.getLogger("requests").setLevel(py_logging.WARN)
py_logging.getLogger("urllib3").setLevel(py_logging.WARN)

if hasattr(logging, 'register_app'):
	if logging.GROUP_LOGS_BY_REQUEST:
		logging.register_app(app)

_TIME_END = time.time()
_TIME_INIT = _TIME_START - _TIME_END
logging.info('INIT main.py took: ~%.3fs' % _TIME_INIT)

if __name__ == '__main__':
	threaded = True
	if os.environ.get('SATERAITO_SET_SINGLETHREAD_MODE', '') == 'True':
		# defalutサービスをF1かつシングルスレッドで動作させる
		threaded = False
	app.run(debug=sateraito_inc.debug_mode, threaded=threaded)

