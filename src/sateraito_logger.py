# GAEGEN2対応：メモリ使用量チューニング
import os
# import psutil
# import threading
# import random
import logging
# import inspect

import sateraito_inc
LOG_LEVEL = sateraito_inc.logging_level


### Change Logs
# 2023-12-05: fix log "WARN" -> "WARNING"
# 2023-12-06: major update improve performance to match ~1:1 with vanilla standard cloud logging handler
# 2023-12-12: try to fix threading del _active[get_ident()] KeyError
# 2023-12-14: update log exception for unhandled exception out of request context
# 2023-12-15: minor update


# if sateraito_inc.site_fqdn.startswith('localhost'):
if not os.environ.get('SERVER_SOFTWARE','').startswith('gunicorn/'):
	logging.getLogger().setLevel(LOG_LEVEL)

	# info = logging.info
	# debug = logging.debug
	# warn = logging.warning
	# warning = logging.warning
	# error = logging.error
	# exception = logging.exception
	# 
	# fatal = logging.fatal
	# critical = logging.critical
	
	from logging import *

else:
	
	# import os
	import sys
	# import inspect
	
	# # import sys
	# # if 'threading' in sys.modules:
	# # 	raise Exception('threading module loaded before patching!')
	# if 'threading' in sys.modules:
	# 	del sys.modules['threading']
	# import gevent
	# # import gevent.socket
	# import gevent.monkey
	# gevent.monkey.patch_all()
	# import threading
	
	TEMPLATE_MESSAGE = '%-160s    [file:%s lineno:%s function:%s]'
	EMBED_SOURCE_LOCATION = True
	# ログエントリの最大サイズは256KBのため大きすぎるvalueをログ出力しようとするとエラーになる
	# 若干余裕を見て80K文字で切り捨てする
	# (Log entry with size 312.2K exceeds maximum size of 256.0K)
	MAX_LOG_VALUE_LENGTH = 80 * 1000

	# auto group logs by request
	GROUP_LOGS_BY_REQUEST = True
	# ref: https://github.com/googleapis/google-cloud-go/issues/1290
	# ref: https://pkg.go.dev/cloud.google.com/go/logging?utm_source=godoc#hdr-Grouping_Logs_by_Request
	# performance batch mode that will batch all logs of a request into a single log request batch at the end, can greatly improve performance but may cause logs to be delayed
	PERFORMANCE_BATCH_MODE = False
	SIZE_BATCH_MODE = 10  # use with PERFORMANCE_BATCH_MODE, number of logs to batch together in a single request log batch
	LOGGER_PARENT_NAME = "sate_req"
	LOG_PARENT_PREFIX = "*** "
	LOGGER_CHILD_NAME = "sate_req_sub"
	LOGGER_OTHER_NAME = "sate"
	LOG_CHILD_PREFIX = "  - "
	# add watch time of process request handler to log request end messages
	SUB_MARGIN_TIME = 0.05
	LOG_WATCH_TIME = True
	# do not gather logs for requests that do not have any sub logs
	SKIP_REQUEST_WITHOUT_ANY_LOG = True
	
	USE_STANDARD_CLOUD_HANDLER_LOGGER = True
	KEEP_OLD_LOGGER_BEHAVIOR = False
	CONCAT_REQ_SUB_LOGS = True

	
	from google.cloud import logging as cloudlogging
	from google.cloud.logging_v2.handlers import CloudLoggingHandler
	log_client = cloudlogging.Client()
	# log_handler = log_client.get_default_handler()
	# log_handler = CloudLoggingHandler(log_client, name=LOGGER_OTHER_NAME) # add category name for other log by sateraito
	log_handler = log_client.get_default_handler(name=LOGGER_OTHER_NAME)
	logger = logging.getLogger("sateraitoLogger")
	#logger.setLevel(LOG_LEVEL)
	logger.addHandler(log_handler)
	logging.getLogger().setLevel(LOG_LEVEL)
	
	
	import datetime
	import time
	import flask
	import traceback
	# from google.cloud import logging as gcp_logging
	# from google.cloud.logging.resource import Resource
	
	CRITICAL = 50
	FATAL = CRITICAL
	ERROR = 40
	EXCEPTION = ERROR
	WARNING = 30
	WARN = WARNING
	INFO = 20
	DEBUG = 10
	NOTSET = 0
	
	_MAP_SEVERITY_VALUES = {
		CRITICAL: 'CRITICAL',
		ERROR: 'ERROR',
		WARNING: 'WARNING',
		INFO: 'INFO',
		DEBUG: 'DEBUG',
		NOTSET: 'NOTSET',
		'FATAL': CRITICAL,
		'CRITICAL': CRITICAL,
		'ERROR': ERROR,
		'EXCEPTION': ERROR,
		'WARN': WARNING,
		'WARNING': WARNING,
		'INFO': INFO,
		'DEBUG': DEBUG,
		'NOTSET': NOTSET,
	}
	
	client = log_client
	logger_parent = client.logger(LOGGER_PARENT_NAME)
	# logger_parent.addHandler(log_handler)
	# logger_parent.setLevel(LOG_LEVEL)
	# logger_child = logger
	logger_child = client.logger(LOGGER_CHILD_NAME)
	# logger_child.addHandler(log_handler)
	# logger_child.setLevel(LOG_LEVEL)
	
	# handler_parent = CloudLoggingHandler(client, name=LOGGER_PARENT_NAME)
	handler_parent = client.get_default_handler(name=LOGGER_PARENT_NAME)
	# from google.cloud.logging_v2.handlers.transports import SyncTransport
	# handler_parent = CloudLoggingHandler(client, name=LOGGER_PARENT_NAME, transport=SyncTransport)
	cloud_logger_parent = logging.getLogger(LOGGER_PARENT_NAME)
	# cloud_logger_parent.setLevel(LOG_LEVEL)
	cloud_logger_parent.addHandler(handler_parent)
	
	cloud_logger_child = None
	if LOGGER_CHILD_NAME != LOGGER_PARENT_NAME:
		# handler_child = CloudLoggingHandler(client, name=LOGGER_CHILD_NAME)
		handler_child = client.get_default_handler(name=LOGGER_CHILD_NAME)
		cloud_logger_child = logging.getLogger(LOGGER_CHILD_NAME)
		# cloud_logger_child.setLevel(LOG_LEVEL)
		cloud_logger_child.addHandler(handler_child)
	else:
		cloud_logger_child = cloud_logger_parent
	
	logging.getLogger().setLevel(LOG_LEVEL)
	
	
	def setup_global_cloud_logging():
		# client.setup_logging()
		
		from google.cloud.logging_v2.handlers import setup_logging
		handler = CloudLoggingHandler(client)
		
		setup_logging(handler)
		logging.getLogger("requests").setLevel(logging.WARNING)
		logging.getLogger("urllib3").setLevel(logging.WARNING)

		loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
		for l in loggers:
			l.setLevel(logging.WARNING)
			if l.level < LOG_LEVEL:
				l.setLevel(LOG_LEVEL)
		
		logging.getLogger("sateraitoLogger").setLevel(LOG_LEVEL)
		logging.getLogger().setLevel(LOG_LEVEL)
		
		logging.disable(LOG_LEVEL - 1)
	
	
	def _minimize_other_modules_logs():
		# import logging as py_logging
		py_logging = logging
		# logger = py_logging.getLogger("sateraitoLogger")
		py_logging.getLogger("requests").setLevel(py_logging.WARNING)
		py_logging.getLogger("urllib3").setLevel(py_logging.WARNING)
		py_logging.getLogger("googleapiclient").setLevel(py_logging.WARNING)
		py_logging.getLogger("google").setLevel(py_logging.WARNING)
		py_logging.getLogger("grpc").setLevel(py_logging.WARNING)
		py_logging.getLogger("gunicorn").setLevel(py_logging.WARNING)
		py_logging.getLogger("pkg_resources").setLevel(py_logging.WARNING)
		loggers = [name for name in py_logging.root.manager.loggerDict]
		for logger_name in loggers:
			# logger.info('logger_name=' + logger_name)
			if logger_name.startswith('google') or logger_name.startswith('requests'):
				l = py_logging.getLogger(logger_name)
				if l.level < py_logging.WARNING:
					l.setLevel(py_logging.WARNING)
					# l.propagate = False
	
	def _log_timestamp():
		return datetime.datetime.now(datetime.timezone.utc)
	
	
	def _log_request_latency(request_start_time):
		return "%.5fs" % (time.time() - request_start_time)
	
	
	def _get_request():
		if flask.has_request_context():
			return flask.request
		else:
			return None
	
	
	# def _get_g():
	# 	if flask.has_request_context():
	# 		return flask.g
	# 	else:
	# 		return None
	
	
	def _get_gae_header_trace(r=None):
		# if r is None:
		# 	r = _get_request()
		# if r:
		# 	return r.headers.get('X-Cloud-Trace-Context', None)
		# else:
		# 	return None
		r = flask.request
		return r.headers.get('X-Cloud-Trace-Context', None)
	
	
	def _get_trace_id():
		# r = _get_request()
		# if not r:
		# 	return None
		r = flask.request
		g = flask.g
		if hasattr(g, 'log_trace_id'):
			return g.log_trace_id
		trace_id = None
		try:
			header_trace = _get_gae_header_trace(r)
			if not header_trace:
				return None
			trace_id = header_trace.split('/')[0]
			trace_id = "projects/{project_id}/traces/{trace_id}".format(project_id=os.getenv('GOOGLE_CLOUD_PROJECT'), trace_id=trace_id)
			setattr(g, 'log_trace_id', trace_id)
		except:
			pass
		return trace_id
	
	
	def _get_request_start_time():
		r = _get_request()
		if not r:
			return None
		g = flask.g
		if hasattr(g, 'log_request_start_time'):
			return g.log_request_start_time
		request_start_time = None
		try:
			request_start_time = time.time()
			# # add some jitter to prevent logs from missing being grouped together
			# request_start_time -= SUB_MARGIN_TIME
			setattr(g, 'log_request_start_time', request_start_time)
		except:
			pass
		return request_start_time
	
	
	def _get_http_request():
		# r = _get_request()
		# if not r:
		# 	return None
		r = flask.request
		g = flask.g
		if hasattr(g, 'log_http_request'):
			return g.log_http_request
		http_request = None
		# user_agent = r.user_agent
		# if user_agent and not isinstance(user_agent, (str, bytes)):
		# 	user_agent = user_agent.string
		# elif user_agent is not None:
		# 	user_agent = str(user_agent)
		try:
			# trace_id = _get_trace_id()
			http_request = dict(
				request_method=r.method,
				request_url=r.url,
				# user_agent=user_agent,
				# # referrer=r.referrer,
				# referer=r.referrer,
				# remote_ip=r.remote_addr,
				# request_id=r.headers.get('X-Request-ID', None),
				# trace_id=trace_id,
				# # latency=_log_request_latency(_get_request_start_time() - SUB_MARGIN_TIME),
				# latency=_log_request_latency(_get_request_start_time()),
			)
			setattr(g, 'log_http_request', http_request)
		except:
			pass
		return http_request
	
	
	_MAP_LOGGER_CHILD_METHODS = {
		CRITICAL: cloud_logger_child.critical,
		ERROR: cloud_logger_child.error,
		WARNING: cloud_logger_child.warning,
		INFO: cloud_logger_child.info,
		DEBUG: cloud_logger_child.debug,
		NOTSET: cloud_logger_child.debug,
		'FATAL': cloud_logger_child.critical,
		'CRITICAL': cloud_logger_child.critical,
		'ERROR': cloud_logger_child.error,
		'EXCEPTION': cloud_logger_child.exception,
		'WARN': cloud_logger_child.warning,
		'WARNING': cloud_logger_child.warning,
		'INFO': cloud_logger_child.info,
		'DEBUG': cloud_logger_child.debug,
		'NOTSET': cloud_logger_child.debug,
	}
	
	def put_log_sub(message, severity, frame_info=None, extra=None, **kwargs):
		if not GROUP_LOGS_BY_REQUEST:
			return
		r = _get_request()
		if not r:
			return None
		severity_level = None
		if isinstance(severity, int):
			severity_level = severity
			severity = _MAP_SEVERITY_VALUES[severity]
		else:
			severity_level = _MAP_SEVERITY_VALUES[severity]
		g = flask.g
		if SKIP_REQUEST_WITHOUT_ANY_LOG:
			# mark that this request has logs
			g.log_request_has_logs = True
		
		if hasattr(g, 'log_request_severity_level'):
			request_severity_level = g.log_request_severity_level
			if request_severity_level < severity_level:
				g.log_request_severity_level = severity_level
		else:
			g.log_request_severity_level = severity_level
		
		log_exception = False
		if USE_STANDARD_CLOUD_HANDLER_LOGGER and (severity == "EXCEPTION" or severity_level == ERROR) and isinstance(message, Exception):
			log_exception = True
			if CONCAT_REQ_SUB_LOGS:
				sub_logs = getattr(g, 'req_sub_logs', None)
				req_sub_logs_len = getattr(g, 'req_sub_logs_len', 0)
				if not sub_logs:
					sub_logs = []
					g.req_sub_logs = sub_logs
					req_sub_logs_len = 0
				if req_sub_logs_len < MAX_LOG_VALUE_LENGTH:
					ex = message
					stack_trace = traceback.TracebackException.from_exception(ex)
					stack_trace_str = ''.join(stack_trace.format())
					message_ex = "[EXCEPTION] " + str(ex) + "\n" + stack_trace_str
					sub_logs.append(LOG_CHILD_PREFIX + message_ex)
					req_sub_logs_len += len(message_ex)
					g.req_sub_logs_len = req_sub_logs_len
		
		else:
			if not isinstance(message, str):
				message = str(message)
			# if not '\n' in message:
			# 	message = "  - " + message
			message = LOG_CHILD_PREFIX + message
			if CONCAT_REQ_SUB_LOGS:
				sub_logs = getattr(g, 'req_sub_logs', None)
				req_sub_logs_len = getattr(g, 'req_sub_logs_len', 0)
				if not sub_logs:
					sub_logs = []
					g.req_sub_logs = sub_logs
					req_sub_logs_len = 0
				if req_sub_logs_len < MAX_LOG_VALUE_LENGTH:
					if severity_level >= CRITICAL:
						sub_logs.append(f"[FATAL]{message}")
					elif severity_level >= ERROR:
						sub_logs.append(f"[ERROR]{message}")
					elif severity_level >= WARNING:
						sub_logs.append(f"[WARN ]{message}")
					else:
						sub_logs.append(message)
					req_sub_logs_len += len(message)
					g.req_sub_logs_len = req_sub_logs_len
			# message = LOG_CHILD_PREFIX + message
			if EMBED_SOURCE_LOCATION and frame_info:
				message = TEMPLATE_MESSAGE % (message, frame_info.filename, frame_info.lineno, frame_info.function)
		
		if USE_STANDARD_CLOUD_HANDLER_LOGGER:
			# f = _MAP_LOGGER_METHODS[severity]
			f = _MAP_LOGGER_CHILD_METHODS[severity]
			if log_exception:
				f = cloud_logger_child.exception
				if 'exc_info' not in kwargs:
					kwargs['exc_info'] = True
			# frameinfo = _frame_info(2)
			# source_location = {
			# 	"file": frameinfo.filename,
			# 	"line": frameinfo.lineno,
			# 	"function": frameinfo.function,
			# }
			if extra is None:
				extra = dict(
					# log_name=LOGGER_CHILD_NAME,
					# trace=_get_trace_id(),
					# timestamp=_log_timestamp(),
					# logger=logger_child,
					# source_location=source_location,
				)
			if frame_info:
				extra['source_location'] = {
					"file": frame_info.filename,
					"line": frame_info.lineno,
					"function": frame_info.function,
				}
			try:
				f(message, extra=extra, **kwargs)
			except Exception as ex:
				logger.warning("put_log_sub failed: %s" % ex)
				logger.error(ex, exc_info=True)
				return False
			
			return True
		
		if severity == "WARN":
			severity = "WARNING"
		elif severity == "EXCEPTION":
			severity = "ERROR"
		try:
			log_args = (
				# {
				# 	"message": message
				# },
				message,
			)
			log_kwargs = dict(
				severity=severity,
				trace=_get_trace_id(),
				timestamp=_log_timestamp(),
			)
			if PERFORMANCE_BATCH_MODE:
				batch_request_logs = getattr(g, 'batch_request_logs', None)
				if batch_request_logs is None:
					batch_request_logs = []
					setattr(g, 'batch_request_logs', batch_request_logs)
				batch_request_logs.append((log_args, log_kwargs))
				
				if len(batch_request_logs) >= SIZE_BATCH_MODE:
					# batch = logger_child.batch(client=client)
					batch = logger_child.batch()
					for pairs in batch_request_logs:
						log_args, log_kwargs = pairs
						# batch.log_struct(*log_args, **log_kwargs)
						batch.log_text(*log_args, **log_kwargs)
					# batch.commit(client=client, partial_success=True)
					batch.commit(partial_success=True)
					delattr(g, 'batch_request_logs')
				
				return True
			
			# logger_child.log_struct(*log_args, **log_kwargs)
			logger_child.log_text(*log_args, **log_kwargs)
			return True
		
		except Exception as ex:
			logger.warning("put_log_sub failed: %s" % ex)
			logger.error(ex, exc_info=True)
		
		return False
	
	
	_MAP_LOGGER_PARENT_METHODS = {
		CRITICAL: cloud_logger_parent.critical,
		ERROR: cloud_logger_parent.error,
		WARNING: cloud_logger_parent.warning,
		INFO: cloud_logger_parent.info,
		DEBUG: cloud_logger_parent.debug,
		NOTSET: cloud_logger_parent.debug,
		'FATAL': cloud_logger_parent.critical,
		'CRITICAL': cloud_logger_parent.critical,
		'ERROR': cloud_logger_parent.error,
		'EXCEPTION': cloud_logger_parent.exception,
		'WARN': cloud_logger_parent.warning,
		'WARNING': cloud_logger_parent.warning,
		'INFO': cloud_logger_parent.info,
		'DEBUG': cloud_logger_parent.debug,
		'NOTSET': cloud_logger_parent.debug,
	}
	
	def put_log_req(message, severity=None, frame_info=None, extra=None, **kwargs):
		if not GROUP_LOGS_BY_REQUEST:
			return
		r = _get_request()
		if not r:
			return None
		g = flask.g
		if severity is None:
			if hasattr(g, 'log_request_severity_level'):
				severity_level = g.log_request_severity_level
				severity = _MAP_SEVERITY_VALUES[severity_level]
			else:
				severity = "INFO"
		else:
			if isinstance(severity, int):
				severity = _MAP_SEVERITY_VALUES[severity]
		
		log_exception = False
		if USE_STANDARD_CLOUD_HANDLER_LOGGER and (severity == "EXCEPTION" or severity_level == ERROR) and isinstance(message, Exception):
			log_exception = True
		else:
			if not isinstance(message, str):
				message = str(message)
			message = LOG_PARENT_PREFIX + message
			if CONCAT_REQ_SUB_LOGS:
				sub_logs = getattr(g, 'req_sub_logs', None)
				if sub_logs:
					message += "\n" + "\n".join(sub_logs)
				sub_logs = None
				g.req_sub_logs = None
				g.req_sub_logs_len = 0
			if len(message) > MAX_LOG_VALUE_LENGTH:
				message = message[:MAX_LOG_VALUE_LENGTH]
				message += "\n..."
		
		http_request = _get_http_request()
		start_time = _get_request_start_time() - SUB_MARGIN_TIME
		latency = _log_request_latency(start_time)
		http_request['latency'] = latency
		
		if USE_STANDARD_CLOUD_HANDLER_LOGGER:
			# f = _MAP_LOGGER_METHODS[severity]
			f = _MAP_LOGGER_PARENT_METHODS[severity]
			if log_exception:
				f = cloud_logger_parent.exception
				if 'exc_info' not in kwargs:
					kwargs['exc_info'] = True
			if extra is None:
				extra = dict(
					# log_name=LOGGER_PARENT_NAME,
					# trace=_get_trace_id(),
					# timestamp=_log_timestamp(),
					# http_request=http_request,
					# logger=logger_parent,
				)
				if not KEEP_OLD_LOGGER_BEHAVIOR:
					extra['http_request'] = http_request
			if frame_info:
				extra['source_location'] = {
					"file": frame_info.filename,
					"line": frame_info.lineno,
					"function": frame_info.function,
				}
			else:
				extra['source_location'] = None
			try:
				f(message, extra=extra, **kwargs)
			except Exception as ex:
				logger.warning("put_log_req failed: %s" % ex)
				logger.error(ex, exc_info=True)
				return False
			
			return True
		
		if severity == "WARN":
			severity = "WARNING"
		elif severity == "EXCEPTION":
			severity = "ERROR"
		try:
			logger_parent.log_text(
				# {
				# 	"message": message
				# },
				message,
				severity=severity,
				trace=_get_trace_id(),
				timestamp=_log_timestamp(),
				# http_request=_get_http_request(),
				http_request=http_request,
			)
			return True
		
		except Exception as ex:
			logger.warning("put_log_req failed: %s" % ex)
			logger.error(ex, exc_info=True)
		
		return False
	
	
	def log_req_start():
		if not GROUP_LOGS_BY_REQUEST:
			return
		_get_request_start_time()
	
	
	def log_req_end(response=None):
		if not GROUP_LOGS_BY_REQUEST:
			return
		
		# request = flask.request
		request = _get_request()
		if not request:
			return
		
		g = flask.g
		if SKIP_REQUEST_WITHOUT_ANY_LOG:
			if not hasattr(g, 'log_request_has_logs'):
				return
		
		if PERFORMANCE_BATCH_MODE:
			batch_request_logs = getattr(g, 'batch_request_logs', None)
			if batch_request_logs:
				# batch = logger_child.batch(client=client)
				batch = logger_child.batch()
				for pairs in batch_request_logs:
					log_args, log_kwargs = pairs
					# batch.log_struct(*log_args, **log_kwargs)
					batch.log_text(*log_args, **log_kwargs)
				# batch.commit(client=client, partial_success=True)
				batch.commit(partial_success=True)
				delattr(g, 'batch_request_logs')
		
		# msg = '[%-4s]  %-96s' % (request.method, request.path)
		# if LOG_WATCH_TIME:
		# 	time_start = _get_request_start_time()
		# 	time_end = time.time()
		# 	msg += '  (~%.3fs)' % (time_end - time_start)
		
		if LOG_WATCH_TIME:
			time_start = _get_request_start_time()
			time_end = time.time()
			time_processed = time_end - time_start
			msg = '(~%6.3fs)  [%-4s]  %s' % (time_processed, request.method, request.path)
		else:
			msg = '[%-4s]  %s' % (request.method, request.path)
		
		if response:
			msg += '  =>  ' + str(response.status_code)
		put_log_req(msg)
	
	
	def register_app(app):
		_minimize_other_modules_logs()
		
		@app.before_request
		def before_request():
			log_req_start()
		
		# @app.teardown_request
		# def teardown_request(exception):
		# 	exception(e)
		# 	log_req_end()
		
		# if app.debug:
		# 	# app.debug is not support @app.teardown_request
		# 	@app.after_request
		# 	def after_request(response):
		# 		log_req_end(response)
		# 		return response
		# else:
		# 	# more correct time processing for flask request
		# 	@app.teardown_request
		# 	def teardown_request(ex):
		# 		if ex:
		# 			exception(ex)
		# 		log_req_end()
		
		@app.after_request
		def after_request(response):
			log_req_end(response)
			return response
		
		# @app.teardown_request
		# def teardown_request(ex):
		# 	if ex:
		# 		exception(ex)
		# 	# log_req_end()
		
		# @app.handle_exception(Exception)
		# def handle_exception(e):
		# 	if e:
		# 		exception(e)
		# 	return 'Internal Server Error', 500
	
	
	# gae_resource = Resource(
	# 	type="gae_app",
	# 	labels={
	# 		'module_id': os.getenv('GAE_SERVICE'),
	# 		'project_id': os.getenv('GOOGLE_CLOUD_PROJECT'),
	# 		'version_id': os.getenv('GAE_VERSION')
	# 	}
	# )
	
	from collections import namedtuple
	FrameInfo = namedtuple('FrameInfo', ['filename', 'lineno', 'function'])
	
	def _frame_info(walkback=0):
		# NOTE: sys._getframe() is a tiny bit faster than inspect.currentframe()
		#   Although the function name is prefixed with an underscore, it is
		#   documented and fine to use assuming we are running under CPython:
		#   https://docs.python.org/3/library/sys.html#sys._getframe
		frame = sys._getframe().f_back
		for __ in range(walkback):
			f_back = frame.f_back
			if not f_back:
				break
			frame = f_back
		return FrameInfo(frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name)
	
	# def _get_frame_info(back=1):
	# 	frameinfo = _frame_info(back)
	# 	return frameinfo
	
	def _try_format_msg(msg, *args):
		if not msg:
			return msg
		try:
			if "%" in msg:
				return msg % args
			elif "{}" in msg:
				return msg.format(*args)
			else:
				return msg
		except:
			return msg
	
	_MAP_LOGGER_METHODS = {
		CRITICAL: logger.critical,
		ERROR: logger.error,
		WARNING: logger.warning,
		INFO: logger.info,
		DEBUG: logger.debug,
		NOTSET: logger.debug,
		'FATAL': logger.critical,
		'CRITICAL': logger.critical,
		'ERROR': logger.error,
		'EXCEPTION': logger.exception,
		'WARN': logger.warning,
		'WARNING': logger.warning,
		'INFO': logger.info,
		'DEBUG': logger.debug,
		'NOTSET': logger.debug,
	}
	
	def debug(value, *args, **kwargs):
		if (LOG_LEVEL > logging.DEBUG):
			return
		
		if args and value and isinstance(value, str):
			value = _try_format_msg(value, *args)
		
		# frameinfo = inspect.stack()[1]
		# msg = (TEMPLATE_MESSAGE % (value, frameinfo.filename, frameinfo.lineno, frameinfo.function))[:MAX_LOG_VALUE_LENGTH]
		if not isinstance(value, str):
			value = str(value)
		if len(value) > MAX_LOG_VALUE_LENGTH:
			value = value[:MAX_LOG_VALUE_LENGTH]
		frameinfo = _frame_info(1)
		if GROUP_LOGS_BY_REQUEST and put_log_sub(value, "DEBUG", frame_info=frameinfo):
			return
		if EMBED_SOURCE_LOCATION:
			msg = TEMPLATE_MESSAGE % (value, frameinfo.filename, frameinfo.lineno, frameinfo.function)
		else:
			msg = value
		logger.debug(msg, **kwargs)
	
	def info(value, *args, **kwargs):
		if (LOG_LEVEL > logging.INFO):
			return
		
		if args and value and isinstance(value, str):
			value = _try_format_msg(value, *args)
		
		# frameinfo = inspect.stack()[1]
		# msg = (TEMPLATE_MESSAGE % (value, frameinfo.filename, frameinfo.lineno, frameinfo.function))[:MAX_LOG_VALUE_LENGTH]
		if not isinstance(value, str):
			value = str(value)
		if len(value) > MAX_LOG_VALUE_LENGTH:
			value = value[:MAX_LOG_VALUE_LENGTH]
		frameinfo = _frame_info(1)
		if GROUP_LOGS_BY_REQUEST and put_log_sub(value, "INFO", frame_info=frameinfo):
			return
		if EMBED_SOURCE_LOCATION:
			msg = TEMPLATE_MESSAGE % (value, frameinfo.filename, frameinfo.lineno, frameinfo.function)
		else:
			msg = value
		logger.info(msg, **kwargs)
	
	def warn(value, *args, **kwargs):
		if (LOG_LEVEL > logging.WARN):
			return
		
		if args and value and isinstance(value, str):
			value = _try_format_msg(value, *args)
		
		# frameinfo = inspect.stack()[1]
		# msg = (TEMPLATE_MESSAGE % (value, frameinfo.filename, frameinfo.lineno, frameinfo.function))[:MAX_LOG_VALUE_LENGTH]
		if not isinstance(value, str):
			value = str(value)
		if len(value) > MAX_LOG_VALUE_LENGTH:
			value = value[:MAX_LOG_VALUE_LENGTH]
		frameinfo = _frame_info(1)
		if GROUP_LOGS_BY_REQUEST and put_log_sub(value, "WARNING", frame_info=frameinfo):
			return
		if EMBED_SOURCE_LOCATION:
			msg = TEMPLATE_MESSAGE % (value, frameinfo.filename, frameinfo.lineno, frameinfo.function)
		else:
			msg = value
		logger.warning(msg, **kwargs)

	def warning(value, *args, **kwargs):
		if (LOG_LEVEL > logging.WARNING):
			return
		
		if args and value and isinstance(value, str):
			value = _try_format_msg(value, *args)
		
		# frameinfo = inspect.stack()[1]
		# msg = (TEMPLATE_MESSAGE % (value, frameinfo.filename, frameinfo.lineno, frameinfo.function))[:MAX_LOG_VALUE_LENGTH]
		if not isinstance(value, str):
			value = str(value)
		if len(value) > MAX_LOG_VALUE_LENGTH:
			value = value[:MAX_LOG_VALUE_LENGTH]
		frameinfo = _frame_info(1)
		if GROUP_LOGS_BY_REQUEST and put_log_sub(value, "WARNING", frame_info=frameinfo):
			return
		if EMBED_SOURCE_LOCATION:
			msg = TEMPLATE_MESSAGE % (value, frameinfo.filename, frameinfo.lineno, frameinfo.function)
		else:
			msg = value
		logger.warning(msg, **kwargs)

	def error(value, *args, **kwargs):
		if args and value and isinstance(str):
			value = _try_format_msg(value, *args)
		
		# frameinfo = inspect.stack()[1]
		# msg = (TEMPLATE_MESSAGE % (value, frameinfo.filename, frameinfo.lineno, frameinfo.function))[:MAX_LOG_VALUE_LENGTH]
		if not isinstance(value, str):
			value = str(value)
		if len(value) > MAX_LOG_VALUE_LENGTH:
			value = value[:MAX_LOG_VALUE_LENGTH]
		frameinfo = _frame_info(1)
		if GROUP_LOGS_BY_REQUEST and put_log_sub(value, "ERROR", frame_info=frameinfo):
			return
		if EMBED_SOURCE_LOCATION:
			msg = TEMPLATE_MESSAGE % (value, frameinfo.filename, frameinfo.lineno, frameinfo.function)
		else:
			msg = value
		logger.error(msg, *args, **kwargs)

	def exception(value, *args, **kwargs):
		if args and value and isinstance(value, str):
			value = _try_format_msg(value, *args)
		
		ex = None
		if isinstance(value, Exception):
			ex = value
		if GROUP_LOGS_BY_REQUEST and flask.has_request_context():
			if ex is not None:
				stack_trace = traceback.TracebackException.from_exception(ex)
				stack_trace_str = ''.join(stack_trace.format())
				value = str(ex) + "\n" + stack_trace_str
				number_lines = value.count('\n')
				if number_lines < 5:
					value = ex
			else:
				value = str(value)
			frameinfo = _frame_info(1)
			if put_log_sub(value, "ERROR", frame_info=frameinfo):
				return
		
		if ex is not None:
			if 'exc_info' not in kwargs:
				kwargs['exc_info'] = True
			logger.exception(ex, **kwargs)
		else:
			# if 'exc_info' in kwargs:
			# 	del kwargs['exc_info']
			# logger.error(value, **kwargs)
			if 'exc_info' not in kwargs:
				kwargs['exc_info'] = True
			logger.exception(value, **kwargs)
	
	def critical(value, *args, **kwargs):
		if args and value and isinstance(str):
			value = _try_format_msg(value, *args)
		
		# frameinfo = inspect.stack()[1]
		# msg = (TEMPLATE_MESSAGE % (value, frameinfo.filename, frameinfo.lineno, frameinfo.function))[:MAX_LOG_VALUE_LENGTH]
		if not isinstance(value, str):
			value = str(value)
		if len(value) > MAX_LOG_VALUE_LENGTH:
			value = value[:MAX_LOG_VALUE_LENGTH]
		frameinfo = _frame_info(1)
		if GROUP_LOGS_BY_REQUEST and put_log_sub(value, "CRITICAL", frame_info=frameinfo):
			return
		if EMBED_SOURCE_LOCATION:
			msg = TEMPLATE_MESSAGE % (value, frameinfo.filename, frameinfo.lineno, frameinfo.function)
		else:
			msg = value
		logger.critical(msg, *args, **kwargs)
	
	def fatal(value, *args, **kwargs):
		return critical(value, *args, **kwargs)
	

	# if 'threading' in sys.modules:
	# 	logger.info('threading module loaded.')
	# else:
	# 	logger.info('threading module loading...')
	# 	import threading



# import psutil
# import threading

# # GAEGEN2対応：メモリ使用量チューニング
# def log_memory(msg):
# 	strID = str(os.getpid()) + '/' + threading.current_thread().getName()
# 	strText = str(format_bytes(psutil.virtual_memory().used)) + ' / ' + str(format_bytes(psutil.virtual_memory().total)) + '(' +   str(psutil.virtual_memory().percent) + '%)'
# 	logger.info(strID + ' : memory used:' + strText + ' : ' + str(msg))
# 
# def format_bytes(size):
# 	power = 2 ** 10  # 2**10 = 1024
# 	n = 0
# 	power_labels = ['B', 'KB', 'MB', 'GB', 'TB']
# 	while size > power and n <= len(power_labels):
# 		size /= power
# 		n += 1
# 	return '{:.2f} {}'.format(size, power_labels[n])
