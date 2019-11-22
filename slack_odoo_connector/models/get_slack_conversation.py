from odoo import models, fields, api, exceptions
from slackclient import SlackClient
from odoo.exceptions import UserError, AccessError
from datetime import datetime, timedelta
import re
import time
from email.utils import parsedate_tz, mktime_tz

_image_dataurl = re.compile(r'(data:image/[a-z]+?);base64,([a-z0-9+/]{3,}=*)([\'"])', re.I)


class AutoGetMessages(models.Model):
    _inherit = "base.automation"

    def auto_get_mesage(self):
        token = self.slack_token

        self.env.user.company_id.slack_token = self.slack_token

        client = SlackClient(token)
        partner_ids = []
        attachment_ids = []
        slack_channels = client.api_call("channels.list", exclude_archived=1)
        slack_channels = slack_channels["channels"]
        # self.import_slack_conversation()
        if slack_channels:
            if client.rtm_connect():
                while client.server.connected is True:
                    for data in client.rtm_read():
                        if "type" in data and data["type"] == "message":
                            if "client_message_id":
                                slack_member = client.api_call('users.info', user=data['user'])
                                if slack_member.get('ok'):
                                    member = slack_member['user']
                                    user_name = member['profile']['real_name']
                                    email = member['profile']['email']
                                    slack_channel = client.api_call('channels.info', channel=data['channel'])
                                    if slack_channel.get('ok'):
                                        channel = slack_channel['channel']
                                        ts = float(data['ts'])

                                        date_time = datetime.fromtimestamp(ts)
                                        channel_id = data['channel']
                                        chat = data['text'].strip("<@" + member['id'] + ">")

                                        ################################################
                                        recipient_partners = []
                                        channel_ids = []

                                        from_partner = self.env['res.partner'].search(
                                            [('email', "=", member['profile']['email'])])
                                        if not from_partner:
                                            from_partner = self.env['res.partner'].create({
                                                'email': member['profile']['email'],
                                                'name': member['profile']['real_name'],
                                            })
                                            recipient_partners.append(from_partner.id)
                                        from_partner = from_partner[0] if from_partner else from_partner
                                        channel_partner = self.env['mail.channel.partner'].search(
                                            [('partner_id', '=', from_partner.id), ('channel_id', 'not in', [1, 2])])

                                        channel_found = False
                                        for channel_prtnr in channel_partner:
                                            to_chanel_partner = self.env['mail.channel.partner'].search(
                                                [('partner_id', '=', from_partner.id),
                                                 ('channel_id', '=', channel_prtnr.channel_id.id),
                                                 ('channel_id', 'not in', [1, 2])])
                                            if to_chanel_partner:
                                                channel_found = True
                                                channel_partner = channel_prtnr
                                                break

                                        if not channel_found:

                                            if channel.get('name') == 'general':
                                                odoo_channel = self.env['mail.channel'].search(
                                                    [('name', '=', channel.get('name'))])
                                                if odoo_channel:

                                                    odoo_channel.write({'channel_id': channel.get('id'),
                                                                        'name': channel.get('name'),

                                                                        'alias_user_id': self.env.user.id
                                                                        })
                                                    channel_ids.append(odoo_channel.id)

                                                else:
                                                    odoo_channel = self.env['mail.channel'].create({
                                                        'channel_id': channel.get('id'),
                                                        'name': channel.get('name'),

                                                        'alias_user_id': self.env.user.id

                                                    })
                                                    channel_ids.append(odoo_channel.id)
                                            else:
                                                odoo_channel = self.env['mail.channel'].search(
                                                    [('name', '=', channel.get('name'))])

                                                if not odoo_channel:
                                                    odoo_channel = self.env['mail.channel'].create({
                                                        'channel_id': channel.get('id'),
                                                        'name': channel.get('name'),
                                                        'alias_user_id': self.env.user.id

                                                    })
                                                    channel_ids.append(odoo_channel.id)

                                            from_channel_partner = self.env['mail.channel.partner'].create({
                                                'member_id': member['id'],
                                                'partner_email': member['profile']['email'],
                                                'display_name': member['profile']['real_name'],
                                                'partner_id': from_partner.id,
                                                'channel_id': odoo_channel.id,
                                                'is_pinned': True,
                                            })

                                            odoo_partner = self.env['mail.channel.partner'].search(
                                                [('member_id', '=', self.env.user.id)])

                                            if not odoo_partner:
                                                self.env['mail.channel.partner'].create({
                                                    'member_id': self.env.user.id,
                                                    'partner_email': self.env.user.email,
                                                    'display_name': self.env.user.name,
                                                    'partner_id': self.env.user.id,
                                                    'channel_id': odoo_channel.id,
                                                    'is_pinned': True,
                                                })



                                        else:
                                            odoo_channel = self.env['mail.channel'].search(
                                                [('name', '=', channel.get('name'))])

                                            if not odoo_channel:
                                                odoo_channel = self.env['mail.channel'].create({
                                                    'channel_id': channel.get('id'),
                                                    'name': channel.get('name'),
                                                    'alias_user_id': self.env.user.id

                                                })
                                                channel_ids.append(channel_partner[0].channel_id.id)
                                            else:
                                                channel_ids.append(channel_partner[0].channel_id.id)

                                        mail_message = self.env['mail.message'].search(
                                            [('client_message_id', '=', data['client_msg_id'])])
                                        if mail_message:
                                            odoo_message = self.env['mail.message'].write({
                                                'subject': chat,
                                                'date': date_time,
                                                'body': chat,
                                                'client_message_id': data['client_msg_id'],
                                                'email_from': member['profile']['email'],
                                                'channel_ids': [[6, 0, channel_ids]],
                                                'partner_ids': [[6, 0, recipient_partners]],
                                                'attachment_ids': [[6, 0, attachment_ids]],
                                                'member_id': data['user'],
                                                'model': 'res.partner',
                                                'res_id': from_partner.id,
                                                'author_id': from_partner.id
                                            })
                                        else:
                                            odoo_message = self.env['mail.message'].create({
                                                'subject': chat,
                                                'date': date_time,
                                                'body': chat,
                                                'client_message_id': data['client_msg_id'],
                                                'email_from': member['profile']['email'],
                                                'channel_ids': [[6, 0, channel_ids]],
                                                'partner_ids': [[6, 0, recipient_partners]],
                                                'attachment_ids': [[6, 0, attachment_ids]],
                                                'member_id': data['user'],
                                                'model': 'res.partner',
                                                'res_id': from_partner.id,
                                                'author_id': from_partner.id
                                            })

                                        ################################################

                                print("client message")
                            else:
                                print('channel message')
                        elif "type" in data and data["type"] == "channel_created":
                            print(data)
                        elif "type" in data and data["type"] == "channel_joined":
                            print(data)
                        elif "type" in data and data['type'] == " member_joined_channel":
                            print(data)
            else:
                print("Connection Failed")





