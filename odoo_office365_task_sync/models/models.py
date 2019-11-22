# -*- coding: utf-8 -*-
import logging
import re
from openerp.exceptions import ValidationError
from openerp.osv import osv
from odoo import _, api, fields, models, modules, SUPERUSER_ID, tools
from odoo.exceptions import UserError, AccessError
import requests
import json
from datetime import datetime
import time
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
                raise osv.except_osv("Wrong Credentials!", "Please Check your Credentials and try again")
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
        raise osv.except_osv("Success!", "Successfully Activated!")


class Office365UserSettings(models.Model):
    _name = 'office.usersettings'

    login_url = fields.Char('Login URL', compute='_compute_url', readonly=True)
    code = fields.Char('code')
    field_name = fields.Char('office')
    token = fields.Char('Office_Token')

    def _compute_url(self):
        settings = self.env['office.settings'].search([])
        settings = settings[0] if settings else settings
        if settings:
            self.login_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize?' \
                             'client_id=%s&redirect_uri=%s&response_type=code&scope=openid+offline_access+' \
                             'Calendars.ReadWrite+Mail.ReadWrite+Mail.Send+User.ReadWrite+' \
                             'Tasks.ReadWrite+Contacts.ReadWrite' % (
                                settings.client_id, settings.redirect_url)

    def test_connection(self):
        try:
            settings = self.env['office.settings'].search([])
            settings = settings[0] if settings else settings
            if not settings.client_id or not settings.redirect_url or not settings.secret:
                raise osv.except_osv("Error!", "Please ask admin to add Office365 settings!")
            header = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            response = requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data='grant_type=authorization_code&code=' + self.code + '&redirect_uri=' +
                     settings.redirect_url + '&client_id=' + settings.client_id +
                     '&client_secret=' + settings.secret, headers=header).content

            if 'error' in json.loads(response.decode('utf-8')) and json.loads(response.decode('utf-8'))['error']:
                raise UserError('Invalid Credentials . Please! Check your credential'
                                ' and  regenerate the code and try again!')
            else:
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
                print("code=", self.code)
        except Exception as e:
            raise ValidationError(_(str(e)))

        raise osv.except_osv("Success!", "Token Generated!")


class CustomUser(models.Model):
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

    def _compute_url(self):
        self.login_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize?' \
                         'client_id=%s&redirect_uri=%s&response_type=code&scope=openid+offline_access+' \
                         'Calendars.ReadWrite+Mail.ReadWrite+Mail.Send+User.ReadWrite+' \
                         'Tasks.ReadWrite+Contacts.ReadWrite' % (
                            self.client_id, self.redirect_url)

    def getAttendee(self, attendees):
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
        if alarm.interval == 'minutes':
            return alarm[0].duration
        elif alarm.interval == "hours":
            return alarm[0].duration * 60
        elif alarm.interval == "days":
            return alarm[0].duration * 60 * 24

    def getdays(self, meeting):
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

    def getAttachment(self, task):
        if self.env.user.expires_in:
            expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
            expires_in = expires_in + timedelta(seconds=3600)
            nowDateTime = datetime.now()
            if nowDateTime > expires_in:
                self.generate_refresh_token()

        response = requests.get(
            'https://graph.microsoft.com/beta/me/outlook/tasks/'+task['id']+'/attachments',
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
    def auto_import_tasks(self):
        print("###########################", self.env.user.name)
        self.import_tasks()

    @api.model
    def auto_export_tasks(self):
        print("###########################", self.env.user.name)
        self.export_tasks()

    def import_tasks(self):
        if self.env.user.token:
            try:
                if self.env.user.expires_in:
                    expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                    expires_in = expires_in + timedelta(seconds=3600)
                    nowDateTime = datetime.now()
                    if nowDateTime > expires_in:
                        self.generate_refresh_token()

                response = requests.get(
                    'https://graph.microsoft.com/beta/me/outlook/tasks',
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Content-type': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    }).content
                if 'value' not in json.loads((response.decode('utf-8'))).keys():
                    raise osv.except_osv(response)
                tasks = json.loads((response.decode('utf-8')))['value']
                partner_model = self.env['ir.model'].search([('model', '=', 'res.partner')])
                partner = self.env['res.partner'].search([('email', '=', self.env.user.email)])
                activity_type = self.env['mail.activity.type'].search([('name', '=', 'Todo')])
                if partner_model:
                    self.env.user.is_task_sync_on = True
                    self.env.cr.commit()
                    for task in tasks:
                        attachments_act = None
                        if task['hasAttachments']:
                            attachments_act = self.getAttachment(task)
                        if not self.env['mail.activity'].search([('office_id', '=', task['id'])]) and\
                                task['status'] != 'completed':
                            if 'dueDateTime' in task:
                                if task['dueDateTime'] is None:
                                    continue
                            else:
                                continue

                            self.env['mail.activity'].create({
                                'res_id': partner[0].id,
                                'activity_type_id': activity_type.id,
                                'summary': task['subject'],
                                'date_deadline': (
                                    datetime.strptime(task['dueDateTime']['dateTime'][:-16], '%Y-%m-%dT')).strftime(
                                    '%Y-%m-%d'),
                                'note': task['body']['content'],
                                'res_model_id': partner_model.id,
                                'office_id': task['id'],
                            })
                        elif self.env['mail.activity'].search([('office_id', '=', task['id'])]) and\
                                task['status'] != 'completed':
                            activity = self.env['mail.activity'].search([('office_id', '=', task['id'])])[0]
                            activity.write({
                                'res_id': partner[0].id,
                                'activity_type_id': activity_type.id,
                                'summary': task['subject'],
                                'date_deadline': (
                                    datetime.strptime(task['dueDateTime']['dateTime'][:-16], '%Y-%m-%dT')).strftime(
                                    '%Y-%m-%d'),
                                'note': task['body']['content'],
                                'res_model_id': partner_model.id,
                                'office_id': task['id'],
                            })
                        elif self.env['mail.activity'].search([('office_id', '=', task['id'])]) and\
                                task['status'] == 'completed':
                            activity = self.env['mail.activity'].search([('office_id', '=', task['id'])])[0]
                            activity.unlink()
                        self.env.cr.commit()

                odoo_activities = self.env['mail.activity'].search(
                    [('office_id', '!=', None), ('res_id', '=', self.env.user.partner_id.id)])
                task_ids = [task['id'] for task in tasks]
                for odoo_activity in odoo_activities:
                    if odoo_activity.office_id not in task_ids:
                        odoo_activity.unlink()
                        self.env.cr.commit()
                self.env.user.is_task_sync_on = False
                self.env.cr.commit()

            except Exception as e:
                self.env.user.is_task_sync_on = False
                self.env.cr.commit()
                raise ValidationError(_(str(e)))

        else:
            raise osv.except_osv('Token is missing!', 'Please ! Generate Token and try Again')

    def export_tasks(self):
        if self.env.user.token:
            if self.env.user.expires_in:
                expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                expires_in = expires_in + timedelta(seconds=3600)
                nowDateTime = datetime.now()
                if nowDateTime > expires_in:
                    self.generate_refresh_token()

            odoo_activities = self.env['mail.activity'].search([('res_id', '=', self.env.user.partner_id.id)])
            for activity in odoo_activities:
                url = 'https://graph.microsoft.com/beta/me/outlook/tasks'
                if activity.office_id:
                    url += '/' + activity.office_id

                data = {
                    'subject': activity.summary if activity.summary else activity.note,
                    "body": {
                        "contentType": "html",
                        "content": activity.note
                    },
                    "dueDateTime": {
                        "dateTime": str(activity.date_deadline) + 'T00:00:00Z',
                        "timeZone": "UTC"
                    },
                }
                if activity.office_id:
                    response = requests.patch(
                        url, data=json.dumps(data),
                        headers={
                            'Host': 'outlook.office.com',
                            'Authorization': 'Bearer {0}'.format(self.env.user.env.user.token),
                            'Accept': 'application/json',
                            'Content-Type': 'application/json',
                            'X-Target-URL': 'http://outlook.office.com',
                            'connection': 'keep-Alive'
                        }).content
                else:
                    response = requests.post(
                        url, data=json.dumps(data),
                        headers={
                            'Host': 'outlook.office.com',
                            'Authorization': 'Bearer {0}'.format(self.env.user.token),
                            'Accept': 'application/json',
                            'Content-Type': 'application/json',
                            'X-Target-URL': 'http://outlook.office.com',
                            'connection': 'keep-Alive'
                        }).content

                    if 'id' not in json.loads((response.decode('utf-8'))).keys():
                        raise osv.except_osv(_("Error!"), (_(response["error"])))
                    activity.office_id = json.loads((response.decode('utf-8')))['id']
                self.env.cr.commit()

    def generate_refresh_token(self):

        if self.env.user.refresh_token:
            settings = self.env['office.settings'].search([])
            settings = settings[0] if settings else settings
            if not settings.client_id or not settings.redirect_url or not settings.secret:
                raise osv.except_osv("Error!", "Please ask admin to add Office365 settings!")
            header = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            response = requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data='grant_type=refresh_token&refresh_token=' + self.env.user.refresh_token +
                     '&redirect_uri=' + settings.redirect_url + '&client_id=' + settings.client_id +
                     '&client_secret=' + settings.secret, headers=header).content
            response = json.loads((str(response)[2:])[:-1])
            if 'access_token' not in response:
                response["error_description"] = response["error_description"].replace("\\r\\n", " ")
                raise osv.except_osv(_("Error!"), (_(response["error"] + " " + response["error_description"])))
            else:
                self.env.user.token = response['access_token']
                self.env.user.refresh_token = response['refresh_token']
                self.env.user.expires_in = int(round(time.time() * 1000))


class CustomActivity(models.Model):
    _inherit = 'mail.activity'

    office_id = fields.Char('Office365 Id')

    @api.model
    def create(self, values):
        if self.env.user.expires_in:
            expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
            expires_in = expires_in + timedelta(seconds=3600)
            nowDateTime = datetime.now()
            if nowDateTime > expires_in:
                self.generate_refresh_token()

        o365_id = None
        if self.env.user.office365_email and not self.env.user.is_task_sync_on and\
                values['res_id'] == self.env.user.partner_id.id:
            data = {
                'subject': values['summary'] if values['summary'] else values['note'],
                "body": {
                    "contentType": "html",
                    "content": values['note']
                },
                "dueDateTime": {
                    "dateTime": values['date_deadline'] + 'T00:00:00Z',
                    "timeZone": "UTC"
                },
            }
            response = requests.post(
                'https://graph.microsoft.com/beta/me/outlook/tasks', data=json.dumps(data),
                headers={
                    'Host': 'outlook.office.com',
                    'Authorization': 'Bearer {0}'.format(self.env.user.token),
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-Target-URL': 'http://outlook.office.com',
                    'connection': 'keep-Alive'
                }).content
            if 'id' in json.loads((response.decode('utf-8'))).keys():
                o365_id = json.loads((response.decode('utf-8')))['id']

        """
        original code!
        """

        activity = super(CustomActivity, self).create(values)
        self.env[activity.res_model].browse(activity.res_id).message_subscribe(
            partner_ids=[activity.user_id.partner_id.id])
        if activity.date_deadline <= fields.Date.today():
            self.env['bus.bus'].sendone(
                (self._cr.dbname, 'res.partner', activity.user_id.partner_id.id),
                {'type': 'activity_updated', 'activity_created': True})
        if o365_id:
            activity.office_id = o365_id
        return activity

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
                data='grant_type=refresh_token&refresh_token=' + self.env.user.refresh_token +
                     '&redirect_uri=' + settings.redirect_url + '&client_id=' + settings.client_id +
                     '&client_secret=' + settings.secret, headers=header).content

            response = json.loads((str(response)[2:])[:-1])
            if 'access_token' not in response:
                response["error_description"] = response["error_description"].replace("\\r\\n", " ")
                raise osv.except_osv("Error!", (response["error"] + " " + response["error_description"]))
            else:
                self.env.user.token = response['access_token']
                self.env.user.refresh_token = response['refresh_token']
                self.env.user.expires_in = int(round(time.time() * 1000))

    def unlink(self):
        for activity in self:
            if activity.office_id:
                response = requests.delete(
                    'https://graph.microsoft.com/beta/me/outlook/tasks/' + activity.office_id,
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    })
                if response.status_code != 204 and response.status_code != 404:
                    raise osv.except_osv(_("Office365 SYNC ERROR"), (_("Error: " + str(response.status_code))))
            if activity.date_deadline <= fields.Date.today():
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', activity.user_id.partner_id.id),
                    {'type': 'activity_updated', 'activity_deleted': True})
        return super(CustomActivity, self).unlink()
