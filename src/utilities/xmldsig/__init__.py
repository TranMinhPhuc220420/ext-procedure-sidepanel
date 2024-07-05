# Copyright 息 2011 Andrew D. Yates
# All Rights Reserved
"""XMLDSig: Sign and Verify XML digital cryptographic signatures.

xmldsig is a minimal implementation of bytestring cryptographic
xml digital signatures which I have written to handle the Google
Application Single Sign On service in Security Assertion Markup
Language. (Google Apps, SSO, SAML respectively).

In this module, all XML must be in Bytestring XML Format:

Bytestring XML Format
=====================
* XML is a utf-8 encoded bytestring.
* XML namespaces must explicitly define all xmlns prefix names
* XML is in minimum whitespace representation.
* <Signature> always signs the entire xml string
* signed XML must be in "Canonicalization" (c14n) form
  see: http://www.w3.org/TR/2001/REC-xml-c14n-20010315#WithComments
* <Signature> is always enveloped as the first child of root
  see: http://www.w3.org/2000/09/xmldsig#enveloped-signature

Note that whitespace, character case, and encoding are significant in
Bytestring XML: e.g. "<b>text</b>" is not the same as "<b> text</b>".

References
==========
* [DI]
  http://www.di-mgt.com.au/xmldsig.html
  Signing an XML document using XMLDSIG
* [RFC 2437]
  http://www.ietf.org/rfc/rfc2437.txt
  PKCS #1: RSA Cryptography Specifications
* [RFC 3275]
  http://www.ietf.org/rfc/rfc3275.txt
  (Extensible Markup Language) XML-Signature Syntax and Processing
* [RSA-SHA1]
  http://www.w3.org/TR/2008/REC-xmldsig-core-20080610/#sec-PKCS1
  XML Signature Syntax and Processing (Second Edition)
  Section: 6.4.2 PKCS1 (RSA-SHA1)
"""

import hashlib
# g2対応
#import logging
import sateraito_logger as logging
import re
# GAEGEN2対応：SAML、SSO連携対応. 廃止
#import int_to_bytes as itb
# GAEGEN2対応：SAML、SSO連携対応. XML正規化ライブラリ変更
#from utilities.pyXml import c14n
#from xml.dom import minidom
import io
from lxml import etree

RX_ROOT = re.compile('<[^> ]+ ?([^>]*)>')
RX_NS = re.compile('xmlns:[^> ]+')

# LINE WORKS直接認証対応…署名に改行が入っているケースがあるので改行考慮した正規表現に変更 2019.06.13
#RX_SIGNATURE = re.compile('<Signature.*?</Signature>')
#RX_SIGNED_INFO = re.compile('<SignedInfo.*?</SignedInfo>')
#RX_SIG_VALUE = re.compile('<SignatureValue[^>]*>([^>]+)</SignatureValue>')
RX_SIGNATURE = re.compile(r'<Signature(.|\s)*?</Signature>')
RX_SIGNED_INFO = re.compile(r'<SignedInfo(.|\s)*?</SignedInfo>')
RX_SIG_VALUE = re.compile(r'<SignatureValue[^>]*>([^>]+)</SignatureValue>')

# SHA1 digest with ASN.1 BER SHA1 algorithm designator prefix [RSA-SHA1]
# GAEGEN2対応
##PREFIX = '\x30\x21\x30\x09\x06\x05\x2B\x0E\x03\x02\x1A\x05\x00\x04\x14'
PREFIX = b'\x30\x21\x30\x09\x06\x05\x2B\x0E\x03\x02\x1A\x05\x00\x04\x14'
#from pyasn1.type import univ, namedtype
#from pyasn1.codec.ber import encoder

## GAEGEN2対応:TODO 本来はPyCrypto→pycryptodome対応したい
#import Crypto.PublicKey.RSA as RSA
#from Crypto.Cipher import PKCS1_OAEP
#from Crypto.Signature import PKCS1_v1_5
#from Crypto.Hash import SHA1



#########################################
# NextSet方式（本番）

# Pattern Map:
#   xmlns_attr: xml name space definition attributes including ' ' prefix
#   digest_value: padded hash of message in base64
PTN_SIGNED_INFO_XML_WITH_C14N = \
'<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#"%(xmlns_attr)s><CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"></CanonicalizationMethod><SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"></SignatureMethod><Reference URI="%(reference_uri)s"><Transforms><Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"></Transform><Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"><ec:InclusiveNamespaces xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#" PrefixList="xs"></ec:InclusiveNamespaces></Transform></Transforms><DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"></DigestMethod><DigestValue>%(digest_value)s</DigestValue></Reference></SignedInfo>'
PTN_SIGNED_INFO_XML_WITH_C14N_WITHCOMMENTS = \
'<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#"%(xmlns_attr)s><CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#WithComments"></CanonicalizationMethod><SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"></SignatureMethod><Reference URI="%(reference_uri)s"><Transforms><Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"></Transform><Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"><ec:InclusiveNamespaces xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#" PrefixList="xs"></ec:InclusiveNamespaces></Transform></Transforms><DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"></DigestMethod><DigestValue>%(digest_value)s</DigestValue></Reference></SignedInfo>'
PTN_SIGNED_INFO_XML = \
'<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#"%(xmlns_attr)s><CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"></CanonicalizationMethod><SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"></SignatureMethod><Reference URI="%(reference_uri)s"><Transforms><Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"></Transform></Transforms><DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"></DigestMethod><DigestValue>%(digest_value)s</DigestValue></Reference></SignedInfo>'
PTN_SIGNED_INFO_XML_WITHCOMMENTS = \
'<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#"%(xmlns_attr)s><CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315#WithComments"></CanonicalizationMethod><SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"></SignatureMethod><Reference URI="%(reference_uri)s"><Transforms><Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"></Transform></Transforms><DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"></DigestMethod><DigestValue>%(digest_value)s</DigestValue></Reference></SignedInfo>'

# Pattern Map:
#   signed_info_xml: str <SignedInfo> bytestring xml
#   signature_value: str computed signature from <SignedInfo> in base64
#   key_info_xml: str <KeyInfo> bytestring xml of signing key information
#   signature_id: str in form `Id="VALUE" ` (trailing space required) or ""
PTN_SIGNATURE_XML = \
'<Signature %(signature_id)sxmlns="http://www.w3.org/2000/09/xmldsig#">%(signed_info_xml)s<SignatureValue>%(signature_value)s</SignatureValue>%(key_info_xml)s</Signature>'

# Pattern Map:
#   modulus: str signing RSA key modulus in base64 
#   exponent: str signing RSA key exponent in base64
PTN_KEY_INFO_RSA_KEY = \
'<KeyInfo><KeyValue><RSAKeyValue><Modulus>%(modulus)s</Modulus><Exponent>%(exponent)s</Exponent></RSAKeyValue></KeyValue></KeyInfo>'

# Pattern Map:
#   cert_b64: str of X509 encryption certificate in base64
#   subject_name_xml: str <X509SubjectName> bytstring xml or ""
PTN_KEY_INFO_X509_CERT = \
'<KeyInfo><X509Data>%(subject_name_xml)s<X509Certificate>%(cert_b64)s</X509Certificate></X509Data></KeyInfo>'

# Pattern Map:both
PTN_KEY_INFO_RSAKEY_AND_X509_CERT = \
'<KeyInfo><X509Data>%(subject_name_xml)s<X509Certificate>%(cert_b64)s</X509Certificate></X509Data><KeyValue><RSAKeyValue><Modulus>%(modulus)s</Modulus><Exponent>%(exponent)s</Exponent></RSAKeyValue></KeyValue></KeyInfo>'

# Pattern Map:
#   subject_name: str of <SubjectName> value
PTN_X509_SUBJECT_NAME = \
'<X509SubjectName>%(subject_name)s</X509SubjectName>'


#########################################
#########################################

# GAEGEN2対応
#b64d = lambda s: s.decode('base64')
import base64
b64d = lambda s: base64.decodebytes(s.encode())

# GAEGEN2対応：動作OK
def b64e(s):
  # GAEGEN2対応
  #if type(s) in (int, long):
  #  s = itb.int_to_bytes(s)
  if isinstance(s, int):
    hexed = "%x" % s
    if len(hexed) % 2 == 1:
      hexed = '0%s' % hexed
    s = hexed.decode('hex')
  # GAEGEN2対応
  #return s.encode('base64').replace('\n', '')
  return base64.encodebytes(s).decode().replace('\n', '')

def sign(xml, f_private, key_info_xml, key_size, with_c14n=False, with_comments=False, reference_uri='', after_issuer=False, sig_id_value=None):
  """Return xmldsig XML string from xml_string of XML.

  Args:
    xml: str of bytestring xml to sign
    f_private: func of RSA key private function
    key_size: int of RSA key modulus size in bits (usually 128, 256, 1024, 2048, etc.)
    key_info_xml: str of <KeyInfo> bytestring xml including public key
    sig_id_value: str of signature id value
  Returns:
    str: signed bytestring xml
  """
  signed_info_xml = _signed_info(xml, with_c14n=with_c14n, with_comments=with_comments, reference_uri=reference_uri)
  signed = _signed_value(signed_info_xml, key_size)
  signature_value = f_private(signed)
  
  if sig_id_value is None:
    signature_id = ""
  else:
    signature_id = 'Id="%s" ' % sig_id_value

  signature_xml = PTN_SIGNATURE_XML % {
    'signed_info_xml': signed_info_xml,
    'signature_value': b64e(signature_value),
    'key_info_xml': key_info_xml,
    'signature_id': signature_id,
  }
  
  # insert xmldsig after first '>' in message
  if after_issuer:
    if xml.find('</saml:Issuer>') >= 0:
      signed_xml = xml.replace('</saml:Issuer>', '</saml:Issuer>'+signature_xml, 1)
    elif xml.find('</saml:issuer>') >= 0:
      signed_xml = xml.replace('</saml:issuer>', '</saml:issuer>'+signature_xml, 1)
    elif xml.find('</Issuer>') >= 0:
      signed_xml = xml.replace('</Issuer>', '</Issuer>'+signature_xml, 1)
    elif xml.find('</saml2:Issuer>') >= 0:
      signed_xml = xml.replace('</saml2:Issuer>', '</saml2:Issuer>'+signature_xml, 1)
  else:
    signed_xml = xml.replace('>', '>'+signature_xml, 1)
  return signed_xml



def verify(xml, f_public, key_size, with_c14n=False, with_comments=False, reference_uri=''):
#def verify(xml, key, f_public, key_size, with_c14n=False, with_comments=False, reference_uri=''):
  """Return if <Signature> is valid for `xml`
  
  Args:
    xml: str of XML with xmldsig <Signature> element
    f_public: func from RSA key public function
    key_size: int of RSA key modulus size in bits
  Returns:
    bool: signature for `xml` is valid
  """
  #logging.debug('****** xml******')
  #logging.debug(xml)
  signature_xml = RX_SIGNATURE.search(xml).group(0)
  unsigned_xml = xml.replace(signature_xml, '')
  logging.debug('****** unsigned_xml******')
  logging.debug(unsigned_xml)
  # compute the given signed value
  signature_value = RX_SIG_VALUE.search(signature_xml).group(1)
  v = b64d(signature_value)
  expected = f_public(v)
  # compute the actual signed value
  signed_info_xml = _signed_info(unsigned_xml, with_c14n=with_c14n, with_comments=with_comments, reference_uri=reference_uri)
  actual = _signed_value(signed_info_xml, key_size)
  is_verified = (expected == actual)
  #is_verified = signer.verify(digest, actual)
  return is_verified


def key_info_xml_rsa(modulus, exponent):
  """Return <KeyInfo> xml bytestring using raw public RSA key.

  Args:
    modulus: str of bytes
    exponent: str of bytes
  Returns:
    str of bytestring xml
  """
  xml = PTN_KEY_INFO_RSA_KEY % {
    'modulus': b64e(modulus),
    'exponent': b64e(exponent),
    }
  return xml


def key_info_xml_cert(cert_b64, subject_name=None):
  """Return <KeyInfo> xml bytestring using RSA X509 certificate.

  Args:
    cert_b64: str of certificate contents in base64
    subject_name: str of value of <X509SubjectName> or None
  """
  if subject_name is None:
    subject_name_xml = ""
  else:
    subject_name_xml = PTN_X509_SUBJECT_NAME % {
      'subject_name': subject_name,
      }
  xml = PTN_KEY_INFO_X509_CERT % {
    'cert_b64': cert_b64,
    'subject_name_xml': subject_name_xml,
    }
  return xml
  
def key_info_xml_rsa_and_cert(modulus, exponent, cert_b64, subject_name=None):
  """Return <KeyInfo> xml bytestring using raw public RSA key and RSA X509 certificate.

  Args:
    modulus: str of bytes
    exponent: str of bytes
  Returns:
    str of bytestring xml
  """
  if subject_name is None:
    subject_name_xml = ""
  else:
    subject_name_xml = PTN_X509_SUBJECT_NAME % {
      'subject_name': subject_name,
      }
  xml = PTN_KEY_INFO_RSAKEY_AND_X509_CERT % {
    'modulus': b64e(modulus),
    'exponent': b64e(exponent),
    'cert_b64': cert_b64,
    'subject_name_xml': subject_name_xml,
    }
  return xml

  
# GAEGEN2対応：動作OK
def _digest(data):
  """SHA1 hash digest of message data.
  
  Implements RFC2437, 9.2.1 EMSA-PKCS1-v1_5, Step 1. for "Hash = SHA1"
  
  Args:
    data: str of bytes to digest
  Returns:
    str: of bytes of digest from `data`
  """
  # GAEGEN2対応
  #hasher = hashlib.sha1(data)
  #return hasher.digest()
  hasher = hashlib.sha1(data.encode())
  return hasher.digest()


def _get_xmlns_prefixes(xml):
  """Return string of root namespace prefix attributes in given order.
  
  Args:
    xml: str of bytestring xml
  Returns:
    str: [xmlns:prefix="uri"] list ordered as in `xml`
  """
  root_attr = RX_ROOT.match(xml).group(1)
  ns_attrs = [a for a in root_attr.split(' ') if RX_NS.match(a)]
#  ns_attrs.append('xmlns="urn:oasis:names:tc:SAML:2.0:assertion"')
  return ' '.join(ns_attrs)


def _signed_info(xml, with_c14n=False, with_comments=False, reference_uri=''):
  """Return <SignedInfo> for bytestring xml.

  Args:
    xml: str of bytestring
  Returns:
    str: xml bytestring of <SignedInfo> computed from `xml`
  """
  xmlns_attr = _get_xmlns_prefixes(xml)
  if xmlns_attr:
    xmlns_attr = ' %s' % xmlns_attr
  logging.debug(xmlns_attr)

  if with_c14n:
    # WithCommentsに対応していないSPもあるようなので（mellonなど）... 2016.08.05
    if with_comments:
      ptn_signed_info_xml = PTN_SIGNED_INFO_XML_WITH_C14N_WITHCOMMENTS
    else:
      ptn_signed_info_xml = PTN_SIGNED_INFO_XML_WITH_C14N

    signed_info_xml = ptn_signed_info_xml % {
      'xmlns_attr': xmlns_attr,
      'reference_uri': reference_uri,
      'digest_value': b64e(_digest(xml)),
    }

    logging.debug(signed_info_xml)
    # GAEGEN2対応：SAML、SSO連携対応. XML正規化ライブラリを変更
    #signed_info_xml=minidom.parseString(signed_info_xml)
    #signed_info_xml = c14n.Canonicalize(signed_info_xml)
    output = io.BytesIO()
    etree.ElementTree(etree.fromstring(signed_info_xml)).write_c14n(output, exclusive=0, with_comments=0)
    signed_info_xml = output.getvalue().decode()

    if xmlns_attr:
      ary_xmlns_attr = xmlns_attr.strip().split(' ')
      for ary_xmlns_attr_item in ary_xmlns_attr:
        signed_info_xml = signed_info_xml.replace(' ' + ary_xmlns_attr_item, '')

  else:

    # WithCommentsに対応していないSPもあるようなので（mellonなど）... 2016.08.05
    if with_comments:
      ptn_signed_info_xml = PTN_SIGNED_INFO_XML_WITHCOMMENTS
    else:
      ptn_signed_info_xml = PTN_SIGNED_INFO_XML

    signed_info_xml = ptn_signed_info_xml % {
      'xmlns_attr': xmlns_attr,
      'reference_uri': reference_uri,
      'digest_value': b64e(_digest(xml)),
    }

  logging.debug(signed_info_xml)
  return signed_info_xml


def _signed_value(data, key_size):
  """Return unencrypted rsa-sha1 signature value `padded_digest` from `data`.
  
  The resulting signed value will be in the form:
  (01 | FF* | 00 | prefix | digest) [RSA-SHA1]
  where "digest" is of the generated c14n xml for <SignedInfo>.
  
  Args:
    data: str of bytes to sign
    key_size: int of key length in bits; => len(`data`) + 3
  Returns:
    str: rsa-sha1 signature value of `data`
  """
  asn_digest = PREFIX + _digest(data)
  
  # Pad to "one octet shorter than the RSA modulus" [RSA-SHA1]
  # WARNING: key size is in bits, not bytes!
  # GAEGEN2対応
  #padded_size = key_size/8 - 1
  padded_size = (int)(key_size/8) - 1
  pad_size = padded_size - len(asn_digest) - 2
  # GAEGEN2対応
  #pad = '\x01' + '\xFF' * pad_size + '\x00'
  pad = b'\x01' + b'\xFF' * pad_size + b'\x00'
  padded_digest = pad + asn_digest

  ## ASN.1のOctetStringとしてエンコード
  #padded_digest = univ.OctetString(_digest(data))
  ## BERエンコーディングを行い、バイト列を得る
  #padded_digest = encoder.encode(padded_digest)

  return padded_digest
