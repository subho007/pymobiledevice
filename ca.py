#!/usr/bin/env python

"""
How to create a CA certificate with Python.

WARNING: This sample only demonstrates how to use the objects and methods,
         not how to create a safe and correct certificate.

Copyright (c) 2004 Open Source Applications Foundation.
Author: Heikki Toivonen
"""

from M2Crypto import RSA, X509, EVP, m2, Rand, Err, BIO
from M2Crypto.RSA import load_pub_key_bio
import base64


def der_length(length):
    #DER encoding of a length
    if length < 128:
        return chr(length)
    prefix = 0x80
    result = ''
    while length > 0:
        result = chr(length & 0xff) + result
        length >>= 8
        prefix += 1
    return chr(prefix) + result

def convertPKCS1toPKCS8pubKey(data):
    #https://mail.python.org/pipermail/python-list/2013-January/638754.html
    res = data.split('\n')
    res = '\0' + base64.decodestring("".join(res[1:-2]))
    res = '\x30\x0d\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x01\x01\x05\x00\x03' + der_length(len(res)) + res
    res = '\x30' + der_length(len(res)) + res
    res = '-----BEGIN PUBLIC KEY-----\n' + base64.encodestring(res) + '-----END PUBLIC KEY-----'
    return res

# XXX Do I actually need more keys?
# XXX Check return values from functions

def generateRSAKey():
    return RSA.gen_key(2048, m2.RSA_F4)

def makePKey(key):
    pkey = EVP.PKey()
    pkey.assign_rsa(key)
    return pkey

def makeRequest(pkey, cn):
    req = X509.Request()
    req.set_version(2)
    req.set_pubkey(pkey)
    name = X509.X509_Name()
    name.CN = cn
    req.set_subject_name(name)
    ext1 = X509.new_extension('subjectAltName', 'DNS:foobar.example.com')
    ext2 = X509.new_extension('nsComment', 'Hello there')
    extstack = X509.X509_Extension_Stack()
    extstack.push(ext1)
    extstack.push(ext2)

    assert(extstack[1].get_name() == 'nsComment')

    req.add_extensions(extstack)
    #req.sign(pkey, 'sha1')
    return req

def makeCert(req, caPkey):
    pkey = req.get_pubkey()
    #woop = makePKey(generateRSAKey())
    #if not req.verify(woop.pkey):
    if not req.verify(pkey):
        # XXX What error object should I use?
        raise ValueError, 'Error verifying request'
    sub = req.get_subject()
    # If this were a real certificate request, you would display
    # all the relevant data from the request and ask a human operator
    # if you were sure. Now we just create the certificate blindly based
    # on the request.
    cert = X509.X509()
    # We know we are making CA cert now...
    # Serial defaults to 0.
    cert.set_serial_number(1)
    cert.set_version(2)
    cert.set_subject(sub)
    issuer = X509.X509_Name()
    issuer.CN = 'The Issuer Monkey'
    issuer.O = 'The Organization Otherwise Known as My CA, Inc.'
    cert.set_issuer(issuer)
    cert.set_pubkey(pkey)
    notBefore = m2.x509_get_not_before(cert.x509)
    notAfter  = m2.x509_get_not_after(cert.x509)
    m2.x509_gmtime_adj(notBefore, 0)
    days = 30
    m2.x509_gmtime_adj(notAfter, 60*60*24*days)
    cert.add_ext(
        X509.new_extension('subjectAltName', 'DNS:foobar.example.com'))
    ext = X509.new_extension('nsComment', 'M2Crypto generated certificate')
    ext.set_critical(0)# Defaults to non-critical, but we can also set it
    cert.add_ext(ext)
    cert.sign(caPkey, 'sha1')

    assert(cert.get_ext('subjectAltName').get_name() == 'subjectAltName')
    assert(cert.get_ext_at(0).get_name() == 'subjectAltName')
    assert(cert.get_ext_at(0).get_value() == 'DNS:foobar.example.com')

    return cert

def ca():
    key = generateRSAKey()
    pkey = makePKey(key)
    req = makeRequest(pkey)
    cert = makeCert(req, pkey)
    return (cert, pkey)


def ca_do_everything(DevicePublicKey):
    rsa = generateRSAKey()
    privateKey = makePKey(rsa)
    req = makeRequest(privateKey, "The Issuer Monkey")
    cert = makeCert(req, privateKey)
    rsa2 = load_pub_key_bio(BIO.MemoryBuffer(convertPKCS1toPKCS8pubKey(DevicePublicKey)))
    pkey2 = EVP.PKey()
    pkey2.assign_rsa(rsa2)
    req = makeRequest(pkey2, "Device")
    cert2 = makeCert(req, privateKey)
    return cert.as_pem(), privateKey.as_pem(None), cert2.as_pem()

if __name__ == '__main__':
    rsa = generateRSAKey()
    pkey = makePKey(rsa)
    print pkey.as_pem(None)
    req = makeRequest(pkey, "The Issuer Monkey")
    #print req.as_text()
    cert = makeCert(req, pkey)
    print cert.as_text()
    cert.save_pem('my_ca_cert.pem')
    rsa.save_key('my_key.pem', None)
