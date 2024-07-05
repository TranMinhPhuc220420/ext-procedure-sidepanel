# coding: utf-8

# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行
#import webapp2
from flask import Flask, Response, render_template, request, make_response, session, redirect
from ucf.utils.helpers import *
from ucf.utils.models import *
from ucf.utils import ucffunc,loginfunc
from ucf.pages.chatgpt_history import *
import sateraito_inc
import sateraito_func


_gnaviid = 'HISTORY'
_leftmenuid = 'INDEX'
class IndexPage(TenantAppHelper):
	def processOfRequest(self, tenant):
		try:
			self._approot_path = os.path.dirname(__file__)
			if self.isValidTenant() == False:
				return

			if loginfunc.checkLogin(self) == False:
				return

			# 権限チェック
			if self.isAdmin() == False:
				self.redirect('/a/' + tenant + '/personal/')
				return

			# ログイン時の各種情報を取得＆チェック
			is_select_ok, user_vo, error_msg = loginfunc.checkLoginInfo(self)
			if is_select_ok == False:
				return
			# パスワード次回変更フラグをチェック
			if self.checkForcePasswordChange() == False:
				return

			ucfp = UcfTenantParameter(self)
			ucfp.data['gnaviid'] = _gnaviid
			ucfp.data['leftmenuid'] = _leftmenuid
			ucfp.data['explains'] = [self.getMsg('EXPLAIN_HISTORY_HEADER')]

			template_vals = {
				'ucfp' : ucfp,
				'unqid':self.request.get('unqid')				# 証明書情報を開く（history.replaceState とも連動）
			}
			self.appendBasicInfoToTemplateVals(template_vals)

			self.render('history_index.html', self._design_type, template_vals)
		except BaseException as e:
			self.outputErrorLog(e)
			self.redirectError(UcfMessage.getMessage(self.getMsg('MSG_SYSTEM_ERROR'), ()))
			return


class XtGetDetailPage(TenantAjaxHelper):
	def processOfRequest(self, tenant):
		try:
			if self.isValidTenant(not_redirect=True) == False:
				self._code = 400
				self._msg = self.getMsg('MSG_NOT_INSTALLED', (self._tenant))
				self.responseAjaxResult()
				return

			if loginfunc.checkLogin(self, not_redirect=True) == False:
				self._code = 403
				self._msg = self.getMsg('MSG_NOT_LOGINED')
				self.responseAjaxResult()
				return

			# ログイン時の各種情報を取得＆チェック
			is_select_ok, user_vo, error_msg = loginfunc.checkLoginInfo(self, not_redirect=True)
			if is_select_ok == False:
				self._code = 403
				self._msg = error_msg
				self.responseAjaxResult()
				return

			if self.isAdmin() == False:
				self._code = 403
				self._msg = self.getMsg('MSG_INVALID_ACCESS_AUTHORITY')
				self.responseAjaxResult()
				return

			# Requestからvoにセット
			req = UcfVoInfo.setRequestToVo(self)

			unique_id = UcfUtil.getHashStr(req, 'unique_id')
			if unique_id == '':
				self._code = 100
				self._msg = self.getMsg('MSG_INVALID_PARAMETER', (unique_id))
				self.responseAjaxResult()
				return

			# 検索
			vo = {}
			entry = ChatGPTHistoryUtils.getData(self, unique_id)
			if entry is not None:
				entry_vo = entry.exchangeVo(self._timezone)
				ChatGPTHistoryUtils.editVoForSelect(self, entry_vo)
				UcfUtil.margeHash(vo, entry_vo)									# 既存データをVoにコピー

				# 委託管理者の場合は自分がアクセスできる管理グループかをチェック
				if self.isOperator() and not ucffunc.isDelegateTargetManagementGroup(UcfUtil.getHashStr(vo, 'management_group'), UcfUtil.csvToList(self.getLoginOperatorDelegateManagementGroups())):
					self._code = 403
					self._msg = self.getMsg('MSG_INVALID_ACCESS_BY_DELEGATE_MANAGEMENT_GROUPS')
					self.responseAjaxResult()
					return

			else:
				self._code = 404
				self._msg = self.getMsg('MSG_NOT_EXIST_DATA')
				self.responseAjaxResult()
				return

			logging.info(vo)
			ret_value = {
				'data': vo
			}

			self._code = 0
			self.responseAjaxResult(ret_value)

		except BaseException as e:
			self.outputErrorLog(e)
			self._code = 999
			self.responseAjaxResult()


class XtListPage(TenantAjaxHelper):
	def processOfRequest(self, tenant):
		# GAEGEN2対応
		#logging.info(self.request)
		logging.info(request.headers)
		logging.info(request.get_data())
		try:
			if self.isValidTenant(not_redirect=True) == False:
				self._code = 400
				self._msg = self.getMsg('MSG_NOT_INSTALLED', (self._tenant))
				self.responseAjaxResult()
				return

			if loginfunc.checkLogin(self, not_redirect=True) == False:
				self._code = 403
				self._msg = self.getMsg('MSG_NOT_LOGINED')
				self.responseAjaxResult()
				return

			# ログイン時の各種情報を取得＆チェック
			is_select_ok, user_vo, error_msg = loginfunc.checkLoginInfo(self, not_redirect=True)
			if is_select_ok == False:
				self._code = 403
				self._msg = error_msg
				self.responseAjaxResult()
				return

			if self.isAdmin() == False:
				self._code = 403
				self._msg = self.getMsg('MSG_INVALID_ACCESS_AUTHORITY')
				self.responseAjaxResult()
				return

			# Requestからvoにセット
			req = UcfVoInfo.setRequestToVo(self)

			start = int(req['start'])
			limit = int(req['limit'])

			sk_access_date_date_from = UcfUtil.getHashStr(req, 'sk_access_date_date_from')
			sk_access_date_date_to = UcfUtil.getHashStr(req, 'sk_access_date_date_to')
			sk_result_code = UcfUtil.getHashStr(req, 'sk_result_code')
			sk_user_id = UcfUtil.getHashStr(req, 'sk_user_id')
			sk_keyword = UcfUtil.getHashStr(req, 'sk_keyword')

			# SearchAPIだと1000件以上ヒットできないので検索条件がなく1000件より先をページングする場合は通常Queryに変更（キーワード検索以外は通常Queryに入れられるがIndex作成が面倒なので...） 2021.11.25
			#sk_search_type = 'fulltext'
			#if sk_keyword == '' and sk_user_id == '' and sk_result_code == '' and sk_access_date_date_from == '' and sk_access_date_date_to == '':
			if start > 1000 and (sk_keyword == '' and sk_user_id == '' and sk_result_code == '' and sk_access_date_date_from == '' and sk_access_date_date_to == ''):
				sk_search_type = ''
			else:
				sk_search_type = 'fulltext'

			sk_access_date_date_from_epoch = 0
			sk_access_date_date_to_epoch = 0

			if sk_access_date_date_from != '':
				logging.info('sk_access_date_date_from=%s' % (UcfUtil.getUTCTime(UcfUtil.getDateTime(sk_access_date_date_from + ' 00:00:00'), self._timezone)))
				sk_access_date_date_from_epoch = sateraito_func.datetimeToEpoch(UcfUtil.getUTCTime(UcfUtil.getDateTime(sk_access_date_date_from + ' 00:00:00'), self._timezone))

			if sk_access_date_date_to != '':
				logging.info('sk_access_date_date_to=%s' % (UcfUtil.getUTCTime(UcfUtil.add_days(UcfUtil.getDateTime(sk_access_date_date_to + ' 00:00:00'), 1), self._timezone)))
				sk_access_date_date_to_epoch = sateraito_func.datetimeToEpoch(UcfUtil.getUTCTime(UcfUtil.add_days(UcfUtil.getDateTime(sk_access_date_date_to + ' 00:00:00'), 1), self._timezone))

			# フルテキスト検索
			if sk_search_type == 'fulltext':

				delegate_management_groups = UcfUtil.csvToList(self.getLoginOperatorDelegateManagementGroups()) if self.getLoginOperatorDelegateManagementGroups() != '' else []
				result_list, count = ChatGPTHistoryUtils.searchDocsByFullText(self, sk_keyword, sk_access_date_date_from_epoch, sk_access_date_date_to_epoch, sk_result_code, sk_user_id, self.isOperator(), delegate_management_groups, limit, offset=start)
				for vo in result_list:
					vo['access_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(sateraito_func.epochTodatetime(float(vo.get('access_date_epoch'))), self._timezone)) if 'access_date_epoch' in vo and vo['access_date_epoch'] != '0.0' else ''
					vo['date_created'] = UcfUtil.nvl(UcfUtil.getLocalTime(sateraito_func.epochTodatetime(float(vo.get('date_created_epoch'))), self._timezone)) if 'date_created_epoch' in vo and vo['date_created_epoch'] != '0.0' else ''
					ChatGPTHistoryUtils.editVoForSelect(self, vo)

			# 通常検索
			else:

				login_history_max_export_cnt = self.getDeptInfo().get('login_history_max_export_cnt')
				max_export_cnt = UcfUtil.toInt(login_history_max_export_cnt)		# 最大出力件数（設定流用）
				if max_export_cnt < 10000:
					max_export_cnt = 10000

				# 検索
				q = UCFMDLChatHistory.query()
				# 委託管理者なら自分が触れるデータのみ対象
				delegate_management_groups = UcfUtil.csvToList(self.getLoginOperatorDelegateManagementGroups()) if self.getLoginOperatorDelegateManagementGroups() != '' else []
				if self.isOperator() and len(delegate_management_groups) > 0:
					q = q.filter(UCFMDLChatHistory.management_group.IN(delegate_management_groups))
				q = q.order(-UCFMDLChatHistory.date_created)

				result_list = []
				for model in q.iter(limit=limit, offset=start):
					vo = model.exchangeVo(self._timezone)
					ChatGPTHistoryUtils.editVoForSelect(self, vo)
					result_list.append(vo)

				# count() はコストかかるが、1000件以下の場合はSearchAPIなのでまあいいかな
				#count = max_export_cnt
				count = q.count()

			ret_value = {
				 'all_count': str(count)
				,'records': result_list
			}

			self._code = 0
			self.responseAjaxResult(ret_value)

		except BaseException as e:
			self.outputErrorLog(e)
			self._code = 999
			self.responseAjaxResult()





# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行. URLはwerkzeugの正規表現書式を使用可能. 従来の末尾の「$」は使用不可. as_view('XXX') はプロダクトを通して一意である必要あり
#app = webapp2.WSGIApplication([('/a/([^/]*)/[^/].+', Page)], debug=sateraito_inc.debug_mode, config=sateraito_func.wsgi_config)
def add_url_rules(app):
	app.add_url_rule('/a/<tenant>/history/',  view_func=IndexPage.as_view(__name__ + '.IndexPage'))
	app.add_url_rule('/a/<tenant>/history/xtgetdetail',  view_func=XtGetDetailPage.as_view(__name__ + '.XtGetDetailPage'))
	app.add_url_rule('/a/<tenant>/history/xtlist',  view_func=XtListPage.as_view(__name__ + '.XtListPage'))

