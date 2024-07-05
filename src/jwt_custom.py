# coding: utf-8
import base64
import binascii
import datetime
import hashlib
import json
import sys
import random

# GAEGEN2対応
import hmac
import sateraito_logger as logging

# from Cryptodome import Random
# from Cryptodome.Cipher import AES
# from Cryptodome.Protocol.KDF import PBKDF2
# from cryptography.fernet import Fernet

# GAEGEN2対応
#from collections import Iterable, Mapping
#from operator import _compare_digest as compare_digest
from collections.abc import Mapping
from secrets import compare_digest

from ucf.utils.ucfutil import UcfUtil

# from os import urandom

PY3 = sys.version_info[0] == 3
if PY3:
	text_type = str
	binary_type = bytes
else:
	text_type = unicode
	binary_type = str

trans_5C = "".join([chr(x ^ 0x5C) for x in range(256)])
trans_36 = "".join([chr(x ^ 0x36) for x in range(256)])

# HMAC が返すダイジェストのサイズは、使用する基礎的なハッシュモジュールに依存します。
# 代わりに、HMAC のインスタンスの digest_size を使用してください。

digest_size = None
_secret_backdoor_key = []


class TokenError(Exception):  # Exception during Token submit
	pass


class InvalidTokenError(TokenError):  # Exception during Token submit (Invalid signature & decode error)
	pass


class DecodeError(InvalidTokenError):
	pass


class ExpiredTokenError(TokenError):  # Exception during Token submit (expired)
	pass


class ImmatureTokenError(TokenError):  # Exception during Token submit (nbf -not yet valid)
	pass


class EncodeError(Exception):  # Exception during Token issue
	pass


# GAEGEN2対応:hmacライブラリを使うように変更
#class HMAC:
#	"""RFC2104のHMACクラスに準拠。 また、RFC4231にも準拠しています。
#	暗号化ハッシュ関数のAPI（PEP 247）に対応しています。.
#	"""
#	blocksize = 64  # 512-bit HMAC; can be changed in subclasses.
#
#	def __init__(self, key, msg=None, digestmod=None):
#		"""Create a new HMAC object.
#		key:       キー付きハッシュオブジェクトのキー.
#		msg:       ハッシュの初期入力（提供されている場合.
#		digestmod: Hashlibデフォルトのhashlib.sha256。
#		"""
#		if key is _secret_backdoor_key:  # cheap
#			return
#		if digestmod is None:
#			digestmod = hashlib.sha256
#
#		if hasattr(digestmod, '__call__'):
#			self.digest_cons = digestmod
#		else:
#			self.digest_cons = lambda d='': digestmod.new(d)
#
#		self.outer = self.digest_cons()
#		self.inner = self.digest_cons()
#		self.digest_size = self.inner.digest_size
#
#		if hasattr(self.inner, 'block_size'):
#			blocksize = self.inner.block_size
#			if blocksize < 16:
#				# Very low blocksize, most likely a legacy value like
#				# Lib/sha.py and Lib/md5.py have.
#				blocksize = self.blocksize
#		else:
#			blocksize = self.blocksize
#
#		if len(key) > blocksize:
#			key = self.digest_cons(key).digest()
#
#		key = key + chr(0) * (blocksize - len(key))
#		self.outer.update(key.translate(trans_5C))
#		self.inner.update(key.translate(trans_36))
#		if msg is not None:
#			self.update(msg)
#
#	def update(self, msg):
#		"""このハッシュオブジェクトを文字列 msg で更新します。
#		"""
#		self.inner.update(msg)
#
#	def copy(self):
#		"""このハッシュオブジェクトの別のコピーを返します。
#		このコピーを更新しても、元のオブジェクトには影響しません。
#		"""
#		other = self.__class__(_secret_backdoor_key)
#		other.digest_cons = self.digest_cons
#		other.digest_size = self.digest_size
#		other.inner = self.inner.copy()
#		other.outer = self.outer.copy()
#		return other
#
#	def _current(self):
#		"""現在の状態を表すハッシュオブジェクトを返します。
#		digest()やhexdigest()で内部的にのみ使用されます。.
#		"""
#		h = self.outer.copy()
#		h.update(self.inner.digest())
#		return h
#
#	def digest(self):
#		"""このハッシュオブジェクトのハッシュ値を返します。
#		これは、8ビットのデータを含む文字列を返します。 このオブジェクトは
#		この関数によってオブジェクトが変更されることはありません。
#		この関数を呼び出した後も、オブジェクトの更新を続けることができます。
#		"""
#		h = self._current()
#		return h.digest()
#
#	def hexdigest(self):
#		"""digest()と似ていますが、代わりに16進数の文字列を返します。
#		"""
#		h = self._current()
#		return h.hexdigest()


def random_string(string_length=16):
	s = 'abcdefghijkmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
	random_string = ''
	for j in range(string_length):
		random_string += random.choice(s)
	return random_string


class _JWT(object):
	default_key = "P@ssW0rd!SAtE1aiT0#"   # encryption password

	default_algorithms = {
		'HS256': hashlib.sha256,
		'HS384': hashlib.sha384,
		'HS512': hashlib.sha512
	}

	def encode(self, payload, key, algorithm='HS256', encrypt=None, json_encoder=None):
		if not isinstance(payload, Mapping):
			raise EncodeError('Expecting a mapping object as JWT only supports JSON objects as payloads.')
		for time_claim in ['exp', 'iat', 'nbf']:
			# Convert datetime to a epoc value
			if time_claim in payload:
				if isinstance(payload.get(time_claim), datetime.datetime):
					payload[time_claim] = timegm(payload[time_claim].utctimetuple())

		return self.encode_token(payload, key, algorithm, encrypt, json_encoder)

	def encode_token(self, payload, key, algorithm='HS256', encrypt=None, json_encoder=None):
		segments = []

		if algorithm not in self.default_algorithms:
			raise EncodeError("Algorithm '%s'is not supported" % algorithm)
		token_id = random_string()

		header = {'type': 'jwt', 'tid': token_id}
		is_payload_encrypt = False
		base64url_encoded_payload= None

		if encrypt:
			try:
				if isinstance(encrypt, str):
					if encrypt=="payload":
						json_payload = json.dumps(payload, separators=(',', ':'), cls=json_encoder).encode('utf-8')
						enc_json_payload = aes_encrypt(json_payload, self.default_key+str(token_id)+ 'payload')
						base64url_encoded_payload = base64url_encode(enc_json_payload)
						header['encrypt'] = 'payload'
						is_payload_encrypt = True
					else:
						if encrypt in payload:
							payload[encrypt] = aes_encrypt(payload[encrypt], self.default_key+str(token_id) + encrypt)
							header['encrypt'] = encrypt

				elif isinstance(encrypt, list):
					encrypt_list = []
					for pay_item in encrypt:
						if pay_item in payload:
							payload[pay_item] = aes_encrypt(payload[pay_item], self.default_key + str(token_id)+pay_item)
							encrypt_list.append(pay_item)
					header['encrypt'] = encrypt_list
				else:
					if not isinstance(encrypt, bool):
						raise EncodeError('encryption header must be one of these: [encrypt=bool] for whole token, [encrypt="payload"] for whole payload, [encrypt=str] for specific key in payload, [encrypt=list[str,str]] for multiple key in payload.')
			except TokenError:
				raise EncodeError('Encryption Error')

		if not is_payload_encrypt:
			json_payload = json.dumps(payload, separators=(',', ':'), cls=json_encoder).encode('utf-8')
			base64url_encoded_payload = base64url_encode(json_payload)
		json_header = force_bytes(json.dumps(header, separators=(',', ':'), cls=json_encoder))
		segments.append(base64url_encode(json_header))
		segments.append(base64url_encoded_payload)
		# to prevent from generation of same token
		key = key + token_id
		# Segments
		signing_input = b'.'.join(segments)
		try:
			hash_alg = self.default_algorithms[algorithm]
			key = prepare_key(key)
			signature = token_sign(signing_input, key, hash_alg)
		except KeyError:
			raise EncodeError('Algorithm not supported')
		segments.append(base64url_encode(signature))

		if encrypt:
			try:
				if isinstance(encrypt, bool):
					return aes_encrypt(b'.'.join(segments), self.default_key)
			except TokenError:
				raise EncodeError('Encryption Error')

		# GAEGEN2対応
		#return b'.'.join(segments)
		return b'.'.join(segments).decode()

	def decode(self, jwt, key='', algorithm='HS256', verify=True, **kwargs):
		if not jwt:
			raise DecodeError('Token cannot be empty')
		payload = self.decode_token(jwt, key=key, algorithm=algorithm, verify=verify)

		self._validate_claims(payload, **kwargs)
		return payload

	def decode_token(self, jwt, key='', algorithm='HS256', verify=True):
		# GAEGEN2対応
		#if len(jwt.rsplit(b'.')) == 1:
		if len(jwt.rsplit('.')) == 1:
			try:
				jwt = aes_decrypt(jwt,  self.default_key)
			except TokenError:
				raise DecodeError('decryption error')
		payload, signing_input, header, signature = self._load(jwt)
		key = key + header.get('tid')
		if verify:
			try:
				hash_alg = self.default_algorithms[algorithm]
				key = prepare_key(key)
				if not self._verify_signature(signing_input, key, signature, hash_alg):
					raise InvalidTokenError('Signature verification failed')
			except KeyError:
				raise DecodeError('Algorithm not supported')
		return payload

	def _load(self, jwt):
		if isinstance(jwt, text_type):
			jwt = jwt.encode('utf-8')
		if not issubclass(type(jwt), binary_type):
			raise DecodeError("Invalid token type. Token must be a {0}".format(str))
		try:
			signing_input, crypto_segment = jwt.rsplit(b'.', 1)
			header_segment, payload_segment = signing_input.split(b'.', 1)
		except ValueError:
			raise DecodeError('Not enough segments')
		try:
			header_data = base64url_decode(header_segment)
		except (TypeError, binascii.Error):
			raise DecodeError('Invalid header padding')
		try:
			header = eval(header_data.decode('utf-8'))
		except ValueError as e:
			raise DecodeError('Invalid header string: %s' % e)
		if not isinstance(header, Mapping):
			raise DecodeError('Invalid header string: must be a json object')

		try:
			payload = base64url_decode(payload_segment)
		except (TypeError, binascii.Error):
			raise DecodeError('Invalid payload padding')
		try:
			payload = json.loads(payload.decode('utf-8'))
			if 'encrypt' in header:
				val_pay = header.get('encrypt')
				if isinstance(val_pay, str):
					if val_pay == "payload":
						payload = aes_decrypt(payload, self.default_key + str(header.get('tid')) + val_pay)
					else:
						if val_pay in payload:
							val = aes_decrypt(payload[val_pay], self.default_key + str(header.get('tid')) + val_pay)
							# GAEGEN2対応
							#payload[val_pay] = unicode(val, "utf-8")
							payload[val_pay] = val
				if isinstance(val_pay, list):
					for val_item in val_pay:
						val = aes_decrypt(payload[val_item], self.default_key + str(header.get('tid')) + val_item)
						# GAEGEN2対応
						#payload[val_item] = unicode(val, "utf-8")
						payload[val_item] = val
		except ValueError as e:
			raise DecodeError('Invalid payload string: %s' % e)
		except TokenError:
			raise DecodeError('decryption error')
		if not isinstance(payload, Mapping):
			raise DecodeError('Invalid payload string: must be a json object')

		try:
			signature = base64url_decode(crypto_segment)
		except (TypeError, binascii.Error):
			raise DecodeError('Invalid crypto padding')

		return payload, signing_input, header, signature

	def _verify_signature(self, msg, key, sig, hash_alg):
		return compare_digest(sig, token_sign(msg, key, hash_alg))

	def _validate_claims(self, payload, **kwargs):
		now = timegm(datetime.datetime.utcnow().utctimetuple())
		if 'iat' in payload:
			self._validate_iat(payload)
		if 'exp' in payload:
			self._validate_exp(payload, now)
		if 'nbf' in payload:
			self._validate_nbf(payload, now)
		for key, value in kwargs.items():
			if str(key) in payload:
				self._validate_args(payload, str(key), value)
			else:
				raise DecodeError('(%) decode parameter is not found in Payload.', str(key))

	def _validate_exp(self, payload, now):
		try:
			exp = int(payload['exp'])
		except ValueError:
			raise DecodeError('Expiration Time claim (exp) must be an integer.')
		if exp < now:
			raise ExpiredTokenError('Token has expired')

	def _validate_iat(self, payload):
		try:
			int(payload['iat'])
		except ValueError:
			raise DecodeError('Issued At claim (iat) must be an integer.')

	def _validate_nbf(self, payload, now):
		try:
			nbf = int(payload['nbf'])
		except ValueError:
			raise DecodeError('Not Before claim (nbf) must be an integer.')
		if nbf > now:
			raise ImmatureTokenError('The token is not yet valid (nbf)')

	def _validate_args(self, payload, key, value):
		try:
			if payload[key] != value:
				raise DecodeError('Value of argument (%) is invalid', key)
		except KeyError:
			raise DecodeError('Invalid argument (%)', key)


def base64url_decode(input):
	if isinstance(input, text_type):
		input = input.encode('ascii')
	rem = len(input) % 4
	if rem > 0:
		input += b'=' * (4 - rem)
	return base64.urlsafe_b64decode(input)


def prepare_key(key):
	key = force_bytes(key)
	invalid_strings = [
		b'-----BEGIN PUBLIC KEY-----',
		b'-----BEGIN CERTIFICATE-----',
		b'-----BEGIN RSA PUBLIC KEY-----',
		b'ssh-rsa'
	]
	if any([string_value in key for string_value in invalid_strings]):
		raise EncodeError(
			'The specified key is an asymmetric key or x509 certificate and'
			' should not be used as an HMAC secret.')
	# GAEGEN2対応
	key = key.decode()
	return key


def token_sign(msg, key, hash_alg):
	# GAEGEN2対応:hmacライブラリを使うように変更
	#value = HMAC(key, msg, hash_alg).digest()
	value = hmac.new(key.encode(), msg, hash_alg).digest()
	return value


def timegm(tuple):
	EPOCH = 1970
	_EPOCH_ORD = datetime.date(EPOCH, 1, 1).toordinal()
	year, month, day, hour, minute, second = tuple[:6]
	days = datetime.date(year, month, 1).toordinal() - _EPOCH_ORD + day - 1
	hours = days * 24 + hour
	minutes = hours * 60 + minute
	seconds = minutes * 60 + second
	return seconds


def base64url_encode(input):
	return base64.urlsafe_b64encode(input).replace(b'=', b'')


def force_bytes(value):
	if isinstance(value, text_type):
		return value.encode('utf-8')
	elif isinstance(value, binary_type):
		return value
	else:
		raise EncodeError('Expected a string value')


def aes_private_key(key):
	private_key = (hashlib.pbkdf2_hmac('sha256', key, b"we1rDs@1t!", 100000))[:32]
	return private_key


def aes_encrypt(data, key):
	# private_key = hashlib.sha256(key).digest()
	# private_key = aes_private_key(str(key))
	# data = str(data) + (16 - len(data) % 16) * "\x00"
	# iv = urandom(16)
	# cipher = AES.new(private_key, AES.MODE_CBC, iv)
	# return base64.urlsafe_b64encode(iv + cipher.encrypt(data)).replace(b'=', b'')
	private_key = aes_private_key(key)
	encipher = UcfUtil.enCrypto(str(data), private_key)
	return encipher.replace(b'=', b'')


def aes_decrypt(data, key):
	# private_key = hashlib.sha256(key).digest()
	# private_key = aes_private_key(str(key))
	# data = base64.urlsafe_b64decode(str(data) + b'=' * (-len(data) % 4))
	# decipher = (AES.new(private_key, AES.MODE_CBC, data[:16])).decrypt(data[16:])
	# return decipher.rstrip('\x00')
	# decipher = Fernet(private_key)
	# return decipher.decrypt(data)

	private_key = aes_private_key(key)
	data = data + b'=' * (-len(data) % 4)
	return UcfUtil.deCrypto(data, private_key)

_jwt_obj = _JWT()
encode = _jwt_obj.encode
decode = _jwt_obj.decode


