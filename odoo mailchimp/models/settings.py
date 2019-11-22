from mailchimp3 import MailChimp
from openerp import _
from odoo import models, fields, api
from openerp.osv import osv
from openerp.exceptions import ValidationError


class MailchimpSetting(models.Model):
    _name = 'mailchimp.settings'

    mailchimp_username = fields.Char('username')
    api_key = fields.Char('API Key')
    field_name = fields.Char('mailchimp_settings', required=True)

    def test_connection(self):
        try:
            client = MailChimp(mc_user=self.mailchimp_username, mc_api=self.api_key)
            client.lists.all(get_all=True, fields="lists.name,lists.id")
            self.env.user.mailchimp_username = self.mailchimp_username
            self.env.user.api_key = self.api_key
            cust = self.env['res.partner'].search([])
            print(cust)
            self.env.cr.commit()

        except Exception as e:
            raise ValidationError('Connection Failed '+str(e))
        raise osv.except_osv("Success!", " Connection Successful !")
