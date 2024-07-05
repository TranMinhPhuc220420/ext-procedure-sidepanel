#!/usr/bin/python
# coding: utf-8

__author__ = 'T.ASAO <asao@sateraito.co.jp>'

import logging
import sateraito_inc


OEM_COMPANY_CODE_DEFAULT = 'sateraito'

def getMailMagazineTargetOEMCompanyCodes():
	return [OEM_COMPANY_CODE_DEFAULT]

def getBlackListTargetOEMCompanyCodes():
	return ['', OEM_COMPANY_CODE_DEFAULT]

def isValidSPCode(oem_company_code, sp_code):
	sp_code = sp_code.lower()
	if oem_company_code.lower() in [OEM_COMPANY_CODE_DEFAULT]:
		#return sp_code in []
		return False
	else:
		return False

def isValidOEMCompanyCode(oem_company_code):
	oem_company_code = oem_company_code.lower()
	return oem_company_code in [OEM_COMPANY_CODE_DEFAULT]

def getValidOEMCompanyCode(oem_company_code):
	if isValidOEMCompanyCode(oem_company_code):
		return oem_company_code.lower()
	else:
		return OEM_COMPANY_CODE_DEFAULT

def getMySiteUrl(oem_company_code):
	return sateraito_inc.my_site_url

def exchangeMessageID(msgid, oem_company_code):
	#logging.info('oem_company_code=' + oem_company_code)
	#logging.info('from msgid=' + msgid)
	#logging.info('exchange msgid into "' + msgid + '"')
	return msgid