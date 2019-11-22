#import rauth
from odoo import models, fields, api
# import requests_oauthlib
import json
import logging
import requests
import webbrowser
import base64
from openerp.osv import osv
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from openerp.tools.translate import _


# The class object which deals with the quickbooks
class QuickBooksODOO(object):
    _name = 'quickbooks'

    def __init__(self, **args):
        self._logger = logging.getLogger('QuickBooks Wrapper')
        if 'client_id' in args:
            self.client_id = args['client_id']
        if 'client_secret' in args:
            self.client_secret = args['client_secret']
        if 'code' in args:
                self.code = args['code']
        if 'redirect_url' in args:
            self.redirect_url = args['redirect_url']
        if 'refresh_access_token' in args:
            self.refresh_access_token = args['refresh_access_token']
        if 'access_token' in args:
            self.access_token = args['access_token']
        self.prod_base_url_v3 = "https://quickbooks.api.intuit.com/v3"
        self.sandbox_base_url_v3 = "https://sandbox-quickbooks.api.intuit.com/v3"
        self.access_token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer?"
        self.authorize_url = "https://appcenter.intuit.com/connect/oauth2"
        self.session = None
        if 'redirect_url' in args:
            base_url = args['redirect_url']
            if base_url.endswith('/'):
                self.redirect_url = base_url #+ "qb"
            if not base_url.endswith('/'):
                self.redirect_url = base_url #+ "/qb"

    def add_record(self, **kwargs):

        '''
        # The generic function which sends
        # the respective entity to quickbooks
        :param kwargs:
        :return:
        '''
        access_token = kwargs['access_token']
        qb_data = kwargs['quickbook_data']
        data = json.dumps(qb_data)
        data = json.loads(data.decode("utf-8"))
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + str(access_token)
        }
        url = kwargs['url']
        resp = requests.post(url, json=data, headers=headers)
        if resp.status_code == 200:
            # It returns all the fields that of the entity in quickbooks
            return resp.json()
        elif resp.status_code == 401:
            # If the access token was expired it returns false
            return False

    def make_customer_url(self, account_type, realm_id):
        '''
         Function creates the url to send in request
        :param account_type:
        :param realm_id:
        :return:
        '''
        try:
            if account_type == 'sandbox':
                quickbook_url = self.sandbox_base_url_v3
            elif account_type == 'production':
                quickbook_url = self.prod_base_url_v3
            url = quickbook_url + '/company/' + str(realm_id) + '/customer/'
            return url
        except Exception as err:
            self._logger.error(err)
            return False

    def make_products_url(self, account_type, realm_id):
        # Function creates the url to send in request
        try:
            if account_type == 'sandbox':
                quickbook_url = self.sandbox_base_url_v3

            elif account_type == 'production':
                quickbook_url = self.prod_base_url_v3
            url = quickbook_url + '/company/' + str(realm_id) + '/item/'
            return url
        except Exception as err:
            self._logger.error(err)
            return False

    def make_invoice_url(self, account_type, realm_id):
        '''
        Function creates the url to send in request
        :param account_type:
        :param realm_id:
        :return:
        '''
        try:
            if account_type == 'sandbox':
                quickbook_url = self.sandbox_base_url_v3
            elif account_type == 'production':
                quickbook_url = self.prod_base_url_v3
            url = quickbook_url + '/company/' + str(realm_id) + '/invoice/'
            return url
        except Exception as err:
            self._logger.error(err)
            return False

    def refresh_token(self):
        '''
        The function which refreshes token
        :return:
        '''
        client_id = self.client_id
        client_secret = self.client_secret

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_access_token,
        }
        urls = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer?"
        response = requests.post(urls,
            data='grant_type=refresh_token&refresh_token=' +self.refresh_access_token +  '&client_id=' + self.client_id + '&client_secret=' + self.client_secret
            , headers=headers)
        #response = requests.post(urls, headers=headers, data=data)
        content = response.content
        if response.status_code == 400:
            # If refresh token expired or in special case generates token

            raise ValidationError(_('Connection Error, Please Generate Token'))
        else:
            # Else it will return the access and refresh token
            dict = json.loads(content.decode('utf-8'))
            access_token = dict['access_token']
            refresh_token = dict['refresh_token']

            self.access_token = access_token

            self.refresh_access_token = refresh_token
            return dict
