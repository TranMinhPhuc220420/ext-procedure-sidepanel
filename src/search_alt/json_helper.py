# coding: utf-8

# import sys
# stdin = sys.stdin
# stdout = sys.stdout
# reload(sys)
# sys.setdefaultencoding('utf-8')
# sys.stdin = stdin
# sys.stdout = stdout


import json
#import logging
# import sateraito_logger as logging

import time
import datetime


from google.appengine.ext import ndb


JSONEncoder = json.JSONEncoder


USE_FORMAT_ISO = False

# FORMAT_DATETIME = '%Y-%m-%d %H:%M:%S.%f'
# FORMAT_DATE = '%Y-%m-%d'
# FORMAT_TIME = '%H:%M:%S.%f'

FORMAT_DATETIME = '%Y/%m/%d %H:%M:%S.%f'
FORMAT_DATE = '%Y/%m/%d'
FORMAT_TIME = '%H:%M:%S.%f'


CACHED_ENCODERS = {}


class BaseValueEncoder(JSONEncoder):
  def default(self, obj):
    if type(obj) == ndb.model._BaseValue:
      return obj.b_val
    else:
      return super(BaseValueEncoder, self).default(obj)

JSONBaseEncoder = BaseValueEncoder

class DateTimeEncoder(JSONBaseEncoder):
  def __init__(self, format_datetime=None, format_date=None, format_time=None, **kwargs):
    self.format_datetime = format_datetime or FORMAT_DATETIME
    self.format_date = format_date or FORMAT_DATE
    self.format_time = format_time or FORMAT_TIME
    # JSONBaseEncoder.__init__(self, **kwargs)
    super(DateTimeEncoder, self).__init__(**kwargs)

  def default(self, obj):
    if isinstance(obj, datetime.datetime):
      if USE_FORMAT_ISO:
        return obj.isoformat()
      else:
        return obj.strftime(self.format_datetime)
    elif isinstance(obj, datetime.date):
      if USE_FORMAT_ISO:
        return obj.isoformat()
      else:
        return obj.strftime(self.format_date)
    elif isinstance(obj, datetime.time):
      if USE_FORMAT_ISO:
        return obj.isoformat()
      else:
        return obj.strftime(self.format_time)
    elif isinstance(obj, datetime.timedelta):
      if USE_FORMAT_ISO:
        return (datetime.datetime.min + obj).time().isoformat()
      else:
        return (datetime.datetime.min + obj).time().strftime(FORMAT_TIME)

    else:
      return super(DateTimeEncoder, self).default(obj)


class DateTimeEncoderIso(JSONBaseEncoder):
  def default(self, obj):
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
      return obj.isoformat()

    elif isinstance(obj, datetime.timedelta):
      return (datetime.datetime.min + obj).time().isoformat()

    else:
      return super(DateTimeEncoderIso, self).default(obj)


class DateTimeEncoderStandard(JSONBaseEncoder):
  def __init__(self, format_datetime=None, format_date=None, format_time=None, **kwargs):
    self.format_datetime = format_datetime or FORMAT_DATETIME
    self.format_date = format_date or FORMAT_DATE
    self.format_time = format_time or FORMAT_TIME
    # JSONBaseEncoder.__init__(self, **kwargs)
    super(DateTimeEncoderStandard, self).__init__(**kwargs)

  def default(self, obj):
    if isinstance(obj, datetime.datetime):
      return obj.strftime(self.format_datetime)
    elif isinstance(obj, datetime.date):
      return obj.strftime(self.format_date)
    elif isinstance(obj, datetime.time):
      return obj.strftime(self.format_time)
    elif isinstance(obj, datetime.timedelta):
      return (datetime.datetime.min + obj).time().strftime(FORMAT_TIME)

    else:
      return super(DateTimeEncoderStandard, self).default(obj)


# ENCODER_DEFAULT = DateTimeEncoder()
# ENCODER_ISO = DateTimeEncoderIso()
# ENCODER_STANDARD = DateTimeEncoderStandard()


# def dumps(obj, format_datetime=None, format_date=None, format_time=None, **kwargs):
#   # return ENCODER_DEFAULT.encode(obj)
#   return json.dumps(obj, cls=DateTimeEncoder, **kwargs)


def dumps(obj, **kwargs):
  # return ENCODER_DEFAULT.encode(obj)
  return json.dumps(obj, cls=DateTimeEncoder, **kwargs)


def dumps_iso(obj, **kwargs):
  # return ENCODER_ISO.encode(obj)
  return json.dumps(obj, cls=DateTimeEncoderIso, **kwargs)


def dumps_standard(obj, format_datetime=None, format_date=None, format_time=None, **kwargs):
  # return ENCODER_STANDARD.encode()
  return json.dumps(obj, cls=DateTimeEncoderStandard, **kwargs)


def create_datetime_encoder_custom(format_datetime=FORMAT_DATETIME, format_date=FORMAT_DATE, format_time=FORMAT_TIME):
  class DateTimeEncoderCustom(JSONBaseEncoder):
    def default(self, obj):
      if isinstance(obj, datetime.datetime):
        return obj.strftime(format_datetime)
      elif isinstance(obj, datetime.date):
        return obj.strftime(format_date)
      elif isinstance(obj, datetime.time):
        return obj.strftime(format_time)
      elif isinstance(obj, datetime.timedelta):
        return (datetime.datetime.min + obj).time().strftime(format_time)

      else:
        return super(DateTimeEncoderCustom, self).default(obj)

  return DateTimeEncoderCustom



def get_datetime_encoder_custom(format_datetime=FORMAT_DATETIME, format_date=FORMAT_DATE, format_time=FORMAT_TIME):
  key = "{}__{}__{}".format(format_datetime, format_date, format_time)
  encoder = CACHED_ENCODERS.get(key)
  if not encoder:
    encoder = create_datetime_encoder_custom(format_datetime=format_datetime, format_date=format_date, format_time=format_time)
    CACHED_ENCODERS[key] = encoder

  return encoder


def dumps_custom(obj, format_datetime=FORMAT_DATETIME, format_date=FORMAT_DATE, format_time=FORMAT_TIME, **kwargs):
  # return ENCODER_STANDARD.encode()

  # encoder = create_datetime_encoder_custom(format_datetime=format_datetime, format_date=format_date, format_time=format_time)
  encoder = get_datetime_encoder_custom(format_datetime=format_datetime, format_date=format_date, format_time=format_time)

  return json.dumps(obj, cls=encoder, **kwargs)

def dumps_temp(obj, **kwargs):
  # return ENCODER_DEFAULT.encode(obj)
  return json.dumps(obj, cls=DateTimeEncoder, **kwargs)

