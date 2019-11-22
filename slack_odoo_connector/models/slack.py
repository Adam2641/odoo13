from odoo import models, fields, api,exceptions
from slackclient import SlackClient
# from slackclient._user import User
import threading
from odoo.exceptions import UserError, AccessError
import time


class SlackForm(models.Model):
    _name = 'slack.data'

    name = fields.Char(string="Name", required=True)
    model_id = fields.Many2one('ir.model', string="Model", required=True)
    channel_id = fields.Many2one('slack.group', string="Channel")
    member_id = fields.Many2one('slack.users', string="Member")
    members_ids = fields.One2many('slack.data.users', 'slack_data_id')
    triggers_ids = fields.One2many('slack.trigger', 'trigger_id')
    active = fields.Boolean(string="Enable", default=True)
    trigger_id = fields.Selection([
        ("on_create", "On creation"),
        ("on_write", "On update"),
        ("on_create_or_write", "On creation or update"),
        ("interval", "On interval"),
        ("only_manual", "Only manually"),
    ], required=True, string="Trigger Condition")

    @api.multi
    def unlink(self):
        for data in self:
            self.env['base.automation'].search([('name', '=', data.name)]).unlink()
            self.env['ir.actions.server'].search([('name', '=', data.name)]).unlink()
        return super(SlackForm, self).unlink()

    @api.multi
    def write(self, values):
        """
        :param values:
        :return:
        """
        self.env['base.automation'].search([('name', '=', self.name)]).write({
            'name': values["name"] if "name" in values.keys() else self.name,
            'model_id': values["model_id"] if "model_id" in values.keys() else self.model_id.id,
            'trigger': values['trigger_id'] if "trigger_id" in values.keys() else self.trigger_id
        })
        record = super(SlackForm, self).write(values)
        return record

    @api.model
    def create(self, values):
        """
        :param values:
        :return:
        """
        record = super(SlackForm, self).create(values)
        # cd = "env['{}'].browse({}).trigger_flows(record)".format(
        #     self._name,
        #     record.id
        # )
        self.env['base.automation'].create({
            'name': values["name"],
            'model_id': values["model_id"],
            'trigger': values['trigger_id'],
            'state': 'code',
            'code': self.env['slack.data'].browse(record.id).trigger_flows(record)
        })
        return record

    def trigger_flows(self, obj):

        if self.env.user.company_id.slack_token:
            api_token = self.env.user.company_id.slack_token
        else:
            raise UserError("No Token Found")
        a = 1
        user_n = self.env.user.name
        if self.active:
            if self.channel_id:
                trigger = self.trigger_id
                product_name = obj.name
                model_name = obj._description
                channel = self.channel_id.name
                msg = model_name + " With Name " + product_name + " Trigger " + trigger + " By User " + user_n
                a += 1
                if self.members_ids:
                    for members in self.members_ids:
                        user = members.user_id
                        thcall = threading.Thread(target=self.send_slack_message, args=(api_token, channel, msg, user))
                        thcall.start()
                else:
                    thcall = threading.Thread(target=self.send_slack_message_channel, args=(api_token, channel, msg))
                    thcall.start()
            else:
                raise UserError('Please Select a Channel')
        else:
            raise UserError('This Slack Data is not Enable')

    def send_slack_message(self, token, channel, message, user):
        sc = SlackClient(token)
        sc.api_call(
            "chat.postEphemeral", channel=channel, text=message, user=user,
            username='OdooBot', icon_emoji=':robot_face:'
        )
        return {}

    def send_slack_message_channel(self, token, channel, message):
        sc = SlackClient(token)
        sc.api_call(
            "chat.postMessage", channel=channel, text=message,
            username='OdooBot', icon_emoji=':robot_face:'
        )
        return {}

    @api.multi
    def get_users(self):
        selected_channel = self.channel_id.name
        if self.env.user.company_id.slack_token:
            token = self.env.user.company_id.slack_token
            sc = SlackClient(token)
        else:
            raise UserError("No Token Found")
        self.members_ids.unlink()
        all_members_ids = []
        if sc.api_call("channels.list"):

            for channel in sc.api_call("channels.list", exclude_archived=1)["channels"]:
                channel_name = channel.get("name")
                if channel_name == selected_channel:
                    for mem in channel.get('members'):

                        members_id = sc.api_call("users.list").get("members")

                        for users_id in members_id:
                            if users_id.get("id") == mem:
                                if users_id.get('profile').get('email'):
                                    name = str(users_id.get('profile').get('real_name'))
                                    new_user = self.env['slack.data.users'].create({
                                        "name_s": name,
                                        "channel": channel_name,
                                        "user_id": users_id.get('id'),
                                    })
                                    all_members_ids.append(new_user.id)
                                    self.members_ids = [new_user.id]
        else:
            raise UserError('Your Token is Invalid')


class SlackMappingForm(models.Model):
    _name = 'slack.mapping'

    schema_property = fields.Char(string="Schema Property")
    model_view = fields.Char(string="Model View")
    type = fields.Selection([('default', 'Default')], string="Type")
    mapping_id = fields.Many2one('slack.data')


class SlackTriggerForm(models.Model):
    _name = 'slack.trigger'

    name = fields.Selection([
        ("on_create", "On creation"),
        ("on_write", "On update"),
        ("on_create_or_write", "On creation or update"),
        ("interval", "On interval"),
        ("only_manual", "Only manually"),
    ], required=True, string="Event")
    interval_number = fields.Char(string="Interval Number")
    trigger_id = fields.Many2one('slack.data')


class SlackDataUsers(models.Model):
    _name = 'slack.data.users'

    name_s = fields.Char('Name')
    channel = fields.Char('Channel')
    user_id = fields.Char('User ID')

    slack_data_id = fields.Many2one('slack.data')
