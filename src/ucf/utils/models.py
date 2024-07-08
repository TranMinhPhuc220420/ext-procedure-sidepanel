# coding: utf-8

import os, sys, datetime, logging, json
import string
from dateutil import zoneinfo, tz

from google.appengine.ext import db
from google.appengine.ext import ndb
# GAEGEN2対応:検索API移行
from google.appengine.api import search
# from search_alt import search_auto
# from search_alt import search_replace as search
from google.appengine.api import namespace_manager
from google.appengine.api import memcache
from ucf.config.ucfconfig import *
from ucf.utils.ucfutil import *

import sateraito_inc
import sateraito_func

REGISTER_TOKEN_EXPIRE_SECONDS = 12 * 60 * 60
REGISTER_TOKEN_LENGTH = 64


############################################################
## モデルクラス群（モデルごとにファイル分けたほうがいいかな？import面倒？）
############################################################

############################################################
## モデル：親クラス
############################################################
class UCFModel(db.Model):

  @classmethod
  def getByKey(cls, key):
    entity = None
    if key is not None:
      if key.name() is not None:
        entity = cls.get_by_key_name(key.name())
      elif key.id() is not None:
        entity = cls.get_by_id(key.id())
    return entity

  def exchangeVo(self, timezone):
    u''' db.ModelデータをVoデータ(ハッシュ)に変換 '''
    vo = {}
    for prop in self.properties().values():
      if prop.get_value_for_datastore(self) != None:
        # リスト型
        if prop.name in self.getListTypes():
          # GAEGEN2対応
          # vo[prop.name] = unicode(UcfUtil.listToCsv(prop.get_value_for_datastore(self)))
          vo[prop.name] = UcfUtil.listToCsv(prop.get_value_for_datastore(self))
        # 日付型
        elif prop.name in self.getDateTimeTypes():
          # GAEGEN2対応
          # vo[prop.name] = unicode(prop.get_value_for_datastore(self))
          vo[prop.name] = prop.get_value_for_datastore(self)
          # LocalTime対応（標準時刻からローカル時間に戻して表示に適切な形式に変換）
          vo[prop.name] = UcfUtil.nvl(UcfUtil.getLocalTime(UcfUtil.getDateTime(vo[prop.name]), timezone))
        else:
          # GAEGEN2対応
          # vo[prop.name] = unicode(prop.get_value_for_datastore(self))
          vo[prop.name] = prop.get_value_for_datastore(self)
      else:
        vo[prop.name] = ''
    return vo

  def margeFromVo(self, vo, timezone):
    u''' db.ModelデータにVoデータ(ハッシュ)をマージ '''
    for prop in self.properties().values():
      if prop.name not in ('unique_id', 'date_created', 'date_changed'):
        if prop.name in vo:
          try:
            # 数値型
            if prop.name in self.getNumberTypes():
              prop.__set__(self, prop.make_value_from_datastore(int(vo[prop.name]) if vo[prop.name] != '' else 0))
            # Bool型
            elif prop.name in self.getBooleanTypes():
              prop.__set__(self, prop.make_value_from_datastore(True if vo[prop.name] == 'True' else False))
            # 日付型
            elif prop.name in self.getDateTimeTypes():
              if UcfUtil.nvl(vo[prop.name]) != '':
                #							prop.__set__(self, prop.make_value_from_datastore(UcfUtil.getDateTime(vo[prop.name])))
                prop.__set__(self, prop.make_value_from_datastore(
                  UcfUtil.getUTCTime(UcfUtil.getDateTime(vo[prop.name]), timezone)))
              else:
                prop.__set__(self, prop.make_value_from_datastore(None))
            # リスト型
            elif prop.name in self.getListTypes():
              prop.__set__(self, UcfUtil.csvToList(vo[prop.name]))
            # Blob型
            elif prop.name in self.getBlobTypes():
              # prop.__set__(self, vo[prop.name])
              pass
            # References型
            elif prop.name in self.getReferencesTypes():
              pass
            else:
              # prop.__set__(self, prop.make_value_from_datastore(unicode(vo[prop.name])))
              prop.__set__(self, prop.make_value_from_datastore(vo[prop.name]))
          except BaseException as e:
            raise Exception('[' + prop.name + '=' + vo[prop.name] + ']' + str(e))

  def getReferenceData(self):
    u''' 参照データの情報をUcfDataリストとして返す（抽象メソッド） '''
    # TODO 自動判別したい
    return []

  def getNumberTypes():
    u''' 数値型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
    # TODO 自動判別したい
    return []

  getNumberTypes = staticmethod(getNumberTypes)

  def getBooleanTypes():
    u''' Bool型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
    # TODO 自動判別したい
    return []

  getBooleanTypes = staticmethod(getBooleanTypes)

  def getListTypes():
    u''' リスト型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
    # TODO 自動判別したい
    return []

  getListTypes = staticmethod(getListTypes)

  def getDateTimeTypes():
    u''' DateTime型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
    # TODO 自動判別したい
    return []

  getDateTimeTypes = staticmethod(getDateTimeTypes)

  def getBlobTypes():
    u''' Blobフィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
    # TODO 自動判別したい
    return []

  getBlobTypes = staticmethod(getBlobTypes)

  def getReferencesTypes():
    u''' 参照型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
    # TODO 自動判別したい
    return []

  getReferencesTypes = staticmethod(getReferencesTypes)


############################################################
## モデル：親クラス
############################################################
class UCFModel2(ndb.Model):
  NDB_MEMCACHE_TIMEOUT = (60 * 60 * 24 * 2)

  @classmethod
  def getByKey(cls, key):
    entity = None
    if key is not None:
      entity = key.get()
    return entity

  def exchangeVo(self, timezone):
    u''' ndb.ModelデータをVoデータ(ハッシュ)に変換 '''
    vo = self.to_dict()
    logging.debug(vo)
    for k, v in vo.items():
      if v is not None:
        # リスト型
        if k in self.getListTypes():
          # vo[k] = unicode(UcfUtil.listToCsv(v))
          vo[k] = UcfUtil.listToCsv(v)
        # 日付型
        elif k in self.getDateTimeTypes():
          # LocalTime対応（標準時刻からローカル時間に戻して表示に適切な形式に変換）
          vo[k] = UcfUtil.nvl(UcfUtil.getLocalTime(UcfUtil.getDateTime(v), timezone))
        else:
          # GAEGEN2対応
          # vo[k] = v
          vo[k] = v.decode() if isinstance(v, bytes) else v
      else:
        vo[k] = ''
    return vo

  def margeFromVo(self, vo, timezone):
    u''' ndb.ModelデータにVoデータ(ハッシュ)をマージ '''
    for prop in self._properties.values():
      # GAEGEN2対応
      # prop_name = prop._name
      prop_name = prop._name.decode()
      if prop_name not in ['unique_id', 'date_created', 'date_changed']:
        if prop_name in vo:
          try:
            # 数値型
            if isinstance(prop, ndb.IntegerProperty):
              # GAEGEN2対応:ついでにsetattrに変更
              # prop.__set__(self, int(vo[prop_name]) if vo[prop_name] != '' else 0)
              setattr(self, prop_name, int(vo[prop_name]) if vo[prop_name] != '' else 0)
            # 小数型
            elif isinstance(prop, ndb.FloatProperty):
              # GAEGEN2対応:ついでにsetattrに変更
              # prop.__set__(self, float(vo[prop_name]) if vo[prop_name] != '' else 0)
              setattr(self, prop_name, float(vo[prop_name]) if vo[prop_name] != '' else 0)
            # Bool型
            elif isinstance(prop, ndb.BooleanProperty):
              # GAEGEN2対応:ついでにsetattrに変更
              # prop.__set__(self, True if vo[prop_name] == 'True' else False)
              setattr(self, prop_name, True if vo[prop_name] == 'True' else False)
            # 日付型
            elif isinstance(prop, ndb.DateTimeProperty):
              if UcfUtil.nvl(vo[prop_name]) != '':
                # GAEGEN2対応:ついでにsetattrに変更
                # prop.__set__(self, UcfUtil.getUTCTime(UcfUtil.getDateTime(vo[prop_name]), timezone))
                setattr(self, prop_name, UcfUtil.getUTCTime(UcfUtil.getDateTime(vo[prop_name]), timezone))
              else:
                # GAEGEN2対応:ついでにsetattrに変更
                # prop.__set__(self, None)
                setattr(self, prop_name, None)
            # リスト型（String）
            elif isinstance(prop, ndb.StringProperty) and prop._repeated:
              # GAEGEN2対応:ついでにsetattrに変更
              # prop.__set__(self, UcfUtil.csvToList(vo[prop_name]))
              setattr(self, prop_name, UcfUtil.csvToList(vo[prop_name]))
            # String型
            elif isinstance(prop, ndb.StringProperty):
              # GAEGEN2対応:ついでにsetattrに変更
              # prop.__set__(self, unicode(vo[prop_name]))
              setattr(self, prop_name, vo[prop_name])
            # Text型
            elif isinstance(prop, ndb.TextProperty):
              # GAEGEN2対応:ついでにsetattrに変更
              # prop.__set__(self, unicode(vo[prop_name]))
              setattr(self, prop_name, vo[prop_name])
            # Blob型
            elif isinstance(prop, ndb.BlobProperty):
              # prop.__set__(self, vo[prop_name])
              pass
            ## References型
            # elif prop_name in self.getReferencesTypes():
            #	pass
            else:
              # prop.__set__(self, unicode(vo[prop_name]))
              prop.__set__(self, vo[prop_name])
          except BaseException as e:
            raise Exception('[' + prop_name + '=' + vo[prop_name] + ']' + str(e))

  def getReferenceData(self):
    u''' 参照データの情報をUcfDataリストとして返す（抽象メソッド） '''
    # TODO 自動判別したい
    return []

  def getNumberTypes():
    u''' 数値型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
    # TODO 自動判別したい
    return []
  getNumberTypes = staticmethod(getNumberTypes)

  def getBooleanTypes():
    u''' Bool型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
    # TODO 自動判別したい
    return []
  getBooleanTypes = staticmethod(getBooleanTypes)

  def getListTypes():
    u''' リスト型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
    # TODO 自動判別したい
    return []
  getListTypes = staticmethod(getListTypes)

  def getDateTimeTypes():
    u''' DateTime型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
    # TODO 自動判別したい
    return []
  getDateTimeTypes = staticmethod(getDateTimeTypes)

  def getBlobTypes():
    u''' Blobフィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
    # TODO 自動判別したい
    return []
  getBlobTypes = staticmethod(getBlobTypes)

  def getReferencesTypes():
    u''' 参照型フィールドがあればここでフィールド名のリストを返す（抽象メソッド） '''
    # TODO 自動判別したい
    return []
  getReferencesTypes = staticmethod(getReferencesTypes)


'''
Database Classes
'''


class GoogleAppsDomainEntry(UCFModel2):
  google_apps_domain = ndb.StringProperty()
  num_users = ndb.IntegerProperty()
  max_users = ndb.IntegerProperty()
  available_users = ndb.IntegerProperty()  # 無償版の利用可能ユーザ数（使用を制限するのではなく、アップグレードのメッセージを出したりするのに使用）　→ 契約管理から連携する契約ライセンス数をセット
  last_login_month = ndb.StringProperty()  # 最後に利用された月を保持
  is_free_mode = ndb.BooleanProperty()  # 無償設定(初期はTrue）
  is_disable = ndb.BooleanProperty()
  available_start_date = ndb.StringProperty()  # 利用開始日（YYYY/MM/DD 形式）
  charge_start_date = ndb.StringProperty()  # 課金開始日（YYYY/MM/DD 形式）
  cancel_date = ndb.StringProperty()  # 解約日（YYYY/MM/DD 形式）
  created_date = ndb.DateTimeProperty(auto_now_add=True)
  updated_date = ndb.DateTimeProperty(auto_now_add=True)
  backends_module_type = ndb.StringProperty()  # 使用するモジュールタイプ（b1、b2、b4、、、）

  def updateLastLoginMonth(self):
    """ update last_login_month to current date
      if no need to update(last_login_month is already current), not update
      Return: True ... last_login_month is updated
              False .. last_login_month is not updated
    """
    tz_utc = zoneinfo.gettz('UTC')
    current_time_utc = datetime.datetime.now(tz_utc)
    current_month = current_time_utc.strftime('%Y-%m')
    if (self.last_login_month is None) or (self.last_login_month != current_month):
      self.last_login_month = current_month
      self.put()
      GoogleAppsDomainEntry.clearInstanceCache(self.google_apps_domain)
      return True
    return False

  @classmethod
  def getMemcacheKey(cls, google_apps_domain):
    return 'script=googleappsdomainentry-getinstance&google_apps_domain=' + google_apps_domain

  @classmethod
  def clearInstanceCache(cls, google_apps_domain):
    memcache.delete(cls.getMemcacheKey(google_apps_domain))

  @classmethod
  def getInstance(cls, google_apps_domain, cache_ok=False):
    google_apps_domain = google_apps_domain.lower()
    old_namespace = namespace_manager.get_namespace()
    namespace_manager.set_namespace(google_apps_domain)

    result = None
    try:
      memcache_key = cls.getMemcacheKey(google_apps_domain)
      memcache_expire_secs = 60 * 60

      if cache_ok:
        # check memcache
        memcache_key = cls.getMemcacheKey(google_apps_domain)
        cached_dict = memcache.get(memcache_key)
        if cached_dict is not None:
          logging.info('GoogleAppsDomainEntry.getDict: found and respond cache')
          namespace_manager.set_namespace(old_namespace)
          return cached_dict

      if result is None:
        q = cls.query()
        q.filter(cls.google_apps_domain == google_apps_domain)

        row = q.get()
        if row is not None:
          is_need_put = False

          if row.backends_module_type is None:
            row.backends_module_type = ''
            is_need_put = True

          if is_need_put:
            row.put()

          row_dict = row.to_dict()
          if not memcache.set(memcache_key, value=row_dict, time=memcache_expire_secs):
            logging.warning("Memcache set failed.")

          result = row

    except Exception as error:
      namespace_manager.set_namespace(old_namespace)
      raise error

    namespace_manager.set_namespace(old_namespace)

    return result

  # @classmethod
  # def getByKey(cls, key):
  #   entity = None
  #   if key is not None:
  #     if key.name() is not None:
  #       entity = cls.get_by_key_name(key.name())
  #     elif key.id() is not None:
  #       entity = cls.get_by_id(key.id())
  #   return entity


class GoogleAppsUserEntry(UCFModel2):
  """
  Datastore class to store User data
  """
  user_email = ndb.StringProperty()
  # user_id = db.StringProperty()
  google_apps_domain = ndb.StringProperty()
  name = ndb.StringProperty()
  family_name = ndb.StringProperty()
  given_name = ndb.StringProperty()
  avatar = ndb.TextProperty()
  provider = ndb.StringProperty(default='')
  locale = ndb.StringProperty()
  is_admin = ndb.BooleanProperty(default=False)
  disable_user = ndb.BooleanProperty()
  created_date = ndb.DateTimeProperty(auto_now_add=True)
  updated_date = ndb.DateTimeProperty(auto_now_add=True)

  # @classmethod
  # def getByKey(cls, key):
  #   entity = None
  #   if key is not None:
  #     if key.name() is not None:
  #       entity = cls.get_by_key_name(key.name())
  #     elif key.id() is not None:
  #       entity = cls.get_by_id(key.id())
  #   return entity

  def before_put(self):
    pass

  def after_put(self):
    if self is not None:
      GoogleAppsUserEntry.clearInstanceCache(self.user_email, self.google_apps_domain)

  def put(self, **kwargs):
    self.before_put()
    super(GoogleAppsUserEntry, self).put(**kwargs)
    self.after_put()

  @classmethod
  def getMemcacheKey(cls, google_apps_domain, user_email):
    return 'script=GoogleAppsUserEntry&user_email=' + str(user_email) + '&google_apps_domain=' + str(google_apps_domain)

  @classmethod
  def clearInstanceCache(cls, google_apps_domain, user_email):
    memcache.delete(cls.getMemcacheKey(google_apps_domain, user_email))

  @classmethod
  def getMemcacheKeyList(cls, google_apps_domain):
    return 'script=GoogleAppsUserEntry-list&google_apps_domain=' + str(google_apps_domain)

  @classmethod
  def clearInstanceCacheList(cls, google_apps_domain):
    memcache.delete(cls.getMemcacheKeyList(google_apps_domain))

  @classmethod
  def get_dict(cls, google_apps_domain, user_email, timezone=sateraito_inc.DEFAULT_TIMEZONE):
    old_namespace = namespace_manager.get_namespace()
    namespace_manager.set_namespace(google_apps_domain)

    # check memcache
    memcache_key = cls.getMemcacheKey(google_apps_domain, user_email)
    logging.info(memcache_key)
    cached_dict = memcache.get(memcache_key)
    if cached_dict is not None:
      logging.info('GoogleAppsUserEntry.getDict: found and respond cache')
      logging.info(cached_dict)
      namespace_manager.set_namespace(old_namespace)
      return cached_dict

    q = GoogleAppsUserEntry.query()
    q.filter(cls.user_email == user_email)
    q.filter(cls.google_apps_domain == google_apps_domain)
    entry = q.get()

    if entry:
      # set to memcache
      row_dict = entry.to_dict()
      row_dict['created_date'] = UcfUtil.nvl(UcfUtil.getLocalTime(entry.created_date, timezone))

      memcache.set(memcache_key, row_dict, time=cls.NDB_MEMCACHE_TIMEOUT)
      namespace_manager.set_namespace(old_namespace)
      return row_dict

    cls.clearInstanceCache(google_apps_domain, user_email)
    namespace_manager.set_namespace(old_namespace)
    return None

  @classmethod
  def getInstance(cls, google_apps_domain, email):
    old_namespace = namespace_manager.get_namespace()
    namespace_manager.set_namespace(google_apps_domain)

    # get data
    email_lower = str(email).lower()

    q = GoogleAppsUserEntry.query()
    q.filter(cls.user_email == email_lower)
    q.filter(cls.google_apps_domain == google_apps_domain)
    user_entry = q.get()

    namespace_manager.set_namespace(old_namespace)

    return user_entry

