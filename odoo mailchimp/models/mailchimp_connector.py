from mailchimp3 import MailChimp
from openerp import _
from odoo import models, fields, api
from openerp.exceptions import Warning, ValidationError


class MailChimpConnector(models.Model):
    """
    Sync the MailChimpList and MailChimp Campaign from mailchimp
    """

    _name = 'mailchimp.connector'

    field_name = fields.Char('mailchimp_connector')
    list_ids = fields.One2many('mailchimp.list', 'mailchimp_connector_id', string="MailChimp Lists")

    campaign_ids = fields.One2many('mailchimp.campaign', 'mailchimp_connector_id', string="MailChimp Campaigns")
    partner_campaign_ids = fields.One2many('partner.campaign', 'mailchimp_connector_id', string="Partner Campaigns")

    def sync(self):
        """
        Import MailChimpList and MailChimp Campaign from mailchimp
        :return:
        """
        try:

            if self.field_name:
                client = MailChimp(mc_user=self.env.user.mailchimp_username, mc_api=self.env.user.api_key)
                campaigns = client.campaigns.all(get_all=True)
                campaign_partner_id = []
                for campaign in campaigns['campaigns']:

                    campaign_list_id = campaign['recipients']['list_id'] if campaign['recipients']['list_id'] else None
                    if campaign_list_id==None:

                        odoo_campaign = self.env['mailchimp.campaign'].search([('mailchimp_id', '=', campaign['id'])])
                        if not odoo_campaign:
                            if campaign['status'] != 'save':
                                self.env['mailchimp.campaign'].create({
                                    'mailchimp_id': campaign['id'],
                                    'mailchimp_connector_id': self.id,
                                    'name': campaign['settings']['title'],
                                    'customer': campaign['emails_sent'],
                                    'total_open': campaign['report_summary']['opens'],
                                    'total_clicks': campaign['report_summary']['clicks'],
                                    'total_order': campaign['report_summary']['ecommerce']['total_orders'],
                                    'total_revenue': campaign['report_summary']['ecommerce']['total_revenue'],
                                    'total_spent': campaign['report_summary']['ecommerce']['total_spent'],
                                    'list_id': campaign['recipients']['list_id'] if campaign['recipients'][
                                        'list_id'] else None,
                                    'list_name': campaign['recipients']['list_name'],
                                    'total_recipient': campaign['recipients']['recipient_count'],
                                    'status': campaign['status'],
                                    'many_customer_ids': [[6, 0, campaign_partner_id]]
                                })


                            else:
                                self.env['mailchimp.campaign'].create({
                                    'mailchimp_id': campaign['id'],
                                    'mailchimp_connector_id': self.id,
                                    'name': campaign['settings']['title'],
                                    'customer': campaign['emails_sent'],
                                    'total_open': campaign['tracking']['opens'],

                                    'list_id': campaign['recipients']['list_id'] if campaign['recipients'][
                                        'list_id'] else None,
                                    'list_name': campaign['recipients']['list_name'],
                                    'total_recipient': campaign['recipients']['recipient_count'],
                                    'status': campaign['status'],
                                    'many_customer_ids': [[6, 0, campaign_partner_id]]
                                })

                        else:
                            if campaign['status'] != 'save':
                                    self.env['mailchimp.campaign'].write({
                                        'mailchimp_id': campaign['id'],
                                        'mailchimp_connector_id': self.id,
                                        'name': campaign['settings']['title'],
                                        'customer': campaign['emails_sent'],
                                        'total_open': campaign['report_summary']['opens'],
                                        'total_clicks': campaign['report_summary']['clicks'],
                                        'total_order': campaign['report_summary']['ecommerce']['total_orders'],
                                        'total_revenue': campaign['report_summary']['ecommerce']['total_revenue'],
                                        'total_spent': campaign['report_summary']['ecommerce']['total_spent'],
                                        'list_id': campaign['recipients']['list_id'],
                                        'list_name': campaign['recipients']['list_name'],
                                        'total_recipient': campaign['recipients']['recipient_count'],
                                        'status': campaign['status'],
                                        'many_customer_ids': [[6, 0, campaign_partner_id]]
                                    })

                    else:
                        campaign_members = client.lists.members.all(campaign_list_id,count=10, offset=0, fields = "members.id,members.merge_fields,members.status,members.email_address" )

                        odoo_campaign = self.env['mailchimp.campaign'].search([('mailchimp_id', '=', campaign['id'])])
                        if not odoo_campaign:

                            for camp_member in campaign_members['members']:
                                if camp_member:

                                    try:
                                        activity = client.reports.email_activity.get(campaign_id=campaign['id'], subscriber_hash=camp_member['id'])
                                        if activity['activity']:
                                            action = activity['activity'][0]['action']
                                        else:
                                            action = 'sent'
                                        subscriber =True
                                    except Exception as e:
                                        if e.args[0]['status'] == 404:
                                            subscriber = False
                                            action = 'Planned'

                                        else :
                                            raise ValidationError(e)


                                    odoo_member = self.env['res.partner'].search([
                                        ('member_id', '=', camp_member['id'])
                                    ])


                                    if odoo_member:
                                        self.env['res.partner'].write({'member_id': camp_member['id'],
                                                                       'email': camp_member['email_address'],
                                                                       'name': camp_member['merge_fields']['FNAME'] + " " +
                                                                               camp_member['merge_fields']['LNAME'] if
                                                                       camp_member['merge_fields']['FNAME'] else
                                                                       str.split(camp_member['email_address'], '@')[0],
                                                                       'phone': camp_member['merge_fields']['PHONE'],
                                                                       'member_status': action

                                                                       })


                                        campaign_partner_id.append(odoo_member.id)

                                    else:
                                        odoo_member=self.env['res.partner'].create({'member_id': camp_member['id'],
                                                                       'email': camp_member['email_address'],
                                                                       'name': camp_member['merge_fields'][
                                                                                   'FNAME'] + " " +
                                                                               camp_member['merge_fields']['LNAME'] if
                                                                       camp_member['merge_fields']['FNAME'] else
                                                                       str.split(camp_member['email_address'], '@')[0],
                                                                       'phone': camp_member['merge_fields']['PHONE'],
                                                                       'member_status': activity['activity'][0][
                                                                           'action'] if activity[
                                                                           'activity'] else 'Planned'

                                                                       })

                                        campaign_partner_id.append(odoo_member.id)

                                    part_campaign = self.env['partner.campaign'].search(
                                        [('campaign_id', '=', campaign['id'])])
                                    if part_campaign:
                                        if campaign['status'] != 'save':
                                            self.env['partner.campaign'].write({'member_id': camp_member['id'],
                                                                                'email': camp_member['email_address'],
                                                                                'member_name':
                                                                                    camp_member['merge_fields'][
                                                                                        'FNAME'] + " " +
                                                                                    camp_member['merge_fields']['LNAME']
                                                                                    if camp_member['merge_fields'][
                                                                                        'FNAME'] else str.split(
                                                                                        camp_member['email_address'],
                                                                                        '@')[0],
                                                                                'phone': camp_member['merge_fields'][
                                                                                    'PHONE'],
                                                                                'member_status': action,
                                                                                'name': campaign['settings']['title'],
                                                                                'customer': campaign['emails_sent'],
                                                                                'list_id': campaign['recipients'][
                                                                                    'list_id'] if
                                                                                campaign['recipients'][
                                                                                    'list_id'] else None,
                                                                                'list_name': campaign['recipients'][
                                                                                    'list_name'],
                                                                                'send_date': campaign['send_time'].split('T')[0],
                                                                                'status': campaign['status'],
                                                                                'customer': campaign['emails_sent'],
                                                                                'total_open':
                                                                                    campaign['report_summary'][
                                                                                        'opens'] if campaign[
                                                                                        'report_summary'] else 0,
                                                                                'total_clicks':
                                                                                    campaign['report_summary'][
                                                                                        'clicks'] if campaign[
                                                                                        'report_summary'] else 0,
                                                                                'total_order':
                                                                                    campaign['report_summary'][
                                                                                        'ecommerce']['total_orders'] if
                                                                                    campaign['report_summary'] else 0,
                                                                                'total_revenue':
                                                                                    campaign['report_summary'][
                                                                                        'ecommerce']['total_revenue'] if
                                                                                    campaign['report_summary'] else 0,
                                                                                'total_spent':
                                                                                    campaign['report_summary'][
                                                                                        'ecommerce']['total_spent'] if
                                                                                    campaign['report_summary'] else 0,
                                                                                'list_id': campaign['recipients'][
                                                                                    'list_id'],
                                                                                'list_name': campaign['recipients'][
                                                                                    'list_name'],
                                                                                'total_recipient':
                                                                                    campaign['recipients'][
                                                                                        'recipient_count'],
                                                                                'customer_ids': odoo_member.id
                                                                                })
                                        else:
                                            self.env['partner.campaign'].write({'member_id': camp_member['id'],
                                                                                'email': camp_member['email_address'],
                                                                                'member_name':
                                                                                    camp_member['merge_fields'][
                                                                                        'FNAME'] + " " +
                                                                                    camp_member['merge_fields']['LNAME']
                                                                                    if camp_member['merge_fields'][
                                                                                        'FNAME'] else str.split(
                                                                                        camp_member['email_address'],
                                                                                        '@')[0],
                                                                                'phone': camp_member['merge_fields'][
                                                                                    'PHONE'],
                                                                                'member_status': action,
                                                                                'name': campaign['settings']['title'],
                                                                                'customer': campaign['emails_sent'],
                                                                                'send_date':campaign['send_time'].split('T')[0],
                                                                                'list_id': campaign['recipients'][
                                                                                    'list_id'] if
                                                                                campaign['recipients'][
                                                                                    'list_id'] else None,
                                                                                'list_name': campaign['recipients'][
                                                                                    'list_name'],
                                                                                'status': campaign['status'],
                                                                                'customer': campaign['emails_sent'],
                                                                                'list_id': campaign['recipients'][
                                                                                    'list_id'],
                                                                                'list_name': campaign['recipients'][
                                                                                    'list_name'],
                                                                                'total_recipient':
                                                                                    campaign['recipients'][
                                                                                        'recipient_count'],
                                                                                'customer_ids': odoo_member.id
                                                                                })
                                    else:
                                        if campaign['status'] != 'save':
                                            self.env['partner.campaign'].create({'member_id': camp_member['id'],
                                                                                'email': camp_member['email_address'],
                                                                                'member_name':
                                                                                    camp_member['merge_fields'][
                                                                                        'FNAME'] + " " +
                                                                                    camp_member['merge_fields']['LNAME']
                                                                                    if camp_member['merge_fields'][
                                                                                        'FNAME'] else str.split(
                                                                                        camp_member['email_address'],
                                                                                        '@')[0],
                                                                                'phone': camp_member['merge_fields'][
                                                                                    'PHONE'],
                                                                                'member_status': action,
                                                                                'name': campaign['settings']['title'],
                                                                                'customer': campaign['emails_sent'],
                                                                                'list_id': campaign['recipients'][
                                                                                    'list_id'] if
                                                                                campaign['recipients'][
                                                                                    'list_id'] else None,
                                                                                'list_name': campaign['recipients'][
                                                                                    'list_name'],
                                                                                'status': campaign['status'],
                                                                                'customer': campaign['emails_sent'],
                                                                                'total_open':
                                                                                    campaign['report_summary'][
                                                                                        'opens'] if campaign[
                                                                                        'report_summary'] else 0,
                                                                                'total_clicks':
                                                                                    campaign['report_summary'][
                                                                                        'clicks'] if campaign[
                                                                                        'report_summary'] else 0,
                                                                                'total_order':
                                                                                    campaign['report_summary'][
                                                                                        'ecommerce']['total_orders'] if
                                                                                    campaign['report_summary'] else 0,
                                                                                'total_revenue':
                                                                                    campaign['report_summary'][
                                                                                        'ecommerce']['total_revenue'] if
                                                                                    campaign['report_summary'] else 0,
                                                                                'total_spent':
                                                                                    campaign['report_summary'][
                                                                                        'ecommerce']['total_spent'] if
                                                                                    campaign['report_summary'] else 0,
                                                                                 'send_date':campaign['send_time'].split('T')[0],
                                                                                'list_id': campaign['recipients'][
                                                                                    'list_id'],
                                                                                'list_name': campaign['recipients'][
                                                                                    'list_name'],
                                                                                'total_recipient':
                                                                                    campaign['recipients'][
                                                                                        'recipient_count'],
                                                                                'customer_ids': odoo_member.id
                                                                                })
                                        else:
                                            self.env['partner.campaign'].create({'member_id': camp_member['id'],
                                                                                'email': camp_member['email_address'],
                                                                                'member_name':
                                                                                    camp_member['merge_fields'][
                                                                                        'FNAME'] + " " +
                                                                                    camp_member['merge_fields']['LNAME']
                                                                                    if camp_member['merge_fields'][
                                                                                        'FNAME'] else str.split(
                                                                                        camp_member['email_address'],
                                                                                        '@')[0],
                                                                                'phone': camp_member['merge_fields'][
                                                                                    'PHONE'],
                                                                                'member_status': action,
                                                                                'name': campaign['settings']['title'],
                                                                                'customer': campaign['emails_sent'],
                                                                                'list_id': campaign['recipients'][
                                                                                    'list_id'] if
                                                                                campaign['recipients'][
                                                                                    'list_id'] else None,
                                                                                 'send_date':
                                                                                campaign['send_time'].split('T')[
                                                                                         0],
                                                                                'list_name': campaign['recipients'][
                                                                                    'list_name'],
                                                                                'status': campaign['status'],
                                                                                'customer': campaign['emails_sent'],
                                                                                'list_id': campaign['recipients'][
                                                                                    'list_id'],
                                                                                'list_name': campaign['recipients'][
                                                                                    'list_name'],
                                                                                'total_recipient':
                                                                                    campaign['recipients'][
                                                                                        'recipient_count'],
                                                                                'customer_ids': odoo_member.id
                                                                                })



                            if campaign['status'] != 'save':
                                self.env['mailchimp.campaign'].create({
                                    'mailchimp_id': campaign['id'],
                                    'mailchimp_connector_id': self.id,
                                    'name': campaign['settings']['title'],
                                    'customer': campaign['emails_sent'],
                                    'total_open': campaign['report_summary']['opens'],
                                    'total_clicks': campaign['report_summary']['clicks'],
                                    'total_order': campaign['report_summary']['ecommerce']['total_orders'],
                                    'total_revenue': campaign['report_summary']['ecommerce']['total_revenue'],
                                    'total_spent': campaign['report_summary']['ecommerce']['total_spent'],
                                    'list_id': campaign['recipients']['list_id'] if campaign['recipients'][
                                        'list_id'] else None,
                                    'send_date': campaign['send_time'].split('T')[0],
                                    'list_name': campaign['recipients']['list_name'],
                                    'total_recipient': campaign['recipients']['recipient_count'],
                                    'status': campaign['status'],
                                    'many_customer_ids': [[6, 0, campaign_partner_id]]
                                })


                            else:
                                self.env['mailchimp.campaign'].create({
                                    'mailchimp_id': campaign['id'],
                                    'mailchimp_connector_id': self.id,
                                    'name': campaign['settings']['title'],
                                    'customer': campaign['emails_sent'],
                                    'total_open': campaign['tracking']['opens'],
                                    'send_date': campaign['send_time'].split('T')[0],
                                    'list_id': campaign['recipients']['list_id'] if campaign['recipients'][
                                        'list_id'] else None,
                                    'list_name': campaign['recipients']['list_name'],
                                    'total_recipient': campaign['recipients']['recipient_count'],
                                    'status': campaign['status'],
                                    'many_customer_ids': [[6, 0, campaign_partner_id]]
                                })


                        else:
                            for camp_member in campaign_members['members']:
                                if camp_member:
                                    odoo_member = self.env['res.partner'].search([
                                        ('member_id', '=', camp_member['id'])
                                    ])
                                    try:
                                        activity = client.reports.email_activity.get(campaign_id=campaign['id'], subscriber_hash=camp_member[ 'id'])
                                        if activity['activity']:
                                            action = activity['activity'][0]['action']
                                        else:
                                            action = 'Sent'
                                        subscriber =True
                                    except Exception as e:
                                        if e.args[0]['status'] == 404:
                                            subscriber = False
                                            action = 'Planned'

                                        else :
                                            raise ValidationError(e)

                                    if odoo_member:
                                        self.env['res.partner'].write({'member_id': camp_member['id'],
                                                                       'email': camp_member['email_address'],
                                                                       'name': camp_member['merge_fields']['FNAME'] + " " +
                                                                               camp_member['merge_fields']['LNAME'] if
                                                                       camp_member['merge_fields']['FNAME'] else
                                                                       str.split(camp_member['email_address'], '@')[0],
                                                                       'member_status': action

                                                                       })
                                        campaign_partner_id.append(odoo_member.id)
                                    else:
                                        odoo_member = self.env['res.partner'].create({'member_id': camp_member['id'],
                                                                                  'email': camp_member['email_address'],
                                                                                  'name': camp_member['merge_fields']['FNAME'] + " " +
                                                                                          camp_member['merge_fields']['LNAME'] if
                                                                                  camp_member['merge_fields']['FNAME'] else
                                                                                  str.split( camp_member['email_address'],'@')[0],
                                                                                  'phone': camp_member['merge_fields']['PHONE'],
                                                                                  'member_status':action

                                                                                  })
                                        campaign_partner_id.append(odoo_member.id)

                                    part_campaign = self.env['partner.campaign'].search(
                                        [('campaign_id', '=', campaign['id'])])
                                    if part_campaign:
                                        if campaign['status']!='save':
                                            self.env['partner.campaign'].write({'member_id': camp_member['id'],
                                                                             'email': camp_member['email_address'],
                                                                             'member_name': camp_member['merge_fields']['FNAME'] + " " +camp_member['merge_fields']['LNAME']
                                                                             if camp_member['merge_fields']['FNAME'] else str.split(camp_member['email_address'], '@')[0],
                                                                             'phone': camp_member['merge_fields']['PHONE'],
                                                                             'member_status': action,
                                                                             'name': campaign['settings']['title'],
                                                                             'customer': campaign['emails_sent'],
                                                                             'list_id': campaign['recipients']['list_id'] if campaign['recipients']['list_id'] else None,
                                                                             'list_name': campaign['recipients']['list_name'],
                                                                             'status': campaign['status'],
                                                                            'send_date': campaign['send_time'].split('T')[0],
                                                                            'customer': campaign['emails_sent'],
                                                                            'total_open': campaign['report_summary'][ 'opens'] if campaign['report_summary'] else 0,
                                                                            'total_clicks': campaign['report_summary']['clicks'] if campaign['report_summary'] else 0,
                                                                            'total_order': campaign['report_summary']['ecommerce']['total_orders'] if campaign['report_summary'] else 0,
                                                                            'total_revenue': campaign['report_summary']['ecommerce']['total_revenue'] if campaign['report_summary'] else 0,
                                                                            'total_spent':campaign['report_summary']['ecommerce']['total_spent'] if campaign['report_summary'] else 0,
                                                                            'list_id': campaign['recipients']['list_id'],
                                                                            'list_name': campaign['recipients'][ 'list_name'],
                                                                            'total_recipient': campaign['recipients']['recipient_count'],
                                                                             'customer_ids': odoo_member.id
                                                                             })
                                        else:
                                            self.env['partner.campaign'].write({'member_id': camp_member['id'],
                                                                                'email': camp_member['email_address'],
                                                                                'member_name':
                                                                                    camp_member['merge_fields'][
                                                                                        'FNAME'] + " " +
                                                                                    camp_member['merge_fields']['LNAME']
                                                                                    if camp_member['merge_fields'][
                                                                                        'FNAME'] else str.split(
                                                                                        camp_member['email_address'],
                                                                                        '@')[0],
                                                                                'phone': camp_member['merge_fields'][
                                                                                    'PHONE'],
                                                                                'send_date': campaign['send_time'].split('T')[0],
                                                                                'member_status': action,
                                                                                'name': campaign['settings']['title'],
                                                                                'customer': campaign['emails_sent'],
                                                                                'list_id': campaign['recipients'][
                                                                                    'list_id'] if
                                                                                campaign['recipients'][
                                                                                    'list_id'] else None,
                                                                                'list_name': campaign['recipients'][
                                                                                    'list_name'],
                                                                                'status': campaign['status'],
                                                                                'customer': campaign['emails_sent'],
                                                                                'list_id': campaign['recipients'][
                                                                                    'list_id'],
                                                                                'list_name': campaign['recipients'][
                                                                                    'list_name'],
                                                                                'total_recipient':
                                                                                    campaign['recipients'][
                                                                                        'recipient_count'],
                                                                                'customer_ids': odoo_member.id
                                                                                })
                                    else:
                                        if campaign['status'] != 'save':
                                            self.env['partner.campaign'].create({'member_id': camp_member['id'],
                                                                                'email': camp_member['email_address'],
                                                                                'member_name':
                                                                                    camp_member['merge_fields'][
                                                                                        'FNAME'] + " " +
                                                                                    camp_member['merge_fields']['LNAME']
                                                                                    if camp_member['merge_fields'][
                                                                                        'FNAME'] else str.split(
                                                                                        camp_member['email_address'],
                                                                                        '@')[0],
                                                                                'phone': camp_member['merge_fields'][
                                                                                    'PHONE'],
                                                                                'member_status': action,
                                                                                'name': campaign['settings']['title'],
                                                                                'customer': campaign['emails_sent'],
                                                                                'list_id': campaign['recipients'][
                                                                                    'list_id'] if
                                                                                campaign['recipients'][
                                                                                    'list_id'] else None,
                                                                                'list_name': campaign['recipients'][
                                                                                    'list_name'],
                                                                                'status': campaign['status'],
                                                                                'customer': campaign['emails_sent'],
                                                                                'total_open':
                                                                                    campaign['report_summary'][
                                                                                        'opens'] if campaign[
                                                                                        'report_summary'] else 0,
                                                                                 'send_date':
                                                                                     campaign['send_time'].split('T')[
                                                                                         0],
                                                                                'total_clicks':
                                                                                    campaign['report_summary'][
                                                                                        'clicks'] if campaign[
                                                                                        'report_summary'] else 0,
                                                                                'total_order':
                                                                                    campaign['report_summary'][
                                                                                        'ecommerce']['total_orders'] if
                                                                                    campaign['report_summary'] else 0,
                                                                                'total_revenue':
                                                                                    campaign['report_summary'][
                                                                                        'ecommerce']['total_revenue'] if
                                                                                    campaign['report_summary'] else 0,
                                                                                'total_spent':
                                                                                    campaign['report_summary'][
                                                                                        'ecommerce']['total_spent'] if
                                                                                    campaign['report_summary'] else 0,
                                                                                'list_id': campaign['recipients'][
                                                                                    'list_id'],
                                                                                'list_name': campaign['recipients'][
                                                                                    'list_name'],
                                                                                'total_recipient':
                                                                                    campaign['recipients'][
                                                                                        'recipient_count'],
                                                                                'customer_ids': odoo_member.id
                                                                                })
                                        else:
                                            self.env['partner.campaign'].create({'member_id': camp_member['id'],
                                                                                'email': camp_member['email_address'],
                                                                                'member_name':
                                                                                    camp_member['merge_fields'][
                                                                                        'FNAME'] + " " +
                                                                                    camp_member['merge_fields']['LNAME']
                                                                                    if camp_member['merge_fields'][
                                                                                        'FNAME'] else str.split(
                                                                                        camp_member['email_address'],
                                                                                        '@')[0],
                                                                                'phone': camp_member['merge_fields'][
                                                                                    'PHONE'],
                                                                                'member_status': action,
                                                                                'name': campaign['settings']['title'],
                                                                                'customer': campaign['emails_sent'],
                                                                                'list_id': campaign['recipients'][
                                                                                    'list_id'] if
                                                                                campaign['recipients'][
                                                                                    'list_id'] else None,
                                                                                'list_name': campaign['recipients'][
                                                                                    'list_name'],
                                                                                 'send_date':
                                                                                     campaign['send_time'].split('T')[
                                                                                         0],
                                                                                'status': campaign['status'],
                                                                                'customer': campaign['emails_sent'],
                                                                                'list_id': campaign['recipients'][
                                                                                    'list_id'],
                                                                                'list_name': campaign['recipients'][
                                                                                    'list_name'],
                                                                                'total_recipient':
                                                                                    campaign['recipients'][
                                                                                        'recipient_count'],
                                                                                'customer_ids': odoo_member.id
                                                                                })



                            if campaign['status'] != 'save':
                                    self.env['mailchimp.campaign'].write({
                                        'mailchimp_id': campaign['id'],
                                        'mailchimp_connector_id': self.id,
                                        'name': campaign['settings']['title'],
                                        'customer': campaign['emails_sent'],
                                        'total_open': campaign['report_summary']['opens'],
                                        'total_clicks': campaign['report_summary']['clicks'],
                                        'total_order': campaign['report_summary']['ecommerce']['total_orders'],
                                        'total_revenue': campaign['report_summary']['ecommerce']['total_revenue'],
                                        'total_spent': campaign['report_summary']['ecommerce']['total_spent'],
                                        'list_id': campaign['recipients']['list_id'],
                                        'list_name': campaign['recipients']['list_name'],
                                        'send_date': campaign['send_time'].split('T')[0],
                                        'total_recipient': campaign['recipients']['recipient_count'],
                                        'status': campaign['status'],
                                        'many_customer_ids': [[6, 0, campaign_partner_id]]
                                    })

                lists = client.lists.all(get_all=True)
                for list in lists['lists']:
                    list_id = list['id']
                    members = client.lists.members.all(list_id,
                                                       fields="members.id,members.merge_fields,members.status,members.email_address",
                                                       count=10, offset=0)
                    partner_ids = []
                    for member in members['members']:

                        if member:
                            odoo_member = self.env['res.partner'].search([
                                ('member_id', '=', member['id'])
                            ])
                            # activity = client.lists.members.activity.all(list_id=list_id,
                            #                                              subscriber_hash=member['id'])
                            # member_status = activity['activity'][0]['action']
                            if not odoo_member:
                                partner = self.env['res.partner'].create({
                                    'member_id': member['id'],
                                    'email': member['email_address'] if member['email_address'] else '',
                                    'phone': member['merge_fields']['PHONE'],
                                    'name': member['merge_fields']['FNAME'] + " " + member['merge_fields']['LNAME'] if
                                    member['merge_fields']['FNAME'] else str.split(member['email_address'], '@')[0],
                                    'phone': member['merge_fields']['PHONE']
                                    # 'member_status':member['status']
                                })
                                # self.env['mailchimp.campaign'].create({'emailL':'wajahat'})
                                partner_ids.append(partner.id)

                            else:
                                self.env['res.partner'].write({
                                    'member_id': member['id'],
                                    'email': member['email_address'],
                                    'name': member['merge_fields']['FNAME'] + " " + member['merge_fields']['LNAME'] if
                                    member['merge_fields']['FNAME'] else str.split(member['email_address'], '@')[0],
                                    'phone': member['merge_fields']['PHONE']
                                    # 'member_status': member['status']

                                })
                                partner_ids.append(odoo_member.id)
                    odoo_list = self.env['mailchimp.list'].search([
                        ('mailchimp_id', '=', list_id)
                    ])
                    if not odoo_list:

                        self.env['mailchimp.list'].create({
                            'name': list['name'],
                            'permission_reminder': list['permission_reminder'],
                            'address1': list['contact']['address1'],
                            'address2': list['contact']['address2'],
                            'city': list['contact']['city'],
                            'company': list['contact']['company'],
                            'country': list['contact']['country'],
                            'phone': list['contact']['phone'],
                            'state': list['contact']['state'],
                            'zip': list['contact']['zip'],
                            'from_email': list['campaign_defaults']['from_email'],
                            'from_name': list['campaign_defaults']['from_name'],
                            'subject': list['campaign_defaults']['subject'],
                            'mailchimp_id': list['id'],
                            'mailchimp_connector_id': self.id,
                            'many_customer_ids': [[6, 0, partner_ids]]
                        })


                    else:
                        odoo_list.write({
                            'name': list['name'],
                            'permission_reminder': list['permission_reminder'],
                            'address1': list['contact']['address1'],
                            'address2': list['contact']['address2'],
                            'city': list['contact']['city'],
                            'company': list['contact']['company'],
                            'country': list['contact']['country'],
                            'phone': list['contact']['phone'],
                            'state': list['contact']['state'],
                            'zip': list['contact']['zip'],
                            'from_email': list['campaign_defaults']['from_email'],
                            'from_name': list['campaign_defaults']['from_name'],
                            'subject': list['campaign_defaults']['subject'],
                            'mailchimp_connector_id': self.id,
                            'many_customer_ids': [[6, 0, partner_ids]]
                        })

                self.env.cr.commit()
            else:
                raise Warning(_("Check MailChimp credentials.", ))

        except Exception as e:
            raise ValidationError(e)



