from odoo import models, fields, api, _
import os
from odoo.exceptions import UserError, ValidationError
from openerp.exceptions import Warning
from .dropbox_api import Dropbox_api
import base64
import dropbox

root_path = os.path.dirname(os.path.abspath(__file__))


class DropboxConnector(models.Model):
    _inherit = 'res.partner'
    user_name_dropbox = fields.Many2one('dropbox.credentials', string='Dropbox Account')
    upload_file_data_dropbox = fields.Many2many('ir.attachment', 'dropbox_ir_attachments_rel', 'dropbox_id',
                                                'attachment_id', 'Attachments')
    order_line = fields.One2many('documents.links', 'order_id', copy=True)
    dropbox = None
    path = None

    def connect_to_dropbox(self):
        if not self.user_name_dropbox:
            raise ValidationError(_('Dropbox account is missing'))
        self.path = "/{}/{}/".format(self.user_name_dropbox.dropbox_folder,
                                     self.name)
        try:
            self.dropbox = Dropbox_api(self.user_name_dropbox.access_token)
        except Exception as e:
            Warning(_(str(e)))

    @api.multi
    def upload_doc_dropbox(self):
        None if self.dropbox else self.connect_to_dropbox()
        if not self.upload_file_data_dropbox:
            raise ValidationError(_('Dropbox attchments are missing'))
        self.create_folder_with_customer_name(self.path)
        documents = []

        for each in self.upload_file_data_dropbox:
            attach_file_name = each.name
            attach_file_data = each.sudo().read(['datas_fname', 'datas'])
            data = attach_file_data[0]['datas']
            cwd = os.path.dirname(os.path.abspath(__file__))
            fh = open(cwd + "/files/attach_file_name", "wb")
            fh.write(base64.b64decode(data))
            fh.close()
            in_file = open(cwd + "/files/attach_file_name", "rb")
            data = in_file.read()
            in_file.close()

            self.dropbox.upload(data, self.path + attach_file_name, overwrite=True)
            link = self.dropbox.dbx.sharing_create_shared_link(self.path+attach_file_name)
            documents.append({"order_id": self.id,
                              "customer_name": self.name,
                              "file_name": attach_file_name,
                              "document_link": str(link.url).replace('dl=0', 'dl=1')})
        attachment = self.env['ir.attachment']
        cr = self._cr
        query = "SELECT attachment_id FROM dropbox_ir_attachments_rel WHERE dropbox_id='%s'" % str(self.id)
        cr.execute(query)
        attachments = attachment.browse([row[0] for row in cr.fetchall()])
        if attachments:
            attachments.unlink()
        self.add_download_link_data(documents)
        raise Warning(_("Successfully uploaded"))

    def add_download_link_data(self, data):
        documents_link = self.env["documents.links"]
        for x in data:
            document_status = documents_link.search([('document_link', '=', x['document_link'])])
            if document_status:
                documents_link.create(x)
            else:
                documents_link.create(x)
        self.env.cr.commit()

    def create_folder_with_customer_name(self, path):
        try:
            self.dropbox.dbx.files_create_folder(path)
        except dropbox.exceptions.ApiError as err:
            print('*** API error', err)

    def sync_data(self):
        documents = []
        None if self.dropbox else self.connect_to_dropbox()
        dropbox_files = self.list_files_of_folder(self.path)
        existing_file_data = self.env['documents.links'].search([('order_id', '=', self.id)])
        existing_file_names = [file.file_name for file in existing_file_data]
        for file in dropbox_files.values():
            if file.name in existing_file_names:
                continue
            link = self.dropbox.dbx.sharing_create_shared_link(self.path + file.name)
            documents.append({"order_id": self.id,
                              "customer_name": self.name,
                              "file_name": file.name,
                              "document_link": str(link.url).replace('dl=0', 'dl=1')})
        self.add_download_link_data(documents)

    def list_files_of_folder(self, path):
        try:
            res = self.dropbox.dbx.files_list_folder(path)
            rv = {}
            for entry in res.entries:
                rv[entry.name] = entry
            return rv
        except dropbox.exceptions.ApiError as err:
            print('Folder listing failed for', self.path, '-- assumed empty:', err)
            return {}


class Dropboxlinks(models.Model):
    _name = 'documents.links'
    order_id = fields.Many2one('res.partner', string='Partner Reference', required=True, ondelete='cascade',
                               index=True,
                               copy=False)
    customer_name = fields.Char('Customer Name', readonly=True)
    file_name = fields.Char('Document Name', readonly=True)
    document_link = fields.Char('Document Link', readonly=True)
