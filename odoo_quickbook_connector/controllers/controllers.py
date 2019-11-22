# -*- coding: utf-8 -*-
from odoo import http, models, fields, api
from odoo.http import request
from .. import models
#from models.models import quickbook_credentials
import datetime
import requests
import base64
import json

class QuickBooksODOO(http.Controller):
    #current_user = fields.Many2one('res.users', 'Current User', default=lambda self: self.env.user)
    #@http.route('/quickbook/', auth='public')
    @http.route('/qb', auth='public')
    def index(self, **kw):
        auth_code = kw['code']
        realm_id = kw['realmId']
        id = request.uid
        qb_credentials = request.env['res.users'].search([])
        qb_credentials = qb_credentials.browse(request.env.context.get('uid'))
        client_id = qb_credentials.client_id
        client_secret = qb_credentials.client_secret
        redirect_uri = qb_credentials.redirect_url
        auth = client_id + ':' + client_secret
        auth = base64.b64encode(auth)
        auth1 = base64.b64encode(client_id + ':' + client_secret)
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Basic ' + auth1,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'oauth.platform.intuit.com'
        }
        datas = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': 'http://localhost:8069/qb'
        }
        urls = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer?"
        response = requests.post(urls, headers=headers, data=datas)
        content = response.content
        dict = json.loads(content)
        access_token = dict['access_token']
        refresh_token = dict['refresh_token']
        qb_credentials.access_token = access_token
        qb_credentials.refresh_access_token = refresh_token
        qb_credentials.realm_id = realm_id
