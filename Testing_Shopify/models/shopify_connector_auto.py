from odoo import models, fields, api


class ShopifyConnector(models.Model):
    _name = 'shopify.autoconnector'

    field_name = fields.Char('shopify_autoconnector')
    history_line = fields.One2many('sync.history', 'sync_id', copy=True)
    customers = fields.Boolean('Auto Sync Customers')
    sales_orders = fields.Boolean('Auto Sync Sale Orders')
    products = fields.Boolean('Auto Sync Products')
    interval_number_customer = fields.Integer(string="Sync Interval Unit")
    interval_unit_customer = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('work_days', 'Work Days'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Interval Unit')
    interval_number_SO = fields.Integer(string="Sync Interval Unit")
    interval_unit_SO = fields.Selection([
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
        done = False
        while not done:
            try:
                scheduler = self.env['ir.cron'].search([('name', '=', 'Customers Scheduler')])
                if not scheduler:
                    scheduler = self.env['ir.cron'].search([('name', '=', 'Customers Scheduler'),
                                                            ('active', '=', False)])
                scheduler.active = self.customers
                scheduler.interval_number = self.interval_number_customer
                scheduler.interval_type = self.interval_unit_customer

                scheduler = self.env['ir.cron'].search([('name', '=', 'Products Scheduler')])
                if not scheduler:
                    scheduler = self.env['ir.cron'].search([('name', '=', 'Products Scheduler'),
                                                            ('active', '=', False)])
                scheduler.active = self.products
                scheduler.interval_number = self.interval_number_product
                scheduler.interval_type = self.interval_unit_product

                scheduler = self.env['ir.cron'].search([('name', '=', 'Sale Order Scheduler')])
                if not scheduler:
                    scheduler = self.env['ir.cron'].search([('name', '=', 'Sale Order Scheduler'),
                                                            ('active', '=', False)])
                scheduler.active = self.sales_orders
                scheduler.interval_number = self.interval_number_SO
                scheduler.interval_type = self.interval_unit_SO

                self.env.cr.commit()
                done = True
            except Exception as e:
                print(str(e))

