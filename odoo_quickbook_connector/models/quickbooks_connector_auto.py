import base64
from base64 import b64encode
from datetime import datetime

from openerp import _
from odoo import models, fields, api
from openerp.osv import osv
from openerp.exceptions import Warning
from . import wizard
import os



class QuickBooksConnector(models.Model):
    _name = 'quickbooks.autoconnector'


    field_name = fields.Char('quickbooks_autoconnector')
    # history_line = fields.One2many('sync.history', 'sync_id', copy=True)
    customers = fields.Boolean('Import/Update Customers')
    invoices = fields.Boolean('Import/Update Invoices')
    products = fields.Boolean('Export/Update Products')
    interval_number_customer = fields.Integer(string="Sync Interval Unit")
    interval_unit_customer = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('work_days', 'Work Days'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Interval Unit')
    interval_number_invoice = fields.Integer(string="Sync Interval Unit")
    interval_unit_invoice = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('work_days', 'Work Days'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Interval Unit')
    interval_number_product = fields.Integer(string="Sync Interval Unit")
    interval_unit_product = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('work_days', 'Work Days'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Interval Unit')

    def sync_data(self):
        """

        :return:
        """
        done = False
        while not done:
            try:
                scheduler = self.env['ir.cron'].search([('name', '=', 'Customers Scheduler')])
                if not scheduler:
                    scheduler = self.env['ir.cron'].search([('name', '=', 'Customers Scheduler'),('active','=',False)])
                scheduler.active = self.customers
                scheduler.interval_number = self.interval_number_customer
                scheduler.interval_type = self.interval_unit_customer

                scheduler = self.env['ir.cron'].search([('name', '=', 'Products Scheduler')])
                if not scheduler:
                    scheduler = self.env['ir.cron'].search([('name', '=', 'Products Scheduler'),('active','=',False)])
                scheduler.active = self.products
                scheduler.interval_number = self.interval_number_product
                scheduler.interval_type = self.interval_unit_product

                scheduler = self.env['ir.cron'].search([('name', '=', 'Invoice Scheduler')])
                if not scheduler:
                    scheduler = self.env['ir.cron'].search([('name', '=', 'Invoice Scheduler'),('active','=',False)])
                scheduler.active = self.sales_orders
                scheduler.interval_number = self.interval_number_invoice
                scheduler.interval_type = self.interval_unit_invoice

                self.env.cr.commit()
                done = True
            except Exception as e:
                print (str(e))

