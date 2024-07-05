
import re

# sateraito_inc = None
# try:
#   import sateraito_inc
# except:
#   sateraito_inc = None
import sateraito_inc

from . import utilities


# mimic google app engine search api datetime field:
# ref: https://cloud.google.com/appengine/docs/legacy/standard/python/search#field-accuracy
ROUND_DATETIME_AS_GAE = sateraito_inc.ES_ROUND_DATETIME_AS_GAE


MULTI_TENANT_SAME_INDEX = sateraito_inc.ES_MULTI_TENANT_SAME_INDEX
CREATE_INDEX_ALIAS_FOR_NAMESPACE = sateraito_inc.ES_CREATE_INDEX_ALIAS_FOR_NAMESPACE

WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH = sateraito_inc.ES_WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH
if WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH and not (utilities.IS_GAE and not utilities.IS_PYTHON_3):
  WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH = False

PROJECT_ID_INDEX_PREFIX = sateraito_inc.ES_PROJECT_ID_INDEX_PREFIX


PROJECT_ID_INDEX_SEPARATOR = sateraito_inc.ES_PROJECT_ID_INDEX_SEPARATOR
NAMESPACE_SEPARATOR_INDEX = sateraito_inc.ES_NAMESPACE_SEPARATOR_INDEX
NAMESPACE_SEPARATOR_DOCUMENT = sateraito_inc.ES_NAMESPACE_SEPARATOR_DOCUMENT

NAMESPACE_GLOBAL = sateraito_inc.ES_NAMESPACE_GLOBAL
DOCUMENT_KEY_INTERNAL_NAMESPACE = sateraito_inc.ES_DOCUMENT_KEY_INTERNAL_NAMESPACE
DOCUMENT_KEY_INTERNAL_ID = sateraito_inc.ES_DOCUMENT_KEY_INTERNAL_ID
DOCUMENT_KEY_INTERNAL_TIMESTAMP = sateraito_inc.ES_DOCUMENT_KEY_INTERNAL_TIMESTAMP


ES_CLOUD_ID = sateraito_inc.ES_CLOUD_ID
ES_AUTH_USER = sateraito_inc.ES_AUTH_USER
ES_AUTH_PASSWORD = sateraito_inc.ES_AUTH_PASSWORD
ES_HTTP_AUTH = sateraito_inc.ES_HTTP_AUTH


ELASTICSEARCH_TIMEOUT = sateraito_inc.ES_ELASTICSEARCH_TIMEOUT

# default number of sharps of a index when create new index
DEFAULT_NUMBER_OF_SHARDS = sateraito_inc.ES_DEFAULT_NUMBER_OF_SHARDS
# default number copy of a sharp when create new index
DEFAULT_NUMBER_OF_REPLICAS = sateraito_inc.ES_DEFAULT_NUMBER_OF_REPLICAS

# custom dict config settings apply for index by match regex pattern with index name
# INDEX_SETTINGS = (
#   (re.compile('test'), {
#     # # https://www.elastic.co/guide/en/elasticsearch/reference/current/size-your-shards.html
#     # "number_of_shards": DEFAULT_NUMBER_OF_SHARDS,
#     # "number_of_replicas": DEFAULT_NUMBER_OF_REPLICAS,
#     # # https://www.elastic.co/guide/en/elasticsearch/reference/current/data-tiers.html
#     # "index.routing.allocation.include._tier_preference": "data_hot",
#   }),
# )
INDEX_SETTINGS = []
for pairs in sateraito_inc.ES_INDEX_SETTINGS:
  INDEX_SETTINGS.append((re.compile(pairs[0]), pairs[1]))

# custom dict config mappings apply for index by match regex pattern with index name
# INDEX_MAPPINGS = (
#   (re.compile('test'), {
#     # "properties": {
#     #   "@id": {
#     #     "type": "keyword",
#     #   }
#     #   "@namespace": {
#     #     "type": "keyword",
#     #   },
#     #   "@timestamp": {
#     #     "type": "date",
#     #   }
#     # }
#   }),
# )
INDEX_MAPPINGS = []
for pairs in sateraito_inc.ES_INDEX_MAPPINGS:
  INDEX_MAPPINGS.append((re.compile(pairs[0]), pairs[1]))


USE_ELASTICSEARCH_DOMAINS = sateraito_inc.ES_USE_ELASTICSEARCH_DOMAINS



USE_OPENSEARCH = sateraito_inc.OS_PREFER_USE_OPENSEARCH

OS_AWS_ENDPOINT = sateraito_inc.OS_AWS_ENDPOINT

OS_AUTH_USER = sateraito_inc.OS_AUTH_USER
OS_AUTH_PASSWORD = sateraito_inc.OS_AUTH_PASSWORD
OS_HTTP_AUTH = sateraito_inc.OS_HTTP_AUTH

WRITE_INDEX_BOTH_ELASTICSEARCH_AND_OPENSEARCH = sateraito_inc.OS_WRITE_INDEX_BOTH_ELASTICSEARCH_AND_OPENSEARCH
