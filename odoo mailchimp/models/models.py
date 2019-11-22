# -*- coding: utf-8 -*-
from odoo import fields, models, api, osv
from openerp.exceptions import ValidationError
from openerp.osv import osv
from openerp import _
from mailchimp3 import MailChimp


class CustomUser(models.Model):
    _inherit = 'res.users'

    mailchimp_username = fields.Char('username')
    api_key = fields.Char('API Key')

    def test_connection(self):
        """
        Test the MailChimp Connection
        :return:
        """

        try:
            client = MailChimp(mc_user=self.mailchimp_username, mc_api=self.api_key)
            client.lists.all(get_all=True, fields="lists.name,lists.id")

        except Exception as e:
            raise ValidationError(_(str(e)))

        raise osv.except_osv(("Success!"), (" Connection Successful !"))


class CustomPartner(models.Model):
    _inherit = "res.partner"

    member_id = fields.Char('MailChimp Id')
    member_status = fields.Char('Member Status')
    campaign_name = fields.Char('Campaign Name')
    list_name = fields.Char('List Name')
    many_list_ids = fields.Many2many('mailchimp.list', 'partner_list_rel', 'list_id', 'partner_id', string='Lists')
    many_campaign_ids = fields.Many2many('mailchimp.campaign', 'partner_campaign_rel', 'mailchimp_id',
                                         'partner_id', string='Campaign')
    many_campaign_customer_ids = fields.Many2many('partner.campaign', 'partner_campaign_rel_tab', 'mailchimp_id',
                                                  'partner_id', string='Customers_Campaign')
    partner_campaign_ids = fields.One2many('partner.campaign',  'customer_ids', copy=True)


class MailChimpList(models.Model):
    _name = "mailchimp.list"

    name = fields.Char(string="Name", required=True)
    from_email = fields.Char(string="From Email", required=True)
    from_name = fields.Char(string="From Name", required=True)
    subject = fields.Char(string="Subject", required=True)
    permission_reminder = fields.Char(string="Permission Reminder", required=True)
    address1 = fields.Char(string="Address1", required=True)
    address2 = fields.Char(string="Address2", required=True)
    phone = fields.Char(string="Phone", required=True)
    city = fields.Char(string="City", required=True)
    state = fields.Char(string="State", required=True)
    zip = fields.Char(string="Zip", required=True)
    country = fields.Char(string="Country", required=True)
    company = fields.Char(string="Company", required=True)
    mailchimp_id = fields.Char(string="MailChimp Id", readonly=True)
    many_customer_ids = fields.Many2many('res.partner', 'partner_list_rel',
                                         'partner_id', 'list_id',string='Customers')
    mailchimp_connector_id = fields.Many2one('mailchimp.connector', string='MailChimp List', ondelete='cascade',
                                             index=True, copy=False)

    def sync_customers(self):
        """
        Create or Update the MailChimp User.

        :return: None
        """

        client = MailChimp(mc_user=self.env.user.mailchimp_username, mc_api=self.env.user.api_key)
        if self.mailchimp_id == False:
            try:
                list_mailchimp = client.lists.create(data={
                    'name': self.name,
                    'permission_reminder': self.permission_reminder,
                    'email_type_option': False,
                    'contact': {
                        'address1':self.address1,
                        'address2':self.address2,
                        'city':self.city,
                        'company':self.company,
                        'country':self.country,
                        'phone':self.phone,
                        'state':self.state,
                        'zip':self.zip,
                    },
                    'campaign_defaults':{
                        'from_email': self.from_email,
                        'from_name': self.from_name,
                        'subject':self.subject,
                        'language':"en",
                    }
                })
                self.mailchimp_id = list_mailchimp['id']
            except Exception as e:
                raise ValidationError(e)
        else:
            client.lists.update(list_id=self.mailchimp_id, data={
                'name': self.name,
                'permission_reminder': self.permission_reminder,
                'email_type_option': False,
                'contact': {
                    'address1': self.address1,
                    'address2': self.address2,
                    'city': self.city,
                    'company': self.company,
                    'country': self.country,
                    'phone': self.phone,
                    'state': self.state,
                    'zip': self.zip,
                },
                'campaign_defaults': {
                    'from_email': self.from_email,
                    'from_name': self.from_name,
                    'subject': self.subject,
                    'language': "en",
                }
            })

        members = client.lists.members.all(self.mailchimp_id, get_all=True)
        partner_ids = []
        for odoo_member in self.many_customer_ids:
            found = False
            street = None
            city = None
            state = None
            country = None
            zip = None
            for mailchimp_member in members['members']:
                if odoo_member.street or odoo_member.street2:
                    street = odoo_member.street if odoo_member.street else odoo_member.street2
                city = odoo_member.city if odoo_member.city else None
                state = odoo_member.state_id.name if odoo_member.state_id else None
                country = odoo_member.country_id.name if odoo_member.country_id else None
                zip = odoo_member.zip if odoo_member.zip else None
                if mailchimp_member['id'] == odoo_member.member_id:
                    if mailchimp_member['status'] == 'unsubscribed':
                        client.lists.members.update(self.mailchimp_id, mailchimp_member['email_address'],
                                                    {"status": "subscribed"})
                    found = True
                    break
            if not found:
                try:
                    if street and state and country and city and zip:

                        response = client.lists.members.create(self.mailchimp_id, {
                            'email_address': odoo_member.email,
                            'status': 'subscribed',
                            'merge_fields': {
                                'FNAME': odoo_member.name,
                                'ADDRESS': {'addr1': street,
                                            'city': city,
                                            'state': state,
                                            'country': country,
                                            'zip': zip},
                                'PHONE': odoo_member.phone if odoo_member.phone else ""
                            },
                        })
                    else:
                        client.lists.members.create(self.mailchimp_id, {
                            'email_address': odoo_member.email,
                            'status': 'subscribed',
                            'merge_fields': {
                                'FNAME': odoo_member.name,
                                'PHONE': odoo_member.phone if odoo_member.phone else ""
                            },
                        })

                except Exception as e:
                    error = e.args[0]['detail']
                    print(error)
                    continue

                    raise ValidationError(e)
        for mailchimp_member in members['members']:
            found = False
            for odoo_member in self.many_customer_ids:
                if mailchimp_member['id'] == odoo_member.member_id:
                    found = True
                    break
            if not found:
                client.lists.members.update(self.mailchimp_id, mailchimp_member['email_address'], {"status": "unsubscribed"})


class MailChimpCampaign(models.Model):
    _name = "mailchimp.campaign"

    name = fields.Char("Name")
    mailchimp_id = fields.Char("Campaign Id")
    customer = fields.Char('Total Sent')
    total_open = fields.Char('Opens')
    total_clicks = fields.Char('Clicks')
    total_orders = fields.Char('Total Order')
    total_revenue = fields.Char('Total Revenue')
    total_spent = fields.Char('Total Spent')
    list_id = fields.Char('List Id')
    list_name = fields.Char('List Name')
    total_recipient = fields.Char('Total Recipient')
    status = fields.Char('Campaign Status')
    send_date = fields.Char('Start Date')
    many_customer_ids = fields.Many2many('res.partner', 'partner_campaign_rel',
                                                        'partner_id', 'mailchimp_id', string='Customers')
    mailchimp_connector_id = fields.Many2one('mailchimp.connector', string='MailChimp Campaign', ondelete='cascade',
                                             index=True, copy=False)

    def replicate_campaign(self):
        try:
            client = MailChimp(mc_user=self.env.user.mailchimp_username, mc_api=self.env.user.api_key)
            replica = client.campaigns.actions.replicate(campaign_id=self.mailchimp_id)
            campaign_id =replica['id']
            sent = client.campaigns.actions.send(campaign_id = replica['id'])
            self.env['mailchimp.campaign'].create({
                'mailchimp_id': replica['id'],
                'name': replica['settings']['title'],
                'mailchimp_connector_id': self.mailchimp_connector_id.id
            })
            self.env.cr.commit()
        except Exception as e:
            raise ValidationError(e)


class PartnerCampaign(models.Model):

    _name = 'partner.campaign'
    email = fields.Char('Email')
    member_status = fields.Char('Member Status')
    campaign_id= fields.Char('Campaign ID')
    name = fields.Char("Campaign Name")
    customer = fields.Char('Total Sent')
    total_open = fields.Char('Opens')
    total_clicks = fields.Char('Clicks')
    total_orders = fields.Char('Total Order')
    total_revenue = fields.Char('Total Revenue')
    total_spent = fields.Char('Total Spent')
    list_id = fields.Char('List Id')
    list_name = fields.Char('List Name')
    total_recipient = fields.Char('Total Recipient')
    status = fields.Char('Campaign Status')
    member_name = fields.Char('Member Name')
    member_id = fields.Char('Member Id')
    phone = fields.Char('Phone Number')
    send_date = fields.Char('Start Date')
    mailchimp_connector_id = fields.Many2one('mailchimp.connector', string='Partner Campaign',
                                             ondelete='cascade', index=True, copy=False)
    customer_ids = fields.Many2one('res.partner', string='Partner Reference', required=False,
                                   ondelete='cascade', index=True, copy=False)
    mailchimp_connector_id = fields.Many2one('mailchimp.connector', string='MailChimp Campaign',
                                             ondelete='cascade',index=True, copy=False)
