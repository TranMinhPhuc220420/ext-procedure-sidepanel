#!/usr/bin/python
# coding: utf-8


# honban
debug_mode = True
http_mode = False
developer_mode = False

DEFAULT_AVAILABLE_USERS = 10

# session time out seconds.
session_timeout = 1440 * 60

version = '200520001'
version_dev = 'ext2005'

import logging

# ログ出力レベル
# 0：全部（10と同じ）
# 10：調査用のデバッグログも出力（調査時のみ指定）
# 20：通常ログまで出力（標準）
# 30：警告ログまで表示
# 40：エラーログまで表示（指定される想定無し）
# 50：クリティカルログまで表示（指定される想定無し）
logging_level = 10
logging.getLogger().setLevel(logging_level)

# Google App Engine setting
site_fqdn = version_dev + '-dot-' + 'vn-sateraito-apps-fileserver2.appspot.com'
if not http_mode:
  my_site_url = 'https://' + site_fqdn
else:
  my_site_url = 'http://' + site_fqdn

# Cookieのドメイン設定（別サーバーの緊急モードサイトとも申請データを共存させるため）
cookie_domain = ''

# csv downloader email
MANAGE_EMAIL = 'asao@baytech.co.jp,haraguchi@baytech.co.jp'
MANAGE_DOMAIN = 'baytech.co.jp'
MANAGE_PROTECT_CODE = '342e0527423a422fad170c93886a56e4'
# key publish email
PUBLISH_KEY_EMAILS = ['haraguchi@baytech.co.jp', 'asao@baytech.co.jp']
# sales email…営業メンバーメール
# SALES_MEMBERS_EMAILS = ['contact-info@sateraito.co.jp','asao@sateraito.co.jp']
SALES_MEMBERS_EMAILS = ['asao@sateraito.co.jp']

LIST_USER_IS_ADMIN = ['test@vn2.sateraito.co.jp', 'phuc@vnd.sateraito.co.jp']

SENDER_EMAIL = 'admin@satelaito.jp'
SUPERVISOR_EMAIL = 'asao@sateraito.co.jp'
DEFAULT_REPLY_TO_EMAIL = 'contact-info@sateraito.co.jp'

MANAGER_SITE_ACCEPT_IP_ADDRESS_LIST = ('127.0.0.1/32', '202.215.197.120/29')

max_password_history_count = 10  # パスワード履歴を保持する最大件数（デフォルト. 将来的にはドメインごとに設定もあり）

DEFAULT_LANGUAGE = 'ja'
default_language = DEFAULT_LANGUAGE
DEFAULT_TIMEZONE = 'Asia/Tokyo'
DEFAULT_ENCODING = 'SJIS'

KEY_SPLIT_RAW = '__sateraito__'
KEY_INDEX_EMPTY = '__sateraito_empty__'

DEFAULT_CHAT_SESSION_TIMEOUT = 5 * 60

# GMAILユーザーやChromeログインしていないユーザー用の専用テナント
TENANT_ID_FOR_PERSONALUSER = 'sateraitooffice.personal'

# GAEGEN2対応:検索API移行
### ElasticSEarch Config START


# mimic google app engine search api datetime field:
# ref: https://cloud.google.com/appengine/docs/legacy/standard/python/search#field-accuracy
ES_ROUND_DATETIME_AS_GAE = False

ES_MULTI_TENANT_SAME_INDEX = True
ES_CREATE_INDEX_ALIAS_FOR_NAMESPACE = True

# must be False for python 3
ES_WRITE_INDEX_BOTH_GAE_AND_ELASTICSEARCH = False

ES_PROJECT_ID_INDEX_PREFIX = ""
ES_PROJECT_ID_INDEX_PREFIX = ES_PROJECT_ID_INDEX_PREFIX + site_fqdn
ES_PROJECT_ID_INDEX_PREFIX = ES_PROJECT_ID_INDEX_PREFIX + "-dev"

ES_PROJECT_ID_INDEX_SEPARATOR = "$"
ES_NAMESPACE_SEPARATOR_INDEX = "@"
ES_NAMESPACE_SEPARATOR_DOCUMENT = "::"

ES_NAMESPACE_GLOBAL = "__GLOBAL__"
ES_DOCUMENT_KEY_INTERNAL_NAMESPACE = "@namespace"
ES_DOCUMENT_KEY_INTERNAL_ID = "@id"
ES_DOCUMENT_KEY_INTERNAL_TIMESTAMP = "@timestamp"

# ES_CLOUD_ID = "Sateraito_Dev:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvOjQ0MyRkNmMzZGQ0YmZmNTY0ZWU1OGNlMzRmZjMzOTU5ZDZjNiQyYjU2ODk5NmQ4Njk0OTFmYjQ1OWM0ODJmNTBmZTA3NA=="
ES_CLOUD_ID = "SateraitoPro:YXNpYS1ub3J0aGVhc3QxLmdjcC5jbG91ZC5lcy5pbzo0NDMkN2QwMzQxODdhZDNmNDFkNzgzYTI5YzAyZGMyM2Q5MGQkZWE5NjUwZjZjNzg0NGQ0MTk4MTViMDE0OTgxYzEwODY="

ES_AUTH_USER = "elastic"
# ES_AUTH_PASSWORD = "Ap1Q2AeLrqfiHrK8w5kOIu1w"
ES_AUTH_PASSWORD = "BBRQ690SEDnvj0QZQr2j1poD"

ES_HTTP_AUTH = (ES_AUTH_USER, ES_AUTH_PASSWORD)

ES_ELASTICSEARCH_TIMEOUT = 30

# default number of sharps of a index when create new index
ES_DEFAULT_NUMBER_OF_SHARDS = 2
# default number copy of a sharp when create new index
ES_DEFAULT_NUMBER_OF_REPLICAS = 1

# custom dict config settings apply for index by match regex pattern with index name
ES_INDEX_SETTINGS = (
  # (re.compile('test'), {
  ('test', {
    # # https://www.elastic.co/guide/en/elasticsearch/reference/current/size-your-shards.html
    # "number_of_shards": DEFAULT_NUMBER_OF_SHARDS,
    # "number_of_replicas": DEFAULT_NUMBER_OF_REPLICAS,
    # # https://www.elastic.co/guide/en/elasticsearch/reference/current/data-tiers.html
    # "index.routing.allocation.include._tier_preference": "data_hot",
  }),
)

# custom dict config mappings apply for index by match regex pattern with index name
ES_INDEX_MAPPINGS = (
  ('test', {
    # "properties": {
    #   "@id": {
    #     "type": "keyword",
    #   }
    #   "@namespace": {
    #     "type": "keyword",
    #   },
    #   "@timestamp": {
    #     "type": "date",
    #   }
    # }
  }),
)

ES_USE_ELASTICSEARCH_DOMAINS = {
  "vn2.sateraito.co.jp": True,
  "sateraito.jp": True,
}

ES_MIGRATE_KEY = 'Sateraito@2023'

### ElasticSEarch Config END

### OpenSearch Config START

# flag use OpenSearch instead of ElasticSearch for text search
OS_PREFER_USE_OPENSEARCH = True

# OS_AWS_ENDPOINT = 'https://search-sateraitopro-xdfuywdqhzawpezwwz7uwvxlvu.ap-northeast-1.es.amazonaws.com'
# OS_AUTH_USER = "sateraito"
# OS_AUTH_PASSWORD = "Sateraito@2023"

OS_AWS_ENDPOINT = 'https://search-sateraito-dev-owe6w4ttuqrt2dwd7asveo5i2i.ap-northeast-1.es.amazonaws.com'
OS_AUTH_USER = "sate"
OS_AUTH_PASSWORD = "Sateraito@2023"

OS_HTTP_AUTH = (OS_AUTH_USER, OS_AUTH_PASSWORD)

# flag to write index both ElasticSearch and OpenSearch
OS_WRITE_INDEX_BOTH_ELASTICSEARCH_AND_OPENSEARCH = False

### OpenSearch Config END

# FireBaseRealTimeDB関連設定（JavaScript側用）…JavaScriptに渡されるので不要な情報は含めないこと
FIREBASE_CONFIG = {
  "apiKey": "AIzaSyCFuEjuBomTlp_09Kre35FSzZgzUAeTFlI",
  "authDomain": "pdsasf-50ce6.firebaseapp.com",
  "databaseURL": "https://pdsasf-50ce6-default-rtdb.firebaseio.com",
  "projectId": "pdsasf-50ce6",
  "storageBucket": "pdsasf-50ce6.appspot.com",
  "messagingSenderId": "639641619695",
  "appId": "1:639641619695:web:fffd775cce7454547a1f1a",
  "measurementId": "G-WTQXNPQECY",
  "vapidKey": "BLyRTnCWp_0fUxM_f6iz6PTZTVQOu4yW0o6wz9ryAYvaPQVhLelzFY_7dJak-9QG_Qq0M7TnNyzKu35UbhhipHc",
}

URLFETCH_TIMEOUT_SECOND = 45

OAUTH2_SCOPES = [
  'https://www.googleapis.com/auth/userinfo.email',
  'https://www.googleapis.com/auth/userinfo.profile',
]
ADMIN_CONSENT_OAUTH2_SCOPES = [
  'https://www.googleapis.com/auth/userinfo.email',
  'https://www.googleapis.com/auth/userinfo.profile',
  'https://www.googleapis.com/auth/admin.directory.user.readonly',
  'https://www.googleapis.com/auth/admin.directory.group.readonly',
]

OAUTH2_SCOPES_GMAIL = [
  'https://mail.google.com',
]

OAUTH2_SCOPES_FOR_CHECK_ADMIN = [
  'https://www.googleapis.com/auth/admin.directory.user.readonly',
]

# For OpenID Connect
WEBAPP_CLIENT_ID = ''
WEBAPP_CLIENT_SECRET = ''

# 下は、AppEngine の サービスアカウントのキーを作成したときに取得できる JSON
service_account_info = {

}
