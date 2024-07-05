#!/usr/bin/python
# coding: utf-8
# GAEGEN2対応:↑のcodingは本当は非推奨らしい. ファイルエンコードはUTF-8（Shift_JISはNG）である必要あり。

# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行
#import webapp2
from flask import Flask, Response, render_template, request, make_response, session, redirect
import json
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
import datetime, time
import random
import urllib
import base64
from google.appengine.api import taskqueue
from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.api import namespace_manager
from ucf.utils.ucfutil import UcfUtil
from ucf.utils.helpers import *

import sateraito_inc
import sateraito_func
#import sateraito_db

class Health(FrontHelper):
	def processOfRequest(self):
		try:
			#template_vals = {
			#}
			#self.appendBasicInfoToTemplateVals(template_vals)
			# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行（Responseをリターン）
			return Response('CHECK OK', status=200)
		except Exception as e:
			logging.exception(e)
			return Response('System Error.', status=500)


# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行. URLはwerkzeugの正規表現書式を使用可能. 従来の末尾の「$」は使用不可. as_view('XXX') はプロダクトを通して一意である必要あり
def add_url_rules(app):
	app.add_url_rule('/health',  view_func=Health.as_view(__name__ + '.Health'))
