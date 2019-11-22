import shopify
from odoo import models, fields, api
from openerp.osv import osv
from openerp.exceptions import ValidationError


class ShopifyConnector(models.Model):
    _name = 'shopify.settings'

    shop_name = fields.Char('Shop Name')
    api_key = fields.Char('API Key')
    api_password = fields.Char('API Password')
    api_secret_key = fields.Char('API Secret Key')
    field_name = fields.Char('Shopify_settings')

    def test_connection(self):
        shop_url = "https://%s:%s@%s.myshopify.com/admin/api/2019-07" % (self.api_key, self.api_password, self.shop_name)
        shopify.ShopifyResource.set_site(shop_url)
        shopify.Session.setup(api_key=self.api_key, secret=self.api_secret_key)
        try:
            shop = shopify.Shop.current()
            self.env.user.shop_name = self.shop_name
            self.env.user.api_key = self.api_key
            self.env.user.api_password = self.api_password
            self.env.api_secret_key = self.api_secret_key
            self.env.cr.commit()
        except:
            raise ValidationError('Connection Failed >> invalid credentials')
        raise osv.except_osv("Success!", " Connection Successful !")
