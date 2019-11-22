# -*- coding: utf-8 -*-
import shopify
import datetime
from odoo import models, fields, api
from openerp.osv import osv


class ShopifyWizard(models.TransientModel):
    _name = 'shopify.wizard'

    import_items = fields.Selection(selection=[('orders', 'orders'), ('customers', 'customers')], string='Import')
    export_items = fields.Selection(selection=[('products', 'products')], string='Export')

    def connect_to_shopify(self):

        """
        connecting shopify to Odoo with provided credentials
        """

        shop_name = self.env.user.shop_name
        api_key = self.env.user.api_key
        api_password = self.env.user.api_password
        api_secret_key = self.env.user.api_secret_key
        shop_url = "https://%s:%s@%s.myshopify.com/admin" % (api_key, api_password, shop_name)
        shopify.ShopifyResource.set_site(shop_url)
        shopify.Session.setup(api_key=api_key, secret=api_secret_key)

    @api.one
    def export_to_shopify(self):

        """
        get shopify data from user and call functions to import orders, customers
        :return:
        """

        self.connect_to_shopify()
        if str(self.export_items) == 'products':
            self.export_products()

    def export_products(self):

        """
        This functions export products of the user to his shopify shop
        :return:
        """

        export_products = ""
        products = self.env['product.template'].search([('create_uid', '=', self.env.user.id)])
        shopify_products = shopify.Product.find(limit=250)
        for product in products:
            already_exist = False
            for shopify_product in shopify_products:
                if shopify_product.attributes['title'] == product.name:
                    already_exist = True
                    break
            if already_exist:
                continue
            export_products = export_products + product.name + " "
            new_product = shopify.Product()
            new_product.title = product.name
            new_product.body_html =  product.description
            new_product.product_type = product.type
            product_variant = shopify.Variant({"title": "v1", "price": 123123})
            new_product.variants = [product_variant]
            new_product.save()
        if export_products:
            raise osv.except_osv("Products Export Success", (export_products + " exported successfully"))
        else:
            raise osv.except_osv("Products Export", "non product to export")

    @api.one
    def import_from_shopify(self):

        """
        get shopify data from user and call functions to import orders, customers
        :return:
        """

        self.connect_to_shopify()
        if str(self.import_items) == 'orders':
            self.import_orders()
        if str(self.import_items) == 'customers':
            self.import_customers()

    def import_customers(self):

        """
        This function import customers from shopify to odoo
        :return:
        """

        is_imported = False
        customers = shopify.Customer.find()
        for customer in customers:
            if not self.env['res.partner'].search([('name', '=',str(customer.attributes['email']))]):

                name = ""
                if customer.attributes['first_name']:
                    name = customer.attributes['first_name'] + " " + customer.attributes['last_name']
                else:
                    name = customer.attributes['email']
                is_imported = True
                self.env['res.partner'].create({
                    'name': name,
                    'phone': customer.attributes['phone'],
                    'email': customer.attributes['email'],
                    'comment': customer.attributes['note'],
                    'street': customer.attributes['default_address'].attributes['address1'],
                    'street2': customer.attributes['default_address'].attributes['address2'],
                    'city': customer.attributes['default_address'].attributes['city'],
                    'zip': customer.attributes['default_address'].attributes['zip'],
                    'country_id': self.env['res.country'].search(
                        [('name', '=', customer.attributes['default_address'].attributes['country'])]).id
                })
        self.env.cr.commit()
        if is_imported:
            raise osv.except_osv("Customers Import Success", 'customers imported success full')
        else:
            raise osv.except_osv("Customers Import Message", 'no customer to import')

    def import_orders(self):

        """
        This function Import orders from shopify and insert them in odoo
        It rejects orders with no customers
        :return:
        """

        orders = shopify.Order.find()
        order_with_no_customers = []
        imported_orders_name = ''
        for order in orders:
            name = ''
            customer = {}
            if 'customer' in order.attributes:
                if order.attributes['customer'].attributes['first_name']:
                    name = order.attributes['customer'].attributes['first_name'] + " " + \
                           order.attributes['customer'].attributes['last_name']
                else:
                    name = order.attributes['customer'].attributes['email']

                customer = self.env['res.partner'].search([('name', '=', name)])
                if customer:
                    customer = customer[0]
            else:
                order_with_no_customers.append(order)
                continue
            if not name:
                name = 'dummy@gmail.com'
            if not customer:
                customer = self.env['res.partner'].create({
                    'name': name,
                    'phone': order.attributes['customer'].attributes['phone'],
                    'email': order.attributes['customer'].attributes['email'],
                    'comment': order.attributes['customer'].attributes['note'],
                })
            odoo_order = self.env['sale.order'].create({
                'partner_id': customer.id,
                'date_order': order.attributes['created_at'],
                'amount_tax': float(order.attributes['total_tax']),
                'amount_total': float(order.attributes['total_price']),
                'state': 'sale',
            })
            imported_orders_name += odoo_order.name + ' '
            for item in order.attributes['line_items']:
                product_id = item.attributes['product_id']
                if product_id:
                    product = shopify.Product.find(id_=product_id)
                    if product:
                        odoo_product_template = self.env['product.template'].\
                            search([('name', '=', str(product.attributes['title']))])

                        if not odoo_product_template:
                            odoo_product_template = self.env['product.template'].create({
                                'name': item.attributes['title'],
                                'price': float(item.attributes['price'])
                            })
                            odoo_product = self.env['product.product'].create({
                                'product_tmpl_id':odoo_product_template.id
                            })
                        else:
                            odoo_product = self.env['product.product'].search([('product_tmpl_id',
                                                                                '=',odoo_product_template.id)])
                    self.env['sale.order.line'].create({
                        'product_id': odoo_product[0].id,
                        'order_id': odoo_order.id,
                        'product_oum_qty': item.attributes['quantity'],
                        'qty_invoiced': item.attributes['fulfillable_quantity'],
                        'name': item.attributes['name'],
                        'product_uom': self.env.ref('product.product_uom_unit').id,
                    })
                else:
                    odoo_order = self.env['sale.order'].create({
                        'partner_id': customer.id,
                        'date_order': order.attributes['created_at'],
                        'amount_tax': float(order.attributes['total_tax']),
                        'amount_total': float(order.attributes['total_price']),
                        'state': 'sale',

                    })
                self.env.cr.commit()
        order_names = ''
        for order in order_with_no_customers:
            order_names += str(order.attributes['name']) + ' \n'
        raise osv.except_osv("orders import message", (imported_orders_name + " imported \n" + order_names + " could not import these because they have no customer"))