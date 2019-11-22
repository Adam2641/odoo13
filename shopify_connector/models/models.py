# -*- coding: utf-8 -*-
import shopify
from odoo import fields, models, api, osv
from openerp.exceptions import ValidationError
from openerp.osv import osv


class CustomUser(models.Model):

    """
    Inherits from base user and adds its own fields
    """

    _inherit = 'res.users'

    # Add new columns to the res.users model,
    shop_name = fields.Char('Shop Name')
    api_key = fields.Char('API Key')
    api_password = fields.Char('API Password')
    api_secret_key = fields.Char('API Secret Key')

    @api.one
    def test_connection(self):

        """
        Testing shopify connection with provided credentials

        """

        shop_url = "https://%s:%s@%s.myshopify.com/admin/api/2019-07" % (self.api_key, self.api_password, self.shop_name)
        shopify.ShopifyResource.set_site(shop_url)
        shopify.Session.setup(api_key=self.api_key, secret=self.api_secret_key)

        try:
            shop = shopify.Shop.current()
        except:
            raise ValidationError('Connection Failed >> invalid credentials')

        raise osv.except_osv("Success!", " Connection Successful !")


class CustomPartner(models.Model):

    """
    Inherits from  base class partner and adds its own field
    """

    _inherit = "res.partner"

    shopify_customer_id = fields.Char(string="Shopify Customer Id")


class CustomSaleOrder(models.Model):

    """
    Inherits from  base class sale.order and adds its own field
    """

    _inherit = "sale.order"

    shopify_order_id = fields.Char(string="Shopify Order Id")


class CustomProduct(models.Model):

    """
    Inherits from  base class product.template and adds its own fields
    """

    _inherit = "product.template"

    shopify_product_id = fields.Char(string="Shopify Product Id")
    sync_to_shopify = fields.Boolean(string="Sync To Shopify")


class Sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    customer_lead = fields.Float(required= False)