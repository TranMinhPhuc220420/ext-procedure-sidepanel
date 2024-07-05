#!/usr/bin/python
# coding: utf-8

import sys

# GAEGEN2対応:実装の意図が不明だが取り急ぎコメントアウト
#stdin = sys.stdin
#stdout = sys.stdout
#reload(sys)
#sys.setdefaultencoding('utf-8')
#sys.stdin = stdin
#sys.stdout = stdout

import json
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
import datetime

import random
import string

from google.appengine.ext import ndb

from ucf.utils.ucfutil import UcfUtil

ACCESS_TOKEN_EXPIRE_SECONDS = 12 * 60 * 60
ACCESS_TOKEN_LENGTH = 64


class PublicApiKey(ndb.Model):
  unique_id = ndb.StringProperty()
  api_key = ndb.StringProperty()

  creator_email = ndb.StringProperty()

  date_created = ndb.DateTimeProperty(auto_now_add=True)
  date_updated = ndb.DateTimeProperty(auto_now=True)

  @classmethod
  def create_api_key(cls, creator_email):
    unique_id = UcfUtil.guid()
    entry = cls(id=unique_id)
    entry.unique_id = unique_id
    api_key = UcfUtil.guid()
    entry.api_key = api_key
    entry.creator_email = creator_email

    entry_key = entry.put()

    entry_dict = entry_key.get().to_dict()

    return entry_dict

  @classmethod
  def list_api_key(cls):
    entries = cls.query().fetch()

    api_keys = []
    for entry in entries:
      entry_dict = entry.to_dict()

      api_keys.append(entry_dict)
    return api_keys

  @classmethod
  def delete_api_key(cls, unique_id):
    entry = cls.get_by_id(unique_id)
    if not entry:
      return False

    entry.key.delete()

    return True

  @classmethod
  def hide_api_key(cls, api_key):
    api_key_hidden = api_key[0:16] + '*' * 16
    return api_key_hidden


class PublicAccessToken(ndb.Model):
  access_token = ndb.StringProperty()
  is_revoked = ndb.IntegerProperty(default=False)
  # expire_seconds = ndb.IntegerProperty()
  expire_date = ndb.DateTimeProperty()

  date_created = ndb.DateTimeProperty(auto_now_add=True)
  date_updated = ndb.DateTimeProperty(auto_now=True)

  @classmethod
  def create_access_token(cls, expire_seconds=ACCESS_TOKEN_EXPIRE_SECONDS, token_length=ACCESS_TOKEN_LENGTH):
    access_token = None
    while True:
      # access_token = UcfUtil.guid()
      # more secured method
      access_token = ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(token_length))
      entry = cls.get_by_id(access_token)
      if not entry:
        break
    entry = cls(id=access_token)
    entry.access_token = access_token
    # entry.expire_seconds = expire_seconds
    entry.expire_date = datetime.datetime.utcnow().replace(tzinfo=None) + datetime.timedelta(seconds=expire_seconds)

    entry_key = entry.put()
    # entry_dict = entry_key.get().to_dict()
    # return entry_dict

    entry_created = entry_key.get()
    return entry_created.access_token

  @classmethod
  def refresh_access_token(cls, access_token, expire_seconds=ACCESS_TOKEN_EXPIRE_SECONDS):
    entry = cls.get_by_id(access_token)
    if not entry:
      return False
    # entry.expire_seconds = expire_seconds
    entry.expire_date = datetime.datetime.utcnow().replace(tzinfo=None) + datetime.timedelta(seconds=expire_seconds)
    # entry.is_revoked = False

    entry.put()

    return True

  @classmethod
  def revoke_access_token(cls, access_token):
    entry = cls.get_by_id(access_token)
    if not entry:
      return False
    entry.is_revoked = True

    entry.put()

    return True

  @classmethod
  def get_access_token(cls, access_token):
    entry = cls.get_by_id(access_token)
    if not entry:
      return

    entry_dict = entry.to_dict()

    return entry_dict

  @classmethod
  def check_access_token(cls, access_token):
    entry = cls.get_by_id(access_token)
    if not entry:
      return False

    if entry.is_revoked:
      return False

    if entry.expire_date <= datetime.datetime.utcnow().replace(tzinfo=None):
      return False

    return True

  @classmethod
  def clear_expired_access_tokens(cls):
    now_date = datetime.datetime.utcnow().replace(tzinfo=None)
    q = cls.query()
    q = q.filter(cls.expire_date <= now_date)

    # keys = q.iter(keys_only=True)
    # for key in keys:
    #   key.delete()

    # keys = q.iter(keys_only=True)
    # ndb.delete_multi(keys)

    while True:
      keys = q.iter(keys_only=True, limit=200)
      if not keys:
        break
      ndb.delete_multi(keys)
