############################################
# glask-gae-sessionsライブラリをベースにカスタマイズ 2023.02.15 By T.ASAO
# 参考） https://github.com/andreibancioiu/flask-gae-sessions
#
# ＜カスタマイズ内容＞
#・Namespace="" でセッションDBが保存されるように対応
#・permanent=True時の動作整備
#・セッションアクセス時、保存時に自動延長されるように対応（permanent=True or Falseにかかわらず）
#・セッションCookie版（permanent=False）でも指定期間放置でセッションが切れるように対応
#・保存サイズ拡張対応（StringProperty → TextProperty）
#・期限切れデータ自動削除対応（DataStoreのTTL設定にて）
#
############################################
import json
# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
# GAEGEN2対応:SameSite=None判定処理のカスタマイズ
import flask
import sateraito_func
from uuid import uuid4
from datetime import datetime

from flask.sessions import SessionInterface as FlaskSessionInterface
from flask.sessions import SessionMixin
from werkzeug.datastructures import CallbackDict
from itsdangerous import Signer, BadSignature, want_bytes
from google.appengine.ext import ndb
from google.appengine.api import memcache
from google.appengine.api import namespace_manager        # デフォルトNamespace対応（Flaskのセッションモジュールの仕組み上非同期でコールされることに起因しコール元のsessionセット、ゲット前後のset_namespaceが反映されないため） 2023.02.15 By T.ASAO


class SessionModel(ndb.Model):
    created_on = ndb.DateTimeProperty(auto_now_add=True, indexed=False)
    updated_on = ndb.DateTimeProperty(auto_now=True, indexed=False)
    # セッションレコード削除時にexpires_onで並び替えをしたいのでindexed=Trueに変更→と思ったがDataStoreのTTLの仕組みで自動削除するためFalseに戻す（Indexなしが推奨なので） 2023.02.15 By T.ASAO
    expires_on = ndb.DateTimeProperty(indexed=False)
    # セッションにセットするサイズを考慮してTextPropertyに変更しておく 2023.02.15 By T.ASAO
    #data = ndb.StringProperty(indexed=False)
    data = ndb.TextProperty(indexed=False)

    def delete(self):
        self.key.delete()

    @classmethod
    def delete_by_id(cls, sid):
        ndb.Key(cls, sid).delete()

    def has_expired(self):
        return self.expires_on and self.expires_on <= datetime.utcnow()

    def should_slide_expiry(self):
        if not self.expires_on or not self.updated_on:
            return False

        # Use a precision of 5 minutes
        return (datetime.utcnow() - self.updated_on).total_seconds() > 300

    def get_data(self):
        return json.loads(want_bytes(self.data))

    def set_data(self, data):
        self.data = json.dumps(dict(data))


class ServerSideSession(CallbackDict, SessionMixin):

    # permanent対応 2023.02.15 By T.ASAO
    #def __init__(self, initial=None, sid=None):
    def __init__(self, initial=None, sid=None, permanent=None):
        def on_update(self):
            self.modified = True
        CallbackDict.__init__(self, initial, on_update)

        self.sid = sid or self._create_sid()
        self.modified = False
        self.must_create = False
        self.must_destroy = False
        if permanent:
            self.permanent = permanent

    def renew_sid(self):
        """
        Renews the session ID.
        Should be normally called when authenticating a user.
        Useful to avoid session fixation.
        """
        self.sid = self._create_sid()
        self['_renewed_on'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')

    def renewed_on(self):
        """
        Gets the timestamp of the latest session ID renewal.
        """
        value = self.get('_renewed_on', None)
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S") if value else None

    def _create_sid(self):
        """
        Creates a sessions ID.
        Cryptographically secure random string is not required.
        Guessing attacks are very hard because the cookie is signed.
        Therefore, using a UUID is fine.
        """
        return str(uuid4())


class GaeNdbSessionInterface(FlaskSessionInterface):
    """
    Uses the GAE Datastore (via ndb) as a session backend.
    """

    # permanent対応 2023.02.15 By T.ASAO
    #def __init__(self, app):
    def __init__(self, app, permanent=False):
        self.app = app
        self.permanent = permanent

    def open_session(self, app, request):
        try:
            return self._try_open_session(request)
        except BadSignature:
            logging.warning("Tampered session ID.")
        except Exception as e:
            logging.exception(e)

        return None  # In case of exceptions, Null session will be created.

    def _try_open_session(self, request):
        # デフォルトNamespace対応（Flaskのセッションモジュールの仕組み上非同期でコールされることに起因しコール元のsessionセット、ゲット前後のset_namespaceが反映されないため） 2023.02.15 By T.ASAO
        strOldNamespace = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        try:
            sid = request.cookies.get(self.app.session_cookie_name)
            if sid:
                sid = self._unsign_sid(sid)
                db_session = SessionModel.get_by_id(sid)
                if db_session:
                    # Delete expired session.
                    # Only makes sense for 'permanent' sessions.
                    if db_session.has_expired():
                        db_session.delete()
                        return None  # Null session will be created.
                    data = db_session.get_data()

                    # アクセス時に期限を自動延長する対応（セッションセット時だけでなく） 2023.02.15 By T.ASAO
                    if db_session.should_slide_expiry():
                        #expires_on = self.get_expiration_time(self.app, session)
                        #if expires_on is None:
                        expires_on = datetime.utcnow() + self.app.permanent_session_lifetime
                        db_session.expires_on = expires_on
                        db_session.put()
                else:
                    # Session not found in the datastore.
                    # Do not create a new SID yet, though.
                    data = {}
                # permanent対応 2023.02.15 By T.ASAO
                #return ServerSideSession(data, sid=sid)
                return ServerSideSession(data, sid=sid, permanent=self.permanent)
            return None  # Null session will be created.
        finally:
            namespace_manager.set_namespace(strOldNamespace)

    def make_null_session(self, app):
        return ServerSideSession()

    def save_session(self, app, session, response):
        # デフォルトNamespace対応（Flaskのセッションモジュールの仕組み上非同期でコールされることに起因しコール元のsessionセット、ゲット前後のset_namespaceが反映されないため） 2023.02.15 By T.ASAO
        strOldNamespace = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        try:
            # In case of 'log-in' (create) or 'log-out' (destroy) requests,
            # delete the existing session, if any.
            if session.must_create or session.must_destroy:
                SessionModel.delete_by_id(session.sid)

            if session.must_destroy:
                # Unset SID cookie.
                self._set_session_cookie(response, None)
                return

            # Avoid session fixation attacks by generating a new SID.
            # 'must_create' should be set at least when creating authenticated sessions.
            if session.must_create:
                session.renew_sid()

            # Fetch session from datastore
            db_session = SessionModel.get_by_id(session.sid)
            if not db_session:
                # Missing in datastore. Thus, create a new one.
                db_session = SessionModel(id=session.sid)

            # Avoid unnecessary calls to datastore by implementing a less precise
            # sliding timeout (for 'permanent' sessions).
            if session.modified or db_session.should_slide_expiry():
                db_session.set_data(session)
                # Only makes sense for 'permanent' sessions.
                # セッションCookie（parmanent=False）の場合でも、指定時間放置したらセッションをクリアする対応（デフォルトだとブラウザを閉じるまで残り続けるため.期限はapp.permanent_session_lifetimeを流用） 2023.02.15 By T.ASAO
                #db_session.expires_on = self.get_expiration_time(app, session)
                expires_on = self.get_expiration_time(app, session)
                if expires_on is None:
                    expires_on = datetime.utcnow() + app.permanent_session_lifetime
                # permanent対応. ndbセットのためにaware→naiveに変換 2023.02.15 By T.ASAO
                else:
                    expires_on = expires_on.replace(tzinfo=None)
                db_session.expires_on = expires_on
                db_session.put()

            sid = self._sign_sid(session.sid)
            # セッションCookie（parmanent=False）の場合でも、指定時間放置したらセッションをクリアする対応 （デフォルトだとブラウザを閉じるまで残り続けるため.期限はapp.permanent_session_lifetimeを流用）…セッションIDのCookieに期限がセットされないように 2023.02.15 By T.ASAO
            #self._set_session_cookie(response, sid, db_session.expires_on)
            self._set_session_cookie(response, sid, db_session.expires_on if self.permanent else None)
        finally:
            namespace_manager.set_namespace(strOldNamespace)

    def _set_session_cookie(self, response, sid, expires=None):
        name = self.app.session_cookie_name
        domain = self.get_cookie_domain(self.app)
        path = self.get_cookie_path(self.app)
        secure = self.get_cookie_secure(self.app)
        # SameSite対応＆ついでにhttponlyも設定から取得対応 2023.02.15 By T.ASAO
        samesite = self.get_cookie_samesite(self.app)
        httponly = self.get_cookie_httponly(self.app)
        if not sateraito_func.isSameSiteCookieSupportedUA(flask.request.headers.get('User-Agent')):
          samesite = None

        if not sid:
            response.delete_cookie(name, domain=domain, path=path)
        else:
            # SameSite対応＆ついでにhttponlyも設定から取得対応 2023.02.15 By T.ASAO
            #response.set_cookie(name, sid,
            #                    expires=expires, httponly=True,
            #                    domain=domain, path=path, secure=secure)
            response.set_cookie(name, sid,
                                expires=expires, httponly=httponly,
                                domain=domain, path=path, secure=secure, samesite=samesite)

    def _unsign_sid(self, signed_sid):
        signer = self._get_signer()
        sid_as_bytes = signer.unsign(signed_sid)
        return sid_as_bytes.decode()

    def _sign_sid(self, unsigned_sid):
        signer = self._get_signer()
        return signer.sign(want_bytes(unsigned_sid))

    def _get_signer(self):
        key = self.app.secret_key
        if not key:
            raise ValueError('Secret key missing.')
        return Signer(key, salt='flask-session', key_derivation='hmac')
