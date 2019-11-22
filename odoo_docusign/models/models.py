# -*- coding: utf-8 -*-
from odoo import models, fields, api
from . import odoo_docosign
from openerp.osv import osv
from openerp.exceptions import ValidationError

import os
import shutil
import base64


class DocusignSettingModel(models.Model):
    _name = 'docu.credentials'

    name = fields.Char(string="Name", required=True)
    useremail = fields.Char(string="Email", required=True)
    userpassword = fields.Char(string="Password", required=True)
    auth_key = fields.Char(string="Docusign Integrator Key", required=True)
    accounttype = fields.Selection([('Demo', 'demo'), ('Live', 'live'),],
                                   string='Docusign Account Type')

    def test_credientials(self):
        status, baseUrl, accountId = odoo_docosign.login_docusign(self.useremail, self.userpassword, self.auth_key)

        if status != '200':
            raise osv.except_osv("Failure!", " Connection Failed !")
        else:
            raise osv.except_osv("Success!", " Connection Successful !")


class AdobeSignAgreement(models.Model):
    _name = 'docusign.agreement'

    name = fields.Char(string="Document Name", readonly="1")
    agreement_id = fields.Char(string="Agreement Id", readonly="1")
    customer_agreement_id = fields.Char(string="Agreement Id", readonly="1")
    customer_id = fields.Many2one('res.partner','Customer')
    agreement_status = fields.Char(string="Salesperson Agreement Status")
    customer_agreement_status = fields.Char(string="Customer Agreement Status")
    salesperson_signed = fields.Boolean("Salesperson Signed")
    customer_signed = fields.Boolean("Customer Signed")
    unsigned_file_data_adobesign = fields.Many2many('ir.attachment', 'unsigneddocuagreement_ir_attachments_rel',
                                                  'unsigneddocuagreement_id', 'attachment_id', 'Unsigned Attachments')

    upload_file_data_adobesign = fields.Many2many('ir.attachment', 'docuagreement_ir_attachments_rel',
                                              'docuagreement_id', 'attachment_id', 'Salesperson Signed Attachments')

    salesperson_signed_file_data_adobesign = fields.Many2many('ir.attachment', 'customerdocuagreement_ir_attachments_rel',
                                                              'docuagreementsale_id', 'attachment_id',
                                                              'Customer Signed Attachments')


class AdobeSignAgreementSale(models.Model):
    _name = 'docusignsale.agreement'

    name = fields.Char(string="Document Name", readonly="1")
    agreement_id = fields.Char(string="Agreement Id", readonly="1")
    customer_agreement_id = fields.Char(string="Customer Agreement Id", readonly="1")
    customer_id = fields.Many2one('sale.order','Customer')
    agreement_status = fields.Char(string="Status")
    customer_agreement_status = fields.Char(string="Customer Agreement Status")
    salesperson_signed = fields.Boolean("Salesperson Signed")
    customer_signed = fields.Boolean("Customer Signed")

    unsigned_file_data_adobesign = fields.Many2many('ir.attachment', 'unsigneddocuagreementsale_ir_attachments_rel',
                                                  'unsigneddocuagreementsale_id', 'attachment_id', 'Unsigned Attachments')

    upload_file_data_adobesign = fields.Many2many('ir.attachment', 'docuagreementsale_ir_attachments_rel',
                                              'docuagreementsale_id', 'attachment_id', 'Salesperson Signed Attachments')

    salesperson_signed_file_data_adobesign = fields.Many2many('ir.attachment', 'customerdocuagreementsale_ir_attachments_rel',
                                                  'docuagreementsale_id', 'attachment_id',
                                                  'Customer Signed Attachments')


class PartnerInherit(models.Model):
    _inherit = 'res.partner'

    attachment_ids = fields.Many2many('ir.attachment', 'partner_ir_attachments_rel', 'partner_id',
                                                                        'attachment_id', 'Attachments (Only PDF)')

    account_id = fields.Many2one('docu.credentials',string='DocuSign Account')

    agreement_ids = fields.One2many('docusign.agreement', 'customer_id', 'Agreements')
    sales_person_agreement_ids = fields.Many2one('docusign.agreement', "Sales Person's Signed Agreements")

    @api.multi
    def send_documents(self):
        if not self.env.context.get('key'):
            receiver_name = self.env.user.name
            receiver_email = self.account_id.useremail if self.account_id else ""
            attachment_ids = self.attachment_ids
            agreement = {}
        else:
            receiver_name = self.name
            receiver_email = self.email
            attachment_ids = self.sales_person_agreement_ids.upload_file_data_adobesign
            agreement = self.sales_person_agreement_ids
        account_id = self.account_id
        model_info = {}
        model_info['model_name'] = str(self._inherit)
        model_info['id'] = self.id

        self.env['docusign.send'].send_documents(agreement, receiver_name, receiver_email, attachment_ids, account_id, model_info)

        ### editntg ###
        Attachment = self.env['ir.attachment']
        cr = self._cr

        query = "SELECT attachment_id FROM partner_ir_attachments_rel WHERE partner_id=" + str(self.id) + ""

        cr.execute(query)
        attachments = Attachment.browse([row[0] for row in cr.fetchall()])
        if attachments:
            print( "attachments")
            print (attachments)
            attachments.unlink()

        self.env.cr.commit()
        raise osv.except_osv(("Success!"), ("Document Sent Successfully !"))

        ### end editing ###

    @api.multi
    def documents_status(self):
        print ("coming in res.partner documents_status")
        documents = self
        if len(documents) == 0:
            documents = self.search([])

        ### Editing ###
        model_info = {}
        model_info['model_name'] = str(self._inherit)

        self.env['docusign.send'].document_status(documents, model_info)

        ### End Editing ###


class QuotationInherit(models.Model):
    _inherit = 'sale.order'

    attachment_ids = fields.Many2many('ir.attachment', 'saleorder_ir_attachments_rel', 'saleorder_id',
                                            'attachment_id', 'Attachments')

    account_id = fields.Many2one('docu.credentials','DocuSign Account')
    agreement_ids = fields.One2many('docusignsale.agreement', 'customer_id', 'Agreements')
    sales_person_agreement_ids = fields.Many2one('docusignsale.agreement', "Sales Person's Signed Agreements")

    def send_documents(self):
        if not self.env.context.get('key'):
            receiver_name = self.env.user.name
            receiver_email = self.account_id.useremail if self.account_id else ""
            attachment_ids = self.attachment_ids
            agreement = {}
        else:
            receiver_name = self.partner_id.name
            receiver_email = self.partner_id.email
            attachment_ids = self.sales_person_agreement_ids.upload_file_data_adobesign
            agreement = self.sales_person_agreement_ids

        ### editing ###

        account_id = self.account_id
        model_info = {}
        model_info['model_name'] = str(self._inherit)
        model_info['id'] = self.id

        # self.env['docusign.send'].send_documents(receiver_name, receiver_email, attachment_ids)
        self.env['docusign.send'].send_documents(agreement, receiver_name, receiver_email, attachment_ids, account_id, model_info)

        ### end editing ###

        ### editntg ###
        Attachment = self.env['ir.attachment']
        cr = self._cr

        query = "SELECT attachment_id FROM saleorder_ir_attachments_rel WHERE saleorder_id=" + str(self.id) + ""

        cr.execute(query)
        attachments = Attachment.browse([row[0] for row in cr.fetchall()])
        if attachments:
            print( "attachments")
            print( attachments)
            attachments.unlink()

        self.env.cr.commit()
        raise osv.except_osv(("Success!"), ("Document Sent Successfully !"))

        ### end editing ###

    @api.multi
    def documents_status(self):
        print ("coming in sale.order documents_status")
        documents = self
        if len(documents) == 0:
            documents = self.search([])

        ### Editing ###
        model_info = {}
        model_info['model_name'] = str(self._inherit)
        ### model_info['id'] = self.id

        self.env['docusign.send'].document_status(documents, model_info)

        ### End Editing ###


class SendDocument(models.Model):
    _name = "docusign.send"

    @api.multi
    def send_documents(self, agreement_rec, receiver_name, receiver_email, attachment_ids, account_id, model_info):
        # print "need to check self"
        # print self
        # print receiver_name
        # print self.id

        user = account_id
        docusign_email = user.useremail
        docusign_pwd = user.userpassword
        docusign_auth_key = user.auth_key

        if not receiver_email:
            raise ValidationError('Recipient email has not been defined')

        if not attachment_ids:
            raise ValidationError('Attachments not found')

        if not docusign_email or not docusign_pwd or not docusign_auth_key:
            raise ValidationError('Connection Failed! Docusign credentials are missing.')

        for file in attachment_ids:
            attach_file_name = file.name
            filename, file_extension = os.path.splitext(attach_file_name)

            if file_extension != '.pdf':
                raise ValidationError('File extension must be .pdf')

            if self._uid != file.create_uid.id:
                raise ValidationError('Authentication Failed! Please verify your docusign account.')

            status, baseUrl, accountId = odoo_docosign.login_docusign(docusign_email, docusign_pwd, docusign_auth_key)

            if not status == '200':
                raise ValidationError('Connection Failed! Please check Docusign credentials.')

            attach_file_data = file.sudo().read(['datas_fname', 'datas'])
            file_data_encoded_string = attach_file_data[0]['datas']
            envelop_id = odoo_docosign.send_docusign_file(docusign_email, docusign_pwd,
                                                docusign_auth_key, attach_file_name, file_data_encoded_string, receiver_email)



            customer_id = model_info['id']

            if str(model_info['model_name']) == 'res.partner':
                print ("coming in %s check", model_info['model_name'])
                agreement_id = envelop_id
                print( agreement_id)
                if receiver_email == account_id.useremail:
                    salesperson_signed = False
                    customer_signed = False
                    agreement_rec = self.env['docusign.agreement'].create({
                        'name': file.name,
                        'agreement_id': agreement_id,
                        'customer_id': int(customer_id),
                        'agreement_status': 'sent',
                        'salesperson_signed': salesperson_signed,
                        'customer_signed': customer_signed
                    })
                    partner_id = agreement_rec.id
                    values = {'name': attach_file_name,
                              'type': 'binary',
                              'res_id': partner_id,
                              'res_model': 'res.partner',
                              'partner_id': partner_id,
                              'datas': file_data_encoded_string,
                              'index_content': 'image',
                              'datas_fname': attach_file_name,
                              }
                    attach_id = self.env['ir.attachment'].create(values)
                    # agreement_rec.write({
                    #     "unsigned_file_data_adobesign": [[6, 0, [attach_id]]]
                    # })
                    # self.env.cr.commit()

                    self.env.cr.execute(
                        """ insert into unsigneddocuagreement_ir_attachments_rel values (%s,%s) """ % (
                            partner_id, attach_id.id))
                else:
                    customer_signed = True
                    salesperson_signed = False
                    agreement_rec.write({
                        'name': file.name,
                        'customer_agreement_status': 'sent',
                        'customer_agreement_id': agreement_id,
                        'customer_id': int(customer_id),
                        'salesperson_signed': salesperson_signed,
                        'customer_signed': customer_signed
                    })
                ###editing code


            elif str(model_info['model_name']) == 'sale.order':
                print ("coming in %s check", model_info['model_name'])
                agreement_id = envelop_id
                print( agreement_id)
                if receiver_email == account_id.useremail:
                    salesperson_signed = False
                    customer_signed = False
                    agreement_rec = self.env['docusignsale.agreement'].create({
                        'name': file.name,
                        'agreement_id': agreement_id,
                        'customer_id': int(customer_id),
                        'agreement_status': 'sent',
                        'salesperson_signed': salesperson_signed,
                        'customer_signed': customer_signed
                    })
                    ###editing code
                    partner_id = agreement_rec.id
                    values = {'name': attach_file_name,
                              'type': 'binary',
                              'res_id': partner_id,
                              'res_model': 'res.partner',
                              'partner_id': partner_id,
                              'datas': file_data_encoded_string,
                              'index_content': 'image',
                              'datas_fname': attach_file_name,
                              }
                    attach_id = self.env['ir.attachment'].create(values)
                    self.env.cr.execute(
                        """ insert into unsigneddocuagreementsale_ir_attachments_rel values (%s,%s) """ % (
                            partner_id, attach_id.id))
                else:
                    salesperson_signed = False
                    customer_signed = True
                    agreement_rec.write({
                        'name': file.name,
                        'customer_agreement_id': agreement_id,
                        'customer_id': int(customer_id),
                        'customer_agreement_status': 'sent',
                        'salesperson_signed': salesperson_signed,
                        'customer_signed': customer_signed
                    })

        self.env.cr.commit()

    @api.multi
    def document_status(self, documents, model_info):

        for document in documents:
            ### if document.agreement_ids and document.account_id:
            if document.agreement_ids:
                user = document.account_id
                docusign_email = user.useremail
                docusign_pwd = user.userpassword
                docusign_auth_key = user.auth_key

                if not docusign_email or not docusign_pwd or not docusign_auth_key:
                    raise ValidationError('Connection Failed! Docusign credentials are missing.')

                for agreement in document.agreement_ids:
                    if agreement.agreement_status != 'completed':
                        envelope_id = agreement.agreement_id

                        if not envelope_id:
                            raise ValidationError(('Connection Failed! Docusign envelope is missing.'))

                        status, baseUrl, accountId = odoo_docosign.login_docusign(docusign_email, docusign_pwd,
                                                                                  docusign_auth_key)
                        if status != '200':
                            raise ValidationError(('Connection Failed! Please check Docusign credentials.'))

                        docu_status, complete_path = odoo_docosign.download_documents(docusign_email,
                                                                                      docusign_pwd, docusign_auth_key, baseUrl,
                                                                                      envelope_id)

                        if complete_path != '':
                            path_split = complete_path.rsplit('/', 1)
                            attach_file_name = path_split[1]
                            folder_path = path_split[0]
                            with open(complete_path, "rb") as open_file:
                                encoded_string = base64.b64encode(open_file.read())
                            doc_id = agreement.id
                            values = {'name': attach_file_name,
                                      'type': 'binary',
                                      'res_id': doc_id,
                                      'res_model': 'res.partner',
                                      'datas': encoded_string,
                                      'index_content': 'image',
                                      'datas_fname': attach_file_name,
                                      }
                            attach_id = self.env['ir.attachment'].create(values)

                            if str(model_info['model_name']) == 'res.partner':

                                self.env.cr.execute(
                                    """ insert into docuagreement_ir_attachments_rel values (%s,%s) """ % (
                                        doc_id, attach_id.id))

                            elif str(model_info['model_name']) == 'sale.order':

                                self.env.cr.execute(
                                    """ insert into docuagreementsale_ir_attachments_rel values (%s,%s) """ % (
                                        doc_id, attach_id.id))

                            os.remove(complete_path)
                            if os.path.exists(folder_path):
                                shutil.rmtree(folder_path)
                        agreement.agreement_status = docu_status
                        if docu_status == 'completed':
                            agreement.salesperson_signed = True
                        self.env.cr.commit()
                    elif agreement.customer_agreement_status != 'completed':
                        envelope_id = agreement.customer_agreement_id

                        if not envelope_id:
                            continue

                        status, baseUrl, accountId = odoo_docosign.login_docusign(docusign_email, docusign_pwd,
                                                                                  docusign_auth_key)
                        if status != '200':
                            raise ValidationError(('Connection Failed! Please check Docusign credentials.'))

                        docu_status, complete_path = odoo_docosign.download_documents(docusign_email,
                                                                                      docusign_pwd, docusign_auth_key,
                                                                                      baseUrl,
                                                                                      envelope_id)

                        if complete_path != '':
                            path_split = complete_path.rsplit('/', 1)
                            attach_file_name = path_split[1]
                            folder_path = path_split[0]
                            with open(complete_path, "rb") as open_file:
                                encoded_string = base64.b64encode(open_file.read())
                            doc_id = agreement.id
                            values = {'name': attach_file_name,
                                      'type': 'binary',
                                      'res_id': doc_id,
                                      'res_model': 'res.partner',
                                      'datas': encoded_string,
                                      'index_content': 'image',
                                      'datas_fname': attach_file_name,
                                      }
                            attach_id = self.env['ir.attachment'].create(values)

                            if str(model_info['model_name']) == 'res.partner':

                                self.env.cr.execute(
                                    """ insert into customerdocuagreement_ir_attachments_rel values (%s,%s) """ % (
                                        doc_id, attach_id.id))

                            elif str(model_info['model_name']) == 'sale.order':

                                self.env.cr.execute(
                                    """ insert into customerdocuagreementsale_ir_attachments_rel values (%s,%s) """ % (
                                        doc_id, attach_id.id))

                            os.remove(complete_path)
                            if os.path.exists(folder_path):
                                shutil.rmtree(folder_path)
                        agreement.customer_agreement_status = docu_status
                        if docu_status == 'completed':
                            agreement.customer_signed = True
                        self.env.cr.commit()