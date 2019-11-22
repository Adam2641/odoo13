# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import os
import base64
from . import cmis_integration
from openerp.osv import osv

from odoo.exceptions import UserError, ValidationError

root_path = os.path.dirname(os.path.abspath(__file__))


class AlfrescoUpload(models.Model):

    _name = 'alfresco.upload'

    directory_name = fields.Selection((('Sales', 'Sales'), ('Orders', 'Orders'), ('Quotation', 'Quotations'),('Invoice','Invoices'),('Others','Others')), 'Directory Name')#fields.Char(string='Directory Name')
    upload_file_data = fields.Many2many('ir.attachment', 'class_ir_attachments_rel', 'class_id', 'attachment_id', 'Attachments')
    user_name = fields.Many2one('alfresco.credentials', string='Username',required=True,default=lambda self: self.env['alfresco.credentials'].search([('name', '!=', [])], limit=1))
    downloaded_file_data_alfresco = fields.Many2many('ir.attachment', 'downloaded_ir_document_attachments_rel', 'id',
                                                     'attachment_id', 'Attachments')


    alfresco_document_link = fields.Many2one('documents.links', string='Alfresco document link')

    download_type = fields.Selection([('file', 'File'), ('link', 'Link')], string='Download Type', default='file')
    order_line = fields.One2many('documents.links', 'order_ids', copy=True)


    @api.multi
    def unlink(self):
        """
        remove directory from alfesco
        :return:
        """
        for each in self:
            alfresco_user_name = each.user_name.name
            alfresco_url =  each.user_name.url
            alfresco_pwd = each.user_name.pass_word
            cms_obj = cmis_integration.CMISController(alfresco_url, alfresco_user_name, alfresco_pwd)
            directory_id = each.id
            direct_name = self.env['alfresco.upload'].search([('id','=',directory_id)]).directory_name
            out_put_flag = cms_obj.delete_complete_folder(direct_name)
            if out_put_flag==False:
                raise ValidationError(_('Some error occured while connecting with alfresco.'))

        return models.Model.unlink(self)

    @api.multi
    def alfresco_doc_upload(self):
        '''
        This function uploads document on selected folders

        :return:
        '''

        if not self.upload_file_data:
            raise ValidationError(_('Alfresco attchments are missing'))

        if not self.user_name:
            raise ValidationError(_('Alfresco account is missing'))

        alfresco_url = self.user_name.url
        alfresco_pwd = self.user_name.pass_word
        alfresco_user_name = self.user_name.name
        alfresco_dirctory_name = self.directory_name
        custom_directory = 'Odoo Document'

        if not alfresco_dirctory_name:
            alfresco_dirctory_name = self.user_name.name

        if alfresco_url and alfresco_pwd and alfresco_user_name:

            cmis_connection = cmis_integration.CMISController(alfresco_url, alfresco_user_name, alfresco_pwd)
            if self._uid == self.user_name.create_uid.id:
                root_directory = cmis_connection.get_root_directory()

                # @@@@@@creating directory @@@@@@@@@@@@
                for each in self.upload_file_data:
                    attach_file_name = each.name
                    sub_directory = None
                    attach_file_data = each.sudo().read(['datas_fname', 'datas'])
                    directory_path = os.path.join(root_path, "files")
                    if not os.path.isdir(directory_path):
                        os.mkdir(directory_path)
                    file_path = os.path.join("files", attach_file_name)
                    complete_path = os.path.join(root_path, file_path)
                    with open(complete_path, "w") as text_file:
                        text_file.write(str(base64.decodestring(attach_file_data[0]['datas'])))
                    if alfresco_dirctory_name == False:
                        out_put_flag = cmis_connection.upload_file(complete_path, custom_directory,
                                                                   directory_name=alfresco_dirctory_name,
                                                                   overwrite_flag=True)
                        if out_put_flag == False:
                            raise ValidationError(_('Some error occured while connecting with alfresco.'))
                    else:
                        out_put_flag = cmis_connection.create_directory(custom_directory)
                        if out_put_flag == False:
                            raise ValidationError(_('Invalid Credentials or Alfresco server is down.'))

                        sub_directory = cmis_connection.create_subdirectory(custom_directory,
                                                                            alfresco_dirctory_name)
                        if sub_directory == False:
                            raise ValidationError(_('Some error occured while connecting with alfresco.Please! check Credentials'))

                        upload_doc = cmis_connection.upload_file(complete_path, custom_directory,
                                                                 directory_name=alfresco_dirctory_name,
                                                                 overwrite_flag=True)
                        if upload_doc == False:
                            raise ValidationError(_('Some error occured while connecting with alfresco.'))
                        os.remove(complete_path)

                        main_instance = cmis_connection.get_folder_instance(root_directory, custom_directory)

                        if main_instance:
                            sub_instance = cmis_connection.get_folder_instance(main_instance,
                                                                               alfresco_dirctory_name)
                            if sub_instance:
                                download_link = cmis_connection.get_folder_instance(sub_instance, each.name)
                                if download_link:
                                    values = {'customer_name': self.user_name.name,

                                              'name': attach_file_name,
                                              'document_link': download_link,
                                              'directory_name':alfresco_dirctory_name,

                                              'order_ids': self.id,
                                              }
                                    attach_id = self.env['documents.links'].create(values)

                                    Attachment = self.env['ir.attachment']
                                    cr = self._cr

                                    query = "SELECT attachment_id FROM class_ir_attachments_rel WHERE class_id=" + str(
                                        self.id) + ""

                                    cr.execute(query)
                                    attachments = Attachment.browse([row[0] for row in cr.fetchall()])
                                    if attachments:
                                        # print "attachments"
                                        # print attachments
                                        attachments.unlink()


class AlfrescoCredentials(models.Model):
    _name = 'alfresco.credentials'

    directory_name = fields.Char(string='Directory Name')
    url = fields.Char(string='URL',required=True)
    name = fields.Char(string='Username', required=True)
    pass_word = fields.Char(string='Password', required=True)
    _sql_constraints = [
                     ('field_unique', 
                      'unique(user_name)',
                      'Choose another value - it has to be unique!')]

    def test_connection(self):

        alfresco_connection= cmis_integration.CMISController(self.url,self.name,self.pass_word)
        root_path=alfresco_connection.get_root_directory()
        if root_path:
            raise osv.except_osv(_("Seccess"),_("Connection Successfully"))
        else:
            raise osv.except_osv(_("Failed"), _("Invalid Credentials Or Alfresco server is down"))







class AlfrescoLinks(models.Model):

    _name = 'documents.links'

    order_id = fields.Many2one('res.partner', string='Partner Reference', required=False, ondelete='cascade', index=True, copy=False)
    order_ids = fields.Many2one('alfresco.upload', string='Document Reference', required=False, ondelete='cascade', index=True,
                               copy=False)

    customer_name = fields.Char('Customer Name')
    name = fields.Char('Document Name')
    directory_name = fields.Char("Directory Name")
    document_link = fields.Char('Document Link')

    status = fields.Char(string='Status')

    def download_file_form_doc_link_alfresco(self):
        """
        Download document link from alfresco to odoo from customer directory as well other specific directory
        :return:
        """

        customer_id = self.order_id
        user_id=self.order_ids

        if customer_id:
            if not customer_id.user_name_alfresco:
                raise ValidationError(_('Alfresco account is not Found'))

            if not self.document_link:
                raise ValidationError(_('Alfresco document link is Not Found'))

            document_name = self.name
            document_link_url = self.document_link

            alfresco_url = customer_id.user_name_alfresco.url
            alfresco_pwd = customer_id.user_name_alfresco.pass_word
            alfresco_user_name = customer_id.user_name_alfresco.name
            alfresco_dirctory_name = customer_id.user_name_alfresco.directory_name

            if not alfresco_dirctory_name:
                alfresco_dirctory_name = "Odoo Client Documents"

            if alfresco_url and alfresco_pwd and alfresco_user_name:

                cmis_connection = cmis_integration.CMISController(alfresco_url, alfresco_user_name, alfresco_pwd)
                if self._uid == customer_id.user_name_alfresco.create_uid.id:
                    upload_file_names = []

                    directory_path = os.path.join(root_path, "files")
                    if not os.path.isdir(directory_path):
                        os.mkdir(directory_path)
                    # @@@@@@creating directory @@@@@@@@@@@@

                    sub_directory = None

                    root_dir = cmis_connection.get_root_directory()

                    root_instance = cmis_connection.get_folder_instance(root_dir, alfresco_dirctory_name)

                    if root_instance == False:
                        raise ValidationError("Sorry ! Check Alfresco Credentials")
                    if root_instance == None:
                        raise ValidationError("Sorry Main Directory not exist")
                    else:
                        sub_dir = cmis_connection.get_folder_instance(root_instance, customer_id.name)

                        if sub_dir == False:
                            raise ValidationError("Directory Does not exist")
                        if sub_dir == None:
                            raise ValidationError("Directory Does not exist")
                        else:
                            old_file = self.name

                            print("coming in old file check")
                            file_path = os.path.join(directory_path, old_file)
                            download_status = cmis_connection.download_file(self.name, alfresco_dirctory_name,
                                                                            directory_name=self.customer_name)

                            if download_status:
                                with open(file_path, "rb") as open_file:
                                    encoded_string = base64.b64encode(open_file.read())
                                partner_id = customer_id.id
                                old_file = self.name
                                #partner_id = self.id
                                values = {'name': old_file,
                                          'type': 'binary',
                                          'res_id': partner_id,
                                          'res_model': 'res.partner',
                                          'partner_id': partner_id,
                                          'datas': encoded_string,
                                          'index_content': 'image',
                                          'datas_fname': old_file,
                                          }
                                attach_id = self.env['ir.attachment'].create(values)
                                self.env.cr.execute(
                                    """ insert into downloaded_ir_attachments_rel values (%s,%s) """ % (
                                        partner_id, attach_id.id))
                                os.remove(file_path)
                                self.status = 'Downloaded'

        else:
            if not user_id.user_name:
                raise ValidationError(_('Alfresco account is not Found'))

            if not self.document_link:
                raise ValidationError(_('Alfresco document link is Not Found'))

            document_name = self.name
            document_link_url = self.document_link

            alfresco_url = user_id.user_name.url
            alfresco_pwd = user_id.user_name.pass_word
            alfresco_user_name = user_id.user_name.name
            alfresco_dirctory_name = user_id.directory_name

            if not alfresco_dirctory_name:
                alfresco_dirctory_name = user_id.user_name.name
            custom_dir ="Odoo Document"

            if alfresco_url and alfresco_pwd and alfresco_user_name:

                cmis_connection = cmis_integration.CMISController(alfresco_url, alfresco_user_name, alfresco_pwd)
                if self._uid == user_id.user_name.create_uid.id:
                    upload_file_names = []

                    directory_path = os.path.join(root_path, "files")
                    if not os.path.isdir(directory_path):
                        os.mkdir(directory_path)
                    # @@@@@@creating directory @@@@@@@@@@@@

                    sub_directory = None

                    root_dir = cmis_connection.get_root_directory()

                    root_instance = cmis_connection.get_folder_instance(root_dir, custom_dir)

                    if root_instance == False:
                        raise ValidationError("Sorry ! Check Alfresco Credentials")
                    if root_instance == None:
                        raise ValidationError("Sorry Main Directory not exist")
                    else:
                        sub_dir = cmis_connection.get_folder_instance(root_instance, alfresco_dirctory_name)

                        if sub_dir == False:
                            raise ValidationError("Directory Does not exist")
                        if sub_dir == None:
                            raise ValidationError("Directory Does not exist")
                        else:
                            old_file = self.name

                            print("coming in old file check")
                            file_path = os.path.join(directory_path, old_file)
                            download_status = cmis_connection.download_file(self.name, custom_dir,
                                                                            directory_name=self.directory_name)

                            if download_status:

                                with open(file_path, "rb") as open_file:
                                    encoded_string = base64.b64encode(open_file.read())
                                partner_id = user_id.id
                                old_file = self.name
                                #doc_id = self.id
                                values = {'name': old_file,
                                          'type': 'binary',
                                          'res_id': partner_id,
                                          'res_model': 'alfresco.upload',
                                          'partner_id': partner_id,
                                          'datas': encoded_string,
                                          'index_content': 'image',
                                          'datas_fname': old_file,
                                          }

                                attach_id = self.env['ir.attachment'].create(values)
                                self.env.cr.execute(
                                """ insert into downloaded_ir_document_attachments_rel values (%s,%s) """ % (
                                        partner_id, attach_id.id))
                                os.remove(file_path)
                                self.status = 'Downloaded'


class CustomerFile(models.Model):
    _inherit = "res.partner"
    #_inherit = "res.users"

    upload_file_data_alfresco = fields.Many2many('ir.attachment', 'alfresco_ir_attachments_rel', 'alfresco_id', 'attachment_id', 'Attachments')
    downloaded_file_data_alfresco= fields.Many2many('ir.attachment', 'downloaded_ir_attachments_rel', 'downloaded_id', 'attachment_id', 'Attachments')
    user_name_alfresco = fields.Many2one('alfresco.credentials', string='Username',required=True,default=lambda self: self.env['alfresco.credentials'].search([('name', '!=', [])], limit=1))

    alfresco_document_link = fields.Many2one('documents.links', string='Alfresco document link')

    download_type = fields.Selection([('file', 'File'), ('link', 'Link')], string='Download Type', default='file')

    order_line = fields.One2many('documents.links', 'order_id', copy=True)

    @api.multi
    def upload_doc_alfresco(self):

        if not self.upload_file_data_alfresco:
            raise ValidationError(_('Alfresco attchments are missing'))

        if not self.user_name_alfresco:
            raise ValidationError(_('Alfresco account is missing'))


        alfresco_url = self.user_name_alfresco.url
        alfresco_pwd = self.user_name_alfresco.pass_word
        alfresco_user_name = self.user_name_alfresco.name
        alfresco_dirctory_name=self.user_name_alfresco.directory_name

        if not alfresco_dirctory_name:
            alfresco_dirctory_name="Odoo Client Documents"

        if alfresco_url and alfresco_pwd and alfresco_user_name:

            cmis_connection = cmis_integration.CMISController(alfresco_url, alfresco_user_name, alfresco_pwd)
            if self._uid == self.self.user_name_alfresco.create_uid.id:
                root_directory = cmis_connection.get_root_directory()
                upload_file_names = []

                # @@@@@@creating directory @@@@@@@@@@@@
                for each in self.upload_file_data_alfresco:
                    attach_file_name = each.name
                    sub_directory = None
                    attach_file_data = each.sudo().read(['datas_fname', 'datas'])
                    directory_path = os.path.join(root_path, "files")
                    if not os.path.isdir(directory_path):
                        os.mkdir(directory_path)
                    file_path = os.path.join("files", attach_file_name)
                    complete_path = os.path.join(root_path, file_path)
                    with open(complete_path, "w") as text_file:
                        text_file.write(str(base64.decodestring(attach_file_data[0]['datas'])))
                    if alfresco_dirctory_name == False:
                        out_put_flag = cmis_connection.upload_file(complete_path, overwrite_flag=True)
                        if out_put_flag == False:
                            raise ValidationError(_('Some error occured while connecting with alfresco.'))
                    else:
                        out_put_flag = cmis_connection.create_directory(alfresco_dirctory_name)
                        if out_put_flag == False:
                            raise ValidationError(_('Some error occured while connecting with alfresco.'))

                        sub_directory = cmis_connection.create_subdirectory(alfresco_dirctory_name, self.name)
                        if sub_directory == False:
                            raise ValidationError(_('Some error occured while connecting with alfresco.'))

                        upload_doc = cmis_connection.upload_file(complete_path, alfresco_dirctory_name,
                                                                 directory_name=self.name,
                                                                 overwrite_flag=True)
                        if upload_doc == False:
                            raise ValidationError(_('Some error occured while connecting with alfresco.'))

                    os.remove(complete_path)

                    main_instance = cmis_connection.get_folder_instance(root_directory, alfresco_dirctory_name)

                    if main_instance:
                        sub_instance = cmis_connection.get_folder_instance(main_instance, self.name)
                        if sub_instance:
                            download_link = cmis_connection.get_folder_instance(sub_instance, each.name)
                            if download_link:
                                values = {'customer_name': self.name,
                                          'name': attach_file_name,
                                          'document_link': download_link,
                                          'order_id': self.id,
                                          }
                                attach_id = self.env['documents.links'].create(values)

                                Attachment = self.env['ir.attachment']
                                cr = self._cr

                                query = "SELECT attachment_id FROM alfresco_ir_attachments_rel WHERE alfresco_id=" + str(
                                    self.id) + ""

                                test = cr.execute(query)
                                attachments = Attachment.browse([row[0] for row in cr.fetchall()])
                                if attachments:
                                    # print "attachments"
                                    # print attachments
                                    attachments.unlink()







