# encoding: utf-8

import os

import json

import re
import threading

# import ssl
# import certifi


# import elasticsearch_inc
# import utilities
from . import elasticsearch_inc
from . import utilities


# import requests
# import httplib

# from httplib2 import Http
# http = Http()
# http.add_credentials(elasticsearch_inc.ES_AUTH_USER, elasticsearch_inc.ES_AUTH_PASSWORD)

# from http.client import HTTPConnection

# import urllib2


# # Changes the underlying 'urllib3' HTTP client to use App Engine URLFetch instead of sockets.
# # Note this takes affect for all uses of requests in your project.
# import requests_toolbelt.adapters.appengine
# requests_toolbelt.adapters.appengine.monkeypatch()


ELASTICSEARCH_TIMEOUT = elasticsearch_inc.ELASTICSEARCH_TIMEOUT


DEFAULT_NUMBER_OF_SHARDS = elasticsearch_inc.DEFAULT_NUMBER_OF_SHARDS
DEFAULT_NUMBER_OF_REPLICAS = elasticsearch_inc.DEFAULT_NUMBER_OF_REPLICAS


INDEX_SETTINGS = elasticsearch_inc.INDEX_SETTINGS

INDEX_MAPPINGS = elasticsearch_inc.INDEX_MAPPINGS


# use pool instances of elasticsearch clients to skip the overhead of re-authentication when create new connections?
POOL_QUEUE_MAX = 5
POOL_QUEUE_LOCK_ELASTICSEARCH = threading.Lock()
POOL_QUEUE_CLIENTS_ELASTICSEARCH = []
POOL_QUEUE_LOCK_OPENSEARCH = threading.Lock()
POOL_QUEUE_CLIENTS_OPENSEARCH = []


USE_OPENSEARCH = elasticsearch_inc.USE_OPENSEARCH
OS_AWS_ENDPOINT = elasticsearch_inc.OS_AWS_ENDPOINT
OS_HTTP_AUTH = elasticsearch_inc.OS_HTTP_AUTH

import elasticsearch
IS_ELASTICSEARCH_NEW = elasticsearch.VERSION >= (8, 0, 0)

import opensearchpy


# CA_CERTS = os.path.join(os.path.dirname(__file__), 'cacert.pem')
# CA_CERTS = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'cacert.pem')

# SSL_CONTEXT = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=certifi.where())
# SSL_CONTEXT.check_hostname = False
# SSL_CONTEXT.verify_mode = ssl.CERT_NONE


# class RequestsHttpConnection:
#   def __init__(self, host, **kwargs):
#     self.host = host
# 
#   def perform_request(self, method, url, params=None, body=None, headers=None):
#     url = self.host + url
#     return requests.request(method=method, url=url, params=params, data=body, headers=headers)
# 
# class RequestsTransport(elasticsearch.Transport):
#   def __init__(self, *args, **kwargs):
#     super(RequestsTransport, self).__init__(*args, **kwargs)
#     self.connection_pool.connection_cls = RequestsHttpConnection


# class MyConnection(elasticsearch.connection.Connection):
#   def __init__(self, *args, **kwargs):
#     super(MyConnection, self).__init__(*args, **kwargs)
# 
#   def _create_connection(self, *args, **kwargs):
#     return httplib.HTTPConnection(*args, **kwargs)
#   
#   def perform_request(self, method, url, params=None, body=None, timeout=None, ignore=(), headers=None):
#     if body:
#       body = body.encode('utf-8')
#     return super(MyConnection, self).perform_request(method, url, params, body, timeout, ignore, headers)


# class JSONSerializerPython2(elasticsearch.serializer.JSONSerializer):
#   """
#   Override elasticsearch library serializer to ensure it encodes utf characters during json dump.
#   See original at: https://github.com/elastic/elasticsearch-py/blob/master/elasticsearch/serializer.py#L42
#   A description of how ensure_ascii encodes unicode characters to ensure they can be sent across the wire
#   as ascii can be found here: https://docs.python.org/2/library/json.html#basic-usage
#   """
#   def dumps(self, data):
#     # don't serialize strings
#     if isinstance(data, elasticsearch.compat.string_types):
#       return data
#     try:
#       return json.dumps(data, default=self.default, ensure_ascii=True)
#     except (ValueError, TypeError) as e:
#       raise elasticsearch.exceptions.SerializationError(data, e)


# class Urllib2Connection(urllib2.HTTPSHandler):
#   def __init__(self, host, *args, **kwargs):
#     super(Urllib2Connection, self).__init__(*args, **kwargs)
#     self.host = host
# 
#   def https_open(self, req):
#     return self.do_open(self.getConnection, req)
# 
#   def getConnection(self, host, timeout=None):
#     return httplib.HTTPSConnection(self.host, timeout=timeout)


# class Urllib2HttpConnection(elasticsearch.connection.RequestsHttpConnection):
#   def __init__(self, *args, **kwargs):
#     super(Urllib2HttpConnection, self).__init__(*args, **kwargs)
# 
#   def _create_connection(self, *args, **kwargs):
#     return urllib2.urlopen(*args, **kwargs)


def get_client_elasticsearch():
  if IS_ELASTICSEARCH_NEW:
    parameters = dict(
      cloud_id=elasticsearch_inc.ES_CLOUD_ID,
      http_auth=elasticsearch_inc.ES_HTTP_AUTH,
      http_compress=True,
      # use_ssl=True,
      verify_certs=True,
      # send_get_body_as='POST',
      timeout=ELASTICSEARCH_TIMEOUT,
    )
  else:
    # TODO: implement connection_class with python 2 support Fetch URL service of App Engine Python 2.7 SDK
    parameters = dict(
      cloud_id=elasticsearch_inc.ES_CLOUD_ID,
      http_auth=elasticsearch_inc.ES_HTTP_AUTH,
      # http_auth=http,
      # connection_class=Http,
      http_compress=True,
      # use_ssl=True,
      verify_certs=True,
      # # TODO: implement use ssl and verify certs in production
      # use_ssl=False,
      # verify_certs=False,
      # ssl_context=SSL_CONTEXT,,
      # ca_certs=certifi.where(),
      # ca_certs=CA_CERTS,
      send_get_body_as='POST',
      timeout=ELASTICSEARCH_TIMEOUT,
      # transport_class=RequestsTransport,
      # connection_class=RequestsHttpConnection,
      # connection_class=MyConnection,
      # connection_class=httplib.HTTPConnection,
      # connection_class=elasticsearch.connections.RequestsHttpConnection,
      # connection_class=elasticsearch.RequestsHttpConnection,
      # serializer=JSONSerializerPython2(),
      # connection_class=HTTPConnection,
      # connection_class=Urllib2Connection,
      # connection_class=Urllib2HttpConnection,
    )
    
  es = elasticsearch.Elasticsearch(**parameters)
  return es


def get_client_opensearch():
  client = opensearchpy.OpenSearch(
    OS_AWS_ENDPOINT,
    http_auth=OS_HTTP_AUTH,
    http_compress=True,
    use_ssl=True,
    verify_certs=True,
    send_get_body_as='POST',
    timeout=30,
  )
  return client


def get_client(use_opensearch=USE_OPENSEARCH):
  if use_opensearch:
    return get_client_opensearch()
  else:
    return get_client_elasticsearch()


def borrow_client(use_opensearch=USE_OPENSEARCH):
  client = None

  if use_opensearch:
    POOL_QUEUE_LOCK_OPENSEARCH.acquire()
    # global POOL_QUEUE_CLIENTS_OPENSEARCH
    if POOL_QUEUE_CLIENTS_OPENSEARCH:
      client = POOL_QUEUE_CLIENTS_OPENSEARCH.pop()
    POOL_QUEUE_LOCK_OPENSEARCH.release()
  else:
    POOL_QUEUE_LOCK_ELASTICSEARCH.acquire()
    # global POOL_QUEUE_CLIENTS_ELASTICSEARCH
    if POOL_QUEUE_CLIENTS_ELASTICSEARCH:
      client = POOL_QUEUE_CLIENTS_ELASTICSEARCH.pop()
    POOL_QUEUE_LOCK_ELASTICSEARCH.release()

  if not client:
    client = get_client(use_opensearch=use_opensearch)
  
  return client


def return_client(client):
  returned = False

  if not client:
    raise Exception('Invalid client: %s' % client)
  
  if isinstance(client, opensearchpy.OpenSearch):
    POOL_QUEUE_LOCK_OPENSEARCH.acquire()
    # global POOL_QUEUE_CLIENTS_OPENSEARCH
    if len(POOL_QUEUE_CLIENTS_OPENSEARCH) < POOL_QUEUE_MAX:
      POOL_QUEUE_CLIENTS_OPENSEARCH.append(client)
      returned = True
    POOL_QUEUE_LOCK_OPENSEARCH.release()

  elif isinstance(client, elasticsearch.Elasticsearch):
    POOL_QUEUE_LOCK_ELASTICSEARCH.acquire()
    # global POOL_QUEUE_CLIENTS_ELASTICSEARCH
    if len(POOL_QUEUE_CLIENTS_ELASTICSEARCH) < POOL_QUEUE_MAX:
      POOL_QUEUE_CLIENTS_ELASTICSEARCH.append(client)
      returned = True
    POOL_QUEUE_LOCK_ELASTICSEARCH.release()
  
  else:
    raise Exception('Invalid client type: %s' % type(client))
  
  return returned


def get_index_settings(index_name):
  settings = {
    "number_of_shards": DEFAULT_NUMBER_OF_SHARDS,
    "number_of_replicas": DEFAULT_NUMBER_OF_REPLICAS,
  }

  for pair in INDEX_SETTINGS:
    if not pair:
      continue
    re_pattern = pair[0]
    overwrite_settings = pair[1]
    if not re_pattern or not overwrite_settings:
      continue
    if re.match(re_pattern, index_name):
      # settings.update(overwrite_settings)
      utilities.update_deep(settings, overwrite_settings)
  
  return settings


def get_index_mappings(index_name):
  mappings = {}

  for pair in INDEX_MAPPINGS:
    if not pair:
      continue
    re_pattern = pair[0]
    overwrite_mappings = pair[1]
    if not re_pattern or not overwrite_mappings:
      continue
    if re.match(re_pattern, index_name):
      # mappings.update(overwrite_mappings)
      utilities.update_deep(mappings, overwrite_mappings)
  
  return mappings

