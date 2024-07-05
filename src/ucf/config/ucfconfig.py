# coding: utf-8

import os,sys
import sateraito_inc

############################################################
## 設定値定義クラス
############################################################
class UcfConfig():
	u'''設定値定義クラス'''

	# REQUESTタイプ：GET
	REQUEST_TYPE_GET = 'GET'
	# REQUESTタイプ：POST
	REQUEST_TYPE_POST = 'POST'

	# サイトのエンコード（UTF-8、shift_jis...）
	ENCODING = 'utf-8'
	# HTMLファイルのエンコード
	FILE_CHARSET = 'UTF-8'
	# ダウンロードCSVのエンコード
	DL_ENCODING = 'cp932'

	# テナントスクリプトフォルダパス
	TENANT_SCRIPT_FOLDER_PATH = 'tenant'
	# ドメインスクリプトフォルダパス
	DOMAIN_SCRIPT_FOLDER_PATH = 'domain'
	# テンプレートフォルダパス
	TEMPLATES_FOLDER_PATH = 'templates'
	#TEMPLATES_FOLDER_PATH = 'templates_automatically'		# includeを取り除いたテンプレートファイル群
	# TEMPLATES_FOLDER_PATH = 'templates_automatically' if not sateraito_inc.developer_mode else 'templates'

	# デフォルトのテンプレート言語フォルダ
	TEMPLATE_LANGUAGE_DEFAULT_FOLDER = 'default'
	# デフォルトのテンプレートデザインタイプフォルダ
	TEMPLATE_DEFAULT_DESIGN_TYPE = 'pc'
	# デフォルトのメッセージファイル名
	#MESSAGE_DEFAULT_FILE = 'default'
	MESSAGE_DEFAULT_FILE = 'ALL_ALL'
	MESSAGE_DEFAULT_LANGUAGE = 'en'
	# filesフォルダパス
	#FILES_FOLDER_PATH = 'files'
	# パラメータファイルフォルダパス
	PARAM_FOLDER_PATH = 'params'

	# Modelのkey_nameのPREFIX
	KEY_PREFIX = 'KN_'

	COOKIE_DATE_FMT = '%a, %d-%b-%Y %H:%M:%S GMT'

	# sateraito_inc で設定
#	# セッションタイムアウト（秒）
#	SESSION_TIMEOUT = 1200
	# クッキーのセッションＩＤ
	SESSION_COOKIE_NAME = 'ucf-session-sid'

	QSTRING_UNIQUEID = 'unqid'

	# ログインパスワード暗号化フラグ(on:有効. それ以外:無効)
	# オペレータデータソースなどによって切り替える必要あり
	LOGIN_PASSWORD_CRYPTOGRAPIC_FLAG = 'on'
	# ログインパスワード暗号化キー（SSOシステムなどと同じにする必要があるので注意.クッキーパスワードの暗号化にも使用）
	LOGIN_PASSWORD_CRYPTOGRAPIC_KEY = 'AEDEAA25-6D38-41a6-A884-9FFBCF2AE08D'

	# 自動ログイン機能拡張 2022.01.13
	JWT_SIGNATURE = "haVt30Yk0x1k9g2CrkW-uagFBxfDhKwNxFV94Wu0ckRt-8jI4yKjbM4q-saTeRaiT0"
	JWT_ISSUER = "NextSet"

	# クッキーキー
	COOKIE_KEY_AUTO_LOGIN = 'al'
	VALUE_AUTO_LOGIN = 'AUTO'
	COOKIE_KEY_LOGIN_TOKEN = 'UCTK'				# 自動ログイン機能拡張 2022.01.13
	COOKIE_KEY_RELAYSTATEURL = 'RSURL'
	COOKIEKEY_LEFTMENUCLASS = 'lm'		# クッキーキー：サイドメニューの開閉ステータス保持用
	COOKIE_KEY_USER_ID = 'tpid'				# AIボードの非ログインユーザー用ID
	COOKIE_KEY_TENANT_ID = 'tid'				# AIボードのテナントID
	COOKIE_KEY_UID = 'uid'				# AIボードのユーザーID（メールアドレス形式）
	COOKIE_KEY_GPT_MODEL = 'model'  # GPT4対応

	####################################
	## キャリア定義
	VALUE_CAREER_TYPE_PC = "PC"					#PCサイト
	VALUE_CAREER_TYPE_SP = "SP"			#スマートフォンサイト
	VALUE_CAREER_TYPE_TABLET = "TABLET"			#タブレット
	VALUE_CAREER_TYPE_MOBILE = "MOBILE"			#モバイルサイト
	VALUE_CAREER_TYPE_API = "API"			#API

	VALUE_CAREER_PC = "PC"							#PCプラウザ
	VALUE_CAREER_IMODE = "IMODE"
	VALUE_CAREER_EZWEB = "EZWEB"
	VALUE_CAREER_SOFTBANK = "SOFTBANK"
	VALUE_CAREER_WILLCOM = "WILLCOM"
	VALUE_CAREER_MOBILE = "MOBILE"			#3キャリア以外のモバイル

	VALUE_DESIGN_TYPE_PC = "pc"
	VALUE_DESIGN_TYPE_SP = "sp"
	VALUE_DESIGN_TYPE_MOBILE = "m"
	VALUE_DESIGN_TYPE_API = "api"

	####################################
	# セッションキー：CSRF用トークンプレフィクス
	SESSIONKEY_CSRF_TOKEN_PREFIX = 'CSRFTKN'
	# クライアントIPアドレス（オペレーションログ用）
	SESSIONKEY_CLIENTIP = 'CIP'
	# セッションキー：ログインＩＤ
	SESSIONKEY_LOGIN_ID = 'SKEYLID'
	# セッションキー：テナントＩＤ
	SESSIONKEY_TENANT_ID = 'SKEYTID'
	# セッションキー：Chrome拡張から渡された文字列（セッションでいいか微妙だが）
	SESSIONKEY_INPUT_TEXT = 'SKEYIPTTXT'
	# セッションキー：CHATGPTメッセージ履歴
	SESSION_KEY_MESSAGE_HISTORYS = 'SKEYMH'

	# セッションキー：Chrome拡張からアクセスされたかどうか
	SESSIONKEY_ACCESS_FROM_BROWSER_EXT = 'SKEYAFBE'
	# セッションキー：/voiceからアクセスされたかどうか
	SESSIONKEY_ACCESS_FROM_VOICEPAGE = 'SKEYAFVP'
	# セッションキー：ログインオペレータＩＤ
	SESSIONKEY_LOGIN_OPERATOR_ID = 'SKEYLOID'
	# セッションキー：ログインオペレータユニークＩＤ
	SESSIONKEY_LOGIN_UNIQUE_ID = 'SKEYLUID'
	# セッションキー：ログイン名称
	SESSIONKEY_LOGIN_NAME = 'SKEYLIN'
	# セッションキー：アクセス権限
	SESSIONKEY_ACCESS_AUTHORITY = 'SKEYAA'
	# セッションキー：委任管理機能
	SESSIONKEY_DELEGATE_FUNCTION = 'SKEYDMF'
	# セッションキー：委任管理する管理グループ
	SESSIONKEY_DELEGATE_MANAGEMENT_GROUPS = 'SKEYDMMG'
	# セッションキー：オペレータ所属店舗ＩＤ
	SESSIONKEY_LOGIN_DEPT_ID = 'SKEYDPTID'
	# セッションキー：オペレータメールアドレス
	SESSIONKEY_LOGIN_MAIL_ADDRESS = 'SKEYMA'
	# セッションキー：ログイン時の適用対象環境種別（office, outside, sp, fp）
	SESSIONKEY_LOGIN_TARGET_ENV = 'SKEYTENV'
	# セッションキー：ユーザにパスワード変更を強制するフラグ
	SESSIONKEY_LOGIN_FORCE_PASSWORD_CHANGE = 'SKEYPFC'
	# セッションキー：自動遷移URL処理済みフラグ
	SESSIONKEY_ALREADY_DEAL_AUTO_REDIRECT_URL = 'SKEYADARU'
	# セッションキー：rurl_key
	SESSIONKEY_RURL_KEY	= 'SKEYRURLKEY'

	# セッションに認証IDをセットする際のキー
	SESSIONKEY_AUTHID = 'authid'
	# Cookieに認証IDをセットする際のキー
	COOKIEKEY_AUTHID = 'a455431d1b604add95f9dc7e69b74c3e'

	# セッションキー：ログイン画面の端末申請の元の処理に戻るためのURL格納用
	SESSIONKEY_ORIGINAL_PROCESS_LINK_PREFIX = 'SKEYOPLK_'

	#####################################
	# 検索条件保持セッションキー
	# セッション保持用識別子Requestキー
	REQUESTKEY_SESSION_SCID = 'scid'
	# 検索条件保持セッションPREFIX
	SESSIONKEY_PREFIX_SEARCHCOND = 'sc:'
	# オペレータ一覧
	SESSIONKEY_SCOND_OPERATOR_LIST = 'f4ed32769d4041a58296b974d1626d34'
	# ログイン履歴
	SESSIONKEY_SCOND_LOGIN_HISTORY = '80fe752671664dc4b73f96dc623ddb2e'
	# オペレーションログ
	SESSIONKEY_SCOND_OPERATIONLOG = 'b969a3b2607c415e9d43bddc08e4f821'
	# チャットGPT利用履歴
	SESSIONKEY_SCOND_HISTORY = '8c9d4cec3bdf4bda8d2db1edb2923c85'
	# プロンプト管理
	SESSIONKEY_SCOND_PROMPT = 'a934de0ff44441318e63019648dd9d7b'		# プロンプト管理対応

	####################################
	## 共通
	# セッションキー：エラー情報
	SESSIONKEY_ERROR_INFO = 'SKEYEINFO'

	# セッションキー:RURL
	SESSIONKEY_RURL = 'RURL'

	# デフォルト暗号化キー（SSOマネージャと同じ）
	CRYPTO_KEY = 'B11D7E41-57C7-4680-83B0-DCF73A437566'
	COOKIE_CRYPTOGRAPIC_KEY = 'a36d610b901b44a787ef608f8ffc07cc'

	QSTRING_TYPE = 'tp'													# 編集タイプ
	QSTRING_TYPE2 = 'tp2'													# 編集タイプ２（コピー新規など用）
	QSTRING_STATUS = 'st'													# 編集ステータス

	# REQUEST値：バリデーションチェック
	VC_CHECK = 'v'
	# REQUEST値：編集タイプ（参照）
	EDIT_TYPE_REFER = 'r'
	# REQUEST値：編集タイプ（新規）
	EDIT_TYPE_NEW = 'n'
	# REQUEST値：編集タイプ（編集）
	EDIT_TYPE_RENEW = 'rn'
	# REQUEST値：編集タイプ（削除）
	EDIT_TYPE_DELETE = 'd'
	# REQUEST値：編集タイプ（スキップ）
	EDIT_TYPE_SKIP = 's'
	# REQUEST値：編集タイプ（コピー新規）
	EDIT_TYPE_COPYNEWREGIST = 'cn'
	# REQUEST値：編集タイプ（CSVダウンロード）
	EDIT_TYPE_DOWNLOAD = 'dl'
	# ステータスバック
	STATUS_BACK = 'b'

	# REQUESTキー:RURL
	REQUESTKEY_RURL = 'RURL'

	# REQUESTキーPREFIX:POSTデータ
	REQUESTKEY_POSTPREFIX = 'post_'

	# REQUESTキー:リダイレクト時パラメータ受け渡しキー（memcacheキー）
	REQUESTKEY_MEMCACHE_KEY = 'mck'

	# REQUESTキー：タスクの種類
	REQUESTKEY_TASK_TYPE = 'tk'

	# REQUESTキー：CSRF対策トークン
	REQUESTKEY_CSRF_TOKEN = 'token'

	# オペレータ権限
	# 特権管理者
	ACCESS_AUTHORITY_ADMIN = 'ADMIN'
	# 委託管理者
	ACCESS_AUTHORITY_OPERATOR = 'OPERATOR'
	# 一般ユーザ
	ACCESS_AUTHORITY_MANAGER = 'MANAGER'

	# 委託:オペレータ管理
	DELEGATE_FUNCTION_OPERATOR_CONFIG = 'OPERATOR'

	##############################
	# URL

	# ログインページ
	URL_LOGIN = '/login'
	# エラーページ
	URL_ERROR = '/error'


	# 採番関連
	# 企業ID（店舗ID）
	NUMBERING_NUMBER_ID_DEPT = 'DeptMaster'
	NUMBERING_NUMBER_SUB_ID_DEPT = '001'
	NUMBERING_PREFIX_DEPT = 'gbt'
	NUMBERING_SEQUENCE_NO_DIGIT_DEPT = 5

	# オペレーションログ
	# オペレーションタイプ（スクリーン＋オペレーションタイプが一意であること）
	OPERATION_TYPE_ADD = 'add'
	OPERATION_TYPE_MODIFY = 'modify'
	OPERATION_TYPE_REMOVE = 'remove'
	OPERATION_TYPE_CHANGEID = 'changeid'
	OPERATION_TYPE_ADD_PICTURE = 'addpicture'
	OPERATION_TYPE_REMOVE_PICTURE = 'removepicture'

	# スクリーン
	SCREEN_OPERATOR = 'operator'
	SCREEN_DASHBOARD = 'dashboard'
	SCREEN_PROMPT = 'prompt'						# プロンプト管理対応


