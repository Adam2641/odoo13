from odoo import models, fields, api, exceptions
from slackclient import SlackClient
from odoo.exceptions import UserError, AccessError
from openerp.osv import osv
from datetime import datetime , timedelta
import re

_image_dataurl = re.compile(r'(data:image/[a-z]+?);base64,([a-z0-9+/]{3,}=*)([\'"])', re.I)


class SlackCompanyAllUsers(models.Model):
    _name = 'slack.users'

    name = fields.Char(string="Name")
    email = fields.Char(string="Email")
    display_name = fields.Char(string="Display Name")
    user_id = fields.Char(string="User ID")
    user_ids = fields.Many2one('res.company')


class SlackCompanyAllGroups(models.Model):
    _name = 'slack.group'

    name = fields.Char(string="Name")
    group_ids = fields.Many2one('res.company')


class SlackAllUsers(models.Model):
    _name = 'slack.all.users'

    name = fields.Char(string="Name")
    email = fields.Char(string="Email")
    display_name = fields.Char(string="Display Name")
    user_id = fields.Char(string="User ID")
    user_ids = fields.Many2one('res.company')
    channel = fields.Char('Channel')


class SlackCompanyToken(models.Model):
    """
    This Class will store members and channels of slack
    """
    _inherit = 'res.company'

    slack_token = fields.Char()
    all_users_ids = fields.One2many('slack.users', 'user_ids', string="All Users")
    all_group_ids = fields.One2many('slack.group', 'group_ids', string="Channels")

    def slack_token_verify(self):

        """
        This method will verify slack token and create records of members and channels from slack to Odoo
        :return:
        """
        if self.slack_token:
            token = self.slack_token
            self.env.user.company_id.slack_token = self.slack_token

            sc = SlackClient(token)
            partner_ids = []
            attachment_ids = []
            slack_channels = sc.api_call("channels.list", exclude_archived=1)
            slack_channels = slack_channels["channels"]
            if slack_channels:
                self.all_group_ids.unlink()
                sg = []
                for channel in slack_channels:

                    slack_member = sc.api_call('users.list', channel=channel['id'])
                    if 'members' in slack_member:
                        for member in slack_member['members']:
                            history = sc.api_call('channels.history', channel=channel['id'])
                            message_list = []
                            partner_ids = []
                            channel_ids = []

                            for message in history['messages']:

                                ts = float(message['ts'])
                                date_time = datetime.fromtimestamp(ts)
                                try:
                                    if message['user']:
                                        member_id = message['user']

                                except Exception as e:
                                    continue

                                if member_id == member['id']:
                                    if 'client_msg_id' in message:
                                        c_msg_id = message['client_msg_id']

                                        if 'files' in message:
                                            attachment_ids = []
                                        chat = message['text'].strip("<@" + member['id'] + ">")
                                        chat = chat
                                        print(chat)

                                        recipient_partners = []
                                        channel_ids = []

                                        from_partner = self.env['res.users'].search(
                                            [('login', "=", member['profile']['email'])])
                                        if not from_partner:
                                            from_partner = self.env['res.users'].create({
                                                'member_id': member['id'],
                                                'email': member['profile']['email'],
                                                'login': member['profile']['email'],
                                                'name': member['profile']['real_name'],
                                            })
                                            recipient_partners.append(from_partner.commercial_partner_id.id)
                                        from_partner = from_partner[0] if from_partner else from_partner
                                        channel_partner = self.env['mail.channel.partner'].search(
                                            [('partner_id', '=', from_partner.commercial_partner_id.id), ('channel_id', 'not in', [1, 2])])

                                        channel_found = False
                                        for channel_prtnr in channel_partner:
                                            to_chanel_partner = self.env['mail.channel.partner'].search(
                                                [('partner_id', '=', from_partner.commercial_partner_id.id),
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
                                                        'is_subscribed': True,
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
                                                        'alias_user_id': self.env.user.id,
                                                        'is_subscribed': True

                                                    })
                                                    channel_ids.append(odoo_channel.id)

                                            from_channel_partner = self.env['mail.channel.partner'].create({
                                                'member_id': member['id'],
                                                'partner_email': member['profile']['email'],
                                                'display_name': member['profile']['real_name'],
                                                'partner_id': from_partner.commercial_partner_id.id,
                                                'channel_id': odoo_channel.id,
                                                'is_pinned': True,
                                            })

                                            # odoo_partner = self.env['mail.channel.partner'].search(
                                            #     [('member_id', '=', self.env.user.id)])
                                            #
                                            # if not odoo_partner:
                                            #     self.env['mail.channel.partner'].create({
                                            #         'member_id': self.env.user.id,
                                            #         'partner_email': self.env.user.email,
                                            #         'display_name': self.env.user.name,
                                            #         'partner_id': self.env.user.id,
                                            #         'channel_id': odoo_channel.id,
                                            #         'is_pinned': True,
                                            #     })



                                        else:
                                            odoo_channel = self.env['mail.channel'].search(
                                                [('name', '=', channel.get('name'))])

                                            if not odoo_channel:
                                                odoo_channel = self.env['mail.channel'].create({
                                                    'channel_id': channel.get('id'),
                                                    'name': channel.get('name'),
                                                    'alias_user_id': self.env.user.id,
                                                    'is_subscribed': True

                                                })
                                                channel_ids.append(channel_partner[0].channel_id.id)
                                            else:
                                                channel_ids.append(channel_partner[0].channel_id.id)

                                        mail_message = self.env['mail.message'].search(
                                            [('client_message_id', '=', c_msg_id)])
                                        if mail_message:
                                            odoo_message = self.env['mail.message'].write({
                                                'subject': chat,
                                                'date': date_time,
                                                'body': chat,
                                                'client_message_id': c_msg_id,
                                                'email_from': member['profile']['email'],
                                                'channel_ids': [[6, 0, channel_ids]],
                                                'partner_ids': [[6, 0, recipient_partners]],
                                                'attachment_ids': [[6, 0, attachment_ids]],
                                                'member_id': message['user'],
                                                'model': 'res.partner',
                                                'res_id': from_partner.commercial_partner_id.id,
                                                'author_id': from_partner.commercial_partner_id.id
                                            })
                                        else:
                                            odoo_message = self.env['mail.message'].create({
                                                'subject': chat,
                                                'date': date_time,
                                                'body': chat,
                                                'client_message_id': c_msg_id,
                                                'email_from': member['profile']['email'],
                                                'channel_ids': [[6, 0, channel_ids]],
                                                'partner_ids': [[6, 0, recipient_partners]],
                                                'attachment_ids': [[6, 0, attachment_ids]],
                                                'member_id': message['user'],
                                                'model': 'res.partner',
                                                'res_id': from_partner.commercial_partner_id.id,
                                                'author_id': from_partner.commercial_partner_id.id
                                            })

                                        self.env.cr.commit()

                    else:
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

                                    'alias_user_id': self.env.user.id,
                                    'is_subscribed': True

                                })
                                channel_ids.append(odoo_channel.id)
                        else:
                            odoo_channel = self.env['mail.channel'].search(
                                [('name', '=', channel.get('name'))])

                            if not odoo_channel:
                                odoo_channel = self.env['mail.channel'].create({
                                    'channel_id': channel.get('id'),
                                    'name': channel.get('name'),
                                    'alias_user_id': self.env.user.id,
                                    'is_subscribed': True

                                })


                    channel_name = channel.get("name")

                    odoo_channel = self.env['mail.channel'].search(
                        [('name', '=', channel.get('name'))])
                    if not odoo_channel:
                        self.env['mail.channel'].create({
                            'channel_id': channel.get('id'),
                            'name': channel.get('name'),
                            'is_subscribed': True,
                            'alias_user_id': self.env.user.id

                        })

                    if channel_name:
                        group = self.env['slack.group'].create({
                            "name": channel_name,
                        })
                        sg.append(group.id)

                self.all_group_ids = sg
                print(len(self.all_group_ids))
                if len(self.all_group_ids) == 0:
                    raise UserError('No Group Found from this Token')
            else:
                raise UserError("No Group Found")

            if sc.api_call("users.list").get('members'):

                members = sc.api_call("users.list")['members']
                self.all_users_ids.unlink()
                sm = []
                for member in members:

                    profile = member['profile']
                    if profile.get("email"):
                        user = self.env['slack.users'].create({
                            "name": profile['real_name'],
                            "email": profile['email'],
                            "user_id": member['id']
                        })
                        sm.append(user.id)
                self.all_users_ids = sm
                print(len(self.all_users_ids))
                if len(self.all_users_ids) == 0:
                    raise UserError('No User Found from this Token')
        else:
            raise osv.except_osv("Token missing", 'Please Enter the Slack Token')

    def export_slack_chat(self):
        token = self.slack_token
        sc = SlackClient(token)
        slack_channels = sc.api_call("channels.list", exclude_archived=1)["channels"]
        slack_member = sc.api_call("channels.list", exclude_archived=1)["channels"]
        s_channel_id = [s['id'] for s in slack_channels]
        odoo_channels = self.env['mail.channel'].search([])
        odoo_channel_member = self.env['mail.channel.partner'].search([])
        for channel in odoo_channels:

            if channel['channel_id'] in s_channel_id:
                odoo_channel_member = self.env['mail.channel.partner'].search([('channel_id', '=', channel['id'])])
                slack_member = sc.api_call('users.list', channel=channel['id'])['members']
                slack_membr_ids = [member['id'] for member in slack_member]
                for member in odoo_channel_member:
                    if member['member_id'] in slack_membr_ids:
                        continue
                    else:
                        profile =  {
                            'real_name':member['display_name'],
                            'email': member['partner_email']

                        }
                        id=sc.api_call('users.profile.set',profile=profile, channel=channel['channel_id'])
            else:
                new_channel = sc.api_call('channels.create', name=channel['name'])

    def getAttachments(self, attachment_ids):
        attachments = attachment_ids['files']
        attachment_ids = []
        for attachment in attachments:
            name = attachment['name']
            url = attachment['url_private_download'].strip('/'+name)
            if 'contentBytes' not in attachment or 'name' not in attachment:
                continue
            odoo_attachment = self.env['ir.attachment'].create({
                'datas': attachment['contentBytes'],
                'name': attachment["name"],
                'datas_fname': attachment["name"]})
            self.env.cr.commit()
            attachment_ids.append(odoo_attachment.id)
        return attachment_ids


class OdooDiscussions(models.Model):
    _inherit = "mail.channel"

    channel_id = fields.Char('Channel Id')
    slack_member_id = fields.Char('Member Id')

    def get_notification(self, odoo_message):
        notification = self.env['mail.notification'].create({
            'mail_message_id': odoo_message.id,
            'res_partner_id': odoo_message.res_id,
        })
        self.env.cr.commit()
        print(notification)

    @api.model
    def auto_import_chats(self):
        self.import_slack_conversation()

    def import_slack_conversation(self):
        """

        :return:
        """
        if self.env.user.company_id.slack_token:
            token = self.env.user.company_id.slack_token

            client = SlackClient(token)
            partner_ids = []
            attachment_ids = []
            channel_ids = []
            recipient_partners = []
            slack_channels = client.api_call("channels.list", exclude_archived=1)
            slack_channels = slack_channels["channels"]
            if slack_channels:
                if client.rtm_connect():
                    while client.server.connected is True:
                        for data in client.rtm_read():
                            print("data: ",data)
                            if 'user' in data:
                                if "type" in data and data['type'] == "user_typing":
                                    continue
                                if "type" in data and data["type"] == "message":
                                    if "client_message_id":
                                        slack_member = client.api_call('users.info', user=data['user'])
                                        if slack_member.get('ok'):
                                            ts = float(data['ts'])
                                            date_time = datetime.fromtimestamp(ts)
                                            member = slack_member['user']
                                            chat = data['text'].strip("<@" + member['id'] + ">")
                                            chat = chat
                                            print(chat)
                                            from_name = member['profile']['real_name']
                                            print(from_name)
                                            from_email = member['profile']['email']
                                            sl_channel = client.api_call('channels.info', channel=data['channel'])
                                            print("sl_channel: ",sl_channel)
                                            if sl_channel.get('ok'):
                                                channel = sl_channel['channel']
                                                channel_id = data['channel']
                                                chat = data['text'].strip("<@" + member['id'] + ">")
                                                chat = chat

                                                ################################################

                                                channel_ids = []

                                                from_partner = self.env['res.users'].search(
                                                    [('login', "=", member['profile']['email'])])
                                                if not from_partner:
                                                    from_partner = self.env['res.user'].create({
                                                        'member_id': member['id'],
                                                        'login': member['profile']['email'],
                                                        'email': member['profile']['email'],
                                                        'name': member['profile']['real_name'],
                                                    })
                                                    recipient_partners.append(from_partner.commercial_partner_id.id)
                                                else:
                                                    recipient_partners.append(from_partner.commercial_partner_id.id)

                                                from_partner = from_partner[0] if from_partner else from_partner
                                                channel_partner = self.env['mail.channel.partner'].search(
                                                    [('partner_id', '=', from_partner.commercial_partner_id.id),
                                                     ('channel_id', 'not in', [1, 2])])

                                                channel_found = False
                                                for channel_prtnr in channel_partner:
                                                    to_chanel_partner = self.env['mail.channel.partner'].search(
                                                        [('partner_id', '=', from_partner.commercial_partner_id.id),
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
                                                        print(odoo_channel)
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
                                                                'is_subscribed': True,
                                                                'alias_user_id': self.env.user.id

                                                            })
                                                            print(odoo_channel)
                                                            channel_ids.append(odoo_channel.id)
                                                    else:
                                                        odoo_channel = self.env['mail.channel'].search(
                                                            [('name', '=', channel.get('name'))])

                                                        if not odoo_channel:
                                                            odoo_channel = self.env['mail.channel'].create({
                                                                'channel_id': channel.get('id'),
                                                                'name': channel.get('name'),
                                                                'alias_user_id': self.env.user.id,
                                                                'is_subscribed': True

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
                                                            'alias_user_id': self.env.user.id,
                                                            'is_subscribed': True

                                                        })
                                                        channel_ids.append(channel_partner[0].channel_id.id)
                                                    else:
                                                        channel_ids.append(odoo_channel.id)

                                                mail_message = self.env['mail.message'].search(
                                                    [('client_message_id', '=', data['client_msg_id'])])
                                                if mail_message:
                                                    ###########
                                                    # self.env['mail.message'].create({'message_type': "notification",
                                                    #                                  "subtype": self.env.ref(
                                                    #                                      "mail.mt_comment").id,
                                                    #                                  'body': "Message body",
                                                    #                                  'subject': "Message subject",
                                                    #                                  'needaction_partner_ids': [
                                                    #                                      (4, self.env.user.partner_id.id)],
                                                    #                                  'model': 'res.partner',
                                                    #                                  'res_id': from_partner.commercial_partner_id.id,
                                                    #                                  })
                                                    ###########

                                                    odoo_message = self.env['mail.message'].write({
                                                        'subject': chat,
                                                        'date': date_time,
                                                        'body': chat,
                                                        'client_message_id': client_msg_id,
                                                        'email_from': member['profile']['email'],
                                                        'channel_ids': [[6, 0, channel_ids]],
                                                        'partner_ids': [[6, 0, recipient_partners]],
                                                        'attachment_ids': [[6, 0, attachment_ids]],
                                                        'member_id': data['user'],
                                                        'model': 'res.partner',
                                                        'res_id': from_partner.commercial_partner_id.id,
                                                        'author_id': from_partner.commercial_partner_id.id
                                                    })
                                                    self.env.cr.commit()
                                                else:
                                                    #########
                                                    # self.env['mail.message'].create({'message_type': "notification",
                                                    #                                  "subtype": self.env.ref(
                                                    #                                      "mail.mt_comment").id,
                                                    #                                  'body': "Message body",
                                                    #                                  'subject': "Message subject",
                                                    #                                  'needaction_partner_ids': [
                                                    #                                      (4, self.env.user.partner_id.id)],
                                                    #                                  'model': 'res.partner',
                                                    #                                  'res_id': from_partner.commercial_partner_id.id,
                                                    #                                  })
                                                    #########
                                                    odoo_message = self.env['mail.message'].create({
                                                        'message_type': "notification",
                                                        "subtype_id": self.env.ref(
                                                            "mail.mt_comment").id,
                                                        'subject': chat,
                                                        'date': date_time,
                                                        'body': chat,
                                                        'needaction_partner_ids': [(4, self.env.user.partner_id.id)],
                                                        'client_message_id': data['client_msg_id'],
                                                        'email_from': member['profile']['email'],
                                                        'channel_ids': [[6, 0, channel_ids]],
                                                        'partner_ids': [[6, 0, recipient_partners]],
                                                        'attachment_ids': [[6, 0, attachment_ids]],
                                                        'member_id': data['user'],
                                                        'model': 'res.partner',
                                                        'res_id': from_partner.commercial_partner_id.id,
                                                        'author_id': from_partner.commercial_partner_id.id
                                                    })
                                                    self.env.cr.commit()
                                                    self.get_notification(odoo_message)
                                            else:
                                                conversation = client.api_call('conversations.info',
                                                                               channel=data['channel'])
                                                """
                                                In This after getting conversation of specific channel
                                                """
     ###################################################################################################################
                                                if conversation.get('ok'):

                                                    if 'user' in conversation['channel']:

                                                        """
                                                        In this section we are fetching history of specific channel
                                                        """

                                                        odoo_username = None
                                                        history = client.api_call('im.history', channel=data['channel'])
                                                        if 'messages' in history:
                                                            for message in history['messages']:
                                                                if 'username' in message:
                                                                    odoo_username = message['username']
                                                                    break
                                                                else:
                                                                    continue
                                                        else:
                                                            print("no message")

    ####################################################################################################################
                                                        """
                                                        In this section we are fetching users list of slack and after 
                                                        doing this we will retrieve data of specific user
                                                        """

                                                        to_id = None
                                                        to_name = None
                                                        users = client.api_call("users.list")
                                                        if 'members' in users:
                                                            for member in users['members']:
                                                                if member['real_name'] == odoo_username:
                                                                    to_id = member['id']
                                                                    to_name = member['real_name']
                                                                    break
                                                                else:
                                                                    continue
                                                        else:
                                                            print("no member")
    ####################################################################################################################
                                                        """
                                                        In this section we are fetching users info(email) of 
                                                        specific user
                                                        """

                                                        user_id = client.api_call("users.info", user=to_id)
                                                        to_email = None

                                                        if "user" in user_id:
                                                            profile_data = user_id['user']['profile']
                                                            if 'email' in profile_data:
                                                                to_email = profile_data['email']
                                                                print(to_email)
                                                            else:
                                                                print("no email")
                                                        else:
                                                            print("no user")
    ####################################################################################################################

                                                        from_partner = self.env['res.users'].search(
                                                            [('login', "=", from_email)])
                                                        if not from_partner:
                                                            from_partner = self.env['res.users'].create({
                                                                'member_id': member['id'],
                                                                'email': member['profile']['email'],
                                                                'name': member['profile']['real_name'],
                                                                'login': member['profile']['email']
                                                            })

                                                        from_partner = from_partner[0] if from_partner else from_partner

                                                        # to_partner = elf.env['res.users'].search(
                                                        #     [('email', "=", to_email)])
                                                        # if not to_partner:
                                                        #     from_partner = self.env['res.users'].create({
                                                        #         'email': to_user['profile']['email'],
                                                        #         'name': to_user['profile']['real_name'],
                                                        #         'login': to_user['profile']['email']
                                                        #     })
                                                        # to_channel_partner = self.env['mail.channel.partner'].search(
                                                        #     [('partner_id', '=', to_partner.commercial_partner_id.id),
                                                        #      ('channel_id', 'not in', [1, 2])])
                                                        #
                                                        channel_partner = self.env['mail.channel.partner'].search(
                                                            [('partner_id', '=', from_partner.commercial_partner_id.id),
                                                             ('channel_id', 'not in', [1, 2])])

                                                        channel_found = False
                                                        for channel_prtnr in channel_partner:
                                                            to_chanel_partner = self.env['mail.channel.partner'].search(
                                                                [('partner_id', '=',
                                                                  from_partner.commercial_partner_id.id),
                                                                 ('channel_id', '=', channel_prtnr.channel_id.id),
                                                                 ('channel_id', 'not in', [1, 2])])
                                                            if to_chanel_partner:
                                                                channel_found = True
                                                                channel_partner = channel_prtnr
                                                                break

                                                        if not channel_found:

                                                            from_channel_partner = self.env[
                                                                'mail.channel.partner'].create({
                                                                'member_id': member['id'],
                                                                'partner_email': from_email,
                                                                'display_name': from_name,
                                                                'partner_id': from_partner.commercial_partner_id.id,

                                                                'is_pinned': True,
                                                            })

                                                            odoo_partner = self.env['mail.channel.partner'].search(
                                                                [(
                                                                    'member_id', '=',
                                                                    self.env.user.commercial_partner_id.id)])

                                                            if not odoo_partner:
                                                                self.env['mail.channel.partner'].create({
                                                                    'member_id': self.env.user.id,
                                                                    'partner_email': self.env.user.email,
                                                                    'display_name': self.env.user.name,
                                                                    'partner_id': self.env.user.commercial_partner_id.id,

                                                                    'is_pinned': True,
                                                                })
                                                        # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@ to_partner
                                                        to_partner = self.env['res.users'].search(
                                                            [('login', "=", to_email)])
                                                        if not to_partner:
                                                            to_partner = self.env['res.users'].create({
                                                                'member_id': member['id'],
                                                                'email': to_email,
                                                                'name': to_name,
                                                                'login': to_email
                                                            })
                                                            recipient_partners.append(
                                                                to_partner.commercial_partner_id.id)
                                                        else:
                                                            recipient_partners.append(
                                                                to_partner.commercial_partner_id.id)
                                                        to_partner = to_partner[0] if to_partner else to_partner
                                                        to_channel_partners = self.env['mail.channel.partner'].search(
                                                            [('partner_id', '=', to_partner.commercial_partner_id.id),
                                                             ('channel_id', 'not in', [1, 2])])

                                                        channel_found = False
                                                        for channel_prtnr in to_channel_partners:
                                                            to_chanel_partner = self.env['mail.channel.partner'].search(
                                                                [('partner_id', '=',
                                                                  from_partner.commercial_partner_id.id),
                                                                 ('channel_id', '=', channel_prtnr.channel_id.id),
                                                                 ('channel_id', 'not in', [1, 2])])
                                                            if to_chanel_partner:
                                                                channel_found = True
                                                                to_channel_partners = channel_prtnr
                                                                break

                                                        if not channel_found:
                                                            to_channel_partners = self.env[
                                                                'mail.channel.partner'].create({
                                                                'member_id': member['id'],
                                                                'partner_email': member['profile']['email'],
                                                                'display_name': member['profile']['real_name'],
                                                                'partner_id': to_partner.commercial_partner_id.id,

                                                                'is_pinned': True,
                                                            })

                                                        channel_name = from_name+', '+self.env.user.name
                                                        channel_id = self.env['mail.channel'].search(
                                                            [("name", "=", channel_name)])
                                                        if channel_id:
                                                            channel_ids.append(channel_id.id)
                                                        else:
                                                            channel_id = self.env['mail.channel'].create({
                                                                'channel_id': data['channel'],
                                                                'name': channel_name,
                                                                'alias_user_id': self.env.user.id

                                                            })
                                                            channel_ids.append(channel_id.id)

                                                        mail_message = self.env['mail.message'].search(
                                                            [('client_message_id', '=', data['client_msg_id'])])
                                                        if mail_message:
                                                            odoo_message = self.env['mail.message'].write({
                                                                'subject': chat,
                                                                'date': date_time,
                                                                'body': chat,
                                                                'client_message_id': data['client_msg_id'],
                                                                'email_from': from_email,
                                                                'channel_ids': [[6, 0, channel_ids]],
                                                                'partner_ids': [[6, 0, recipient_partners]],
                                                                'attachment_ids': [[6, 0, attachment_ids]],
                                                                'member_id': data['user'],
                                                                'model': 'res.partner',
                                                                'res_id': to_partner.commercial_partner_id.id,
                                                                'author_id': from_partner.commercial_partner_id.id
                                                            })
                                                            self.env.cr.commit()
                                                        else:
                                                            ###########
                                                            odoo_message = self.env['mail.message'].create({
                                                                'message_type': "notification",
                                                                "subtype_id": self.env.ref(
                                                                    "mail.mt_comment").id,
                                                                'subject': chat,
                                                                'date': date_time,
                                                                'body': chat,
                                                                'needaction_partner_ids': [
                                                                    (4, self.env.user.partner_id.id)],
                                                                'client_message_id': data['client_msg_id'],
                                                                'email_from': member['profile']['email'],
                                                                'channel_ids': [[6, 0, channel_ids]],
                                                                'partner_ids': [[6, 0, recipient_partners]],
                                                                'attachment_ids': [[6, 0, attachment_ids]],
                                                                'member_id': data['user'],
                                                                'model': 'res.partner',
                                                                'res_id': to_partner.commercial_partner_id.id,
                                                                'author_id': from_partner.commercial_partner_id.id
                                                            })
                                                            ###########
                                                            # odoo_message = self.env['mail.message'].create({
                                                            #     'subject': chat,
                                                            #     'date': date_time,
                                                            #     'body': chat,
                                                            #     'client_message_id': data['client_msg_id'],
                                                            #     'email_from': from_email,
                                                            #     # 'channel_ids': [[6, 0, channel_ids]],
                                                            #     'partner_ids': [[6, 0, recipient_partners]],
                                                            #     'attachment_ids': [[6, 0, attachment_ids]],
                                                            #     'member_id': data['user'],
                                                            #     'model': 'res.partner',
                                                            #     'res_id': to_partner.commercial_partner_id.id,
                                                            #     'author_id': from_partner.commercial_partner_id.id
                                                            # })
                                                            print(odoo_message)
                                                            self.env.cr.commit()
                                                            self.get_notification(odoo_message)

                                                        # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@



                                                    else:
                                                        if 'purpose' in conversation['channel']:
                                                            user_list = conversation['channel']['purpose'][
                                                                'value'].split(
                                                                '@')
                                                            user = client.api_call('users.list')['members']
                                                            for name in user:
                                                                if name == from_name:
                                                                    continue
                                                                elif name['name'] in user_list:
                                                                    to_name = name['profile']['real_name']
                                                                    to_email = name['profile']['email']

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
        else:
            raise osv.except_osv(('Invalid Token'), ("Token does not found"))


class MailChannelPartner(models.Model):

    _inherit = 'mail.channel.partner'

    member_id = fields.Char('Member_id')
    is_slack = fields.Boolean(compute=' _is_slack_member ')


class MailChannelUser(models.Model):
    _inherit = 'res.users'

    member_id = fields.Char('Member_id')
    is_slack = fields.Boolean(compute='_is_slack_member')
    is_invite = fields.Char("Message")

    def _is_slack_member(self):

        if self.member_id:
            self.is_slack = True
            self.is_invite = ("User also exist on Slack")
        else:
            self.is_slack = False

    def send_invitation(self):
        if self.env.user.company_id.slack_token:
            token = self.env['res.company'].search([]).slack_token
            sc = SlackClient(token)

            if sc:
                channels = sc.api_call('channels.list')
                email = self.email
                if re.match("^.+@([?)[a-zA-Z0-9-.]+.([a-zA-Z]{2,3}|[0-9]{1,3})(]?)$)", email):
                    for channel in channels['channels']:
                        if channel['name'].upper() == 'GENERAL':
                            user = sc.api_call('users.admin.invite', email=email)
                            if 'error' in user:
                                raise osv.except_osv(" Invitation is already sent ")


                            else:

                                raise osv.except_osv(('Success'), ("Invitation is successfully sent"))




                        else:
                            print('connection problem')

                else:
                    raise osv.except_osv(("Sorry!"), ("Invalid Email Address"))

        else:
           raise osv.except_osv(('Invalid Token'),('Sorry! Token is missing!'))


class MailMessage(models.Model):

    _inherit = 'mail.message'
    client_message_id = fields.Char('Client Message Id')
    member_id = fields.Char('Slack Member Id')
    message_id = fields.Char('Message Id')

    @api.model
    def invite(self, values):
        print('')
        print(values)

    @api.model
    def create(self, values):

        if self.env.user.company_id.slack_token:
            if values['body']=='Contact created':
                res_id = super(MailMessage, self).create(values)
                return res_id
            elif 'client_message_id' not in values:
                if "subjects" not in values:
                    # attachments_list = self.getAttachments(values['attachment_ids'])
                    subject = values['subject'] if values['subject'] else values['body']
                    body = values['body']
                    token = self.env['res.company'].search([]).slack_token
                    sc = SlackClient(token)
                    slack_channels = sc.api_call("channels.list", exclude_archived=1)["channels"]
                    slack_user = sc.api_call("users.list")
                    body = body.strip('<>/p')
                    to_partner = None
                    if values['model'] == 'mail.channel':
                        if values['message_type'] == 'comment':
                            odoo_channel = self.env['mail.channel'].search([(('id'), '=', values['res_id'])])
                            if odoo_channel:
                                from_partner = self.env['res.users'].search(
                                    [('email', '=', self.env.user.email)])
                                to_channel = self.env['mail.channel'].search([(('id'), '=', values['res_id'])])
                                from_partner = from_partner[0] if from_partner else from_partner

                                found = False

                                if to_channel:
                                    real_name = None
                                    email = from_partner.email
                                    if email:
                                        head, sep, tail = email.partition('@')

                                    if values['message_type'] == 'comment':
                                        users = sc.api_call("users.list")
                                        i = 0
                                        check = 0
                                        if 'members' in users:
                                            for member in users['members']:
                                                i = i + 1
                                        else:
                                            print("no hello")

                                        for channel in slack_channels:
                                            if channel.get('name') == odoo_channel['name']:
                                                if 'members' in users:
                                                    for member in users['members']:
                                                        if member['name'] == head:
                                                            real_name = member['real_name']
                                                            sc.api_call(
                                                                "chat.postMessage",
                                                                channel=channel['id'],
                                                                text=body,
                                                                username=real_name,
                                                                icon_emoji='true'
                                                                )
                                                            break
                                                        else:
                                                            check = check + 1
                                                            if check == i:
                                                                raise osv.except_osv(('Invalid User'), (
                                                                    "Please invite user to slack."))
                                                            continue

                                                else:
                                                    print("no member")

                                                found = True
                                                break

                                            else:
                                                continue
                                        if not found:
                                            partner = self.env['res.users'].search([])
                                            for part in partner:
                                                to_part_channel = self.env['mail.channel'].search(
                                                    [(('id'), '=', values['res_id'])])
                                                if part.name in list(to_part_channel['display_name'].split(',')):
                                                    if part.name == self.env.user.name:
                                                        continue
                                                    else:
                                                        channel_partner = part
                                                        from_partner = self.env['res.users'].search(
                                                            [('email', '=', self.env.user.email)])
                                                        to_channel = self.env['mail.channel'].search(
                                                            [(('id'), '=', values['res_id'])])
                                                        from_partner = from_partner[0] if from_partner else from_partner
                                                        if channel_partner:
                                                            partner_id = channel_partner.commercial_partner_id.id
                                                            partner_name = channel_partner.name
                                                        to_partner = self.env['mail.channel.partner'].search(
                                                            [('partner_id', '=', partner_id),
                                                             ('channel_id', '=', to_channel.id),
                                                             ('channel_id', 'not in', [1, 2])])
                                                        if not to_partner:
                                                            to_partner = self.env['mail.channel.partner'].create({
                                                                'partner_email': channel_partner.email,
                                                                'display_name': partner_name,
                                                                'partner_id': partner_id,
                                                                'channel_id': to_channel.id,
                                                                'is_pinned': True,
                                                            })

                                                        if to_partner and to_partner['display_name'] == partner_name:
                                                            if values['message_type'] == 'comment':

                                                                for user in slack_user['members']:
                                                                    if to_partner['display_name'].upper() == \
                                                                            user['profile'][
                                                                                'real_name'].upper():
                                                                        self.env['mail.channel.partner'].write({
                                                                            'partner_email': user['profile']['email'],
                                                                            'display_name': user['profile'][
                                                                                'real_name'],
                                                                            'partner_id': partner_id,
                                                                            'channel_id': to_channel.id,
                                                                            'is_pinned': True,
                                                                        })
                                                                        userChannel = sc.api_call(
                                                                            "im.open",
                                                                            user=user['id']
                                                                        )
                                                                        if userChannel:
                                                                            real_name = None
                                                                            email = from_partner.email
                                                                            if email:
                                                                                head, sep, tail = email.partition('@')
                                                                            users = sc.api_call("users.list")
                                                                            i = 0
                                                                            check = 0
                                                                            if 'members' in users:
                                                                                for member in users['members']:
                                                                                    i = i + 1
                                                                            else:
                                                                                print("no hello")
                                                                            if 'members' in users:
                                                                                for member in users['members']:
                                                                                    if member['name'] == head:
                                                                                        real_name = member['real_name']
                                                                                        print(real_name)
                                                                                        sc.api_call(
                                                                                            "chat.postMessage",
                                                                                            channel=
                                                                                            userChannel['channel'][
                                                                                                'id'],
                                                                                            text=body,
                                                                                            username=real_name,
                                                                                            icon_emoji='true'
                                                                                        )
                                                                                        break
                                                                                    else:
                                                                                        check = check + 1
                                                                                        if check == i:
                                                                                            raise osv.except_osv(
                                                                                                ('Invalid User'), (
                                                                                                    "Please invite user to slack."))
                                                                                        continue
                                                                            else:
                                                                                print('no member')
                                                                        found = True
                                                                        break
                                                                    else:
                                                                        continue
                                                                if not found:
                                                                    raise ValueError('user does not found')

                                        else:
                                            print('Channel Created')

                                print('channel')
                            else:
                                partner = self.env['res.users'].search([])
                                for part in partner:
                                    to_part_channel = self.env['mail.channel'].search([(('id'), '=', values['res_id'])])
                                    if part.name in list(to_part_channel['display_name'].split(',')):
                                        if part.name == self.env.user.name:
                                            continue
                                        else:
                                            channel_partner = part
                                            from_partner = self.env['res.users'].search(
                                                [('email', '=', self.env.user.email)])
                                            to_channel = self.env['mail.channel'].search(
                                                [(('id'), '=', values['res_id'])])
                                            from_partner = from_partner[0] if from_partner else from_partner
                                            # channel_partner = self.env['mail.channel'].search([('id', '=', values['res_id'])])
                                            if channel_partner:
                                                partner_id = channel_partner.commercial_partner_id.id
                                                partner_name = channel_partner.name
                                            to_partner = self.env['mail.channel.partner'].search(
                                                [('partner_id', '=', partner_id),
                                                 ('channel_id', '=', to_channel.id),
                                                 ('channel_id', 'not in', [1, 2])])
                                            if not to_partner:
                                                to_partner = self.env['mail.channel.partner'].create({
                                                    'partner_email': channel_partner.email,
                                                    'display_name': partner_name,
                                                    'partner_id': partner_id,
                                                    'channel_id': to_channel.id,
                                                    'is_pinned': True,
                                                })

                                            if to_partner and to_partner['display_name'] == partner_name:
                                                if values['message_type'] == 'comment':

                                                    for user in slack_user['members']:
                                                        # slack_name = [channel.get('name').upper() for channel in slack_channels]
                                                        if to_partner['display_name'].upper() == user['profile'][
                                                            'real_name'].upper():
                                                            self.env['mail.channel.partner'].write({
                                                                'partner_email': user['profile']['email'],
                                                                'display_name': user['profile']['real_name'],
                                                                'partner_id': partner_id,
                                                                'channel_id': to_channel.id,
                                                                'is_pinned': True,
                                                            })

                                                            userChannel = sc.api_call(
                                                                "im.open",
                                                                user=user['id']
                                                            )
                                                            if userChannel:

                                                                sc.api_call(
                                                                    "chat.postMessage",
                                                                    channel=userChannel['channel']['id'],
                                                                    text=body,
                                                                    username=from_partner.name

                                                                )

                                                                print('ok')
                                                            found = True
                                                            break

                                                    if not found:
                                                        raise ValueError('user does not found')

                        else:
                            print('Channel Created')

                        res_id = super(MailMessage, self).create(values)
                        self.env.cr.commit()
                        return res_id



                    elif values['model'] == 'res.partner':
                            subject = values['subject'] if values['subject'] else values['body']
                            body = values['body']
                            body = body.strip('<>/p')

                            slack_channels = sc.api_call("channels.list", exclude_archived=1)["channels"]
                            # slack_name = [channel for channel in slack_channels]
                            # channel_id = [channel['id'] for channel in slack_channels]

                            to_partner = None

                            from_partner = self.env['res.partner'].search([('id', '=', values['res_id'])])

                            from_partner = from_partner[0] if from_partner else from_partner
                            channel_partner = self.env['mail.channel.partner'].search(
                                [('channel_id', '=', values['res_id']), ('partner_id', '!=', from_partner.id)])
                            if channel_partner:
                                to_partner = channel_partner[0].partner_id if channel_partner else channel_partner

                            slack_member = sc.api_call("users.list", exclude_archived=1)['members']
                            if slack_member:
                                slack_name = [channel.get('name').upper() for channel in slack_member]
                                found = False
                                for slack_mem in slack_member:
                                    # slack_name = [channel.get('name').upper() for channel in slack_channels]
                                    if from_partner.email.upper() == slack_mem['profile']['email'].upper():
                                        # for channel in slack_channels:
                                        # if slack_mem['id'] in channel.get('members'):
                                        from_name = from_partner.name
                                        from_email = from_partner.email

                                        userChannel = sc.api_call(
                                            "im.open",
                                            user=slack_mem['id']
                                        )
                                        if userChannel:
                                            sc.api_call(
                                                "chat.postMessage",
                                                channel=userChannel['channel']['id'],
                                                text=body,
                                                username=self.env.user.name

                                            )

                                        found = True
                                        break
                                if not found:
                                    raise osv.except_osv(("Success!"), (("Token Generated!")))

                                res_id = super(MailMessage, self).create(values)
                                self.env.cr.commit()
                                return res_id

                    else:
                        res_id = super(MailMessage, self).create(values)
                        return res_id

            else:
                res_id = super(MailMessage, self).create(values)
                return res_id

        else:
            raise osv.except_osv(('Invalid Token'),("Token does not found"))
