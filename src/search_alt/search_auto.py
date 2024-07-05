# encoding: utf-8
# WARN: this file is python2 only

import os

import json
import logging
# import sateraito_logger as logging


# search_gae = None
# try:
#   from google.appengine.api import search
#   search_gae = search
# except ImportError:
#   pass

# from search_alt import search_adapt
from . import search_adapt

if search_adapt.IS_GAE:
  from .  import search_gae
else:
  search_gae = None

# from search_alt import search_replace
from . import search_replace


KEY_REQUEST_CAN_USE_ELASTICSEARCH = "REQUEST_CAN_USE_ELASTICSEARCH"


def get_request_can_use_elasticsearch():
  ###
  # fast check current request can use elasticsearch or not
  ###
  val = os.environ.get("KEY_REQUEST_CAN_USE_ELASTICSEARCH", None)
  return val


def set_request_can_use_elasticsearch(val):
  ###
  # fast set current request can use elasticsearch or not
  ###
  os.environ[KEY_REQUEST_CAN_USE_ELASTICSEARCH] = val


def get_module():
  if not search_gae:
    return search_replace
  
  # use_elasticsearch = get_request_can_use_elasticsearch()
  # if use_elasticsearch is None:
  #   use_elasticsearch = search_adapt.check_can_use_elasticsearch()
  #   set_request_can_use_elasticsearch(str(use_elasticsearch))
  # else:
  #   use_elasticsearch = bool(use_elasticsearch)
  
  use_elasticsearch = is_use_elasticsearch()
  if use_elasticsearch:
    return search_replace
  
  return search_gae


def is_use_elasticsearch():
  if not search_gae:
    return True
  
  use_elasticsearch = get_request_can_use_elasticsearch()
  if use_elasticsearch is None:
    use_elasticsearch = search_adapt.check_can_use_elasticsearch()
    set_request_can_use_elasticsearch(str(use_elasticsearch))
  else:
    use_elasticsearch = bool(use_elasticsearch)
  
  return use_elasticsearch
