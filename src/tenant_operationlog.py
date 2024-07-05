# coding: utf-8

# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
# GAEGEN2対応:webapp2ライブラリ廃止→Flask移行
#import webapp2
from flask import Flask, Response, render_template, request, make_response, session, redirect
from ucf.utils.helpers import *
from ucf.utils import loginfunc
from ucf.pages.operator import *
from ucf.pages.operationlog import *
import sateraito_inc
import sateraito_func

_gnaviid = 'DASHBOARD'
_leftmenuid = 'OPERATIONLOG'
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
#				self.redirectError(UcfMessage.getMessage(self.getMsg('MSG_INVALID_ACCESS_AUTHORITY')))
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
			ucfp.data['explains'] = [self.getMsg('EXPLAIN_OPERATIONLOG_HEADER')]

			template_vals = {
				'ucfp' : ucfp,
			}
			self.appendBasicInfoToTemplateVals(template_vals)

			self.render('operationlog.html', self._design_type, template_vals)
		except BaseException as e:
			self.outputErrorLog(e)
			self.redirectError(UcfMessage.getMessage(self.getMsg('MSG_SYSTEM_ERROR'), ()))
			return


class XtListPage(TenantAjaxHelper):
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

			start = int(req['start'])
			limit = int(req['limit'])

			sk_operation = UcfUtil.getHashStr(req, 'sk_operation').lower()
			sk_operator_unique_id = UcfUtil.getHashStr(req, 'sk_operator_unique_id')

			# 検索
			q = UCFMDLOperationLog.query()

			# ユーザ詳細ページの検索
			if sk_operator_unique_id != '':
				q = q.filter(UCFMDLOperationLog.operator_unique_id == sk_operator_unique_id)
			# 全体のログイン履歴一覧
			else:
				if sk_operation != '':
					q = q.filter(UCFMDLOperationLog.operation == sk_operation)

			q = q.order(-UCFMDLOperationLog.operation_date)

			# q.count() が非常に負荷、時間がかかるので暫定的に変更（将来は「もっと表示」方式、あるいはマウススクロールで次の情報を取る方式に変更したい） 2016.02.26
			#logging.info('before q.count()...')
			#count = q.count()
			#logging.info('after q.count() = ' + str(count) + '...')
			login_history_max_export_cnt = self.getDeptInfo().get('login_history_max_export_cnt')
			max_export_cnt = UcfUtil.toInt(login_history_max_export_cnt)		# 最大出力件数
			if max_export_cnt <= 0:
				max_export_cnt = 1000
			count = max_export_cnt

			result_list = []
			for model in q.iter(limit=limit, offset=start):
				vo = model.exchangeVo(self._timezone)
				OperationLogUtils.editVoForList(self, vo)
				result_list.append(vo)

			logging.info(result_list)
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
	app.add_url_rule('/a/<tenant>/operationlog/',  view_func=IndexPage.as_view(__name__ + '.IndexPage'))
	app.add_url_rule('/a/<tenant>/operationlog/xtlist',  view_func=XtListPage.as_view(__name__ + '.XtListPage'))
