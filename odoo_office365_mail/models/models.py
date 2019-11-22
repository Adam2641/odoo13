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

    def _compute_url(self):
        settings = self.env['office.settings'].search([])
        settings = settings[0] if settings else settings
        if settings:
            self.login_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=%s&redirect_uri=%s&response_type=code&scope=openid+offline_access+Calendars.ReadWrite+Mail.ReadWrite+Mail.Send+User.ReadWrite+Tasks.ReadWrite+Contacts.ReadWrite' % (
                settings.client_id, settings.redirect_url)

    def test_connection(self):

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

    @api.model
    def sync_customer_mail_scheduler(self):
        print("###########################", self.env.user.name)
        self.sync_customer_mail()

    def sync_customer_mail(self):
        try:
            self.env.cr.commit()
            self.sync_customer_inbox_mail()
            self.sync_customer_sent_mail()

        except Exception as e:
            self.env.cr.commit()
            raise ValidationError(_(str(e)))
        self.env.cr.commit()

    def sync_customer_inbox_mail(self):
        if self.env.user.token:
            try:
                if self.env.user.expires_in:
                    expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                    expires_in = expires_in + timedelta(seconds=3600)
                    nowDateTime = datetime.now()
                    if nowDateTime > expires_in:
                        self.generate_refresh_token()

                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/mailFolders',
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Accept': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    }).content
                if 'value' not in json.loads((response.decode('utf-8'))).keys():
                    raise osv.except_osv("Access TOken Expired!", " Please Regenerate Access Token !")
                folders = json.loads((response.decode('utf-8')))['value']
                inbox_id = [folder['id'] for folder in folders if folder['displayName'] == 'Inbox']
                if inbox_id:
                    inbox_id = inbox_id[0]
                    response = requests.get(
                        'https://graph.microsoft.com/v1.0/me/mailFolders/' + inbox_id + '/messages?$top=100&$count=true',
                        headers={
                            'Host': 'outlook.office.com',
                            'Authorization': 'Bearer {0}'.format(self.env.user.token),
                            'Accept': 'application/json',
                            'X-Target-URL': 'http://outlook.office.com',
                            'connection': 'keep-Alive'
                        }).content
                    if 'value' not in json.loads((response.decode('utf-8'))).keys():
                        raise osv.except_osv("Access TOken Expired!", " Please Regenerate Access Token !")

                    else:
                        messages = json.loads((response.decode('utf-8')))['value']
                        for message in messages:
                            if 'from' not in message.keys() or self.env['mail.mail'].search(
                                    [('office_id', '=', message['conversationId'])]) or self.env['mail.message'].search(
                                    [('office_id', '=', message['conversationId'])]):
                                continue

                            if 'address' not in message.get('from').get('emailAddress') or message['bodyPreview'] == "":
                                continue

                            attachment_ids = self.getAttachment(message)

                            from_partner = self.env['res.partner'].search(
                                [('email', "=", message['from']['emailAddress']['address'])])
                            if not from_partner:
                                continue
                            from_partner = from_partner[0] if from_partner else from_partner
                            # if from_partner:
                            #     from_partner = from_partner[0]
                            recipient_partners = []
                            channel_ids = []
                            for recipient in message['toRecipients']:
                                if recipient['emailAddress']['address'].lower() == self.env.user.office365_email.lower() or \
                                        recipient['emailAddress'][
                                            'address'].lower() == self.env.user.office365_id_address.lower():
                                    to_user = self.env['res.users'].search(
                                        [('id', "=", self._uid)])
                                else:
                                    to = recipient['emailAddress']['address']
                                    to_user = self.env['res.users'].search(
                                        [('office365_id_address', "=", to)])
                                    to_user = to_user[0] if to_user else to_user

                                if to_user:
                                    to_partner = to_user.partner_id
                                    recipient_partners.append(to_partner.id)
                            date = datetime.strptime(message['sentDateTime'], "%Y-%m-%dT%H:%M:%SZ")
                            self.env['mail.message'].create({
                                'subject': message['subject'],
                                'date': date,
                                'body': message['bodyPreview'],
                                'email_from': message['from']['emailAddress']['address'],
                                'partner_ids': [[6, 0, recipient_partners]],
                                'attachment_ids': [[6, 0, attachment_ids]],
                                'office_id': message['conversationId'],
                                'author_id': from_partner.id,
                                'model': 'res.partner',
                                'res_id': from_partner.id
                            })
                            self.env.cr.commit()
            except Exception as e:
                # self.env.user.send_mail_flag = True
                raise ValidationError(_(str(e)))

    def sync_customer_sent_mail(self):
        """
        :return:
        """
        if self.env.user.token:
            try:
                if self.env.user.expires_in:
                    expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                    expires_in = expires_in + timedelta(seconds=3600)
                    nowDateTime = datetime.now()
                    if nowDateTime > expires_in:
                        self.generate_refresh_token()

                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/mailFolders',
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Accept': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    }).content
                if 'value' not in json.loads((response.decode('utf-8'))).keys():
                    raise osv.except_osv("Access Token Expired!", " Please Regenerate Access Token !")
                else:
                    folders = json.loads((response.decode('utf-8')))['value']
                    sentbox_folder_id = [folder['id'] for folder in folders if folder['displayName'] == 'Sent Items']
                    if sentbox_folder_id:
                        sentbox_id = sentbox_folder_id[0]
                        response = requests.get(
                            'https://graph.microsoft.com/v1.0/me/mailFolders/' + sentbox_id + '/messages?$top=100000&$count=true',
                            headers={
                                'Host': 'outlook.office.com',
                                'Authorization': 'Bearer {0}'.format(self.env.user.token),
                                'Accept': 'application/json',
                                'X-Target-URL': 'http://outlook.office.com',
                                'connection': 'keep-Alive'
                            }).content
                        if 'value' not in json.loads((response.decode('utf-8'))).keys():

                            raise osv.except_osv("Access Token Expired!", " Please Regenerate Access Token !")
                        else:
                            messages = json.loads((response.decode('utf-8')))['value']
                            for message in messages:

                                if 'from' not in message.keys() or self.env['mail.mail'].search(
                                        [('office_id', '=', message['conversationId'])]) or self.env['mail.message'].search(
                                        [('office_id', '=', message['conversationId'])]):
                                    continue

                                if message['bodyPreview'] == "":
                                    continue

                                attachment_ids = self.getAttachment(message)
                                if message['from']['emailAddress'][
                                    'address'].lower() == self.env.user.office365_email.lower() or \
                                        message['from']['emailAddress'][
                                            'address'].lower() == self.env.user.office365_id_address.lower():
                                    email_from = self.env.user.email
                                else:
                                    email_from = message['from']['emailAddress']['address']

                                from_user = self.env['res.users'].search(
                                    [('id', "=", self._uid)])
                                if from_user:
                                    from_partner = from_user.partner_id
                                else:
                                    continue

                                channel_ids = []
                                for recipient in message['toRecipients']:

                                    to_partner = self.env['res.partner'].search(
                                        [('email', "=", recipient['emailAddress']['address'])])
                                    to_partner = to_partner[0] if to_partner else to_partner

                                    if not to_partner:
                                        continue
                                    date = datetime.strptime(message['sentDateTime'], "%Y-%m-%dT%H:%M:%SZ")
                                    self.env['mail.message'].create({
                                        'subject': message['subject'],
                                        'date': date,
                                        'body': message['bodyPreview'],
                                        'email_from': email_from,
                                        'partner_ids': [[6, 0, [to_partner.id]]],
                                        'attachment_ids': [[6, 0, attachment_ids]],
                                        'office_id': message['conversationId'],
                                        'author_id': from_partner.id,
                                        'model': 'res.partner',
                                        'res_id': to_partner.id
                                    })
                                    self.env.cr.commit()

            except Exception as e:
                raise ValidationError(_(str(e)))

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
        else:
            print('Token is missing')


class CustomMeeting(models.Model):
    """
    adding office365 event ID to ODOO meeting to remove duplication and facilitate updation
    """
    _inherit = 'calendar.event'
    office_id = fields.Char('Office365 Id')


class CustomMessageInbox(models.Model):
    """
    Email will store in mail.message class so that's why we need office_id
    """
    _inherit = 'mail.message'

    office_id = fields.Char('Office Id')


class CustomMessage(models.Model):

    # Email will be sent to the recipient of the message.

    _inherit = 'mail.mail'
    office_id = fields.Char('Office Id')
    # from_office = fields.Char(string= 'check')

    @api.model
    def create(self, values):
        """
        overriding create message to send email on message creation
        :param values:
        :return:
        """
        ################## New Code ##################
        ################## New Code ##################
        o365_id = None
        conv_id = None
        context = self._context

        current_uid = context.get('uid')

        user = self.env['res.users'].browse(current_uid)
        if user.send_mail_flag:
            if user.token:
                if user.expires_in:
                    expires_in = datetime.fromtimestamp(int(user.expires_in) / 1e3)
                    expires_in = expires_in + timedelta(seconds=3600)
                    nowDateTime = datetime.now()
                    if nowDateTime > expires_in:
                        self.generate_refresh_token()
            if 'mail_message_id' in values:
                email_obj = self.env['mail.message'].search([('id', '=', values['mail_message_id'])])
                partner_id = values['recipient_ids'][0][1]
                partner_obj = self.env['res.partner'].search([('id', '=', partner_id)])

                new_data = {
                            "subject": values['subject'] if values['subject'] else email_obj.body,
                            # "importance": "high",
                            "body": {
                                "contentType": "HTML",
                                "content": email_obj.body
                            },
                            "toRecipients": [
                                {
                                    "emailAddress": {
                                        "address": partner_obj.email
                                    }
                                }
                            ]
                        }

                response = requests.post(
                    'https://graph.microsoft.com/v1.0/me/messages', data=json.dumps(new_data),
                                        headers={
                                            'Host': 'outlook.office.com',
                                            'Authorization': 'Bearer {0}'.format(user.token),
                                            'Accept': 'application/json',
                                            'Content-Type': 'application/json',
                                            'X-Target-URL': 'http://outlook.office.com',
                                            'connection': 'keep-Alive'
                                        })
                if 'conversationId' in json.loads((response.content.decode('utf-8'))).keys():
                    conv_id = json.loads((response.content.decode('utf-8')))['conversationId']

                if 'id' in json.loads((response.content.decode('utf-8'))).keys():

                    o365_id = json.loads((response.content.decode('utf-8')))['id']
                    if email_obj.attachment_ids:
                        for attachment in self.getAttachments(email_obj.attachment_ids):
                            attachment_response = requests.post(
                                'https://graph.microsoft.com/beta/me/messages/' + o365_id + '/attachments',
                                data=json.dumps(attachment),
                                headers={
                                    'Host': 'outlook.office.com',
                                    'Authorization': 'Bearer {0}'.format(user.token),
                                    'Accept': 'application/json',
                                    'Content-Type': 'application/json',
                                    'X-Target-URL': 'http://outlook.office.com',
                                    'connection': 'keep-Alive'
                                })
                    send_response = requests.post(
                        'https://graph.microsoft.com/v1.0/me/messages/' + o365_id + '/send',
                        headers={
                            'Host': 'outlook.office.com',
                            'Authorization': 'Bearer {0}'.format(user.token),
                            'Accept': 'application/json',
                            'Content-Type': 'application/json',
                            'X-Target-URL': 'http://outlook.office.com',
                            'connection': 'keep-Alive'
                        })

                    message = super(CustomMessage, self).create(values)
                    message.email_from = None

                    if conv_id:
                        message.office_id = conv_id

                    return message

            else:
                return super(CustomMessage, self).create(values)
        else:
            return super(CustomMessage, self).create(values)

    def getAttachments(self, attachment_ids):
        attachment_list = []
        if attachment_ids:
            # attachments = self.env['ir.attachment'].browse([id[0] for id in attachment_ids])
            attachments = self.env['ir.attachment'].search([('id', 'in', [i.id for i in attachment_ids])])
            for attachment in attachments:
                attachment_list.append({
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": attachment.name,
                    "contentBytes": attachment.datas.decode("utf-8")
                })
        return attachment_list

    def generate_refresh_token(self):
        context = self._context

        current_uid = context.get('uid')

        user = self.env['res.users'].browse(current_uid)
        if user.refresh_token:
            settings = self.env['office.settings'].search([])
            settings = settings[0] if settings else settings

            if not settings.client_id or not settings.redirect_url or not settings.secret:
                raise osv.except_osv(_("Error!"), (_("Please ask admin to add Office365 settings!")))
            header = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            response = requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data='grant_type=refresh_token&refresh_token=' + user.refresh_token + '&redirect_uri=' + settings.redirect_url + '&client_id=' + settings.client_id + '&client_secret=' + settings.secret
                , headers=header).content

            response = json.loads((str(response)[2:])[:-1])
            if 'access_token' not in response:
                response["error_description"] = response["error_description"].replace("\\r\\n", " ")
                raise osv.except_osv(_("Error!"), (_(response["error"] + " " + response["error_description"])))
            else:
                user.token = response['access_token']
                user.refresh_token = response['refresh_token']
                user.expires_in = int(round(time.time() * 1000))
                self.env.cr.commit()
