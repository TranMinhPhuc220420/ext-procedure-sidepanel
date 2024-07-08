# coding: utf-8
from webapp_common.base_helper import *

from ucf.utils.models import GoogleAppsDomainEntry, GoogleAppsUserEntry

import sateraito_func

# モデル
model = 'gpt-3.5-turbo'

NUM_PER_PAGE = 15


############################################################
# REQUEST FOR USER LOGGED
############################################################
class AuthGetInfo(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if str(self.viewer_email) == '' or self.viewer_email is None:
        return self.responseError403()

      google_apps_domain = sateraito_func.getDomainPart(self.viewer_email)
      user_entry_dict = GoogleAppsUserEntry.get_dict(google_apps_domain, self.viewer_email)

      if user_entry_dict is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOTFOUND_USER_ENTRY'),
          'error_code': 400
        })

      if sateraito_func.logoutIfUserDisabled(self, google_apps_domain, self.viewer_email, user_entry_dict=user_entry_dict):
        return self.send_error_response({
          'error_message': self.getMsg('ACCOUNT_DISABLED_IN_APP'),
          'error_code': 403
        })

      ret_obj = {
        'user_email': user_entry_dict['user_email'],
        'google_apps_domain': user_entry_dict['google_apps_domain'],
        'family_name': user_entry_dict['family_name'],
        'given_name': user_entry_dict['given_name'],
        'avatar': user_entry_dict['avatar'],
        'provider': user_entry_dict['provider'],
        'locale': user_entry_dict['locale'],
        'is_admin': user_entry_dict['is_admin'],
        'disable_user': user_entry_dict['disable_user'],

        'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(user_entry_dict['created_date'], self._timezone)),
        'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(user_entry_dict['updated_date'], self._timezone)),
      }

      self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      # return Response(UcfMessage.getMessage(self.getMsg('MSG_SYSTEM_ERROR'), ()), status=999)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })


class RequestTodoSomething(WebappHelper):
  def processOfRequest(self):
    try:
      return self.send_success_response({
        "result": "success",
      })
    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

def add_url_rules(app):
  # ============ URL INDEX PAGE ============

  # ============ URL API ============

  # For /auth/<request_action>
  app.add_url_rule('/api/auth/get-info', view_func=AuthGetInfo.as_view(__name__ + '.AuthGetInfo'))

  app.add_url_rule('/api/req-todo-something', view_func=RequestTodoSomething.as_view(__name__ + '.RequestTodoSomething'))
