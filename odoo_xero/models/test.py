# from xero import Xero
# from xero.auth import PrivateCredentials
# import base64
#
# with open('/home/mateen/privatekey.pem') as keyfile:
#     rsa_key = keyfile.read()
#
# credentials = PrivateCredentials('RLKH68RBT3WYYGSK4ZWNUO1MMFXVDU', rsa_key)
#
# xero = Xero(credentials)
#
# c = xero.contacts.get(u'43c830e9-a7b4-44f9-b66e-f65b74c874d9')
# c[0]["Name"] = 'Mateen'
# try:
#     xero.contacts.save(c)
#
# except Exception:
#     print (Exception)
from xero import Xero
from xero.auth import PublicCredentials
credentials = PublicCredentials('CNALIRCTB3ZBCXHMBPCYOJFHPPWGMC', 'XFC9ZQSEDQAV6IJ8YJBKWXWVTHQTIE', 'localhost')

xero = Xero(credentials)
print(xero.contacts.all())