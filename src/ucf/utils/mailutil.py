# coding: utf-8

import os,sys,math,datetime,time,hashlib
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行
#from google.appengine.ext import webapp
from google.appengine.api import mail
from ucf.utils.ucfxml import UcfXml

from ucf.config.ucfconfig import UcfConfig
from ucf.config.ucfmessage import UcfMessage
from ucf.utils.ucfutil import *
import oem_func

class UcfMailUtil():

	MAIL_TO = 'To'
	MAIL_CC = 'Cc'
	MAIL_BCC = 'Bcc'
	MAIL_REPLYTO = 'ReplyTo'
	MAIL_SUBJECT = 'Subject'
	MAIL_BODY = 'Body'
	MAIL_BODYHTML = 'BodyHtml'

	def getMailTemplateInfo(helper, mail_template_id):
		info = {}
		param_file_path = helper.getParamFilePath(os.path.join('mail', mail_template_id  + '.xml'))
		#logging.info(param_file_path)
		if os.path.exists(param_file_path):
			xml_mail_template = UcfXml.load(param_file_path)
			# ハッシュにして返す
#			info = xml_mail_template.exchangeToHash(isAttr=True, isChild=True)
			info[UcfMailUtil.MAIL_TO] = UcfXml.getInnerTextNvl(xml_mail_template, UcfMailUtil.MAIL_TO)
			info[UcfMailUtil.MAIL_CC] = UcfXml.getInnerTextNvl(xml_mail_template, UcfMailUtil.MAIL_CC)
			info[UcfMailUtil.MAIL_BCC] = UcfXml.getInnerTextNvl(xml_mail_template, UcfMailUtil.MAIL_BCC)
			info[UcfMailUtil.MAIL_REPLYTO] = UcfXml.getInnerTextNvl(xml_mail_template, UcfMailUtil.MAIL_REPLYTO)
			info[UcfMailUtil.MAIL_SUBJECT] = UcfXml.getInnerTextNvl(xml_mail_template, UcfMailUtil.MAIL_SUBJECT)
			info[UcfMailUtil.MAIL_BODY] = UcfXml.getInnerTextNvl(xml_mail_template, UcfMailUtil.MAIL_BODY)
			info[UcfMailUtil.MAIL_BODYHTML] = UcfXml.getInnerTextNvl(xml_mail_template, UcfMailUtil.MAIL_BODYHTML)
		return info
	getMailTemplateInfo = staticmethod(getMailTemplateInfo)

	# XMLではなくメッセージ定義ファイルから、件名、本文のみ取り出す版
	def getMailTemplateInfoByLanguageDef(helper, mail_template_id, lang=None):

		is_other_lang = lang is not None and lang != '' and lang != helper._language

		info = {}
		# ハッシュにして返す
		info[UcfMailUtil.MAIL_TO] = ''
		info[UcfMailUtil.MAIL_CC] = ''
		info[UcfMailUtil.MAIL_BCC] = ''
		info[UcfMailUtil.MAIL_REPLYTO] = ''
		if not is_other_lang:
			info[UcfMailUtil.MAIL_SUBJECT] = helper.getMsg('MAILSUBJECT_' + mail_template_id.upper())
			info[UcfMailUtil.MAIL_BODY] = helper.getMsg('MAILBODY_' + mail_template_id.upper())
		else:
			#msgs = UcfMessage.getMessageList(helper._approot_path, lang)
			msgs = UcfMessage.getMessageListEx(lang)
			
			info[UcfMailUtil.MAIL_SUBJECT] = UcfMessage.getMessage(UcfUtil.getHashStr(msgs, oem_func.exchangeMessageID('MAILSUBJECT_' + mail_template_id.upper(), helper._oem_company_code)))
			info[UcfMailUtil.MAIL_BODY] = UcfMessage.getMessage(UcfUtil.getHashStr(msgs, oem_func.exchangeMessageID('MAILBODY_' + mail_template_id.upper(), helper._oem_company_code)))
		info[UcfMailUtil.MAIL_BODYHTML] = ''
		return info
	getMailTemplateInfoByLanguageDef = staticmethod(getMailTemplateInfoByLanguageDef)

	#+++++++++++++++++++++++++++++++++++++++
	#+++ メールを1件送信
	#+++++++++++++++++++++++++++++++++++++++
	def sendOneMail(to='', sender='', subject='', body='', cc='', bcc='', reply_to='', body_html='', data=None, start_tag='[$$', end_tag='$$]'):
		u''' メールを1件送信 

		～パラメータ～
		[基本]
		to:Toアドレス
		sender:Sender
		subject:件名
		body:本文（TEXT）
		[オプション]
		reply_to:ReplyTo
		cc:Ccアドレス
		bcc:Bccアドレス
		body_html:本文（HTML)

		data:差込データ用ハッシュ
		start_tag:差込タグ（開始）
		end_tag:差込タグ（閉じ）

		'''

		# body, body_html, subject の差込対応
		subject = UcfUtil.editInsertTag(subject, data, start_tag, end_tag)
		body = UcfUtil.editInsertTag(body, data, start_tag, end_tag)
		body_html = UcfUtil.editInsertTag(body_html, data, start_tag, end_tag)


		#キーワード辞書
		kw = {}
#		kw['to'] = UcfUtil.nvl(to).encode('utf-8')
#		kw['sender'] = UcfUtil.nvl(sender).encode('utf-8')
#		kw['subject'] = UcfUtil.nvl(subject).encode('utf-8')
#		kw['body'] = UcfUtil.nvl(body).encode('utf-8')
#
#		#オプションキーワード辞書
#		if reply_to and reply_to != '':
#			kw['reply_to'] = reply_to.encode('utf-8')
#		if cc and cc != '':
#			kw['cc'] = cc.encode('utf-8')
#		if bcc and bcc != '':
#			kw['bcc'] = bcc.encode('utf-8')
#		if body_html and body_html != '':
#			kw['html'] = body_html.encode('utf-8')

#		kw['to'] = UcfUtil.nvl(to)
#		kw['sender'] = UcfUtil.nvl(sender)
#		kw['subject'] = UcfUtil.nvl(subject)
#		kw['body'] = UcfUtil.nvl(body)

#		#オプションキーワード辞書
#		if reply_to and reply_to != '':
#			kw['reply_to'] = reply_to
#		if cc and cc != '':
#			kw['cc'] = cc
#		if bcc and bcc != '':
#			kw['bcc'] = bcc
#		if body_html and body_html != '':
#			kw['html'] = body_html

		#メール送信
		message = mail.EmailMessage()
		message.sender = UcfUtil.nvl(sender)
		if to != '':
			message.to = UcfUtil.nvl(to)
		if cc != '':
			message.cc = UcfUtil.nvl(cc)
		if bcc != '':
			message.bcc = UcfUtil.nvl(bcc)
		if reply_to != '':
			message.reply_to = UcfUtil.nvl(reply_to)
		if subject != '':
			message.subject = UcfUtil.nvl(subject)
		if body != '':
			message.body = UcfUtil.nvl(body)
#		if body_html != '':
#			message.body_html = UcfUtil.nvl(body_html)
		message.send()

	sendOneMail = staticmethod(sendOneMail)
