# encoding: utf-8
# WARN: this file is python2 only

import json
import logging
# import sateraito_logger as logging

from google.appengine.api import search

from . import elasticsearch_inc
from . import search_replace
from . import search_adapt

generate_random_document_id = search_adapt.generate_random_document_id

WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH = elasticsearch_inc.WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH


class Index(search.Index):
  def __init__(self, name, namespace=None):
    super(Index, self).__init__(name, namespace=namespace)
    self._es_index = None
  
  @property
  def es_index(self):
    if self._es_index is None:
      self._es_index = search_replace.Index(self.name, namespace=self.namespace, write_index_both=False)
    return self._es_index

  def put(self, documents, deadline=None, write_index_both=WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH):
    if write_index_both:
      # elasticsearch need doc_id before put because it use 'namespace + doc_id' as id of doc in alias of a share index
      if isinstance(documents, search.Document):
        doc = documents
        if not doc.doc_id:
          doc.doc_id = generate_random_document_id()
      else:
        for doc in documents:
          if not doc.doc_id:
            doc.doc_id = generate_random_document_id()
    
    results = super(Index, self).put(documents, deadline=deadline)
    
    if write_index_both:
      es_documents = []
      if isinstance(documents, search.Document):
        doc = documents
        es_documents.append(doc.to_elasticsearch_document())
      else:
        for doc in documents:
          es_documents.append(doc.to_elasticsearch_document())
      try:
        # self.es_index.put(es_documents, deadline=deadline)
        self.es_index.put(es_documents, deadline=deadline, write_index_both=False)
      except Exception as e:
        logging.error('elasticsearch put error: %s' % e)
        logging.exception(e, exc_info=True)

    return results
  
  def delete(self, document_ids, deadline=None, write_index_both=WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH):
    results = super(Index, self).delete(document_ids, deadline=deadline)
    
    if write_index_both:
      try:
        # self.es_index.delete(document_ids, deadline=deadline)
        self.es_index.delete(document_ids, deadline=deadline, write_index_both=False)
      except Exception as e:
        logging.error('elasticsearch delete error: %s' % e)
        logging.exception(e, exc_info=True)
    
    return results


Field = search.Field
TextField = search.TextField
HtmlField = search.HtmlField
AtomField = search.AtomField
NumberField = search.NumberField
DateField = search.DateField
GeoPoint = search.GeoPoint
GeoField = search.GeoField


MAP_FIELD_TYPE_TO_ELASTICSEARCH_FIELD = {
  AtomField: search_replace.AtomField,
  NumberField: search_replace.NumberField,
  TextField: search_replace.TextField,
  HtmlField: search_replace.HtmlField,
  DateField: search_replace.DateField,
  GeoField: search_replace.GeoField,
}

class Document(search.Document):
  def to_elasticsearch_document(self):
    es_fields = []
    for field in self.fields:
      field_cls = field.__class__
      es_field_cls = MAP_FIELD_TYPE_TO_ELASTICSEARCH_FIELD[field_cls]
      es_field = es_field_cls(name=field.name, value=field.value)
      es_fields.append(es_field)
    es_document = search_replace.Document(doc_id=self.doc_id, fields=es_fields)
    return es_document


# class Query(search.Query):
#   pass
# class QueryOptions(search.QueryOptions):
#   pass
# class SortOptions(search.SortOptions):
#   pass
# class SortExpression(search.SortExpression):
#   pass
# class Cursor(search.Cursor):
#   pass
# class SearchResults(search.SearchResults):
#   pass

Query = search.Query
QueryOptions = search.QueryOptions
SortOptions = search.SortOptions
SortExpression = search.SortExpression
Cursor = search.Cursor
SearchResults = search.SearchResults


Error = search.Error
PutError = search.PutError
InternalError = search.InternalError
DeleteError = search.DeleteError
TransientError = search.TransientError
InvalidRequest = search.InvalidRequest
