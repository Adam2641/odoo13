from odoo import models, fields, api, _
from .import adobesign
import requests
import json
from odoo.exceptions import UserError, ValidationError
from openerp.osv import osv
import time

import datetime, os

import base64

class AdobeSignAgreement(models.Model):
    _name = 'adobesign.agreement'

    name = fields.Char(string="Document Name", readonly="1")
    agreement_id = fields.Char(string="Agreement Id", readonly="1")
    customer_id =fields.Many2one('res.partner','Customer')
    agreement_status = fields.Char(string="Status")

    unsigned_file_data_adobesign = fields.Many2many('ir.attachment', 'unsignedadobeagreement_ir_attachments_rel',
                                                  'unsignedadobeagreement_id', 'attachment_id', 'Unsigned Attachments')

    upload_file_data_adobesign = fields.Many2many('ir.attachment', 'adobeagreement_ir_attachments_rel',
                                              'adobeagreement_id', 'attachment_id', 'Signed Attachments')


class AdobeSignCredentials(models.Model):
    _name = 'adobe.credentials'

    name = fields.Char(string='Adobe Sign Account Name', required=True)

    odoo_url = fields.Char(string="ODOO URL",
                           help="Write down the complete base url of your ODOO including the http/https")

    access_token = fields.Char(string='Access Token', readonly=True)
    refresh_token = fields.Char(string='Refresh Token')
    access_token_time = fields.Datetime(string='Token Generation Time')
    expire_in = fields.Char('Expires IN', readonly=True)
    client_id = fields.Char(string='Client Id', required=True)
    client_secret = fields.Char(string='Secret Id', required=True)
    api_access_point = fields.Char(string='Api Access Point')
    redirect_url = fields.Char(string='Redirect url', required=True)
    login_url = fields.Char('Login URL', compute='_compute_url', readonly=True)
    url = fields.Char(string='url')
    code = fields.Char(string='code')

    def _compute_url(self):
        authorize_url = "https://secure.na2.echosign.com/public/oauth"

        redirect_url = 'redirect_uri=' + str(self.redirect_url) + '&'
        client_id = 'client_id=' + str(self.client_id) + '&'
        authorize_url = str(authorize_url) + '?'
        scope = "scope=user_login:account+agreement_write:account+agreement_send:account+widget_write:account+library_write:account+library_read:account+agreement_read:account"
        self.login_url = authorize_url + redirect_url + client_id + 'response_type=code&' + scope   # + state

    @api.one
    def test_connection(self):
        if not self.client_id or not self.redirect_url or not self.client_secret:
            raise osv.except_osv(_("Error!"), (_(
                "Please give Credentials!")))
        else:
            try:
                self.env.user.client_id = self.client_id
                self.env.user.redirect_url = self.redirect_url
                self.env.user.client_secret = self.client_secret
                self.env.user.name = self.name

                self.api_access_point = "https://api.na2.echosign.com"
                self.env.user.api_access_point = self.api_access_point

                self.env.cr.commit()

            except Exception as e:
                raise ValidationError(_((e)))

            raise osv.except_osv(_("Success!"), (_("Successfully! Url is Generated!")))

    @api.multi
    def generate_token(self):

        if not self.code:
            raise UserError(_('Please enter ODOO url'))

        if not self.client_id or not self.redirect_url or not self.client_secret:
            raise osv.except_osv(_("Error!"), (_("Please  add credentials!")))

        else:

            header = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            try:
                response = requests.post(
                    "https://api.na2.echosign.com/oauth/token?",
                    data='grant_type=authorization_code&code=' + self.code + '&redirect_uri=' + self.redirect_url + '&client_id=' + self.client_id + '&client_secret=' + self.client_secret
                    , headers=header).content
                response = json.loads(response.decode('utf-8'))
                self.access_token = response['access_token']
                self.refresh_token = response['refresh_token']
                self.expire_in = int(round(time.time() * 1000))
                self.env.user.expire_in = self.expire_in
                self.env.user.code = self.code
                self.env.user.access_token = self.access_token
                self.env.user.refresh_token = self.refresh_token
                self.env.user.access_token_time = None
                self.env.cr.commit()

            except Exception as e:
                raise ValidationError(e)

            raise osv.except_osv(_("Success!"), (_("Successfully! Token Generated!")))


class AdobeSignPartner(models.Model):
    _inherit = 'res.partner'

    account_id = fields.Many2one('adobe.credentials','AdobeSign Account')

    adobesign_upload_data = fields.Many2many('ir.attachment', 'adobesign_ir_attachment_rel', 'adobesign_id',
                                                   'attachment_id', 'Attachments (Only PDF)')
    agreement_ids = fields.One2many('adobesign.agreement', 'customer_id', 'Agreements')

    @api.multi
    def send_document(self):
        if not self.adobesign_upload_data:
            raise UserError(_('Please Attach a PDF file'))
        if not self.email:
            raise UserError(_('Please Enter Email to send the document'))

        if not self.account_id:
            raise UserError(_('AdobeSign Account is not selected'))
        token_obj = self.account_id

        access_token = token_obj.access_token
        expire_in = token_obj.expire_in
        client_id = token_obj.client_id
        client_secret = token_obj.client_secret
        api_access_point = token_obj.api_access_point
        refresh_token = token_obj.refresh_token
        redirect_url = token_obj.redirect_url

        if access_token:
            token = adobesign.verify_token(access_token, redirect_url,expire_in, api_access_point, client_id, client_secret, refresh_token)

            if not token:
                raise UserError(_('Error in refresing token'))
            else:
                access_token = token
                token_obj.access_token = access_token
                token_obj.access_token_time = datetime.datetime.now()
        else:
            raise UserError(_('Please Generate Access Token'))

        for file in self.adobesign_upload_data:
            file_name = file.name
            filename = file_name
            file_name = file_name.split('.')
            if file_name[-1] != 'pdf':
                raise UserError(_('Please attach PDF file'))

            file_path = adobesign.get_file_path(file)
            transient_doc_id = adobesign.upload_document(api_access_point, file_path, access_token)
            content_encoded = adobesign.read_file(file_path)
            os.remove(file_path)
            agreement = adobesign.send_agreement(api_access_point, access_token, transient_doc_id, self.email, file.name)
            if 'Access token' in str(agreement[1]):
                raise UserError(_(str(agreement[1])))
            if'unable to process your PDF document' in str(agreement[1]):
                raise UserError(_(str(agreement[1])))
            agreement_id = agreement[1]
            agreement_rec = self.env['adobesign.agreement'].create({
                'name': file.name,
                'agreement_id': agreement_id,
                'customer_id':self.id,
                'agreement_status':'OUT_FOR_SIGNATURE',
            })

            partner_id = agreement_rec.id

            values = {'name': filename,
                      'type': 'binary',
                      'res_id': partner_id,
                      'res_model': 'res.partner',
                      'partner_id': partner_id,
                      'datas': content_encoded,
                      'index_content': 'image',
                      'datas_fname': filename,
                      }
            attach_id = self.env['ir.attachment'].create(values)
            self.env.cr.execute(
                """ insert into unsignedadobeagreement_ir_attachments_rel values (%s,%s) """ % (
                    partner_id, attach_id.id))
        self.env.cr.commit()

        Attachment = self.env['ir.attachment']
        cr = self._cr
        query = "SELECT attachment_id FROM adobesign_ir_attachment_rel WHERE adobesign_id=" + str(self.id) + ""
        cr.execute(query)
        attachments = Attachment.browse([row[0] for row in cr.fetchall()])
        if attachments:
            attachments.unlink()

        self.env.cr.commit()
        raise osv.except_osv(_("Success!"), _("Document Sent Successfully !"))

    @api.multi
    def update_status(self):
        if not self.agreement_ids:
            return

        if not self.account_id:
            raise UserError(_('AdobeSign Account is not selected'))
        token_obj = self.account_id

        access_token = token_obj.access_token
        api_access_point = token_obj.api_access_point
        expire_in = token_obj.expire_in
        client_id = token_obj.client_id
        client_secret = token_obj.client_secret
        refresh_token = token_obj.refresh_token
        agreements = self.agreement_ids
        redirect_url = token_obj.redirect_url

        if access_token:
            token = adobesign.verify_token(access_token, redirect_url,expire_in, api_access_point, client_id, client_secret, refresh_token)
            if not token:
                raise UserError(_('Error in refresing token'))
            else:
                access_token = token
                token_obj.access_token = access_token
                token_obj.access_token_time = datetime.datetime.now()
        else:
            raise UserError(_('Please Generate Access Token'))

        for agreement in agreements:
            if agreement.agreement_status != 'SIGNED':
                agreement_id = agreement.agreement_id
                status_array = adobesign.get_agreement_detail(api_access_point, access_token, agreement_id)

                if status_array:
                    status = status_array[0]

                    if status == 'SIGNED':
                        filename = status_array[1]
                        response_content = adobesign.download_agreement(api_access_point, access_token, agreement_id)
                        if response_content:
                            encoded_string = base64.b64encode(response_content)

                            try:
                                filename = str(filename).split(']')[1]
                            except:
                                pass

                            partner_id = agreement.id
                            values = {'name': filename,
                                      'type': 'binary',
                                      'res_id': partner_id,
                                      'res_model': 'res.partner',
                                      'partner_id': partner_id,
                                      'datas': encoded_string,
                                      'index_content': 'image',
                                      'datas_fname': filename,
                                      }
                            attach_id = self.env['ir.attachment'].create(values)
                            self.env.cr.execute(
                                """ insert into adobeagreement_ir_attachments_rel values (%s,%s) """ % (
                                    partner_id, attach_id.id))
                        else:
                            raise UserError(_('Error in downloading file'))

                    agreement.agreement_status = status

