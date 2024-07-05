# encoding: utf-8

import re
import json
#import logging
# import sateraito_logger as logging

from google.appengine.ext import ndb
# from google.appengine.api import namespace_manager
# from google.appengine.api import memcache
# from google.appengine.api import search


MIGRATE_STATUS_RUNNING = "RUNNING"
MIGRATE_STATUS_COMPLETED = "COMPLETED"
MIGRATE_STATUS_ERROR = "ERROR"

ID_ALL_DOMAIN_NAMESPACES = "ALL_DOMAIN_NAMESPACES"
ID_ALL_FULL_PROJECT = "ALL_FULL_PROJECT"


class SearchIndexMigrateStatus(ndb.Model):
  namespace = ndb.StringProperty()
  status = ndb.StringProperty()
  info = ndb.StringProperty()
  result = ndb.StringProperty(indexed=False)
  created = ndb.DateTimeProperty(auto_now_add=True)
  updated = ndb.DateTimeProperty(auto_now=True)

  @classmethod
  def get_key(cls, namespace):
    return ndb.Key(cls, namespace)

  @classmethod
  def get(cls, namespace):
    return cls.get_key(namespace).get()
  
  @classmethod
  def set(cls, namespace, status=MIGRATE_STATUS_RUNNING, info=None, result=None):
    entity = cls.get(namespace)
    if entity is None:
      entity = cls(key=cls.get_key(namespace))
    entity.namespace = namespace
    entity.status = status
    entity.info = info
    if result is not None:
      result = json.dumps(result, sort_keys=True)
      entity.result = result
    entity.put()
    return entity

  @classmethod
  def create(cls, namespace, status=MIGRATE_STATUS_RUNNING, info=None, result=None):
    entity = cls.get(namespace)
    if entity is not None:
      raise Exception("Entry SearchIndexMigrateStatus already exists")
    entity.namespace = namespace
    entity.status = status
    entity.info = info
    if result is not None:
      result = json.dumps(result, sort_keys=True)
      entity.result = result
    entity.put()
    return entity

  @classmethod
  def update(cls, namespace, status=None, info=None, result=None):
    entity = cls.get(namespace)
    if entity is None:
      raise Exception("Entry SearchIndexMigrateStatus not found")
    if status is not None:
      entity.status = status
    if info is not None:
      entity.info = info
    if result is not None:
      result = json.dumps(result, sort_keys=True)
      entity.result = result
    entity.put()
    return entity

  @classmethod
  def delete(cls, namespace):
    entity = cls.get(namespace)
    if entity is not None:
      entity.key.delete()
    return entity

  def to_dict(self):
    result = super(SearchIndexMigrateStatus, self).to_dict()
    if self.result is not None:
      result["result"] = json.loads(self.result)
    return result
  
  @classmethod
  def get_dict(cls, namespace):
    entity = cls.get(namespace)
    if entity is None:
      return None
    return entity.to_dict()
    
