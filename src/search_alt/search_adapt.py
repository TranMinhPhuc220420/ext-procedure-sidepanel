# encoding: utf-8

# import os
# import sys

import re
# import uuid
import random
import string


# import utilities
from . import utilities
IS_GAE = utilities.check_is_running_gae()
IS_PYTHON_3 = utilities.IS_PYTHON_3

import json
if IS_GAE and IS_PYTHON_3:
  import sateraito_logger as logging
else:
  import logging

# import elasticsearch_inc
from . import elasticsearch_inc

if IS_GAE:
  from google.appengine.api import namespace_manager
  from google.appengine.api import memcache
  # from google.appengine.api import search
  from google.appengine.ext import ndb

  sateraito_func = None
  try:
    import sateraito_func
  except:
    pass

  # import db_migrate
  from . import db_migrate

else:
  namespace_manager = None
  memcache = None
  # search = None
  ndb = None

  sateraito_func = None

  db_migrate = None


STRING_RAMDOM_CHARACTERS = string.ascii_lowercase + string.digits


LIST_REGEX_CONVERT_QUERY = (
  [r'^"([^"]+)"$', r'\1'],
  [r'^""([^"]+)""$', r'"\1"'],
  [r'^""([^"]+)""(\s+.+)$', r'"\1"\2'],
  [r'^"([^"\s]+)"(\s+.+)$', r'\1\2'],
  [r'\(\s*"([^"\s]+)"\s*\)', r'\1'],
  [r'\(\s*""([^"\s]+)""\s*\)', r'"\1"'],
  [r'([a-zA-Z][A-Za-z0-9_]*)((?:\s*)(?:>=|<=|>|<)(?![<=>])\s*)', r'\1:\2'],
  [r'([a-zA-Z][A-Za-z0-9_]*)(?:\s*)(?:=)(?![<=>])\s*', r'\1:'],
  [r'([a-zA-Z][A-Za-z0-9_]*)(:(?:>=|<=|>|<)(?![<=>]))"([^"\s]+)"', r'\1\2\3'],
  [r'([a-zA-Z][A-Za-z0-9_]*)(:(?:>=|<=|>|<)(?![<=>]))""([^"\s]+)""', r'\1\2"\3"'],
  # [r'\(\s*([a-zA-Z][A-Za-z0-9_]*)(:(?:>=|<=|>|<)(?![<=>]))"([^"]+)"\s*\)', r'(\1\2(\3))'],
)
for pairs in LIST_REGEX_CONVERT_QUERY:
  pairs[0] = re.compile(pairs[0])


def convert_query_string_gae_search_to_elasticsearch(query_string):
  query_string_alt = query_string
  
  for pairs in LIST_REGEX_CONVERT_QUERY:
    reg = pairs[0]
    rel = pairs[1]
    # query_string_alt = reg.sub(rel, query_string_alt)
    query_string_alt = re.sub(reg, rel, query_string_alt)

  return query_string_alt


def memcache_get(*args, **kwargs):
  if not IS_GAE:
    return
  if not memcache:
    return
  
  return memcache.get(*args, **kwargs)


def memcache_set(*args, **kwargs):
  if not IS_GAE:
    return
  if not memcache:
    return
  
  return memcache.set(*args, **kwargs)


def memcache_delete(*args, **kwargs):
  if not IS_GAE:
    return
  if not memcache:
    return
  
  return memcache.delete(*args, **kwargs)


def get_current_namespace():
  if not IS_GAE:
    # for test on local machine without GAE namespace env
    return "vn2.sateraito.co.jp__default"
  
  namespace = namespace_manager.get_namespace()

  if not namespace:
    return elasticsearch_inc.NAMESPACE_GLOBAL

  return namespace


def extract_namespace_domain(namespace):
  if sateraito_func:
    domain = sateraito_func.getDomainFromNamespace(namespace)
    return domain

  parts = re.split(r'__+', namespace)
  if len(parts) == 2:
    return parts[0]
  elif len(parts) >= 3:
    alt_parts = re.split(r'___+', namespace)
    if len(alt_parts) == 1:
      return parts[0]
    elif len(alt_parts) == 2:
      return alt_parts[0]
    elif len(alt_parts) >= 3:
      return alt_parts[0]
    else:
      return parts[0]
  
  return namespace


def get_current_domain():
  namespace = get_current_namespace()
  assert namespace, "namespace is empty"
  
  return extract_namespace_domain(namespace)


def list_gae_all_namespaces():
  # from google.appengine.ext.db import metadata
  # namespaces = []
  # for kind in metadata.get_namespaces():
  #   namespaces.append(kind.namespace_name)

  from google.appengine.ext.ndb import metadata
  namespaces = [ns for ns in metadata.get_namespaces()]

  return namespaces


def list_domain_all_namespaces(domain=None):
  if not domain:
    domain = get_current_domain()
    assert domain, "domain is empty"


  #all_namespaces = list_gae_all_namespaces()
  #domain_namespaces = []
  #domain_prefix = domain + "__"
  #for namespace in all_namespaces:
  #  if namespace == domain:
  #    domain_namespaces.append(namespace)
  #  else:
  #    # namespace_domain = extract_namespace_domain(namespace)
  #    # if namespace_domain == domain:
  #    #   domain_namespaces.append(namespace)
  #    if namespace.startswith(domain_prefix):
  #      domain_namespaces.append(namespace)
  domain_namespaces = []
  domain_namespaces.append(domain)
  return domain_namespaces


def get_domain_all_namespaces(domain=None):
  if not domain:
    domain = get_current_domain()
    assert domain, "domain is empty"
  
  domain_namespaces = memcache.get("domain_all_namespaces", namespace=domain)
  if domain_namespaces:
    return domain_namespaces
  
  domain_namespaces = list_domain_all_namespaces(domain)
  domain_namespaces.sort()
  memcache.set("domain_all_namespaces", domain_namespaces, namespace=domain)
  return domain_namespaces


def list_all_domain_names():
  all_namespaces = list_gae_all_namespaces()
  marked_domains = {}
  list_domains = []
  for namespace in all_namespaces:
    if not namespace:
      continue
    domain = extract_namespace_domain(namespace)
    if not domain:
      continue
    if marked_domains.get(domain):
      continue
    marked_domains[domain] = True
    list_domains.append(domain)
  list_domains.sort()
  return list_domains


def get_all_domain_names():
  list_domains = memcache.get("all_domain_names", namespace="")
  if list_domains:
    return list_domains
  
  list_domains = list_all_domain_names()
  list_domains.sort()
  memcache.set("all_domain_names", list_domains, namespace="")
  return list_domains


def generate_random_document_id(length=32, characters=STRING_RAMDOM_CHARACTERS):
  # return str(uuid.uuid4())
  return ''.join(random.choice(characters) for _ in range(length))


def check_can_use_elasticsearch(domain=None):
  if not IS_GAE:
    return True
  
  if not domain:
    domain = get_current_domain()
    assert domain, "domain is empty"
  
  if not elasticsearch_inc.USE_ELASTICSEARCH_DOMAINS.get(domain):
    return False
  
  old_namespace = namespace_manager.get_namespace()
  namespace_manager.set_namespace(domain)
  record = db_migrate.SearchIndexMigrateStatus.get(db_migrate.ID_ALL_DOMAIN_NAMESPACES)
  if not record:
    namespace_manager.set_namespace(old_namespace)
    return False
  
  if record.status == db_migrate.MIGRATE_STATUS_COMPLETED:
    namespace_manager.set_namespace(old_namespace)
    return True
  
  if record.status == db_migrate.MIGRATE_STATUS_RUNNING:
    logging.warning("Current migrate search index is running. Modify search index document can cause out of sync when mirgate. Better to wait a moment before use search function for this domain.")

  namespace_manager.set_namespace(old_namespace)
  return False

