from odoo import models, fields, api
from openerp.osv import osv


class DropboxCredentials(models.Model):
    _name = 'dropbox.credentials'
    name = fields.Char(string='Connector Name', required=True)
    dropbox_folder = fields.Char(string='Dropbox Folder Name', required=True)
    access_token = fields.Char(string='Access Token', required=True)

    @api.one
    def test_connection(self):
        connection_flag = True
        if connection_flag:
            raise osv.except_osv("Success!", " Connection Successful !")
        raise osv.except_osv("Failure!", " Connection Failed !")
