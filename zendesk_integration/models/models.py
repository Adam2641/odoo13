# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.osv import osv
from zenpy import Zenpy
from zenpy.lib.api_objects import Comment
import os
import json
import requests
import base64


root_path = os.path.dirname(os.path.abspath(__file__))


class Zendesk_con(models.Model):
    _inherit = 'res.users'

    co_url = fields.Char(string='Company URL', required=True)
    email_id = fields.Char(string='Company Email', required=True)
    passw = fields.Char(string='Email Password', required=True)

    def test_connection(self):
        creds = {
            'email': self.env.user.email_id,
            'password': self.env.user.passw,
            'subdomain': self.env.user.co_url
        }
        zenpy_client = Zenpy(**creds)
        if not zenpy_client:
            raise osv.except_osv('', 'Authentication Credentials are not valid')
        raise osv.except_osv('', 'Successfully Connected to Zendesk')

    @api.model
    def auto_sync_data(self):
        self.sync_data()

    def sync_data(self):
        creds = {
            'email': self.env.user.email_id,
            'password': self.env.user.passw,
            'subdomain': self.env.user.co_url
        }
        zenpy_client = Zenpy(**creds)
        if zenpy_client:
            for user in zenpy_client.users():
                if not self.env['res.partner'].search([('email', '=', user.email)]):
                    if user.role != 'admin' and user.email != 'customer@example.com':
                        self.env['res.partner'].create({
                            'name': user.name,
                            'email': user.email,
                        })
                        self.env.cr.commit()

            tickets = zenpy_client.search(type='ticket')
            for ticket in tickets:
                comment_ids = None
                if not self.env['zendesk.tickets'].search([('ticket_id', '=', str(ticket.id))]):
                    if ticket.created_at:
                        date, t, time = ticket.created_at.partition('T')
                        newtime = time.replace("Z", "")
                        requested = date+"  "+newtime
                    else:
                        requested = ''
                    self.env['zendesk.tickets'].create({
                        'ticket_id': str(ticket.id),
                        'name': ticket.requester.name if ticket.requester.name else None,
                        'description': ticket.description if ticket.description else None,
                        'subject': ticket.subject if ticket.subject else None,
                        'requester': ticket.requester.email if ticket.requester.email else None,
                        'requested': requested,
                        'type': ticket.type if ticket.type else None,
                        'priority': ticket.priority if ticket.priority else None,
                        'status': ticket.status if ticket.status else None,
                    })
                    self.env.cr.commit()
                    comment_id = self.env['zendesk.tickets'].search([('ticket_id', '=', str(ticket.id))]).id
                    comments = zenpy_client.tickets.comments(ticket.id)
                    for comment in comments:
                        author_id = self.env['res.partner'].search([('email', '=', comment.author.email)]).id
                        self.env['mail.message'].create({
                            'comment_id': str(comment.id),
                            'message_type': 'comment',
                            'body': comment.body,
                            'display_name': comment.author.name if comment.author.name else None,
                            'email_from': comment.author.email if comment.author.email else None,
                            'author_id': author_id,
                            'ticket_id': comment_id,
                            'model': 'zendesk.tickets',
                            'res_id': comment_id
                        })
                else:
                    if ticket.created_at:
                        date, t, time = ticket.created_at.partition('T')
                        newtime = time.replace("Z", "")
                        requested = date+"  "+newtime
                    else:
                        requested = ''
                    self.env['zendesk.tickets'].write({
                        'ticket_id': str(ticket.id),
                        'name': ticket.requester.name if ticket.requester.name else None,
                        'description': ticket.description if ticket.description else None,
                        'subject': ticket.subject if ticket.subject else None,
                        'requester': ticket.requester.email if ticket.requester.email else None,
                        'requested': requested,
                        'type': ticket.type if ticket.type else None,
                        'priority': ticket.priority if ticket.priority else None,
                        'status': ticket.status if ticket.status else None,
                    })
                    self.env.cr.commit()
                    comment_id = self.env['zendesk.tickets'].search([('ticket_id', '=', str(ticket.id))]).id
                    comments = zenpy_client.tickets.comments(ticket.id)
                    for comment in comments:
                        if not self.env['mail.message'].search([('comment_id', '=', str(comment.id))]):
                            author_id = self.env['res.partner'].search([('email', '=', comment.author.email)]).id
                            self.env['mail.message'].create({
                                'comment_id': str(comment.id),
                                'message_type': 'comment',
                                'body': comment.body,
                                'display_name': ticket.requester.name if ticket.requester.name else None,
                                'email_from': ticket.requester.email if ticket.requester.email else None,
                                'author_id': author_id,
                                'ticket_id': comment_id,
                                'model': 'zendesk.tickets',
                                'res_id': comment_id
                            })
            raise osv.except_osv('', 'Successfully sync data to odoo')
        else:
            raise osv.except_osv('', 'Something went wrong please check your credentials')


class Zendesk_Tickets(models.Model):
    _name = 'zendesk.tickets'
    _inherit = 'mail.thread'

    image = fields.Binary(string="Image")
    ticket_id = fields.Char(string='Ticket Number')
    name = fields.Char(string='Name')
    description = fields.Text(string='Description')
    subject = fields.Char(string='Subject')
    requester = fields.Char(string='Requester')
    requested = fields.Char(string='Requested')
    type = fields.Selection([('question', 'Question'), ('incident', 'Incident'), ('problem', 'Problem'), ('task', 'Task')], default='question')
    priority = fields.Selection([('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')], default='low')
    status = fields.Selection([('open', 'Open'), ('pending', 'Pending'), ('solved', 'Solved')], default='open')
    public = fields.Boolean(string='Comment Publicly')
    tags = fields.Many2many('zendesk.tags', string="Add Tags")
    file_to_upload = fields.Many2many('ir.attachment', 'upload_ir_attachment_rel', 'upload_id', 'attachment_id',
                                      'Attachments')
    comment = fields.Text(string='Comment')

    def update_ticket(self):
        tag = []
        if self.env.user.email_id and self.env.user.co_url and self.env.user.passw:
            auth = {
                'email': self.env.user.email_id,
                'password': self.env.user.passw,
                'subdomain': self.env.user.co_url
            }
            zenpy_client = Zenpy(**auth)
            if zenpy_client:
                for id in self.tags.ids:
                    tag.append(self.env['zendesk.tags'].search([('id', '=', id)]).name)
                ticket = zenpy_client.tickets(id=int(self.ticket_id))
                if ticket:
                    ticket.status = self.status
                    ticket.type = self.type
                    ticket.priority = self.priority
                    ticket.tags.extend(tag)
                    zenpy_client.tickets.update(ticket)
        else:
            raise osv.except_osv('', 'Authentication Credentials are not valid')

    def send_message(self):
        complete_path = None
        if self.env.user.email_id and self.env.user.co_url and self.env.user.passw:
            auth = {
                'email': self.env.user.email_id,
                'password': self.env.user.passw,
                'subdomain': self.env.user.co_url
            }
            zenpy_client = Zenpy(**auth)
            if zenpy_client:
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

                ticket = zenpy_client.tickets(id=int(self.ticket_id))
                if ticket:
                    if complete_path:
                        upload_instance = zenpy_client.attachments.upload(complete_path)
                        ticket.comment = Comment(body=self.comment, public=self.public,
                                                 uploads=[upload_instance.token])
                    else:
                        ticket.comment = Comment(body=self.comment, public=self.public)
                zenpy_client.tickets.update(ticket)
                context = self._context
                current_uid = context.get('uid')
                user = self.env['res.users'].browse(current_uid)
                comment_id = self.env['zendesk.tickets'].search([('ticket_id', '=', str(ticket.id))]).id
                author_id = self.env['res.partner'].search([('email', '=', user.email)]).id

                self.env['mail.message'].create({
                    'message_type': 'comment',
                    'body': self.comment,
                    'display_name': user.name,
                    'email_from': user.email,
                    'author_id': author_id,
                    'ticket_id': comment_id,
                    'model': 'zendesk.tickets',
                    'res_id': comment_id
                })
                self.env.cr.commit()


class Zendesk_Tags(models.Model):
    _name = 'zendesk.tags'

    name = fields.Char()


class Edit_Mail_Message(models.Model):
    _inherit = 'mail.message'

    ticket_id = fields.Many2one('zendesk.tickets', string='Comments')
    comment_id = fields.Char(string='Comment Id')


