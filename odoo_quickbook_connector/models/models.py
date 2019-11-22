# -*- coding: utf-8 -*-
import os
from odoo import models, fields, api, _
from .quickbooks import QuickBooksODOO
from openerp.osv import osv
from odoo.exceptions import UserError, ValidationError
import datetime
import time
import requests
import webbrowser
import base64
from odoo.http import request
import json
import random
from openerp.exceptions import Warning


root_path = os.path.dirname(os.path.abspath(__file__))


class QuickBooksCredentials(models.Model):
    """
    This Class holds the current user credentials.
    """

    _inherit = 'res.users'

    client_id = fields.Char(string="Client ID", required=True)
    client_secret = fields.Char(string="Client Secret", required=True)
    redirect_url = fields.Char(string="Base URL", required=True)
    login_url = fields.Char('Login URL', compute='_compute_url', readonly=True)

    auth_code = fields.Char(string="code")
    code = fields.Char(string='code')
    qb_email = fields.Char(string='Email Address', required=True)
    qb_password = fields.Char(string='Password', required=True)
    # login_url = fields.Char(string='Login Url', readonly=True)
    access_token = fields.Char(string="Access Token")
    refresh_access_token = fields.Char(string='Refresh Token')
    # Realm_id is the previous Company_id
    realm_id = fields.Char(string="Realm ID")
    access_token_time = fields.Datetime(string='Token Generation Time')

    def _get_account_list(self):

        return (('sandbox', 'Sandbox'), ('production', 'Production'))

    account_type = fields.Selection('_get_account_list', string='QuickBooks Account Type', required=True)

    @api.one
    def _compute_url(self):
        """
        this function creates a url. By hitting this URL creates a code that is require to generate token. That token will be sent with every API request
        :return:
        """
        authorize_url = "https://appcenter.intuit.com/connect/oauth2"
        redirect_url = 'redirect_uri=' + str(self.redirect_url) + '&'
        client_id = 'client_id=' + str(self.client_id) + '&'
        authorize_url = str(authorize_url) + '?'
        scope = 'scope=com.intuit.quickbooks.accounting&'
        state = 'state=1234567898989'
        self.login_url = authorize_url + client_id + 'response_type=code&' + scope + redirect_url + state
        # webbrowser.open_new(self.login_url)

    @api.multi
    def test_connection(self):
        """
        This Functin Test the User Account Connection

        :return:
        """
        if not self.client_id or not self.redirect_url or not self.client_secret:
            raise osv.except_osv(_("Error!"), (_(
                "Please give Credentials!")))
        else:
            try:
                self.env.user.client_id = self.client_id
                self.env.user.redirect_url = self.redirect_url
                self.env.user.client_secret = self.client_secret
                self.env.user.qb_email = self.qb_email
                self.env.user.qb_password = self.qb_password
                self.env.cr.commit()

            except Exception as e:
                raise ValidationError(_((e)))

            raise osv.except_osv(_("Success!"), (_("Successfully! Url is Generated!")))

    def generate_token(self):
        """
        The function Generates Token
        :return:
        """
        if not self.client_id or not self.redirect_url or not self.client_secret:
            raise osv.except_osv(_("Error!"), (_("Please ask admin to add Office365 settings!")))

        else:

            header = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            try:
                response = requests.post(
                    "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer?",
                    data='grant_type=authorization_code&code=' + self.code + '&redirect_uri=' + self.redirect_url + '&client_id=' + self.client_id + '&client_secret=' + self.client_secret
                    , headers=header).content
                response = json.loads(response.decode('utf-8'))
                self.access_token = response['access_token']
                self.refresh_access_token = response['refresh_token']

                self.env.user.expire_in = int(round(time.time() * 1000))
                self.env.user.code = self.code
                self.env.user.access_token = self.access_token
                self.env.user.refresh_access_token = self.refresh_access_token
                self.env.user.access_token_time = self.access_token_time
                self.env.cr.commit()

            except Exception as e:
                raise  ValidationError(e)

            raise osv.except_osv(_("Success!"), (_("Successfully! Token Generated!")))

    def get_refresh_token(self):
        """

        The function which refreshes the access token
        :return:
        """
        client_id = self.client_id
        client_secret = self.client_secret
        refresh_token = self.refresh_access_token
        # Authorization Code generates here then is added in the header section
        auth = base64.b64encode(client_id + ':' + client_secret)
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Basic ' + auth,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'oauth.platform.intuit.com',
            'Cache-Control': 'no-cache'
        }
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        }
        urls = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer?"
        response = requests.post(urls, headers=headers, data=data)
        content = response.content
        dict = json.loads(content.decode('utf-8'))
        access_token = dict['access_token']
        refresh_token = dict['refresh_token']
        qb = request.env['res.users'].search([])
        qb = qb.browse(request.env.context.get('uid'))
        qb.access_token = access_token
        self.access_token = access_token
        qb.refresh_access_token = refresh_token
        self.refresh_access_token = refresh_token
        print (dict)


class QuickBookProductSync(models.Model):

    _inherit = 'product.template'

    quickbooks_id = fields.Char('quickbooks_id')
    sync_token = fields.Char('sync_token', default='0')

    # The class object of the Product to send to Quickbooks
    def sync_product(self, is_auto):
        """
        he function which is launched when user clicks on the Sync Button
        :return:
        """
        product = self
        current_user = self.env.user
        quickbook_realm_id = current_user.realm_id
        quickbook_client_id = current_user.client_id
        quickbook_client_secret = current_user.client_secret
        quickbook_access_token = current_user.access_token
        quickbook_refresh_token = current_user.refresh_access_token
        quickbook_account_type = current_user.account_type
        quickbook_create_time = current_user.access_token_time
        if quickbook_access_token and quickbook_refresh_token:
            # Checks if the user had the initial access token and refresh token
            quickbook_obj = QuickBooksODOO(realm_id=quickbook_realm_id, client_id=quickbook_client_id,
                                           client_secret=quickbook_client_secret,
                                           refresh_access_token=quickbook_refresh_token)
            url = quickbook_obj.make_products_url(quickbook_account_type, quickbook_realm_id)
            test = self.env['res.users'].search([])
            # test = test.browse(request.uid)
            # test = test.test_connection()
            if is_auto:
                objects = self.env['product.template'].search([])
            else:
                objects = self
            for each in objects:
                # The Product selected to sync
                quickbook_data = self.get_product_fields(each)

                if each.quickbooks_id:
                    quickbook_data['Id'] = each.quickbooks_id
                    quickbook_data['SyncToken'] = each.sync_token
                    url = url + "?operation=update&minorversion=4"
                resp = quickbook_obj.add_record(url=url, quickbook_data=quickbook_data,
                                                access_token=quickbook_access_token,
                                                refresh_access_token=quickbook_refresh_token)
                if resp is False:
                    # If response had 400 or 401 error then it first refreshes
                    # the token and updates the respective objects too
                    response = quickbook_obj.refresh_token()
                    access_token = response['access_token']
                    refresh_token_new = response['refresh_token']
                    current_user.access_token = access_token
                    current_user.refresh_access_token = refresh_token_new
                    resp = quickbook_obj.add_record(url=url, quickbook_data=quickbook_data,
                                                    access_token=access_token,
                                                    refresh_access_token=refresh_token_new)
                    if resp and 'Item' in resp.keys():
                        if each.quickbooks_id:
                            each.write({'sync_token': str(int(each.sync_token) + 1),
                                           'quickbooks_id': resp['Item']['Id']
                                           })
                        else:
                            each.write({'quickbooks_id': resp['Item']['Id']})
                        self.env.cr.commit()
                else:
                    if resp and 'Item' in resp.keys():
                        if each.quickbooks_id:
                            each.write({'sync_token': str(int(each.sync_token) + 1),
                                           'quickbooks_id': resp['Item']['Id']
                                           })
                        else:
                            each.write({'quickbooks_id': resp['Item']['Id']})
                        self.env.cr.commit()
            raise ValidationError(_('Successfully Synced'))
        else:
            raise ValidationError(_('Access token is missing'))

    def get_product_fields(self, res):

        """

        This function gets the required values for syncing
        :param res:
        :return:
        """
        dict = {}
        if res.type == 'product':
            dict['Type'] = 'Inventory'
            dict['AssetAccountRef'] = {
                'value': '81',
                'name': 'Inventory Asset'
            }
            dict["ExpenseAccountRef"] = {
                "value": "80",
                "name": "Cost of Goods Sold"
            }
            dict['TrackQtyOnHand'] = True
            if res.qty_available:
                dict['QtyOnHand'] = str(int(float(res.qty_available)))
            elif not res.qty_available:
                dict['QtyOnHand'] = str(0)
        if res.display_name:
            dict['Name'] = str(res.display_name)
        if not res.display_name:
            dict['Name'] = str(res.name)
        if res.standard_price:
            dict['UnitPrice'] = str(res.standard_price)
        if res.list_price:
            dict['UnitPrice'] = str(res.list_price)
        if res.type == 'service' or res.type == 'consu':
            dict['Type'] = 'Service'
        dict['IncomeAccountRef'] = {
            'value': '79',
            'name': 'Sales of Product Income'
        }
        if res.price:
            dict['UnitPrice'] = str(res.price)
        dict['SyncToken'] = str(random.randrange(0, 4))
        if res.create_date:
            date = res.create_date
            date = date.split()
            dict['InvStartDate'] = date[0]
        return dict


# The class object of the invoices to sync
class QuickBookInvoiceSync(models.Model):
    _inherit = 'account.invoice'

    quickbooks_id = fields.Char('quickbooks_id')
    sync_token = fields.Char('sync_token', default='0')

    def sync_invoice(self, is_auto):
        """
        The function which is launched when the user clicks on the sync button
        :return:
        """
        current_user = self.env.user
        quickbook_realm_id = current_user.realm_id
        quickbook_client_id = current_user.client_id
        quickbook_client_secret = current_user.client_secret
        quickbook_access_token = current_user.access_token
        quickbook_refresh_token = current_user.refresh_access_token
        quickbook_account_type = current_user.account_type
        quickbook_create_time = current_user.access_token_time

        if not quickbook_access_token:
            raise ValidationError(_('Access token is missing'))

        quickbook_obj = QuickBooksODOO(realm_id=quickbook_realm_id, client_id=quickbook_client_id,
                                       client_secret=quickbook_client_secret,
                                       refresh_access_token=quickbook_refresh_token)
        url = quickbook_obj.make_invoice_url(quickbook_account_type, quickbook_realm_id)
        test = self.env['res.users'].search([])

        already_exist = False
        if is_auto:
            objects = self.env['account.invoice'].search([("type", "=", "out_invoice")])
        else:
            objects = self
        for invoice in objects:
            if invoice.quickbooks_id:
                already_exist = True
            # The selected invoices by the user
            customer = invoice.partner_id
            date = invoice.date_invoice
            customer_name = customer.name
            customer_id = self.get_record_qb('customer', customer_name, quickbook_realm_id, quickbook_access_token,
                                             quickbook_client_id, quickbook_client_secret, quickbook_account_type,
                                             quickbook_refresh_token)
            invoice_dict = {}
            invoice_dict['CustomerRef'] = {}
            invoice_dict['CustomerRef']['value'] = str(customer_id)
            invoice_dict['TxnDate'] = date
            if already_exist:
                invoice_dict['Id'] = invoice.quickbooks_id
                invoice_dict['SyncToken'] = invoice.sync_token
                url = url + "?operation=update&minorversion=4"
            line_list = []
            for invoice_line in invoice.invoice_line_ids:
                # For every line item in the invoices
                unit_price = invoice_line.price_unit
                quantity = invoice_line.quantity
                amount = unit_price * quantity

                product_id = self.get_record_qb('item', invoice_line.product_id.display_name, quickbook_realm_id,
                                                quickbook_access_token, quickbook_client_id, quickbook_client_secret,
                                                quickbook_account_type, quickbook_refresh_token)
                temp = {}
                temp['Amount'] = amount
                detail_type = "SalesItemLineDetail"
                temp['DetailType'] = detail_type
                temp['SalesItemLineDetail'] = {}
                temp['SalesItemLineDetail']['ItemRef'] = {}
                temp['SalesItemLineDetail']['ItemRef']['value'] = str(product_id)
                temp['SalesItemLineDetail']['Qty'] = quantity
                temp['SalesItemLineDetail']['UnitPrice'] = unit_price
                line_list.append(temp.copy())
            invoice_dict['Line'] = line_list
            resp = quickbook_obj.add_record(url=url, quickbook_data=invoice_dict,
                                            access_token=quickbook_access_token,
                                            refresh_access_token=quickbook_refresh_token)

            if resp is False:
                # If the access token is expired it will refresh the token
                # and then will sync the invoice
                response = quickbook_obj.refresh_token()
                access_token = response['access_token']
                refresh_token_new = response['refresh_token']
                self.env.user.access_token = access_token
                self.env.user.refresh_access_token = refresh_token_new
                resp = quickbook_obj.add_record(url=url, quickbook_data=invoice_dict,
                                                access_token=access_token,
                                                refresh_access_token=refresh_token_new)
                if resp:
                    if invoice.quickbooks_id:
                        invoice.write({'sync_token': str(int(invoice.sync_token) + 1),
                                    'quickbooks_id': resp['Invoice']['Id']
                                    })
                    else:
                        invoice.write({'quickbooks_id': resp['Invoice']['Id']})
                    self.env.cr.commit()
            elif resp:
                if invoice.quickbooks_id:
                    invoice.write({'sync_token': str(int(invoice.sync_token) + 1),
                                   'quickbooks_id': resp['Invoice']['Id']
                                   })
                else:
                    invoice.write({'quickbooks_id': resp['Invoice']['Id']})
                self.env.cr.commit()
        raise Warning(_("Successfully Synced", ))

    def import_invoice(self):
        pass

    def get_record_qb(self, table, name, realm_id, access_token, client_id, client_secret, account_type, refresh_token):

        """
         The function which gets the records from quickbooks to get
         id of product and customer

        :param table:
        :param name:
        :param realm_id:
        :param access_token:
        :param client_id:
        :param client_secret:
        :param account_type:
        :param refresh_token:
        :return:
        """
        if table == 'item':
            print ("Table:" + table)
            base_url = "https://sandbox-quickbooks.api.intuit.com/v3/company"
            url = base_url + "/" + realm_id + "/query?query=select id from " + table + " where name='" + name + "'"
            headers = {
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + access_token
            }
            response = requests.get(url, headers=headers)
            quickbook_obj = QuickBooksODOO(realm_id=realm_id, client_id=client_id,
                                           client_secret=client_secret, refresh_access_token=refresh_token)

            if response.status_code == 200:
                data = response.json()
                if not data['QueryResponse']:
                    # If the product is not available in quickbooks
                    # then create the product first
                    url = quickbook_obj.make_products_url(account_type, realm_id)
                    product = self.env['product.template'].search([])
                    for each in product:
                        # For every product selected by the user
                        if each.display_name == name or each.name == name:
                            product_to_sync = each
                            quickbook_data = product.get_product_fields(product_to_sync)
                            resp = quickbook_obj.add_record(url=url, quickbook_data=quickbook_data,
                                                            access_token=access_token,
                                                            refresh_access_token=refresh_token)
                            if not resp['Item']['Id']:
                                # If the Product to Sync didnt had the required values
                                raise ValidationError(_('Error in Creating Product'))
                            if resp is False:
                                # If the access token was expired
                                response = quickbook_obj.refresh_token()
                                access_token = response['access_token']
                                refresh_token_new = response['refresh_token']
                                self.env.user.access_token = access_token
                                self.env.user.refresh_access_token = refresh_token_new
                                resp = quickbook_obj.add_record(url=url, quickbook_data=quickbook_data,
                                                                access_token=access_token,
                                                                refresh_access_token=refresh_token_new)
                                if resp and 'Item' in resp.keys():
                                    each.write({'quickbooks_id': resp['Item']['Id']})
                                    self.env.cr.commit()
                            if resp and 'Item' in resp.keys():
                                each.write({'quickbooks_id': resp['Item']['Id']})
                                self.env.cr.commit()
                            # Returns the Product Id in Quickbooks
                            return resp['Item']['Id']
                else:
                    # If the product was found this way it extracts the id
                    temp = data['QueryResponse']['Item']
                    if isinstance(temp, list):
                        product_id = temp[0]['Id']
                        # Returns the product id
                        return product_id
            elif response.status_code == 401 or response.status_code == 400:
                # If the access token or refresh token was expired
                # Refresh token first then get product id
                resp = quickbook_obj.refresh_token()
                access_token = resp['access_token']
                refresh_token_new = resp['refresh_token']
                self.env.user.access_token = access_token
                self.env.user.refresh_access_token = refresh_token_new
                response = self.get_record_qb(table, name, realm_id, access_token, client_id, client_secret,
                                              account_type, refresh_token_new)
                user = self.env['res.users'].search([])
                user = user.browse(request.uid)
                user.access_token = resp['access_token']
                user.refresh_access_token = resp['refresh_token']
                quickbook_obj.refresh_access_token = resp['refresh_token']
                quickbook_obj.access_token = resp['access_token']
                # Returns the product id
                return response
        if table == 'customer':
            # Same goes for the customer part
            base_url = "https://sandbox-quickbooks.api.intuit.com/v3/company"
            url = base_url + "/" + realm_id + "/query?query=select id from " + table + " where displayname='" + name + "'"
            headers = {
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + access_token
            }
            response = requests.get(url, headers=headers)
            quickbook_obj = QuickBooksODOO(realm_id=realm_id, client_id=client_id,
                                           client_secret=client_secret, refresh_access_token=refresh_token)
            if response.status_code == 200:
                data = response.json()
                if not data['QueryResponse']:
                    url = quickbook_obj.make_customer_url(account_type, realm_id)
                    customer = self.env['res.partner'].search([])
                    for each in customer:
                        if each.name == name:
                            customer_to_sync = each
                            quickbook_data = customer.get_customer_fields(customer_to_sync)
                            resp = quickbook_obj.add_record(url=url, quickbook_data=quickbook_data,
                                                            access_token=access_token,
                                                            refresh_access_token=refresh_token)
                            if resp is False:
                                response = quickbook_obj.refresh_token()
                                access_token = response['access_token']
                                refresh_token_new = response['refresh_token']
                                self.env.user.access_token = access_token
                                self.env.user.refresh_access_token = refresh_token_new
                                resp = quickbook_obj.add_record(url=url, quickbook_data=quickbook_data,
                                                                access_token=access_token,
                                                                refresh_access_token=refresh_token_new)
                                if resp and 'Customer' in resp.keys():
                                    each.write({'quickbooks_id': resp['Customer']['Id']})
                                    self.env.cr.commit()
                            else:
                                if resp and 'Customer' in resp.keys():
                                    each.write({'quickbooks_id': resp['Customer']['Id']})
                                    self.env.cr.commit()

                            return resp['Customer']['Id']
                else:
                    data = response.json()
                    record_id = data['QueryResponse']['Customer'][0]['Id']
                    return record_id
            elif response.status_code == 401 or response.status_code == 400:
                resp = quickbook_obj.refresh_token()
                access_token = resp['access_token']
                refresh_token_new = resp['refresh_token']
                self.env.user.access_token = access_token
                self.env.user.refresh_access_token = refresh_token_new
                response = self.get_record_qb(table, name, realm_id, access_token, client_id, client_secret,
                                              account_type, refresh_token_new)
                user = self.env['res.users'].search([])
                user = user.browse(request.uid)
                user.access_token = resp['access_token']
                user.refresh_access_token = resp['refresh_token']
                quickbook_obj.refresh_access_token = resp['refresh_token']
                quickbook_obj.access_token = resp['access_token']
                return response


class QuickBookCustomerSync(models.Model):
    _inherit = 'res.partner'

    quickbooks_id = fields.Char('quickbooks_id')
    sync_token = fields.Char('sync_token', default = '0')

    def sync_customer(self, is_auto):
        """
        The function which is launched when the user clicks on the
        sync button

        :param is_auto:
        :return:
        """
        customer = self
        current_user = self.env.user
        quickbook_realm_id = current_user.realm_id
        quickbook_client_id = current_user.client_id
        quickbook_client_secret = current_user.client_secret
        quickbook_access_token = current_user.access_token
        quickbook_refresh_token = current_user.refresh_access_token
        quickbook_account_type = current_user.account_type
        quickbook_create_time = current_user.access_token_time
        if quickbook_access_token and quickbook_refresh_token:
            quickbook_obj = QuickBooksODOO(realm_id=quickbook_realm_id, client_id=quickbook_client_id,
                                           client_secret=quickbook_client_secret,
                                           refresh_access_token=quickbook_refresh_token)
            url = quickbook_obj.make_customer_url(quickbook_account_type, quickbook_realm_id)
            # It takes out the active and individual
            # customers or users of the respective companies
            token_obj = self.env['res.partner'].search(
                [("customer", "=", 't'), ("active", "=", 't'), ("parent_id", "=", False)])
            test = self.env['res.users'].search([])
            test = test.browse(self.env.user.id)
            response = quickbook_obj.refresh_token()
            if is_auto:
                objects = self.env['res.partner'].search([])
            else:
                objects = self
            for each in objects:
                # For every customer selected by the user
                quickbook_data = self.get_customer_fields(each)
                if each.quickbooks_id:
                    quickbook_data['Id'] = each.quickbooks_id
                    quickbook_data['SyncToken'] = each.sync_token
                    url = url + "?operation=update&minorversion=4"

                resp = quickbook_obj.add_record(url=url, quickbook_data=quickbook_data,
                                                access_token=quickbook_access_token,
                                                refresh_access_token=quickbook_refresh_token)

                if resp is False:
                    # If access token was expired
                    response = quickbook_obj.refresh_token()
                    access_token = response['access_token']
                    refresh_token_new = response['refresh_token']
                    current_user.access_token = access_token
                    current_user.refresh_access_token = refresh_token_new
                    resp = quickbook_obj.add_record(url=url, quickbook_data=quickbook_data,
                                                    access_token=access_token,
                                                    refresh_access_token=refresh_token_new)
                    if resp and 'Customer' in resp.keys():
                        if each.quickbooks_id:
                            each.write({'sync_token': str(int(each.sync_token) + 1),
                                        'quickbooks_id': resp['Customer']['Id']
                                        })
                        else:
                            each.write({'quickbooks_id': resp['Customer']['Id']})
                        self.env.cr.commit()
                else:
                    if resp and 'Customer' in resp.keys():
                        if each.quickbooks_id:
                            each.write({'sync_token': str(int(each.sync_token) + 1),
                                        'quickbooks_id': resp['Customer']['Id']
                                        })
                        else:
                            each.write({'quickbooks_id': resp['Customer']['Id']})
                        self.env.cr.commit()

            raise Warning(_("Successfully Synced", ))
        else:
            raise ValidationError(_('Access token is missing'))

    def get_customer_fields(self, res):

        """
        It gets all the required fields of the customer
        :param res:
        :return dict:
        """
        dict = {}
        if res.parent_id:
            company_name = res.parent_id.name
            dict["CompanyName"] = str(company_name)
        if res.name:
            display_name = res.name
            dict["DisplayName"] = str(display_name)
        if res.title:
            customer_title = res.title.name
            dict["Title"] = customer_title
        if res.email:
            email_address = res.email
            temp_dict = {}
            temp_dict['Address'] = str(email_address)
            dict['PrimaryEmailAddr'] = temp_dict
        if res.fax:
            fax = res.fax
            temp_dict = {}
            temp_dict['FreeFormNumber'] = fax
            dict['Fax'] = temp_dict
        if res.mobile:
            mobile = res.mobile
            temp_dict = {}
            temp_dict['FreeFormNumber'] = mobile
            dict['Mobile'] = temp_dict
        if res.phone:
            phone = res.phone
            temp_dict = {}
            temp_dict['FreeFormNumber'] = str(phone)
            dict['PrimaryPhone'] = temp_dict
        if res.website:
            website = res.website
            temp_dict = {}
            temp_dict['URI'] = str(website)
            dict['WebAddr'] = temp_dict
        if res.street or res.street2:
            if res.street and res.street2:
                st_address = res.street + ' ' + res.street2
            else:
                if res.street:
                    st_address = res.street
                else:
                    st_address = res.street2
            temp_dict = {}
            temp_dict['Line1'] = str(st_address)
            if 'BillAddr' in dict:
                dict['BillAddr'].update(temp_dict)
            else:
                dict['BillAddr'] = temp_dict
        if res.city:
            city = res.city
            temp_dict = {}
            temp_dict['City'] = city
            if 'BillAddr' in dict:
                dict['BillAddr'].update(temp_dict)
            else:
                dict['BillAddr'] = temp_dict
        if res.country_id:
            country = res.country_id.name
            temp_dict = {}
            temp_dict['Country'] = country
            if 'BillAddr' in dict:
                dict['BillAddr'].update(temp_dict)
            else:
                dict['BillAddr'] = temp_dict
        if res.state_id:
            state = res.state_id.name
            temp_dict = {}
            temp_dict['CountrySubDivisionCode'] = str(state)
            if 'BillAddr' in dict:
                dict['BillAddr'].update(temp_dict)
            else:
                dict['BillAddr'] = temp_dict
        if res.zip:
            postal_code = res.zip
            temp_dict = {}
            temp_dict['PostalCode'] = str(postal_code)
            if 'BillAddr' in dict:
                dict['BillAddr'].update(temp_dict)
            else:
                dict['BillAddr'] = temp_dict
        return dict


class QuickBooksConnector(models.Model):
    _name = 'quickbooks.connector'

    last_sync_date = fields.Datetime('Last Sync Date', readonly=True, default=fields.Datetime.now)
    field_name = fields.Char('quickbooks_connector')
    # history_line = fields.One2many('sync.history', 'sync_id', copy=True)
    customers = fields.Boolean('Import/Update Customers')
    invoices = fields.Boolean('Import/Update Invoices')
    products = fields.Boolean('Import/Update Products')

    def sync_data(self):
        """
        sync data
        :return:
        """
        if self.invoices or self.customers or self.products:
            try:
                self.import_data()
            except Exception as e:
                raise Warning(e)

            raise osv.except_osv(_('Success'),(_('Sync Successfully')))

        else:
            raise Warning(_("No Option Checked.", ))

    def import_data(self):
        """
        :return:
        """
        if self.invoices:
            self.sync_invoices()
        if self.customers:
            self.sync_customers()
        if self.products:
            self.sync_products()

    def sync_products(self):
        """
        Sync Products Between Odoo and QuickBooks
        :return:
        """
        current_user = self.env.user
        quickbook_realm_id = current_user.realm_id
        quickbook_client_id = current_user.client_id
        quickbook_client_secret = current_user.client_secret
        quickbook_access_token = current_user.access_token
        quickbook_refresh_token = current_user.refresh_access_token
        quickbook_account_type = current_user.account_type
        quickbook_create_time = current_user.access_token_time

        if quickbook_access_token and quickbook_refresh_token:
            # Checks if the user had the initial access token and refresh token
            quickbook_obj = QuickBooksODOO(realm_id=quickbook_realm_id, client_id=quickbook_client_id,
                                           client_secret=quickbook_client_secret,
                                           refresh_access_token=quickbook_refresh_token)
            response = quickbook_obj.refresh_token()
            access_token = response['access_token']
            refresh_token_new = response['refresh_token']
            self.env.user.access_token = access_token
            self.env.user.refresh_access_token = refresh_token_new

            url = quickbook_obj.make_products_url(quickbook_account_type, quickbook_realm_id)
            test = self.env['res.users'].search([])
            # test = test.browse(request.uid)
            odoo_products = self.env['product.template'].search([])
            qb_products = self.get_record_qb('products', 'name', quickbook_realm_id, quickbook_access_token,
                                              quickbook_client_id, quickbook_client_secret, quickbook_account_type,
                                              quickbook_refresh_token)
            for qb_product in json.loads(qb_products.content.decode('utf-8'))['QueryResponse']['Item']:
                already_exist = False
                Name = qb_product['Name'] if 'Name' in qb_product.keys() else ""
                UnitPrice = float(qb_product['UnitPrice']) if 'UnitPrice' in qb_product.keys() else ""
                Type = qb_product['Type'].lower() if 'Type' in qb_product.keys() else ""
                if Type == 'inventory':
                    Type = "product"
                if qb_product['Id'] in [each.quickbooks_id for each in odoo_products]:
                    already_exist = True
                    odoo_product = self.env['product.template'].search([("quickbooks_id", "=", qb_product['Id'])])
                    odoo_product = odoo_product[0]

                    odoo_product.write({
                        "name": Name,
                        "list_price": UnitPrice,
                        "type": Type,
                    })
                    if not self.env['product.product'].search([("product_tmpl_id", "=", odoo_product.id)]):
                        self.env['product.product'].create({
                            'product_tmpl_id': odoo_product.id
                        })
                if not already_exist:
                    odoo_product = self.env['product.template'].create({
                        "name": Name,
                        "list_price": UnitPrice,
                        "type": Type,
                        "quickbooks_id": qb_product['Id']
                    })
                    odoo_product = self.env['product.product'].create({
                        'product_tmpl_id': odoo_product.id
                    })
                self.env.cr.commit()

    def sync_customers(self):
        """
        Sync Customer Between Odoo and QuickBooks
        :return:
        """
        current_user = self.env.user
        quickbook_realm_id = current_user.realm_id
        quickbook_client_id = current_user.client_id
        quickbook_client_secret = current_user.client_secret
        quickbook_access_token = current_user.access_token
        quickbook_refresh_token = current_user.refresh_access_token
        quickbook_account_type = current_user.account_type
        #quickbook_create_time = current_user.access_token_time
        if quickbook_access_token and quickbook_refresh_token:
            quickbook_obj = QuickBooksODOO(realm_id=quickbook_realm_id, client_id=quickbook_client_id,
                                           client_secret=quickbook_client_secret,
                                           refresh_access_token=quickbook_refresh_token)
            response = quickbook_obj.refresh_token()
            access_token = response['access_token']
            refresh_token_new = response['refresh_token']
            self.env.user.access_token = access_token
            self.env.user.refresh_access_token = refresh_token_new

            url = quickbook_obj.make_customer_url(quickbook_account_type, quickbook_realm_id)
            # It takes out the active and individual
            # customers or users of the respective companies
            token_obj = self.env['res.partner'].search(
                [("customer", "=", 't'), ("active", "=", 't'), ("parent_id", "=", False)])
            # test = self.env['res.users'].search([])
            # test = test.browse(request.uid)
            odoo_customers = self.env['res.partner'].search([])
            qb_customers = self.get_record_qb('partner', 'name', quickbook_realm_id, quickbook_access_token,
                                              quickbook_client_id, quickbook_client_secret, quickbook_account_type,
                                              quickbook_refresh_token)
            for qb_customer in json.loads(qb_customers.content.decode('utf-8'))['QueryResponse']['Customer']:
                already_exist = False
                displayname = qb_customer['DisplayName'] if 'DisplayName' in qb_customer.keys() else ""
                title = qb_customer['Title'] if 'Title' in qb_customer.keys() else ""
                CompanyName = qb_customer['CompanyName'] if 'CompanyName' in qb_customer.keys() else ""
                PrimaryEmailAddr = qb_customer[
                    'PrimaryEmailAddr']['Address'] if 'PrimaryEmailAddr' in qb_customer.keys() else ""
                Fax = qb_customer['Fax'] if 'Fax' in qb_customer.keys() else ""
                if Fax:
                    Fax = Fax['FreeFormNumber']
                Mobile = qb_customer['Mobile'] if 'Mobile' in qb_customer.keys() else ""
                if Mobile:
                    Mobile = Mobile['FreeFormNumber']
                PrimaryPhone = qb_customer['PrimaryPhone']['FreeFormNumber'] if 'PrimaryPhone' in qb_customer.keys() else ""
                WebAddr = qb_customer['WebAddr']['URI'] if 'WebAddr' in qb_customer.keys() else ""

                if qb_customer['Id'] in [each.quickbooks_id for each in odoo_customers]:
                    already_exist = True
                    odoo_customer = self.env['res.partner'].search([("quickbooks_id", "=", qb_customer['Id'])])
                    odoo_customer = odoo_customer[0]

                    odoo_customer = odoo_customer.write({
                        "name": displayname,
                        "email": PrimaryEmailAddr,
                        "fax": Fax,
                        "mobile": Mobile,
                        "phone": PrimaryPhone,
                        "website": WebAddr,
                        "title.name": title,
                        "parent_id.name": CompanyName,

                    })
                if not already_exist:
                    odoo_customer = self.env['res.partner'].create({
                        "name": displayname,
                        "email": PrimaryEmailAddr,
                        "fax": Fax,
                        "mobile": Mobile,
                        "phone": PrimaryPhone,
                        "website": WebAddr,
                        "quickbooks_id": qb_customer['Id']
                    })
                self.env.cr.commit()

    def sync_invoices(self):
        """

        The function which is launched when the user clicks on the sync button
        :return:
        """
        current_user = self.env.user
        quickbook_realm_id = current_user.realm_id
        quickbook_client_id = current_user.client_id
        quickbook_client_secret = current_user.client_secret
        quickbook_access_token = current_user.access_token
        quickbook_refresh_token = current_user.refresh_access_token
        quickbook_account_type = current_user.account_type
        quickbook_create_time = current_user.access_token_time

        if not quickbook_access_token:
            raise ValidationError(_('Access token is missing'))

        quickbook_obj = QuickBooksODOO(realm_id=quickbook_realm_id, client_id=quickbook_client_id,
                                       client_secret=quickbook_client_secret,
                                       refresh_access_token=quickbook_refresh_token)
        response = quickbook_obj.refresh_token()
        access_token = response['access_token']
        refresh_token_new = response['refresh_token']
        self.env.user.access_token = access_token
        self.env.user.refresh_access_token = refresh_token_new
        url = quickbook_obj.make_invoice_url(quickbook_account_type, quickbook_realm_id)
        test = self.env['res.users'].search([])
        # test = test.browse(request.uid)
        # test = test.test_connection()
        odoo_invoices = self.env['account.invoice'].search([])
        qb_invoices = self.get_record_qb('invoice', 'name', quickbook_realm_id, quickbook_access_token,
                                         quickbook_client_id, quickbook_client_secret, quickbook_account_type,
                                         quickbook_refresh_token)
        for qb_invoice in json.loads(qb_invoices.content.decode('utf-8'))['QueryResponse']['Invoice']:
            already_exist = False

            if qb_invoice['Id'] in [each.quickbooks_id for each in odoo_invoices]:
                odoo_invoice = self.env['account.invoice'].search([("quickbooks_id", "=", qb_invoice['Id'])])
                odoo_invoice = odoo_invoice[0]
                if qb_invoice['Balance'] == 0:
                    odoo_invoice.state = 'open'
                if odoo_invoice.state != 'draft':
                    continue
                for line_old in odoo_invoice.invoice_line_ids:
                    line_old.unlink()
                self.env.cr.commit()
                for line in qb_invoice['Line']:
                    if 'SalesItemLineDetail' not in line.keys():
                        continue
                    qb_name = line['SalesItemLineDetail']['ItemRef']['name']
                    odoo_product = self.env['product.template'].search([("name", "=", qb_name)])
                    if odoo_product:
                        odoo_product = self.env['product.product'].search(
                            [('product_tmpl_id', '=', odoo_product[0].id)])
                    else:
                        odoo_product_template = self.env['product.template'].create({
                            'name': line['SalesItemLineDetail']['ItemRef']['name'],
                            # 'shopify_product_id': product.attributes['id'],
                            'price': float(line['SalesItemLineDetail']['UnitPrice'])
                        })
                        odoo_product = self.env['product.product'].create({
                            'product_tmpl_id': odoo_product_template.id
                        })
                    if "Qty" in line['SalesItemLineDetail'].keys() and "UnitPrice" in line[
                        'SalesItemLineDetail'].keys():
                        self.env['account.invoice.line'].create({
                            'product_id': odoo_product[0].id,
                            'invoice_id': odoo_invoice.id,
                            'account_id': odoo_invoice.account_id.id,
                            'product_oum_qty': line['SalesItemLineDetail']["Qty"],
                            'qty_invoiced': line['SalesItemLineDetail']['Qty'],
                            'name': line['SalesItemLineDetail']['ItemRef']['name'],
                            #'product_uom': self.env.ref('product.product_uom_unit').id,
                            'price_unit': float(line['SalesItemLineDetail']['UnitPrice'])
                        })

                already_exist = True

            if not already_exist:

                qb_customer = self.get_record_qb('customers', qb_invoice['CustomerRef']['value'], quickbook_realm_id,
                                                 quickbook_access_token, quickbook_client_id,
                                                 quickbook_client_secret, quickbook_account_type,
                                                 quickbook_refresh_token)
                qb_customer = json.loads(qb_customer.content.decode('utf-8'))
                odoo_customer = self.env['res.partner'].search([("quickbooks_id", "=", qb_customer['Customer']['Id'])])
                if not odoo_customer:
                    odoo_customer = self.env['res.partner'].create({
                        'name': qb_customer['Customer']['DisplayName'],
                        'quickbooks_id': qb_customer['Customer']['Id']
                    })
                state = ""
                if qb_invoice['Balance'] == 0:
                    state = 'open'
                else:
                    state = 'draft'

                odoo_invoice_new = self.env['account.invoice'].create({
                    'quickbooks_id': qb_invoice['Id'],
                    'partner_id': odoo_customer.id,
                    'date': qb_invoice["MetaData"]["CreateTime"],
                    'amount_tax': float(qb_invoice['TxnTaxDetail']['TotalTax']),
                    'amount_total': float(qb_invoice['TotalAmt']),
                    'state': state,
                    'type': 'out_invoice'
                })
                for line in qb_invoice['Line']:
                    if 'SalesItemLineDetail' in line.keys():
                        odoo_product_template = self.env['product.template']. \
                            search([('quickbooks_id', '=', line['SalesItemLineDetail']['ItemRef']['value'])])

                        if not odoo_product_template:
                            qb_product = self.get_record_qb('items', line['SalesItemLineDetail']['ItemRef']['value'],
                                                            quickbook_realm_id, quickbook_access_token,
                                                            quickbook_client_id,
                                                            quickbook_client_secret, quickbook_account_type,
                                                            quickbook_refresh_token)
                            qb_product = json.loads(qb_product.content.decode('utf-8'))

                            odoo_product_template = self.env['product.template'].create({
                                'name': qb_product['Item']["Name"],
                                'quickbooks_id': qb_product['Item']["Id"],
                                'price': float(qb_product['Item']["UnitPrice"])
                            })
                            odoo_product = self.env['product.product'].create({
                                'product_tmpl_id': odoo_product_template.id
                            })
                        else:
                            odoo_product = self.env['product.product'].search([('product_tmpl_id',
                                                                                '=', odoo_product_template.id)])
                            if not odoo_product:
                                odoo_product = self.env['product.product'].create({
                                    'product_tmpl_id': odoo_product_template.id
                                })
                        if "Qty" in line['SalesItemLineDetail'].keys() and "UnitPrice" in line[
                            'SalesItemLineDetail'].keys():
                            self.env['account.invoice.line'].create({
                                'product_id': odoo_product[0].id,
                                'invoice_id': odoo_invoice_new.id,
                                'account_id': odoo_invoice_new.account_id.id,
                                'product_oum_qty': line['SalesItemLineDetail']['Qty'],
                                'qty_invoiced': line['SalesItemLineDetail']['Qty'],
                                'name': line['SalesItemLineDetail']['ItemRef']['name'],
                                #'product_uom': self.env.ref('product.product_uom_unit').id,
                                'price_unit': float(line['SalesItemLineDetail']['UnitPrice'])
                            })

            self.env.cr.commit()

    def get_record_qb(self, table, name, realm_id, access_token, client_id, client_secret, account_type, refresh_token):

        # The function which gets the records from quickbooks to get
        # id of product and customer
        if table == 'invoice':
            base_url = "https://sandbox-quickbooks.api.intuit.com/v3/company"

            url = base_url + "/" + realm_id + "/query?query=select * from " + table
            headers = {
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + access_token
            }
            response = requests.get(url, headers=headers)
            return response
        if table == 'partner':
            base_url = "https://sandbox-quickbooks.api.intuit.com/v3/company"

            url = base_url + "/" + realm_id + "/query?query=select id, displayname, title, CompanyName, primaryemailaddr, fax, mobile, primaryphone, webaddr from " + "customer"
            headers = {
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + access_token
            }
            response = requests.get(url, headers=headers)
            return response
        if table == 'products':
            base_url = "https://sandbox-quickbooks.api.intuit.com/v3/company"

            url = base_url + "/" + realm_id + "/query?query=select id, Name, UnitPrice, Type from " + "item"
            headers = {
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + access_token
            }
            response = requests.get(url, headers=headers)
            return response

        if table == 'item':
            print( "Table:" + table)
            base_url = "https://sandbox-quickbooks.api.intuit.com/v3/company"
            url = base_url + "/" + realm_id + "/query?query=select id from " + table + " where name='" + name + "'"
            headers = {
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + access_token
            }
            response = requests.get(url, headers=headers)
            quickbook_obj = QuickBooksODOO(realm_id=realm_id, client_id=client_id,
                                           client_secret=client_secret, refresh_access_token=refresh_token)

            if response.status_code == 200:
                data = response.json()
                if not data['QueryResponse']:
                    # If the product is not available in quickbooks
                    # then create the product first
                    url = quickbook_obj.make_products_url(account_type, realm_id)
                    product = self.env['product.template'].search([])
                    for each in product:
                        # For every product selected by the user
                        if each.display_name == name or each.name == name:
                            product_to_sync = each
                            quickbook_data = product.get_product_fields(product_to_sync)
                            resp = quickbook_obj.add_record(url=url, quickbook_data=quickbook_data,
                                                            access_token=access_token,
                                                            refresh_access_token=refresh_token)
                            if not resp['Item']['Id']:
                                # If the Product to Sync didnt had the required values
                                raise ValidationError(_('Error in Creating Product'))
                            if resp is False:
                                # If the access token was expired
                                response = quickbook_obj.refresh_token()
                                access_token = response['access_token']
                                refresh_token_new = response['refresh_token']
                                self.env.user.access_token = access_token
                                self.env.user.refresh_access_token = refresh_token_new
                                resp = quickbook_obj.add_record(url=url, quickbook_data=quickbook_data,
                                                                access_token=access_token,
                                                                refresh_access_token=refresh_token_new)
                            # Returns the Product Id in Quickbooks
                            return resp['Item']['Id']
                else:
                    # If the product was found this way it extracts the id
                    temp = data['QueryResponse']['Item']
                    if isinstance(temp, list):
                        product_id = temp[0]['Id']
                        # Returns the product id
                        return product_id
            elif response.status_code == 401 or response.status_code == 400:
                # If the access token or refresh token was expired
                # Refresh token first then get product id
                resp = quickbook_obj.refresh_token()
                access_token_new = resp['access_token']
                refresh_access_token_new = resp['refresh_token']
                response = self.get_record_qb(table, name, realm_id, access_token_new, client_id, client_secret,
                                              account_type, refresh_access_token_new)
                user = self.env['res.users'].search([])
                user = user.browse(request.uid)
                user.access_token = resp['access_token']
                user.refresh_access_token = resp['refresh_token']
                quickbook_obj.refresh_access_token = resp['refresh_token']
                quickbook_obj.access_token = resp['access_token']
                # Returns the product id
                return response
        if table == 'items':
            base_url = "https://sandbox-quickbooks.api.intuit.com/v3/company"

            url = base_url + "/" + realm_id + "/" + table[:-1] + "/" + name
            headers = {
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + access_token
            }
            response = requests.get(url, headers=headers)
            return response
        if table == 'customer':
            # Same goes for the customer part
            base_url = "https://sandbox-quickbooks.api.intuit.com/v3/company"
            url = base_url + "/" + realm_id + "/query?query=select id from " + table + " where displayname='" + name + "'"
            headers = {
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + access_token
            }
            response = requests.get(url, headers=headers)
            quickbook_obj = QuickBooksODOO(realm_id=realm_id, client_id=client_id,
                                           client_secret=client_secret, refresh_access_token=refresh_token)
            if response.status_code == 200:
                data = response.json()
                if not data['QueryResponse']:
                    url = quickbook_obj.make_customer_url(account_type, realm_id)
                    customer = self.env['res.partner'].search([])
                    for each in customer:
                        if each.name == name:
                            customer_to_sync = each
                            quickbook_data = customer.get_customer_fields(customer_to_sync)
                            resp = quickbook_obj.add_record(url=url, quickbook_data=quickbook_data,
                                                            access_token=access_token,
                                                            refresh_access_token=refresh_token)
                            if resp is False:
                                response = quickbook_obj.refresh_token()
                                access_token = response['access_token']
                                refresh_token_new = response['refresh_token']
                                self.env.user.access_token = access_token
                                self.env.user.refresh_access_token = refresh_token_new
                                resp = quickbook_obj.add_record(url=url, quickbook_data=quickbook_data,
                                                                access_token=access_token,
                                                                refresh_access_token=refresh_token_new)

                            return resp['Customer']['Id']
                else:
                    data = response.json()
                    record_id = data['QueryResponse']['Customer'][0]['Id']
                    return record_id
            elif response.status_code == 401 or response.status_code == 400:
                resp = quickbook_obj.refresh_token()
                access_token_new = resp['access_token']
                refresh_access_token_new = resp['refresh_token']
                response = self.get_record_qb(table, name, realm_id, access_token_new, client_id, client_secret,
                                              account_type, refresh_access_token_new)
                user = self.env['res.users'].search([])
                user = user.browse(request.uid)
                user.access_token = resp['access_token']
                user.refresh_access_token = resp['refresh_token']
                quickbook_obj.refresh_access_token = resp['refresh_token']
                quickbook_obj.access_token = resp['access_token']
                return response
        if table == 'customers':
            # Same goes for the customer part
            base_url = "https://sandbox-quickbooks.api.intuit.com/v3/company"
            url = base_url + "/" + realm_id + "/" + table[:-1] + "/" + name
            headers = {
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + access_token
            }
            response = requests.get(url, headers=headers)
            return response


class QuickBooksAutoConnector(models.Model):
    _name = 'quickbooks.autoconnector'


    field_name = fields.Char('quickbooks_autoconnector')
    # history_line = fields.One2many('sync.history', 'sync_id', copy=True)
    customers = fields.Boolean('Import/Update Customers')
    invoices = fields.Boolean('Import/Update Invoices')
    products = fields.Boolean('Import/Update Products')
    interval_number_customer = fields.Integer(string="Sync Interval Number")
    interval_unit_customer = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('work_days', 'Work Days'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Interval Unit')
    interval_number_invoice = fields.Integer(string="Sync Interval Number")
    interval_unit_invoice = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('work_days', 'Work Days'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Interval Unit')
    interval_number_product = fields.Integer(string="Sync Interval Number")
    interval_unit_product = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('work_days', 'Work Days'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Interval Unit')

    def sync_data(self):
        """

        :return:
        """
        done = False
        while not done:
            try:
                scheduler = self.env['ir.cron'].search([('name', '=', 'Import Customers Scheduler')])
                if not scheduler:
                    scheduler = self.env['ir.cron'].search([('name', '=', 'Import Customers Scheduler'),('active','=',False)])
                scheduler.active = self.customers
                scheduler.interval_number = self.interval_number_customer
                scheduler.interval_type = self.interval_unit_customer

                scheduler = self.env['ir.cron'].search([('name', '=', 'Import Products Scheduler')])
                if not scheduler:
                    scheduler = self.env['ir.cron'].search([('name', '=', 'Import Products Scheduler'),('active','=',False)])
                scheduler.active = self.products
                scheduler.interval_number = self.interval_number_product
                scheduler.interval_type = self.interval_unit_product

                scheduler = self.env['ir.cron'].search([('name', '=', 'Import Invoices Scheduler')])
                if not scheduler:
                    scheduler = self.env['ir.cron'].search([('name', '=', 'Import Invoices Scheduler'),('active','=',False)])
                scheduler.active = self.invoices
                scheduler.interval_number = self.interval_number_invoice
                scheduler.interval_type = self.interval_unit_invoice

                self.env.cr.commit()
                done = True
            except Exception as e:
                print (e)


class QuickBooksAutoExportConnector(models.Model):
    _name = 'quickbooks.autoexportconnector'


    field_name = fields.Char('quickbooks_autoexportconnector')
    # history_line = fields.One2many('sync.history', 'sync_id', copy=True)
    customers = fields.Boolean('Export/Update Customers')
    invoices = fields.Boolean('Export/Update Invoices')
    products = fields.Boolean('Export/Update Products')
    interval_number_customer = fields.Integer(string="Sync Interval Number")
    interval_unit_customer = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('work_days', 'Work Days'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Interval Unit')
    interval_number_invoice = fields.Integer(string="Sync Interval Number")
    interval_unit_invoice = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('work_days', 'Work Days'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Interval Unit')
    interval_number_product = fields.Integer(string="Sync Interval Number")
    interval_unit_product = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('work_days', 'Work Days'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Interval Unit')

    def sync_data(self):
        """

        :return:
        """
        done = False
        while not done:
            try:
                scheduler = self.env['ir.cron'].search([('name', '=', 'Export Customers Scheduler')])
                if not scheduler:
                    scheduler = self.env['ir.cron'].search([('name', '=', 'Export Customers Scheduler'),('active','=',False)])
                scheduler.active = self.customers
                scheduler.interval_number = self.interval_number_customer
                scheduler.interval_type = self.interval_unit_customer

                scheduler = self.env['ir.cron'].search([('name', '=', 'Export Products Scheduler')])
                if not scheduler:
                    scheduler = self.env['ir.cron'].search([('name', '=', 'Export Products Scheduler'),('active','=',False)])
                scheduler.active = self.products
                scheduler.interval_number = self.interval_number_product
                scheduler.interval_type = self.interval_unit_product

                scheduler = self.env['ir.cron'].search([('name', '=', 'Export Invoices Scheduler')])
                if not scheduler:
                    scheduler = self.env['ir.cron'].search([('name', '=', 'Export Invoices Scheduler'),('active','=',False)])
                scheduler.active = self.invoices
                scheduler.interval_number = self.interval_number_invoice
                scheduler.interval_type = self.interval_unit_invoice

                self.env.cr.commit()
                done = True
            except Exception as e:
                print (e)

