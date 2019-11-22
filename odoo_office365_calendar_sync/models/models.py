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
    event_del_flag = fields.Boolean(string='Delete event from office365. ', default=False)
    # is_task_sync_on = fields.Boolean('is sync in progress', default=False)

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
        :return:ODoo
        """
        try:
            web = webbrowser.open(self.login_url)

        except Exception as e:
            raise ValidationError(_(str(e)))

        # raise osv.except_osv(_("Success!"), (_("Token Generated!")))

    def auto_import_calendar(self):
        print("###########################",self.env.user.name)
        self.import_calendar()

    @api.model
    def auto_export_calendar(self):
        print("###########################", self.env.user.name)
        self.export_calendar()

    # @api.one
    def import_calendar(self):
        """
        this function imports Office 365  Calendar to Odoo Calendar

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
                    'https://graph.microsoft.com/v1.0/me/events',
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Accept': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    }).content
                if 'value' not in json.loads((response.decode('utf-8'))).keys():
                    raise osv.except_osv(response)
                events = json.loads((response.decode('utf-8')))['value']
                for event in events:

                    # if 'showAs' in event:
                    odoo_meeting = self.env['calendar.event'].search([("office_id", "=", event['id'])])
                    if odoo_meeting:
                        odoo_meeting.write({
                            'office_id': event['id'],
                            'name': event['subject'],
                            "description": event['bodyPreview'],
                            'location': (event['location']['address']['city'] + ', ' + event['location']['address'][
                                'countryOrRegion']) if 'address' in event['location'] and 'city' in event['location'][
                                'address'].keys() else "",
                            'start': datetime.strptime(event['start']['dateTime'][:-8], '%Y-%m-%dT%H:%M:%S'),
                            'stop': datetime.strptime(event['end']['dateTime'][:-8], '%Y-%m-%dT%H:%M:%S'),
                            'allday': event['isAllDay'],
                            'show_as': event['showAs'] if 'showAs' in event and (
                                        event['showAs'] == 'free' or event['showAs'] == 'busy') else None,
                            'recurrency': True if event['recurrence'] else False,
                            'end_type': 'end_date' if event['recurrence'] else "",
                            'rrule_type': event['recurrence']['pattern']['type'].replace('absolute', '').lower() if
                            event[
                                'recurrence'] else "",
                            'count': event['recurrence']['range']['numberOfOccurrences'] if event['recurrence'] else "",
                            'final_date': datetime.strptime(event['recurrence']['range']['endDate'],
                                                            '%Y-%m-%d').strftime(
                                '%Y-%m-%d') if event['recurrence'] else None,
                            'mo': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                'pattern'].keys() and 'monday' in event['recurrence']['pattern'][
                                              'daysOfWeek'] else False,
                            'tu': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                'pattern'].keys() and 'tuesday' in event['recurrence']['pattern'][
                                              'daysOfWeek'] else False,
                            'we': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                'pattern'].keys() and 'wednesday' in event['recurrence']['pattern'][
                                              'daysOfWeek'] else False,
                            'th': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                'pattern'].keys() and 'thursday' in event['recurrence']['pattern'][
                                              'daysOfWeek'] else False,
                            'fr': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                'pattern'].keys() and 'friday' in event['recurrence']['pattern'][
                                              'daysOfWeek'] else False,
                            'sa': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                'pattern'].keys() and 'saturday' in event['recurrence']['pattern'][
                                              'daysOfWeek'] else False,
                            'su': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                                'pattern'].keys() and 'sunday' in event['recurrence']['pattern'][
                                              'daysOfWeek'] else False,
                        })
                        partner_ids = []
                        attendee_ids = []
                        for attendee in event['attendees']:
                            partner = self.env['res.partner'].search(
                                [('email', "=", attendee['emailAddress']['address'])])
                            if not partner:
                                partner = self.env['res.partner'].create({
                                    'name': attendee['emailAddress']['name'],
                                    'email': attendee['emailAddress']['address'],
                                })
                            partner_ids.append(partner[0].id)
                            odoo_attendee = self.env['calendar.attendee'].create({
                                'partner_id': partner[0].id,
                                'event_id': odoo_meeting.id,
                                'email': attendee['emailAddress']['address'],
                                'common_name': attendee['emailAddress']['name'],

                            })
                            attendee_ids.append(odoo_attendee.id)
                            if not event['attendees']:
                                odoo_attendee = self.env['calendar.attendee'].create({
                                'partner_id': self.env.user.partner_id.id,
                                'event_id': odoo_meeting.id,
                                'email': self.env.user.partner_id.email,
                                'common_name': self.env.user.partner_id.name,

                                })
                            attendee_ids.append(odoo_attendee.id)
                            partner_ids.append(self.env.user.partner_id.id)
                            odoo_meeting.write({
                            'attendee_ids': [[6, 0, attendee_ids]],
                            'partner_ids': [[6, 0, partner_ids]]
                        })
                            self.env.cr.commit()
                        # odoo_meeting.unlink()
                        # self.env.cr.commit()
                    else:
                        odoo_event = self.env['calendar.event'].create({
                        'office_id': event['id'],
                        'name': event['subject'],
                        "description": event['bodyPreview'],
                        'location': (event['location']['address']['city'] + ', ' + event['location']['address'][
                            'countryOrRegion']) if 'address' in event['location'] and 'city' in event['location'][
                            'address'].keys() else "",
                        'start':datetime.strptime(event['start']['dateTime'][:-8], '%Y-%m-%dT%H:%M:%S'),
                        'stop': datetime.strptime(event['end']['dateTime'][:-8], '%Y-%m-%dT%H:%M:%S'),
                        'allday': event['isAllDay'],
                        'show_as': event['showAs'] if 'showAs' in event and (event['showAs'] == 'free' or event['showAs'] == 'busy') else None,
                        'recurrency': True if event['recurrence'] else False,
                        'end_type': 'end_date' if event['recurrence'] else "",
                        'rrule_type': event['recurrence']['pattern']['type'].replace('absolute', '').lower() if
                        event[
                            'recurrence'] else "",
                        'count': event['recurrence']['range']['numberOfOccurrences'] if event['recurrence'] else "",
                        'final_date': datetime.strptime(event['recurrence']['range']['endDate'],
                                                        '%Y-%m-%d').strftime(
                            '%Y-%m-%d') if event['recurrence'] else None,
                        'mo': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                            'pattern'].keys() and 'monday' in event['recurrence']['pattern'][
                                          'daysOfWeek'] else False,
                        'tu': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                            'pattern'].keys() and 'tuesday' in event['recurrence']['pattern'][
                                          'daysOfWeek'] else False,
                        'we': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                            'pattern'].keys() and 'wednesday' in event['recurrence']['pattern'][
                                          'daysOfWeek'] else False,
                        'th': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                            'pattern'].keys() and 'thursday' in event['recurrence']['pattern'][
                                          'daysOfWeek'] else False,
                        'fr': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                            'pattern'].keys() and 'friday' in event['recurrence']['pattern'][
                                          'daysOfWeek'] else False,
                        'sa': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                            'pattern'].keys() and 'saturday' in event['recurrence']['pattern'][
                                          'daysOfWeek'] else False,
                        'su': True if event['recurrence'] and 'daysOfWeek' in event['recurrence'][
                            'pattern'].keys() and 'sunday' in event['recurrence']['pattern'][
                                          'daysOfWeek'] else False,
                        })
                        partner_ids = []
                        attendee_ids = []
                        for attendee in event['attendees']:
                            partner = self.env['res.partner'].search(
                                [('email', "=", attendee['emailAddress']['address'])])
                            if not partner:
                                partner = self.env['res.partner'].create({
                                    'name': attendee['emailAddress']['name'],
                                    'email': attendee['emailAddress']['address'],
                                })
                            partner_ids.append(partner[0].id)
                            odoo_attendee = self.env['calendar.attendee'].create({
                                'partner_id': partner[0].id,
                                'event_id': odoo_event.id,
                                'email': attendee['emailAddress']['address'],
                                'common_name': attendee['emailAddress']['name'],

                            })
                            attendee_ids.append(odoo_attendee.id)
                            if not event['attendees']:
                                odoo_attendee = self.env['calendar.attendee'].create({
                                'partner_id': self.env.user.partner_id.id,
                                'event_id': odoo_event.id,
                                'email': self.env.user.partner_id.email,
                                'common_name': self.env.user.partner_id.name,

                            })
                            attendee_ids.append(odoo_attendee.id)
                            partner_ids.append(self.env.user.partner_id.id)
                            odoo_event.write({
                            'attendee_ids': [[6, 0, attendee_ids]],
                            'partner_ids': [[6, 0, partner_ids]]
                            })
                            self.env.cr.commit()


            except Exception as e:
                print(e)

        else:
            raise osv.except_osv(_("Token is missing!"), (_(" Token is not founded! ")))

    # @api.one
    def export_calendar(self):
        """
        this function export  odoo calendar event  to office 365 Calendar

        """
        if self.env.user.token:
            try:
                if self.env.user.expires_in:
                    expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                    expires_in = expires_in + timedelta(seconds=3600)
                    nowDateTime = datetime.now()
                    if nowDateTime > expires_in:
                        self.generate_refresh_token()

                header = {
                    'Authorization': 'Bearer {0}'.format(self.env.user.token),
                    'Content-Type': 'application/json'
                }
                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/calendars',
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Accept': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    }).content
                if 'value' not in json.loads((response.decode('utf-8'))).keys():
                    raise osv.except_osv(("Access Token Expired!"), (" Please Regenerate Access Token !"))
                calendars = json.loads((response.decode('utf-8')))['value']
                calendar_id = calendars[0]['id']

                meetings = self.env['calendar.event'].search([("office_id", "=", False),("create_uid", '=', self.env.user.id)])
                added_meetings = self.env['calendar.event'].search([("office_id", "!=", False),("create_uid", '=', self.env.user.id)])

                added = []
                for meeting in meetings:
                    temp = meeting
                    id = str(meeting.id).split('-')[0]
                    metngs = [meeting for meeting in meetings if id in str(meeting.id)]
                    index = len(metngs)
                    meeting = metngs[index - 1]
                    if meeting.start is not None:
                        metting_start = meeting.start.strftime(
                            '%Y-%m-%d T %H:%M:%S') if meeting.start else meeting.start
                    else:
                        metting_start = None

                    payload = {
                        "subject": meeting.name,
                        "attendees": self.getAttendee(meeting.attendee_ids),
                        'reminderMinutesBeforeStart': self.getTime(meeting.alarm_ids),
                        "start": {
                            "dateTime": meeting.start.strftime(
                                '%Y-%m-%d T %H:%M:%S') if meeting.start else meeting.start,
                            "timeZone": "UTC"
                        },
                        "end": {
                            "dateTime": meeting.stop.strftime('%Y-%m-%d T %H:%M:%S') if meeting.stop else meeting.stop,
                            "timeZone": "UTC"
                        },
                        "showAs": meeting.show_as,
                        "location": {
                            "displayName": meeting.location if meeting.location else "",
                        },

                    }
                    if meeting.recurrency:
                        payload.update({"recurrence": {
                            "pattern": {
                                "daysOfWeek": self.getdays(meeting),
                                "type": (
                                            'Absolute' if meeting.rrule_type != "weekly" and meeting.rrule_type != "daily" else "") + meeting.rrule_type,
                                "interval": meeting.interval,
                                "month": int(meeting.start.month),  # meeting.start[5] + meeting.start[6]),
                                "dayOfMonth": int(meeting.start.day),  # meeting.start[8] + meeting.start[9]),
                                "firstDayOfWeek": "sunday",
                                # "index": "first"
                            },
                            "range": {
                                "type": "endDate",
                                "startDate": str(
                                    str(meeting.start.year) + "-" + str(meeting.start.month) + "-" + str(meeting.start.day)),
                                "endDate": str(meeting.final_date),
                                "recurrenceTimeZone": "UTC",
                                "numberOfOccurrences": meeting.count,
                            }
                        }})
                    if meeting.name not in added:
                        response = requests.post(
                            'https://graph.microsoft.com/v1.0/me/calendars/' + calendar_id + '/events',
                            headers=header, data=json.dumps(payload)).content
                        if 'id' in json.loads((response.decode('utf-8'))):
                            temp.write({
                                'office_id': json.loads((response.decode('utf-8')))['id']
                            })
                            self.env.cr.commit()
                            if meeting.recurrency:
                                added.append(meeting.name)

            except Exception as e:
                raise ValidationError(_(str(e)))


        # raise osv.except_osv(_("Success!"), (_(" Sync Successfully !")))

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


class CustomMeeting(models.Model):
    """
    adding office365 event ID to ODOO meeting to remove duplication and facilitate updation
    """
    _inherit = 'calendar.event'


    office_id = fields.Char('Office365 Id')

    @api.model
    def create(self,values):
        message = super(CustomMeeting, self).create(values)
        if 'office_id' in values and values['office_id']:
            return message

        elif self.env.user.token:
            try:
                if self.env.user.expires_in:
                    expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                    expires_in = expires_in + timedelta(seconds=3600)
                    nowDateTime = datetime.now()
                    if nowDateTime > expires_in:
                        self.env['res.users'].generate_refresh_token()

                header = {
                    'Authorization': 'Bearer {0}'.format(self.env.user.token),
                    'Content-Type': 'application/json'
                }
                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/calendars',
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Accept': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    }).content
                if 'value' not in json.loads((response.decode('utf-8'))).keys():
                    raise osv.except_osv(("Access Token Expired!"), (" Please Regenerate Access Token !"))
                calendars = json.loads((response.decode('utf-8')))['value']
                calendar_id = calendars[0]['id']

                meetings = message #self.env['calendar.event'].search(
                #     [("office_id", "=", False), ("create_uid", '=', self.env.user.id)])
                # added_meetings = self.env['calendar.event'].search(
                #     [("office_id", "!=", False), ("create_uid", '=', self.env.user.id)])

                added = []
                for meeting in meetings:
                    temp = meeting
                    id = str(meeting.id).split('-')[0]
                    metngs = [meeting for meeting in meetings if id in str(meeting.id)]
                    index = len(metngs)
                    meeting = metngs[index - 1]
                    if meeting.start is not None:
                        metting_start = meeting.start.strftime(
                            '%Y-%m-%d T %H:%M:%S') if meeting.start else meeting.start
                    else:
                        metting_start = None

                    payload = {
                        "subject": meeting.name,
                        "attendees": self.env['res.users'].getAttendee(meeting.attendee_ids),
                        'reminderMinutesBeforeStart': self.env['res.users'].getTime(meeting.alarm_ids),
                        "start": {
                            "dateTime": meeting.start.strftime(
                                '%Y-%m-%d T %H:%M:%S') if meeting.start else meeting.start,
                            "timeZone": "UTC"
                        },
                        "end": {
                            "dateTime": meeting.stop.strftime('%Y-%m-%d T %H:%M:%S') if meeting.stop else meeting.stop,
                            "timeZone": "UTC"
                        },
                        "showAs": meeting.show_as,
                        "location": {
                            "displayName": meeting.location if meeting.location else "",
                        },

                    }
                    if meeting.recurrency:
                        payload.update({"recurrence": {
                            "pattern": {
                                "daysOfWeek": self.env['res.users'].getdays(meeting),
                                "type": (
                                            'Absolute' if meeting.rrule_type != "weekly" and meeting.rrule_type != "daily" else "") + meeting.rrule_type,
                                "interval": meeting.interval,
                                "month": int(meeting.start.month),  # meeting.start[5] + meeting.start[6]),
                                "dayOfMonth": int(meeting.start.day),  # meeting.start[8] + meeting.start[9]),
                                "firstDayOfWeek": "sunday",
                                # "index": "first"
                            },
                            "range": {
                                "type": "endDate",
                                "startDate": str(
                                    str(meeting.start.year) + "-" + str(meeting.start.month) + "-" + str(
                                        meeting.start.day)),
                                "endDate": str(meeting.final_date),
                                "recurrenceTimeZone": "UTC",
                                "numberOfOccurrences": meeting.count,
                            }
                        }})
                    if meeting.name not in added:
                        response = requests.post(
                            'https://graph.microsoft.com/v1.0/me/calendars/' + calendar_id + '/events',
                            headers=header, data=json.dumps(payload)).content
                        if 'id' in json.loads((response.decode('utf-8'))):
                            temp.write({
                                'office_id': json.loads((response.decode('utf-8')))['id']
                            })
                            self.env.cr.commit()
                            if meeting.recurrency:
                                added.append(meeting.name)

                return temp


            except Exception as e:
                raise ValidationError(_(str(e)))


    @api.multi
    def write(self,values):

        message = super(CustomMeeting, self).write(values)
        if self.env.user.token:

            try:
                if self.env.user.expires_in:
                    expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                    expires_in = expires_in + timedelta(seconds=3600)
                    nowDateTime = datetime.now()
                    if nowDateTime > expires_in:
                        self.env['res.users'].generate_refresh_token()

                header = {
                    'Authorization': 'Bearer {0}'.format(self.env.user.token),
                    'Content-Type': 'application/json'
                }
                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/calendars',
                    headers={
                        'Host': 'outlook.office.com',
                        'Authorization': 'Bearer {0}'.format(self.env.user.token),
                        'Accept': 'application/json',
                        'X-Target-URL': 'http://outlook.office.com',
                        'connection': 'keep-Alive'
                    }).content
                if 'value' not in json.loads((response.decode('utf-8'))).keys():
                    raise osv.except_osv(("Access Token Expired!"), (" Please Regenerate Access Token !"))
                calendars = json.loads((response.decode('utf-8')))['value']
                calendar_id = calendars[0]['id']

                meeting =values
                if self.office_id:

                    payload = {
                        "subject": meeting['name'] if 'name' in meeting else self.name,
                        "attendees": self.getAttendee(meeting['attendee_ids']) if 'attendee_ids' in meeting else self.env['res.users'].getAttendee(self.attendee_ids),
                        'reminderMinutesBeforeStart': self.getTime(meeting['alarm_ids']) if 'alarm_ids' in meeting else (self.env['res.users'].getTime(self.alarm_ids), ),
                        "start": {
                            "dateTime": datetime.strptime(str(meeting['start']), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d T %H:%M:%S') if 'start' in meeting else (self.start.strftime('%Y-%m-%d T %H:%M:%S') if self.start  else self.start),
                            "timeZone": "UTC"
                        },
                        "end": {
                            "dateTime": datetime.strptime(str(meeting['stop']), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d T %H:%M:%S') if 'stop' in meeting  else (self.stop.strftime('%Y-%m-%d T %H:%M:%S') if self.stop  else self.stop),
                            "timeZone": "UTC"
                        },
                        "showAs": meeting['show_as'] if 'show_as' in meeting else self.show_as,
                        "location": {
                            "displayName": meeting['location'] if 'location' in meeting else self.location,
                        },

                    }
                    if 'recurrency' in  meeting and meeting['recurrency']:
                        payload.update({"recurrence": {
                            "pattern": {
                                "daysOfWeek": self.getdays(meeting),
                                "type": (
                                            'Absolute' if meeting['rrule_type'] != "weekly" and meeting['rrule_type'] != "daily" else "") + meeting['rrule_type'] if('rrule_type' in meeting ) else self.rrule_type,
                                "interval": meeting['interval'] if 'interval' in meeting else self.interval,
                                "month": int(meeting['start'][5:7] if 'start' in meeting else self.start.month),  # meeting.start[5] + meeting.start[6]),
                                "dayOfMonth": int(meeting['start'][8:10] if 'start' in meeting else self.start.day),  # meeting.start[8] + meeting.start[9]),
                                "firstDayOfWeek": "sunday",
                                # "index": "first"
                            },
                            "range": {
                                "type": "endDate",
                                "startDate": str( meeting['start'][0:10] if 'start' in meeting  else
                                    str(self.start.year) + "-" + str(self.start.month) + "-" + str(
                                        self.start.day)),
                                "endDate": str(meeting['final_date'] if 'final_date' in meeting else self.final_date),
                                "recurrenceTimeZone": "UTC",
                                "numberOfOccurrences":meeting['count'] if  'count' in meeting else self.count,
                            }
                        }})

                    response = requests.patch(
                            'https://graph.microsoft.com/v1.0/me/calendars/' + calendar_id + '/events/' + self.office_id,
                            headers=header, data=json.dumps(payload)).content

                    self.env.cr.commit()
                    return message

            except Exception as e:
                raise ValidationError(_(str(e)))
            else:
                return message


    @api.multi
    def unlink(self):
        if self.office_id and self.env.user.event_del_flag:
            if self.env.user.expires_in:
                expires_in = datetime.fromtimestamp(int(self.env.user.expires_in) / 1e3)
                expires_in = expires_in + timedelta(seconds=3600)
                nowDateTime = datetime.now()
                if nowDateTime > expires_in:
                    self.env['res.users'].generate_refresh_token()
            header = {
                'Authorization': 'Bearer {0}'.format(self.env.user.token),
                'Content-Type': 'application/json'
            }

            response = requests.get(
                'https://graph.microsoft.com/v1.0/me/calendars',
                headers={
                    'Host': 'outlook.office.com',
                    'Authorization': 'Bearer {0}'.format(self.env.user.token),
                    'Accept': 'application/json',
                    'X-Target-URL': 'http://outlook.office.com',
                    'connection': 'keep-Alive'
                }).content
            if 'value' not in json.loads((response.decode('utf-8'))).keys():
                raise osv.except_osv(("Access Token Expired!"), (" Please Regenerate Access Token !"))
            calendars = json.loads((response.decode('utf-8')))['value']
            calendar_id = calendars[0]['id']
            response = requests.delete(
                'https://graph.microsoft.com/v1.0/me/calendars/' + calendar_id + '/events/' + self.office_id,
                headers=header)
            if response.status_code == 204:
                print('successfull deleted event ' + self.name)
                res = super(CustomMeeting, self).unlink(self)
                return res

        res = super(CustomMeeting, self).unlink(self)
        return res

    def getAttendee(self, attendees):
        """
        Get attendees from odoo and convert to attendees Office365 accepting
        :param attendees:
        :return: Office365 accepting attendees

        """
        attendee_list = []
        for attendee in attendees:
            if len(attendee)> 1 :

                partner = self.env['calendar.attendee'].search([('id','=',attendee[1])])
                attendee_list.append({
                    "status": {
                        "response": 'Accepted',
                        "time": datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
                    },
                    "type": "required",
                    "emailAddress": {
                        "address": partner.email,
                        "name": partner.display_name
                    }
                })
        return attendee_list

    def getdays(self, meeting):
        """
        Returns days of week the event will occure
        :param meeting:
        :return: list of days
        """
        days = []
        if 'su' in meeting :
            days.append("sunday")
        if 'mo' in meeting:
            days.append("monday")
        if 'tu' in meeting:
            days.append("tuesday")
        if 'we' in meeting:
            days.append("wednesday")
        if 'th' in meeting:
            days.append("thursday")
        if 'fr' in meeting:
            days.append("friday")
        if 'sa' in meeting:
            days.append("saturday")
        return days

    def getTime(self, alarm_ids):
        """
        Convert ODOO time to minutes as Office365 accepts time in minutes
        :param alarm:
        :return: time in minutes
        """
        alarm = self.env['calendar.alarm'].search([('id', '=', alarm_ids[0][2][0])])
        if alarm.interval == 'minutes':
            return alarm[0].duration
        elif alarm.interval == "hours":
            return alarm[0].duration * 60
        elif alarm.interval == "days":
            return alarm[0].duration * 60 * 24







