# encoding: utf-8

###
# This module intent to used to mimic Google App Engine Search API
# Work as a drop-in replacement for Google App Engine Search API by wrapping elasticsearch client python.
# Work in all python 2 and 3.
# *** Limitation: 
#   1. Not support 'Facet' because elasticsearch use 'aggregation' to do similar job.
#   2. Not support 'index.get_range'function with start_id like GAE search API because elasticsearch field '_id' is not allow for range query.
#      - Note: '_id' field can be sort in Elasticsearch with setup 'indices.id_field_data.enabled' in server.
#      - Workaround: use 'index.get_range' function with 'field_id_alt' parameter to specify a field that replace doc_id of document in GAE search API.
#   3. Not directly support 'HtmlField' like GAE Search API. All HtmlField will be converted to TextField with value stripped of html tags.
#   4. Not support 'asynchronous' functions yet.
#   5. ...
# *** Difference Notes:
#   1. GAE Search API only have 'Numberfield'. Elasticsearch have many 'int', 'float', 'long'... to act as number. This module automatically convert 'Numberfield' form GAE to 'double' in elasticsearch.
#   2. GAE Search API use 'datetime' will trim time part but elasticsearch do not do that.
#   3. GAE create document need specify type of all fields in document but don't need specific schema of index ahead of time.
#      elasticsearch create document with request only need values, but support dynamic auto mapping not always result is the type you want.
#      So, this module will create index with specific schema ahead of time with static mapping when create document by compare current schema new document type fields.
#      This make easy to mimic GAE Search API but have some performance impact.
#   4. While GAE Search APE easy to use and error tolerant,
#      Elasticsearch need careful design of database before use and easy throw error if mismatch data/operation found when request.
#      This module will try to handle some error but not all.
#   5. ...
###

import sys

import re
import json
#import logging
# import sateraito_logger as logging

# import utilities
from . import utilities
IS_GAE = utilities.check_is_running_gae()
IS_PYTHON_3 = utilities.IS_PYTHON_3

import json
if IS_GAE and IS_PYTHON_3:
  import sateraito_logger as logging
else:
  import logging

from datetime import datetime
import dateutil.parser

# from collections.abc import Iterable

from . import elasticsearch_inc
from . import elasticsearch_func
from . import search_adapt
# IS_GAE = search_adapt.IS_GAE

USE_OPENSEARCH = elasticsearch_inc.USE_OPENSEARCH
# if USE_OPENSEARCH:
#   import opensearchpy
#   opensearchpy.logger.setLevel(opensearchpy.logging.WARNING)
#   # SearchException = opensearchpy.exceptions.OpenSearchException
#   SearchException = opensearchpy.OpenSearchException
# else:
#   import elasticsearch
#   elasticsearch.logger.setLevel(elasticsearch.logging.WARNING)
#   # SearchException = elasticsearch.exceptions.ElasticsearchException
#   SearchException = elasticsearch.ElasticsearchException

import elasticsearch
IS_ELASTICSEARCH_NEW = elasticsearch.VERSION >= (8, 0, 0)
elasticsearch.logger.setLevel(elasticsearch.logging.WARNING)
if hasattr(elasticsearch, 'ElasticsearchException'):
  # Elasticsearch version <= 7
  ElasticsearchException = elasticsearch.ElasticsearchException
else:
  # Elasticsearch version >= 8
  # ElasticsearchException = elasticsearch.ApiError
  ElasticsearchException = elasticsearch.exceptions.ApiError

import opensearchpy
opensearchpy.logger.setLevel(opensearchpy.logging.WARNING)
OpenSearchException = opensearchpy.OpenSearchException


# from . import utilities
is_str = utilities.is_str
is_num = utilities.is_num

IS_PYTHON_3 = utilities.IS_PYTHON_3

# KIND_ELASTICSEARCH = 'ELASTICSEARCH'
# KIND_OPENSEARCH = 'OPENSEARCH'


USE_POOL_CLIENTS = True


# mimic google app engine search api datetime field
ROUND_DATETIME_AS_GAE = elasticsearch_inc.ROUND_DATETIME_AS_GAE

MULTI_TENANT_SAME_INDEX = elasticsearch_inc.MULTI_TENANT_SAME_INDEX
CREATE_INDEX_ALIAS_FOR_NAMESPACE = elasticsearch_inc.CREATE_INDEX_ALIAS_FOR_NAMESPACE

PROJECT_ID_INDEX_PREFIX = elasticsearch_inc.PROJECT_ID_INDEX_PREFIX

PROJECT_ID_INDEX_SEPARATOR = elasticsearch_inc.PROJECT_ID_INDEX_SEPARATOR

NAMESPACE_SEPARATOR_INDEX = elasticsearch_inc.NAMESPACE_SEPARATOR_INDEX
NAMESPACE_SEPARATOR_DOCUMENT = elasticsearch_inc.NAMESPACE_SEPARATOR_DOCUMENT


NAMESPACE_GLOBAL = elasticsearch_inc.NAMESPACE_GLOBAL
DOCUMENT_KEY_INTERNAL_NAMESPACE = elasticsearch_inc.DOCUMENT_KEY_INTERNAL_NAMESPACE
DOCUMENT_KEY_INTERNAL_ID = elasticsearch_inc.DOCUMENT_KEY_INTERNAL_ID
DOCUMENT_KEY_INTERNAL_TIMESTAMP = elasticsearch_inc.DOCUMENT_KEY_INTERNAL_TIMESTAMP

DEFAULT_INDEX_PIPELINE = "automatic_timestamp"

TEMP_ELASTICSEARCH_MEMCACHE_KEY_INDEX_MAPPINGS = "ELASTICSEARCH_INDEX_MAPPINGS__{}"
TEMP_ELASTICSEARCH_MEMCACHE_KEY_ALIAS_DATA = "ELASTICSEARCH_ALIAS_DATA__{}"

TEMP_OPENSEARCH_MEMCACHE_KEY_INDEX_MAPPINGS = "OPENSEARCH_INDEX_MAPPINGS__{}"
TEMP_OPENSEARCH_MEMCACHE_KEY_ALIAS_DATA = "OPENSEARCH_ALIAS_DATA__{}"


AUTO_CONVERT_QUERY_STRING_GAE_SEARCH_TO_ELASTICSEARCH = True

WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH = elasticsearch_inc.WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH
WRITE_INDEX_BOTH_ELASTICSEARCH_AND_OPENSEARCH = elasticsearch_inc.WRITE_INDEX_BOTH_ELASTICSEARCH_AND_OPENSEARCH

REGEX_INDEX_NAME_CHECK = re.compile(r'^(?![-_+])[a-z][a-z0-9_@$%&\(\)\-.]*$')

if IS_GAE:
  if IS_PYTHON_3:
    search = None
  else:
    from google.appengine.api import search
else:
  search = None

get_current_namespace = search_adapt.get_current_namespace
generate_random_document_id = search_adapt.generate_random_document_id


# TODO: Complete mirgate from Elasticsearch 7 to 8 changes:
#   + Keyword-only arguments for APIs
#   + Start using .options() for transport parameters: headers, api_key, http_auth, opaque_id, request_timeout, ignore
#   + Request responses are now wrapped in a Response class have properties: body, meta
#   + ElasticsearchError split into ApiError and TransportError


class Field(object):
# class that mimic Google App Engine Search API 'Field'
  def __init__(self, name, value, language=None):
    self.name = name
    self.value = value
    self.language = language

  def to_value(self):
    return self.value
  
  def to_dict(self):
    res = {
      "value": self.value
    }
    return res


class TextField(Field):
  def __init__(self, name, value, language=None):
    super(TextField, self).__init__(name, value, language)
    self.type = "text"

  def to_dict(self):
    res = super(TextField, self).to_dict()
    res["type"] = "text"
    return res
  

class HtmlField(Field):
  def __init__(self, name, value, language=None):
    super(HtmlField, self).__init__(name, value, language)
    value_html_striped = None
    if self.value:
      value_html_striped = re.sub('<[^<]+?>', '', self.value)
    self.value_text = value_html_striped
    self.type = "text"

  def to_value(self):
    return self.value_text
  
  def to_dict(self):
    res = super(HtmlField, self).to_dict()
    res["type"] = "text"
    res["value"] = self.value_text
    return res


class AtomField(Field):
  def __init__(self, name, value, language=None):
    super(AtomField, self).__init__(name, value, language)
    self.type = "keyword"

  def to_dict(self):
    res = super(AtomField, self).to_dict()
    res["type"] = "keyword"
    return res


class NumberField(Field):
  def __init__(self, name, value, language=None, field_type="double"):
    super(NumberField, self).__init__(name, value, language)
    self.field_type = field_type
    self.type = field_type or "double"
    self.value_raw = value
    if utilities.is_num(value):
      if self.type == "double":
        self.value = float(value)
      elif self.type == "float":
        self.value = float(value)
      elif self.type == "integer":
        self.value = int(value)
      elif self.type == "long":
        if IS_PYTHON_3:
          self.value = int(value)
        else:
          self.value = long(value)
      else:
        self.value = value
    elif utilities.is_str(value):
      try:
        if self.type == "double":
          self.value = float(value)
        elif self.type == "float":
          self.value = float(value)
        elif self.type == "integer":
          self.value = int((float(value)))
        elif self.type == "long":
          if IS_PYTHON_3:
            self.value = int(float(value))
          else:
            self.value = long(float(value))
        else:
          self.value = float(value)
      except:
        logging.warn("NumberField: failed to convert value to number: {}".format(value))
        # TODO: set value representing error
        self.value = 0

  def to_dict(self):
    res = super(NumberField, self).to_dict()
    res["type"] = self.field_type or "double"
    return res


class DateField(Field):
  def __init__(self, name, value, language=None, strip_time=False):
    super(DateField, self).__init__(name, value, language)
    self.strip_time = strip_time
    value_raw = value
    value_date = None
    if isinstance(value_raw, datetime):
      value_date = value_raw
    
    elif is_str(value_raw):
      # if re.match(r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}$", value_raw):
      #   value_date = datetime.strptime(value_raw, "%Y/%m/%d %H:%M:%S")
      # elif re.match(r"^\d{4}/\d{2}/\d{2}$", value_raw):
      #   value_date = datetime.strptime(value_raw, "%Y-%m-%d")
      # elif re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3,10}Z$", value_raw):
      #   value_date = datetime.strptime(value_raw, "%Y-%m-%dT%H:%M:%S.%fZ")
      # elif re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3,10}$", value_raw):
      #   value_date = datetime.strptime(value_raw, "%Y-%m-%dT%H:%M:%S.%f")
      # elif re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", value_raw):
      #   value_date = datetime.strptime(value_raw, "%Y-%m-%dT%H:%M:%SZ")
      # elif re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", value_raw):
      #   value_date = datetime.strptime(value_raw, "%Y-%m-%dT%H:%M:%S")
      # elif re.match(r"^\d{4}-\d{2}-\d{2}$", value_raw):
      #   value_date = datetime.strptime(value_raw, "%Y-%m-%d")
      # else:
      #   raise ValueError("Invalid date format: {}".format(value_raw))
      
      # # best performance way to parse date string return by elasticsearch in python 3
      # value_date = datetime.fromisoformat(date_string)
      
      try:
        value_date = dateutil.parser.parse(value_raw)
      except ValueError:
        raise ValueError("Invalid date string: {}".format(value_raw))
    
    elif is_num(value_raw):
      value_date = datetime.fromtimestamp(value_raw)
    
    else:
      value_date = value_raw
    
    # if value_date is None:
    #   raise ValueError("Invalid date: {}".format(value_date))

    if value_date:
      if ROUND_DATETIME_AS_GAE or self.strip_time:
        # value_date = datetime(year=value_date.year, month=value_date.month, day=value_date.day, hour=0, minute=0, second=0, microsecond=0)
        # value_raw = value_raw.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        # value_raw = value_raw.strftime("%Y-%m-%d")
        value_date = datetime(year=value_date.year, month=value_date.month, day=value_date.day)
    self.value_date = value_date
    self.type = "date"

  def to_value(self):
    return self.value_date
  
  def to_dict(self):
    res = super(DateField, self).to_dict()
    res["type"] = "date"
    res["value"] = self.value_date
    
    return res


class GeoPoint(object):
  def __init__(self, lat, lon):
    self.latitude = lat
    self.longitude = lon

  def to_value(self):
    return {
      "lat": self.latitude,
      "lon": self.longitude
    }


class GeoField(Field):
  def __init__(self, name, value, language=None):
    super(GeoField, self).__init__(name, value, language)
    value_geo = None
    geo_point = self.value
    if geo_point:
      if isinstance(geo_point, GeoPoint):
        value_geo = geo_point.to_value()
      elif isinstance(geo_point, dict):
        if 'latitude' in geo_point and 'longitude' in geo_point:
          value_geo = {
            "lat": geo_point['latitude'],
            "lon": geo_point['longitude'],
          }
          self.value = GeoPoint(geo_point['latitude'], geo_point['longitude'])
        elif 'lat' in geo_point and 'lon' in geo_point:
          value_geo = {
            "lat": geo_point['lat'],
            "lon": geo_point['lon'],
          }
          self.value = GeoPoint(geo_point['lat'], geo_point['lon'])
        else:
          raise ValueError("Invalid geo point: {}".format(geo_point))
      elif isinstance(geo_point, (list, tuple)):
        value_geo = {
          "lat": geo_point[0],
          "lon": geo_point[1],
        }
        self.value = GeoPoint(geo_point[0], geo_point[1])
      else:
        raise ValueError("Invalid geo point: {}".format(geo_point))
    self.value_geo = value_geo
    self.type = "geo_point"

  def to_value(self):
    return self.value_geo
  
  def to_dict(self):
    res = super(GeoField, self).to_dict()
    res["type"] = "geo_point"
    res["value"] = self.value_geo
    
    return res


MAP_FIELD_TYPE = {
  'keyword': AtomField,
  'text': TextField,
  'byte': NumberField,
  'short': NumberField,
  'integer': NumberField,
  'long': NumberField,
  'float': NumberField,
  'float': NumberField,
  'double': NumberField,
  'date': DateField,
  'geo_point': GeoField,
}


if search is not None:
  MAP_FIELD_TYPE_TO_GAE_SEARCH_FIELD = {
    AtomField: search.AtomField,
    NumberField: search.NumberField,
    TextField: search.TextField,
    HtmlField: search.HtmlField,
    DateField: search.DateField,
    GeoField: search.GeoField,
  }
else:
  MAP_FIELD_TYPE_TO_GAE_SEARCH_FIELD = {}


# class that mimic Google App Engine Search API 'Document'
class Document(object):
  def __init__(self, doc_id=None, fields=None, language=None, rank=None):
    # assert(fields is not None, "fields is required")
    self.doc_id = doc_id
    self.fields = fields
    self.language = language
    self.rank = rank

    self.cursor = None

    self._index_namespace = None
    self._index_timestamp = None

  def to_value(self):
    res = {}
    # if self.doc_id:
    #   res['_id'] = self.doc_id
    if self.fields:
      for field in self.fields:
        if field.name not in res:
          res[field.name] = field.to_value()
        else:
          current_value = res[field.name]
          if isinstance(current_value, list):
            current_value.append(field.to_value())
          else:
            res[field.name] = [current_value, field.to_value()]
    return res
  
  def to_dict(self):
    res = {}
    if self.doc_id:
      res['_id'] = self.doc_id
    if self.fields:
      for field in self.fields:
        if field.name not in res:
          res[field.name] = field.to_dict()
        else:
          current_value = res[field.name]
          if isinstance(current_value, list):
            current_value.append(field.to_dict())
          else:
            res[field.name] = [current_value, field.to_dict()]
    return res

  def __str__(self):
    obj = self.to_value()
    obj[DOCUMENT_KEY_INTERNAL_ID] = self.doc_id
    if self._index_namespace:
      obj[DOCUMENT_KEY_INTERNAL_NAMESPACE] = self._index_namespace
    if self._index_timestamp:
      obj[DOCUMENT_KEY_INTERNAL_TIMESTAMP] = self._index_timestamp
    # return json.dumps(obj, indent=2, sort_keys=True)
    return str(obj)
  
  @classmethod
  def import_res(cls, rel_doc_id, res_fields=None, es_mappings=None, index=None, cls_fields=None):
    # remove namespace from doc_id when using multi namespace in one index
    doc_id = rel_doc_id
    index_namespace = None
    if MULTI_TENANT_SAME_INDEX:
      doc_id_parts = rel_doc_id.split(NAMESPACE_SEPARATOR_DOCUMENT, 1)
      if len(doc_id_parts) == 2:
        doc_id = doc_id_parts[1]
        index_namespace = doc_id_parts[0]
      else:
        # doc_id = doc_id_parts[0]
        pass
    if not res_fields:
      doc = cls(doc_id)
      if index_namespace:
        doc._index_namespace = index_namespace
      return doc
    
    es_mappings_properties = None
    if index:
      es_mappings_properties = index.mappings['properties']
    elif es_mappings:
      es_mappings_properties = es_mappings.get('properties')

    index_timestamp = None

    fields = []
    if isinstance(res_fields, dict):
      index_timestamp = res_fields.get(DOCUMENT_KEY_INTERNAL_TIMESTAMP)
      for field_name in res_fields:
        field_value = res_fields[field_name]
        field_cls = Field
        if cls_fields:
          field_cls = cls_fields.get(field_name) or Field
        elif es_mappings_properties:
          field_type_obj = es_mappings_properties.get(field_name)
          if field_type_obj:
            field_type_str = field_type_obj.get('type')
            if field_type_str:
              field_cls = MAP_FIELD_TYPE.get(field_type_str) or Field
        
        if isinstance(field_value, dict):
          # TODO: Need handle this case because Elasticsearch support nested field, but GAE Search API not support, only work with geo_point for now
          field_obj = field_cls(field_name, field_value)
          fields.append(field_obj)
        
        elif isinstance(field_value, (list, tuple)):
          # Elasticsearch support multi values for a field as array that similar to GAE Search API
          for field_value_item in field_value:
            if field_cls == DateField and field_value_item:
              # field_value_item = field_value_item.replace("T", " ")
              if IS_PYTHON_3:
                field_value_item = datetime.fromisoformat(field_value_item)
              else:
                try:
                  field_value_item = dateutil.parser.parse(field_value_item)
                except ValueError:
                  logging.warning("Unexpected date string returned: {}".format(field_value_item))
            field_obj = field_cls(field_name, field_value_item)
            fields.append(field_obj)
        
        else:
          if field_cls == DateField and field_value:
            # field_value = field_value.replace("T", " ")
            if IS_PYTHON_3:
              field_value = datetime.fromisoformat(field_value)
            else:
              try:
                field_value = dateutil.parser.parse(field_value)
              except ValueError:
                logging.warning("Unexpected date string returned: {}".format(field_value))
          field_obj = field_cls(field_name, field_value)
          fields.append(field_obj)
    
    document_obj = cls(doc_id, fields)
    if index_namespace:
      document_obj._index_namespace = index_namespace
    if index_timestamp:
      document_obj._index_timestamp = index_timestamp
    return document_obj

  def to_gae_search_document(self):
    gae_fields = []
    for field in self.fields:
      field_cls = field.__class__
      gae_field_cls = MAP_FIELD_TYPE_TO_GAE_SEARCH_FIELD[field_cls]
      gae_field = gae_field_cls(name=field.name, value=field.value)
      gae_fields.append(gae_field)
    gae_document = search.Document(doc_id=self.doc_id, fields=gae_fields)
    return gae_document


# class that mimic Google App Engine Search API 'Index'
class IndexInstance(object):
  def __init__(self, name, namespace=None, client=None, write_index_both=WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH, use_opensearch=USE_OPENSEARCH):
  # def __init__(self, name, namespace=None, client=None):
    # Elasticsearch indices have the following naming restrictions:
    #   + All letters must be lowercase.
    #   + Index names can't begin with _ (underscore) or - (hyphen) and + (plus).
    #   + Index names can't contain spaces, commas, or the following characters: : , '," , * , + , / , \ , | , ? , # , > , or <
    #   + Note: Invalid characters maybe difference between Elasticsearch version

    self.use_opensearch = use_opensearch

    self.name_raw = name
    # auto lowercase index name
    self.name = name.lower()
    
    # sort check name valid for elasticsearch index name
    # if not re.match(r'^(?![-_+])[a-z][a-z0-9_@$%&\(\)\-.]*$', self.name):
    if not REGEX_INDEX_NAME_CHECK.match(self.name):
      raise ValueError("Invalid elsaticsearch index name: {}".format(name))
    
    # if namespace is not None:
    #   self.namespace = namespace
    # else:
    #   self.namespace = get_current_namespace()
    self._namespace = namespace
    # self.fullname = self.namespace + "@" + self.name
    # self.client = client or elasticsearch_func.get_client(self.use_opensearch)
    # self.client = client
    self.client_instance = client
    self.client_temp = None
    # self.resolve()
    
    # self.intialized = False
    # self.created = None
    # self.mappings = None

    self.dict_intialized = {}
    self.dict_created = {}
    # self.dict_info = {}
    self.dict_mappings = {}

    self.dict_alias_intialized = {}
    self.dict_alias_created = {}

    if write_index_both and IS_GAE and search:
      self.gae_instance = search.Index(name=name)
    else:
      self.gae_instance = None
  
  @property
  def namespace(self):
    if self._namespace is not None:
      return self._namespace
    return get_current_namespace()

  @property
  def fullname(self):
    if MULTI_TENANT_SAME_INDEX:
      fullname = self.name
      if PROJECT_ID_INDEX_PREFIX:
        fullname = PROJECT_ID_INDEX_PREFIX + PROJECT_ID_INDEX_SEPARATOR + fullname
      return fullname
    separator = NAMESPACE_SEPARATOR_INDEX
    fullname = None
    if self._namespace:
      fullname = self._namespace + separator + self.name
    else:
      namespace = get_current_namespace()
      if namespace:
        fullname = namespace + separator + self.name
      else:
        fullname = self.name
    if PROJECT_ID_INDEX_PREFIX:
      fullname = PROJECT_ID_INDEX_PREFIX + PROJECT_ID_INDEX_SEPARATOR + fullname
    return fullname

  @property
  def client(self):
    if not USE_POOL_CLIENTS:
      if self.client_instance:
        return self.client_instance
      self.client_instance = elasticsearch_func.get_client(use_opensearch=self.use_opensearch)
      return self.client_instance
    
    else:
      if self.client_instance:
        return self.client_instance
      self.client_temp = elasticsearch_func.borrow_client(use_opensearch=self.use_opensearch)
      return self.client_temp

  def client_return(self):
    if self.client_temp:
      # if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
      #   self.client_temp.options(ignore_status=None)
      if USE_POOL_CLIENTS:
        elasticsearch_func.return_client(self.client_temp)
        self.client_temp = None
        return True
    return False

  @property
  def intialized(self):
    res = self.dict_intialized.get(self.fullname) or False
    return res
  
  @intialized.setter
  def intialized(self, value):
    self.dict_intialized[self.fullname] = value

  @property
  def created(self):
    res = self.dict_created.get(self.fullname) or False
    return res
  
  @created.setter
  def created(self, value):
    self.dict_created[self.fullname] = value
  
  # @property
  # def info(self):
  #   res = self.dict_info.get(self.fullname)
  #   return res
  
  # @info.setter
  # def info(self, value):
  #   self.dict_info[self.fullname] = value

  @property
  def mappings(self):
    res = self.dict_mappings.get(self.fullname)
    return res
  
  @mappings.setter
  def mappings(self, value):
    self.dict_mappings[self.fullname] = value

  @property
  def alias(self):
    # if not MULTI_TENANT_SAME_INDEX:
    #   return None
    separator = NAMESPACE_SEPARATOR_INDEX
    fullname = None
    if self._namespace:
      fullname = self._namespace + separator + self.name
    else:
      namespace = get_current_namespace()
      if namespace:
        fullname = namespace + separator + self.name
      else:
        namespace = NAMESPACE_GLOBAL
        fullname = namespace + separator + self.name
    if PROJECT_ID_INDEX_PREFIX:
      fullname = PROJECT_ID_INDEX_PREFIX + PROJECT_ID_INDEX_SEPARATOR + fullname
    alias_name = fullname
    return alias_name
  
  @property
  def alias_intialized(self):
    res = self.dict_alias_intialized.get(self.alias) or False
    return res
  
  @alias_intialized.setter
  def alias_intialized(self, value):
    self.dict_alias_intialized[self.alias] = value
  
  @property
  def alias_created(self):
    res = self.dict_alias_created.get(self.alias) or False
    return res
  
  @alias_created.setter
  def alias_created(self, value):
    self.dict_alias_created[self.alias] = value

  def initialize(self):
    self.resolve()
    self.intialized = True
  
  def uninitialize(self):
    # TODO: set index and alias status to global mem cache

    self.intialized = False
    self.created = None

    self.alias_intialized = False
    self.alias_created = None

  @property
  def available_index_name_or_alias(self, auto_initialize=False):
    # auto return index name or alias name based on MULTI_TENANT_SAME_INDEX and CREATE_INDEX_ALIAS_FOR_NAMESPACE settings
    if auto_initialize and not self.intialized:
      self.initialize()
    if MULTI_TENANT_SAME_INDEX and CREATE_INDEX_ALIAS_FOR_NAMESPACE:
      return self.alias
    return self.fullname

  def resolve(self, auto_create_alias=False):
    logging.debug("Resolve index: {}".format(self.fullname))
    
    self.created = False
    info = None
    mappings = None
    
    # TODO: change memcache module solution when upgrade to python 3
    mem_key_index = TEMP_ELASTICSEARCH_MEMCACHE_KEY_INDEX_MAPPINGS
    if self.use_opensearch:
      mem_key_index = TEMP_OPENSEARCH_MEMCACHE_KEY_INDEX_MAPPINGS
    mem_key_index = mem_key_index.format(self.fullname)
    
    mappings = search_adapt.memcache_get(mem_key_index)
    
    if mappings is None:
      # result = self.client.indices.get(index=self.fullname, ignore=[404])
      # if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
      #   self.client.options(ignore_status=[404])
      client = self.client
      if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
        client = client.options(ignore_status=[404])
      result = client.indices.get_mapping(index=self.fullname, ignore=[404])
      client = None
      self.client_return()
      if result.get('error'):
        # if result.get('status') == 404:
        #   pass
        # else:
        #   raise Exception("Error getting index mappings: " + str(result))
        self.created = False
      else:
        result_info = result[self.fullname]
        # info = result_info
        mappings = result_info['mappings']
        self.created = True

        search_adapt.memcache_set(mem_key_index, mappings)
    
    else:
      self.created = True
    
    # self.info = info
    self.mappings = mappings

    if not MULTI_TENANT_SAME_INDEX:
      return
    
    if self.alias_intialized:
      if not CREATE_INDEX_ALIAS_FOR_NAMESPACE or self.alias_created:
        return

    self.resolve_alias(auto_create_alias=auto_create_alias)

  def resolve_alias(self, auto_create_alias=False):
    self.alias_intialized = False
    
    self.alias_created = False
    if CREATE_INDEX_ALIAS_FOR_NAMESPACE:
      logging.debug("Resolve alias: {}".format(self.alias))

      # TODO: change memcache module solution when upgrade to python 3
      mem_key_alias = TEMP_ELASTICSEARCH_MEMCACHE_KEY_ALIAS_DATA
      if self.use_opensearch:
        mem_key_alias = TEMP_OPENSEARCH_MEMCACHE_KEY_ALIAS_DATA
      mem_key_alias = mem_key_alias.format(self.alias)

      alias_exists = search_adapt.memcache_get(mem_key_alias)

      if alias_exists is None:
        alias_exists = None
        if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
          resp = self.client.indices.exists_alias(name=self.alias)
          alias_exists = resp.body is True
        else:
          alias_exists = self.client.indices.exists_alias(name=self.alias)
        logging.info("alias_exists: {}".format(alias_exists))
        if alias_exists:
          self.alias_created = True
          search_adapt.memcache_set(mem_key_alias, True)

        else:
          if auto_create_alias:
            filter_query = {
              "term": {
                DOCUMENT_KEY_INTERNAL_NAMESPACE: self.namespace
              }
            }
            body = {
              "filter": filter_query,
            }
            result = self.client.indices.put_alias(index=self.fullname, name=self.alias, body=body)
            self.client_return()
            if result.get('error'):
              raise Exception("Error creating alias: " + str(result))
            else:
              logging.debug("Created alias: {}".format(json.dumps(result, indent=2, sort_keys=True)))
              self.alias_created = True
              
              search_adapt.memcache_set(mem_key_alias, True)
      
      else:
        self.alias_created = alias_exists
    
    self.alias_intialized = True

  def _put_mapping_for(self, documents):
    if isinstance(documents, (list, tuple)):
      pass
    else:
      documents = [documents]
    
    # TODO: better handle field that is array type like tags

    if not self.created:
      logging.info("Create New Index: {}".format(self.fullname))
      new_properties = {}
      for document in documents:
        for field in document.fields:
          field_type = field.type
          field_name = field.name
          if field_name in new_properties:
            continue
          field_map = {
            'type': field.type,
          }
          if field_type == 'text':
            # field_map['analyzer'] = 'standard'
            # it not good for performance when setting fielddata to true
            # better to use keyword type instead
            field_map['fielddata'] = True
          # elif field_type == 'keyword':
          #   field_map['ignore_above'] = 256
          # elif field_type == 'date':
          #   field_map['format'] = 'date_time_no_millis'
          # elif field_type == 'geo_point':
          #   field_map['lat_lon'] = True
          new_properties[field_name] = field_map
        
      if MULTI_TENANT_SAME_INDEX:
        new_properties[DOCUMENT_KEY_INTERNAL_NAMESPACE] = {
          'type': 'keyword'
        }
      new_properties[DOCUMENT_KEY_INTERNAL_ID] = {
        'type': 'keyword'
      }
      new_properties[DOCUMENT_KEY_INTERNAL_TIMESTAMP] = {
        'type': 'date'
      }
      body_settings = elasticsearch_func.get_index_settings(self.fullname)
      body_mappings = elasticsearch_func.get_index_mappings(self.fullname)
      document_mappings = {
        "properties": new_properties
      }
      utilities.update_deep(body_mappings, document_mappings)
      body = {
        "settings": body_settings,
        "mappings": body_mappings,
      }
      # if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
      #   self.client.options(ignore_status=[400])
      client = self.client
      if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
        client = client.options(ignore_status=[400])
      result = client.indices.create(index=self.fullname, body=body, ignore=[400])
      client = None
      self.client_return()
      mem_key_index = TEMP_ELASTICSEARCH_MEMCACHE_KEY_INDEX_MAPPINGS
      if self.use_opensearch:
        mem_key_index = TEMP_OPENSEARCH_MEMCACHE_KEY_INDEX_MAPPINGS
      mem_key_index = mem_key_index.format(self.fullname)
      if result.get('error') and result.get('status') == 400 and result['error']['type'] == 'resource_already_exists_exception':
        search_adapt.memcache_delete(mem_key_index)
        self.resolve()
      else:
        if result.get('acknowledged'):
          search_adapt.memcache_delete(mem_key_index)
          auto_create_alias = MULTI_TENANT_SAME_INDEX
          self.resolve(auto_create_alias=auto_create_alias)
          return result
        else:
          raise Exception("Error when creating index with mappings: " + str(result))
    
    if MULTI_TENANT_SAME_INDEX and CREATE_INDEX_ALIAS_FOR_NAMESPACE:
      if not self.alias_created:
        mem_key_alias = TEMP_ELASTICSEARCH_MEMCACHE_KEY_ALIAS_DATA
        if self.use_opensearch:
          mem_key_alias = TEMP_OPENSEARCH_MEMCACHE_KEY_ALIAS_DATA
        mem_key_alias = mem_key_alias.format(self.alias)
        search_adapt.memcache_delete(mem_key_alias)
        self.resolve_alias(auto_create_alias=True)

    last_error = None
    for _ in range(3):
      old_properties = self.mappings['properties']
      new_properties = {}
      for document in documents:
        for field in document.fields:
          field_name = field.name
          if field_name in new_properties:
            continue
          if field_name in old_properties:
            # TODO: check if field type is the same and handle case if field type is not same
            continue
          field_type = field.type
          field_map = {
            'type': field_type,
            # 'fielddata': True,
          }
          if field_type == 'text':
            # field_map['analyzer'] = 'standard'
            # it not good for performance when setting fielddata to true, maybe we should not set it
            field_map['fielddata'] = True
          new_properties[field_name] = field_map
      
      if not new_properties:
        return
      
      body_mappings = {
        "properties": new_properties
      }
      result = self.client.indices.put_mapping(index=self.fullname, body=body_mappings, ignore=[400])
      self.client_return()
      
      result_error = result.get('error')
      if result_error:
        if last_error == result_error:
          raise Exception("Error when update index with mappings: " + str(result))
        last_error = result_error
        if result.get('status') == 400 and result_error.get('type') == 'illegal_argument_exception':
          mem_key_index = TEMP_ELASTICSEARCH_MEMCACHE_KEY_INDEX_MAPPINGS
          if self.use_opensearch:
            mem_key_index = TEMP_OPENSEARCH_MEMCACHE_KEY_INDEX_MAPPINGS
          mem_key_index = mem_key_index.format(self.fullname)
          search_adapt.memcache_delete(mem_key_index)
          self.resolve()
          # refresh index mappings and try again
          continue
        else:
          raise Exception("Error when update index with mappings: " + str(result))
      
      if result.get('acknowledged'):
        mem_key_index = TEMP_ELASTICSEARCH_MEMCACHE_KEY_INDEX_MAPPINGS
        if self.use_opensearch:
          mem_key_index = TEMP_OPENSEARCH_MEMCACHE_KEY_INDEX_MAPPINGS
        mem_key_index = mem_key_index.format(self.fullname)
        search_adapt.memcache_delete(mem_key_index)
        auto_create_alias = MULTI_TENANT_SAME_INDEX
        self.resolve(auto_create_alias=auto_create_alias)
      return result

  def _rel_routing(self):
    routing = self.namespace
    # if PROJECT_ID_INDEX_PREFIX:
    #   routing = PROJECT_ID_INDEX_PREFIX + PROJECT_ID_INDEX_SEPARATOR + routing
    return routing

  def _rel_document_id(self, document):
    document_id = None
    if document:
      if is_str(document):
        document_id = document
      elif isinstance(document, Document):
        document_id = document.doc_id
      elif isinstance(document, dict):
        document_id = document.get("doc_id")
      else:
        raise Exception("Invalid document type: " + str(type(document)))
      
    if MULTI_TENANT_SAME_INDEX:
      # if not document_id:
      #   document_id = generate_random_document_id()
      document_id = self.namespace + NAMESPACE_SEPARATOR_DOCUMENT + document_id
    return document_id

  def put(self, documents, deadline=None, skip_mapping=False, mapping_all=True, write_index_both=WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH):
  # def put(self, documents, deadline=None, skip_mapping=False, mapping_all=False):
    if not skip_mapping:
      if not self.intialized:
        self.initialize()
    
    if not documents:
      return

    if write_index_both and IS_GAE and self.gae_instance:
      if isinstance(documents, (list, tuple)):
        gae_documents = []
        for doc in documents:
          if not doc.doc_id:
            doc.doc_id = generate_random_document_id()
          gae_doc = doc.to_gae_search_document()
          gae_documents.append(gae_doc)
        try:
          self.gae_instance.put(gae_documents, deadline=deadline)
        except Exception as e:
          logging.error(e, exc_info=True)
      else:
        doc = documents
        if not doc.doc_id:
          doc.doc_id = generate_random_document_id()
        gae_document = doc.to_gae_search_document()
        try:
          self.gae_instance.put(gae_document, deadline=deadline)
        except Exception as e:
          logging.error(e, exc_info=True)

    # TODO: Return list of results (PutResult), one for each document requested to be indexed.
    if isinstance(documents, Document):
      return self._put_single(documents, deadline=deadline, skip_mapping=skip_mapping)
    elif isinstance(documents, (list, tuple)):
      return self._put_multiple(documents, deadline=deadline, skip_mapping=skip_mapping, mapping_all=mapping_all)
  
  def _put_single(self, document, deadline=None, skip_mapping=False):
    if not skip_mapping:
      self._put_mapping_for(document)
    if not document.doc_id:
      document.doc_id = generate_random_document_id()
    body = document.to_value()
    if MULTI_TENANT_SAME_INDEX:
      index_namespace = self.namespace
      body[DOCUMENT_KEY_INTERNAL_NAMESPACE] = index_namespace
    body[DOCUMENT_KEY_INTERNAL_ID] = document.doc_id
    # body[DOCUMENT_KEY_INTERNAL_TIMESTAMP] = datetime.utcnow()
    document_id = self._rel_document_id(document)
    index_name = None
    if MULTI_TENANT_SAME_INDEX and CREATE_INDEX_ALIAS_FOR_NAMESPACE:
      index_name = self.alias
    else:
      index_name = self.fullname
    require_alias = MULTI_TENANT_SAME_INDEX and CREATE_INDEX_ALIAS_FOR_NAMESPACE
    # if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
    #   if '_id' in body:
    #     del body['_id']
    result = self.client.index(
      index=index_name,
      id=document_id,
      body=body,
      routing=self._rel_routing(),
      pipeline=DEFAULT_INDEX_PIPELINE,
      require_alias=require_alias,
      request_timeout=deadline or None,
    )
    self.client_return()
    return result
  
  def _put_multiple(self, documents, deadline=None, skip_mapping=False, mapping_all=True):
    if not skip_mapping:
      if not mapping_all:
        self._put_mapping_for(documents[0])
      else:
        self._put_mapping_for(documents)

    for document in documents:
      if not document.doc_id:
        document.doc_id = generate_random_document_id()

    # for document in documents:
    #   self._put_single(document)

    # bulk_data = []
    # for document in documents:
    #   bulk_data.append(
    #     {
    #         "_index": self.fullname,
    #         "_id": document.doc_id,
    #         "_source": document.to_value(),
    #     }
    #   )
    # results = elasticsearch.helpers.bulk(self.client, bulk_data)
    
    bulk_body = []
    index_name = None
    if MULTI_TENANT_SAME_INDEX and CREATE_INDEX_ALIAS_FOR_NAMESPACE:
      index_name = self.alias
    else:
      index_name = self.fullname
    routing = self._rel_routing()
    index_namespace = self.namespace
    # indexed_timestamp = datetime.utcnow()
    require_alias = MULTI_TENANT_SAME_INDEX and CREATE_INDEX_ALIAS_FOR_NAMESPACE
    for document in documents:
      document_id = self._rel_document_id(document)
      action = {
        "index": {
          "_index": index_name,
          "_id": document_id,
          "routing": routing,
          "pipeline": DEFAULT_INDEX_PIPELINE,
          "require_alias": require_alias,
        }
      }
      bulk_body.append(action)
      document_body = document.to_value()
      if MULTI_TENANT_SAME_INDEX:
        document_body[DOCUMENT_KEY_INTERNAL_NAMESPACE] = index_namespace
      document_body[DOCUMENT_KEY_INTERNAL_ID] = document.doc_id
      # document_body[DOCUMENT_KEY_INTERNAL_TIMESTAMP] = indexed_timestamp
      bulk_body.append(document_body)
    if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
      result = self.client.bulk(
        operations=bulk_body,
        index=index_name,
        request_timeout=deadline or None,
      )
    else:
      result = self.client.bulk(
        bulk_body,
        index=index_name,
        request_timeout=deadline or None,
      )
    self.client_return()
    # utilities.print_yaml(result)

    # result_ids = []
    # for item in result["items"]:
    #   result_ids.append(item['index']["_id"])
    # return result_ids

    return result
  
  def delete(self, document_ids, deadline=None, write_index_both=WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH):
  # def delete(self, document_ids, deadline=None):
    if not document_ids:
      return

    if write_index_both and IS_GAE and self.gae_instance:
      try:
        self.gae_instance.delete(document_ids, deadline=deadline)
      except Exception as e:
        logging.error(e, exc_info=True)

    if isinstance(document_ids, (list, tuple)):
      return self._delete_multiple(document_ids, deadline=deadline)
    else:
      return self._delete_single(document_ids, deadline=deadline)
  
  def _delete_single(self, document_id, deadline=None):
    document_id = self._rel_document_id(document_id)
    index_name = None
    if MULTI_TENANT_SAME_INDEX and CREATE_INDEX_ALIAS_FOR_NAMESPACE:
      index_name = self.alias
    else:
      index_name = self.fullname
    # require_alias = MULTI_TENANT_SAME_INDEX and CREATE_INDEX_ALIAS_FOR_NAMESPACE
    # if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
    #   self.client.options(ignore_status=[404])
    client = self.client
    if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
      client = client.options(ignore_status=[404])
    result = client.delete(
      index=index_name,
      id=document_id,
      routing=self._rel_routing(),
      # require_alias=require_alias,
      request_timeout=deadline or None,
      ignore=[404],
    )
    client = None
    self.client_return()
    return result
  
  def _delete_multiple(self, document_ids, deadline=None):
    # for document_id in document_ids:
    #   self._delete_single(document_id)

    bulk_body = []
    index_name = None
    if MULTI_TENANT_SAME_INDEX and CREATE_INDEX_ALIAS_FOR_NAMESPACE:
      index_name = self.alias
    else:
      index_name = self.fullname
    routing = self._rel_routing()
    # require_alias = MULTI_TENANT_SAME_INDEX and CREATE_INDEX_ALIAS_FOR_NAMESPACE
    for document_id in document_ids:
      document_id_rel = self._rel_document_id(document_id)
      action = {
        "delete": {
          "_index": index_name,
          "_id": document_id_rel,
          "routing": routing,
          # "require_alias": require_alias,
        }
      }
      bulk_body.append(action)
    
    if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
      # self.client.options(ignore_status=[404])
      client = self.client
      client = client.options(ignore_status=[404])
      results = client.bulk(
        operations=bulk_body,
        index=index_name,
        request_timeout=deadline or None,
        ignore=[404],
      )
      client = None
    else:
      results = self.client.bulk(
        bulk_body,
        index=index_name,
        request_timeout=deadline or None,
        ignore=[404],
      )
    self.client_return()
    return results
  
  def get(self, doc_id, deadline=None, return_raw=False):
    if not self.intialized:
      self.initialize()
    
    result = None
    index_name = None
    if MULTI_TENANT_SAME_INDEX and CREATE_INDEX_ALIAS_FOR_NAMESPACE:
      index_name = self.alias
    else:
      index_name = self.fullname
    doc_id_rel = self._rel_document_id(doc_id)
    # try:
    #   result = self.client.get(
    #     index=index_name,
    #     id=doc_id_rel,
    #     routing=self._rel_routing(),
    #     # ignore=[404],
    #   )
    # except elasticsearch.exceptions.NotFoundError:
    #   return None

    # if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
    #   self.client.options(ignore_status=[404])
    client = self.client
    if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
      client = client.options(ignore_status=[404])
    result = client.get(
      index=index_name,
      id=doc_id_rel,
      routing=self._rel_routing(),
      ignore=[404],
      request_timeout=deadline or None,
    )
    client = None
    self.client_return()
    if 'error' in result:
      if result['status'] == 404:
        err_info = result['error']
        err_msg = err_info['reason']
        logging.warning(err_msg)
        return None
      else:
        # raise SearchException(result['error']['reason'])
        if self.use_opensearch:
          raise OpenSearchException(result['error']['reason'])
        else:
          raise ElasticsearchException(result['error']['reason'])
    
    if return_raw:
      if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
        return result.body
      else:
        return result

    # # for performance, we don't need to convert to Document object because in Sateraito code we rarely use it
    # # just return result raw values is enough
    # res = result["_source"]
    # return res

    if not result["found"]:
      return None

    doc = Document.import_res(result['_id'], result["_source"], index=self)
    return doc

  def get_range(self, start_id=None, include_start_object=True, limit=100, ids_only=False, deadline=None, field_id_alt=DOCUMENT_KEY_INTERNAL_ID, return_raw=False):
    if not self.intialized:
      self.initialize()
    # Status: Not working because field '_id' in elsaticsearch is not only use for hash for fast access and not support range query on it value
    # Workaround: Use field 'field_id_alt' instead of '_id' when have it
    
    id_field = field_id_alt or "_id"
    if id_field == "_id" and start_id:
      start_id = self._rel_document_id(start_id)

    # if start_id is None:
    #   start_id = 0
    query = {
      "query": {
        # 'match_all' : {},
        # "range": {
        #   "_id": {
        #     "gte": start_id
        #   }
        # }
      },
      "size": limit,
      "sort": [
        {
          id_field: {
            "order": "asc",
            # "missing": "_first"
            # "missing": "_last"
          }
        }
      ]
      # "stored_fields": [
      #   "_id"
      # ],
      # "sort": {
      #   "_uid": "desc"
      # }
    }

    index_namespace = None
    if MULTI_TENANT_SAME_INDEX:
      index_namespace = self.namespace

    if start_id:
      query_range = None
      if not include_start_object:
        # query["query"]["range"]["_id"]["gt"] = start_id
        query_range = {
          id_field: {
            "gt": start_id
          }
        }
      else:
        # del query["query"]["range"]["_id"]["gte"]
        query_range = {
          id_field: {
            "gte": start_id
          }
        }
      if id_field != '_id':
        query["query"] = {
          "bool": {
            # "must": {
            #   "match_all": {}
            # },
            "must": [
              {
                "exists": {
                  "field": id_field
                }
              },
              {
                "range": query_range
              },
            ],
            # "filter": {
            #   "range": query_range
            # }
          }
        }
      if MULTI_TENANT_SAME_INDEX:
        query["query"]["bool"]["must"].append({
          "term": {
            DOCUMENT_KEY_INTERNAL_NAMESPACE: index_namespace
          }
        })
    else:
      # query["query"]["match_all"] = {}
      if id_field == "_id":
        # query["query"]["match_all"] = {}
        if MULTI_TENANT_SAME_INDEX:
          query["query"]["bool"] = {
            "must": [
              {
                "term": {
                  DOCUMENT_KEY_INTERNAL_NAMESPACE: index_namespace
                }
              }
            ]
          }
        else:
          query["query"]["match_all"] = {}
      else:
        query["query"] = {
          "bool": {
            "must": [
              {
                "exists": {
                  "field": id_field
                }
              },
            ]
          }
        }
        if MULTI_TENANT_SAME_INDEX:
          query["query"]["bool"]["must"].append({
            "term": {
              DOCUMENT_KEY_INTERNAL_NAMESPACE: index_namespace
            }
          })
    
    # if not start_id:
    #   del query["query"]["range"]["_id"]

    # q = elasticsearch_dsl.Q('range', _id={'gte':start_id})
    # s = elasticsearch_dsl.Search(using=self.client, index=self.fullname)
    # s = s.query(q)
    # response = s.execute()
    # return response
    
    index_name = None
    if MULTI_TENANT_SAME_INDEX and CREATE_INDEX_ALIAS_FOR_NAMESPACE:
      index_name = self.alias
    else:
      index_name = self.fullname

    # if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
    #   self.client.options(ignore_status=[404])
    client = self.client
    if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
      client = client.options(ignore_status=[404])
    result = client.search(
      index=index_name,
      body=query,
      routing=self._rel_routing(),
      ignore=[404],
      request_timeout=deadline or None,
    )
    client = None
    self.client_return()
    if 'error' in result:
      if result['status'] == 404:
        err_info = result['error']
        err_msg = err_info['reason']
        logging.warning(err_msg)
        return []
      else:
        # raise SearchException(result['error']['reason'])
        if self.use_opensearch:
          raise OpenSearchException(result['error']['reason'])
        else:
          raise ElasticsearchException(result['error']['reason'])

    if return_raw:
      if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
        return result.body
      else:
        return result
    
    if ids_only:
      # ids = [hit["_id"] for hit in result["hits"]["hits"]]
      # return ids

      documents = []
      empty_fields = []
      for hit in result["hits"]["hits"]:
        doc = Document.import_res(hit["_id"], empty_fields, index=self)
        documents.append(doc)
      return documents

    else:
      documents = []
      for hit in result["hits"]["hits"]:
        doc = Document.import_res(hit["_id"], hit["_source"], index=self)
        documents.append(doc)
      return documents

  def search(self, query, deadline=None, return_raw=False, auto_convert_query_string=AUTO_CONVERT_QUERY_STRING_GAE_SEARCH_TO_ELASTICSEARCH):
    if not self.intialized:
      self.initialize()

    query_body = query.to_value()
    # logging.debug("Query:\n%s", utilities.dump_yaml(query_body))
    query_size = query_body.get("size")
    if not query_size:
      # if not specific query 'size' then elsaticsearch will return only 10 documents by default
      # set default query 'size' to 20 to mimic GAE Search API
      query_body["size"] = 20

    query_string = query_body["query"]["query_string"]
    if not query_string.get("query"):
      # if query string is empty then elsaticsearch will return all documents by default
      # set query string to '*' to mimic GAE Search API
      query_string["query"] = "*"
    else:
      logging.info("ElasticSearch Query String: %s" % query_string["query"])
      
      query_string["default_operator"] = "AND"
      # query_string["analyze_wildcard"] = True
      # query_string["allow_leading_wildcard"] = True
      # # query_string["lenient"] = True

      # # TODO: better handler unescaped double quotes in query string
      # if re.match(r'^"[^"]+"$', query_string["query"]):
      #   query_string["query"] = query_string["query"][1:-1]
    
    if auto_convert_query_string:
      query_string = query_body["query"]["query_string"]
      query_string_query = query_string.get("query")
      if query_string_query and query_string_query != "*":
        # if re.match(r'^"[^"]+"$', query_string_query):
        #   query_string_query = query_string_query[1:-1]
        query_string_query_alt = search_adapt.convert_query_string_gae_search_to_elasticsearch(query_string_query)
        if query_string_query_alt != query_string.get("query"):
          query_string["query"] = query_string_query_alt
          logging.info("Converted to Query String: %s" % query_string_query_alt)

    if MULTI_TENANT_SAME_INDEX:
      index_namespace = self.namespace
      del query_body["query"]["query_string"]
      query_body["query"]["bool"] = {
        "must": [
          {
            "term": {
              DOCUMENT_KEY_INTERNAL_NAMESPACE: index_namespace
            }
          },
          {
            "query_string": query_string
          }
        ]
      }
      # query_body["query"]["bool"]["must"].append({
      #   "term": {
      #     DOCUMENT_KEY_INTERNAL_NAMESPACE: index_namespace
      #   }
      # })
    
    query_sort = query_body.get("sort")
    if not query_sort:
      # add default sort to make elsaticsearch return sort value that can be use to mimic GAE Search API cursor
      # sort_field = "_id"
      # field '_id' is meta field of elasticsearch but not support sorting by default. so we use custom internal timestamp field instead
      sort_field = DOCUMENT_KEY_INTERNAL_TIMESTAMP
      query_body["sort"] = [
        {
          sort_field: {
            # "order": "asc",
            "order": "desc",
            # "missing": "_first"
            # "missing": "_last"
          }
        }
      ]

    index_name = None
    if MULTI_TENANT_SAME_INDEX and CREATE_INDEX_ALIAS_FOR_NAMESPACE:
      index_name = self.alias
    else:
      index_name = self.fullname
    #logging.debug("ElasticSearch Search: %s", json.dumps(query_body, indent=2, sort_keys=True))
    logging.debug("ElasticSearch Search: %s" % json.dumps(query_body, indent=2, sort_keys=True))
    query_sort = query_body.get("sort")
    if query_sort and self.mappings:
      mapping_propertis = self.mappings['properties']
      if isinstance(query_sort, list):
        invalid_fields = []
        for sort in query_sort:
          for field in sort:
            if field not in mapping_propertis:
              invalid_fields.append(field)
        if invalid_fields:
          query_sort_new = []
          for sort in query_sort:
            for field in invalid_fields:
              if field in sort:
                del sort[field]
                logging.warning("ElasticSearch remove invalid sort field: {}".format(field))
            if sort:
              query_sort_new.append(sort)
          if not query_sort_new:
            # replace with default sort when all sort fields are invalid
            query_sort_new = [{
              DOCUMENT_KEY_INTERNAL_TIMESTAMP: {
                "order": "desc",
              }
            }]
          query_body["sort"] = query_sort_new
      elif isinstance(query_sort, dict):
        invalid_fields = []
        for field in query_sort:
          if field not in mapping_propertis:
            invalid_fields.append(field)
        if invalid_fields:
          for field in invalid_fields:
            del query_sort[field]
            logging.warning("ElasticSearch remove invalid sort field: {}".format(field))
          if not query_sort:
            # replace with default sort when all sort fields are invalid
            query_sort[DOCUMENT_KEY_INTERNAL_TIMESTAMP] = {
              "order": "desc",
            }

    # if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
    #   self.client.options(ignore_status=[404])
    client = self.client
    if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
      client = client.options(ignore_status=[404])
    result = client.search(
      index=index_name,
      body=query_body,
      routing=self._rel_routing(),
      ignore=[404],
      request_timeout=deadline or None,
    )
    client = None
    self.client_return()
    if 'error' in result:
      if result['status'] == 404:
        err_info = result['error']
        err_msg = err_info['reason']
        logging.warning(err_msg)
        # return []
        return SearchResults(number_found=0, results=[])
      else:
        # raise SearchException(result['error']['reason'])
        if self.use_opensearch:
          raise OpenSearchException(result['error']['reason'])
        else:
          raise ElasticsearchException(result['error']['reason'])

    if return_raw:
      if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
        return result.body
      else:
        return result
    
    # TODO: make result object like google app engine search api
    documents = []
    doc_hits = result["hits"]["hits"]
    query_cursor_per_result = query.options and query.options.cursor and query.options.cursor.per_result
    for hit in doc_hits:
      doc_id = hit["_id"]
      doc_fields = hit["_source"] if "_source" in hit else {}
      doc = Document.import_res(doc_id, doc_fields, index=self)
      if query_cursor_per_result:
        hit_sort = hit.get("sort")
        if hit_sort:
          hit_sort_val = json.dumps(hit_sort)
          doc.cursor = Cursor(hit_sort_val)
      documents.append(doc)
    total_hits = result["hits"]["total"]["value"]
    # elasticsearch return 10k results total hits by default setting
    search_results = SearchResults(number_found=total_hits, results=documents)
    query_limit = query.options and query.options.limit
    if doc_hits:
      if not query_limit:
        # default elasticsearch setting limit to 10k results returned in 1 query
        query_limit = 10000
      # TODO: better check that query have more results to set cursor
      if len(doc_hits) == query_limit and (total_hits > query_limit or total_hits == 10000):
        # only have sort value if there is sort in query
        last_hit_doc = doc_hits[-1]
        last_sort_val = last_hit_doc["sort"]
        if isinstance(last_sort_val, list):
          # fake search cursor
          # cursor = Cursor(last_sort_val)
          last_sort_val_str = json.dumps(last_sort_val)
          # # last_sort_val_str = base64.b64encode(last_sort_val_str.encode("utf-8"))
          # last_sort_val_str = base64.b64encode(last_sort_val_str)
          cursor = Cursor(last_sort_val_str)
          # setattr(documents, "cursor", cursor)
          search_results.cursor = cursor
    
    # if not hasattr(documents, "cursor"):
    #   setattr(documents, "cursor", None)
    # return documents

    return search_results
  
  def clear(self, remove_alias=False, remove_index=False):
    if not self.intialized:
      self.initialize()
    
    if not self.created:
      return
    
    if not MULTI_TENANT_SAME_INDEX:
      if remove_index:
        # TODO: handle error
        # if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
        #   self.client.options(ignore_status=[404])
        client = self.client
        if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
          client = client.options(ignore_status=[404])
        result = client.indices.delete(index=self.fullname, ignore=[404])
        client = None
        self.client_return()
        result_error = result.get('error')
        if result_error and result['status'] == 404:
          logging.warning(result['error']['reason'])
        self.uninitialize()
      else:
        # if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
        #   self.client.options(ignore_status=[404])
        client = self.client
        if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
          client = client.options(ignore_status=[404])
        result = client.delete_by_query(index=self.fullname, body={"query": {"match_all": {}}}, ignore=[404])
        client = None
        self.client_return()
        result_error = result.get('error')
        if result_error and result['status'] == 404:
          logging.warning(result['error']['reason'])
      return

    if CREATE_INDEX_ALIAS_FOR_NAMESPACE:
      if self.alias_created:
        # if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
        #   self.client.options(ignore_status=[404])
        client = self.client
        if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
          client = client.options(ignore_status=[404])
        result = client.delete_by_query(
          index=self.alias,
          body={"query": {"match_all": {}}},
          routing=self._rel_routing(),
          ignore=[404],
        )
        client = None
        self.client_return()
        result_error = result.get('error')
        if result_error and result['status'] == 404:
          logging.warning(result['error']['reason'])
        else:
          if remove_alias:
            # TODO: handle except
            # if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
            #   self.client.options(ignore_status=[404])
            client = self.client
            if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
              client = client.options(ignore_status=[404])
            result = client.indices.delete_alias(
              index=self.fullname,
              name=self.alias,
              ignore=[404]
            )
            client = None
            self.client_return()
            result_error = result.get('error')
            if result_error and result['status'] == 404:
              logging.warning(result['error']['reason'])
            self.uninitialize()
        return
    
    body = {
      "query": {
        "term": {
          DOCUMENT_KEY_INTERNAL_NAMESPACE: self.namespace
        }
      }
    }
    # if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
    #   self.client.options(ignore_status=[404])
    client = self.client
    if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
      client = client.options(ignore_status=[404])
    result = client.delete_by_query(
      index=self.fullname,
      body=body,
      routing=self._rel_routing(),
      ignore=[404],
    )
    client = None
    self.client_return()
    result_error = result.get('error')
    if result_error and result['status'] == 404:
      logging.warning(result['error']['reason'])
    else:
      if remove_index:
        if MULTI_TENANT_SAME_INDEX:
          # not allow to delete index when have multi tenant share the same index
          return
        # TODO: handle except
        # if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
        #   self.client.options(ignore_status=[404])
        client = self.client
        if not self.use_opensearch and IS_ELASTICSEARCH_NEW:
          client = client.options(ignore_status=[404])
        result = client.indices.delete(
          index=self.fullname,
          ignore=[404]
        )
        client = None
        self.client_return()
        result_error = result.get('error')
        if result_error and result['status'] == 404:
          logging.warning(result['error']['reason'])
        self.uninitialize()


if WRITE_INDEX_BOTH_ELASTICSEARCH_AND_OPENSEARCH:
  class Index(object):
    def __init__(self, name, namespace=None, client=None, write_index_both=WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH, use_opensearch=USE_OPENSEARCH):
      self.use_opensearch = use_opensearch
      client_es = None
      client_os = None
      if client:
        if isinstance(client, opensearchpy.OpenSearch):
          client_es = client
        elif isinstance(client, elasticsearch.Elasticsearch):
          client_os = client
      self._instance_elasticsearch = IndexInstance(name, namespace=namespace, client=client_es, write_index_both=write_index_both, use_opensearch=False)
      self._instance_opensearch = IndexInstance(name, namespace=namespace, client=client_os, write_index_both=False, use_opensearch=True)

    def put(self, documents, deadline=None, skip_mapping=False, mapping_all=False, write_index_both=WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH):
      if isinstance(documents, (list, tuple)):
        for document in documents:
          if not document.doc_id:
            document.doc_id = generate_random_document_id()
      else:
        doc = documents
        if not doc.doc_id:
          doc.doc_id = generate_random_document_id()
      # res_elasticsearch = self._instance_elasticsearch.put(documents, deadline=deadline, skip_mapping=skip_mapping, mapping_all=mapping_all, write_index_both=write_index_both)
      # res_opensearch = self._instance_opensearch.put(documents, deadline=deadline, skip_mapping=skip_mapping, mapping_all=mapping_all, write_index_both=False)
      # res = res_elasticsearch
      # if self.use_opensearch:
      #   res = res_opensearch
      # return res
      if self.use_opensearch:
        instance_main = self._instance_opensearch
        instance_other = self._instance_elasticsearch
      else:
        instance_main = self._instance_elasticsearch
        instance_other = self._instance_opensearch
      res_main = instance_main.put(documents, deadline=deadline, skip_mapping=skip_mapping, mapping_all=mapping_all, write_index_both=write_index_both)
      try:
        res_other = instance_other.put(documents, deadline=deadline, skip_mapping=skip_mapping, mapping_all=mapping_all, write_index_both=False)
      except Exception as e:
        logging.error(e, exc_info=True)
      return res_main

    def delete(self, document_ids, deadline=None, write_index_both=WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH):
      # res_elasticsearch = self._instance_elasticsearch.delete(document_ids, deadline=deadline, write_index_both=write_index_both)
      # res_opensearch = self._instance_opensearch.delete(document_ids, deadline=deadline, write_index_both=False)
      # res = res_elasticsearch
      # if self.use_opensearch:
      #   res = res_opensearch
      # return res
      if self.use_opensearch:
        instance_main = self._instance_opensearch
        instance_other = self._instance_elasticsearch
      else:
        instance_main = self._instance_elasticsearch
        instance_other = self._instance_opensearch
      res_main = instance_main.delete(document_ids, deadline=deadline, write_index_both=write_index_both)
      try:
        res_other = instance_other.delete(document_ids, deadline=deadline, write_index_both=False)
      except Exception as e:
        logging.error(e, exc_info=True)
      return res_main

    def get(self, doc_id, deadline=None, return_raw=False):
      instance = self._instance_elasticsearch
      if self.use_opensearch:
        instance = self._instance_opensearch
      return instance.get(doc_id, deadline=deadline, return_raw=return_raw)

    def get_range(self, start_id=None, include_start_object=True, limit=100, ids_only=False, deadline=None, field_id_alt=DOCUMENT_KEY_INTERNAL_ID, return_raw=False):
      instance = self._instance_elasticsearch
      if self.use_opensearch:
        instance = self._instance_opensearch
      return instance.get_range(start_id=start_id, include_start_object=include_start_object, limit=limit, ids_only=ids_only, deadline=deadline, field_id_alt=field_id_alt, return_raw=return_raw)

    def search(self, query, deadline=None, return_raw=False, auto_convert_query_string=AUTO_CONVERT_QUERY_STRING_GAE_SEARCH_TO_ELASTICSEARCH):
      instance = self._instance_elasticsearch
      if self.use_opensearch:
        instance = self._instance_opensearch
      return instance.search(query, deadline=deadline, return_raw=return_raw, auto_convert_query_string=auto_convert_query_string)

    def clear(self, remove_alias=False, remove_index=False):
      # res_elasticsearch = self._instance_elasticsearch.clear(remove_alias=remove_alias, remove_index=remove_index)
      # res_opensearch = self._instance_opensearch.clear(remove_alias=remove_alias, remove_index=remove_index)
      # res = res_elasticsearch
      # if self.use_opensearch:
      #   res = res_opensearch
      # return res
      # self._instance_elasticsearch.clear(remove_alias=remove_alias, remove_index=remove_index)
      # self._instance_opensearch.clear(remove_alias=remove_alias, remove_index=remove_index)
      if self.use_opensearch:
        instance_main = self._instance_opensearch
        instance_other = self._instance_elasticsearch
      else:
        instance_main = self._instance_elasticsearch
        instance_other = self._instance_opensearch
      instance_main.clear(remove_alias=remove_alias, remove_index=remove_index)
      try:
        instance_other.clear(remove_alias=remove_alias, remove_index=remove_index)
      except Exception as e:
        logging.error(e, exc_info=True)


else:
  class Index(IndexInstance):
    pass


# class that mimic Google App Engine Search API 'Query'
class Query(object):
  def __init__(self, query_string, options=None, enable_facet_discovery=False, return_facets=None, facet_options=None, facet_refinements=None):
    # ignore all facet parameters for because Elasticsearch doesn't support it
    self.query_string = query_string
    self.options = options

  def to_value(self):
    res = {}
    if self.options:
      res_options = self.options.to_value()
      res.update(res_options)
    
    query = {
      "query_string": {
        "query": self.query_string
      }
    }
    res["query"] = query
    
    return res
  
  def __str__(self):
    return json.dumps(self.to_value(), sort_keys=True)


# class that mimic Google App Engine Search API 'QueryOptions'
class QueryOptions(object):
  def __init__(self, limit=20, number_found_accuracy=None, cursor=None, offset=None, sort_options=None, returned_fields=None, ids_only=False,  snippeted_fields=None, returned_expressions=None):
    # number_found_accuracy = number_found_accuracy or 1000
    # TODO: handle snippeted_fields and returned_expressions

    # ignore number_found_accuracy for now
    self.number_found_accuracy = number_found_accuracy
    self.cursor = cursor
    self.limit = limit
    self.offset = offset
    self.sort_options = sort_options
    self.returned_fields = returned_fields
    self.ids_only = ids_only

  def to_value(self):
    res = {}

    if self.limit:
      res["size"] = self.limit
    if self.offset:
      res["from"] = self.offset
    if self.sort_options:
      res["sort"] = self.sort_options.to_value()
    if self.cursor:
      cursor_value = self.cursor.to_value()
      if cursor_value:
        res["search_after"] = cursor_value
    
    if self.returned_fields:
      if len(self.returned_fields) == 1:
        res["_source"] = self.returned_fields[0]
      else:
        # res["_source"] = {
        #   "fields": {
        #     "includes": [fld for fld in self.returned_fields]
        #   }
        # }
        res["_source"] = [fld for fld in self.returned_fields if fld]

    if self.ids_only:
      res["_source"] = False
    
    return res
  
  def __str__(self):
    return json.dumps(self.to_value(), sort_keys=True)


# class that mimic Google App Engine Search API 'SortOptions'
class SortOptions(object):
  def __init__(self, expressions=None, match_scorer=None, limit=1000):
    # TODO: handle match_scorer
    self.expressions = expressions
    self.match_scorer = match_scorer
    # Elasticsearch doesn't support limit for sort, so we ignore it
    self.limit = limit
  
  def to_value(self):
    sort_options = []
    for expression in self.expressions:
      if not expression:
        continue
      if not expression.expression:
        logging.warning("Skip sort expression that is invalid: " + str(expression))
        continue
      sort_options.append(expression.to_value())
    return sort_options
  
  def __str__(self):
    sort_options = []
    for expression in self.expressions:
      if expression:
        sort_options.append(expression.to_value())
      else:
        sort_options.append(None)
    return json.dumps(sort_options, sort_keys=True)


# class that mimic Google App Engine Search API 'SortExpression'
class SortExpression(object):
  # ASCENDING =  'asc'
  # DESCENDING =  'desc'
  ASCENDING =  'ASCENDING'
  DESCENDING =  'DESCENDING'

  def __init__(self, expression, direction=None, default_value=None):
    # TODO: current only support simple expression that only field name, not support complex expression
    self.expression = expression
    self.direction = direction
    self.default_value = default_value
  
  def to_value(self):
    res = {
      self.expression: {
        "order": "asc" if self.direction == SortExpression.ASCENDING else "desc",
        "missing": self.default_value
      }
    }
    return res

  def __str__(self):
    return json.dumps(self.to_value(), sort_keys=True)


class Cursor():
  def __init__(self, web_safe_string=None, per_result=False):
    self.web_safe_string = web_safe_string
    # ignore per_result for now
    self.per_result = per_result
  
  def to_value(self):
    if not self.web_safe_string:
      return None
    try:
      str_val = self.web_safe_string
      # str_val = base64.b64decode(self.str_val)
      val = json.loads(str_val)
      return val
    except Exception as e:
      logging.warning("Failed to decode cursor: %s" % e)
    return None

  def __str__(self):
    return self.web_safe_string


class SearchResults():
  def __init__(self, number_found, results=None, cursor=None):
    self.number_found = number_found
    self.results = results
    self.cursor = cursor
  
  def __iter__(self):
    return iter(self.results)

  def __len__(self):
    return len(self.results)


# TODO: custom handle error match GAE Search API
Error = Exception
PutError = Exception
InternalError = Exception
DeleteError = Exception
# TransientError = Exception  # TODO: handle Elasticsearch exception like transient error
class TransientError(Exception):
  "current not be raise at all because Elasticsearch doesn't have custom TransientError class like GAE but support automatic retry"
  # TODO: catch Elasticsearch error with behave like TransientError
  pass
InvalidRequest = Exception
