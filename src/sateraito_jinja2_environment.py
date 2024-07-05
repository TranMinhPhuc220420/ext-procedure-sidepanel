# coding: utf-8

import os,sys
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
import jinja2
from google.appengine.api import memcache
from ucf.config.ucfconfig import UcfConfig
from ucf.utils import ucffunc,jinjacustomfilters
import sateraito_inc
import sateraito_func

bcc = jinja2.MemcachedBytecodeCache(client=memcache.Client(), prefix='jinja2/bytecode/', timeout=None)

##################################################
# ルート

# デフォルトデザイン
path_for_default = os.path.join(os.path.dirname(__file__), UcfConfig.TEMPLATES_FOLDER_PATH, UcfConfig.TEMPLATE_LANGUAGE_DEFAULT_FOLDER, UcfConfig.TEMPLATE_DEFAULT_DESIGN_TYPE)

# PC用
path_for_pc = os.path.join(os.path.dirname(__file__), UcfConfig.TEMPLATES_FOLDER_PATH, UcfConfig.TEMPLATE_LANGUAGE_DEFAULT_FOLDER, UcfConfig.VALUE_DESIGN_TYPE_PC)
jinja_environment_for_pc = jinja2.Environment(loader=jinja2.FileSystemLoader([path_for_pc, path_for_default], encoding=UcfConfig.FILE_CHARSET), autoescape=True, cache_size=400, auto_reload=False, bytecode_cache=bcc)
jinjacustomfilters.registCustomFilters(jinja_environment_for_pc)

# SP用
path_for_sp = os.path.join(os.path.dirname(__file__), UcfConfig.TEMPLATES_FOLDER_PATH, UcfConfig.TEMPLATE_LANGUAGE_DEFAULT_FOLDER, UcfConfig.VALUE_DESIGN_TYPE_SP)
jinja_environment_for_sp = jinja2.Environment(loader=jinja2.FileSystemLoader([path_for_sp, path_for_default], encoding=UcfConfig.FILE_CHARSET), autoescape=True, cache_size=400, auto_reload=False, bytecode_cache=bcc)
jinjacustomfilters.registCustomFilters(jinja_environment_for_sp)

# Mobile用
path_for_mobile = os.path.join(os.path.dirname(__file__), UcfConfig.TEMPLATES_FOLDER_PATH, UcfConfig.TEMPLATE_LANGUAGE_DEFAULT_FOLDER, UcfConfig.VALUE_DESIGN_TYPE_MOBILE)
jinja_environment_for_mobile = jinja2.Environment(loader=jinja2.FileSystemLoader([path_for_mobile, path_for_default], encoding=UcfConfig.FILE_CHARSET), autoescape=True, cache_size=400, auto_reload=False, bytecode_cache=bcc)
jinjacustomfilters.registCustomFilters(jinja_environment_for_mobile)

# API用
path_for_api = os.path.join(os.path.dirname(__file__), UcfConfig.TEMPLATES_FOLDER_PATH, UcfConfig.TEMPLATE_LANGUAGE_DEFAULT_FOLDER, UcfConfig.VALUE_DESIGN_TYPE_API)
jinja_environment_for_api = jinja2.Environment(loader=jinja2.FileSystemLoader([path_for_api, path_for_default], encoding=UcfConfig.FILE_CHARSET), autoescape=True, cache_size=400, auto_reload=False, bytecode_cache=bcc)
jinjacustomfilters.registCustomFilters(jinja_environment_for_api)


##################################################
# テナント

# デフォルトデザイン
tenant_path_for_default = os.path.join(os.path.dirname(__file__), UcfConfig.TEMPLATES_FOLDER_PATH, UcfConfig.TEMPLATE_LANGUAGE_DEFAULT_FOLDER, UcfConfig.TEMPLATE_DEFAULT_DESIGN_TYPE, UcfConfig.TENANT_SCRIPT_FOLDER_PATH)

# PC用
tenant_path_for_pc = os.path.join(os.path.dirname(__file__), UcfConfig.TEMPLATES_FOLDER_PATH, UcfConfig.TEMPLATE_LANGUAGE_DEFAULT_FOLDER, UcfConfig.VALUE_DESIGN_TYPE_PC, UcfConfig.TENANT_SCRIPT_FOLDER_PATH)
tenant_jinja_environment_for_pc = jinja2.Environment(loader=jinja2.FileSystemLoader([tenant_path_for_pc, tenant_path_for_default], encoding=UcfConfig.FILE_CHARSET), autoescape=True, cache_size=400, auto_reload=False, bytecode_cache=bcc)
jinjacustomfilters.registCustomFilters(tenant_jinja_environment_for_pc)

# SP用
tenant_path_for_sp = os.path.join(os.path.dirname(__file__), UcfConfig.TEMPLATES_FOLDER_PATH, UcfConfig.TEMPLATE_LANGUAGE_DEFAULT_FOLDER, UcfConfig.VALUE_DESIGN_TYPE_SP, UcfConfig.TENANT_SCRIPT_FOLDER_PATH)
tenant_jinja_environment_for_sp = jinja2.Environment(loader=jinja2.FileSystemLoader([tenant_path_for_sp, tenant_path_for_default], encoding=UcfConfig.FILE_CHARSET), autoescape=True, cache_size=400, auto_reload=False, bytecode_cache=bcc)
jinjacustomfilters.registCustomFilters(tenant_jinja_environment_for_sp)

# Mobile用
tenant_path_for_mobile = os.path.join(os.path.dirname(__file__), UcfConfig.TEMPLATES_FOLDER_PATH, UcfConfig.TEMPLATE_LANGUAGE_DEFAULT_FOLDER, UcfConfig.VALUE_DESIGN_TYPE_MOBILE, UcfConfig.TENANT_SCRIPT_FOLDER_PATH)
tenant_jinja_environment_for_mobile = jinja2.Environment(loader=jinja2.FileSystemLoader([tenant_path_for_mobile, tenant_path_for_default], encoding=UcfConfig.FILE_CHARSET), autoescape=True, cache_size=400, auto_reload=False, bytecode_cache=bcc)
jinjacustomfilters.registCustomFilters(tenant_jinja_environment_for_mobile)

# API用
tenant_path_for_api = os.path.join(os.path.dirname(__file__), UcfConfig.TEMPLATES_FOLDER_PATH, UcfConfig.TEMPLATE_LANGUAGE_DEFAULT_FOLDER, UcfConfig.VALUE_DESIGN_TYPE_API, UcfConfig.TENANT_SCRIPT_FOLDER_PATH)
tenant_jinja_environment_for_api = jinja2.Environment(loader=jinja2.FileSystemLoader([tenant_path_for_api, tenant_path_for_default], encoding=UcfConfig.FILE_CHARSET), autoescape=True, cache_size=400, auto_reload=False, bytecode_cache=bcc)
jinjacustomfilters.registCustomFilters(tenant_jinja_environment_for_api)


##################################################
# ドメイン

# デフォルトデザイン
domain_path_for_default = os.path.join(os.path.dirname(__file__), UcfConfig.TEMPLATES_FOLDER_PATH, UcfConfig.TEMPLATE_LANGUAGE_DEFAULT_FOLDER, UcfConfig.TEMPLATE_DEFAULT_DESIGN_TYPE, UcfConfig.DOMAIN_SCRIPT_FOLDER_PATH)

## PC用
#domain_path_for_pc = os.path.join(os.path.dirname(__file__), UcfConfig.TEMPLATES_FOLDER_PATH, UcfConfig.TEMPLATE_LANGUAGE_DEFAULT_FOLDER, UcfConfig.VALUE_DESIGN_TYPE_PC, UcfConfig.DOMAIN_SCRIPT_FOLDER_PATH)
#domain_jinja_environment_for_pc = jinja2.Environment(loader=jinja2.FileSystemLoader([domain_path_for_pc, domain_path_for_default], encoding=UcfConfig.FILE_CHARSET), autoescape=True, cache_size=400, auto_reload=False, bytecode_cache=bcc)
#jinjacustomfilters.registCustomFilters(domain_jinja_environment_for_pc)

## SP用
#domain_path_for_sp = os.path.join(os.path.dirname(__file__), UcfConfig.TEMPLATES_FOLDER_PATH, UcfConfig.TEMPLATE_LANGUAGE_DEFAULT_FOLDER, UcfConfig.VALUE_DESIGN_TYPE_SP, UcfConfig.DOMAIN_SCRIPT_FOLDER_PATH)
#domain_jinja_environment_for_sp = jinja2.Environment(loader=jinja2.FileSystemLoader([domain_path_for_sp, domain_path_for_default], encoding=UcfConfig.FILE_CHARSET), autoescape=True, cache_size=400, auto_reload=False, bytecode_cache=bcc)
#jinjacustomfilters.registCustomFilters(domain_jinja_environment_for_sp)

## Mobile用
#domain_path_for_mobile = os.path.join(os.path.dirname(__file__), UcfConfig.TEMPLATES_FOLDER_PATH, UcfConfig.TEMPLATE_LANGUAGE_DEFAULT_FOLDER, UcfConfig.VALUE_DESIGN_TYPE_MOBILE, UcfConfig.DOMAIN_SCRIPT_FOLDER_PATH)
#domain_jinja_environment_for_mobile = jinja2.Environment(loader=jinja2.FileSystemLoader([domain_path_for_mobile, domain_path_for_default], encoding=UcfConfig.FILE_CHARSET), autoescape=True, cache_size=400, auto_reload=False, bytecode_cache=bcc)
#jinjacustomfilters.registCustomFilters(domain_jinja_environment_for_mobile)

# API用
domain_path_for_api = os.path.join(os.path.dirname(__file__), UcfConfig.TEMPLATES_FOLDER_PATH, UcfConfig.TEMPLATE_LANGUAGE_DEFAULT_FOLDER, UcfConfig.VALUE_DESIGN_TYPE_API, UcfConfig.DOMAIN_SCRIPT_FOLDER_PATH)
domain_jinja_environment_for_api = jinja2.Environment(loader=jinja2.FileSystemLoader([domain_path_for_api, domain_path_for_default], encoding=UcfConfig.FILE_CHARSET), autoescape=True, cache_size=400, auto_reload=False, bytecode_cache=bcc)
jinjacustomfilters.registCustomFilters(domain_jinja_environment_for_api)



def getEnvironmentObj(design_type):
	# logging.info('getEnvironmentObj=%s' % design_type)
	# logging.info('path_for_pc=%s' % path_for_pc)
	# logging.info('path_for_sp=%s' % path_for_sp)
	# logging.info('path_for_mobile=%s' % path_for_mobile)
	# logging.info('path_for_api=%s' % path_for_api)
	if design_type == UcfConfig.VALUE_DESIGN_TYPE_PC:
		return jinja_environment_for_pc
	elif design_type == UcfConfig.VALUE_DESIGN_TYPE_SP:
		return jinja_environment_for_sp
	elif design_type == UcfConfig.VALUE_DESIGN_TYPE_MOBILE:
		return jinja_environment_for_mobile
	elif design_type == UcfConfig.VALUE_DESIGN_TYPE_API:
		return jinja_environment_for_api
	else:
		return jinja_environment_for_pc


def getEnvironmentObjForTenant(design_type):
	if design_type == UcfConfig.VALUE_DESIGN_TYPE_PC:
		return tenant_jinja_environment_for_pc
	elif design_type == UcfConfig.VALUE_DESIGN_TYPE_SP:
		return tenant_jinja_environment_for_sp
	elif design_type == UcfConfig.VALUE_DESIGN_TYPE_MOBILE:
		return tenant_jinja_environment_for_mobile
	elif design_type == UcfConfig.VALUE_DESIGN_TYPE_API:
		return tenant_jinja_environment_for_api
	else:
		return tenant_jinja_environment_for_pc


def getEnvironmentObjForDomain(design_type):
	return domain_jinja_environment_for_api
#	if design_type == UcfConfig.VALUE_DESIGN_TYPE_PC:
#		return domain_jinja_environment_for_pc
#	elif design_type == UcfConfig.VALUE_DESIGN_TYPE_SP:
#		return domain_jinja_environment_for_sp
#	elif design_type == UcfConfig.VALUE_DESIGN_TYPE_MOBILE:
#		return domain_jinja_environment_for_mobile
#	elif design_type == UcfConfig.VALUE_DESIGN_TYPE_API:
#		return domain_jinja_environment_for_api
#	else:
#		return domain_jinja_environment_for_pc
