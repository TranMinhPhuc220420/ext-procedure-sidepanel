# coding: utf-8
import datetime
import re

from google.appengine.datastore.datastore_query import Cursor

from webapp_common.base_helper import *

from ucf.pages.book import BookUtils
from ucf.pages.user_stories import UserStoriesUtils
from ucf.pages.user_chapters import UserChaptersUtils
from ucf.pages.stories_users_joined import StoriesUsersJoinedUtils
from ucf.pages.user_info import UserInfoUtils

import sateraito_mail
from webapp_common import chatgpt_func_v2

# モデル
model = 'gpt-3.5-turbo'
api_key = sateraito_inc.CHATGPT_API_KEY

NUM_PER_PAGE = 15


# Webapp Page
class BasePage(WebappHelper):
  def processOfRequest(self, path):
    # check login
    loginCheck = self.checkLogin()
    logging.info("loginCheck=" + str(loginCheck))

    template_vals = {}
    if loginCheck.get('status') and not sateraito_func.logoutIfUserDisabled(self, self.viewer_email):
      uid = self.viewer_email

      template_vals = {
        'my_site_url': sateraito_inc.my_site_url,
        'uid': uid,
        'viewer_email': self.viewer_email,
        'viewer_name': self.viewer_email.split('@')[0],
        'is_workflow_admin': self.is_workflow_admin,
      }
    else:
      template_vals = {
        'my_site_url': sateraito_inc.my_site_url,
      }

    self.appendBasicInfoToTemplateVals(template_vals)
    self.render('reactjs_frontend.html', self._design_type, template_vals)

class IndexPage(WebappHelper):
  def processOfRequest(self):
    # check login
    loginCheck = self.checkLogin()
    logging.info("loginCheck=" + str(loginCheck))

    template_vals = {}
    if loginCheck.get('status') and not sateraito_func.logoutIfUserDisabled(self, self.viewer_email):
      uid = self.viewer_email

      template_vals = {
        'my_site_url': sateraito_inc.my_site_url,
        'uid': uid,
        'viewer_email': self.viewer_email,
        'viewer_name': self.viewer_email.split('@')[0],
        'is_workflow_admin': self.is_workflow_admin,
      }
    else:
      template_vals = {
        'my_site_url': sateraito_inc.my_site_url,
      }

    self.appendBasicInfoToTemplateVals(template_vals)
    self.render('reactjs_frontend.html', self._design_type, template_vals)

class DetailBookPage(WebappHelper):
  def processOfRequest(self, book_id):
    # check login
    loginCheck = self.checkLogin()
    logging.info("loginCheck=" + str(loginCheck))

    template_vals = {}
    if loginCheck.get('status') and not sateraito_func.logoutIfUserDisabled(self, self.viewer_email):
      uid = self.viewer_email

      template_vals = {
        'my_site_url': sateraito_inc.my_site_url,
        'uid': uid,
        'viewer_email': self.viewer_email,
        'viewer_name': self.viewer_email.split('@')[0],
        'is_workflow_admin': self.is_workflow_admin,
      }
    else:
      template_vals = {
        'my_site_url': sateraito_inc.my_site_url,
      }

    book_dict = UCFMDLBook.getDict(book_id)
    if book_dict:
      creator_dict = UCFMDLUserInfo.getDict(book_dict['creator_id'])

      template_vals['book_head'] = {
        'book_id': book_dict['id'],
        'book_url': sateraito_inc.my_site_url + '/book/' + book_dict['id'],
        'title': book_dict['title'],
        'category_name': book_dict['category_book_name'],
        'creator_name': creator_dict['fullname'],
        'book_cover': json.JSONDecoder().decode(book_dict['book_cover']),
        'summary': book_dict['summary'][0:200],
      }

    self.appendBasicInfoToTemplateVals(template_vals)
    self.render('reactjs_frontend.html', self._design_type, template_vals)


############################################################
# REQUEST FOR USER LOGGED
############################################################
class AuthGetInfo(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      user_entry = sateraito_func.UserEntry.getInstance(self.viewer_email)
      if user_entry is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOTFOUND_USER_ENTRY'),
          'error_code': 400
        })

      if sateraito_func.logoutIfUserDisabled(self, self.viewer_email, user_entry=user_entry):
        return self.send_error_response({
          'error_message': self.getMsg('ACCOUNT_DISABLED_IN_APP'),
          'error_code': 403
        })

      u_info_entry = UCFMDLUserInfo.getDict(self.viewer_email)
      if u_info_entry is None:
        u_info_entry = {
          'be_registered': False,
          'email': self.viewer_email,
          'skill': '',
          'nickname': '',
          'date_of_birth': '',
          'gender': '',
          'description': '',
          'lives_in': '',
          'come_from': '',
          'works_at': '',
          'website_url': '',
          'twitter_url': '',
          'facebook_url': '',
          'instagram_url': '',
          'linkedin_url': '',
          'language': '',
          'created_date': '',
          'updated_date': '',
        }

      skill = []
      if u_info_entry['skill']:
        skill = json.JSONDecoder().decode(u_info_entry['skill'])

      ret_obj = {
        'id': u_info_entry['id'],
        'avatar_url': u_info_entry['avatar_url'],
        'be_registered': u_info_entry['be_registered'],
        'come_from': u_info_entry['come_from'],
        'date_of_birth': u_info_entry['date_of_birth'],
        'description': u_info_entry['description'],
        'email': u_info_entry['email'],
        'facebook_url': u_info_entry['facebook_url'],
        'family_name': u_info_entry['family_name'],
        'fullname': u_info_entry['fullname'],
        'gender': u_info_entry['gender'],
        'given_name': u_info_entry['given_name'],
        'google_apps_user_id': u_info_entry['google_apps_user_id'],
        'instagram_url': u_info_entry['instagram_url'],
        'language': u_info_entry['language'],
        'linkedin_url': u_info_entry['linkedin_url'],
        'lives_in': u_info_entry['lives_in'],
        'nickname': u_info_entry['nickname'],
        'skill': skill,
        'twitter_url': u_info_entry['twitter_url'],
        'website_url': u_info_entry['website_url'],
        'works_at': u_info_entry['works_at'],

        'followers': u_info_entry['followers'],
        'following': u_info_entry['following'],

        'user_email': user_entry.user_email,
        'sign_with': user_entry.sign_with,
        'role': user_entry.role,
        'disable_user': user_entry.disable_user,

        'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(u_info_entry['created_date'], self._timezone)),
        'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(u_info_entry['updated_date'], self._timezone)),
      }

      self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      # return Response(UcfMessage.getMessage(self.getMsg('MSG_SYSTEM_ERROR'), ()), status=999)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class AuthGetInfoById(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      user_logged = self.checkLogin().get('status')

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      user_info_id = request_json.get('user_info_id', '')
      if user_info_id == '':
        logging.error("Not has user_info_id")
        return self.send_error_response({
          'error_message': self.getMsg('NOTFOUND_USER'),
          'error_code': 400
        })

      logging.info(user_info_id)
      u_info_entry = UCFMDLUserInfo.getDict(user_info_id)
      if u_info_entry is None:
        logging.error("NOTFOUND_USER")
        return self.send_error_response({
          'error_message': self.getMsg('NOTFOUND_USER'),
          'error_code': 400
        })

      skill = []
      if u_info_entry['skill']:
        skill = json.JSONDecoder().decode(u_info_entry['skill'])

      ret_obj = {
        'id': u_info_entry['id'],
        'user_entry_id': u_info_entry['user_entry_id'],
        'avatar_url': u_info_entry['avatar_url'],
        'be_registered': u_info_entry['be_registered'],
        'come_from': u_info_entry['come_from'],
        'date_of_birth': u_info_entry['date_of_birth'],
        'description': u_info_entry['description'],
        'email': u_info_entry['email'],
        'facebook_url': u_info_entry['facebook_url'],
        'family_name': u_info_entry['family_name'],
        'fullname': u_info_entry['fullname'],
        'gender': u_info_entry['gender'],
        'given_name': u_info_entry['given_name'],
        'google_apps_user_id': u_info_entry['google_apps_user_id'],
        'instagram_url': u_info_entry['instagram_url'],
        'language': u_info_entry['language'],
        'linkedin_url': u_info_entry['linkedin_url'],
        'lives_in': u_info_entry['lives_in'],
        'nickname': u_info_entry['nickname'],
        'skill': skill,
        'twitter_url': u_info_entry['twitter_url'],
        'website_url': u_info_entry['website_url'],
        'works_at': u_info_entry['works_at'],

        'followers': u_info_entry['followers'],
        'following': u_info_entry['following'],

        # 'user_email': user_entry.user_email,
        # 'sign_with': user_entry.sign_with,
        # 'role': user_entry.role,
        # 'disable_user': user_entry.disable_user,

        'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(u_info_entry['created_date'], self._timezone)),
        'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(u_info_entry['updated_date'], self._timezone)),
      }

      self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class AuthSetInfo(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      user_entry = sateraito_func.UserEntry.getInstance(self.viewer_email)
      if user_entry is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOTFOUND_USER_ENTRY'),
          'error_code': 400
        })

      u_info_entry = UCFMDLUserInfo.getInstance(self.viewer_email)
      if u_info_entry is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOTFOUND_USER'),
          'error_code': 400
        })

      # get params
      request_json = json.JSONDecoder().decode(request.get_data().decode())

      email = request_json.get('email')
      given_name = request_json.get('given_name')
      family_name = request_json.get('family_name')
      fullname = request_json.get('fullname')
      language = request_json.get('language')

      skill = request_json.get('skill')
      nickname = request_json.get('nickname')
      date_of_birth = request_json.get('date_of_birth')
      gender = request_json.get('gender')

      description = request_json.get('description')
      lives_in = request_json.get('lives_in')
      come_from = request_json.get('come_from')
      works_at = request_json.get('works_at')

      website_url = request_json.get('website_url')
      twitter_url = request_json.get('twitter_url')
      facebook_url = request_json.get('facebook_url')
      instagram_url = request_json.get('instagram_url')
      linkedin_url = request_json.get('linkedin_url')

      need_put = False

      # flag user was registered
      if not u_info_entry.be_registered:
        u_info_entry.be_registered = True
        need_put = True

      if given_name and given_name != u_info_entry.given_name:
        u_info_entry.given_name = given_name
        need_put = True
      if family_name and family_name != u_info_entry.family_name:
        u_info_entry.family_name = family_name
        need_put = True
      if email != u_info_entry.email:
        if email and email != '' and UCFMDLUserInfo.isDuppliceEmail(email, self.viewer_email):
          return self.send_error_response({
            'error_message': self.getMsg('EMAIL_IS_WAS_REGISTERED'),
            'error_code': 400
          })
        u_info_entry.email = email
        need_put = True
      if fullname and fullname != u_info_entry.fullname:
        u_info_entry.fullname = fullname
        need_put = True
      if language and language != u_info_entry.language:
        u_info_entry.language = language
        need_put = True

      if skill and skill != u_info_entry.skill:
        u_info_entry.skill = skill
        need_put = True
      if nickname and nickname != u_info_entry.nickname:
        u_info_entry.nickname = nickname
        need_put = True
      if date_of_birth and date_of_birth != u_info_entry.date_of_birth:
        u_info_entry.date_of_birth = date_of_birth
        need_put = True
      if gender and gender != u_info_entry.gender:
        u_info_entry.gender = gender
        need_put = True

      if description and description != u_info_entry.description:
        u_info_entry.description = description
        need_put = True
      if lives_in and lives_in != u_info_entry.lives_in:
        u_info_entry.lives_in = lives_in
        need_put = True
      if come_from and come_from != u_info_entry.come_from:
        u_info_entry.come_from = come_from
        need_put = True
      if works_at and works_at != u_info_entry.works_at:
        u_info_entry.works_at = works_at
        need_put = True

      if website_url and website_url != u_info_entry.website_url:
        u_info_entry.website_url = website_url
        need_put = True
      if twitter_url and twitter_url != u_info_entry.twitter_url:
        u_info_entry.twitter_url = twitter_url
        need_put = True
      if facebook_url and facebook_url != u_info_entry.facebook_url:
        u_info_entry.facebook_url = facebook_url
        need_put = True
      if instagram_url and instagram_url != u_info_entry.instagram_url:
        u_info_entry.instagram_url = instagram_url
        need_put = True
      if linkedin_url and linkedin_url != u_info_entry.linkedin_url:
        u_info_entry.linkedin_url = linkedin_url
        need_put = True

      if need_put:
        u_info_entry.put()
        UserInfoUtils.rebuildTextSearchIndex(u_info_entry)

      ret_obj = {
        'id': u_info_entry.key.id(),
        'avatar_url': u_info_entry.avatar_url,
        'be_registered': u_info_entry.be_registered,
        'come_from': u_info_entry.come_from,
        'date_of_birth': u_info_entry.date_of_birth,
        'description': u_info_entry.description,
        'email': u_info_entry.email,
        'facebook_url': u_info_entry.facebook_url,
        'family_name': u_info_entry.family_name,
        'fullname': u_info_entry.fullname,
        'gender': u_info_entry.gender,
        'given_name': u_info_entry.given_name,
        'google_apps_user_id': u_info_entry.google_apps_user_id,
        'instagram_url': u_info_entry.instagram_url,
        'language': u_info_entry.language,
        'linkedin_url': u_info_entry.linkedin_url,
        'lives_in': u_info_entry.lives_in,
        'nickname': u_info_entry.nickname,
        'skill': skill,
        'twitter_url': u_info_entry.twitter_url,
        'website_url': u_info_entry.website_url,
        'works_at': u_info_entry.works_at,

        'user_email': user_entry.user_email,
        'sign_with': user_entry.sign_with,
        'role': user_entry.role,
        'disable_user': user_entry.disable_user,

        'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(u_info_entry.created_date, self._timezone)),
        'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(u_info_entry.updated_date, self._timezone)),
      }

      self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      # return Response(UcfMessage.getMessage(self.getMsg('MSG_SYSTEM_ERROR'), ()), status=999)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class AuthSetRole(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      user_entry = sateraito_func.UserEntry.getInstance(self.viewer_email)
      if user_entry is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOTFOUND_USER_ENTRY'),
          'error_code': 400
        })

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # set role
      role = request_json.get('role', '')

      if role not in [sateraito_inc.KEY_ROLE_ADMIN, sateraito_inc.KEY_ROLE_CREATOR, sateraito_inc.KEY_ROLE_USER]:
        return self.send_error_response({
          'error_message': self.getMsg('ROLE_NOT_DEFINE'),
          'error_code': 400
        })

      user_entry.role = role
      user_entry.put()

      ret_obj = {
        'user_email': user_entry.user_email,
        'sign_with': user_entry.sign_with,
        'role': user_entry.role,
        'disable_user': user_entry.disable_user,
        'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(user_entry.created_date, self._timezone)),
        'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(user_entry.updated_date, self._timezone)),
      }

      self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class AuthSetLanguage(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      user_info_row = UCFMDLUserInfo.getInstance(self.viewer_email)
      if user_info_row is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND_USER_INFO'),
          'error_code': 400
        })

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # set language
      language = request_json.get('language', '')

      if language not in sateraito_func.LIST_LANGUAGE:
        return self.send_error_response({
          'error_message': self.getMsg('LANGUAGE_NOT_DEFINE'),
          'error_code': 400
        })

      user_info_row.language = language
      user_info_row.put()

      ret_obj = {
        'language': language,
        'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(user_info_row.updated_date, self._timezone)),
      }

      self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class AuthAddFollower(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      userinfo_row = UCFMDLUserInfo.getInstance(self.viewer_email)
      if userinfo_row is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND_USER_INFO'),
          'error_code': 400
        })
      id_userinfo = userinfo_row.key.id()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # set role
      id_user_follow = request_json.get('id_user_follow')
      userinfo_follow_row = UCFMDLUserInfo.getInstance(id_user_follow)
      if userinfo_follow_row is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND_USER_INFO_WANT_FOLLOW'),
          'error_code': 400
        })

      # set for user are following
      u_following = userinfo_row.following
      if id_user_follow not in u_following:

        u_following.append(id_user_follow)

        userinfo_row.following = u_following
        userinfo_row.put()

      # set for user are followed
      u_followers = userinfo_follow_row.followers
      if id_userinfo not in u_followers:

        u_followers.append(id_userinfo)

        userinfo_follow_row.u_followers = u_followers
        userinfo_follow_row.put()

      ret_obj = {
        'id_user_follower': id_userinfo,
        'id_user_following': id_user_follow,
      }

      self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class AuthRemoveFollower(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      userinfo_row = UCFMDLUserInfo.getInstance(self.viewer_email)
      if userinfo_row is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND_USER_INFO'),
          'error_code': 400
        })
      id_userinfo = userinfo_row.key.id()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # set role
      id_user_follow = request_json.get('id_user_follow', '')
      userinfo_follow_row = UCFMDLUserInfo.getInstance(id_user_follow)
      if userinfo_follow_row is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND_USER_INFO_WANT_FOLLOW'),
          'error_code': 400
        })

      # set for user are following
      u_following = userinfo_row.following
      if id_user_follow in u_following:

        u_following.remove(id_user_follow)

        userinfo_row.following = u_following
        userinfo_row.put()

      # set for user are followed
      u_followers = userinfo_follow_row.followers
      if id_userinfo in u_followers:

        u_followers.remove(id_userinfo)

        userinfo_follow_row.u_followers = u_followers
        userinfo_follow_row.put()

      ret_obj = {
        'id_user_follower': id_userinfo,
        'id_user_following': id_user_follow,
      }

      self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class SearchUserInfo(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())
      limit = int(request_json.get('limit', '500'))
      user_name = request_json.get('user_name', '')

      data_res = []
      result_list, count, have_more_rows = UserInfoUtils.searchDocsByFullText(self, self.viewer_email, user_name, page=1, limit=limit)
      logging.info("SearchUserInfo count=%s" % str(count))

      for item in result_list:
        user_info_dict = UCFMDLUserInfo.getDict(item['user_entry_id'])
        if user_info_dict:

          data_res.append({
            'id': user_info_dict['id'],
            'email': user_info_dict['email'],
            'family_name': user_info_dict['family_name'],
            'fullname': user_info_dict['fullname'],
            'given_name': user_info_dict['given_name'],
            'nickname': user_info_dict['nickname'],
            'user_info_id': user_info_dict['id'],
            'user_entry_id': user_info_dict['user_entry_id'],
            'avatar_url': user_info_dict['avatar_url'],
            'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(user_info_dict['created_date'], self._timezone)),
            'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(user_info_dict['updated_date'], self._timezone)),
          })
        else:
          UserInfoUtils.removeFromIndexById(item['user_entry_id'])

      ret_obj = {
        'data': data_res,
        'count': count,
      }
      self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class AdminSearchUserInfo(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()
      # check is workflow admin
      if not self.is_workflow_admin:
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())
      limit = int(request_json.get('limit', '500'))
      page = request_json.get('page', 1)
      user_name = request_json.get('user_name', '')

      data_res = []
      result_list, count, have_more_rows = UserInfoUtils.searchDocsByFullText(self, self.viewer_email, user_name, limit, page)
      logging.info("AdminSearchUserInfo count=%s" % str(count))

      for item in result_list:
        u_info_entry = UCFMDLUserInfo.getDict(item['user_entry_id'])

        if u_info_entry:
          skill = []
          if u_info_entry['skill']:
            skill = json.JSONDecoder().decode(u_info_entry['skill'])

          data_item = {
            'id': u_info_entry['id'],
            'avatar_url': u_info_entry['avatar_url'],
            'be_registered': u_info_entry['be_registered'],
            'come_from': u_info_entry['come_from'],
            'date_of_birth': u_info_entry['date_of_birth'],
            'description': u_info_entry['description'],
            'email': u_info_entry['email'],
            'facebook_url': u_info_entry['facebook_url'],
            'family_name': u_info_entry['family_name'],
            'fullname': u_info_entry['fullname'],
            'gender': u_info_entry['gender'],
            'given_name': u_info_entry['given_name'],
            'instagram_url': u_info_entry['instagram_url'],
            'language': u_info_entry['language'],
            'linkedin_url': u_info_entry['linkedin_url'],
            'lives_in': u_info_entry['lives_in'],
            'nickname': u_info_entry['nickname'],
            'skill': skill,
            'twitter_url': u_info_entry['twitter_url'],
            'website_url': u_info_entry['website_url'],
            'works_at': u_info_entry['works_at'],

            'followers': u_info_entry['followers'],
            'following': u_info_entry['following'],

            'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(u_info_entry['created_date'], self._timezone)),
            'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(u_info_entry['updated_date'], self._timezone)),
          }

          data_res.append(data_item)
        else:
          UserInfoUtils.removeFromIndexById(item['user_entry_id'])

      ret_obj = {
        "results": data_res,
        "have_more_rows": have_more_rows,
      }
      self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class AdminSearchUserEntry(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()
      # check is workflow admin
      if not self.is_workflow_admin:
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())
      page_size = request_json.get('page_size', 100)
      page = request_json.get('page', 1)
      sign_with = request_json.get('sign_with')
      disable_user = request_json.get('disable_user')
      email_verified = request_json.get('email_verified')
      role = request_json.get('role')

      query = sateraito_func.UserEntry.query()
      if sign_with:
        query = query.filter(sateraito_func.UserEntry.sign_with == sign_with)
      if disable_user:
        query = query.filter(sateraito_func.UserEntry.disable_user == disable_user)
      if email_verified:
        query = query.filter(sateraito_func.UserEntry.email_verified == email_verified)
      if role:
        query = query.filter(sateraito_func.UserEntry.role == role)

      query = query.order(-sateraito_func.UserEntry.created_date)
      results = query.fetch(limit=(page_size + 1), offset=((page - 1) * page_size))

      have_more_rows = len(results) == (page_size + 1)
      logging.info("have_more_rows=%s" % str(have_more_rows))

      # remove last item for check have more rows
      if have_more_rows:
        results.pop()

      data_res = []
      for row in results:
        user_entry_id = row.key.id()
        row_dict = row.to_dict()

        user_dict = UCFMDLUserInfo.getDict(user_entry_id)
        if not user_dict:
          logging.error("UCFMDLUserInfo.getDict(%s) is None" % str(user_entry_id))
          continue

        # hide security
        del row_dict['pws_hashed']

        row_dict['user_info_id'] = user_dict['id']

        row_dict['avatar_url'] = user_dict['avatar_url']
        row_dict['be_registered'] = user_dict['be_registered']
        row_dict['come_from'] = user_dict['come_from']
        row_dict['date_of_birth'] = user_dict['date_of_birth']
        row_dict['description'] = user_dict['description']
        row_dict['email'] = user_dict['email']
        row_dict['facebook_url'] = user_dict['facebook_url']
        row_dict['family_name'] = user_dict['family_name']
        row_dict['fullname'] = user_dict['fullname']
        row_dict['gender'] = user_dict['gender']
        row_dict['given_name'] = user_dict['given_name']
        row_dict['google_apps_user_id'] = user_dict['google_apps_user_id']
        row_dict['instagram_url'] = user_dict['instagram_url']
        row_dict['language'] = user_dict['language']
        row_dict['linkedin_url'] = user_dict['linkedin_url']
        row_dict['lives_in'] = user_dict['lives_in']
        row_dict['nickname'] = user_dict['nickname']
        row_dict['twitter_url'] = user_dict['twitter_url']
        row_dict['website_url'] = user_dict['website_url']
        row_dict['works_at'] = user_dict['works_at']

        row_dict['skill'] = []
        if user_dict['skill']:
          row_dict['skill'] = json.JSONDecoder().decode(user_dict['skill'])

        row_dict['created_date'] = UcfUtil.getLocalTime(row_dict['created_date'], self._timezone).strftime('%Y/%m/%d %H:%M')
        row_dict['updated_date'] = UcfUtil.getLocalTime(row_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M')

        data_res.append(row_dict)

      self.send_success_response({
        "results": data_res,
        "have_more_rows": have_more_rows,
      })

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class AdminSetDisableUserEntry(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()
      # check is workflow admin
      if not self.is_workflow_admin:
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # set role
      username_entry = request_json.get('username_entry')
      is_disable = request_json.get('is_disable')

      if username_entry in sateraito_inc.LIST_USER_IS_ADMIN:
        return self.send_error_response({
          'error_message': self.getMsg('CAN_NOT_DISABLE_ACCOUNT_ADMIN'),
          'error_code': 400
        })

      user_entry = sateraito_func.UserEntry.getInstance(username_entry)
      if user_entry is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOTFOUND_USER_ENTRY'),
          'error_code': 400
        })

      user_entry.disable_user = is_disable
      user_entry.put()

      ret_obj = {
        'user_email': user_entry.user_email,
        'sign_with': user_entry.sign_with,
        'role': user_entry.role,
        'disable_user': user_entry.disable_user,
        'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(user_entry.created_date, self._timezone)),
        'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(user_entry.updated_date, self._timezone)),
      }

      self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })


############################################################
# REQUEST FOR TYPES BOOK
############################################################
class AddTypeBook(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()
      # check is workflow admin
      if not self.is_workflow_admin:
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      name = request_json.get('name', '').strip()
      type_parent_id = request_json.get('type_parent_id', None)

      if name == '':
        return self.send_error_response({
          'error_message': self.getMsg('PARAM_INVALID'),
          'error_code': 400
        })

      # has in datastore
      if UCFMDLTypeBook.getKeyTypeByName(name, type_parent_id=type_parent_id):
        return self.send_error_response({
          'error_message': self.getMsg('NAME_TYPE_BOOK_HAD_IN_DATASTORE'),
          'error_code': 400
        })

      new_row = UCFMDLTypeBook()
      new_row.name = name
      if type_parent_id:
        new_row.type_parent_id = type_parent_id
      new_row.put()

      UCFMDLTypeBook.clearAllTypeInstanceCache()
      UCFMDLTypeBook.clearAllCategoryInstanceCache(type_parent_id)
      UCFMDLTypeBook.clearAllCategoryInstanceCache()

      ret_obj = {
        'id': new_row.key.id(),
        'name': new_row.name,
        'type_parent_id': new_row.type_parent_id,
        'total_category': 0,
        'total_book': 0,
        'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(new_row.created_date, self._timezone)),
        'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(new_row.updated_date, self._timezone)),
      }

      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class EditTypeBook(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()
      # check is workflow admin
      if not self.is_workflow_admin:
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      type_book_name = request_json.get('type_book_name', '')
      type_book_id = request_json.get('type_book_id', '')
      type_parent_id = request_json.get('type_parent_id', None)

      type_book_row = UCFMDLTypeBook.getInstance(type_book_id)
      if type_book_row is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND_TYPE_BOOK'),
          'error_code': 400
        })

      if not type_parent_id and type_book_row.type_parent_id:
        type_parent_id = type_book_row.type_parent_id

      # has in datastore
      key_had_in_datastore = UCFMDLTypeBook.getKeyTypeByName(type_book_name, type_parent_id=type_parent_id)
      if key_had_in_datastore and key_had_in_datastore.id() != type_book_id:
        return self.send_error_response({
          'error_message': self.getMsg('NAME_TYPE_BOOK_HAD_IN_DATASTORE'),
          'error_code': 400
        })

      is_edit_type_book = type_book_row.type_parent_id is None

      type_book_row.name = type_book_name
      if type_parent_id and type_book_row.type_parent_id != type_parent_id:
        type_book_row.type_parent_id = type_parent_id
      # Save
      type_book_row.put()

      # clear memcache book use type_book
      UCFMDLTypeBook.clearAllTypeInstanceCache()
      UCFMDLTypeBook.clearAllCategoryInstanceCache(type_parent_id)
      UCFMDLTypeBook.clearAllCategoryInstanceCache()

      query_book = UCFMDLBook.query()
      if is_edit_type_book:
        query_book = query_book.filter(UCFMDLBook.type_book_id == type_book_id)
        rows = query_book.fetch()
        for row in rows:
            row.type_book_name = type_book_name
            row.put()
      else:
        query_book = query_book.filter(UCFMDLBook.category_book_id == type_book_id)
        rows = query_book.fetch()
        for row in rows:
          row.category_book_name = type_book_name
          row.put()

      ret_obj = {
      }
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class RemoveTypeBook(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()
      # check is workflow admin
      if not self.is_workflow_admin:
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      type_book_id = request_json.get('type_book_id', '')

      type_book_row = UCFMDLTypeBook.getInstance(type_book_id)
      if type_book_row is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND_TYPE_BOOK'),
          'error_code': 400
        })

      # check ok to delete

      if not type_book_row.type_parent_id:
        # had category use type_book
        query_category = UCFMDLTypeBook.query()
        query_category = query_category.filter(UCFMDLTypeBook.type_parent_id == str(type_book_id))
        query_category = query_category.filter(UCFMDLTypeBook.del_flag == False)
        if query_category.count() > 0:
          return self.send_error_response({
            'error_message': self.getMsg('HAD_CATEGORY_USE_TYPE_BOOK'),
            'error_code': 400
          })

        # had book use type_book
        query_book = UCFMDLBook.query()
        query_book = query_book.filter(UCFMDLBook.type_book_id == type_book_id)
        query_book = query_book.filter(UCFMDLBook.del_flag == False)
        if query_book.count() > 0:
          return self.send_error_response({
            'error_message': self.getMsg('HAD_BOOK_USE_TYPE_BOOK'),
            'error_code': 400
          })
      else:
        # had book use category_book
        query_book = UCFMDLBook.query()
        query_book = query_book.filter(UCFMDLBook.category_book_id == type_book_id)
        query_book = query_book.filter(UCFMDLBook.del_flag == False)
        if query_book.count() > 0:
          return self.send_error_response({
            'error_message': self.getMsg('HAD_BOOK_USE_CATEGORY_BOOK'),
            'error_code': 400
          })

        UCFMDLTypeBook.clearAllCategoryInstanceCache(type_book_row.type_parent_id)

      type_book_row.del_flag = True
      type_book_row.put()

      UCFMDLTypeBook.clearAllTypeInstanceCache()
      UCFMDLTypeBook.clearAllCategoryInstanceCache()

      ret_obj = {
      }
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class RemoveMultipleTypeBook(WebappHelper):
  def check_ok_to_remove(self, type_book_id):

    type_book_row = UCFMDLTypeBook.getInstance(type_book_id)
    if type_book_row is None:
      return None, self.getMsg('NOT_FOUND_TYPE_BOOK')

    # check ok to delete
    if not type_book_row.type_parent_id:
      # had category use type_book
      query_category = UCFMDLTypeBook.query()
      query_category = query_category.filter(UCFMDLTypeBook.type_parent_id == str(type_book_id))
      query_category = query_category.filter(UCFMDLTypeBook.del_flag == False)
      if query_category.count() > 0:
        return None, self.getMsg('HAD_CATEGORY_USE_TYPE_BOOK')

      # had book use type_book
      query_book = UCFMDLBook.query()
      query_book = query_book.filter(UCFMDLBook.type_book_id == type_book_id)
      query_book = query_book.filter(UCFMDLBook.del_flag == False)
      if query_book.count() > 0:
        return None, self.getMsg('HAD_BOOK_USE_TYPE_BOOK')

    else:
      # had book use category_book
      query_book = UCFMDLBook.query()
      query_book = query_book.filter(UCFMDLBook.category_book_id == type_book_id)
      query_book = query_book.filter(UCFMDLBook.del_flag == False)
      if query_book.count() > 0:
        return None, self.getMsg('HAD_BOOK_USE_CATEGORY_BOOK')

      UCFMDLTypeBook.clearAllCategoryInstanceCache(type_book_row.type_parent_id)

    return type_book_row, ''

  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()
      # check is workflow admin
      if not self.is_workflow_admin:
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      list_type_book_id = json.JSONDecoder().decode(request_json.get('list_type_book_id', ''))

      rows_update = []

      for type_book_id in list_type_book_id:
        row_update, msg = self.check_ok_to_remove(type_book_id)

        if row_update is None:
          return self.send_error_response({
            'error_message': msg,
            'error_code': 400
          })
        else:
          rows_update.append(row_update)

      for row_update in rows_update:
        row_update.del_flag = True
        row_update.put()

      UCFMDLTypeBook.clearAllTypeInstanceCache()
      UCFMDLTypeBook.clearAllCategoryInstanceCache()

      ret_obj = {
      }
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class GetAllTypeBook(WebappHelper):
  def processOfRequest(self):
    try:
      ret_obj = UCFMDLTypeBook.getAll()
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class GetAllJustTypeBook(WebappHelper):
  def processOfRequest(self):
    try:
      request_json = json.JSONDecoder().decode(request.get_data().decode())

      is_admin = sateraito_func.strToBool(request_json.get('is_admin', 'false'))

      if is_admin:
        # check login
        if not self.checkLogin().get('status'):
          return self.responseError403()
        # check is workflow admin
        if not self.is_workflow_admin:
          return self.responseError403()

      ret_obj = UCFMDLTypeBook.getAllType(del_flag=False, is_admin=is_admin, timezone=self._timezone)
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class GetAllCategoriesByTypeBook(WebappHelper):
  def processOfRequest(self):
    try:
      request_json = json.JSONDecoder().decode(request.get_data().decode())

      is_admin = sateraito_func.strToBool(request_json.get('is_admin', 'false'))
      type_book_id = request_json.get('type_book_id', "")

      if is_admin:
        # check login
        if not self.checkLogin().get('status'):
          return self.responseError403()
        # check is workflow admin
        if not self.is_workflow_admin:
          return self.responseError403()

      ret_obj = UCFMDLTypeBook.getCategories(type_book_id=type_book_id, del_flag=False, is_admin=is_admin, timezone=self._timezone)
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class GetTypeAndCategoryBook(WebappHelper):
  def processOfRequest(self):
    try:
      request_json = json.JSONDecoder().decode(request.get_data().decode())

      is_admin = sateraito_func.strToBool(request_json.get('is_admin', 'false'))
      without_category = sateraito_func.strToBool(request_json.get('without_category', 'false'))

      if is_admin:
        # check login
        if not self.checkLogin().get('status'):
          return self.responseError403()
        # check is workflow admin
        if not self.is_workflow_admin:
          return self.responseError403()

      ret_obj = UCFMDLTypeBook.getAllType(without_category=without_category, del_flag=False, is_admin=is_admin, timezone=self._timezone)
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })


############################################################
# REQUEST FOR BOOK
############################################################

class CreateBook(WebappHelper):
  def checkParam(self):
    request_json = json.JSONDecoder().decode(request.get_data().decode())

    # get params
    status = request_json.get('status', '').strip()
    share_for = request_json.get('share_for')
    type_book = request_json.get('type_book')
    category_book = request_json.get('category_book')
    title = request_json.get('title', '').strip()
    book_cover = request_json.get('book_cover', '').strip()
    images = request_json.get('images', '').strip()
    summary = request_json.get('summary', '').strip()
    characters = request_json.get('characters', '').strip()   # array[{name, age, gender, description, is_protagonist}, ...]
    chapters = request_json.get('chapters', '').strip()   # array[{title, idea}, ...]

    if status == '':
      return False, {'field': 'status'}, 'required'
    elif status not in [sateraito_func.KEY_STATUS_BOOK_PUBLIC, sateraito_func.KEY_STATUS_BOOK_SHARE, sateraito_func.KEY_STATUS_BOOK_PRIVATE]:
      return False, {'field': 'share_for'}, 'not_define'
    elif status == sateraito_func.KEY_STATUS_BOOK_SHARE:
      if share_for == '':
        return False, {'field': 'share_for'}, 'required'

    if not type_book:
      return False, {'field': 'type_book'}, 'required'
    else:
      type_book_dict = UCFMDLTypeBook.getDict(type_book)
      if not type_book_dict:
        return False, {'field': 'type_book'}, 'undefined'
      if type_book_dict['type_parent_id']:
        return False, {'field': 'type_book'}, 'not_type_book'

    if not category_book:
      return False, {'field': 'category_book'}, 'required'
    else:
      category_book_dict = UCFMDLTypeBook.getDict(category_book)
      if not category_book_dict:
        return False, {'field': 'category_book'}, 'undefined'
      if not category_book_dict['type_parent_id']:
        return False, {'field': 'type_book'}, 'not_category_book'

    if title == '':
      return False, {'field': 'title'}, 'required'
    if summary == '':
      return False, {'field': 'summary'}, 'required'
    if book_cover == '':
      return False, {'field': 'book_cover'}, 'required'
    if images == '':
      return False, {'field': 'images'}, 'required'
    if characters == '':
      return False, {'field': 'characters'}, 'required'
    if chapters == '':
      return False, {'field': 'chapters'}, 'required'

    book_cover_dict = json.JSONDecoder().decode(book_cover)
    if not book_cover_dict.get('url') or book_cover_dict.get('url').strip() == '':
      return False, {'field': 'book_cover.url'}, 'required'

    images_dict = json.JSONDecoder().decode(images)
    for index, image in enumerate(images_dict):
      # validate url image
      if not image.get('url') or image.get('url').strip() == '':
        return False, {'field': 'images.%s.url' % str(index)}, 'required'

    characters_dict = json.JSONDecoder().decode(characters)
    for index, character in enumerate(characters_dict):
      # validate name character
      if not character.get('name') or character.get('name').strip() == '':
        return False, {'field': 'characters.%s.name' % str(index)}, 'required'
      # validate age character
      if not character.get('age'):
        return False, {'field': 'characters.%s.age' % str(index)}, 'required'
      # validate gender character
      if not character.get('gender'):
        return False, {'field': 'characters.%s.gender' % str(index)}, 'required'
      # validate description character
      if not character.get('description') or character.get('description').strip() == '':
        return False, {'field': 'characters.%s.description' % str(index)}, 'required'
      # validate is_protagonist character
      if character.get('is_protagonist') is None:
        return False, {'field': 'characters.%s.is_protagonist' % str(index)}, 'required'

    chapters_dict = json.JSONDecoder().decode(chapters)
    for index, chapter in enumerate(chapters_dict):
      # validate title character
      if not chapter.get('title') or chapter.get('title').strip() == '':
        return False, {'field': 'chapters.%s.title' % str(index)}, 'required'
      # validate idea character
      if not chapter.get('idea') or chapter.get('idea').strip() == '':
        return False, {'field': 'chapters.%s.idea' % str(index)}, 'required'

    share_for = json.JSONDecoder().decode(share_for)

    param = {
      'status': status,
      'share_for': share_for,
      'type_book': type_book,
      'category_book': category_book,
      'title': title,
      'book_cover': book_cover,
      'images': images,
      'summary': summary,
      'characters': characters,
      'chapters': chapters,
    }
    return True, param, ''

  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      param_valid, param, error_code = self.checkParam()

      if not param_valid:
        return self.send_error_response({
          'error_message': self.getMsg('PARAMS_INVALIDATE'),
          'error_code': error_code,
          'param': param,
        })

      type_book_dict = UCFMDLTypeBook.getDict(param['type_book'])
      category_dict = UCFMDLTypeBook.getDict(param['category_book'])

      id_new_book = BookUtils.getKey(self)
      new_row = UCFMDLBook(id=id_new_book)
      new_row.creator_id = self.viewer_email

      new_row.status = param['status']
      new_row.share_for = param['share_for']

      new_row.type_book_id = param['type_book']
      new_row.type_book_name = type_book_dict['name']
      new_row.category_book_id = param['category_book']
      new_row.category_book_name = category_dict['name']

      new_row.title = param['title']
      new_row.book_cover = param['book_cover']
      new_row.images = param['images']
      new_row.summary = param['summary']
      # new_row.characters = param['characters']
      new_row.chapters = param['chapters']

      characters_convert = []
      characters = json.JSONDecoder().decode(param['characters'])
      for character in characters:
        name = character['name']
        age = character['age']
        gender = character['gender']
        is_protagonist = character['is_protagonist']
        description = character['description']

        # input_text_small = '"{0}"\nThay đổi đại từ xưng hô trên thành tôi'.format(description)
        # is_success, error_message, description_if_is_me, message_history = chatgpt_func_v2.callChatGPT(self, api_key, model, input_text_small, [], False)
        characters_convert.append({
          'name': name,
          "is_protagonist": is_protagonist,
          'age': age,
          'gender': gender,
          'description': description,
          # 'description_if_is_me': description_if_is_me,
        })

      new_row.characters = json.JSONEncoder().encode(characters_convert)

      new_row.put()

      BookUtils.addToTextSearchIndex(new_row)
      BookUtils.addTaskAfterBookCreate(id_new_book)

      ret_obj = {
        'creator_id': new_row.creator_id,
        'del_flag': new_row.del_flag,
        'total_join': new_row.total_join,
        'popular': new_row.popular,
        'rate_star': new_row.rate_star,
        'comment': new_row.total_comment,
        'status': new_row.status,
        'share_for': new_row.share_for,
        'type_book_id': new_row.type_book_id,
        'type_book_name': new_row.type_book_name,
        'category_book_id': new_row.category_book_id,
        'category_book_name': new_row.category_book_name,
        'title': new_row.title,
        'book_cover': new_row.book_cover,
        'images': new_row.images,
        'summary': new_row.summary,
        'characters': new_row.characters,
        'chapters': new_row.chapters,

        'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(new_row.created_date, self._timezone)),
        'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(new_row.updated_date, self._timezone)),
      }

      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class EditBook(WebappHelper):
  def checkParam(self):
    request_json = json.JSONDecoder().decode(request.get_data().decode())

    # get params
    book_id = request_json.get('book_id').strip()
    status = request_json.get('status', '').strip()
    share_for = request_json.get('share_for')
    type_book = request_json.get('type_book')
    category_book = request_json.get('category_book')
    title = request_json.get('title', '').strip()
    book_cover = request_json.get('book_cover', '').strip()
    images = request_json.get('images', '').strip()
    summary = request_json.get('summary', '').strip()
    characters = request_json.get('characters', '').strip()   # array[{name, age, gender, description, is_protagonist}, ...]
    chapters = request_json.get('chapters', '').strip()   # array[{title, idea}, ...]

    if status == '':
      return False, {'field': 'status'}, 'required'
    elif status not in [sateraito_func.KEY_STATUS_BOOK_PUBLIC, sateraito_func.KEY_STATUS_BOOK_SHARE, sateraito_func.KEY_STATUS_BOOK_PRIVATE]:
      return False, {'field': 'share_for'}, 'not_define'
    elif status == sateraito_func.KEY_STATUS_BOOK_SHARE:
      if share_for == '':
        return False, {'field': 'share_for'}, 'required'

    if book_id == '':
      return False, {'field': 'book_id'}, 'required'
    else:
      book_dict = UCFMDLBook.getDict(book_id)
      if not book_dict:
        return False, {'field': 'book'}, 'undefined'
      if book_dict['del_flag']:
        return False, {'field': 'book'}, 'deleted'

    if not type_book:
      return False, {'field': 'type_book'}, 'required'
    else:
      type_book_dict = UCFMDLTypeBook.getDict(type_book)
      if not type_book_dict:
        return False, {'field': 'type_book'}, 'undefined'
      if type_book_dict['type_parent_id']:
        return False, {'field': 'type_book'}, 'not_type_book'

    if not category_book:
      return False, {'field': 'category_book'}, 'required'
    else:
      category_book_dict = UCFMDLTypeBook.getDict(category_book)
      if not category_book_dict:
        return False, {'field': 'category_book'}, 'undefined'
      if not category_book_dict['type_parent_id']:
        return False, {'field': 'type_book'}, 'not_category_book'

    if title == '':
      return False, {'field': 'title'}, 'required'
    if summary == '':
      return False, {'field': 'summary'}, 'required'
    if book_cover == '':
      return False, {'field': 'book_cover'}, 'required'
    if images == '':
      return False, {'field': 'images'}, 'required'
    if characters == '':
      return False, {'field': 'characters'}, 'required'
    if chapters == '':
      return False, {'field': 'chapters'}, 'required'

    book_cover_dict = json.JSONDecoder().decode(book_cover)
    if not book_cover_dict.get('url') or book_cover_dict.get('url').strip() == '':
      return False, {'field': 'book_cover.url'}, 'required'

    images_dict = json.JSONDecoder().decode(images)
    for index, image in enumerate(images_dict):
      # validate url image
      if not image.get('url') or image.get('url').strip() == '':
        return False, {'field': 'images.%s.url' % str(index)}, 'required'

    characters_dict = json.JSONDecoder().decode(characters)
    for index, character in enumerate(characters_dict):
      # validate name character
      if not character.get('name') or character.get('name').strip() == '':
        return False, {'field': 'characters.%s.name' % str(index)}, 'required'
      # validate age character
      if not character.get('age'):
        return False, {'field': 'characters.%s.age' % str(index)}, 'required'
      # validate gender character
      if not character.get('gender'):
        return False, {'field': 'characters.%s.gender' % str(index)}, 'required'
      # validate description character
      if not character.get('description') or character.get('description').strip() == '':
        return False, {'field': 'characters.%s.description' % str(index)}, 'required'
      # validate is_protagonist character
      if character.get('is_protagonist') is None:
        return False, {'field': 'characters.%s.is_protagonist' % str(index)}, 'required'

    chapters_dict = json.JSONDecoder().decode(chapters)
    for index, chapter in enumerate(chapters_dict):
      # validate title character
      if not chapter.get('title') or chapter.get('title').strip() == '':
        return False, {'field': 'chapters.%s.title' % str(index)}, 'required'
      # validate idea character
      if not chapter.get('idea') or chapter.get('idea').strip() == '':
        return False, {'field': 'chapters.%s.idea' % str(index)}, 'required'

    share_for = json.JSONDecoder().decode(share_for)

    param = {
      'book_id': book_id,
      'status': status,
      'share_for': share_for,
      'type_book': type_book,
      'category_book': category_book,
      'title': title,
      'book_cover': book_cover,
      'images': images,
      'summary': summary,
      'characters': characters,
      'chapters': chapters,
    }
    return True, param, ''

  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      param_valid, param, error_code = self.checkParam()

      if not param_valid:
        return self.send_error_response({
          'error_message': self.getMsg('PARAMS_INVALIDATE'),
          'error_code': error_code,
          'param': param,
        })

      book_row = UCFMDLBook.getInstance(param['book_id'])
      if book_row is None or book_row.del_flag:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })
      if book_row.creator_id != self.viewer_email:
        return self.send_error_response({
          'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION'),
          'error_code': 403
        })

      if book_row.status != param['status']:
        book_row.status = param['status']

      if book_row.share_for != param['share_for']:
        book_row.share_for = param['share_for']

      if book_row.type_book_id != param['type_book']:
        type_book_dict = UCFMDLTypeBook.getDict(param['type_book'])
        book_row.type_book_id = param['type_book']
        book_row.type_book_name = type_book_dict['name']

      if book_row.category_book_id != param['category_book']:
        category_dict = UCFMDLTypeBook.getDict(param['category_book'])
        book_row.category_book_id = param['category_book']
        book_row.category_book_name = category_dict['name']

      if book_row.title != param['title']:
        book_row.title = param['title']
      if book_row.book_cover != param['book_cover']:
        book_row.book_cover = param['book_cover']
      if book_row.images != param['images']:
        book_row.images = param['images']
      if book_row.summary != param['summary']:
        book_row.summary = param['summary']
      if book_row.characters != param['characters']:
        characters_convert = []

        characters = json.JSONDecoder().decode(param['characters'])
        for character in characters:
          name = character['name']
          age = character['age']
          gender = character['gender']
          is_protagonist = character['is_protagonist']
          description = character['description']

          # input_text_small = '"{0}"\nThay đổi đại từ xưng hô trên thành tôi'.format(description)
          # is_success, error_message, description_if_is_me, message_history = chatgpt_func_v2.callChatGPT(self, api_key, model, input_text_small, [], False)

          characters_convert.append({
            'name': name,
            "is_protagonist": is_protagonist,
            'age': age,
            'gender': gender,
            'description': description,
            # 'description_if_is_me': description_if_is_me,
          })

        book_row.characters = json.JSONEncoder().encode(characters_convert)
      if book_row.chapters != param['chapters']:
        book_row.chapters = param['chapters']

      book_row.put()

      # rebuild text search index
      BookUtils.rebuildTextSearchIndex(book_row)
      BookUtils.addTaskAfterBookUpdate(param['book_id'])

      ret_obj = {
        'creator_id': book_row.creator_id,
        'del_flag': book_row.del_flag,
        'total_join': book_row.total_join,
        'popular': book_row.popular,
        'rate_star': book_row.rate_star,
        'total_comment': book_row.total_comment,
        'status': book_row.status,
        'share_for': book_row.share_for,
        'type_book_id': book_row.type_book_id,
        'type_book_name': book_row.type_book_name,
        'category_book_id': book_row.category_book_id,
        'category_book_name': book_row.category_book_name,
        'title': book_row.title,
        'book_cover': book_row.book_cover,
        'images': book_row.images,
        'summary': book_row.summary,
        'characters': book_row.characters,
        'chapters': book_row.chapters,

        'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(book_row.created_date, self._timezone)),
        'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(book_row.updated_date, self._timezone)),
      }

      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class DeleteBook(WebappHelper):
  def check_param(self):
    request_json = json.JSONDecoder().decode(request.get_data().decode())

    # get params
    book_id = request_json.get('book_id', '')
    is_admin = sateraito_func.strToBool(request_json.get('is_admin', 'false'))

    if book_id == '':
      return False, {'field': 'book_id'}, 'required'
    else:
      book_dict = UCFMDLBook.getDict(book_id)
      if not book_dict:
        return False, {'field': 'book'}, 'undefined'
      if book_dict['del_flag']:
        return False, {'field': 'book'}, 'deleted'

      # check permission
      if is_admin:
        if not self.is_workflow_admin:
          return False, {'field': 'auth'}, 'not_is_admin'
      else:
        if book_dict['creator_id'] != self.viewer_email:
          return False, {'field': 'book'}, 'not_the_creator_of_this_book'

    param = {
      'book_id': book_id,
    }
    return True, param, ''

  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      param_valid, param, error_code = self.check_param()

      if not param_valid:
        return self.send_error_response({
          'error_message': self.getMsg('PARAMS_INVALIDATE'),
          'error_code': error_code,
          'param': param,
        })

      book_row = UCFMDLBook.getInstance(param['book_id'])
      book_row.del_flag = True
      book_row.put()

      # Add task run update del flag in other model
      BookUtils.addTaskAfterBookDelete(param['book_id'])

      # remove text search index
      BookUtils.rebuildTextSearchIndex(book_row)

      ret_obj = {
        'creator_id': book_row.creator_id,
        'del_flag': book_row.del_flag,
        'total_join': book_row.total_join,
        'popular': book_row.popular,
        'rate_star': book_row.rate_star,
        'total_comment': book_row.total_comment,
        'status': book_row.status,
        'share_for': book_row.share_for,
        'type_book_id': book_row.type_book_id,
        'type_book_name': book_row.type_book_name,
        'category_book_id': book_row.category_book_id,
        'category_book_name': book_row.category_book_name,
        'title': book_row.title,
        'book_cover': book_row.book_cover,
        'images': book_row.images,
        'summary': book_row.summary,
        'characters': book_row.characters,
        'chapters': book_row.chapters,

        'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(book_row.created_date, self._timezone)),
        'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(book_row.updated_date, self._timezone)),
      }

      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class GetBookById(WebappHelper):
  def processOfRequest(self, book_id):
    try:
      # check login
      user_logged = self.checkLogin().get('status')
      viewer_email = ''
      if user_logged:
        viewer_email = self.viewer_email

      request_json = json.JSONDecoder().decode(request.get_data().decode())
      # get params
      story_history_id = request_json.get('story_history_id', '')
      is_for_manager = sateraito_func.strToBool(request_json.get('for_manager', 'false'))

      book_dict = UCFMDLBook.getDict(book_id)
      if book_dict is None or book_dict['del_flag']:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })

      if not BookUtils.accessBookDict(book_dict, viewer_email=viewer_email):
        return self.send_error_response({
          'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION'),
          'error_code': '',
          'param': '',
        })

      if is_for_manager and book_dict['creator_id'] != self.viewer_email:
        return self.send_error_response({
          'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION'),
          'error_code': 403
        })

      share_for = []
      if book_dict['status'] == sateraito_func.KEY_STATUS_BOOK_SHARE:
        for id_user_share in book_dict['share_for']:
          infouser_share_dict = UCFMDLUserInfo.getDict(id_user_share)
          share_for.append({
            'id': infouser_share_dict['id'],
            'user_entry_id': infouser_share_dict['user_entry_id'],
            'fullname': infouser_share_dict['fullname'],
            'email': infouser_share_dict['email'],
            'avatar_url': infouser_share_dict['avatar_url'],
          })

      creator_dict = UCFMDLUserInfo.getDict(book_dict['creator_id'])
      creator_skill = []
      if creator_dict['skill']:
        creator_skill = json.JSONDecoder().decode(creator_dict['skill'])

      characters = json.JSONDecoder().decode(book_dict['characters'])
      chapters = json.JSONDecoder().decode(book_dict['chapters'])

      images = json.JSONDecoder().decode(book_dict['images'])
      book_cover = json.JSONDecoder().decode(book_dict['book_cover'])

      my_story = None
      story_history = None
      my_feedback_dict = None
      my_stories_history = []
      shared_users_book = []
      if user_logged:
        shared_users_book = UCFMDLUserShareStories.getListUsersShared(book_id, viewer_email, type_share=sateraito_func.KEY_TYPE_BOOK_SHARE)

        if not is_for_manager:
          my_story = UserStoriesUtils.getByBookId(book_id, viewer_email, timezone=self._timezone)
          my_stories_history = UserStoriesUtils.getHistoryByBookId(book_id, viewer_email, to_dict=True, timezone=self._timezone)

          if my_story is not None:
            my_story['shared_users'] = UCFMDLUserShareStories.getListUsersShared(book_id, viewer_email, user_story_id=my_story['id'], type_share=sateraito_func.KEY_TYPE_STORY_SHARE)
            for index, user_chaper in enumerate(my_story['user_chapters']):
              shared_users = UCFMDLUserShareStories.getListUsersShared(book_id, viewer_email, user_story_id=my_story['id'], user_chapter_id=user_chaper['id'], type_share=sateraito_func.KEY_TYPE_CHAPTER_SHARE)
              my_story['user_chapters'][index]['shared_users'] = shared_users

          my_feedback_row = UCFMDLFeedbackBookUsers.getByBookIdUserId(book_id, viewer_email, sateraito_inc.KEY_FEEDBACK_TYPE_BOOK)
          if my_feedback_row:
            my_feedback_dict = my_feedback_row.to_dict()
            my_feedback_dict['id'] = my_feedback_row.key.id()
            my_feedback_dict['created_date'] = UcfUtil.getLocalTime(my_feedback_dict['created_date'], self._timezone).strftime('%Y/%m/%d %H:%M')
            my_feedback_dict['updated_date'] = UcfUtil.getLocalTime(my_feedback_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M')

      if story_history_id:
        story_history = UserStoriesUtils.getById(story_history_id, timezone=self._timezone)
        if story_history['creator_id'] != self.viewer_email:
          query = UCFMDLUserShareStories.query()
          query = query.filter(UCFMDLUserShareStories.type_share == sateraito_func.KEY_TYPE_STORY_SHARE)
          query = query.filter(UCFMDLUserShareStories.user_story_id == story_history_id)
          query = query.filter(UCFMDLUserShareStories.user_id_shared == self.viewer_email)
          key = query.get(keys_only=True)
          if not key:
            return self.send_error_response({
              'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION'),
              'error_code': '',
              'param': '',
            })

        story_history['shared_users'] = UCFMDLUserShareStories.getListUsersShared(book_id, viewer_email, type_share=sateraito_func.KEY_TYPE_STORY_SHARE, user_story_id=story_history_id)
        for index, user_chaper in enumerate(story_history['user_chapters']):
          shared_users = UCFMDLUserShareStories.getListUsersShared(book_id, viewer_email, user_story_id=story_history_id, user_chapter_id=user_chaper['id'], type_share=sateraito_func.KEY_TYPE_CHAPTER_SHARE)
          story_history['user_chapters'][index]['shared_users'] = shared_users

      if book_dict['feedback_summary']:
        feedback_summary = json.JSONDecoder().decode(book_dict['feedback_summary'])
      else:
        feedback_summary = {
          "total": 0,
          "level": {}
        }

      ret_obj = {
          'id': book_dict['id'],

          'book_cover': book_cover,
          'images': images,

          'status': book_dict['status'],
          'share_for': share_for,

          'title': book_dict['title'],
          'summary': book_dict['summary'],

          'total_join': book_dict['total_join'],
          'rate_star': book_dict['rate_star'],
          'total_comment': book_dict['total_comment'],
          'feedback_summary': feedback_summary,

          'characters': characters,
          'chapter_limit': len(chapters),
          'chapters': chapters,

          'created_date': UcfUtil.getLocalTime(book_dict['created_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),
          'updated_date': UcfUtil.getLocalTime(book_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),

          'my_story': my_story,
          'story_history': story_history,
          'my_stories_history': my_stories_history,
          'my_feedback': my_feedback_dict,

          'shared_users': shared_users_book,

          'category': {
            'id': book_dict['category_book_id'],
            'name': book_dict['category_book_name'],
          },
          'type_book': {
            'id': book_dict['type_book_id'],
            'name': book_dict['type_book_name'],
          },
          'creator': {
            'id': creator_dict['id'],
            'skill': creator_skill,
            'fullname': creator_dict['fullname'],
            'email': creator_dict['email'],
            'avatar_url': creator_dict['avatar_url'],
            'nickname': creator_dict['nickname'],
            'gender': creator_dict['gender'],
            'date_of_birth': creator_dict['date_of_birth'],
            'description': creator_dict['description'],
            'lives_in': creator_dict['lives_in'],
            'come_from': creator_dict['come_from'],
            'works_at': creator_dict['works_at'],
            'website_url': creator_dict['website_url'],
            'twitter_url': creator_dict['twitter_url'],
            'facebook_url': creator_dict['facebook_url'],
            'instagram_url': creator_dict['instagram_url'],
            'linkedin_url': creator_dict['linkedin_url'],
            'family_name': creator_dict['family_name'],
            'given_name': creator_dict['given_name'],
            'language': creator_dict['language'],

            'followers': creator_dict['followers'],
            'following': creator_dict['following'],
          }
        }
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class SearchBook(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      user_logged = self.checkLogin().get('status')

      request_json = json.JSONDecoder().decode(request.get_data().decode())
      # get params
      keyword = request_json.get('keyword', '')
      title_book = request_json.get('title_book', '')
      type_search = request_json.get('type_search', '')
      type_book_id = request_json.get('type_book', '')
      category_id = request_json.get('category', '')
      sort_by = request_json.get('sort_by', '')
      limit = int(request_json.get('limit', '500'))

      viewer_email = ''
      if user_logged:
        viewer_email = self.viewer_email

      result_list, count = BookUtils.searchDocsByFullText(self, viewer_email, keyword, limit=limit,
                                                          title_book=title_book,
                                                          type_search=type_search, type_book_id=type_book_id,
                                                          category_id=category_id, sort_by=sort_by)

      data_books = []
      for dict_item in result_list:
        book_dict = UCFMDLBook.getDict(dict_item['id'])

        # Check book dict empty or deleted
        if book_dict is None:
          # removeFromIndex book entry None
          BookUtils.removeFromIndexById(dict_item['id'])
          continue

        if not BookUtils.accessBookDict(book_dict, viewer_email=viewer_email):
          continue

        creator_skill = []
        creator_dict = UCFMDLUserInfo.getDict(book_dict['creator_id'])
        if creator_dict['skill']:
          creator_skill = json.JSONDecoder().decode(creator_dict['skill'])

        characters = json.JSONDecoder().decode(book_dict['characters'])
        chapters = json.JSONDecoder().decode(book_dict['chapters'])

        images = json.JSONDecoder().decode(book_dict['images'])
        book_cover = json.JSONDecoder().decode(book_dict['book_cover'])

        data_books.append({
          'id': book_dict['id'],
          'status': book_dict['status'],

          'book_cover': book_cover,
          'images': images,

          'title': book_dict['title'],
          'summary': book_dict['summary'],

          'total_join': book_dict['total_join'],
          'rate_star': book_dict['rate_star'],
          'total_comment': book_dict['total_comment'],

          'characters': characters,
          'chapter_limit': len(chapters),
          'chapters': chapters,

          'created_date': UcfUtil.getLocalTime(book_dict['created_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),
          'updated_date': UcfUtil.getLocalTime(book_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),

          'my_story': None,
          'my_stories_history': [],

          'category': {
            'id': book_dict['category_book_id'],
            'name': book_dict['category_book_name'],
          },
          'type_book': {
            'id': book_dict['type_book_id'],
            'name': book_dict['type_book_name'],
          },
          'creator': {
            'id': creator_dict['id'],
            'skill': creator_skill,
            'email': creator_dict['email'],
            'avatar_url': creator_dict['avatar_url'],
            'nickname': creator_dict['nickname'],
            'gender': creator_dict['gender'],
            'date_of_birth': creator_dict['date_of_birth'],
            'description': creator_dict['description'],
            'lives_in': creator_dict['lives_in'],
            'come_from': creator_dict['come_from'],
            'works_at': creator_dict['works_at'],
            'website_url': creator_dict['website_url'],
            'twitter_url': creator_dict['twitter_url'],
            'facebook_url': creator_dict['facebook_url'],
            'instagram_url': creator_dict['instagram_url'],
            'linkedin_url': creator_dict['linkedin_url'],
            'fullname': creator_dict['fullname'],
            'family_name': creator_dict['family_name'],
            'given_name': creator_dict['given_name'],
            'language': creator_dict['language'],

            'followers': creator_dict['followers'],
            'following': creator_dict['following'],
          }
        })

      ret_obj = data_books
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class GetBookByFavorite(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      query = UCFMDLFavoritesBookUsers.query()
      query = query.filter(UCFMDLFavoritesBookUsers.user_id == self.viewer_email)
      query = query.order(-UCFMDLFavoritesBookUsers.created_date)
      results = query.fetch()

      data = []
      for row in results:
        book_dict = UCFMDLBook.getDict(row.book_id)

        if book_dict is None or book_dict['del_flag']:
          continue

        if not BookUtils.accessBookDict(book_dict, viewer_email=self.viewer_email):
          continue

        creator_dict = UCFMDLUserInfo.getDict(book_dict['creator_id'])

        creator_skill = []
        if creator_dict['skill']:
          creator_skill = json.JSONDecoder().decode(creator_dict['skill'])

        characters = json.JSONDecoder().decode(book_dict['characters'])
        chapters = json.JSONDecoder().decode(book_dict['chapters'])

        images = json.JSONDecoder().decode(book_dict['images'])
        book_cover = json.JSONDecoder().decode(book_dict['book_cover'])

        data.append({
          'id': book_dict['id'],
          'status': book_dict['status'],

          'book_cover': book_cover,
          'images': images,

          'title': book_dict['title'],
          'summary': book_dict['summary'],

          'total_join': book_dict['total_join'],
          'rate_star': book_dict['rate_star'],
          'total_comment': book_dict['total_comment'],

          'characters': characters,
          'chapter_limit': len(chapters),
          'chapters': chapters,

          'created_date': UcfUtil.getLocalTime(book_dict['created_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),
          'updated_date': UcfUtil.getLocalTime(book_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),

          'my_story': None,
          'my_stories_history': [],

          'category': {
            'id': book_dict['category_book_id'],
            'name': book_dict['category_book_name'],
          },
          'type_book': {
            'id': book_dict['type_book_id'],
            'name': book_dict['type_book_name'],
          },
          'creator': {
            'id': creator_dict['id'],
            'skill': creator_skill,
            'email': creator_dict['email'],
            'avatar_url': creator_dict['avatar_url'],
            'nickname': creator_dict['nickname'],
            'gender': creator_dict['gender'],
            'date_of_birth': creator_dict['date_of_birth'],
            'description': creator_dict['description'],
            'lives_in': creator_dict['lives_in'],
            'come_from': creator_dict['come_from'],
            'works_at': creator_dict['works_at'],
            'website_url': creator_dict['website_url'],
            'twitter_url': creator_dict['twitter_url'],
            'facebook_url': creator_dict['facebook_url'],
            'instagram_url': creator_dict['instagram_url'],
            'linkedin_url': creator_dict['linkedin_url'],
            'fullname': creator_dict['fullname'],
            'family_name': creator_dict['family_name'],
            'given_name': creator_dict['given_name'],
            'language': creator_dict['language'],

            'followers': creator_dict['followers'],
            'following': creator_dict['following'],
          }
        })

      ret_obj = data
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class GetBookByRecentlyRead(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      query = UCFMDLStoriesUsersJoined.query()
      query = query.filter(UCFMDLStoriesUsersJoined.user_id == self.viewer_email)
      query = query.filter(UCFMDLStoriesUsersJoined.del_flag == False)
      query = query.order(-UCFMDLStoriesUsersJoined.created_date)
      results = query.fetch()

      data = []
      for row in results:
        book_dict = UCFMDLBook.getDict(row.book_id)
        if book_dict is None or book_dict['del_flag']:
          continue

        if not BookUtils.accessBookDict(book_dict, viewer_email=self.viewer_email):
          continue

        creator_dict = UCFMDLUserInfo.getDict(book_dict['creator_id'])

        creator_skill = []
        if creator_dict['skill']:
          creator_skill = json.JSONDecoder().decode(creator_dict['skill'])

        characters = json.JSONDecoder().decode(book_dict['characters'])
        chapters = json.JSONDecoder().decode(book_dict['chapters'])

        images = json.JSONDecoder().decode(book_dict['images'])
        book_cover = json.JSONDecoder().decode(book_dict['book_cover'])

        data.append({
          'id': book_dict['id'],
          'status': book_dict['status'],

          'book_cover': book_cover,
          'images': images,

          'title': book_dict['title'],
          'summary': book_dict['summary'],

          'total_join': book_dict['total_join'],
          'rate_star': book_dict['rate_star'],
          'total_comment': book_dict['total_comment'],

          'characters': characters,
          'chapter_limit': len(chapters),
          'chapters': chapters,

          'created_date': UcfUtil.getLocalTime(book_dict['created_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),
          'updated_date': UcfUtil.getLocalTime(book_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),

          'my_story': None,
          'my_stories_history': [],

          'category': {
            'id': book_dict['category_book_id'],
            'name': book_dict['category_book_name'],
          },
          'type_book': {
            'id': book_dict['type_book_id'],
            'name': book_dict['type_book_name'],
          },
          'creator': {
            'id': creator_dict['id'],
            'skill': creator_skill,
            'email': creator_dict['email'],
            'avatar_url': creator_dict['avatar_url'],
            'nickname': creator_dict['nickname'],
            'gender': creator_dict['gender'],
            'date_of_birth': creator_dict['date_of_birth'],
            'description': creator_dict['description'],
            'lives_in': creator_dict['lives_in'],
            'come_from': creator_dict['come_from'],
            'works_at': creator_dict['works_at'],
            'website_url': creator_dict['website_url'],
            'twitter_url': creator_dict['twitter_url'],
            'facebook_url': creator_dict['facebook_url'],
            'instagram_url': creator_dict['instagram_url'],
            'linkedin_url': creator_dict['linkedin_url'],
            'fullname': creator_dict['fullname'],
            'family_name': creator_dict['family_name'],
            'given_name': creator_dict['given_name'],
            'language': creator_dict['language'],

            'followers': creator_dict['followers'],
            'following': creator_dict['following'],
          }
        })

      ret_obj = data
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class GetMyBookCreated(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())
      # get params
      search_keyword = request_json.get('search_keyword', '')
      type_search = request_json.get('type_search', '')
      type_book_id = request_json.get('type_book', '')
      category_id = request_json.get('category', '')
      limit = int(request_json.get('limit', '500'))

      result_list, count = BookUtils.searchDocsByFullText(self, self.viewer_email, search_keyword, limit=limit,
                                                          type_search=type_search, type_book_id=type_book_id,
                                                          category_id=category_id, just_my_book=True)

      data_books = []
      for dict_item in result_list:
        book_dict = UCFMDLBook.getDict(dict_item['id'])

        # Check book dict empty or deleted
        if book_dict is None:
          # removeFromIndex book entry None
          BookUtils.removeFromIndexById(dict_item['id'])
          continue

        if not BookUtils.accessBookDict(book_dict, viewer_email=self.viewer_email):
          continue

        creator_skill = []
        creator_dict = UCFMDLUserInfo.getDict(book_dict['creator_id'])
        if creator_dict['skill']:
          creator_skill = json.JSONDecoder().decode(creator_dict['skill'])

        characters = json.JSONDecoder().decode(book_dict['characters'])
        chapters = json.JSONDecoder().decode(book_dict['chapters'])

        images = json.JSONDecoder().decode(book_dict['images'])
        book_cover = json.JSONDecoder().decode(book_dict['book_cover'])

        data_books.append({
          'id': book_dict['id'],
          'status': book_dict['status'],

          'book_cover': book_cover,
          'images': images,

          'title': book_dict['title'],
          'summary': book_dict['summary'],

          'total_join': book_dict['total_join'],
          'rate_star': book_dict['rate_star'],
          'total_comment': book_dict['total_comment'],

          'characters': characters,
          'chapter_limit': len(chapters),
          'chapters': chapters,

          'created_date': UcfUtil.getLocalTime(book_dict['created_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),
          'updated_date': UcfUtil.getLocalTime(book_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),

          'my_story': None,
          'my_stories_history': [],

          'category': {
            'id': book_dict['category_book_id'],
            'name': book_dict['category_book_name'],
          },
          'type_book': {
            'id': book_dict['type_book_id'],
            'name': book_dict['type_book_name'],
          },
          'creator': {
            'id': creator_dict['id'],
            'skill': creator_skill,
            'email': creator_dict['email'],
            'avatar_url': creator_dict['avatar_url'],
            'nickname': creator_dict['nickname'],
            'gender': creator_dict['gender'],
            'date_of_birth': creator_dict['date_of_birth'],
            'description': creator_dict['description'],
            'lives_in': creator_dict['lives_in'],
            'come_from': creator_dict['come_from'],
            'works_at': creator_dict['works_at'],
            'website_url': creator_dict['website_url'],
            'twitter_url': creator_dict['twitter_url'],
            'facebook_url': creator_dict['facebook_url'],
            'instagram_url': creator_dict['instagram_url'],
            'linkedin_url': creator_dict['linkedin_url'],
            'fullname': creator_dict['fullname'],
            'family_name': creator_dict['family_name'],
            'given_name': creator_dict['given_name'],
            'language': creator_dict['language'],

            'followers': creator_dict['followers'],
            'following': creator_dict['following'],
          }
        })

      ret_obj = data_books
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class GetBookByUserEntryId(WebappHelper):
  def processOfRequest(self):
    try:
      loginCheck = self.checkLogin()
      logging.info("loginCheck=" + str(loginCheck))
      
      viewer_email = None
      if loginCheck.get('status') and not sateraito_func.logoutIfUserDisabled(self, self.viewer_email):
        viewer_email = self.viewer_email

      request_json = json.JSONDecoder().decode(request.get_data().decode())
      # get params
      user_entry_id = request_json.get('user_entry_id', '')
      search_keyword = request_json.get('search_keyword', '')
      type_search = request_json.get('type_search', '')
      type_book_id = request_json.get('type_book', '')
      category_id = request_json.get('category', '')
      limit = int(request_json.get('limit', '500'))

      result_list, count = BookUtils.searchDocsByFullText(self, viewer_email, search_keyword, limit=limit,
                                                          type_search=type_search, type_book_id=type_book_id,
                                                          category_id=category_id, just_book_of=True, of_viewer_email=user_entry_id)

      data_books = []
      for dict_item in result_list:
        book_dict = UCFMDLBook.getDict(dict_item['id'])

        # Check book dict empty or deleted
        if book_dict is None:
          # removeFromIndex book entry None
          BookUtils.removeFromIndexById(dict_item['id'])
          continue

        if not BookUtils.accessBookDict(book_dict, viewer_email=viewer_email):
          continue

        creator_skill = []
        creator_dict = UCFMDLUserInfo.getDict(book_dict['creator_id'])
        if creator_dict['skill']:
          creator_skill = json.JSONDecoder().decode(creator_dict['skill'])

        characters = json.JSONDecoder().decode(book_dict['characters'])
        chapters = json.JSONDecoder().decode(book_dict['chapters'])

        images = json.JSONDecoder().decode(book_dict['images'])
        book_cover = json.JSONDecoder().decode(book_dict['book_cover'])

        data_books.append({
          'id': book_dict['id'],
          'status': book_dict['status'],

          'book_cover': book_cover,
          'images': images,

          'title': book_dict['title'],
          'summary': book_dict['summary'],

          'total_join': book_dict['total_join'],
          'rate_star': book_dict['rate_star'],
          'total_comment': book_dict['total_comment'],

          'characters': characters,
          'chapter_limit': len(chapters),
          'chapters': chapters,

          'created_date': UcfUtil.getLocalTime(book_dict['created_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),
          'updated_date': UcfUtil.getLocalTime(book_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),

          'my_story': None,
          'my_stories_history': [],

          'category': {
            'id': book_dict['category_book_id'],
            'name': book_dict['category_book_name'],
          },
          'type_book': {
            'id': book_dict['type_book_id'],
            'name': book_dict['type_book_name'],
          },
          'creator': {
            'id': creator_dict['id'],
            'skill': creator_skill,
            'email': creator_dict['email'],
            'avatar_url': creator_dict['avatar_url'],
            'nickname': creator_dict['nickname'],
            'gender': creator_dict['gender'],
            'date_of_birth': creator_dict['date_of_birth'],
            'description': creator_dict['description'],
            'lives_in': creator_dict['lives_in'],
            'come_from': creator_dict['come_from'],
            'works_at': creator_dict['works_at'],
            'website_url': creator_dict['website_url'],
            'twitter_url': creator_dict['twitter_url'],
            'facebook_url': creator_dict['facebook_url'],
            'instagram_url': creator_dict['instagram_url'],
            'linkedin_url': creator_dict['linkedin_url'],
            'fullname': creator_dict['fullname'],
            'family_name': creator_dict['family_name'],
            'given_name': creator_dict['given_name'],
            'language': creator_dict['language'],

            'followers': creator_dict['followers'],
            'following': creator_dict['following'],
          }
        })

      ret_obj = data_books
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class AdminSearchBook(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()
      # check is workflow admin
      if not self.is_workflow_admin:
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())
      # get params
      search_keyword = request_json.get('search_keyword', '')
      type_search = request_json.get('type_search', '')
      del_flag = request_json.get('del_flag', None)
      type_book_id = request_json.get('type_book', '')
      category_id = request_json.get('category', '')
      sort_by = request_json.get('sort_by', '')
      date_from = request_json.get('date_from', '')
      date_to = request_json.get('date_to', '')

      limit = int(request_json.get('limit', '500'))
      page = request_json.get('page', 1)

      result_list, count, have_more_rows = BookUtils.adminSearchDocsByFullText(self, self.viewer_email, search_keyword, limit=limit, page=page,
                                                                                del_flag=del_flag, type_search=type_search,
                                                                                date_from=date_from, date_to=date_to,
                                                                                type_book_id=type_book_id, category_id=category_id,
                                                                                sort_by=sort_by)

      data_books = []
      for dict_item in result_list:
        book_dict = UCFMDLBook.getDict(dict_item['id'])

        # # Check book dict empty or deleted
        # is_skip = (book_dict is None) or book_dict['del_flag']
        # if is_skip:
        #   # ignore book entry None or flag delete True
        #   # BookUtils.removeFromIndexById(dict_item['id'])
        #   continue
        #
        # if not BookUtils.accessBookDict(book_dict, viewer_email=viewer_email):
        #   continue

        creator_skill = []
        creator_dict = UCFMDLUserInfo.getDict(book_dict['creator_id'])
        if creator_dict['skill']:
          creator_skill = json.JSONDecoder().decode(creator_dict['skill'])

        characters = json.JSONDecoder().decode(book_dict['characters'])
        chapters = json.JSONDecoder().decode(book_dict['chapters'])

        images = json.JSONDecoder().decode(book_dict['images'])
        book_cover = json.JSONDecoder().decode(book_dict['book_cover'])

        list_user_joined = UCFMDLStoriesUsersJoined.getDictListByBookId(dict_item['id'], timezone=self._timezone)

        if book_dict['feedback_summary']:
          feedback_summary = json.JSONDecoder().decode(book_dict['feedback_summary'])
        else:
          feedback_summary = {
            "total": 0,
            "level": {}
          }

        data_books.append({
          'id': book_dict['id'],
          'status': book_dict['status'],

          'book_cover': book_cover,
          'images': images,

          'title': book_dict['title'],
          'summary': book_dict['summary'],

          'total_join': book_dict['total_join'],
          'list_user_joined': list_user_joined,
          'rate_star': book_dict['rate_star'],
          'total_comment': book_dict['total_comment'],
          'feedback_summary': feedback_summary,

          'characters': characters,
          'chapter_limit': len(chapters),
          'chapters': chapters,

          'created_date': UcfUtil.getLocalTime(book_dict['created_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),
          'updated_date': UcfUtil.getLocalTime(book_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),

          'my_story': None,
          'my_stories_history': [],

          'category': {
            'id': book_dict['category_book_id'],
            'name': book_dict['category_book_name'],
          },
          'type_book': {
            'id': book_dict['type_book_id'],
            'name': book_dict['type_book_name'],
          },
          'creator': {
            'id': creator_dict['id'],
            'skill': creator_skill,
            'email': creator_dict['email'],
            'avatar_url': creator_dict['avatar_url'],
            'nickname': creator_dict['nickname'],
            'gender': creator_dict['gender'],
            'date_of_birth': creator_dict['date_of_birth'],
            'description': creator_dict['description'],
            'lives_in': creator_dict['lives_in'],
            'come_from': creator_dict['come_from'],
            'works_at': creator_dict['works_at'],
            'website_url': creator_dict['website_url'],
            'twitter_url': creator_dict['twitter_url'],
            'facebook_url': creator_dict['facebook_url'],
            'instagram_url': creator_dict['instagram_url'],
            'linkedin_url': creator_dict['linkedin_url'],
            'fullname': creator_dict['fullname'],
            'family_name': creator_dict['family_name'],
            'given_name': creator_dict['given_name'],
            'language': creator_dict['language'],

            'followers': creator_dict['followers'],
            'following': creator_dict['following'],
          }
        })

      ret_obj = {
        "results": data_books,
        "count": count,
        "have_more_rows": have_more_rows
      }
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class SetFeedbackUserBook(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      user_dict = UCFMDLUserInfo.getDict(self.viewer_email)
      if not user_dict:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND_YOUR_INFO'),
          'error_code': 400
        })

      # get params
      request_json = json.JSONDecoder().decode(request.get_data().decode())
      book_id = request_json.get('book_id')
      id_my_feedback = request_json.get('id_my_feedback')
      rating_feedback = request_json.get('rating_feedback', 0)
      comment_feedback = request_json.get('comment_feedback', "")

      book_dict = UCFMDLBook.getDict(book_id)
      if not book_dict or book_dict['del_flag']:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })
      if not BookUtils.accessBookDict(book_dict, viewer_email=self.viewer_email):
        return self.send_error_response({
          'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION_BOOK'),
          'error_code': 403
        })

      row = None
      if id_my_feedback:
        row = UCFMDLFeedbackBookUsers.getById(id_my_feedback)
        row.rating = int(rating_feedback)
        row.comment = comment_feedback
        row.put()
      else:
        new_row = UCFMDLFeedbackBookUsers()
        new_row.user_id = self.viewer_email
        new_row.book_id = book_id
        new_row.type_feedback = sateraito_inc.KEY_FEEDBACK_TYPE_BOOK
        new_row.rating = int(rating_feedback)
        new_row.comment = comment_feedback
        new_row.put()

        row = new_row

      UCFMDLFeedbackBookUsers.clearListByBookInstanceCache(book_id=book_id, type_feedback=sateraito_inc.KEY_FEEDBACK_TYPE_BOOK)

      # Add task run update total rating and total comment
      BookUtils.addTaskUpdateByFeedback(book_id)

      row_dict = row.to_dict()
      row_dict['id'] = row.key.id()
      row_dict['user_create'] = {
        'id': user_dict['id'],
        'email': user_dict['email'],
        'avatar_url': user_dict['avatar_url'],
        'nickname': user_dict['nickname'],
        'fullname': user_dict['fullname'],
        'language': user_dict['language'],
      }
      row_dict['created_date'] = UcfUtil.getLocalTime(row_dict['created_date'], self._timezone).strftime('%Y/%m/%d %H:%M')
      row_dict['updated_date'] = UcfUtil.getLocalTime(row_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M')

      ret_obj = row_dict
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class SendMailNotificaFollowerCreator(WebappHelper):

  def processOfRequest(self):
    try:
      self._approot_path = os.path.dirname(__file__)

      # get params
      # request_json = json.JSONDecoder().decode(request.get_data().decode())

      book_id = request.get('book_id', '')
      logging.info("book_id=%s" % str(book_id))
      is_update_book = sateraito_func.strToBool(request.get('is_update_book', 'false'))
      logging.info("is_update_book=%s" % str(is_update_book))
      follower_id = request.get('follower_id', '')
      logging.info("follower_id=%s" % str(follower_id))

      if book_id == '':
        return self.send_error_response({
          'error_message': self.getMsg('PARAMS_INVALIDATE'),
          'error_code': 'book_id',
          'param': 'book_id',
        })
      if follower_id == '':
        return self.send_error_response({
          'error_message': self.getMsg('PARAMS_INVALIDATE'),
          'error_code': 'follower_id',
          'param': 'follower_id',
        })

      book_dict = UCFMDLBook.getDict(book_id)
      if book_dict is None or book_dict['del_flag']:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })

      follower_info = UCFMDLUserInfo.getDict(follower_id)
      if not follower_info:
        return self.send_error_response({
          'error_message': self.getMsg('NOTFOUND_USER'),
          'error_code': '',
          'param': '',
        })

      if not follower_info['email'] or follower_info['email'] == '':
        return self.send_error_response({
          'error_message': self.getMsg('NOTFOUND_USER'),
          'error_code': '',
          'param': '',
        })

      if not BookUtils.accessBookDict(book_dict, viewer_email=follower_info['user_entry_id']):
        return self.send_error_response({
          'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION'),
          'error_code': '',
          'param': '',
        })

      creator_dict = UCFMDLUserInfo.getDict(book_dict['creator_id'])

      if is_update_book:
        subject = self.getMsg('CREATOR_FOLLOW_UPDATE_BOOK_SEND_MAIL_SUBJECT_TITLE')
        template_render = 'creator_update_book.html'
      else:
        subject = self.getMsg('CREATOR_FOLLOW_HAVE_NEW_BOOK_SEND_MAIL_SUBJECT_TITLE')
        template_render = 'creator_have_new_book.html'

      url = sateraito_inc.my_site_url + '/book/%s' % str(book_id)

      book_cover = json.JSONDecoder().decode(book_dict['book_cover'])

      template_vals = {
        'url': url,
        'title': subject,
        'my_site_url': sateraito_inc.my_site_url,

        'id_book': book_id,
        'title_book': book_dict['title'],
        'book_cover_url': book_cover['url'],
        'summary_book': book_dict['summary'],
        'updated_date_book': UcfUtil.getLocalTime(book_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),

        'category': {
          'id': book_dict['category_book_id'],
          'name': book_dict['category_book_name'],
        },
        'type_book': {
          'id': book_dict['type_book_id'],
          'name': book_dict['type_book_name'],
        },

        'creator': {
          'id': creator_dict['id'],
          'fullname': creator_dict['fullname'],
          'email': creator_dict['email'],
          'avatar_url': creator_dict['avatar_url'],
          'nickname': creator_dict['nickname'],
          'gender': creator_dict['gender'],
          'date_of_birth': creator_dict['date_of_birth'],
          'description': creator_dict['description'],
          'lives_in': creator_dict['lives_in'],
          'come_from': creator_dict['come_from'],
          'works_at': creator_dict['works_at'],
          'website_url': creator_dict['website_url'],
          'twitter_url': creator_dict['twitter_url'],
          'facebook_url': creator_dict['facebook_url'],
          'instagram_url': creator_dict['instagram_url'],
          'linkedin_url': creator_dict['linkedin_url'],
          'family_name': creator_dict['family_name'],
          'given_name': creator_dict['given_name'],
          'language': creator_dict['language'],

          'followers': creator_dict['followers'],
          'following': creator_dict['following'],
        },
      }

      self.appendBasicInfoToTemplateVals(template_vals)
      emailBody = self.render_template(template_render, self._design_type, template_vals)
      sateraito_mail.sendMail(follower_info['email'], subject, emailBody, is_html=True)

      ret_obj = {
      }
      self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      self.redirectError(UcfMessage.getMessage(self.getMsg('MSG_SYSTEM_ERROR'), ()))
      return

############################################################
# REQUEST FOR USER STORIES
############################################################

class CreateUserStory(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      book_id = request_json.get('book_id', '')
      join_with = request_json.get('join_with', '')

      book_dict = UCFMDLBook.getDict(book_id)
      if not book_dict or book_dict['del_flag']:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })

      if not BookUtils.accessBookDict(book_dict, viewer_email=self.viewer_email):
        return self.send_error_response({
          'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION_BOOK'),
          'error_code': 403
        })

      # Process update row user joined book
      book_row = UCFMDLBook.getInstance(book_id)
      user_joined_row = StoriesUsersJoinedUtils.getUserJoined(self.viewer_email, book_id, del_flag=False)
      if user_joined_row is None:
        book_row.total_join = book_row.total_join + 1
        book_row.popular = book_row.popular + 1
        book_row.put()

        # rebuild text search index
        BookUtils.rebuildTextSearchIndex(book_row)

        user_joined_row = UCFMDLStoriesUsersJoined()
        user_joined_row.book_id = book_id
        user_joined_row.user_id = self.viewer_email
        user_joined_row.count_joined = 1
      else:
        user_joined_row.count_joined = (user_joined_row.count_joined + 1)
      user_joined_row.put()

      # Process initialize my_story for user
      new_row = UCFMDLUserStories(id=UserStoriesUtils.getKey(self))
      new_row.creator_id = self.viewer_email
      new_row.book_id = book_id
      new_row.join_with = join_with

      join_with_character_name = "character_default"
      if join_with and join_with != "character_default":
        join_with = json.JSONDecoder().decode(join_with)
        join_with_character_name = join_with['name']
      logging.info("join_with_character_name=%s" % (str(join_with_character_name)))

      chapters = json.JSONDecoder().decode(book_row.chapters)
      len_chapters = len(chapters)
      characters = json.JSONDecoder().decode(book_row.characters)
      character_main = None
      for character in characters:
        if character['is_protagonist']:
          character_main = character

      assistant_content = ""
      assistant_content += "Tiêu đề câu chuyện: %s.\n" % (book_row.title)

      name = None
      age = None
      # description_if_is_me = None

      assistant_content += "Gồm có {0} nhân vật:\n".format(len(characters))
      for character in characters:
        name = character['name']
        age = character['age']
        description = character['description']
        # description = character['description']
        # description_if_is_me = character['description_if_is_me']

        is_protagonist = character_main['name'] == name
        logging.info('name="%s"' % (str(name)))
        logging.info('join_with_character_name="%s"' % (str(join_with_character_name)))

        if join_with_character_name != name:
          assistant_content += "  {0} {1}, {2} tuổi, {3}\n".format(name, "nhân vật chính" if is_protagonist else '', age, description)

        if join_with_character_name == name:
          assistant_content += "  tôi là {0} {1}, {2} tuổi, {3}\n".format(name, "nhân vật chính" if is_protagonist else '', age, description)

      assistant_content += "Tóm tắt: %s.\n" % (book_row.summary)

      for index, chapter_item in enumerate(chapters):
        assistant_content += "Chương {0}:\n  {1}: {2}\n".format((index + 1), chapter_item['title'], chapter_item['idea'])

      if join_with_character_name != "character_default":
        assistant_content += "\nKể chuyện bằng ngôi thứ nhất bằng nhân vật {0}.".format(join_with_character_name)

      assistant_content += "\nNội dung của chương đang viết được làm tiền đề cho chương tiếp theo, chỉ có nội dung kết khi ở chương cuối"

      # input_text_request = "%s\n Tóm tắt chi tiết nhân vật, mô tả về nhân nhật và nội dung chương" % (assistant_content)
      # is_success, error_message, output_text, message_history = chatgpt_func_v2.callChatGPT(self, api_key, model, input_text_request, [], False)
      new_row.summary_request_for_gpt = assistant_content

      new_row.put()

      UCFMDLStoriesUsersJoined.clearListByBookInstanceCache(book_id)

      row_dict = new_row.to_dict()
      row_dict['id'] = new_row.key.id()
      if new_row.join_with != 'character_default':
        row_dict['join_with'] = json.JSONDecoder().decode(new_row.join_with)
      row_dict['created_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(new_row.created_date, self._timezone))
      row_dict['updated_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(new_row.updated_date, self._timezone))

      ret_obj = row_dict
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class UpdateUserStory(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      user_story_id = request_json.get('user_story_id', '')
      join_with = request_json.get('join_with', '')

      story_row = UCFMDLUserStories.getInstance(user_story_id)
      if story_row is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND'),
          'error_code': 400
        })
      if story_row.creator_id != self.viewer_email:
        return self.send_error_response({
          'error_message': self.getMsg('THIS_STORY_IS_NOT_YOURS'),
          'error_code': 403
        })

      book_dict = UCFMDLBook.getDict(story_row.book_id)
      if not book_dict or book_dict['del_flag']:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })
      if not BookUtils.accessBookDict(book_dict, viewer_email=self.viewer_email):
        return self.send_error_response({
          'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION_BOOK'),
          'error_code': 403
        })

      story_row.join_with = join_with

      join_with_character_name = "character_default"
      if join_with and join_with != "character_default":
        join_with = json.JSONDecoder().decode(join_with)
        join_with_character_name = join_with['name']

      chapters = json.JSONDecoder().decode(book_dict['chapters'])
      len_chapters = len(chapters)
      characters = json.JSONDecoder().decode(book_dict['characters'])
      character_main = None
      for character in characters:
        if character['is_protagonist']:
          character_main = character

      assistant_content = ""
      assistant_content += "Tiêu đề câu chuyện: %s.\n" % (book_dict['title'])

      name = None
      age = None

      assistant_content += "Gồm có {0} nhân vật:\n".format(len(characters))
      for character in characters:
        name = character['name']
        age = character['age']
        description = character['description']

        is_protagonist = character_main['name'] == name
        logging.info('name="%s"' % (str(name)))
        logging.info('join_with_character_name="%s"' % (str(join_with_character_name)))

        if join_with_character_name != name:
          assistant_content += "  {0} {1}, {2} tuổi, {3}\n".format(name, "nhân vật chính" if is_protagonist else '', age, description)

        if join_with_character_name == name:
          assistant_content += "  tôi là {0} {1}, {2} tuổi, {3}\n".format(name, "nhân vật chính" if is_protagonist else '', age, description)

      assistant_content += "Tóm tắt: %s.\n" % (book_dict['summary'])

      for index, chapter_item in enumerate(chapters):
        assistant_content += "Chương {0}:\n  {1}: {2}\n".format((index + 1), chapter_item['title'], chapter_item['idea'])

      if join_with_character_name != "character_default":
        assistant_content += "\nKể chuyện bằng ngôi thứ nhất bằng nhân vật {0}.".format(join_with_character_name)

      assistant_content += "\nNội dung của chương đang viết được làm tiền đề cho chương tiếp theo, chỉ có nội dung kết khi ở chương cuối"
      story_row.summary_request_for_gpt = assistant_content

      story_row.put()

      UCFMDLStoriesUsersJoined.clearListByBookInstanceCache(story_row.book_id)

      row_dict = story_row.to_dict()
      row_dict['id'] = story_row.key.id()
      if row_dict['join_with'] != 'character_default':
        row_dict['join_with'] = json.JSONDecoder().decode(row_dict['join_with'])
      row_dict['created_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(row_dict['created_date'], self._timezone))
      row_dict['updated_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(row_dict['updated_date'], self._timezone))

      ret_obj = row_dict
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class SetFeedbackUserStory(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      book_id = request_json.get('book_id', '')
      user_story_id = request_json.get('user_story_id', '')
      rating_feedback = request_json.get('rating_feedback', '0')
      comment_feedback = request_json.get('comment_feedback', '')

      story_row = UCFMDLUserStories.getInstance(user_story_id)
      if story_row is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND'),
          'error_code': 400
        })
      if story_row.creator_id != self.viewer_email:
        return self.send_error_response({
          'error_message': self.getMsg('THIS_STORY_IS_NOT_YOURS'),
          'error_code': 403
        })
      if story_row.book_id != book_id:
        return self.send_error_response({
          'error_message': self.getMsg('THIS_STORY_WITHOUT_THIS_BOOK_ID'),
          'error_code': 403
        })

      book_dict = UCFMDLBook.getDict(book_id)
      if not book_dict or book_dict['del_flag']:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })
      if not BookUtils.accessBookDict(book_dict, viewer_email=self.viewer_email):
        return self.send_error_response({
          'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION_BOOK'),
          'error_code': 403
        })

      new_row = UCFMDLFeedbackBookUsers()
      new_row.user_id = self.viewer_email
      new_row.book_id = book_id
      new_row.user_story_id = user_story_id
      new_row.type_feedback = sateraito_inc.KEY_FEEDBACK_TYPE_STORY
      new_row.rating = int(rating_feedback)
      new_row.comment = comment_feedback
      new_row.put()

      UCFMDLFeedbackBookUsers.clearListByBookInstanceCache(book_id=book_id, type_feedback=sateraito_inc.KEY_FEEDBACK_TYPE_STORY)

      # Add task run update total rating and total comment
      BookUtils.addTaskUpdateByFeedback(book_id)

      row_dict = new_row.to_dict()
      row_dict['id'] = new_row.key.id()
      user_dict = UCFMDLUserInfo.getDict(self.viewer_email)
      row_dict['user_create'] = {
        'id': user_dict['id'],
        'email': user_dict['email'],
        'avatar_url': user_dict['avatar_url'],
        'nickname': user_dict['nickname'],
        'fullname': user_dict['fullname'],
        'language': user_dict['language'],
      }
      row_dict['created_date'] = UcfUtil.getLocalTime(row_dict['created_date'], self._timezone).strftime('%Y/%m/%d %H:%M')
      row_dict['updated_date'] = UcfUtil.getLocalTime(row_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M')

      ret_obj = row_dict
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class ChangeToHistoryUserStory(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      user_story_id = request_json.get('user_story_id', '')

      story_row = UCFMDLUserStories.getInstance(user_story_id)
      if story_row is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND'),
          'error_code': 400
        })
      if story_row.creator_id != self.viewer_email:
        return self.send_error_response({
          'error_message': self.getMsg('THIS_STORY_IS_NOT_YOURS'),
          'error_code': 403
        })

      book_dict = UCFMDLBook.getDict(story_row.book_id)
      if not book_dict or book_dict['del_flag']:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })
      if not BookUtils.accessBookDict(book_dict, viewer_email=self.viewer_email):
        return self.send_error_response({
          'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION_BOOK'),
          'error_code': 403
        })

      story_row.history_flag = True
      story_row.put()

      row_dict = story_row.to_dict()
      row_dict['id'] = story_row.key.id()
      if row_dict['join_with'] != 'character_default':
        row_dict['join_with'] = json.JSONDecoder().decode(row_dict['join_with'])
      row_dict['created_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(row_dict['created_date'], self._timezone))
      row_dict['updated_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(row_dict['updated_date'], self._timezone))

      ret_obj = row_dict
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class GetUserStoryById(WebappHelper):
  def processOfRequest(self, book_id, user_story_id):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      # get params

      story_dict = UCFMDLUserStories.getDict(user_story_id)
      if story_dict is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND'),
          'error_code': 400
        })

      if story_dict['book_id'] != book_id:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND'),
          'error_code': 400
        })

      # user_chapters = UserChaptersUtils.getChaptersByIdStory(book_id, user_story_id, to_dict=True, timezone=self._timezone)
      story_dict['user_chapters'] = UCFMDLUserChapters.getDictList(book_id, user_story_id, timezone=self._timezone)

      if story_dict['join_with'] != 'character_default':
        story_dict['join_with'] = json.JSONDecoder().decode(story_dict['join_with'])
      story_dict['created_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(story_dict['created_date'], self._timezone))
      story_dict['updated_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(story_dict['updated_date'], self._timezone))

      ret_obj = story_dict
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class ListStoriesJoinMyBook(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      book_id = request_json.get('book_id')
      page_size = request_json.get('page_size', 100)
      page = request_json.get('page', 1)

      book_dict = UCFMDLBook.getDict(book_id)
      if book_dict is None:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })

      # Fetch the next page of results using the cursor
      query = UCFMDLUserStories.query()
      query = query.filter(UCFMDLUserStories.book_id == book_id)
      query = query.order(-UCFMDLUserStories.updated_date)
      results = query.fetch(limit=(page_size + 1), offset=((page - 1) * page_size))

      # Store the next cursor for the next page
      have_more_rows = len(results) == (page_size + 1)
      logging.info("have_more_rows=%s" % str(have_more_rows))

      # remove last item for check have more rows
      if have_more_rows:
        results.pop()

      data_res = []
      for row in results:
        row_dict = row.to_dict()

        row_dict['id'] = row.key.id()
        user_dict = UCFMDLUserInfo.getDict(row_dict["creator_id"])

        row_dict['user_create'] = {
          'id': user_dict['id'],
          'email': user_dict['email'],
          'avatar_url': user_dict['avatar_url'],
          'nickname': user_dict['nickname'],
          'fullname': user_dict['fullname'],
          'language': user_dict['language'],
        }

        if row_dict['join_with'] != 'character_default':
          row_dict['join_with'] = json.JSONDecoder().decode(row_dict['join_with'])

        # user_chapters = UserChaptersUtils.getChaptersByIdStory(book_id, row_dict['id'], to_dict=True, timezone=self._timezone)
        row_dict['user_chapters'] = UCFMDLUserChapters.getDictList(book_id, row_dict['id'], timezone=self._timezone)

        row_dict['created_date'] = UcfUtil.getLocalTime(row_dict['created_date'], self._timezone).strftime('%Y/%m/%d %H:%M')
        row_dict['updated_date'] = UcfUtil.getLocalTime(row_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M')

        data_res.append(row_dict)

      return self.send_success_response({
        "results": data_res,
        "have_more_rows": have_more_rows,
      })

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class GetProcessStoryUserById(WebappHelper):
  def processOfRequest(self, user_story_id):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      # get params

      story_dict = UCFMDLUserStories.getDict(user_story_id)
      if story_dict is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND'),
          'error_code': 400
        })

      # if story_dict['book_id'] != book_id:
      #   return self.send_error_response({
      #     'error_message': self.getMsg('NOT_FOUND'),
      #     'error_code': 400
      #   })

      # user_chapters = UserChaptersUtils.getChaptersByIdStory(book_id, user_story_id, to_dict=True, timezone=self._timezone)
      # story_dict['user_chapters'] = UCFMDLUserChapters.getDictList(book_id, user_story_id, timezone=self._timezone)

      # if story_dict['join_with'] != 'character_default':
      #   story_dict['join_with'] = json.JSONDecoder().decode(story_dict['join_with'])
      # story_dict['created_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(story_dict['created_date'], self._timezone))
      # story_dict['updated_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(story_dict['updated_date'], self._timezone))

      ret_obj = story_dict['processing_flag']
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })


############################################################
# REQUEST FOR USER CHAPTERS
############################################################

class GetUserChapterById(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      chapter_id = request_json.get('chapter_id', '')
      chapter_dict = UCFMDLUserChapters.getDict(chapter_id)

      book_id = chapter_dict['book_id']
      user_story_id = chapter_dict['user_story_id']

      book_dict = UCFMDLBook.getDict(book_id)
      if not book_dict or book_dict['del_flag']:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })
      if not BookUtils.accessBookDict(book_dict, viewer_email=self.viewer_email):
        return self.send_error_response({
          'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION_BOOK'),
          'error_code': 403
        })

      user_story_dict = UCFMDLUserStories.getDict(user_story_id)
      if user_story_dict is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND'),
          'error_code': 400
        })
      if user_story_dict['creator_id'] != self.viewer_email:
        return self.send_error_response({
          'error_message': self.getMsg('THIS_STORY_IS_NOT_YOURS'),
          'error_code': 403
        })

      chapter_dict['shared_users'] = UCFMDLUserShareStories.getListUsersShared(book_id, self.viewer_email,
                                                                               user_story_id=user_story_id,
                                                                               user_chapter_id=chapter_id,
                                                                               type_share=sateraito_func.KEY_TYPE_CHAPTER_SHARE)

      chapter_dict['created_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(chapter_dict['created_date'], self._timezone))
      chapter_dict['updated_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(chapter_dict['updated_date'], self._timezone))
      ret_obj = chapter_dict
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class AddUserChapter(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      book_id = request_json.get('book_id', '')
      user_story_id = request_json.get('user_story_id', '')
      title = request_json.get('title', '')
      idea_of_user = request_json.get('idea')
      logging.info("idea_of_user=" + str(idea_of_user))

      book_dict = UCFMDLBook.getDict(book_id)
      if not book_dict or book_dict['del_flag']:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })
      if not BookUtils.accessBookDict(book_dict, viewer_email=self.viewer_email):
        return self.send_error_response({
          'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION_BOOK'),
          'error_code': 403
        })

      user_story_row = UCFMDLUserStories.getInstance(user_story_id)
      if user_story_row is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND'),
          'error_code': 400
        })
      if user_story_row.creator_id != self.viewer_email:
        return self.send_error_response({
          'error_message': self.getMsg('THIS_STORY_IS_NOT_YOURS'),
          'error_code': 403
        })

      # 入力チェック（不適切なキーワードチェックも）…とりあえず簡易的に
      chatgpt_prohibited_keywords = self.getDeptValue('chatgpt_prohibited_keywords')
      logging.info('chatgpt_prohibited_keywords=%s' % chatgpt_prohibited_keywords)

      chatgpt_prohibited_keywords_ary = chatgpt_prohibited_keywords.lower().replace('\r\n', '\n').replace('\n\r','\n').split('\n')
      for regexp_str in chatgpt_prohibited_keywords_ary:
        logging.debug('regexp_str=%s' % (regexp_str))
        if regexp_str.strip() != '':
          try:
            # 該当テキストすべてヒットさせようと思ったが、正規表現パターンに( )が含まれている場合にうまく全体が取得できないので単発に変更
            result_idea = re.search(regexp_str, idea_of_user, re.DOTALL | re.MULTILINE | re.IGNORECASE)
            if (result_idea and result_idea.group(0) and result_idea.group(0) != ''):
              matched_result = result_idea.group(0)
              logging.debug(matched_result)
              return self.send_error_response({
                'error_message': self.getMsg('EXIST_PROHIBITED_WORD'),
                'error_code': 400
              })

            result_title = re.search(regexp_str, title, re.DOTALL | re.MULTILINE | re.IGNORECASE)
            if (result_title and result_title.group(0) and result_title.group(0) != ''):
              matched_result = result_title.group(0)
              logging.debug(matched_result)
              return self.send_error_response({
                'error_message': self.getMsg('EXIST_PROHIBITED_WORD'),
                'error_code': 400
              })
          # 正規表現が正しくない場合はスキップ
          except Exception as e:
            logging.warning('invalid regexp:%s' % (regexp_str))
            logging.exception(e)

      # # ChatGPTのModeration API でもチェック 2023.06.13
      # from sateraito_chatgpt.moderation import Moderation
      # moderation = Moderation()
      # categories, category_scores = moderation.execute(idea)
      # THRESHOLD = 0.1
      # is_exist_inappropriate_expression = False
      # inappropriate_expression_categories = []
      # inappropriate_expression_messages = []
      # if categories is not None and category_scores is not None:
      #   if categories.hate or category_scores.hate >= THRESHOLD:
      #     is_exist_inappropriate_expression = True
      #     inappropriate_expression_categories.append('hate')
      #     inappropriate_expression_messages.append(self.getMsg('CATEGORY_HATE'))
      #   if categories.hate_threatening or category_scores.hate_threatening >= THRESHOLD:
      #     is_exist_inappropriate_expression = True
      #     inappropriate_expression_categories.append('hate_threatening')
      #     inappropriate_expression_messages.append(self.getMsg('CATEGORY_HATE_THREATENING'))
      #   if categories.self_harm or category_scores.self_harm >= THRESHOLD:
      #     is_exist_inappropriate_expression = True
      #     inappropriate_expression_categories.append('self_harm')
      #     inappropriate_expression_messages.append(self.getMsg('CATEGORY_SELF_HARM'))
      #   if categories.sexual or category_scores.sexual >= THRESHOLD:
      #     is_exist_inappropriate_expression = True
      #     inappropriate_expression_categories.append('sexual')
      #     inappropriate_expression_messages.append(self.getMsg('CATEGORY_SEXUAL'))
      #   if categories.sexual_minors or category_scores.sexual_minors >= THRESHOLD:
      #     is_exist_inappropriate_expression = True
      #     inappropriate_expression_categories.append('sexual_minors')
      #     inappropriate_expression_messages.append(self.getMsg('CATEGORY_SEXUAL_MINORS'))
      #   if categories.violence or category_scores.violence >= THRESHOLD:
      #     is_exist_inappropriate_expression = True
      #     inappropriate_expression_categories.append('violence')
      #     inappropriate_expression_messages.append(self.getMsg('CATEGORY_VIOLENCE'))
      #   if categories.violence_graphic or category_scores.violence_graphic >= THRESHOLD:
      #     is_exist_inappropriate_expression = True
      #     inappropriate_expression_categories.append('violence_graphic')
      #     inappropriate_expression_messages.append(self.getMsg('CATEGORY_VIOLENCE_GRAPHIC'))
      #   if is_exist_inappropriate_expression:
      #     # self.insertHistory()
      #     return Response(UcfMessage.getMessage(self.getMsg('EXIST_INAPPROPRIATE_EXPRESSION'), ('/'.join(inappropriate_expression_messages))), status=400)

      if user_story_row.processing_flag:
        return self.send_error_response({
          'error_message': self.getMsg('IT_PROCESSIONG'),
          'error_code': 400
        })

      user_story_row.started_flag = True
      user_story_row.processing_flag = True
      user_story_row.put()

      chapters = json.JSONDecoder().decode(book_dict['chapters'])
      len_chapters_book = len(chapters)
      characters = json.JSONDecoder().decode(book_dict['characters'])
      character_main = None
      for character in characters:
        if character['is_protagonist']:
          character_main = character

      message_history = []

      user_chapters = UCFMDLUserChapters.getDictList(book_id, user_story_id, timezone=self._timezone)
      len_chapters_user = len(user_chapters)
      chapter_number_user = len_chapters_user + 1

      # join_with = None
      join_with_character_name = "character_default"
      if user_story_row.join_with and user_story_row.join_with != "character_default":
        join_with = json.JSONDecoder().decode(user_story_row.join_with)
        join_with_character_name = join_with['name']

      # update assistant_content when users want the next chapter with their ideas
      if idea_of_user:
        logging.info("update assistant_content when users want the next chapter with their ideas")

        content_chapter = "Chương {0}:\n  {1}: {2}\n".format(chapter_number_user, title, chapters[len_chapters_user]['idea'])
        content_chapter_replace = "Chương {0}:\n  {1}: {2}\n".format(chapter_number_user, title, idea_of_user)

        user_story_row.summary_request_for_gpt = user_story_row.summary_request_for_gpt.replace(content_chapter, content_chapter_replace)
        user_story_row.put()

      message_history.append({
        "role": "assistant",
        "content": user_story_row.summary_request_for_gpt
      })

      if self._language in sateraito_func.ACTIVE_LANGUAGES:
        language_disp = self.getMsg(sateraito_func.LANGUAGES_MSGID.get(self._language, ''))
        message_history.append({
          "role": "system",
          # "content": 'I ask in Vietnamese and you only have to answer in %s.' % language_disp
          "content": 'You must answer in %s only.' % language_disp
        })

      if not idea_of_user:
        idea_of_user = chapters[len_chapters_user]['idea']

      input_text_edit = ""
      if len_chapters_user == 0:

        # input_text_edit = "Giúp tôi viết truyện\n"
        # input_text_edit += "Tiêu đề: %s\n" % book_dict['title']
        # input_text_edit += "Tóm tắt: %s\n" % book_dict['summary']

        # for character in characters:
        #   name = character['name']
        #   age = character['age']
        #   description = character['description']
        #   description = character['description']
        #   description_if_is_me = character['description_if_is_me']

        #   if join_with_character_name == name:
        #     input_text_edit += "Tôi trong vai {0}, {1} tuổi, {2}\n".format(name, age, description_if_is_me)
        #   else:
        #     input_text_edit += "Nhân vật {0}, {1} tuổi, {2}\n".format(name, age, description)

        # input_text_edit += "Nhân vật chính: {0}.\n".format(character_main['name'])

        # for index, chapter_item in enumerate(chapters):
        #   input_text_edit += "Chương {0}: {1}\n".format((index + 1), chapter_item['title'])
        #   input_text_edit += "  Nội dung: {0}\n".format(chapter_item['idea'])

        input_text_edit = "Viết chương 1"
        # input_text_edit = "Giúp tôi viết đầu tiên tiêu đề: {0}, ý tưởng: {1}. ".format(chapters[0]['title'], chapters[0]['idea'])
      else:
        # for user_chapter_dict in user_chapters:
        #   message_history.append({
        #     "role": "user",
        #     "content": user_chapter_dict['user_content']
        #   })
        #   message_history.append({
        #     "role": "assistant",
        #     "content": user_chapter_dict['content']
        #   })
        if chapter_number_user == len_chapters_book:
          # input_text_edit = "Giúp tôi viết chương cuối tiêu đề: {0}, ý tưởng: {1}. ".format(title, idea)
          input_text_edit = "Viết chương cuối"
        else:
          input_text_edit = "Viết chương {0}".format(chapter_number_user)

      # if (chapter_number_user) < len_chapters_book:
      #   input_text_edit += "Nội dung chương này là tiền đề cho nội dung chương tiếp theo, nhưng không viết về nội dung của chương tiếp theo"

      # input_text_edit += "\nKhông cần thông tin chương, không chương số và không tiêu đề chương"

      # GPT4対応
      is_enable_gpt4 = self.getDeptValue('chatgpt_model4_available_flag') == 'AVAILABLE'
      logging.info('is_enable_gpt4=%s' % (is_enable_gpt4))
      use_model = request_json.get('use_model', '')
      logging.info('use_model=%s' % (use_model))
      self.setCookie(UcfConfig.COOKIE_KEY_GPT_MODEL, use_model)

      # GPT4対応：使用モデルの決定
      # model = 'gpt-3.5-turbo'
      # if use_model == 'gpt-4' and is_enable_gpt4:
      #   model = 'gpt-4'
      # logging.info('model=%s' % (model))

      id_new_chapter = UserChaptersUtils.getKey(self)
      new_chapter_row = UCFMDLUserChapters(id=id_new_chapter)
      new_chapter_row.creator_id = self.viewer_email
      new_chapter_row.book_id = book_id
      new_chapter_row.user_story_id = user_story_id
      new_chapter_row.chapter_number = chapter_number_user
      new_chapter_row.title = title
      new_chapter_row.idea = idea_of_user
      new_chapter_row.user_content = input_text_edit
      new_chapter_row.status = 'processing'
      new_chapter_row.put()

      UserStoriesUtils.startAskChatgptWithStream(self, self.viewer_email, book_id, user_story_id, id_new_chapter, json.JSONEncoder().encode(message_history), model)

      UCFMDLUserChapters.clearListInstanceCache(book_id, user_story_id)

      ret_obj = new_chapter_row.exchangeVo(self._timezone)
      ret_obj['id'] = id_new_chapter
      ret_obj['shared_users'] = []

      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class SetFeedbackUserChapter(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      book_id = request_json.get('book_id', '')
      user_story_id = request_json.get('user_story_id', '')
      user_chapter_id = request_json.get('user_chapter_id', '')
      is_good = request_json.get('is_good', '')
      comment = request_json.get('comment', '')

      book_dict = UCFMDLBook.getDict(book_id)
      if not book_dict or book_dict['del_flag']:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })
      if not BookUtils.accessBookDict(book_dict, viewer_email=self.viewer_email):
        return self.send_error_response({
          'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION_BOOK'),
          'error_code': 403
        })

      user_story_dict = UCFMDLUserStories.getDict(user_story_id)
      if user_story_dict is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND'),
          'error_code': 400
        })
      if user_story_dict['creator_id'] != self.viewer_email:
        return self.send_error_response({
          'error_message': self.getMsg('THIS_STORY_IS_NOT_YOURS'),
          'error_code': 403
        })

      chapter_row = UCFMDLUserChapters.getInstance(user_chapter_id)
      if chapter_row is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND'),
          'error_code': 400
        })
      if chapter_row.creator_id != self.viewer_email:
        return self.send_error_response({
          'error_message': self.getMsg('THIS_CHAPTER_IS_NOT_YOURS'),
          'error_code': 400
        })

      is_good_set = sateraito_func.strToBool(is_good)
      if is_good_set == chapter_row.is_good:
        chapter_row.is_good = None
      else:
        chapter_row.is_good = is_good_set
      chapter_row.comment = comment
      chapter_row.put()

      row_feedback = UCFMDLFeedbackBookUsers.getInstance(self.viewer_email, user_story_id, book_id, sateraito_inc.KEY_FEEDBACK_TYPE_CHAPTER, chapter_id=user_chapter_id)

      if chapter_row.is_good is None:
        if row_feedback:
          row_feedback.key.delete()
      else:
        if row_feedback:
          row_feedback.is_good = is_good_set
          row_feedback.comment = comment
          row_feedback.put()
        else:
          new_row = UCFMDLFeedbackBookUsers()
          new_row.user_id = self.viewer_email
          new_row.book_id = book_id
          new_row.user_story_id = user_story_id
          new_row.type_feedback = sateraito_inc.KEY_FEEDBACK_TYPE_CHAPTER
          new_row.is_good = is_good_set
          new_row.chapter_id = user_chapter_id
          new_row.comment = comment
          new_row.put()

      ret_obj = {
        'id': chapter_row.key.id(),
        'book_id': chapter_row.book_id,
        'creator_id': chapter_row.creator_id,
        'del_flag': chapter_row.del_flag,
        'title': chapter_row.title,
        'idea': chapter_row.idea,
        'status': chapter_row.status,
        'content': chapter_row.content,
        'is_good': chapter_row.is_good,
        'comment': chapter_row.comment,
        'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(chapter_row.created_date, self._timezone)),
        'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(chapter_row.updated_date, self._timezone)),
      }

      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class GetUserChapterPreview(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      user_info_dict = UCFMDLUserInfo.getDict(self.viewer_email)

      # get params
      # message_history = request_json.get('message_history', '')
      join_with = request_json.get('join_with', '')
      user_chapter_index = request_json.get('user_chapter_index', 0)
      chapters = request_json.get('chapters', '')
      characters = request_json.get('characters', '')
      summary = request_json.get('summary', '')
      title = request_json.get('title', '')
      idea = request_json.get('idea', '')

      chapters = json.JSONDecoder().decode(chapters)
      characters = json.JSONDecoder().decode(characters)
      # message_history = json.JSONDecoder().decode(message_history)
      character_main = None
      for character in characters:
        if character['is_protagonist']:
          character_main = character

      join_with_character_name = "character_default"
      if join_with and join_with != "character_default":
        join_with = json.JSONDecoder().decode(join_with)
        join_with_character_name = join_with['name']

      assistant_content = ""
      assistant_content += "Tiêu đề câu chuyện: %s. " % (title)

      name = None
      age = None

      assistant_content += "Gồm {0} nhân vật:".format(len(characters))
      for character in characters:
        name = character['name']
        age = character['age']
        description = character['description']
        description = character['description']

        is_protagonist = character_main['name'] == name

        if join_with_character_name != name:
          assistant_content += "  {0} {1}, {2} tuổi, {3}. ".format(name, "nhân vật chính" if is_protagonist else '', age, description)

        if join_with_character_name == name:
          assistant_content += "  tôi là {0} {1}, {2} tuổi, {3}\n".format(name, "nhân vật chính" if is_protagonist else '', age, description)

      assistant_content += "Tóm tắt: %s. " % (summary)

      for index, chapter_item in enumerate(chapters):
        idea_custom = ''
        if (idea != '') and (index == user_chapter_index):
          idea_custom = idea
        else:
          idea_custom = chapter_item['idea']

        assistant_content += "Chương {0}:  {1}: {2}. ".format((index + 1), chapter_item['title'], idea_custom)

      if join_with_character_name != "character_default":
        assistant_content += "\nKể chuyện bằng ngôi thứ nhất bằng nhân vật {0}.".format(join_with_character_name)

      message_history = []
      message_history.append({
        "role": "system",
        "content": 'You must answer in Vietnamese only.'
      })
      message_history.append({
        "role": "assistant",
        "content": assistant_content
      })

      input_text_edit = ''

      if idea == '':
        idea = chapters[user_chapter_index]['idea']

      if user_chapter_index == 0:
        input_text_edit = "Viết chương 1"
      else:
        if (user_chapter_index + 1) == len(chapters):
          input_text_edit = "Viết chương cuối"
        else:
          input_text_edit = "Viết chương {0}".format(user_chapter_index + 1)

      logging.info("input_text_edit=" + str(input_text_edit))
      is_success, error_message, output_text, message_history = chatgpt_func_v2.callChatGPT(self, api_key, model, input_text_edit, message_history, False)

      ret_obj = {
        'idea': idea,
        'title': title,
        'is_success': is_success,
        'error_message': error_message,
        'output_text': output_text,
        'message_history': message_history,
      }
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class TqChatgptCreateChapterWithStream(WebappHelper):
  def processOfRequest(self):
    try:
      self.viewer_email = self.request.get('viewer_email')
      uid = self.viewer_email
      logging.info('uid=%s' % (uid))

      # # 言語を決定（Cookieの値を考慮）
      # language_list = []
      hl_from_cookie = self.getCookie('hl')
      logging.info('hl_from_cookie=' + str(hl_from_cookie))
      if hl_from_cookie is None or hl_from_cookie == '':
        hl_from_cookie = sateraito_inc.DEFAULT_LANGUAGE
      if hl_from_cookie is not None and hl_from_cookie in sateraito_func.ACTIVE_LANGUAGES:
        self._language = hl_from_cookie

      book_id = self.request.get('book_id', None)
      logging.info("book_id=%s" % str(book_id))
      user_story_id = self.request.get('user_story_id', None)
      logging.info("user_story_id=%s" % str(user_story_id))
      chapter_id = self.request.get('chapter_id', None)
      logging.info("chapter_id=%s" % str(chapter_id))
      message_history = self.request.get('message_history')
      message_history = json.loads(message_history)
      logging.info("message_history=%s" % str(message_history))

      book_dict = UCFMDLBook.getDict(book_id)
      chapters = json.JSONDecoder().decode(book_dict['chapters'])
      len_chapters_book = len(chapters)

      user_story_row = UCFMDLUserStories.getInstance(user_story_id)

      chapter_row = UCFMDLUserChapters.getInstance(chapter_id)
      # len_chapters_user = chapter_row.chapter_number
      input_text_edit = chapter_row.user_content

      logging.info("input_text_edit=" + str(input_text_edit))
      is_success, error_message, output_text, message_history = chatgpt_func_v2.callChatGPT(self, api_key, model, input_text_edit, message_history, False)
      if not is_success:
        return self.send_error_response({
          'error_message': self.getMsg('ERROR_GPT'),
          'error_code': 400
        })

      chapter_row.content = output_text

      # message_history_summary = []
      # if self._language in sateraito_func.ACTIVE_LANGUAGES:
      #   language_disp = self.getMsg(sateraito_func.LANGUAGES_MSGID.get(self._language, ''))
      #   message_history_summary.append({
      #     "role": "system",
      #     # "content": 'You must answer in %s only.' % language_disp
      #     "content": 'You must answer in Vietnamese only.'
      #   })
      # input_text_edit_summary = "%s\n Tóm tắt còn %s ký tự" % (chapter_row.content, str(int(3000 / (len_chapters_user))))
      # is_success, error_message, output_summary, message_history_summary = chatgpt_func_v2.callChatGPT(self, api_key, model, input_text_edit_summary, message_history_summary, False)
      # if not is_success:
      #   logging.error(error_message)
      #   return self.send_error_response({
      #     'error_message': self.getMsg('ERROR_GPT'),
      #     'error_code': 400
      #   })
      #
      # chapter_row.assistant_content = output_summary
      chapter_row.status = 'complete'
      chapter_row.put()

      UCFMDLUserChapters.clearListInstanceCache(book_id, user_story_id)

      # UserStoriesUtils.addTaskSummaryChapter(self, chapter_id, model)

      # Update user story
      chapters_total = UserChaptersUtils.countChapter(book_id, user_story_id)
      user_story_row.chapters_total = chapters_total
      user_story_row.processing_flag = False
      user_story_row.ended_flag = (len_chapters_book == chapters_total)
      user_story_row.put()

      return jsonify({})

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class TqChatgptSummaryChapter(WebappHelper):
  def processOfRequest(self):
    try:
      chapter_id = self.request.get('chapter_id', None)
      logging.info("chapter_id=%s" % str(chapter_id))

      chapter_row = UCFMDLUserChapters.getInstance(chapter_id)
      book_id = chapter_row.book_id
      user_story_id = chapter_row.user_story_id
      len_chapters_user = chapter_row.chapter_number
      input_text_edit = chapter_row.user_content

      user_story_row = UCFMDLUserStories.getInstance(user_story_id)

      book_dict = UCFMDLBook.getDict(book_id)
      chapters = json.JSONDecoder().decode(book_dict['chapters'])
      len_chapters_book = len(chapters)

      message_history_summary = []
      if self._language in sateraito_func.ACTIVE_LANGUAGES:
        language_disp = self.getMsg(sateraito_func.LANGUAGES_MSGID.get(self._language, ''))
        message_history_summary.append({
          "role": "system",
          # "content": 'You must answer in %s only.' % language_disp
          "content": 'You must answer in Vietnamese only.'
        })
      input_text_edit_summary = "%s\n Tóm tắt còn %s ký tự" % (chapter_row.content, str(int(1500 / (len_chapters_book))))
      is_success, error_message, output_summary, message_history_summary = chatgpt_func_v2.callChatGPT(self, api_key, model, input_text_edit_summary, message_history_summary, False)
      if not is_success:
        logging.error(error_message)
        return self.send_error_response({
          'error_message': self.getMsg('ERROR_GPT'),
          'error_code': 400
        })

      chapter_row.assistant_content = output_summary
      chapter_row.status = 'complete'
      chapter_row.put()

      UCFMDLUserChapters.clearListInstanceCache(book_id, user_story_id)

      # Update user story
      chapters_total = UserChaptersUtils.countChapter(book_id, user_story_id)
      user_story_row.chapters_total = chapters_total
      user_story_row.processing_flag = False
      user_story_row.ended_flag = (len_chapters_book == chapters_total)
      user_story_row.put()

      return jsonify({})

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })


############################################################
# REQUEST FOR FAVORITES BOOK USERS
############################################################

class GetFavoriteBookUser(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      query = UCFMDLFavoritesBookUsers.query()
      query = query.filter(UCFMDLFavoritesBookUsers.user_id == self.viewer_email)
      query = query.order(-UCFMDLFavoritesBookUsers.created_date)
      results = query.fetch()

      data = []
      for row in results:
        book_dict = UCFMDLBook.getDict(row.book_id)
        if not book_dict or book_dict['del_flag']:
          continue
        if not BookUtils.accessBookDict(book_dict, viewer_email=self.viewer_email):
          continue

        data.append({
          'id': row.key.id(),
          'book_id': row.book_id,
          'user_id': row.user_id
        })

      ret_obj = data
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class AddFavoriteBookUser(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      book_id = request_json.get('book_id', '')

      book_dict = UCFMDLBook.getDict(book_id)
      if book_dict is None or book_dict['del_flag']:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })
      if not BookUtils.accessBookDict(book_dict, viewer_email=self.viewer_email):
        return self.send_error_response({
          'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION_BOOK'),
          'error_code': 403
        })

      if UCFMDLFavoritesBookUsers.isFavorite(self.viewer_email, book_id):
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_ALREADY_IN_FAVORITE'),
          'error_code': 400
        })

      new_row = UCFMDLFavoritesBookUsers()
      new_row.user_id = self.viewer_email
      new_row.book_id = book_id
      new_row.put()

      ret_obj = {
        'id': new_row.key.id(),
        'user_id': new_row.user_id,
        'book_id': new_row.book_id,
        'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(new_row.created_date, self._timezone)),
        'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(new_row.updated_date, self._timezone)),
      }

      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class RemoveFavoriteBookUser(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      favorite_id = request_json.get('favorite_id', '')
      book_id = request_json.get('book_id', '')

      # book_dict = UCFMDLBook.getDict(book_id)
      # if book_dict is None or book_dict['del_flag']:
      #   return self.send_error_response({
      #     'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
      #     'error_code': 400
      #   })

      favorite_row = UCFMDLFavoritesBookUsers.getInstance(favorite_id)
      if favorite_row is None:
        return self.send_error_response({
          'error_message': self.getMsg('NOT_FOUND'),
          'error_code': 400
        })

      favorite_row.delete(self.viewer_email, book_id)

      ret_obj = {
        'id': favorite_row.key.id(),
        'user_id': favorite_row.user_id,
        'book_id': favorite_row.book_id,
        'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(favorite_row.created_date, self._timezone)),
        'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(favorite_row.updated_date, self._timezone)),
      }

      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })


############################################################
# REQUEST FOR USER SHARED STORIES
############################################################

class AddUserSharedStories(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      type_share = request_json.get('type_share', '')
      book_id = request_json.get('book_id', '')
      user_story_id = request_json.get('user_story_id', None)
      user_chapter_id = request_json.get('user_chapter_id', None)
      message = request_json.get('message', '')
      user_id_share = request_json.get('user_id_share', '')

      book_dict = UCFMDLBook.getDict(book_id)
      if book_dict is None or book_dict['del_flag']:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })
      if not BookUtils.accessShareBookDict(book_dict, viewer_email=self.viewer_email):
        return self.send_error_response({
          'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION_SHARE_BOOK'),
          'error_code': 403
        })

      if type_share == sateraito_func.KEY_TYPE_STORY_SHARE:
        user_story_dict = UCFMDLUserStories.getDict(user_story_id)
        if user_story_dict is None or user_story_dict['del_flag']:
          return self.send_error_response({
            'error_message': self.getMsg('STORY_NOT_FOUND_OR_DELETED'),
            'error_code': 400
          })

        if type_share == sateraito_func.KEY_TYPE_CHAPTER_SHARE:
          user_chapter_dict = UCFMDLUserChapters.getDict(user_chapter_id)
          if user_chapter_dict is None or user_chapter_dict['del_flag']:
            return self.send_error_response({
              'error_message': self.getMsg('CHAPTER_NOT_FOUND_OR_DELETED'),
              'error_code': 400
            })

      # user_info_dict = UCFMDLUserInfo.getDict(user_id_share)
      # if user_info_dict['email'] and user_info_dict['email'] != '':
      #   user_id_add = user_info_dict['email']
      # else:
      #   user_id_add = user_info_dict['id']

      new_row = UCFMDLUserShareStories()
      new_row.type_share = type_share
      new_row.user_id = self.viewer_email
      new_row.book_id = book_id
      new_row.message = message
      new_row.user_id_shared = user_id_share
      new_row.user_story_id = user_story_id
      new_row.user_chapter_id = user_chapter_id
      new_row.put()

      UCFMDLUserShareStories.clearInstanceListUsersSharedCache(book_id, self.viewer_email, user_story_id, user_chapter_id, False, type_share)

      ret_obj = {
        'id': new_row.key.id(),
        'user_id': new_row.user_id,
        'book_id': new_row.book_id,
        'user_id_shared': new_row.user_id_shared,
        'user_story_id': new_row.user_story_id,
        'user_chapter_id': new_row.user_chapter_id,
        'created_date': UcfUtil.nvl(UcfUtil.getLocalTime(new_row.created_date, self._timezone)),
        'updated_date': UcfUtil.nvl(UcfUtil.getLocalTime(new_row.updated_date, self._timezone)),
      }

      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class RemoveUserSharedStories(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      user_share_id = request_json.get('user_share_id', '')

      shared_row = UCFMDLUserShareStories.getInstance(user_share_id)

      if shared_row is None:
        return self.send_error_response({
          'error_message': self.getMsg('SHARED_NOT_FOUND'),
          'error_code': 400
        })
      if shared_row.user_id_shared != self.viewer_email:
        return self.send_error_response({
          'error_message': self.getMsg('YOU_NOT_USER_SHARED'),
          'error_code': 403
        })

      shared_row.del_flag = True
      shared_row.put()
      UCFMDLUserShareStories.clearInstanceListUsersSharedCache(shared_row.book_id, shared_row.user_id, shared_row.user_story_id, shared_row.user_chapter_id, False, shared_row.type_share)

      ret_obj = {
        'status': 'success'
      }
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class ListStoriesSharedForMe(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      type_share = request_json.get('type_share', None)
      limit = int(request_json.get('limit', '500'))

      results = UCFMDLUserShareStories.getStoriesSharedFor(self.viewer_email, del_flag=False, type_share=type_share, limit=limit)
      logging.info(results)

      data_type_book = []
      data_type_story = []
      data_type_chapter = []

      for row in results:
        user_share = UCFMDLUserInfo.getDict(row.user_id)

        item = {
          'id': row.key.id(),
          'user_id': row.user_id,
          'user_share': {
            'id': user_share['id'],
            'email': user_share['email'],
            'avatar_url': user_share['avatar_url'],
            'nickname': user_share['nickname'],
            'gender': user_share['gender'],
            'date_of_birth': user_share['date_of_birth'],
            'description': user_share['description'],
            'lives_in': user_share['lives_in'],
            'come_from': user_share['come_from'],
            'works_at': user_share['works_at'],
            'website_url': user_share['website_url'],
            'twitter_url': user_share['twitter_url'],
            'facebook_url': user_share['facebook_url'],
            'instagram_url': user_share['instagram_url'],
            'linkedin_url': user_share['linkedin_url'],
            'fullname': user_share['fullname'],
            'family_name': user_share['family_name'],
            'given_name': user_share['given_name'],
            'language': user_share['language'],
          },
          'user_id_shared': row.user_id_shared,
          'message': row.message,
          'book_id': row.book_id,
          'user_story_id': row.user_story_id,
          'user_chapter_id': row.user_chapter_id,
          'created_date': UcfUtil.getLocalTime(row.created_date, sateraito_inc.DEFAULT_TIMEZONE).strftime('%Y/%m/%d %H:%M'),
          'updated_date': UcfUtil.getLocalTime(row.updated_date, sateraito_inc.DEFAULT_TIMEZONE).strftime('%Y/%m/%d %H:%M'),
        }

        book_dict = UCFMDLBook.getDict(row.book_id)
        # Check book dict empty or deleted
        is_skip = (book_dict is None) or book_dict['del_flag']
        if is_skip:
          # ignore book entry None or flag delete True
          continue

        if not BookUtils.accessBookDict(book_dict, viewer_email=self.viewer_email):
          # ignore book when user don't have permission into book
          continue

        creator_skill = []
        creator_dict = UCFMDLUserInfo.getDict(book_dict['creator_id'])
        if creator_dict['skill']:
          creator_skill = json.JSONDecoder().decode(creator_dict['skill'])

        characters = json.JSONDecoder().decode(book_dict['characters'])
        chapters = json.JSONDecoder().decode(book_dict['chapters'])

        images = json.JSONDecoder().decode(book_dict['images'])
        book_cover = json.JSONDecoder().decode(book_dict['book_cover'])

        item['book'] = {
          'id': book_dict['id'],
          'status': book_dict['status'],

          'book_cover': book_cover,
          'images': images,

          'title': book_dict['title'],
          'summary': book_dict['summary'],

          'total_join': book_dict['total_join'],
          'rate_star': book_dict['rate_star'],
          'total_comment': book_dict['total_comment'],

          'characters': characters,
          'chapter_limit': len(chapters),
          'chapters': chapters,

          'created_date': UcfUtil.getLocalTime(book_dict['created_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),
          'updated_date': UcfUtil.getLocalTime(book_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M'),

          'my_story': None,
          'my_stories_history': [],

          'category': {
            'id': book_dict['category_book_id'],
            'name': book_dict['category_book_name'],
          },
          'type_book': {
            'id': book_dict['type_book_id'],
            'name': book_dict['type_book_name'],
          },
          'creator': {
            'id': creator_dict['id'],
            'skill': creator_skill,
            'email': creator_dict['email'],
            'avatar_url': creator_dict['avatar_url'],
            'nickname': creator_dict['nickname'],
            'gender': creator_dict['gender'],
            'date_of_birth': creator_dict['date_of_birth'],
            'description': creator_dict['description'],
            'lives_in': creator_dict['lives_in'],
            'come_from': creator_dict['come_from'],
            'works_at': creator_dict['works_at'],
            'website_url': creator_dict['website_url'],
            'twitter_url': creator_dict['twitter_url'],
            'facebook_url': creator_dict['facebook_url'],
            'instagram_url': creator_dict['instagram_url'],
            'linkedin_url': creator_dict['linkedin_url'],
            'fullname': creator_dict['fullname'],
            'family_name': creator_dict['family_name'],
            'given_name': creator_dict['given_name'],
            'language': creator_dict['language'],

            'followers': creator_dict['followers'],
            'following': creator_dict['following'],
          }
        }

        # For book
        if row.type_share == sateraito_func.KEY_TYPE_BOOK_SHARE:
          data_type_book.append(item)

        # For story
        elif row.type_share == sateraito_func.KEY_TYPE_STORY_SHARE:
          item['story'] = UserStoriesUtils.getStorySharedById(row.book_id, row.user_story_id)
          data_type_story.append(item)

        # For chapter
        elif row.type_share == sateraito_func.KEY_TYPE_CHAPTER_SHARE:
          item['story'] = UserStoriesUtils.getStorySharedById(row.book_id, row.user_story_id)

          row_dict = UCFMDLUserChapters.getDict(row.user_chapter_id)
          row_dict['created_date'] = UcfUtil.getLocalTime(row_dict['created_date'], sateraito_inc.DEFAULT_TIMEZONE).strftime('%Y/%m/%d %H:%M')
          row_dict['updated_date'] = UcfUtil.getLocalTime(row_dict['updated_date'], sateraito_inc.DEFAULT_TIMEZONE).strftime('%Y/%m/%d %H:%M')
          item['chapter'] = row_dict
          data_type_chapter.append(item)

      ret_obj = {}
      if type_share is None:
        ret_obj = {
          'data_type_book': data_type_book,
          'data_type_story': data_type_story,
          'data_type_chapter': data_type_chapter,
        }
      elif type_share == sateraito_func.KEY_TYPE_BOOK_SHARE:
        ret_obj = data_type_book
      elif type_share == sateraito_func.KEY_TYPE_STORY_SHARE:
        ret_obj = data_type_story
      elif type_share == sateraito_func.KEY_TYPE_CHAPTER_SHARE:
        ret_obj = data_type_chapter

      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class GetUserSharedStoriesById(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      user_share_id = request_json.get('user_share_id', None)

      result_dict = UCFMDLUserShareStories.getDict(user_share_id)

      if result_dict['user_id_shared'] != self.viewer_email:
        return self.send_error_response({
          'error_message': self.getMsg('DO_NOT_HAVE_PERMISSION'),
          'error_code': '',
          'param': '',
        })

      result_dict['created_date'] = UcfUtil.getLocalTime(result_dict['created_date'], sateraito_inc.DEFAULT_TIMEZONE).strftime('%Y/%m/%d %H:%M'),
      result_dict['updated_date'] = UcfUtil.getLocalTime(result_dict['updated_date'], sateraito_inc.DEFAULT_TIMEZONE).strftime('%Y/%m/%d %H:%M'),

      user_share = UCFMDLUserInfo.getDict(result_dict['user_id'])
      result_dict['user_share'] = {
        'id': user_share['id'],
        'email': user_share['email'],
        'avatar_url': user_share['avatar_url'],
        'nickname': user_share['nickname'],
        'gender': user_share['gender'],
        'date_of_birth': user_share['date_of_birth'],
        'description': user_share['description'],
        'lives_in': user_share['lives_in'],
        'come_from': user_share['come_from'],
        'works_at': user_share['works_at'],
        'website_url': user_share['website_url'],
        'twitter_url': user_share['twitter_url'],
        'facebook_url': user_share['facebook_url'],
        'instagram_url': user_share['instagram_url'],
        'linkedin_url': user_share['linkedin_url'],
        'fullname': user_share['fullname'],
        'family_name': user_share['family_name'],
        'given_name': user_share['given_name'],
        'language': user_share['language'],
      }

      ret_obj = result_dict
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })


############################################################
# REQUEST FOR FEEDBACK BOOK USERS
############################################################

class GetListFeedbackBookUsersByBookID(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      self.checkLogin().get('status')

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      book_id = request_json.get('book_id')
      page_size = request_json.get('page_size', 100)
      page_cursor = request_json.get('page_cursor', None)
      type_feedback = request_json.get('type_feedback', sateraito_inc.KEY_FEEDBACK_TYPE_BOOK)
      if page_cursor is not None:
        page_cursor = Cursor(urlsafe=page_cursor)

      book_dict = UCFMDLBook.getDict(book_id)
      if book_dict is None:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })

      query = UCFMDLFeedbackBookUsers.query()
      query = query.filter(UCFMDLFeedbackBookUsers.book_id == book_id)
      query = query.filter(UCFMDLFeedbackBookUsers.type_feedback == type_feedback)
      query = query.order(-UCFMDLFeedbackBookUsers.updated_date)

      # Fetch the next page of results using the cursor
      if page_cursor is not None:
        results, next_cursor, have_more_row = query.fetch_page(page_size, start_cursor=page_cursor)
      else:
        results, next_cursor, have_more_row = query.fetch_page(page_size)
      logging.info("next_cursor=%s" % str(next_cursor))
      logging.info("have_more_row=%s" % str(have_more_row))

      data_res = []
      for row in results:
        row_dict = row.to_dict()

        row_dict['id'] = row.key.id()
        user_dict = UCFMDLUserInfo.getDict(row_dict["user_id"])

        row_dict['user_create'] = {
          'id': user_dict['id'],
          'email': user_dict['email'],
          'avatar_url': user_dict['avatar_url'],
          'nickname': user_dict['nickname'],
          'fullname': user_dict['fullname'],
          'language': user_dict['language'],
        }

        row_dict['created_date'] = UcfUtil.getLocalTime(row_dict['created_date'], self._timezone).strftime('%Y/%m/%d %H:%M')
        row_dict['updated_date'] = UcfUtil.getLocalTime(row_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M')

        data_res.append(row_dict)

      # Store the next cursor for the next page
      next_cursor = next_cursor.urlsafe().decode('utf-8') if next_cursor else None
      logging.info("next_cursor=%s" % str(next_cursor))

      return self.send_success_response({
        "results": data_res,
        "have_more_row": have_more_row,
        "next_cursor": next_cursor,
      })

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })


############################################################
# REQUEST FOR STORIES USERS JOINED
############################################################

class GetListUserJoinedBookByBookID(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      request_json = json.JSONDecoder().decode(request.get_data().decode())

      # get params
      book_id = request_json.get('book_id')
      page_size = request_json.get('page_size', 100)
      page_cursor = request_json.get('page_cursor', None)
      if page_cursor is not None:
        page_cursor = Cursor(urlsafe=page_cursor)

      book_dict = UCFMDLBook.getDict(book_id)
      if book_dict is None:
        return self.send_error_response({
          'error_message': self.getMsg('BOOK_NOT_FOUND_OR_DELETED'),
          'error_code': 400
        })

      query = UCFMDLStoriesUsersJoined.query()
      query = query.filter(UCFMDLStoriesUsersJoined.book_id == book_id)
      query = query.order(-UCFMDLStoriesUsersJoined.created_date)

      # Fetch the next page of results using the cursor
      if page_cursor is not None:
        results, next_cursor, have_more_row = query.fetch_page(page_size, start_cursor=page_cursor)
      else:
        results, next_cursor, have_more_row = query.fetch_page(page_size)
      logging.info("next_cursor=%s" % str(next_cursor))
      logging.info("have_more_row=%s" % str(have_more_row))

      data_res = []
      for row in results:
        row_dict = row.to_dict()

        row_dict['id'] = row.key.id()
        user_dict = UCFMDLUserInfo.getDict(row_dict["user_id"])

        row_dict['user_create'] = {
          'id': user_dict['id'],
          'email': user_dict['email'],
          'avatar_url': user_dict['avatar_url'],
          'nickname': user_dict['nickname'],
          'fullname': user_dict['fullname'],
          'language': user_dict['language'],
        }

        row_dict['created_date'] = UcfUtil.getLocalTime(row_dict['created_date'], self._timezone).strftime('%Y/%m/%d %H:%M')
        row_dict['updated_date'] = UcfUtil.getLocalTime(row_dict['updated_date'], self._timezone).strftime('%Y/%m/%d %H:%M')

        data_res.append(row_dict)

      # Store the next cursor for the next page
      next_cursor = next_cursor.urlsafe().decode('utf-8') if next_cursor else None
      logging.info("next_cursor=%s" % str(next_cursor))

      return self.send_success_response({
        "results": data_res,
        "have_more_row": have_more_row,
        "next_cursor": next_cursor,
      })

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })


############################################################
# REQUEST FOR KEY REGISTER EMAIL
############################################################

class SendMailRegisterAccount(WebappHelper):

  def processOfRequest(self):
    try:
      self._approot_path = os.path.dirname(__file__)

      # get params
      request_json = json.JSONDecoder().decode(request.get_data().decode())

      email = request_json.get('email_register', '').strip()
      if email == '':
        return self.send_error_response({
          'error_message': self.getMsg('PARAMS_INVALIDATE'),
          'error_code': 'email_register',
          'param': 'email_register',
        })

      if sateraito_func.UserEntry.getInstance(email):
        return self.send_error_response({
          'error_message': self.getMsg('EMAIL_HAS_REGISTERED'),
          'error_code': 'had_email_register',
          'param': 'had_email_register',
        })

      register_token = UCFMDLKeyRegisterEmail.create_register_token(email)
      subject = self.getMsg('REGISTER_SEND_MAIL_SUBJECT_TITLE')
      url = sateraito_inc.my_site_url + '/auth/%s/register' % str(register_token)
      template_vals = {
        'url': url,
        'title': subject,
        'my_site_url': sateraito_inc.my_site_url,
      }

      self.appendBasicInfoToTemplateVals(template_vals)
      emailBody = self.render_template('auth_register.html', self._design_type, template_vals)
      sateraito_mail.sendMail(email, subject, emailBody, is_html=True)

      ret_obj = {
      }
      self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      self.redirectError(UcfMessage.getMessage(self.getMsg('MSG_SYSTEM_ERROR'), ()))
      return

class CheckTokenRegisterAccount(WebappHelper):

  def processOfRequest(self):
    try:
      self._approot_path = os.path.dirname(__file__)

      # get params
      request_json = json.JSONDecoder().decode(request.get_data().decode())

      register_token = request_json.get('register_token', '').strip()
      if register_token == '':
        return self.send_error_response({
          'error_message': self.getMsg('PARAMS_INVALIDATE'),
          'error_code': 'register_token',
          'param': 'register_token',
        })

      token_ok, row = UCFMDLKeyRegisterEmail.check_register_token(register_token)
      if not token_ok or row is None:
        return self.send_error_response({
          'error_message': self.getMsg('PARAMS_INVALIDATE'),
          'error_code': 'register_token_invalidate',
          'param': 'register_token_invalidate',
        })

      ret_obj = {
        'register_token': register_token,
        'register_email': row.email,
      }
      self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      self.redirectError(UcfMessage.getMessage(self.getMsg('MSG_SYSTEM_ERROR'), ()))
      return

class RegisterAccountByToken(WebappHelper):

  def processOfRequest(self, register_token):
    try:
      self._approot_path = os.path.dirname(__file__)

      token_ok, row = UCFMDLKeyRegisterEmail.check_register_token(register_token)
      if not token_ok or row is None:
        return self.send_error_response({
          'error_message': self.getMsg('PARAMS_INVALIDATE'),
          'error_code': 'register_token_invalidate',
          'param': 'register_token_invalidate',
        })

      viewer_email = row.email

      user_entry = sateraito_func.UserEntry.getInstance(viewer_email)
      if user_entry:
        return self.send_error_response({
          'error_message': self.getMsg('USER_ENTRY_HAD_REGISTERED'),
          'error_code': 400
        })

      # get params
      request_json = json.JSONDecoder().decode(request.get_data().decode())

      if register_token != request_json.get('register_token'):
        return self.send_error_response({
          'error_message': self.getMsg('REGISTER_TOKEN_INVALIDATE'),
          'error_code': 400
        })

      password = request_json.get('password')
      user_entry = sateraito_func.registUserEntryWithUsernamePassword(viewer_email, viewer_email, password)
      if user_entry:

        u_info_entry = UCFMDLUserInfo()
        u_info_entry.be_registered = True
        u_info_entry.email = viewer_email
        u_info_entry.user_entry_id = user_entry.key.id()
        u_info_entry.avatar_url = sateraito_inc.my_site_url + '/images/sateraito.png'

        given_name = request_json.get('given_name')
        if given_name and given_name != u_info_entry.given_name:
          u_info_entry.given_name = given_name

        family_name = request_json.get('family_name')
        if family_name and family_name != u_info_entry.family_name:
          u_info_entry.family_name = family_name

        fullname = request_json.get('fullname')
        if fullname and fullname != u_info_entry.fullname:
          u_info_entry.fullname = fullname

        language = request_json.get('language')
        if language and language != u_info_entry.language:
          u_info_entry.language = language

        skill = request_json.get('skill')
        if skill and skill != u_info_entry.skill:
          u_info_entry.skill = skill

        nickname = request_json.get('nickname')
        if nickname and nickname != u_info_entry.nickname:
          u_info_entry.nickname = nickname

        date_of_birth = request_json.get('date_of_birth')
        if date_of_birth and date_of_birth != u_info_entry.date_of_birth:
          u_info_entry.date_of_birth = date_of_birth

        gender = request_json.get('gender')
        if gender and gender != u_info_entry.gender:
          u_info_entry.gender = gender

        description = request_json.get('description')
        if description and description != u_info_entry.description:
          u_info_entry.description = description

        lives_in = request_json.get('lives_in')
        if lives_in and lives_in != u_info_entry.lives_in:
          u_info_entry.lives_in = lives_in

        come_from = request_json.get('come_from')
        if come_from and come_from != u_info_entry.come_from:
          u_info_entry.come_from = come_from

        works_at = request_json.get('works_at')
        if works_at and works_at != u_info_entry.works_at:
          u_info_entry.works_at = works_at

        website_url = request_json.get('website_url')
        if website_url and website_url != u_info_entry.website_url:
          u_info_entry.website_url = website_url

        twitter_url = request_json.get('twitter_url')
        if twitter_url and twitter_url != u_info_entry.twitter_url:
          u_info_entry.twitter_url = twitter_url

        facebook_url = request_json.get('facebook_url')
        if facebook_url and facebook_url != u_info_entry.facebook_url:
          u_info_entry.facebook_url = facebook_url

        instagram_url = request_json.get('instagram_url')
        if instagram_url and instagram_url != u_info_entry.instagram_url:
          u_info_entry.instagram_url = instagram_url

        linkedin_url = request_json.get('linkedin_url')
        if linkedin_url and linkedin_url != u_info_entry.linkedin_url:
          u_info_entry.linkedin_url = linkedin_url

        # Save
        u_info_entry.put()

        # Add row user info to Text Search
        UserInfoUtils.rebuildTextSearchIndex(u_info_entry)

        # Update flag revoke of register token
        UCFMDLKeyRegisterEmail.revoke_register_token(register_token)

      ret_obj = {
        'success': True,
      }
      self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      self.redirectError(UcfMessage.getMessage(self.getMsg('MSG_SYSTEM_ERROR'), ()))
      return


############################################################
# REQUEST FOR USER CONFIG
############################################################
class UserGetConfig(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      uid = self.viewer_email
      logging.info('uid=%s' % (uid))

      theme_config_default = '{"theme":"light","skinColor":"#9c27b0","layout":"material","position":"left","behavior":"sticky"}'
      theme_config = ''

      row_dict = UCFMDLUserConfig.get_dict(uid)
      if row_dict:
        if row_dict['theme_config'] and row_dict['theme_config'] != '{}':
          theme_config = row_dict['theme_config']
        else:
          q = UCFMDLUserConfig.query()
          q = q.filter(UCFMDLUserConfig.user_id == uid)
          entry = q.get()

          entry.theme_config = theme_config_default
          entry.put()

          theme_config = theme_config_default

      ret_obj = {
        'theme_config': json.JSONDecoder().decode(theme_config),
      }
      return self.send_success_response(ret_obj)

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })

class UserUpdateConfig(WebappHelper):
  def processOfRequest(self):
    try:
      # check login
      if not self.checkLogin().get('status'):
        return self.responseError403()

      uid = self.viewer_email
      logging.info('uid=%s' % (uid))

      request_json = json.JSONDecoder().decode(request.get_data().decode())
      # get params
      theme_config = request_json.get('theme_config', '{}')

      q = UCFMDLUserConfig.query()
      q = q.filter(UCFMDLUserConfig.user_id == uid)
      entry = q.get()
      # ボードの存在チェック
      if not entry:
        unique_id = UcfUtil.guid()
        entry = UCFMDLUserConfig(unique_id=unique_id)
        entry.user_id = uid

      if 'theme_config' in request_json:
        entry.theme_config = theme_config
      entry.put()

      if 'locale' in request_json:
        user_info_row = UCFMDLUserInfo.getInstance(uid)
        user_info_row.language = request_json.get('locale', sateraito_inc.DEFAULT_LANGUAGE)
        user_info_row.put()

      return self.send_success_response({
        "result": "success",
      })

    except BaseException as e:
      self.outputErrorLog(e)
      return self.send_error_response({
        'error_message': 'MSG_SYSTEM_ERROR',
        'error_code': 999
      })


class ReuqestTodoSomething(WebappHelper):
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
  app.add_url_rule('/', view_func=IndexPage.as_view(__name__ + '.IndexPage'))
  app.add_url_rule('/book/<book_id>', view_func=DetailBookPage.as_view(__name__ + '.DetailBookPage'))
  app.add_url_rule('/<path:path>', view_func=BasePage.as_view(__name__ + '.BasePage'))

  # ============ URL API ============

  # For /auth/<request_action>
  app.add_url_rule('/api/auth/get-info', view_func=AuthGetInfo.as_view(__name__ + '.AuthGetInfo'))
  app.add_url_rule('/api/auth/get-info-by-id', view_func=AuthGetInfoById.as_view(__name__ + '.AuthGetInfoById'))
  app.add_url_rule('/api/auth/set-info', view_func=AuthSetInfo.as_view(__name__ + '.AuthSetInfo'))
  app.add_url_rule('/api/auth/set-role', view_func=AuthSetRole.as_view(__name__ + '.AuthSetRole'))
  app.add_url_rule('/api/auth/set-language', view_func=AuthSetLanguage.as_view(__name__ + '.AuthSetLanguage'))
  app.add_url_rule('/api/auth/add-follower', view_func=AuthAddFollower.as_view(__name__ + '.AuthAddFollower'))
  app.add_url_rule('/api/auth/remove-follower', view_func=AuthRemoveFollower.as_view(__name__ + '.AuthRemoveFollower'))
  app.add_url_rule('/api/auth/search', view_func=SearchUserInfo.as_view(__name__ + '.SearchUserInfo'))
  app.add_url_rule('/api/auth/admin-search-userinfo', view_func=AdminSearchUserInfo.as_view(__name__ + '.AdminSearchUserInfo'))
  app.add_url_rule('/api/auth/admin-search-account', view_func=AdminSearchUserEntry.as_view(__name__ + '.AdminSearchUserEntry'))
  app.add_url_rule('/api/auth/admin-set-disable-account', view_func=AdminSetDisableUserEntry.as_view(__name__ + '.AdminSetDisableUserEntry'))
  app.add_url_rule('/api/auth/send-mail-register-account',  view_func=SendMailRegisterAccount.as_view(__name__ + '.SendMailRegisterAccount'))

  # For /type-book/<request_action>
  app.add_url_rule('/api/type-book/add', view_func=AddTypeBook.as_view(__name__ + '.TypeBookAdd'))
  app.add_url_rule('/api/type-book/edit', view_func=EditTypeBook.as_view(__name__ + '.EditTypeBook'))
  app.add_url_rule('/api/type-book/remove', view_func=RemoveTypeBook.as_view(__name__ + '.TypeBookRemove'))
  app.add_url_rule('/api/type-book/remove-multiple', view_func=RemoveMultipleTypeBook.as_view(__name__ + '.RemoveMultipleTypeBook'))
  app.add_url_rule('/api/type-book/all', view_func=GetAllTypeBook.as_view(__name__ + '.TypeBookGetAll'))
  app.add_url_rule('/api/type-book/just-type-book', view_func=GetAllJustTypeBook.as_view(__name__ + '.GetAllJustTypeBook'))
  app.add_url_rule('/api/type-book/categories-by-type-book', view_func=GetAllCategoriesByTypeBook.as_view(__name__ + '.GetAllCategoriesByTypeBook'))
  app.add_url_rule('/api/type-book/type-with-category', view_func=GetTypeAndCategoryBook.as_view(__name__ + '.GetTypeAndCategoryBook'))

  # For /book/<request_action>
  app.add_url_rule('/api/book/create', view_func=CreateBook.as_view(__name__ + '.CreateBook'))
  app.add_url_rule('/api/book/edit', view_func=EditBook.as_view(__name__ + '.EditBook'))
  app.add_url_rule('/api/book/delete', view_func=DeleteBook.as_view(__name__ + '.DeleteBook'))
  app.add_url_rule('/api/book/get-by-id/<book_id>', view_func=GetBookById.as_view(__name__ + '.GetBookById'))
  app.add_url_rule('/api/book/search', view_func=SearchBook.as_view(__name__ + '.SearchBook'))
  app.add_url_rule('/api/book/get-by-favorite', view_func=GetBookByFavorite.as_view(__name__ + '.GetBookByFavorite'))
  app.add_url_rule('/api/book/get-by-recently-read', view_func=GetBookByRecentlyRead.as_view(__name__ + '.GetBookByRecentlyRead'))
  app.add_url_rule('/api/book/get-my-created', view_func=GetMyBookCreated.as_view(__name__ + '.GetMyBookCreated'))
  app.add_url_rule('/api/book/get-of-user', view_func=GetBookByUserEntryId.as_view(__name__ + '.GetBookByUserEntryId'))
  app.add_url_rule('/api/book/admin-search', view_func=AdminSearchBook.as_view(__name__ + '.AdminSearchBook'))
  app.add_url_rule('/api/book/set-feedback', view_func=SetFeedbackUserBook.as_view(__name__ + '.SetFeedbackUserBook'))
  app.add_url_rule('/api/book/send-mail-notifica-follower-creator', view_func=SendMailNotificaFollowerCreator.as_view(__name__ + '.SendMailNotificaFollowerCreator'))

  # For /user-stories/<request_action>
  app.add_url_rule('/api/user-stories/create', view_func=CreateUserStory.as_view(__name__ + '.CreateUserStory'))
  app.add_url_rule('/api/user-stories/update', view_func=UpdateUserStory.as_view(__name__ + '.UpdateUserStory'))
  app.add_url_rule('/api/user-stories/feedback', view_func=SetFeedbackUserStory.as_view(__name__ + '.SetFeedbackUserStory'))
  app.add_url_rule('/api/user-stories/change-to-history', view_func=ChangeToHistoryUserStory.as_view(__name__ + '.ChangeToHistoryUserStory'))
  app.add_url_rule('/api/user-stories/get-by-id/<book_id>/<user_story_id>', view_func=GetUserStoryById.as_view(__name__ + '.GetUserStoryById'))
  app.add_url_rule('/api/user-stories/list-stories-join-my-book', view_func=ListStoriesJoinMyBook.as_view(__name__ + '.ListStoriesJoinMyBook'))
  app.add_url_rule('/api/user-stories/get-process/<user_story_id>', view_func=GetProcessStoryUserById.as_view(__name__ + '.GetProcessStoryUserById'))

  # For /user-chapters/<request_action>
  app.add_url_rule('/api/user-chapters/get-by-id', view_func=GetUserChapterById.as_view(__name__ + '.GetUserChapterById'))
  app.add_url_rule('/api/user-chapters/add', view_func=AddUserChapter.as_view(__name__ + '.AddUserChapter'))
  app.add_url_rule('/api/user-chapters/set-feedback', view_func=SetFeedbackUserChapter.as_view(__name__ + '.SetFeedbackUserChapter'))
  app.add_url_rule('/api/user-chapters/get-preview', view_func=GetUserChapterPreview.as_view(__name__ + '.GetUserChapterPreview'))
  app.add_url_rule('/api/tq/user-chapters/chatgpt-create-chapter-with-stream', view_func=TqChatgptCreateChapterWithStream.as_view(__name__ + '.TqChatgptCreateChapterWithStream'))
  app.add_url_rule('/api/tq/user-chapters/chatgpt-summary-chapter', view_func=TqChatgptSummaryChapter.as_view(__name__ + '.TqChatgptSummaryChapter'))

  # For /user-favorites/<request_action>
  app.add_url_rule('/api/favorites-book-user/get-all', view_func=GetFavoriteBookUser.as_view(__name__ + '.GetFavoriteBookUser'))
  app.add_url_rule('/api/favorites-book-user/add', view_func=AddFavoriteBookUser.as_view(__name__ + '.AddFavoriteBookUser'))
  app.add_url_rule('/api/favorites-book-user/remove', view_func=RemoveFavoriteBookUser.as_view(__name__ + '.RemoveFavoriteBookUser'))

  # For /user-shared/<request_action>
  app.add_url_rule('/api/user-shared/add', view_func=AddUserSharedStories.as_view(__name__ + '.AddUserSharedStories'))
  app.add_url_rule('/api/user-shared/remove', view_func=RemoveUserSharedStories.as_view(__name__ + '.RemoveUserSharedStories'))
  app.add_url_rule('/api/user-shared/get-by-id', view_func=GetUserSharedStoriesById.as_view(__name__ + '.GetUserSharedStoriesById'))
  app.add_url_rule('/api/user-shared/list-for-me', view_func=ListStoriesSharedForMe.as_view(__name__ + '.ListStoriesSharedForMe'))

  # For /feedback-book-users/<request_action>
  app.add_url_rule('/api/feedback-book-users/get-by-book-id', view_func=GetListFeedbackBookUsersByBookID.as_view(__name__ + '.GetListFeedbackBookUsersByBookID'))

  # For /stories-user-joined/<request_action>
  app.add_url_rule('/api/stories-user-joined/get-by-book-id', view_func=GetListUserJoinedBookByBookID.as_view(__name__ + '.GetListUserJoinedBookByBookID'))

  # For /key-register-email/<request_action>
  app.add_url_rule('/api/key-register-email/check-token-register-account', view_func=CheckTokenRegisterAccount.as_view(__name__ + '.CheckTokenRegisterAccount'))
  app.add_url_rule('/api/key-register-email/<register_token>/register-account', view_func=RegisterAccountByToken.as_view(__name__ + '.RegisterAccountByToken'))

  # For /user-config/<request_action>
  app.add_url_rule('/api/user-config/get', view_func=UserGetConfig.as_view(__name__ + '.UserGetConfig'))
  app.add_url_rule('/api/user-config/set', view_func=UserUpdateConfig.as_view(__name__ + '.UserUpdateConfig'))

  app.add_url_rule('/api/req-todo-something', view_func=ReuqestTodoSomething.as_view(__name__ + '.ReuqestTodoSomething'))
