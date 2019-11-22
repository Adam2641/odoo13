import base64
from datetime import datetime
import shopify
from openerp import _
from odoo import models, fields, api
from openerp.osv import osv
from openerp.exceptions import Warning
import time


class ExportProduct(models.Model):
    _inherit = "product.template"

    def export_product(self):

        """
        Exporting user products to their shopify shop
        :return:
        """

        shop_name = self.env.user.shop_name
        api_key = self.env.user.api_key
        api_password = self.env.user.api_password
        api_secret_key = self.env.user.api_secret_key
        shop_url = "https://%s:%s@%s.myshopify.com/admin/api/2019-07" % (api_key, api_password, shop_name)
        shopify.ShopifyResource.set_site(shop_url)
        shopify.Session.setup(api_key=api_key, secret=api_secret_key)
        exported_products = ""
        products = self.env['product.template'].search([('id', 'in', self.ids)])
        shopify_products = shopify.Product.find()

        for product in products:
            already_exist = False
            for shopify_product in shopify_products:
                if shopify_product.attributes['title'] == product.name:
                    already_exist = True
                    break

            if already_exist:
                continue

            exported_products = exported_products + product.name + " "
            new_product = shopify.Product()
            new_product.title = product.name
            new_product.body_html = product.description
            new_product.product_type = product.type
            product_variant = shopify.Variant({"title": "v1", "price": 123123})
            new_product.variants = [product_variant]
            new_product.save()

        if exported_products:
            raise osv.except_osv("Products Export Success", (exported_products + " exported successfully"))
        else:
            raise osv.except_osv("Products Export Message", "non product to export")


class ShopifyConnector(models.Model):
    _name = 'shopify.connector'

    last_sync_date = fields.Datetime('Last Sync Date', readonly=True, default=fields.Datetime.now)
    field_name = fields.Char('shopify_connector')
    history_line = fields.One2many('sync.history', 'sync_id', copy=True)
    customers = fields.Boolean('Import/Update Customers')
    sales_orders = fields.Boolean('Import/Update Sale Orders')
    products = fields.Boolean('Export/Update Products')

    @api.model
    def auto_import_orders(self):
        self.import_sale_orders(True)

    @api.model
    def auto_import_customers(self):
        self.import_customers(True)

    @api.model
    def auto_export_products(self):
        self.export_products(True)

    def sync_data(self):

        """
        Sync data (customers, orders, products) between Odoo and shopify
        """

        if self.customers or self.products or self.sales_orders:
            self.import_data()
        else:
            raise Warning(_("No Option Checked.", ))

    def connect_to_shopify(self):

        """
        connecting shopify to Odoo with provided credentials
        """

        shop_url = "https://%s:%s@%s.myshopify.com/admin/api/2019-07" % (
            self.env.user.api_key, self.env.user.api_password, self.env.user.shop_name)
        shopify.ShopifyResource.set_site(shop_url)
        shopify.Session.setup(api_key=self.env.user.api_key, secret=self.env.user.api_secret_key)

        try:
            return shopify.Shop.current()
        except Exception as e:
            Warning(_(e))

    def import_data(self):

        """
        Importing data from shopify to Odoo (customers, sales order)
        Exporting products from odoo to shopify
        """

        success_message = "Customers Added: {} and {} updated.\n" \
                          "SalesOrders Added: {} and {} updated.\n" \
                          "Products Exported: {} and {} updated.\n"

        data_dictionary = {}
        if self.connect_to_shopify() is None:
            raise Warning(_("Kindly provide Shopify credentails for odoo user", ))

        if self.customers:
            customers = self.import_customers(False)
            data_dictionary["customers"] = customers[0]
            data_dictionary["customers_updated"] = customers[1]

        if self.sales_orders:
            sale_orders = self.import_sale_orders(False)
            data_dictionary["sales_orders"] = sale_orders[0]
            data_dictionary["sales_orders_updated"] = sale_orders[1]

        if self.products:
            products = self.export_products(False)
            data_dictionary["products"] = products[0]
            data_dictionary["products_updated"] = products[1]

        no_of_customers = len(data_dictionary.get("customers", []))
        no_of_customers_updated = len(data_dictionary.get("customers_updated", []))
        no_of_sales_orders = len(data_dictionary.get("sales_orders", []))
        no_of_sales_orders_updated = len(data_dictionary.get("sales_orders_updated", []))
        no_of_products = len(data_dictionary.get('products', []))
        no_of_products_updated = len(data_dictionary.get('products_updated', []))
        self.write({'last_sync_date': datetime.now()})
        self.env.cr.commit()

        if no_of_customers + no_of_customers_updated + no_of_products + no_of_products_updated + no_of_sales_orders + no_of_sales_orders_updated:
            self.sync_history(no_of_customers, no_of_customers_updated,
                              no_of_sales_orders, no_of_sales_orders_updated,
                              no_of_products, no_of_products_updated, data_dictionary)
        else:
            raise osv.except_osv(_("Sync Details!"), _("No new sync needed. Data already synced."))

    def sync_history(self, no_of_customers, no_of_customers_updated, no_of_sales_orders, no_of_sales_orders_updated,
                     no_of_products, no_of_products_updated, data_dictionary):

        """

        Maintaining sync history with provided args
        :return:
        """

        sync_history = self.env["sync.history"].search([])
        if not sync_history:
            sync_history.create({
                "sync_type": 'Manual',
                "no_of_orders_sync": no_of_sales_orders,
                "no_of_orders_sync_update": no_of_sales_orders_updated,
                "no_of_customers_sync": no_of_customers,
                "no_of_customers_sync_update": no_of_customers_updated,
                "no_of_products_sync": no_of_products,
                "no_of_products_sync_update": no_of_products_updated,
                "sync_id": 1,
            })
        else:
            sync_history.write({
                "sync_type": 'Manual',
                "no_of_orders_sync": no_of_sales_orders,
                "no_of_orders_sync_update": no_of_sales_orders_updated,
                "no_of_customers_sync": no_of_customers,
                "no_of_customers_sync_update": no_of_customers_updated,
                "no_of_products_sync": no_of_products,
                "no_of_products_sync_update": no_of_products_updated,
                "sync_id": 1,
            })
        self.env.cr.commit()

    def import_customers(self, is_auto):

        """
        Importing customers from shopify to odoo
        """

        try:
            self.connect_to_shopify()
            customers_imported = []
            customers_updated = []
            count = 0
            while True:
                count += 1

                customers = shopify.Customer.find(page=count)
                if not customers:
                    break
                if customers:
                    for customer in customers:
                        if customer is not None:
                            odoo_customer = self.env['res.partner'].search(
                                [('shopify_customer_id', '=', str(customer.attributes['id']))])
                            if odoo_customer:
                                customers_updated.append(self.update_customer(customer, odoo_customer))
                            if not odoo_customer:
                                name = ""

                                f_name = customer.attributes['first_name'] if customer.attributes['first_name'] else ""
                                l_name = customer.attributes['last_name'] if customer.attributes['last_name'] else ""

                                name = f_name + " " + l_name
                                if not f_name and not l_name:
                                    name = customer.attributes['email']

                                if 'default_address' in customer.attributes:
                                    customer = self.env['res.partner'].create({
                                        'shopify_customer_id': customer.attributes['id'],
                                        'name': name,
                                        'phone': customer.attributes['phone'] if customer.attributes['phone'] else "",
                                        'email': customer.attributes['email'] if customer.attributes['email'] else "",
                                        'comment': customer.attributes['note'] if customer.attributes['note'] else "",
                                        'street': customer.attributes['default_address'].attributes['address1'],
                                        'street2': customer.attributes['default_address'].attributes['address2'],
                                        'city': customer.attributes['default_address'].attributes['city'],
                                        'zip': customer.attributes['default_address'].attributes['zip'],
                                        'country_id': self.env['res.country'].search(
                                            [(
                                             'name', '=', customer.attributes['default_address'].attributes['country'])]).id
                                    })
                                    customers_imported.append(customer)
                                else:
                                    customer = self.env['res.partner'].create({
                                        'shopify_customer_id': customer.attributes['id'],
                                        'name': name,
                                        'phone': customer.attributes['phone'] if customer.attributes['phone'] else "",
                                        'email': customer.attributes['email'] if customer.attributes['email'] else "",
                                        'comment': customer.attributes['note'] if customer.attributes['note'] else "",
                                    })
                                    customers_imported.append(customer)
                    self.env.cr.commit()

                    if is_auto:
                        data_dictionary = {"customers_imported": len(customers_imported),
                                           "customers_updated": len(customers_updated)}
                        sync_history = self.env["sync.history"].search([])
                        if not sync_history:
                            sync_history.create({
                                "sync_type": 'Auto',
                                "no_of_orders_sync": 0,
                                "no_of_orders_sync_update": 0,
                                "no_of_customers_sync": len(customers_imported),
                                "no_of_customers_sync_update": len(customers_updated),
                                "no_of_products_sync": 0,
                                "no_of_products_sync_update": 0,
                                "sync_id": 1
                            })
                        else:
                            sync_history.write({
                                "sync_type": 'Auto',
                                "no_of_orders_sync": 0,
                                "no_of_orders_sync_update": 0,
                                "no_of_customers_sync": len(customers_imported),
                                "no_of_customers_sync_update": len(customers_updated),
                                "no_of_products_sync": 0,
                                "no_of_products_sync_update": 0,
                                "sync_id": 1
                            })
                        self.env.cr.commit()
            return [customers_imported, customers_updated]
        except Exception as e:
            raise Warning(_(str(e)))

    def update_customer(self, customer, odoo_customer):

        """

        Updating odoo customer with shopify customer

        :param customer:
        :param odoo_customer:
        :return:
        """

        name = ""
        f_name = customer.attributes['first_name'] if customer.attributes['first_name'] else ""
        l_name = customer.attributes['last_name'] if customer.attributes['last_name'] else ""

        name = f_name + " " + l_name
        if not f_name and not l_name:
            name = customer.attributes['email']

        if 'default_address' in customer.attributes:
            customer = odoo_customer.write({
                'shopify_customer_id': customer.attributes['id'],
                'name': name,
                'phone': customer.attributes['phone'] if customer.attributes['phone'] else "",
                'email': customer.attributes['email'] if customer.attributes['email'] else "",
                'comment': customer.attributes['note'] if customer.attributes['note'] else "",
                'street': customer.attributes['default_address'].attributes['address1'],
                'street2': customer.attributes['default_address'].attributes['address2'],
                'city': customer.attributes['default_address'].attributes['city'],
                'zip': customer.attributes['default_address'].attributes['zip'],
                'country_id': self.env['res.country'].search(
                    [('name', '=', customer.attributes['default_address'].attributes['country'])]).id
            })
        else:
            customer = odoo_customer.write({
                'shopify_customer_id': customer.attributes['id'],
                'name': name,
                'phone': customer.attributes['phone'] if customer.attributes['phone'] else "",
                'email': customer.attributes['email'] if customer.attributes['email'] else "",
                'comment': customer.attributes['note'] if customer.attributes['note'] else "",
            })
        self.env.cr.commit()

    def import_sale_orders(self, is_auto):

        """
        Importing orders from shopify to odoo
        """

        try:
            self.connect_to_shopify()
            order_imported = []
            order_updated = []
            count = 0
            while True:
                count += 1
                orders = shopify.Order.find(page=count)
                if not orders:
                    break
                if orders:
                    for order in orders:
                        temp_order = self.env['sale.order'].search([('shopify_order_id', '=', order.attributes['id'])])
                        if temp_order:
                            order_updated.append(self.update_sale_order(order, temp_order))
                            continue
                        name = ''
                        customer = {}
                        if 'customer' in order.attributes:

                            f_name = order.attributes['customer'].attributes['first_name'] if \
                                    order.attributes['customer'].attributes['first_name'] else ""
                            l_name = order.attributes['customer'].attributes['last_name'] if \
                                    order.attributes['customer'].attributes['last_name'] else ""
                            name = f_name + " " + l_name
                            if not f_name and not l_name:
                                name = order.attributes['customer'].attributes['email']

                            customer = self.env['res.partner'].search(
                                [('shopify_customer_id', '=', order.attributes['customer'].attributes['id'])])
                            if customer:
                                customer = customer[0]
                            if not customer:
                                customer = self.env['res.partner'].create({
                                    'name': name,
                                    'phone': order.attributes['customer'].attributes['phone'] if
                                    order.attributes['customer'].attributes['phone'] else "",
                                    'email': order.attributes['customer'].attributes['email'] if
                                    order.attributes['customer'].attributes['email'] else "",
                                    'comment': order.attributes['customer'].attributes['note'] if
                                    order.attributes['customer'].attributes['note'] else "",
                                })
                            all_products_fields_available = False
                            for item in order.attributes['line_items']:
                                product_id = item.attributes['product_id']
                                if product_id:
                                    all_products_fields_available = True
                                else:
                                    all_products_fields_available = False

                            if not all_products_fields_available:
                                continue

                            odoo_order = self.env['sale.order'].create({
                                'shopify_order_id': order.attributes['id'],
                                'partner_id': customer.id,
                                'date_order': order.attributes['created_at'],
                                'amount_tax': float(order.attributes['total_tax']),
                                'amount_total': float(order.attributes['total_price']),
                                'confirmation_date': order.attributes['processed_at'],
                                'state': 'sale',
                            })
                            order_imported.append(odoo_order)
                            for item in order.attributes['line_items']:
                                product_id = item.attributes['product_id']
                                if product_id:
                                    product = shopify.Product.find(id_=product_id)
                                    if product:
                                        odoo_product_template = self.env['product.template']. \
                                            search([('shopify_product_id', '=', str(product.attributes['id']))])

                                        if not odoo_product_template:
                                            odoo_product_template = self.env['product.template'].create({
                                                'name': product.attributes['title'],
                                                'shopify_product_id': product.attributes['id'],
                                                'price': float(product.attributes['variants'][0].price)
                                            })
                                            odoo_product = self.env['product.product'].create({
                                                'product_tmpl_id': odoo_product_template.id
                                            })
                                        if odoo_product_template:
                                            odoo_product = self.env['product.product'].search([('product_tmpl_id',
                                                                                                '=',
                                                                                                odoo_product_template.id)])
                                            if not odoo_product:
                                                odoo_product = self.env['product.product'].create({
                                                    'product_tmpl_id': odoo_product_template.id
                                                })

                                        self.env['sale.order.line'].create({
                                            'product_id': odoo_product[0].id,
                                            'order_id': odoo_order.id,
                                            'product_uom_qty': item.attributes['quantity'],
                                            'qty_invoiced': item.attributes['fulfillable_quantity'],
                                            'name': item.attributes['name'],
                                            'price_unit': item.attributes['price'],
                                        })

                            self.env.cr.commit()

                        if is_auto:
                            data_dictionary = {"order_imported": len(order_imported), "order_updated": len(order_updated)}
                            sync_history = self.env["sync.history"].search([])
                            if not sync_history:
                                sync_history.create({
                                    "sync_type": 'Auto',
                                    "no_of_orders_sync": len(order_imported),
                                    "no_of_orders_sync_update": len(order_updated),
                                    "no_of_customers_sync": 0,
                                    "no_of_customers_sync_update": 0,
                                    "no_of_products_sync": 0,
                                    "no_of_products_sync_update": 0,
                                    "sync_id": 1
                                })
                            else:
                                sync_history.write({
                                    "sync_type": 'Auto',
                                    "no_of_orders_sync": len(order_imported),
                                    "no_of_orders_sync_update": len(order_updated),
                                    "no_of_customers_sync": 0,
                                    "no_of_customers_sync_update": 0,
                                    "no_of_products_sync": 0,
                                    "no_of_products_sync_update": 0,
                                    "sync_id": 1
                                })
                            self.env.cr.commit()
            return [order_imported, order_updated]
        except Exception as e:
            raise Warning(_(str(e)))

    def update_sale_order(self, order, odoo_order):

        """

        Updating odoo sales orders with shopify sales orders

        :param order:
        :param odoo_order:
        :return:
        """

        name = ''
        customer = {}
        if 'customer' in order.attributes:
            if order.attributes['customer'].attributes['first_name']:
                name = order.attributes['customer'].attributes['first_name'] + " " + \
                       order.attributes['customer'].attributes['last_name']
            else:
                name = order.attributes['customer'].attributes['email']

            customer = self.env['res.partner'].search(
                [('shopify_customer_id', '=', order.attributes['customer'].attributes['id'])])
            if customer:
                customer = customer[0]
            if not customer:
                customer = self.env['res.partner'].create({
                    'name': name,
                    'phone': order.attributes['customer'].attributes['phone'] if
                    order.attributes['customer'].attributes['phone'] else "",
                    'email': order.attributes['customer'].attributes['email'] if
                    order.attributes['customer'].attributes['email'] else "",
                    'comment': order.attributes['customer'].attributes['note'] if
                    order.attributes['customer'].attributes['note'] else "",
                })
            odoo_order.write({
                'shopify_order_id': order.attributes['id'],
                'partner_id': customer.id,
                'date_order': order.attributes['created_at'],
                'amount_tax': float(order.attributes['total_tax']),
                'amount_total': float(order.attributes['total_price']),
                'state': 'sale',
            })
            self.env.cr.commit()

    def export_products(self, is_auto):

        """
        Exporting products from odoo to shopify
        """

        try:
            self.connect_to_shopify()
            exported_products = []
            updated_products = []
            products = self.env['product.template'].search([('sync_to_shopify', '=', True)])
            for product in products:
                if shopify.Product.exists(product.shopify_product_id):
                    updated_products.append(self.update_product(product))
                else:
                    new_product = shopify.Product()
                    new_product.title = product.name

                    if product.description_sale:
                        new_product.body_html = product.description_sale
                    new_product.product_type = product.type
                    product_variant = shopify.Variant({"title": "v1", "price": product.list_price ,
                                                       "inventory_management": "shopify",
                                                       "inventory_quantity": int(product.qty_available),
                                                       "weight": product.weight,
                                                       "weight_unit": product.weight_uom_name,
                                                       })
                    new_product.variants = [product_variant]
                    new_product.save()
                    category = self.env['product.category'].search([('id', 'in', product.categ_id.ids)])

                    if category:
                        collections = shopify.CustomCollection().find()
                        existed_collection = None

                        for collection in collections:
                            if collection.attributes['title'] == category.name:
                                existed_collection = collection
                                break
                        if existed_collection:
                            collection = shopify.CustomCollection().find(existed_collection.attributes['id'])
                        else:
                            collection = shopify.CustomCollection()
                        collection.title = category[0].name
                        collection.save()
                        collect = shopify.Collect({'product_id': new_product.id, 'collection_id': collection.id})
                        collect.save()

                    odoo_product = self.env['product.template'].search([('id', '=', product.id)])
                    odoo_product.write({'shopify_product_id': new_product.attributes['id']})
                    exported_products.append(new_product)
                    image_position = 1

                    if product.image:
                        image = shopify.Image({'product_id': new_product.id})
                        image.position = image_position
                        binary_in = base64.b64decode(product.image)
                        image.attach_image(data=binary_in, filename='ipod-nano.png')
                        image.save()
                        if hasattr(product, 'product_image_ids'):
                            for image_odoo in product.product_image_ids:
                                image_position += 1
                                image = shopify.Image({'product_id': new_product.id})
                                binary_in = base64.b64decode(image_odoo.image)
                                image.position = image_position
                                image.attach_image(data=binary_in, filename='ipod-nano.png')
                                image.save()

            if is_auto:
                data_dictionary = {"exported_products": len(exported_products), "updated_products": len(updated_products)}
                sync_history = self.env["sync.history"].search([])
                if not sync_history:
                    sync_history.create({
                        "sync_type": 'Auto',
                        "no_of_orders_sync": 0,
                        "no_of_orders_sync_update": 0,
                        "no_of_customers_sync": 0,
                        "no_of_customers_sync_update": 0,
                        "no_of_products_sync": len(exported_products),
                        "no_of_products_sync_update": len(updated_products),
                        "sync_id": 1
                    })
                else:
                    sync_history.write({
                        "sync_type": 'Auto',
                        "no_of_orders_sync": 0,
                        "no_of_orders_sync_update": 0,
                        "no_of_customers_sync": 0,
                        "no_of_customers_sync_update": 0,
                        "no_of_products_sync": len(exported_products),
                        "no_of_products_sync_update": len(updated_products),
                        "sync_id": 1
                    })
                self.env.cr.commit()
            return [exported_products, updated_products]
        except Exception as e:
            raise Warning(_(str(e)))

    def update_product(self, product):

        """
        Updating product
        :param new_product:
        :param product:
        :return:
        """

        time.sleep(1)
        new_product = shopify.Product.find(product.shopify_product_id)
        new_product.title = product.name

        if product.description_sale:
            new_product.body_html = product.description_sale

        new_product.product_type = product.type
        product_variant = shopify.Variant({"title": "v1", "price": product.list_price,
                                           "inventory_management": "shopify",
                                           "inventory_quantity": int(product.qty_available),
                                           "weight": product.weight,
                                           "weight_unit": product.weight_uom_name,
                                           })
        new_product.variants = [product_variant]
        new_product.save()
        category = self.env['product.category'].search([('id', 'in', product.categ_id.ids)])

        if category:
            collections = shopify.CustomCollection().find()
            existed_collection = None

            for collection in collections:
                if collection.attributes['title'] == category.name:
                    existed_collection = collection
                    break

            if existed_collection:
                collection = shopify.CustomCollection().find(existed_collection.attributes['id'])
            else:
                collection = shopify.CustomCollection()

            collection.title = category[0].name
            collection.save()
            collect = shopify.Collect({'product_id': new_product.id, 'collection_id': collection.id})
            collect.save()

        odoo_product = self.env['product.template'].search([('id', '=', product.id)])
        odoo_product.write({"shopify_product_id": new_product.attributes['id']})
        image_position = 1

        if product.image:
            image = shopify.Image({'product_id': new_product.id})
            image.position = image_position
            binary_in = base64.b64decode(product.image)
            image.attach_image(data=binary_in, filename='ipod-nano.png')
            image.save()
            if hasattr(product, 'product_image_ids'):
                for image_odoo in product.product_image_ids:
                    image_position += 1
                    image = shopify.Image({'product_id': new_product.id})
                    binary_in = base64.b64decode(image_odoo.image)
                    image.position = image_position
                    image.attach_image(data=binary_in, filename='ipod-nano.png')
                    image.save()


class Dropboxlinks(models.Model):
    _name = 'sync.history'
    _order = 'sync_date desc'

    sync_id = fields.Many2one('salesforce.connector', string='Partner Reference', required=True, ondelete='cascade',
                              index=True, copy=False)
    sync_date = fields.Datetime('Sync Date', readonly=True, required=True, default=fields.Datetime.now)
    no_of_orders_sync = fields.Integer('SalesOrders Imported', readonly=True)
    no_of_orders_sync_update = fields.Integer('SalesOrders Updated', readonly=True)
    no_of_products_sync = fields.Integer('Products Exported', readonly=True)
    no_of_products_sync_update = fields.Integer('Products Updated', readonly=True)
    no_of_customers_sync = fields.Integer('Customers Imported', readonly=True)
    no_of_customers_sync_update = fields.Integer('Customers Updated', readonly=True)
    document_link = fields.Char('Document Link', readonly=True)
    sync_type = fields.Char('Sync_Type', readonly=True)

    @api.multi
    def sync_data(self):
        """
        :return:
        """
        client_action = {

            'type': 'ir.actions.act_url',
            'name': "log_file",
            'target': 'new',
            'url': self.document_link
        }
        return client_action
