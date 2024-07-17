# coding: utf-8
import os, sys

from webapp_common.base_helper import *

from ucf.utils.models import GoogleAppsDomainEntry, GoogleAppsUserEntry, WorkflowDoc

from firebase_admin import messaging

import sateraito_func

# モデル
model = 'gpt-3.5-turbo'

NUM_PER_PAGE = 15

############################################################
# REQUEST FOR WEBAPP
############################################################

class WebAppConfig(WebappHelper):
  def processOfRequest(self):
    try:
      if not self.checkLogin():
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      config_get = request_json.get('config_get')
      logging.info("config_get=" + str(config_get))

      ret_obj = {}

      if config_get == 'firebase_config':
        ret_obj = sateraito_inc.FIREBASE_CONFIG

      self.send_success_response(ret_obj)

    except BaseException as e:
      logging.error(str(e))
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class ActionNotification(WebappHelper):
  def processOfRequest(self, google_apps_domain):
    try:
      if not self.checkLogin():
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      token_notification = request_json.get('token_notification')
      logging.info("token_notification=" + str(token_notification))

      user_entry = GoogleAppsUserEntry.getInstance(google_apps_domain, self.viewer_email)
      if user_entry is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOTFOUND_USER_ENTRY'),
          'error_code': 400
        })

      user_entry.token_notification = token_notification
      user_entry.put()

      ret_obj = {
        'msg': 'ok'
      }

      self.send_success_response(ret_obj)

    except BaseException as e:
      logging.error(str(e))
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

############################################################
# REQUEST FOR USER LOGGED
############################################################

class SetTokenNotification(WebappHelper):
  def processOfRequest(self, google_apps_domain):
    try:
      self.setNamespace(google_apps_domain)

      if not self.checkLogin():
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      token_notification = request_json.get('token_notification')
      logging.info("token_notification=" + str(token_notification))

      user_entry = GoogleAppsUserEntry.getInstance(google_apps_domain, self.viewer_email)
      if user_entry is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOTFOUND_USER_ENTRY'),
          'error_code': 400
        })

      user_entry.token_notification = token_notification
      user_entry.put()

      sateraito_func.notificationThanksForAccept(google_apps_domain, self.viewer_email, token_notification)

      ret_obj = {
        'msg': 'ok'
      }

      self.send_success_response(ret_obj)

    except BaseException as e:
      logging.error(str(e))
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })


class AuthGetInfo(WebappHelper):
  def processOfRequest(self):
    try:
      if not self.checkLogin():
        return self.responseError403()

      google_apps_domain = sateraito_func.getDomainPart(self.viewer_email)
      user_entry_dict = GoogleAppsUserEntry.get_dict(google_apps_domain, self.viewer_email)

      if user_entry_dict is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOTFOUND_USER_ENTRY'),
          'error_code': 400
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
      logging.error(str(e))
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

############################################################
# REQUEST FOR WORKFLOW DOC
############################################################

class GetNewWorkflowDocID(WebappHelper):
  def processOfRequest(self, google_apps_domain):
    try:
      if not self.checkLogin():
        return self.responseError403()
      
      self.setNamespace(google_apps_domain)

      ret_obj = {
        'status': 'ok',
        'workflow_doc_id': WorkflowDoc.getNewWorkflowDocID(),
      }

      self.send_success_response(ret_obj)

    except BaseException as e:
      logging.error(str(e))
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class CreateWorkflowDoc(WebappHelper):
  def processOfRequest(self, google_apps_domain):
    try:
      if not self.checkLogin():
        return self.responseError403()
      
      self.setNamespace(google_apps_domain)
      user_entry_dict = GoogleAppsUserEntry.get_dict(google_apps_domain, self.viewer_email)
      
      request_json = json.JSONDecoder().decode(request.get_data().decode())

      workflow_doc_id = request_json.get('workflow_doc_id')
      logging.info("workflow_doc_id=" + str(workflow_doc_id))
      if (workflow_doc_id is None or workflow_doc_id == ''):
        workflow_doc_id = WorkflowDoc.getNewWorkflowDocID()
        logging.info("getNewWorkflowDocID workflow_doc_id=" + str(workflow_doc_id))

      user_email = request_json.get('user_email')
      logging.info("user_email=" + str(user_email))

      id_email_request_check = request_json.get('id_email_request_check')
      logging.info("id_email_request_check=" + str(id_email_request_check))

      is_draft_email_request_check = sateraito_func.strToBool(request_json.get('is_draft_email_request_check'))
      logging.info("is_draft_email_request_check=" + str(is_draft_email_request_check))

      status_request_check = request_json.get('status_request_check')
      logging.info("status_request_check=" + str(status_request_check))

      seen_request_check_flag = sateraito_func.strToBool(request_json.get('seen_request_check_flag'))
      logging.info("seen_request_check_flag=" + str(seen_request_check_flag))

      new_row = WorkflowDoc(id=workflow_doc_id)
      new_row.workflow_doc_id = workflow_doc_id
      new_row.user_email = user_email
      new_row.id_email_request_check = id_email_request_check
      new_row.is_draft_email_request_check = is_draft_email_request_check
      new_row.status_request_check = status_request_check
      new_row.seen_request_check_flag = seen_request_check_flag

      new_row.author_email = self.viewer_email
      new_row.author_name = user_entry_dict.get('given_name', '')

      new_row.put()

      row_dict = new_row.to_dict()
      row_dict['id'] = new_row.key.id()

      sateraito_func.notificationForAdminHasNewDoc(google_apps_domain, self.viewer_email, row_dict)

      ret_obj = {
        'status': 'ok',
      }

      self.send_success_response(ret_obj)

    except BaseException as e:
      logging.error(str(e))
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

############################################################
# REQUEST FOR UNIT TEST
############################################################

class RequestTodoSomething(WebappHelper):
  def processOfRequest(self):
    try:
      if not self.checkLogin():
        return self.responseError403()

      google_apps_domain = sateraito_func.getDomainPart(self.viewer_email)
      user_entry_dict = GoogleAppsUserEntry.get_dict(google_apps_domain, self.viewer_email)

      webpush_action_detail = messaging.WebpushNotificationAction(
        action='action_detail',
        title='Detail',
        icon="https://ext2005-dot-vn-sateraito-apps-fileserver2.appspot.com/favicon.ico"
      )
      webpush_action_allow = messaging.WebpushNotificationAction(
        action='action_allow',
        title='Allow',
        icon="https://ext2005-dot-vn-sateraito-apps-fileserver2.appspot.com/images/check-48.png"
      )
      webpush_action_block = messaging.WebpushNotificationAction(
        action='action_block',
        title='Block',
        icon="https://ext2005-dot-vn-sateraito-apps-fileserver2.appspot.com/images/close-48.png"
      )
      webpush_notification = messaging.WebpushNotification(
        title=sateraito_func.randomString(10) + "- Title",
        body=sateraito_func.randomString(30) + "- Description",
        badge="https://ext2005-dot-vn-sateraito-apps-fileserver2.appspot.com/favicon.ico",
        icon="https://ext2005-dot-vn-sateraito-apps-fileserver2.appspot.com/favicon.ico",
        actions=[webpush_action_allow, webpush_action_block]
      )
      webpush = messaging.WebpushConfig(
        data={
          'test': 'hello world!'
        },
        notification=webpush_notification
      )

      message = messaging.Message(
        webpush=webpush,
        token=user_entry_dict['token_notification']
      )

      response = messaging.send(message)

      return self.send_success_response({
        "result": str(response),
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

  # For /webapp/<request_action>
  app.add_url_rule('/api/webapp/config',
                   view_func=WebAppConfig.as_view(__name__ + '.WebAppConfig'))

  # For /workflow-doc/<request_action>
  app.add_url_rule('/<google_apps_domain>/api/workflow-doc/get-new-id',
                   view_func=GetNewWorkflowDocID.as_view(__name__ + '.GetNewWorkflowDocID'))

  app.add_url_rule('/<google_apps_domain>/api/workflow-doc/create-new-doc',
                   view_func=CreateWorkflowDoc.as_view(__name__ + '.CreateWorkflowDoc'))

  # For /auth/<request_action>
  app.add_url_rule('/<google_apps_domain>/api/auth/set-token-notification',
                   view_func=SetTokenNotification.as_view(__name__ + '.SetTokenNotification'))

  app.add_url_rule('/api/auth/get-info',
                   view_func=AuthGetInfo.as_view(__name__ + '.AuthGetInfo'))

  app.add_url_rule('/api/req-todo-something',
                   view_func=RequestTodoSomething.as_view(__name__ + '.RequestTodoSomething'))
