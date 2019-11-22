# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import webbrowser
import base64
from openerp.osv import osv
from datetime import datetime, timedelta
import time
import json
from boxsdk.exception import BoxAPIException, BoxOAuthException
import requests
import os
from boxsdk import OAuth2, Client

root_path = os.path.dirname(os.path.abspath(__file__))


class BoxSettings(models.Model):
    _name = 'box.settings'

    name = fields.Char(string="Name", required=True)
    client_id = fields.Char(string="Client ID", required=True)
    client_secret = fields.Char(string="Client Secret", required=True)
    redirect_uri = fields.Char(string="Redirect Uri", required=True)
    responce_code = fields.Char(string="Response Code")
    access_token = fields.Char(string="Access Token", readonly=True)
    refresh_token = fields.Char(string="Refresh Token", readonly=True)
    expires_in = fields.Char('Expires IN', readonly=True)
    json_file = fields.Binary('CLIENT SECRET FILE')
    auth_url = fields.Char("Auth URL")

    @api.one
    def get_code(self):
        oauth = OAuth2(
            client_id=self.client_id,
            client_secret=self.client_secret,
        )
        auth_url, csrf_token = oauth.get_authorization_url(self.redirect_uri)
        self.auth_url = auth_url
        webbrowser.open_new_tab(auth_url)

    @api.one
    def test_connection(self):
        try:
            oauth = OAuth2(
                client_id=self.client_id,
                client_secret=self.client_secret,
            )
            access_token, refresh_token = oauth.authenticate(self.responce_code)
            self.access_token = access_token
            self.refresh_token = refresh_token
            self.expires_in = int(round(time.time() * 1000))
        except BoxOAuthException:
            raise UserError('Code is not Correct')


class BoxSyncer(models.Model):
    _inherit = 'res.partner'

    get_files_ids = fields.One2many('box.connector.id', 'get_files_id', string="Attachments")
    downloaded_files = fields.Many2many('ir.attachment', 'downloaded_ir_attachments_rel', 'downloaded_id',
                                        'attachment_id', 'Attachments')
    user_name_google = fields.Many2one('box.settings', string='Box Account')
    file_to_upload = fields.Many2many('ir.attachment', 'upload_ir_attachment_rel', 'upload_id', 'attachment_id',
                                      'Attachments')
    file_name = fields.Char('Filename')
    google_drive_folder_id = fields.Char('Box Drive Folder Id')

    @api.one
    def upload_document(self):
        if not self.file_to_upload:
            raise ValidationError(_('Box attachments are missing'))
        if not self.user_name_google:
            raise ValidationError(_('Box Account is missing'))
        if self.user_name_google.expires_in:
            expires_in = datetime.fromtimestamp(int(self.user_name_google.expires_in) / 1e3)
            expires_in = expires_in + timedelta(seconds=3600)
            nowDateTime = datetime.now()
            if nowDateTime > expires_in:
                self.generate_refresh_token()
        try:
            oauth = OAuth2(
                client_id=self.user_name_google.client_id,
                client_secret=self.user_name_google.client_secret,
                access_token=self.user_name_google.access_token,
                refresh_token=self.user_name_google.refresh_token,
            )
            client = Client(oauth)
            all_folder = client.folder(folder_id='0').get_items(limit=None)
        except BoxOAuthException:
            raise UserError('Problem with Box Connection')

        folders_name = []
        for folder_name in all_folder:
            folders_name.append(folder_name['name'])
        if self.name in folders_name:
            all_folder = client.folder(folder_id='0').get_items(limit=None)
            for folder in all_folder:
                if self.name == folder.name:
                    for each in self.file_to_upload:
                        attach_file_name = each.name
                        attach_file_data = each.sudo().read(['datas_fname', 'datas'])
                        directory_path = os.path.join(root_path, "files")
                        if not os.path.isdir(directory_path):
                            os.mkdir(directory_path)
                        file_path = os.path.join("files", attach_file_name)
                        complete_path = os.path.join(root_path, file_path)
                        with open(complete_path, "wb") as text_file:
                            data = base64.decodestring(attach_file_data[0]['datas'])
                            text_file.write(data)
                        stream = open(complete_path, "rb")
                        try:
                            client.folder(folder_id=folder['id']).upload_stream(stream, attach_file_name)
                            if complete_path:
                                os.remove(complete_path)
                        except BoxAPIException:
                            raise UserError('This File Name is Already Exists For %s' % self.name)
                    raise osv.except_osv(_("Success!"), _(" File(s) Uploaded In %s !" % self.name))

        else:
            new_folder = client.folder('0').create_subfolder(self.name)
            for each in self.file_to_upload:
                attach_file_name = each.name
                attach_file_data = each.sudo().read(['datas_fname', 'datas'])
                directory_path = os.path.join(root_path, "files")
                if not os.path.isdir(directory_path):
                    os.mkdir(directory_path)
                file_path = os.path.join("files", attach_file_name)
                complete_path = os.path.join(root_path, file_path)
                with open(complete_path, "wb") as text_file:
                    data = base64.decodestring(attach_file_data[0]['datas'])
                    text_file.write(data)
                stream = open(complete_path, "rb")
                try:
                    client.folder(folder_id=new_folder['id']).upload_stream(stream, attach_file_name)
                    if complete_path:
                        os.remove(complete_path)
                except BoxAPIException:
                    raise UserError('This File Name is Already Exists For %s' % self.name)
            raise osv.except_osv(_("Success!"), _(" File(s) Uploaded In %s !" % self.name))

    @api.one
    def generate_refresh_token(self):
        print("generating token")
        if self.user_name_google.refresh_token:
            settings = self.env['box.settings'].search([])
            settings = settings[0] if settings else settings
            if not settings.client_id or not settings.redirect_uri or not settings.client_secret:
                raise osv.except_osv(_("Error!"), (_("Please ask admin to add Box settings!")))
            header = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            response = requests.post(
                'https://api.box.com/oauth2/token',
                data='grant_type=refresh_token&client_id=' + self.user_name_google.client_id + '&client_secret='
                     + self.user_name_google.client_secret + '&refresh_token=' + self.user_name_google.refresh_token
                , headers=header).content
            response = json.loads((str(response)[2:])[:-1])
            if 'access_token' not in response:
                response["error_description"] = response["error_description"].replace("\\r\\n", " ")
                raise osv.except_osv(("Error!"), (response["error"] + " " + response["error_description"]))
            else:
                settings.write({
                    "access_token": response['access_token'],
                    "refresh_token": response['refresh_token'],
                    "expires_in": int(round(time.time() * 1000))
                })
                self.env.cr.commit()

    @api.one
    def import_documents(self):
        if self.user_name_google.expires_in:
            expires_in = datetime.fromtimestamp(int(self.user_name_google.expires_in) / 1e3)
            expires_in = expires_in + timedelta(seconds=3600)
            nowDateTime = datetime.now()
            if nowDateTime > expires_in:
                self.generate_refresh_token()
        try:
            oauth = OAuth2(
                client_id=self.user_name_google.client_id,
                client_secret=self.user_name_google.client_secret,
                access_token=self.user_name_google.access_token,
                refresh_token=self.user_name_google.refresh_token
            )
            client = Client(oauth)
            all_folder = client.folder(folder_id='0').get_items(limit=None)
        except BoxOAuthException:
            raise UserError('Problem with Box Connection')

        for folder in all_folder:
            if folder.name == self.name:
                all_files = client.folder(folder_id=folder.object_id).get()['item_collection']['entries']
                if not all_files:
                    raise osv.except_osv(_("Information!"), _("No file(s) to import from %s !" % self.name))
                attachment_ids = []
                for files in all_files:
                    file_url = client.file(file_id=files['id']).create_shared_link(allow_download=True,allow_preview=True,password=None).shared_link['url']
                    size = float(client.file(file_id=files['id']).get().size)/1000.0
                    attachment = self.env['box.connector.id'].create({
                        # 'datas': img_byte,
                        'name': files.name,
                        'url': file_url,
                        'type': client.file(file_id=files['id']).get().type,
                        'size': str(size) + " KB"
                    })
                    self.env.cr.commit()
                    attachment_ids.append(attachment.id)
                self.get_files_ids = [[6, 0, attachment_ids]]


class BoxConnectionId(models.Model):
    _name = 'box.connector.id'

    get_files_id = fields.Many2one('res.partner')
    name = fields.Char('Name')
    url = fields.Char('Download URL')
    type = fields.Char('Type')
    size = fields.Char('Size')
