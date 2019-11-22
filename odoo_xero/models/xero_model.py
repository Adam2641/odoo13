# -*- coding: utf-8 -*-
from odoo import models, fields, api
# from rs import rs
# import lxml.etree
# import requests
# import urllib2
# import urllib

# import httplib

# import right_signature
from odoo.osv import osv
from odoo.exceptions import ValidationError,AccessError, UserError
import time
import json
from datetime import datetime, timedelta
from ast import literal_eval


# from odoo.exceptions import UserError
# import string
# import random
# import logging
from xero import Xero
from xero.auth import PublicCredentials
from xero import Xero
import os
import base64
import webbrowser

cre = None


class XeroSettingModel(models.Model):
    """
    This class adds coustomer field in res.users
    """

    _inherit = 'res.users'
    #  Add custom fields
    credentials = fields.Char(string = 'credentials')


class ProductSync(models.Model):
    """
    This classs import the product from Xero to Odoo Product.Template Model

    """
    _inherit = 'product.template'
    xero_product_id = fields.Char( "Xero Product ID")
    default_code = fields.Char(string = "Internal Reference", unique = True)

    def xero_authentication(self):

        user = self.env.user
        if user.credentials:
            save_state = json.loads(user.credentials)
        else:
            raise osv.except_osv("Failure!", " Your Authentication code has been expired Please generate a new one !")

        if str(datetime.now()) > save_state['oauth_expires_at']:
            raise osv.except_osv("Failure!", " Your Authentication code has been expired Please generate a new one !")
        else:
            credentials = PublicCredentials(**save_state)
            # credentials.verify(self.env.user.verify_code)
            return credentials

    def sync_product_to_zero(self):
        """
        This function uploads products from Odoo to Xero
        :return:
        """

        products = self
        if len(products) == 0:
            products = self.search([])
        credentials = self.xero_authentication()
        xero = Xero(credentials)
        connection = True
        try:
            all_items = xero.items.all()
            connection = True
        except:
            all_items = []
            connection = False
        if (connection != True):
            raise ValidationError('Authentication Failed! Please verify your credentials.')
        all_accounts_connection = True
        try:
            all_accounts = xero.accounts.all()
            all_accounts_connection = True
        except:
            all_accounts = []
            all_accounts_connection = False
        if (all_accounts_connection != True):
            raise ValidationError('Authentication Failed! Please verify your credentials.')
        odoo_all_account_types = {'Current Assets': 'CURRENT', 'Non-current Assets': 'NONCURRENT', 'Fixed Assets': 'FIXED',
         'Current Liabilities': 'CURRLIAB', 'Non-current Liabilities': 'TERMLIAB',
         'Equity': 'EQUITY', 'Other Income': 'OTHERINCOME', 'Depreciation': 'DEPRECIATN',
         'Cost of Revenue': 'REVENUE'}
        all_get_accounts_code = []
        for each in all_accounts:
            if 'Code' in each:
                xero_account_code = each['Code']
                all_get_accounts_code.append(str(xero_account_code))
        all_get_code = []
        for each in all_items:
            if 'Code' in each:
                code = each['Code']
                all_get_code.append(str(code))
        check_product_codes = []
        check_account_codes = []
        all_accounts_array = []
        all_items_array = []
        for each_product in products:
            already_exist = False
            for xero_product in all_items:
                time.sleep(.5)
                if str(each_product.xero_product_id) == str(xero_product['ItemID']):
                    self.update_product(xero, xero_product , each_product,)
                    already_exist = True
                    break

            if already_exist:
                continue
            internal_reference = each_product.default_code
            if not internal_reference:
                internal_reference = "PR-COD" + str(each_product.id)
            if (str(internal_reference) not in all_get_code) and (str(internal_reference) not in check_product_codes):
                name = each_product.name
                description = each_product.description
                description_purchase = each_product.description_purchase
                seller_ids = each_product.seller_ids
                unit_price_to_purchase_a_product = 0
                if len(seller_ids) != 0:
                    seller_id = seller_ids[0]
                    unit_price_to_purchase_a_product = seller_id.price
                list_price = each_product.list_price
                income_account = each_product.property_account_income_id
                income_account_code = None
                if income_account:
                    income_account_code = income_account.code
                    income_account_name = income_account.name
                    income_account_type_name = income_account.user_type_id.name
                    income_account_code = str(income_account_code)
                    if (income_account_code not in all_get_accounts_code) and (income_account_code not in check_account_codes):
                        try:
                            accounttype = odoo_all_account_types[income_account_type_name]
                        except:
                            accounttype = None

                        if accounttype == None:
                            income_account_type_name = 'OTHERINCOME'
                        else:
                            income_account_type_name = accounttype
                        all_accounts_array.append({'Code': str(income_account_code), 'Name': str(income_account_name), 'Type': str(income_account_type_name)})
                        check_account_codes.append(str(income_account_code))
                expense_account = each_product.property_account_expense_id
                expense_account_code = None
                if expense_account:
                    expense_account_code = expense_account.code
                    expense_account_name = expense_account.name
                    expense_account_type_name = expense_account.user_type_id.name
                    expense_account_code = str(expense_account_code)
                    if (expense_account_code not in all_get_accounts_code) and (expense_account_code not in check_account_codes):
                        try:
                            expense_accounttype = odoo_all_account_types[expense_account_type_name]
                        except:
                            expense_accounttype = None
                        if expense_accounttype == None:
                            expense_account_type_name = 'EXPENSE'
                        else:
                            expense_account_type_name = expense_accounttype
                        all_accounts_array.append({'Code': str(expense_account_code), 'Name': str(expense_account_name),
                                                   'Type': str(expense_account_type_name)})
                        check_account_codes.append(str(expense_account_code))
                mydict = {}
                purchase_dict = {}
                sale_dict = {}
                error_account_codes = []
                if len(all_accounts_array) != 0:
                    for each_accounts in all_accounts_array:
                        try:
                            xero.accounts.put(each_accounts)
                        except:
                            error_code = each_accounts['Code']
                            error_account_codes.append(error_code)
                if internal_reference:
                    mydict['Code'] = str(internal_reference)
                    if name:
                        mydict['Name'] = str(name)
                    if description:
                        mydict['Description'] = str(description)
                    if description_purchase:
                        mydict['PurchaseDescription'] = str(description_purchase)
                    if unit_price_to_purchase_a_product != 0:
                        purchase_dict['UnitPrice'] = str(unit_price_to_purchase_a_product)
                    if expense_account_code != None:
                        purchase_dict['AccountCode'] = str(expense_account_code)
                    if purchase_dict:
                        mydict['PurchaseDetails'] = purchase_dict
                    if list_price:
                        sale_dict['UnitPrice'] = str(list_price)
                    if income_account_code != None:
                        sale_dict['AccountCode'] = str(income_account_code)
                    if sale_dict:
                        mydict['SalesDetails'] = sale_dict
                    try:
                        xero_product = xero.items.put(mydict)
                        each_product.write({'xero_product_id': xero_product[0]['ItemID'], 'default_code': internal_reference})
                    except Exception as e:
                        raise ValidationError(str(e))
                    mydict = {}
                    purchase_dict = {}
                    sale_dict = {}


    def update_product(self, xero, new_product, product):

        """
        :param xero: xero object
        :param new_product: xero product which will be updated
        :param product: odoo product
        :return:
        """

        internal_reference = product.default_code
        if not internal_reference:
            internal_reference = "PR-COD" + str(product.id)

        name = product.name
        description = product.description
        description_purchase = product.description_purchase
        seller_ids = product.seller_ids
        unit_price_to_purchase_a_product = 0
        if len(seller_ids) != 0:
            seller_id = seller_ids[0]
            unit_price_to_purchase_a_product = seller_id.price
        list_price = product.list_price
        xero_product = xero.items.get(new_product["ItemID"])
        purchase_dict = {}
        sale_dict = {}
        if internal_reference:
            xero_product[0]['Code'] = str(internal_reference)
            if name:
                xero_product[0]['Name'] = str(name)
            if description:
                xero_product[0]['Description'] = str(description)
            if description_purchase:
                xero_product[0]['PurchaseDescription'] = str(description_purchase)
            if unit_price_to_purchase_a_product != 0:
                purchase_dict['UnitPrice'] = str(unit_price_to_purchase_a_product)
            if purchase_dict:
                xero_product[0]['PurchaseDetails'] = purchase_dict
            if list_price:
                sale_dict['UnitPrice'] = str(list_price)
            if sale_dict:
                xero_product[0]['SalesDetails'] = sale_dict


            # Below lines are for lower the values because xero support false and true
            xero_product[0]['IsTrackedAsInventory'] = str(xero_product[0]['IsTrackedAsInventory']).lower()
            xero_product[0]['IsSold'] = str(xero_product[0]['IsSold']).lower()
            xero_product[0]['IsPurchased'] = str(xero_product[0]['IsPurchased']).lower()
            purchase_dict = {}
            sale_dict = {}
        error_items_codes = []
        try:
            xero.items.save(xero_product)
        except:
            error_itm_code = xero_product[0]['Code']
            error_items_codes.append(error_itm_code)
        if len(error_items_codes) != 0:
            raise ValidationError('Some Products are not uploaded due to some api issues, these Internal references are, \n' + str(error_items_codes))


class CustomerSync(models.Model):

    _inherit = 'res.partner'

    xero_contact_id = fields.Char('Xero ContactID')


    def upload_contacts_xero(self):
        """
        Sync contacts from odoo to xero
        :return:
        """
        odoo_contacts = self
        if len(odoo_contacts) == 0:
            odoo_contacts = self.search([])
        credentials = self.env['product.template'].xero_authentication()
        xero = Xero(credentials)
        connection = True
        try:
            xero_contacts_name=[]
            xero_all_contacts = xero.contacts.all()
            xero_contacts_name.append([xero_contact['Name'] for xero_contact in xero_all_contacts])
            connection = True
            all_xero_contacts = []
            all_xero_name_cotact_id_dicts = {}
            for each_contact in xero_all_contacts:
                contact_name = each_contact["Name"]
                contact_name = str(contact_name).lower()
                all_xero_contacts.append(contact_name)
        except:
            xero_all_contacts = []
            connection = False
        if (connection != True):
            raise ValidationError('Authentication Failed! Please verify your credentials.')

        all_contacts_list = []
        for each_contact in odoo_contacts:
            already_exist = False
            for xero_contact in xero_all_contacts:
                if str(each_contact.xero_contact_id) == str(xero_contact['ContactID']):
                    self.update_xero_contact(xero, xero_contact, each_contact)
                    already_exist = True
                    break

            if already_exist:
                continue

            # if str(each_contact.xero_contact_id) == str
            mydict = {}
            address_dict = {}
            phones_array = []

            customer_name = each_contact.display_name
            if customer_name.lower() in all_xero_contacts:
                continue
            customer_street = each_contact.street
            customer_street2 = each_contact.street2
            customer_city = each_contact.city
            customer_state = each_contact.state_id.name
            customer_zip = each_contact.zip
            customer_country = each_contact.country_id.name
            customer_phone = each_contact.phone
            customer_mobile = each_contact.mobile
            customer_email = each_contact.email


            mydict['Name'] = customer_name
            mydict['FirstName'] = customer_name
            if customer_email:
                mydict['EmailAddress'] = str(customer_email)
            if customer_street:
                street = str(customer_street)
                if customer_street2:
                    street = street + ' ' + str(customer_street2)
                address_dict['AttentionTo'] = str(street)
            if customer_city:
                address_dict['City'] = str(customer_city)
            if customer_state:
                address_dict['Region'] = str(customer_state)
            if customer_zip:
                address_dict['PostalCode'] = str(customer_zip)
            if customer_country:
                address_dict['Country'] = str(customer_country)
            if address_dict:
                address_dict['AddressType'] = 'STREET'
                mydict['Addresses'] = [address_dict]
            phone_default_dict = {}
            if customer_phone:
                phone_default_dict['PhoneType'] = 'DEFAULT'
                phone_default_dict['PhoneNumber'] = str(customer_phone)
                phones_array.append(phone_default_dict)
            phone_fax_dict = {}
            phone_mobile_dict = {}
            if customer_mobile:
                phone_mobile_dict['PhoneType'] = 'MOBILE'
                phone_mobile_dict['PhoneNumber'] = str(customer_mobile)
                phones_array.append(phone_mobile_dict)
            if len(phones_array) != 0:
                mydict['Phones'] = phones_array

            if each_contact.vat:
                mydict['TaxNumber'] = each_contact.vat

            try:
                xero_contact_response = xero.contacts.put(mydict)
                each_contact.write({'xero_contact_id': xero_contact_response[0]['ContactID']})

            except Exception as e:
                raise ValidationError(str(e))



    def update_xero_contact(self, xero ,xero_contact, each_contact):


        mydict = xero.contacts.get(xero_contact["ContactID"])[0]
        address_dict = {}
        phones_array = []

        customer_name = each_contact.display_name
        customer_street = each_contact.street
        customer_street2 = each_contact.street2
        customer_city = each_contact.city
        customer_state = each_contact.state_id.name
        customer_zip = each_contact.zip
        customer_country = each_contact.country_id.name
        customer_phone = each_contact.phone
        customer_mobile = each_contact.mobile
        customer_email = each_contact.email


        mydict['Name'] = customer_name
        mydict['FirstName'] = customer_name
        if customer_email:
            mydict['EmailAddress'] = str(customer_email)
        if customer_street:
            street = str(customer_street)
            if customer_street2:
                street = street + ' ' + str(customer_street2)
            address_dict['AttentionTo'] = str(street)
        if customer_city:
            address_dict['City'] = str(customer_city)
        if customer_state:
            address_dict['Region'] = str(customer_state)
        if customer_zip:
            address_dict['PostalCode'] = str(customer_zip)
        if customer_country:
            address_dict['Country'] = str(customer_country)
        if address_dict:
            address_dict['AddressType'] = 'STREET'
            mydict['Addresses'] = [address_dict]
        phone_default_dict = {}
        if customer_phone:
            phone_default_dict['PhoneType'] = 'DEFAULT'
            phone_default_dict['PhoneNumber'] = str(customer_phone)
            phones_array.append(phone_default_dict)
        phone_fax_dict = {}
        phone_mobile_dict = {}
        if customer_mobile:
            phone_mobile_dict['PhoneType'] = 'MOBILE'
            phone_mobile_dict['PhoneNumber'] = str(customer_mobile)
            phones_array.append(phone_mobile_dict)
        if len(phones_array) != 0:
            mydict['Phones'] = phones_array
        if each_contact.vat:
            mydict['TaxNumber'] = each_contact.vat
        try:
            xero.contacts.save(mydict)
        except Exception as e:
            raise ValidationError(str(e))


class AccountChartSync(models.Model):
    _inherit = 'account.account'
    xero_account_chart_id = fields.Char('Xero Chart of Account ID')


class InvoicesSync(models.Model):
    _inherit = 'account.move'

    xero_invoice_id = fields.Char("Xero Invoice ID")
    check_field = fields.Boolean("Check Field", default=False)
    number = fields.Char(readonly=False)
    amount_tax = fields.Monetary(readonly= False)
    amount_total = fields.Monetary(readonly = False)
    residual = fields.Monetary(readonly = False)

    def make_contact_to_upload(self, invoice):
        mydict = {}
        address_dict = {}
        phones_array = []
        partner_id = invoice.partner_id
        customer_name = partner_id.display_name
        customer_street = partner_id.street
        customer_street2 = partner_id.street2
        customer_city = partner_id.city
        customer_state = partner_id.state_id.name
        customer_zip = partner_id.zip
        customer_country = partner_id.country_id.name
        customer_phone = partner_id.phone
        customer_mobile = partner_id.mobile
        customer_email = partner_id.email
        mydict['Name'] = customer_name
        mydict['FirstName'] = customer_name
        if customer_email:
            mydict['EmailAddress'] = str(customer_email)
        if customer_street:
            street = str(customer_street)
            if customer_street2:
                street = street + ' ' + str(customer_street2)
            address_dict['AttentionTo'] = str(street)
        if customer_city:
            address_dict['City'] = str(customer_city)
        if customer_state:
            address_dict['Region'] = str(customer_state)
        if customer_zip:
            address_dict['PostalCode'] = str(customer_zip)
        if customer_country:
            address_dict['Country'] = str(customer_country)
        if address_dict:
            address_dict['AddressType'] = 'STREET'
            mydict['Addresses'] = [address_dict]
        phone_default_dict = {}
        if customer_phone:
            phone_default_dict['PhoneType'] = 'DEFAULT'
            phone_default_dict['PhoneNumber'] = str(customer_phone)
            phones_array.append(phone_default_dict)
        phone_fax_dict = {}
        phone_mobile_dict = {}
        if customer_mobile:
            phone_mobile_dict['PhoneType'] = 'MOBILE'
            phone_mobile_dict['PhoneNumber'] = str(customer_mobile)
            phones_array.append(phone_mobile_dict)
        if len(phones_array) != 0:
            mydict['Phones'] = phones_array
        return mydict

    def sync_invoices_to_xero(self):
        invoices = self
        if len(invoices) == 0:
            invoices = self.search([])
        credentials = self.env['product.template'].xero_authentication()
        xero = Xero(credentials)
        connection = True
        try:
            all_invoices = xero.invoices.all()
            connection = True
        except:
            all_invoices = []
            connection = False
        if connection != True:
            raise ValidationError('Authentication Failed! Please verify your credentials.')
        connection_contact = True
        try:
            all_contact = xero.contacts.all()
            connection_contact = True
        except:
            all_contact = []
            connection_contact = False
        if (connection_contact != True):
            raise ValidationError('Authentication Failed! Please verify your credentials.')
        all_xero_contacts = []
        all_xero_name_cotact_id_dicts = {}
        for each_contact in all_contact:
            contact_name = each_contact["Name"]
            contact_name = str(contact_name).lower()
            all_xero_contacts.append(contact_name)
            xero_contact_id = each_contact["ContactID"]
            all_xero_name_cotact_id_dicts[contact_name] = str(xero_contact_id)
        connection = True
        try:
            all_items = xero.items.all()
            connection = True
        except:
            all_items = []
            connection = False
        if connection != True:
            raise ValidationError('Authentication Failed! Please verify your credentials.')
        all_get_code = []
        for each in all_items:
            code = each['Code']
            all_get_code.append(str(code))
        all_accounts_connection = True
        try:
            all_accounts = xero.accounts.all()
            all_accounts_connection = True
        except:
            all_accounts = []
            all_accounts_connection = False
        if all_accounts_connection != True:
            raise ValidationError('Auhttps://api.xero.com/oauth/Authorize?oauth_token=Z4AU3MJGHIDX7MOUA5VA1LE2YZCXE2thentication Failed! Please verify your credentials.')
        odoo_all_account_types = {'Current Assets': 'CURRENT', 'Non-current Assets': 'NONCURRENT',
                                  'Fixed Assets': 'FIXED', 'Income':'SALES', 'Expense':'EXPENSE', 'prepayments':'PREPAYMENT',
                                  'Current Liabilities': 'CURRLIAB', 'Non-current Liabilities': 'TERMLIAB',
                                  'Equity': 'EQUITY', 'Other Income': 'OTHERINCOME', 'Depreciation': 'DEPRECIATN',
                                  'Cost of Revenue': 'REVENUE', 'Bank and Cash': 'BANK',}
        all_get_accounts_code = []
        for each in all_accounts:
            if 'Code' in each:
                xero_account_code = each['Code']
                all_get_accounts_code.append(str(xero_account_code))
        error_items_codes = []
        error_account_codes = []
        check_product_codes = []
        check_account_codes = []
        check_contact_names = []
        for invoice in invoices:
            if invoice.xero_invoice_id and invoice.xero_invoice_id in [xero_invoice['InvoiceID'] for xero_invoice in all_invoices]:
                self.update_invoice_status(xero,invoice)
                continue
            partner_id = invoice.partner_id
            customer_name = partner_id.name
            customer_name_in_lower = str(customer_name).lower()
            invoice_line_ids = invoice.invoice_line_ids
            invoice_dict = {}
            invoice_dict['Contact'] = {}
            invoice_dict['Type'] = {}
            invoice_dict['LineItems'] = {}
            listtt = []
            lineitem = {}
            if not partner_id or not invoice_line_ids:
                pass
            else:
                contact_id = None
                if (customer_name_in_lower not in all_xero_contacts) and (customer_name_in_lower not in check_contact_names):
                    contact_dict = self.make_contact_to_upload(invoice)
                    try:
                        response_contact_put = xero.contacts.put(contact_dict)
                        partner_id.write({'xero_contact_id': response_contact_put[0]['ContactID']})
                        contact_id = response_contact_put[0]['ContactID']
                        contact_id = str(contact_id)
                        all_xero_name_cotact_id_dicts[customer_name_in_lower] = str(contact_id)
                        check_contact_names.append(customer_name_in_lower)
                    except:
                        contact_id = None
                else:
                    contact_id = all_xero_name_cotact_id_dicts[customer_name_in_lower]
                if contact_id:
                    invoice_date = invoice.invoice_date
                    if invoice_date:
                        odoo_invoice_date = invoice.invoice_date
                        odoo_invoice_date = datetime.strptime(str(odoo_invoice_date),'%Y-%m-%d')
                        invoice_dict['Date'] = odoo_invoice_date
                    invoice_date_due = invoice.invoice_date_due
                    if invoice_date_due:
                        invoice_dict['DueDate'] = datetime.strptime(str(invoice_date_due),'%Y-%m-%d')
                    else:
                        invoice_dict['DueDate'] = (datetime.now() - timedelta(days=30)).date()
                    invoice_number = invoice.number
                    if invoice_number:
                        invoice_dict['InvoiceNumber'] = invoice.number
                    reference = invoice.name
                    if reference:
                        invoice_dict['Reference'] = reference
                        print(reference)
                    state = invoice.state
                    if state:
                        if state == 'draft':
                            invoice_dict['Status'] = 'DRAFT'
                        if state == 'open':
                            invoice_dict['Status'] = 'AUTHORISED'

                        else:
                            pass
                    currency_code = invoice.currency_id.name
                    invoice_dict['Contact']['ContactID'] = contact_id
                    for each_invoice_line in invoice_line_ids:
                        s_product_description = each_invoice_line.name
                        s_taxes = each_invoice_line.tax_ids
                        quantity = each_invoice_line.quantity
                        price_unit = each_invoice_line.price_unit
                        product_id = each_invoice_line.product_id
                        internal_reference = None
                        if product_id:
                            internal_reference = product_id.default_code
                            if not internal_reference:
                                internal_reference = "PR-COD" + str(product_id)
                            if (str(internal_reference) not in all_get_code) and (str(internal_reference) not in check_product_codes):
                                product_name = product_id.name
                                lst_price = product_id.lst_price
                                mydict = {}
                                # purchase_dict = {}
                                sale_dict = {}
                                if internal_reference:
                                    mydict['Code'] = str(internal_reference)
                                    if product_name:
                                        mydict['Name'] = str(product_name)
                                    if lst_price:
                                        sale_dict['UnitPrice'] = str(lst_price)
                                    if sale_dict:
                                        mydict['SalesDetails'] = sale_dict
                                    if mydict:
                                        try:

                                            xero.items.put(mydict)
                                        except:
                                            error_itm_code = mydict['Code']
                                            error_items_codes.append(error_itm_code)
                                        if internal_reference not in error_items_codes:
                                            check_product_codes.append(str(internal_reference))
                                    mydict = {}
                                    sale_dict = {}
                        else:
                            continue
                        account_id = each_invoice_line.account_id
                        income_account_code = None
                        if account_id:
                            income_account_code = account_id.code
                            income_account_name = account_id.name
                            income_account_type_name = account_id.user_type_id.name
                            income_account_code = str(income_account_code)
                            if (income_account_code not in all_get_accounts_code) and (income_account_code not in check_account_codes):
                                try:
                                    accounttype = odoo_all_account_types[income_account_type_name]
                                except:
                                    accounttype = None
                                if accounttype == None:
                                    income_account_type_name = 'OTHERINCOME'
                                else:
                                    income_account_type_name = accounttype
                                # acc_array = {'Code': str(income_account_code), 'Name': str(income_account_name), 'Type': str(income_account_type_name)}
                                acc_array = {'Code': str(income_account_code), 'Name': str(income_account_name), 'Type': str(income_account_type_name), 'TaxType': 'NONE'}
                                if acc_array:
                                    try:
                                        response_acc_chart = xero.accounts.put(acc_array)
                                        account_id.write({'xero_account_chart_id': response_acc_chart[0]['AccountID']})

                                    except:
                                        error_code = acc_array['Code']
                                        error_account_codes.append(error_code)
                                    if income_account_code not in error_account_codes:
                                        check_account_codes.append(str(income_account_code))
                        odoo_tax_type = ''
                        if str(s_taxes) == 'account.tax()':
                            tax_id = 1
                            odoo_tax_type = 'NONE'
                        else:
                            tax_id = s_taxes.id
                        xero_all_taxes = xero.taxrates.all()
                        odoo_tax = self.env['account.tax']
                        odoo_tax_name = odoo_tax.browse(tax_id)
                        odoo_tax_rate = str(odoo_tax_name.amount)
                        odoo_tax_name = str(odoo_tax_name.name)
                        filtered = xero.taxrates.filter(Name=odoo_tax_name, Status='ACTIVE')
                        if len(filtered) == 1:
                            response_tax_dictionary = xero.taxrates.filter(Name=odoo_tax_name)
                        else:
                            odoo_tax_put = odoo_tax.browse(tax_id)
                            name_tax = str(odoo_tax_put.name)
                            if odoo_tax_put.type_tax_use == 'sale':
                                odoo_tax_type = 'OUTPUT'
                            elif odoo_tax_put.type_tax_use == 'purchase':
                                odoo_tax_type = 'INPUT'
                            else:
                                odoo_tax_type = 'NONE'
                            odoo_tax_status = 'ACTIVE'
                            odoo_report_tax_type = odoo_tax_type
                            odoo_tax_component_name = name_tax
                            odoo_tax_rate = odoo_tax_component_rate = str(odoo_tax_put.amount)
                            odoo_tax_component_IsCompound = 'false'
                            odoo_tax_dict = {}
                            odoo_tax_dict['TaxComponents'] = {}
                            odoo_tax_dict['TaxComponents']['TaxComponent'] = {}
                            odoo_tax_dict['Name'] = str(name_tax)
                            odoo_tax_dict['TaxType'] = str(odoo_tax_type)
                            odoo_tax_dict['Status'] = str(odoo_tax_status)
                            odoo_tax_dict['TaxComponents']['TaxComponent']['Name'] = str(odoo_tax_component_name)
                            odoo_tax_dict['TaxComponents']['TaxComponent']['Rate'] = str(odoo_tax_component_rate)
                            odoo_tax_dict['TaxComponents']['TaxComponent']['IsCompound'] = odoo_tax_component_IsCompound
                            response_tax_put = xero.taxrates.put(odoo_tax_dict)
                            # odoo_tax_put.write({'xero_tax_id': response_tax_put[0]['']})
                        lineitem['Description'] = s_product_description
                        lineitem['Quantity'] = quantity
                        lineitem['UnitAmount'] = price_unit
                        lineitem['ItemCode'] = internal_reference
                        lineitem['AccountCode'] = income_account_code
                        lineitem['TaxType'] = odoo_tax_type
                        if odoo_tax_type == 'NONE':
                            odoo_tax_rate = 0
                            lineitem['TaxAmount'] = str(((float(price_unit)*float(quantity))*(float(odoo_tax_rate)/100)))
                        # print "Tax Amount" + lineitem['TaxAmount']
                        else:
                            lineitem['TaxAmount'] = str(((float(price_unit) * float(quantity)) * (float(odoo_tax_rate) / 100)))
                        if invoice.type == 'in_invoice':
                            invoice_dict['Type'] = "ACCPAY"
                        if invoice.type == 'out_invoice':
                            invoice_dict['Type'] = "ACCREC"

                        invoice_dict['LineAmountTypes'] = 'Exclusive'
                        listtt.append(lineitem.copy())
                    if not listtt:
                        continue
                invoice_dict['LineItems'] = listtt
                try:

                    if invoice.state == 'paid':
                        invoice_dict['Status'] = 'AUTHORISED'
                        try:
                            xero_response = xero.invoices.put(invoice_dict.copy())
                            invoice.write({"xero_invoice_id": xero_response[0]['InvoiceID'] })
                        except:

                            xero_response = xero.invoices.filter(InvoiceNumber= invoice_dict['InvoiceNumber'])
                            invoice.write({"xero_invoice_id": xero_response[0]['InvoiceID']})
                            amount = 0.0
                            for line in invoice_dict['LineItems']:
                                amount += (float(line['Quantity']) * float(line['UnitAmount'])) + float(line['TaxAmount'])
                            payment_dict = {

                                "Invoice": {"InvoiceID": xero_response[0]['InvoiceID']},
                                "Account": {"Code": income_account_code},
                                "Date": datetime.strptime(str(self.payment_ids[-1].payment_date), '%Y-%m-%d')
                                                        if self.payment_ids.payment_date else datetime.now(),

                                    "Amount": self.payment_ids[-1].amount if self.payment_ids else amount


                            }
                            try:
                                xero.payments.put(payment_dict.copy())
                            except:
                                continue
                        try:
                            amount = 0.0
                            for line in invoice_dict['LineItems']:
                                amount += (float(line['Quantity']) * float(line['UnitAmount'])) + float(line['TaxAmount'])
                            payment_dict = {

                                    "Invoice": {"InvoiceID": xero_response[0]['InvoiceID']},
                                    "Account": {"Code": income_account_code},
                                    "Date": datetime.strptime(str(self.payment_ids[-1].payment_date), '%Y-%m-%d')
                                                        if self.payment_ids.payment_date else datetime.now(),

                                    "Amount": self.payment_ids[-1].amount if self.payment_ids else amount

                            }
                            xero.payments.put(payment_dict.copy())
                        except Exception as e:

                            raise UserError(("Please enable payments on account having code " + str(income_account_code)) +" in xero")
                    else:
                        try:
                            xero_response = xero.invoices.put(invoice_dict.copy())
                            invoice.write({"xero_invoice_id": xero_response[0]['InvoiceID']})
                        except:
                            continue

                except Exception as e:

                    raise ValidationError(str(e))

    def update_invoice_status(self, xero, invoice):

        xero_invoice_id = invoice.xero_invoice_id
        xero_invoice = xero.invoices.get(xero_invoice_id)[0]
        if xero_invoice['Status']== 'PAID':
            return
        else:


            status = None
            if invoice.state:
                if invoice.state == 'draft' or invoice.invoice_payment_state == 'draft':
                    status = 'DRAFT'
                if invoice.state == 'posted' and invoice.invoice_payment_state == 'not_paid':
                    status = 'AUTHORISED'
                if invoice.state == 'posted' and invoice.invoice_payment_state == 'paid':
                    status = "PAID"
                else:
                    pass
            if not xero_invoice['Status'] == 'AUTHORISED' and (invoice.state == 'paid' or invoice.invoice_payment_state == 'paid'):
                xero_invoice['Status'] = 'AUTHORISED'
                xero_invoice['InvoiceNumber'] = invoice.number
                xero.invoices.save(xero_invoice)
            if xero_invoice['Status'] == status:
                return
            else:
                if invoice.invoice_payment_state == 'paid':

                    # for line_item in xero_invoice['LineItems']:
                    try:
                        payment = self.env['account.payment'].search([('invoice_ids', '=', invoice.id)])
                        if 'LineItems' in xero_invoice:
                            xero_account = xero.accounts.get(xero_invoice['LineItems'][0]['AccountCode'])[0]

                        if payment:
                            pay_amout = payment[0].amount

                        payment_dict = {

                            "Invoice": xero_invoice ,
                            "PaymentType": payment.payment_type,#{"InvoiceID": xero_invoice['InvoiceID']},
                            "Account": {"AccountID": xero_account['AccountID'] ,"Code": xero_account['Code']},
                            # "Account": xero_account,
                            "Date": payment.payment_date,#datetime.strptime(str(self.payment_ids[-1].payment_date), '%Y-%m-%d'),
                            "BankAmount": invoice.amount_total,
                            "Amount": pay_amout,


                        }

                        print(payment_dict)
                        xero.payments.put(payment_dict.copy())
                    except Exception as e:

                        raise UserError(
                            ( "Please enable payments on account having code " + str(xero_invoice['LineItems'][0]['AccountCode'])) + " in xero")

                else:
                    xero_invoice['Status'] = status
                    # xero_invoice['InvoiceNumber'] = invoice.number
                    xero.invoices.save(xero_invoice)


class Xero_Import(models.Model):
    _name = 'xero.connector'
    _description = "xero.connector"

    consumer_key = fields.Char(string="Consumer Key", required=True, default= 'CNALIRCTB3ZBCXHMBPCYOJFHPPWGMC')
    consumer_secret = fields.Char(string="Consumer Secret", required=True, default= 'XFC9ZQSEDQAV6IJ8YJBKWXWVTHQTIE')
    verify_code = fields.Char(string="Code")
    credentials = fields.Char(string='Credentials')

    @api.model
    def call_js(self):
       print( 'testing js in odooooooooooooooooooooooooooo')

    def mydateconverter(self, o):
        if isinstance(o, datetime):
            return o.__str__()

    def get_code(self):
        try:
            cre = PublicCredentials(self.consumer_key, self.consumer_secret)
            self.env.user.credentials = json.dumps(cre.state, default=self.mydateconverter)
            webbrowser.open_new_tab(cre.url)
        except Exception as e:
            raise ValidationError(str(e))

    def code_verify(self):
        try:
            save_state = json.loads(self.env.user.credentials)
            cre = PublicCredentials(**save_state)
            cre.verify(self.verify_code)
            xero = Xero(cre)
            all_contacts = xero.contacts.all()
            self.env.user.credentials = json.dumps(cre.state, default=self.mydateconverter)
            self.env.cr.commit()
            connection = True
        except:
            connection = False
        if (connection == True):
            raise ValidationError(" Connection Successful !")
        else:
            raise ValidationError(" Connection Failed !")

    def import_contacts(self, **kwargs):


        credentials = self.env['product.template'].xero_authentication()
        xero = Xero(credentials)
        connection = True
        try:
            if 'xero_contact' in kwargs:
                xero_all_contacts = xero.contacts.get(kwargs['xero_contact'])
            else:
                xero_all_contacts = xero.contacts.all()
            connection = True
        except:
            xero_all_contacts = []
            connection = False
        if (connection != True):
            raise ValidationError('Authentication Failed! Please verify your credentials.')
        try:
            for xero_contact in xero_all_contacts:

                if not self.env['res.partner'].search([('xero_contact_id', '=', str(xero_contact['ContactID']))]):
                    first_name = ''
                    last_name = ''
                    if "FirstName" in xero_contact:
                        first_name = xero_contact['FirstName']

                    if "LastName" in xero_contact:
                        last_name = xero_contact['LastName']
                    if str(first_name + last_name) == '':
                        first_name = xero_contact['Name']

                    for address in xero_contact['Addresses']:
                        if address['AddressType'] == "STREET":
                            street = str(address['AttentionTo']) if "AttentionTo" in address else None
                            city = address['City'] if 'City' in address and address['City'] else None
                            zip = address['PostalCode'] if 'PostalCode' in address and address['PostalCode'] else None
                            state_id = country_id = None
                            if "Region" in address and address['Region']:
                                state_id = self.env['res.country.state'].search([('name', '=', address['Region'])])
                                if state_id:
                                    state_id = state_id[0].id
                            if "Country" in address and address["Country"]:
                                country_id =self.env['res.country'].search([('name', '=', address['Country'])])
                                if country_id:
                                    country_id = country_id[0].id

                    tax_no = None
                    phone_no = None
                    mob = None
                    customer_rank = None
                    supplier_rank = None
                    if 'IsCustomer' in xero_contact and xero_contact['IsCustomer']:
                        customer_rank = 1
                    if 'IsSupplier' in xero_contact and xero_contact['IsCustomer']:
                        supplier_rank =1

                    if 'TaxNumber' in xero_contact:
                        tax_no = xero_contact['TaxNumber']

                    for phone in xero_contact['Phones']:
                        if phone['PhoneType'] == 'DEFAULT':
                            if 'PhoneCountryCode' in phone and 'PhoneAreaCode' in phone and 'PhoneNumber' in phone:
                                phone_no = phone['PhoneCountryCode'] + phone['PhoneAreaCode'] + phone['PhoneNumber']
                            elif 'PhoneNumber' in phone:
                                phone_no = phone["PhoneNumber"]
                        if phone['PhoneType'] == 'MOBILE':
                            if 'PhoneCountryCode' in phone and 'PhoneAreaCode' in phone and 'PhoneNumber' in phone:
                                mob = phone['PhoneCountryCode'] + phone['PhoneAreaCode'] + phone['PhoneNumber']
                            elif 'PhoneNumber' in phone:
                                mob = phone["PhoneNumber"]
                    self.env['res.partner'].create({
                        'xero_contact_id': xero_contact['ContactID'],
                        'name': str(first_name + last_name),
                        'email': xero_contact['EmailAddress'] if 'EmailAddress' in xero_contact else None,
                        'vat': tax_no,
                        'street': street,
                        'city': city,
                        'state_id':  state_id,
                        'country_id': country_id,
                        'zip':zip,
                        'phone': phone_no,
                        'mobile': mob,
                        'customer_rank':customer_rank,
                        'supplier_rank': supplier_rank,

                    })
        except Exception as e:
            raise ValidationError(str(e))

    def import_products(self, **kwargs):
        credentials = self.env['product.template'].xero_authentication()
        xero = Xero(credentials)
        connection = True
        try:
            if 'code' in kwargs:
                xero_all_items = xero.items.filter(Code= kwargs['code'])
            else:
                xero_all_items = xero.items.all()
            connection = True
        except:
            xero_all_items = []
            connection = False
        if (connection != True):
            raise ValidationError('Authentication Failed! Please verify your credentials.')
        try:
            for xero_product in xero_all_items:
                if not self.env['product.template'].search([('xero_product_id', '=', str(xero_product['ItemID']))]):
                    cost = None
                    sale = None
                    if 'UnitPrice' in xero_product['PurchaseDetails']:
                        cost = xero_product['PurchaseDetails']['UnitPrice']
                    if 'UnitPrice' in xero_product['SalesDetails']:
                        sale = xero_product['SalesDetails']['UnitPrice']
                    self.env['product.template'].create({
                        'xero_product_id': xero_product['ItemID'],
                        'default_code': xero_product['Code'],
                        'name': xero_product['Name'],
                        'standard_price':cost,
                        'list_price':sale,
                        'sale_ok':xero_product['IsSold'],
                        'purchase_ok': xero_product['IsPurchased'],
                    })


        except Exception as e:

            raise ValidationError(str(e))




    def import_invoices(self):

            # self.import_taxes()
            credentials = self.env['product.template'].xero_authentication()
            xero = Xero(credentials)
            connection = True
            try:
                xero_all_invoices = xero.invoices.all()
                connection = True
            except:
                xero_all_invoices = []
                connection = False
            if (connection != True):
                raise ValidationError('Authentication Failed! Please verify your credentials.')
            try:
                total_tax =0
                for xero_invoice in xero_all_invoices:
                    if not self.env['account.move'].search(
                            [('xero_invoice_id', '=', str(xero_invoice['InvoiceID']))]):
                        customer = self.env['res.partner'].search(
                            [('xero_contact_id', '=', xero_invoice['Contact']['ContactID'])])
                        if not customer:
                            self.import_contacts(xero_contact=xero_invoice['Contact']['ContactID'])
                            customer = self.env['res.partner'].search(
                                [('xero_contact_id', '=', xero_invoice['Contact']['ContactID'])])

                        currency_id = self.env['res.currency'].search([('name', '=', xero_invoice['CurrencyCode'])])
                        if not currency_id:
                            currency_id = self.env['res.currency'].search(
                                [('active', '=', False), ('name', '=', xero_invoice['CurrencyCode'])])
                            currency_id.write({'active': True})
                        pay_status = None


                        if xero_invoice['Status'] == 'DRAFT':
                            state = 'draft'
                        elif xero_invoice['Status'] == 'PAID':
                            state = 'paid'
                            pay_status = 'paid'

                        elif xero_invoice['Status'] == 'AUTHORISED':
                            state = 'authorised'

                        else:
                            continue


                        invoice_number_uniq = self.env['account.move'].search(
                            [('number', '=', xero_invoice['InvoiceNumber'])])
                        if invoice_number_uniq:
                            continue
                        # CHECK EITHER THE INVOICE DATA IS BILL OR INVOICE..
                        if xero_invoice['Type'] == "ACCPAY":
                            inv_type = 'in_invoice'
                            journal_id = self.env['account.journal'].search([('code', '=', 'BILL')]).id
                        if xero_invoice['Type'] == "ACCREC":
                            inv_type = 'out_invoice'
                            journal_id = self.env['account.journal'].search([('code', '=', 'INV')]).id



                        due_date = str((xero_invoice['Date'] - timedelta(days=30)).date())
                        invoice = None
                        # if state == 'draft':
                        count =0
                        tax_per = []
                        product_ids =[]
                        acc_id =[]
                        move_list = []

                        line_items = xero.invoices.get(xero_invoice['InvoiceID'])[0]['LineItems']

                        for line_item in line_items:
                            count = count + 1
                            if 'ItemCode' in line_item:
                                code = line_item['ItemCode']
                                product = self.env['product.product'].search([('default_code', '=', code)])
                                if not product:
                                    self.import_products(code=code)
                                    product = self.env['product.product'].search([('default_code', '=', code)])[0]
                                    product_ids.append(product.id)
                                else:
                                    product = product[0]
                                    product_ids.append(product.id)
                                account_id = None

                                if "AccountCode" in line_item:
                                    account_id = self.env['account.account'].search(
                                        [('code', '=', line_item['AccountCode'])]).id
                                    acc_id.append(account_id)
                                    if not account_id:
                                        self.import_charts_of_accounts(code=line_item['AccountCode'])
                                        account_id = self.env['account.account'].search(
                                            [('code', '=', line_item['AccountCode'])]).id
                                        acc_id.append(account_id)
                                else:
                                    type_id = self.env['account.account.type'].search([('name', '=', 'Other Income')]).id
                                    account_id = self.env['account.account'].search([('user_type_id', '=', type_id)]).id
                                    acc_id.append(account_id)

                                tax_id = None

                                if 'TaxType' in line_item:
                                    tax = xero.taxrates.filter(TaxType=line_item['TaxType'])
                                    if tax:
                                        # tax_type = tax[0]['TaxType']
                                        tax_name = tax[0]['Name']
                                        # tax_id = tax[0].id
                                        # tax_per.append(tax_id)

                                    tax_type = "none"
                                    if line_item['TaxType'] == 'OUTPUT':
                                        tax_type = 'sale'

                                    elif line_item['TaxType'] == 'INPUT':
                                        tax_type = 'purchase'
                                    elif line_item['TaxType'] == 'GSTONIMPORTS' or line_item['TaxType']:
                                        tax_type = 'sale'
                                    elif line_item['TaxType']:
                                            odoo_tax = self.env['account.tax'].search([('name','=',tax_name)])
                                            if odoo_tax:
                                                tax_ids = odoo_tax

                                            else:
                                                self.import_taxes()
                                                tax_id = self.env['account.tax'].search( [('type_tax_use', '=', tax_type),('name','=',tax_name)])
                                                tax_id = odoo_tax.id

                                    else:
                                        tax_type = None

                                    tax_ids = []
                                    if not tax_id:
                                        tax_id = self.env['account.tax'].search([('type_tax_use', '=', tax_type),('name','=',tax_name)])
                                        tax_per.append(tax_id)
                                        if not tax_id:
                                            self.import_taxes()
                                            tax_id = self.env['account.tax'].search([('type_tax_use', '=', tax_type),('name','=',tax_name)])
                                            tax_ids.append(tax_id[0].id)
                                            tax_per.append(tax_id)
                                        else:
                                            tax_ids.append(tax_id[0].id)
                                            tax_per.append(tax_id)


                                    else:
                                        tax_ids.append(tax_id[0].id)
                                        tax_per.append(tax_id)

                                    move_line_dict ={
                                        'product_id': product.id,
                                        'name': line_item['Description'] if 'Description' in line_item else None,
                                        'quantity': line_item['Quantity'] if 'Quantity' in line_item else None,
                                        'account_id': account_id,
                                        'price_unit': line_item[
                                        'UnitAmount'] if 'UnitAmount' in line_item else None,
                                        'price_subtotal': line_item['LineAmount'],
                                        'tax_ids': tax_ids,
                                        'price_total': line_item['LineAmount'],
                                        'credit': line_item['LineAmount'],

                                    }

                                    move_list.append(move_line_dict)

                            else:
                                account_id = None

                                if "AccountCode" in line_item:
                                    account_id = self.env['account.account'].search(
                                        [('code', '=', line_item['AccountCode'])]).id
                                    if not account_id:
                                        self.import_charts_of_accounts(code=line_item['AccountCode'])
                                        account_id = self.env['account.account'].search(
                                            [('code', '=', line_item['AccountCode'])]).id
                                else:
                                    type_id = self.env['account.account.type'].search(
                                        [('name', '=', 'Other Income')]).id
                                    account_id = self.env['account.account'].search([('user_type_id', '=', type_id)]).id

                                    tax_id = None
                                    if 'TaxType' in line_item:
                                        tax_type = "none"
                                        if line_item['TaxType'] == 'OUTPUT':
                                            tax_type = 'sale'

                                        if line_item['TaxType'] == 'INPUT':
                                            tax_type = 'purchase'
                                        if line_item['TaxType'] == 'GSTONIMPORTS':
                                            tax_type = 'adjustment'

                                        tax_id = self.env['account.tax'].search([('type_tax_use', '=', tax_type)])
                                        if not tax_id:
                                            self.import_taxes()
                                            tax_id = self.env['account.tax'].search([('type_tax_use', '=', tax_type)])

                                        move_line_dict = {
                                            'name': line_item[
                                                'Description'] if 'Description' in line_item else None,
                                            'quantity': line_item['Quantity'] if 'Quantity' in line_item else None,
                                            'account_id': account_id,
                                            'price_unit': line_item[
                                                'UnitAmount'] if 'UnitAmount' in line_item else None,
                                            'price_subtotal': line_item['LineAmount'],
                                            'tax_ids': tax_id.id,
                                            'price_total': line_item['LineAmount'],
                                            'credit': line_item['LineAmount'],

                                        }

                                        move_list.append(move_line_dict)

                        if state == 'draft':
                            continue

                            invoice = self.env['account.move'].create({
                                'xero_invoice_id': xero_invoice['InvoiceID'],
                                'type': inv_type,
                                'number': xero_invoice['InvoiceNumber'],
                                'currency_id': currency_id.id,
                                'state': state,
                                'journal_id': journal_id,
                                'partner_id': customer.id,
                                'invoice_date': xero_invoice['DateString'],
                                'invoice_date_due': due_date,
                                'invoice_line_ids' :  move_list


                            })

                        elif state == 'authorised':
                            continue
                            invoice = self.env['account.move'].create({
                                'xero_invoice_id': xero_invoice['InvoiceID'],
                                'type': inv_type,
                                'number': xero_invoice['InvoiceNumber'],
                                'currency_id': currency_id.id,
                                # 'invoice_payment_ref' :
                                'journal_id': journal_id,
                                'partner_id': customer.id,
                                'invoice_date': xero_invoice['DateString'],
                                'invoice_date_due': due_date,
                                'invoice_line_ids': move_list

                            })

                            invoice.post()

                        elif state == 'paid':
                            invoice = self.env['account.move'].create({
                                'xero_invoice_id': xero_invoice['InvoiceID'],
                                'type': inv_type,
                                'number': xero_invoice['InvoiceNumber'],
                                'currency_id': currency_id.id,
                                'invoice_payment_state': 'paid',
                                # 'state': state,
                                # 'invoice_payment_state' : state,
                                'journal_id': journal_id,
                                'partner_id': customer.id,
                                'invoice_date': xero_invoice['DateString'],
                                'invoice_date_due': due_date,
                                'invoice_line_ids': move_list

                            })


                            if invoice:

                                payment_type = None
                                payment_method_id = None

                                if inv_type == 'out_invoice':
                                    payment_type = 'outbound'
                                    payment_method_id = 2
                                    partner_type = 'customer'

                                elif inv_type == 'in_invoice':
                                    payment_type = 'inbound'
                                    payment_method_id = 1
                                    partner_type = 'supplier'

                                else:
                                    payment_type ='transfer'
                                    payment_method_id = 3

                                payment_dict = {

                                    'invoice_ids' : invoice,
                                    'currency_id' : currency_id.id,
                                    'payment_method_id' : payment_method_id,
                                    'partner_type' : partner_type,
                                    'payment_type':payment_type if payment_type else None,
                                    'partner_id': customer.id if customer else None,
                                    'amount':xero_invoice['Payments'][0]['Amount'] if 'Payments' in xero_invoice else None,
                                    'payment_date': xero_invoice['Payments'][0]['Date'] if 'Payments' in xero_invoice else None,
                                    'journal_id': journal_id
                                }

                                invoice.post()
                                invoice.action_invoice_register_payment()
                                invoice.invoice_payment_state = state
                                invoice.amount_residual_signed = 0
                                invoice.amount_residual = 0

                                mod = self.env['account.payment']
                                id = mod.create(payment_dict)
                                id.state = 'posted'
                                self.env.cr.commit()
                                # id.post()
                                # mod.browse(id.id).invoice_ids = invoice
                                # invoice.action_invoice_register_payment()
                                # mod.post()



                        else:

                            pass

                        self.env.cr.commit()
            except Exception as e:
                raise ValidationError(str(e))

    def import_taxes(self):

        credentials = self.env['product.template'].xero_authentication()
        xero = Xero(credentials)
        connection = True
        try:
            xero_all_taxes = xero.taxrates.all()
            connection = True
        except:
            xero_all_taxes = []
            connection = False
        if (connection != True):
            raise ValidationError('Authentication Failed! Please verify your credentials.')

        try:
            for xero_tax in xero_all_taxes:
                if not xero_tax['Status'] == 'ACTIVE':
                    continue
                tax_type = "none"

                if xero_tax['TaxType'] == 'OUTPUT':
                    tax_type = 'sale'

                elif xero_tax['TaxType'] == 'INPUT':
                    tax_type = 'purchase'

                # elif xero_tax['TaxType'] == 'GSTONIMPORTS':
                #     tax_type = 'adjustment'

                elif xero_tax['TaxType'] =='GSTONIMPORTS' or xero_tax['TaxType']!=None:
                    tax_type = 'sale'


                if not self.env['account.tax'].search([('name', '=', xero_tax['Name']), ('type_tax_use', '=', tax_type)]):
                    tax_ids = self.env['account.tax'].create({
                        'name': xero_tax['Name'],

                        'type_tax_use': tax_type,
                        'amount': float(xero_tax['TaxComponents'][0]['Rate']),
                        'description': xero_tax['TaxComponents'][0]['Name'],

                    })

        except Exception as e:
            raise ValidationError(str(e))

    def import_charts_of_accounts(self, **kwargs):

        credentials = self.env['product.template'].xero_authentication()
        xero = Xero(credentials)
        connection = True
        try:
            if 'code' in kwargs:
                xero_all_accounts = xero.accounts.filter(Code = kwargs['code'])
            else:
                xero_all_accounts = xero.accounts.all()
            connection = True
        except:
            xero_all_accounts = []
            connection = False
        if (connection != True):
            raise ValidationError('Authentication Failed! Please verify your credentials.')

        xero_account_type = { 'CURRENT':'Current Assets', 'NONCURRENT': 'Non-current Assets',
                                   'FIXED':'Fixed Assets', 'SALES':'Income', 'EXPENSE':'Expenses', 'PREPAYMENT':'prepayments',
                                   'CURRLIAB':'Current Liabilities', 'TERMLIAB':'Non-current Liabilities',
                                   'EQUITY':'Equity', 'OTHERINCOME':'Other Income', 'DEPRECIATN':'Depreciation',
                                   'REVENUE':'Cost of Revenue', 'BANK':'Bank and Cash',}

        try:
            for xero_account in xero_all_accounts:
                if xero_account['Type'] in xero_account_type:
                    type_id = self.env['account.account.type'].search([('name', '=', xero_account_type[xero_account['Type']])])
                else:
                    type_id = self.env['account.account.type'].search([('name', '=', 'Other Income')])

                if not self.env['account.account'].search([('xero_account_chart_id', '=', xero_account['AccountID'])]):
                    self.env['account.account'].create({
                        'code': xero_account['Code'],
                        'name': xero_account['Name'],
                        'user_type_id': type_id.id,
                    })
        except Exception as e:
            raise ValidationError(str(e))


    def export_all_contacts(self):
        self.env['res.partner'].upload_contacts_xero()

    def export_all_products(self):
        self.env['product.template'].sync_product_to_zero()

    def export_all_invoices(self):
        self.env['account.move'].sync_invoices_to_xero()