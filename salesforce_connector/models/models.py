# -*- coding: utf-8 -*-

from odoo import models, fields, api
from simple_salesforce import Salesforce
from openerp import _
from openerp.exceptions import Warning, ValidationError
from openerp.osv import osv


class SalesForceSettingModel(models.Model):

    _inherit = 'res.users'

    sf_username = fields.Char(string='Username')
    sf_password = fields.Char(string='Password')
    sf_security_token = fields.Char(string='Security Token')

    def test_credentials(self):
        """
        Tests the user SalesForce account credentials

        :return:
        """
        try:
            record = self._cr.execute("SELECT name FROM res_partner")
            sf = Salesforce(username=self.sf_username, password=self.sf_password, security_token=self.sf_security_token)

        except Exception as e:
            raise Warning(_(str(e)))

        raise osv.except_osv(_("Success!"), (_("Credentials Test Successful")))


class CustomPartner(models.Model):
    """
    Add fields in res.partner

    """
    _inherit = "res.partner"
    sf_customer_id = fields.Char(string="SalesForce Customer Id")
    sf_customer_name = fields.Char(string="SalesForce Customer Name", readonly=True)


class CustomLead(models.Model):
    """
    Adds custom fields in crm.lead model
    """
    _inherit = "crm.lead"

    sf_name = fields.Char(string="Sales Force Name")
    sf_opportunity_id = fields.Char(string="SalesForce Opportunity Id")
    Services_Project__c = fields.Char(string="Services - Project Closeout Fees")
    Total__c = fields.Char(string="Total Licenses")
    Total_Services__c = fields.Char(string="Total Services")
    Duration__c = fields.Char(string="Duration in Months")
    Initial_Lisence__c = fields.Char(string="Initial License Fee")
    Recurring_License_Fee__c = fields.Char(string="Recurring License Fee")
    Services_Set_Up_Fee__c = fields.Char(string="Services Set Up Fees")
    Services__c = fields.Char(string="Services - Project Support Fees")
