# -*- coding: utf-8 -*-

import logging
import re

from odoo import fields, models, api, osv
from openerp.exceptions import ValidationError
from openerp.osv import osv
from openerp import _
import webbrowser
from odoo.http import request
from email.utils import formataddr

from odoo import _, api, fields, models, modules, SUPERUSER_ID, tools
from odoo.exceptions import UserError, AccessError
from odoo.osv import expression

import requests
import json
from datetime import datetime
import time
from dateutil import tz
from datetime import timedelta

_logger = logging.getLogger(__name__)
_image_dataurl = re.compile(r'(data:image/[a-z]+?);base64,([a-z0-9+/]{3,}=*)([\'"])', re.I)


class OfficeSettings(models.Model):
    """
    This class separates one time office 365 settings from Token generation settings
    """
    _name = "office.settings"


    field_name = fields.Char('Office365')
    redirect_url = fields.Char('Redirect URL')
    client_id = fields.Char('Client Id')
    secret = fields.Char('Secret')
    # login_url = fields.Char('Login URL', compute='_compute_url', readonly=True)

    @api.one
    def sync_data(self):
        try:
            if not self.client_id or not self.redirect_url or not self.secret:
                 raise osv.except_osv(_("Wrong Credentials!"), (_("Please Check your Credentials and try again")))
            else:
                self.env.user.redirect_url = self.redirect_url
                self.env.user.client_id = self.client_id
                self.env.user.secret = self.secret
                self.env.user.code = None
                self.env.user.token = None
                self.env.user.refresh_token = None
                self.env.user.expires_in = None
                self.env.user.office365_email = None
                self.env.user.office365_id_address = None

                self.env.cr.commit()



        except Exception as e:
            raise ValidationError(_(str(e)))
        raise osv.except_osv(_("Success!"), (_("Successfully Activated!")))


class Office365UserSettings(models.Model):
    """
    This class facilitates the users other than admin to enter office 365 credential
    """
    _name = 'office.usersettings'


    login_url = fields.Char('Login URL', compute='_compute_url', readonly=True)
    code = fields.Char('code')
    field_name = fields.Char('office')
    token = fields.Char('Office_Token')


    @api.one
    def _compute_url(self):


        settings = self.env['office.settings'].search([])
        settings = settings[0] if settings else settings
        if settings:
            self.login_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=%s&redirect_uri=%s&response_type=code&scope=openid+offline_access+Calendars.ReadWrite+Mail.ReadWrite+Mail.Send+User.ReadWrite+Tasks.ReadWrite+Contacts.ReadWrite' % (
                settings.client_id, settings.redirect_url)


    @api.one
    def test_connectiom(self):

        try:

            settings = self.env['office.settings'].search([])
            settings = settings[0] if settings else settings

            if not settings.client_id or not settings.redirect_url or not settings.secret:
                raise osv.except_osv(_("Error!"), (_("Please ask admin to add Office365 settings!")))

            header = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            response = requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data='grant_type=authorization_code&code=' + self.code + '&redirect_uri=' + settings.redirect_url + '&client_id=' + settings.client_id + '&client_secret=' + settings.secret
                , headers=header).content

            if 'error' in json.loads(response.decode('utf-8')) and json.loads(response.decode('utf-8'))['error']:
                raise UserError('Invalid Credentials . Please! Check your credential and  regenerate the code and try again!')

            else :
                response = json.loads((str(response)[2:])[:-1])
                self.env.user.token = response['access_token']
                self.env.user.refresh_token = response['refresh_token']
                self.token = response['refresh_token']


                self.env.user.expires_in = int(round(time.time() * 1000))
                self.env.user.code = self.code
                self.code = ""
                response = json.loads((requests.get(
                    'https://graph.microsoft.com/v1.0/me',
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Accept': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    }).content.decode('utf-8')))
                self.env.user.office365_email = response['userPrincipalName']
                self.env.user.office365_id_address = 'outlook_' + response['id'].upper() + '@outlook.com'
                self.env.cr.commit()
                print("code=",self.code)
                # print('token=', self.token)



        except Exception as e:
            raise ValidationError(_(str(e)))

        raise osv.except_osv(_("Success!"), (_("Token Generated!")))


class CustomUser(models.Model):
    """
    This class adds functionality to user for Office365 Integration
    """
    _inherit = 'res.users'


    login_url = fields.Char('Login URL', compute='_compute_url', readonly=True)
    code = fields.Char('code')
    token = fields.Char('Token', readonly=True)
    refresh_token = fields.Char('Refresh Token', readonly=True)
    expires_in = fields.Char('Expires IN', readonly=True)
    redirect_url = fields.Char('Redirect URL')
    client_id = fields.Char('Client Id')
    secret = fields.Char('Secret')
    office365_email = fields.Char('Office365 Email Address', readonly=True)
    office365_id_address = fields.Char('Office365 Id Address', readonly=True)
    send_mail_flag = fields.Boolean(string='Send messages using office365 Mail', default=True)
    is_task_sync_on = fields.Boolean('is sync in progress', default=False)
    users = fields.Boolean('Export/Update Users')
    customers = fields.Boolean('Export/Update Customers')
    office_id = fields.Char('Office365 Id')



    @api.one
    def _compute_url(self):
        """
        this function creates a url. By hitting this URL creates a code that is require to generate token. That token will be sent with every API request

        :return:
        """
        self.login_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=%s&redirect_uri=%s&response_type=code&scope=openid+offline_access+Calendars.ReadWrite+Mail.ReadWrite+Mail.Send+User.ReadWrite+Tasks.ReadWrite+Contacts.ReadWrite' % (
            self.client_id, self.redirect_url)

    @api.one
    def user_login(self):
        """
        This function generates token using code generated using above login URL
        :return:
        """
        try:
            web = webbrowser.open(self.login_url)


        except Exception as e:
            raise ValidationError(_(str(e)))

        # raise osv.except_osv(_("Success!"), (_("Token Generated!")))

    def getAttendee(self, attendees):
        """
        Get attendees from odoo and convert to attendees Office365 accepting
        :param attendees:
        :return: Office365 accepting attendees

        """
        attendee_list = []
        for attendee in attendees:
            attendee_list.append({
                "status": {
                    "response": 'Accepted',
                    "time": datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
                },
                "type": "required",
                "emailAddress": {
                    "address": attendee.email,
                    "name": attendee.display_name
                }
            })
        return attendee_list

    def getTime(self, alarm):
        """
        Convert ODOO time to minutes as Office365 accepts time in minutes
        :param alarm:
        :return: time in minutes
        """
        if alarm.interval == 'minutes':
            return alarm[0].duration
        elif alarm.interval == "hours":
            return alarm[0].duration * 60
        elif alarm.interval == "days":
            return alarm[0].duration * 60 * 24

    def getdays(self, meeting):
        """
        Returns days of week the event will occure
        :param meeting:
        :return: list of days
        """
        days = []
        if meeting.su:
            days.append("sunday")
        if meeting.mo:
            days.append("monday")
        if meeting.tu:
            days.append("tuesday")
        if meeting.we:
            days.append("wednesday")
        if meeting.th:
            days.append("thursday")
        if meeting.fr:
            days.append("friday")
        if meeting.sa:
            days.append("saturday")
        return days

    def getAttachment(self, message):
        if self.env.user.expires_in:
            expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
            expires_in = expires_in + timedelta(seconds=3600)
            nowDateTime = datetime.now()
            if nowDateTime > expires_in:
                self.generate_refresh_token()

        response = requests.get(
            'https://graph.microsoft.com/v1.0/me/messages/' + message['id'] + '/attachments/',
            headers={
                'Host': 'outlook.office.com',
                'Authorization': 'Bearer {0}'.format(self.env.user.token),
                'Accept': 'application/json',
                'X-Target-URL': 'http://outlook.office.com',
                'connection': 'keep-Alive'
            }).content
        attachments = json.loads((response.decode('utf-8')))['value']
        attachment_ids = []
        for attachment in attachments:
            if 'contentBytes' not in attachment or 'name' not in attachment:
                continue
            odoo_attachment = self.env['ir.attachment'].create({
                'datas': attachment['contentBytes'],
                'name': attachment["name"],
                'datas_fname': attachment["name"]})
            self.env.cr.commit()
            attachment_ids.append(odoo_attachment.id)
        return attachment_ids

    def developer_test(self):
        try:
            channel = self.env['mail.channel'].search()
            raise osv.except_osv(_("Error!"), (_(channel)))
        except Exception as e:
            # self.env.user.send_mail_flag = True
            self.env.cr.commit()
            raise ValidationError(_(str(e)))
        self.env.cr.commit()


    def generate_refresh_token(self):

        if self.env.user.refresh_token:
            settings = self.env['office.settings'].search([])
            settings = settings[0] if settings else settings

            if not settings.client_id or not settings.redirect_url or not settings.secret:
                raise osv.except_osv(_("Error!"), (_("Please ask admin to add Office365 settings!")))

            header = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            response = requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data='grant_type=refresh_token&refresh_token=' + self.env.user.refresh_token + '&redirect_uri=' + settings.redirect_url + '&client_id=' + settings.client_id + '&client_secret=' + settings.secret
                , headers=header).content

            response = json.loads((str(response)[2:])[:-1])
            if 'access_token' not in response:
                response["error_description"] = response["error_description"].replace("\\r\\n", " ")
                raise osv.except_osv(_("Error!"), (_(response["error"] + " " + response["error_description"])))
            else:
                self.env.user.token = response['access_token']
                self.env.user.refresh_token = response['refresh_token']
                self.env.user.expires_in = int(round(time.time() * 1000))
        # else:
        #     raise osv.except_osv(_("Error!"), (_("Token is not exist to resfresh it!")))

    @api.model
    def auto_export_contact(self):
        self.export_contacts()
    @api.model
    def auto_import_contact(self):
        self.import_contacts()

    def export_contacts(self):
        if self.users or self.customers:
            self.export_details()
        else:
            print('Please select the check button on Office365 Contact to export the contact from odoo to office365')

    def export_details(self):

        is_customer = False
        if self.customers:
            is_customer = True
            self.export_Contact_details(is_customer)
        if self.users:
            is_customer = False
            self.export_Contact_details(is_customer)

    def export_Contact_details(self,is_customer):

        if self.env.user.token:
            try:
                if self.env.user.token:
                    if self.env.user.expires_in:
                        expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                        expires_in = expires_in + timedelta(seconds=3600)
                        nowDateTime = datetime.now()
                        if nowDateTime > expires_in:
                            self.generate_refresh_token()

                    odoo_contacts = self.env['res.partner'].search([('customer','=', is_customer)])
                    headers = {

                        'Host': 'outlook.office365.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'}

                    url = 'https://graph.microsoft.com/v1.0/me/contacts'


                    for contact in odoo_contacts:

                        company = None
                        city = None
                        country = None
                        street = None
                        state = None
                        if contact.company_name:
                            company = contact.company_name

                        elif contact.parent_id.name:
                            company = contact.parent_id.name
                            street = contact.parent_id.street +',' + contact.parent_id.street2
                            country = contact.parent_id.country_id['name']
                            state = contact.parent_id.state_id.name
                            city = contact.parent_id.city
                        else:
                            street = str(contact.street) + ',' + str(contact.street2)
                            country = contact.country_id['name']
                            state = contact.state_id.name
                            city = contact.city

                        data = {
                            "givenName": contact.name if contact.name else None,
                            'companyName': company if company else None,
                            'mobilePhone': contact.mobile if contact.mobile else None,
                            'jobTitle': contact.function if contact.function else None,
                            # 'homePhones' : ,
                            "businessPhones": [
                                contact.phone if contact.phone else None
                            ],
                            'homeAddress': {'city': city if city else None, 'state': state if state else None, 'street': street if street else None, 'countryOrRegion': country if country else None,
                                            'postalCode': contact.zip if contact.zip else ''},
                            'title' : contact.title.name if contact.title.name else None,
                            'businessHomePage' : contact.website if contact.website else None,
                                             }

                        if contact.email:
                            data["emailAddresses"] = [
                                    {
                                        "address": contact.email if contact.email else None,
                                    }
                                ]

                        if not contact.email and not contact.mobile and not contact.phone :
                            print(contact)
                            continue
                        if contact.office_id:
                            patch_response = requests.patch(
                                url+ '/' +contact.office_id, data=json.dumps(data), headers=headers
                            )
                            if patch_response.status_code != 200:
                                post_response = requests.post(
                                    url, data=json.dumps(data), headers=headers
                                ).content

                                if 'id' not in json.loads(post_response.decode('utf-8')).keys():
                                    raise osv.except_osv(_("Error!"), (_(post_response["error"])))
                                else:
                                    contact.write({'office_id': json.loads(post_response.decode('utf-8'))['id'] })

                        else :
                            post_response = requests.post(
                                url, data=json.dumps(data), headers=headers
                            ).content

                            if 'id' not in json.loads(post_response.decode('utf-8')).keys():
                                raise osv.except_osv(_("Error!"), (_(post_response["error"])))
                            else:
                                contact.write({'office_id': json.loads(post_response.decode('utf-8'))['id'] })

                else:
                    raise UserWarning('Token is missing. Please Generate Token ')

            except Exception as e:
                raise ValidationError(_(str(e)))

        else:
            print('token is not Founded! Please  generate the token by follow the given instructions in apps detail')

    def import_contacts(self):
        """
        This is for importing contacts to office 365
        :return:
        """
        if self.env.user.token:
            try:
                if self.env.user.token:
                    if self.env.user.expires_in:
                        expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                        expires_in = expires_in + timedelta(seconds=3600)
                        nowDateTime = datetime.now()
                        if nowDateTime > expires_in:
                            self.generate_refresh_token()
                    count = 0
                    while True:

                        url = 'https://graph.microsoft.com/v1.0/me/contacts?$skip=' + str(count)

                        headers = {

                            'Host': 'outlook.office365.com',
                            'Authorization': 'Bearer {0}'.format(self.env.user.token),
                            'Accept': 'application/json',
                            'Content-Type': 'application/json',
                            'X-Target-URL': 'http://outlook.office.com',
                            'connection': 'keep-Alive'

                        }

                        response = requests.get(url, headers=headers).content
                        response = json.loads(response.decode('utf-8'))
                        if not response['value']:
                            break

                        office_contact_email = []
                        if 'value' in response:
                            for each_contact in response['value']:
                                if len(each_contact['emailAddresses']) > 0:
                                    if not self.env['res.partner'].search([('email', '=', each_contact['emailAddresses'][0]['address'])]):
                                        phone = None
                                        if len(each_contact['homePhones']) > 0:
                                            phone = each_contact['homePhones'][0]
                                        elif len(each_contact['businessPhones']) > 0:
                                            phone = each_contact['businessPhones'][0]

                                        self.env['res.partner'].create({
                                            'name': each_contact['displayName'],
                                            'office_id' : each_contact['id'],
                                            'email': each_contact['emailAddresses'][0]['address'],
                                            'company_name': each_contact['companyName'],
                                            'function': each_contact['jobTitle'],
                                            'mobile': each_contact['mobilePhone'],
                                            'phone': phone,
                                            'title' : each_contact['title'],
                                            'street': each_contact['homeAddress']['street'] if each_contact['homeAddress'] else None,
                                            'city': each_contact['homeAddress']['city'] if each_contact['homeAddress'] else None,
                                            'zip': each_contact['homeAddress']['postalCode'] if each_contact['homeAddress'] else None,
                                            'state_id': self.env['res.country.state'].search([('name', '=', each_contact['homeAddress']['state'])]).id if each_contact['homeAddress']  else None,
                                            'country_id': self.env['res.country'].search([('name', '=', each_contact['homeAddress']['countryOrRegion'])]).id if each_contact['homeAddress'] else None,
                                        })

                                elif each_contact['mobilePhone'] or len(each_contact['homePhones'])>0 or len(each_contact['businessPhones'])>0 :
                                    phone = None
                                    if len(each_contact['homePhones'])>0:
                                        phone = each_contact['homePhones'][0]
                                    elif len(each_contact['businessPhones'])>0:
                                        phone =each_contact['businessPhones'][0]

                                    if phone or each_contact['mobilePhone']:

                                        self.env['res.partner'].create({
                                            'name': each_contact['displayName'],
                                            'company_name': each_contact['companyName'],
                                            'function': each_contact['jobTitle'],
                                            'mobile': each_contact['mobilePhone'],
                                            'phone': phone,
                                            'street': each_contact['homeAddress']['street'] if each_contact[
                                                'homeAddress'] else None,
                                            'city': each_contact['homeAddress']['city'] if each_contact[
                                                'homeAddress'] else None,
                                            'zip': each_contact['homeAddress']['postalCode'] if each_contact[
                                                'homeAddress'] else None,
                                            'state_id': self.env['res.country.state'].search(
                                                [('name', '=', each_contact['homeAddress']['state'])]).id if each_contact[
                                                'homeAddress'] else None,
                                            'country_id': self.env['res.country'].search(
                                                [('name', '=', each_contact['homeAddress']['countryOrRegion'])]).id if
                                            each_contact['homeAddress'] else None,
                                        })

                        count +=10

                else:
                    raise UserWarning('Token is missing. Please Generate Token ')

            except Exception as e:
                raise ValidationError(_(str(e)))

        else:
            print('Sorry! Token is not founded.')

        # raise osv.except_osv(_("Success!"), (_("Contacts are Successfully exported!!")))

class CustomCustomer(models.Model):

    _inherit = 'res.partner'
    office_id = fields.Char('Office365 Id')








