# coding: utf-8

import re
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
# GAEGEN2対応:jinja2ライブラリのバージョン変更に伴うフィルタ処理の変更
#from jinja2 import contextfilter, Markup
from jinja2 import pass_context
from markupsafe import Markup, escape

#+++++++++++++++++++++++++++++++++++++++
#+++ フィルタを登録
#+++++++++++++++++++++++++++++++++++++++
def registCustomFilters(jinja_environment):
	jinja_environment.filters['escapejs'] = escapejs
#	jinja_environment.filters['escapejson'] = escapejson
	jinja_environment.filters['linebreaksbr'] = linebreaksbr
	jinja_environment.filters['hyperlink_linebreaksbr'] = hyperlink_linebreaksbr

#+++++++++++++++++++++++++++++++++++++++
#+++ hyperlink_linebreaksbr:リンクをtarget="_brank" のハイパーリンク文字列に変換する
#+++++++++++++++++++++++++++++++++++++++
# GAEGEN2対応:jinja2ライブラリのバージョン変更に伴うフィルタ処理の変更
#@contextfilter
@pass_context
def hyperlink_linebreaksbr(context, value):
	result = ''
	if type(value) is int:
		result = str(value)
	else:
		if value is not None:
			result = value
			ptn_link = re.compile(r"(https?://[-_.!~*'()a-zA-Z0-9;/?:@&=+$,%#]+)")
			result = ptn_link.sub(r'!#!a href=!%!\1!%! target=!%!_blank!%! !$!\1!#!/a!$!', result)
			if context.eval_ctx.autoescape:
				result = result.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
			result = result.replace('\n', '<br />\n')
			result = result.replace('!#!', '<').replace('!$!', '>').replace('!%!', '"')
			if context.eval_ctx.autoescape:
				result = Markup(result)
	return result

#+++++++++++++++++++++++++++++++++++++++
#+++ escapejs:JavaScript用のエスケープ
#+++++++++++++++++++++++++++++++++++++++
# GAEGEN2対応:jinja2ライブラリのバージョン変更に伴うフィルタ処理の変更
#@contextfilter
@pass_context
def escapejs(context, value):
	result = ''
	if type(value) is int:
		result = str(value)
	else:
		if value is not None:
			# 長い文字列の連結パフォーマンス改善対応 2022.05.30
			#for c in value:
			#	result = result + '\\u' + hex(ord(c))[2:].zfill(4)
			result_list = []
			for c in value:
				result_list.append('\\u' + hex(ord(c))[2:].zfill(4))
			result = ''.join(result_list)
			if context.eval_ctx.autoescape:
				result = Markup(result)
	return result

#+++++++++++++++++++++++++++++++++++++++
#+++ escapejson:JavaScript用のjson用のエスケープ（escapejsでもOKだが長い文字列だとエラーしちゃうので簡易的に）
#+++++++++++++++++++++++++++++++++++++++
#@pass_context
#def escapejson(context, value):
#	result = ''
#	if type(value) is int:
#		result = str(value)
#	else:
#		for c in value:
#			if c in ('"', '\'', '}', '{', '_', ' ', '\\', ',', ':', '.', '@', '/', '<', '>'):
#				result = result + '\\u' + hex(ord(c))[2:].zfill(4)
#			else:
#				result = result + c
#		if context.eval_ctx.autoescape:
#			result = Markup(result)
#	return result

#+++++++++++++++++++++++++++++++++++++++
#+++ linebreaksbr:JavaScript用のエスケープ（autosafe設定の場合は、safeフィルタも使用される前提。例： xxx|linebreaksbr|safe）
#+++++++++++++++++++++++++++++++++++++++
# GAEGEN2対応:jinja2ライブラリのバージョン変更に伴うフィルタ処理の変更
#@contextfilter
@pass_context
def linebreaksbr(context, value):
	result = ''
	if type(value) is int:
		result = str(value)
	else:
		if value is not None:
			result = value
			if context.eval_ctx.autoescape:
				result = result.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
			result = result.replace('\n', '<br />\n')
			if context.eval_ctx.autoescape:
				result = Markup(result)
	return result

