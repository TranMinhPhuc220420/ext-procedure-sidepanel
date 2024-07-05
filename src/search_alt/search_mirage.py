# encoding: utf-8
# WARN: this file is python2 only

import json
import logging
# import sateraito_logger as logging

import time

# from google.appengine.ext import ndb
from google.appengine.api import search
from google.appengine.api import memcache
from google.appengine.api import namespace_manager

# from . import search_replace
# from . import search_adapt
# from . import db_migrate
from . import search_replace
from . import search_adapt
from . import db_migrate

gae_search = search
es_search = search_replace


MAP_CLS_FIELDS = {
  search.TextField: search_replace.TextField,
  search.AtomField: search_replace.AtomField,
  search.HtmlField: search_replace.HtmlField,
  search.NumberField: search_replace.NumberField,
  search.DateField: search_replace.DateField,
  search.GeoField: search_replace.GeoField,
}

ONLY_MIRAGE_TO_ELASTICSEARCH = False
ONLY_MIRAGE_TO_OPENSEARCH = True


def list_namespace_search_indexes(namespace):
  name_indexes = []
  start_index_name = None
  while True:
    indexes = search.get_indexes(namespace=namespace, start_index_name=start_index_name, include_start_index=False, limit=1000)
    if not indexes:
      break
    for index in indexes:
      name_indexes.append(index.name)
    if len(indexes) < 1000:
      break
    start_index_name = name_indexes[-1]
  name_indexes.sort()
  return name_indexes


def get_namespace_search_indexes(namespace):
  name_indexes = memcache.get("search_indexes_%s" % namespace)
  if name_indexes is None:
    name_indexes = list_namespace_search_indexes(namespace)
    memcache.set("search_indexes_%s" % namespace, name_indexes, 60*60*24)
  return name_indexes


def mirage_search_data_namespace(name_indexes, search_from, search_to, resume_info=None, limit_time=6*60, namespace=None):
  time_start = time.time()

  old_namespace = None
  if namespace is not None:
    old_namespace = namespace_manager.get_namespace()
    namespace_manager.set_namespace(namespace)
  
  if resume_info is None:
    resume_info = {}
  else:
    logging.info("Resume info: " + json.dumps(resume_info, sort_keys=True, indent=2, ensure_ascii=False))

  marked_warn_type_fields = {}
  
  total_seconds = resume_info.get("total_seconds") or 0
  total_doc = resume_info.get("total_doc") or 0
  total_index = resume_info.get("total_index") or 0
  
  last_index_name = resume_info.get("last_index_name")
  
  # last_index_doc_id = resume_info.get("last_index_doc_id")
  # last_index_doc_id = last_index_doc_id or None

  last_index_cursor = resume_info.get("last_index_cursor")
  last_index_cursor = last_index_cursor or None
  if last_index_cursor:
    last_index_cursor = search_from.Cursor(web_safe_string=last_index_cursor)
  
  last_index_count = resume_info.get("last_index_count")
  last_index_count = last_index_count or 0

  done_indexes = resume_info.get('done_indexes') or {}

  count_doc = 0
  count_index = 0

  idx_next = 0
  if last_index_name:
    idx_next = name_indexes.index(last_index_name)
  assert idx_next >= 0, "Not found to resume last_index_name: %s" % last_index_name
  for idx in range(idx_next, len(name_indexes)):
    time_current = time.time()
    elapsed_seconds = time_current - time_start
    if elapsed_seconds > limit_time:
      if old_namespace is not None:
        namespace_manager.set_namespace(old_namespace)
      return {
        "total_seconds": total_seconds + elapsed_seconds,
        "total_doc": total_doc + count_doc,
        "total_index": total_index + count_index,
        "seconds": elapsed_seconds,
        "count_doc": count_doc,
        "count_index": count_index,
        "last_index_name": name_indexes[idx],
        # "last_index_doc_id": last_index_doc_id,
        "last_index_cursor": last_index_cursor.web_safe_string if last_index_cursor else None,
        "last_index_count": last_index_count,
        "done_indexes": done_indexes,
        "done": False,
      }

    name_index = name_indexes[idx]
    index_from = search_from.Index(name_index)

    is_begin_migration_at_index = True
    if last_index_cursor:
      logging.info("Resume migrate search index: %s", name_index)
      is_begin_migration_at_index = False
    else:
      logging.info("Start migrate search index: %s", name_index)

    # batch_size=10000
    while True:
      # # shit,get range only support max 1000 results
      # documents = index_from.get_range(start_id=last_index_doc_id, include_start_object=False, limit=batch_size)

      documents = []
      for _ in range(0, 5):
        query_options = search_from.QueryOptions(limit=100, cursor=last_index_cursor or search_from.Cursor())
        query = search_from.Query("", options=query_options)
        query_result = index_from.search(query)

        if not query_result:
          last_index_cursor = None
          break

        return_documents = query_result.results
        if not return_documents:
          last_index_cursor = None
          break
        
        documents.extend(return_documents)

        last_index_cursor = query_result.cursor
        if not last_index_cursor:
          break
      
      if not documents:
          break

      documents_to = []
      for doc in documents:
        fields = []
        for field in doc.fields:
          cls_field = MAP_CLS_FIELDS.get(type(field))
          if not cls_field:
            if not marked_warn_type_fields.get(type(field)):
              marked_warn_type_fields[type(field)] = True
              logging.warn("Not support migrate type field: %s", type(field))
            continue
          
          field_to = cls_field(name=field.name, value=field.value)
          fields.append(field_to)
        doc_to = search_to.Document(doc_id=doc.doc_id, fields=fields)
        documents_to.append(doc_to)
      
      # free memory
      del documents
      
      if not documents_to:
        break
      
      index_to = None
      if ONLY_MIRAGE_TO_ELASTICSEARCH:
        index_to = search_replace.IndexInstance(name_index, write_index_both=False, use_opensearch=False)
      elif ONLY_MIRAGE_TO_OPENSEARCH:
        index_to = search_replace.IndexInstance(name_index, write_index_both=False, use_opensearch=True)
      else:
        index_to = search_to.Index(name_index)
      # index_to.put(documents_to)
      # TODO: handle both case gae <=> elasticsearch, opensearch
      if is_begin_migration_at_index:
        index_to.put(documents_to, write_index_both=False, skip_mapping=False, mapping_all=True)
        is_begin_migration_at_index = False
      else:
        index_to.put(documents_to, write_index_both=False)

      count_migrated = len(documents_to)
      count_doc += count_migrated
      last_index_count += count_migrated

      current_index_done = done_indexes.get(name_index) or 0
      current_index_done += count_migrated
      done_indexes[name_index] = current_index_done

      # if len(documents) < batch_size:
      #   last_index_doc_id = None
      #   break

      # last_index_doc_id = documents[-1].doc_id

      if not last_index_cursor:
        break
      
      time_current = time.time()
      elapsed_seconds = time_current - time_start
      if elapsed_seconds > limit_time:
        logging.info("Pause temporarily migrate process at %s documents in search index: %s", last_index_count, name_index)
        if old_namespace is not None:
          namespace_manager.set_namespace(old_namespace)
        return {
          "total_seconds": total_seconds + elapsed_seconds,
          "total_doc": total_doc + count_doc,
          "total_index": total_index + count_index,
          "seconds": elapsed_seconds,
          "count_doc": count_doc,
          "count_index": count_index,
          "last_index_name": name_indexes[idx],
          "last_index_cursor": last_index_cursor.web_safe_string if last_index_cursor else None,
          # "last_index_doc_id": last_index_doc_id,
          "last_index_count": last_index_count,
          "done_indexes": done_indexes,
          "done": False,
        }
    
    logging.info("Finish migrate %s documents in search index: %s", last_index_count, name_index)
    logging.info("Current total %s documents in %s search indexes migrated", count_doc, count_index)

    last_index_count = 0
    # last_index_doc_id = None
    last_index_cursor = None
    
    count_index += 1
  
  time_current = time.time()
  elapsed_seconds = time_current - time_start
  if old_namespace is not None:
    namespace_manager.set_namespace(old_namespace)
  return {
    "total_seconds": total_seconds + elapsed_seconds,
    "total_doc": total_doc + count_doc,
    "total_index": total_index + count_index,
    "seconds": elapsed_seconds,
    "count_doc": count_doc,
    "count_index": count_index,
    "done_indexes": done_indexes,
    "done": True,
  }


def process_migrate_search_data_domain(domain=None, limit_time=8*60):
  if domain is None:
    domain = search_adapt.get_current_domain()
    assert domain, "domain is None"

  time_start = time.time()

  old_namespace = namespace_manager.get_namespace()

  domain_namespaces = search_adapt.get_domain_all_namespaces(domain)

  namespace_manager.set_namespace(domain)
  dict_status = db_migrate.SearchIndexMigrateStatus.get_dict(db_migrate.ID_ALL_DOMAIN_NAMESPACES)
  last_result_info = None
  if not dict_status:
    logging.info('Start process migrate search index data of domain: %s', domain)
    last_result_info = {}
  else:
    logging.info('Resume process migrate search index data of domain: %s', domain)
    last_result_info = dict_status.get('result') or {}

  last_namespace = last_result_info.get('last_namespace')
  last_namespace_result = last_result_info.get('last_namespace_result')

  count_seconds = last_result_info.get('count_seconds') or 0

  count_namespace = last_result_info.get('count_namespace') or 0
  count_index = last_result_info.get('count_index') or 0
  count_doc = last_result_info.get('count_doc') or 0
  
  total_result_info = json.loads(json.dumps(last_result_info))

  idx_next = 0
  if last_namespace:
    idx_next = domain_namespaces.index(last_namespace)
    assert idx_next >= 0, "Not found to resume last_namespace: %s" % last_namespace
  
  for idx in range(idx_next, len(domain_namespaces)):
    namespace = domain_namespaces[idx]

    total_result_info['last_namespace'] = namespace

    last_namespace_result = last_namespace_result or {}

    time_current = time.time()
    elapsed_seconds = time_current - time_start
    remain_limit_time = 9*60 - elapsed_seconds
    if elapsed_seconds > limit_time or remain_limit_time < 2*60:
      total_result_info['count_seconds'] = count_seconds + elapsed_seconds
      set_db_mirgate_status_domain_namespace(domain, db_migrate.ID_ALL_DOMAIN_NAMESPACES, result=total_result_info)
      namespace_manager.set_namespace(old_namespace)
      return total_result_info

    set_db_mirgate_status_domain_namespace(domain, namespace, status=db_migrate.MIGRATE_STATUS_RUNNING)
    namespace_manager.set_namespace(namespace)

    name_indexes = get_namespace_search_indexes(namespace)
    
    batch_limit_time = remain_limit_time - 1*60
    batch_resume_info = last_namespace_result
    try:
      batch_result = mirage_search_data_namespace(name_indexes, gae_search, es_search, resume_info=batch_resume_info, limit_time=batch_limit_time, namespace=namespace)
    except Exception as e:
      logging.exception(e, exc_info=True)
      set_db_mirgate_status_domain_namespace(domain, namespace, status=db_migrate.MIGRATE_STATUS_ERROR, info=str(e))
      total_result_info['count_seconds'] = count_seconds + (time.time() - time_start)
      total_result_info['error'] = str(e)
      set_db_mirgate_status_domain_namespace(domain, db_migrate.ID_ALL_DOMAIN_NAMESPACES, status=db_migrate.MIGRATE_STATUS_ERROR, info=str(e), result=total_result_info)
      namespace_manager.set_namespace(old_namespace)
      return total_result_info

    namespace_done = batch_result.get('done')
    namespace_mirgate_status = db_migrate.MIGRATE_STATUS_RUNNING
    if namespace_done:
      namespace_mirgate_status = db_migrate.MIGRATE_STATUS_COMPLETED
    set_db_mirgate_status_domain_namespace(domain, namespace, status=namespace_mirgate_status, result=batch_result)
    
    count_index += batch_result.get('count_index')
    total_result_info['count_index'] = count_index
    count_doc += batch_result.get('count_doc')
    total_result_info['count_doc'] = count_doc
    if batch_result.get('done'):
      count_namespace += 1
      total_result_info['count_namespace'] = count_namespace
      last_namespace_result = None
    else:
      last_namespace_result = batch_result
    total_result_info['last_namespace_result'] = last_namespace_result
    if not batch_result.get('done'):
      set_db_mirgate_status_domain_namespace(domain, db_migrate.ID_ALL_DOMAIN_NAMESPACES, status=db_migrate.MIGRATE_STATUS_RUNNING, result=total_result_info)
      namespace_manager.set_namespace(old_namespace)
      return total_result_info

  time_current = time.time()
  elapsed_seconds = time_current - time_start
  total_result_info['count_seconds'] = count_seconds + elapsed_seconds
  total_result_info['last_namespace'] = None
  total_result_info['last_namespace_result'] = None
  total_result_info['done'] = True
  set_db_mirgate_status_domain_namespace(domain, db_migrate.ID_ALL_DOMAIN_NAMESPACES, status=db_migrate.MIGRATE_STATUS_COMPLETED, result=total_result_info)
  namespace_manager.set_namespace(old_namespace)
  return total_result_info


def process_migrate_search_data_all_project(limit_time=8*60):
  time_start = time.time()

  old_namespace = namespace_manager.get_namespace()
  namespace_manager.set_namespace("")
  
  all_domains = search_adapt.get_all_domain_names()
  
  dict_status = get_db_mirgate_status_all_project(as_dict=True)
  last_result_info = None
  if not dict_status:
    logging.info('Start process migrate search index data of project')
    set_db_mirgate_status_all_project(status=db_migrate.MIGRATE_STATUS_RUNNING, result={})
    last_result_info = {}
  else:
    logging.info('Resume process migrate search index data of project')
    last_result_info = dict_status.get('result') or {}

  last_domain = last_result_info.get('last_domain')

  count_seconds = last_result_info.get('count_seconds') or 0

  count_domain_done = last_result_info.get('count_domain_done') or 0
  count_domain_error = last_result_info.get('count_domain_error') or 0

  count_namespace = last_result_info.get('count_namespace') or 0
  count_index = last_result_info.get('count_index') or 0
  count_doc = last_result_info.get('count_doc') or 0
  
  total_result_info = json.loads(json.dumps(last_result_info))

  idx_next = 0
  if last_domain:
    idx_next = all_domains.index(last_domain)
    assert idx_next >= 0, "Not found to resume last_domain: %s" % last_domain
  
  for idx in range(idx_next, len(all_domains)):
    domain = all_domains[idx]

    total_result_info['last_domain'] = domain

    time_current = time.time()
    elapsed_seconds = time_current - time_start
    remain_limit_time = 9*60 - elapsed_seconds
    if elapsed_seconds > limit_time or remain_limit_time < 2*60:
      total_result_info['count_seconds'] = count_seconds + elapsed_seconds
      set_db_mirgate_status_all_project(result=total_result_info)
      namespace_manager.set_namespace(old_namespace)
      return total_result_info

    entry_status_domain = get_db_mirgate_status_domain_namespace(domain, db_migrate.ID_ALL_DOMAIN_NAMESPACES, as_dict=False)
    # if entry_status_domain and (entry_status_domain.status == db_migrate.MIGRATE_STATUS_COMPLETED or entry_status_domain.status == db_migrate.MIGRATE_STATUS_ERROR):
    if entry_status_domain and (entry_status_domain.status == db_migrate.MIGRATE_STATUS_COMPLETED):
      continue

    batch_limit_time = remain_limit_time - 1*60
    batch_result = process_migrate_search_data_domain(domain, limit_time=batch_limit_time)
    domain_done = batch_result.get('done')
    domain_error = batch_result.get('error')

    if domain_done:
      if batch_result.get('count_namespace'):
        count_namespace += batch_result.get('count_namespace')
        total_result_info['count_namespace'] = count_namespace
      if batch_result.get('count_index'):
        count_index += batch_result.get('count_index')
        total_result_info['count_index'] = count_index
      if batch_result.get('count_doc'):
        count_doc += batch_result.get('count_doc')
        total_result_info['count_doc'] = count_doc
      
      count_domain_done += 1
      total_result_info['count_domain_done'] = count_domain_done
    
    elif domain_error:
      if batch_result.get('count_namespace'):
        count_namespace += batch_result.get('count_namespace')
        total_result_info['count_namespace'] = count_namespace
      if batch_result.get('count_index'):
        count_index += batch_result.get('count_index')
        total_result_info['count_index'] = count_index
      if batch_result.get('count_doc'):
        count_doc += batch_result.get('count_doc')
        total_result_info['count_doc'] = count_doc

      count_domain_error += 1
      total_result_info['count_domain_error'] = count_domain_error
    
    else:
      elapsed_seconds = time_current - time_start
      total_result_info['count_seconds'] = count_seconds + elapsed_seconds
      set_db_mirgate_status_all_project(result=total_result_info)
      namespace_manager.set_namespace(old_namespace)
      return total_result_info

  time_current = time.time()
  elapsed_seconds = time_current - time_start
  total_result_info['count_seconds'] = count_seconds + elapsed_seconds
  total_result_info['last_domain'] = None
  total_result_info['done'] = True
  set_db_mirgate_status_all_project(status=db_migrate.MIGRATE_STATUS_COMPLETED, result=total_result_info)
  namespace_manager.set_namespace(old_namespace)
  return total_result_info


def get_db_mirgate_status_domain_namespace(domain, namespace=db_migrate.ID_ALL_DOMAIN_NAMESPACES, as_dict=True):
  old_namespace = namespace_manager.get_namespace()
  if old_namespace != domain:
    namespace_manager.set_namespace(domain)
  
  status = None
  if as_dict:
    status = db_migrate.SearchIndexMigrateStatus.get_dict(namespace)
  else:
    status = db_migrate.SearchIndexMigrateStatus.get(namespace)
  
  if old_namespace != domain:
    namespace_manager.set_namespace(old_namespace)
  
  return status


def set_db_mirgate_status_domain_namespace(domain, namespace, status=None, info=None, result=None):
  old_namespace = namespace_manager.get_namespace()
  if old_namespace != domain:
    namespace_manager.set_namespace(domain)

  if not status:
    status = db_migrate.MIGRATE_STATUS_RUNNING
  
  res = db_migrate.SearchIndexMigrateStatus.set(namespace, status=status, info=info, result=result)

  if old_namespace != domain:
    namespace_manager.set_namespace(old_namespace)
  
  return res


def get_db_mirgate_status_domain_namespace_all(domain, as_dict=True):
  old_namespace = namespace_manager.get_namespace()
  if old_namespace != domain:
    namespace_manager.set_namespace(domain)
  
  # domain_namespaces = search_adapt.get_domain_all_namespaces(domain)
  # domain_all_namespaces = [db_migrate.ID_ALL_DOMAIN_NAMESPACES]
  # domain_all_namespaces.extend(domain_namespaces)

  all_status = {}
  if as_dict:
    all_status["__" + db_migrate.ID_ALL_DOMAIN_NAMESPACES] = db_migrate.SearchIndexMigrateStatus.get_dict(db_migrate.ID_ALL_DOMAIN_NAMESPACES)
  else:
    all_status["__" + db_migrate.ID_ALL_DOMAIN_NAMESPACES] = db_migrate.SearchIndexMigrateStatus.get(db_migrate.ID_ALL_DOMAIN_NAMESPACES)

  domain_all_namespaces = search_adapt.get_domain_all_namespaces(domain)
  for namespace in domain_all_namespaces:
    status = None
    if as_dict:
      status = db_migrate.SearchIndexMigrateStatus.get_dict(namespace)
    else:
      status = db_migrate.SearchIndexMigrateStatus.get(namespace)
    all_status[namespace] = status
  
  if old_namespace != domain:
    namespace_manager.set_namespace(old_namespace)
  
  return all_status


def get_db_mirgate_status_all_project(as_dict=True):
  old_namespace = namespace_manager.get_namespace()
  if old_namespace != "":
    namespace_manager.set_namespace("")
  
  status = None
  if as_dict:
    status = db_migrate.SearchIndexMigrateStatus.get_dict(db_migrate.ID_ALL_FULL_PROJECT)
  else:
    status = db_migrate.SearchIndexMigrateStatus.get(db_migrate.ID_ALL_FULL_PROJECT)
  
  if old_namespace != "":
    namespace_manager.set_namespace(old_namespace)
  
  return status


def set_db_mirgate_status_all_project(status=None, info=None, result=None):
  old_namespace = namespace_manager.get_namespace()
  if old_namespace != "":
    namespace_manager.set_namespace("")

  if not status:
    status = db_migrate.MIGRATE_STATUS_RUNNING
  
  res = db_migrate.SearchIndexMigrateStatus.set(db_migrate.ID_ALL_FULL_PROJECT, status=status, info=info, result=result)

  if old_namespace != "":
    namespace_manager.set_namespace(old_namespace)
  
  return res


def get_db_mirgate_status_all_project_full(as_dict=True):
  old_namespace = namespace_manager.get_namespace()
  if old_namespace != "":
    namespace_manager.set_namespace("")
  
  all_status = {}
  all_status["__" + db_migrate.ID_ALL_FULL_PROJECT] = get_db_mirgate_status_all_project(as_dict=as_dict)

  domain_names = search_adapt.get_all_domain_names()
  for domain in domain_names:
    namespace_manager.set_namespace(domain)
    status = None
    if as_dict:
      status = db_migrate.SearchIndexMigrateStatus.get_dict(db_migrate.ID_ALL_DOMAIN_NAMESPACES)
    else:
      status = db_migrate.SearchIndexMigrateStatus.get(db_migrate.ID_ALL_DOMAIN_NAMESPACES)
    all_status[domain] = status
  
  namespace_manager.set_namespace("")

  if old_namespace != "":
    namespace_manager.set_namespace(old_namespace)
  
  return all_status


def get_db_mirgate_status_all_project_full_detail(as_dict=True):
  old_namespace = namespace_manager.get_namespace()
  if old_namespace != "":
    namespace_manager.set_namespace("")
  
  all_status = {}
  all_status["__" + db_migrate.ID_ALL_FULL_PROJECT] = get_db_mirgate_status_all_project(as_dict=as_dict)

  domain_names = search_adapt.get_all_domain_names()
  for domain in domain_names:
    # namespace_manager.set_namespace(domain)
    status = get_db_mirgate_status_domain_namespace_all(domain, as_dict=as_dict)
    all_status[domain] = status
  
  namespace_manager.set_namespace("")

  if old_namespace != "":
    namespace_manager.set_namespace(old_namespace)
  
  return all_status


def clean_db_mirgate_status_all_project_full():
  old_namespace = namespace_manager.get_namespace()
  if old_namespace != "":
    namespace_manager.set_namespace("")
  
  db_migrate.SearchIndexMigrateStatus.delete(db_migrate.ID_ALL_FULL_PROJECT)

  domain_names = search_adapt.get_all_domain_names()
  for domain in domain_names:
    namespace_manager.set_namespace(domain)
    db_migrate.SearchIndexMigrateStatus.delete(db_migrate.ID_ALL_DOMAIN_NAMESPACES)
    
  namespace_manager.set_namespace("")

  if old_namespace != "":
    namespace_manager.set_namespace(old_namespace)
  
  return

