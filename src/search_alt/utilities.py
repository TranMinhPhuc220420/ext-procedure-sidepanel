# encoding: utf-8

import os
import sys

# import re
import json
# import yaml


IS_PYTHON_3 = sys.version_info.major >= 3

if IS_PYTHON_3:
  import collections.abc as collections_abc
else:
  import collections as collections_abc

cls_mapping = collections_abc.Mapping


def check_is_running_gae():
  server_software = os.getenv('SERVER_SOFTWARE', '')
  if not server_software:
    return False
  
  if IS_PYTHON_3:
    # GAE Python 3.7 Standard Environment
    if server_software.startswith('gunicorn/'):
      return True
  
  else:
    # GAE Python 2.7 SDK
    if server_software.startswith('Google App Engine/'):
      return True
    
    if server_software.startswith('Development/'):
      return True
  
  return False


IS_GAE = check_is_running_gae()


def update_deep(dst, src):
  src_items = src.items() if IS_PYTHON_3 else src.iteritems()
  for k, v in src_items:
    v0 = dst.get(k, None)
    if isinstance(v, cls_mapping) and isinstance(v0, cls_mapping):
      dst[k] = update_deep(v0, v)
    else:
      dst[k] = v
  return dst


def is_str(s):
  if IS_PYTHON_3:
    return isinstance(s, str)
  else:
    return isinstance(s, basestring)


def is_num(v):
  if IS_PYTHON_3:
    return isinstance(v, (int, float))
  else:
    return isinstance(v, (int, long, float))


def dump_json(obj):
  res = json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True, encoding='utf-8')
  return res


def print_json(obj):
  res = dump_json(obj)
  print(res)


# def dump_yaml(obj):
#   res = yaml.safe_dump(obj, default_flow_style=False, allow_unicode=True, sort_keys=True, indent=2, encoding='utf-8')
#   return res


# def print_yaml(obj):
#   res = dump_yaml(obj)
#   print(res)
