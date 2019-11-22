# -*- coding: utf-8 -*-
import base64

from odoo import fields, models, api, osv
from openerp.exceptions import ValidationError
from openerp.osv import osv
import requests
import json
from openerp import _
from openerp.osv import osv
from openerp.exceptions import Warning
from datetime import datetime
import os

from eventbrite import Eventbrite


class CustomUser(models.Model):
    _inherit = 'res.users'

    access_token = fields.Char(string="Access Token")

    def test_connection(self):
        status_code = False
        try:
            if not self.access_token:
                raise ValidationError('please enter access token')
            eventbrite = Eventbrite(self.access_token)
            user = eventbrite.get_user()
            if user.status_code == 200:
                status_code =  True
        except:
            raise ValidationError('Connection Failed >> invalid credentials')
        if status_code:
            raise osv.except_osv(("Success!"), ("Connection Successful"))


class EventBriteSettings(models.Model):
    _name = 'eventbrite.connector'

    sales_force = None
    field_name = fields.Char()
    event_id = fields.Char('event id')
    events = fields.One2many('event.event', 'eventbrite_connector_id')

    def sync_data(self):
        """
        :return:
        """
        try:
            eventbrite = Eventbrite(self.env.user.access_token)
            eventbrite_user = eventbrite.get_user()
            events = eventbrite.get_user_events(eventbrite_user['id'])['events']

            for event in events:
                self.event_id = event['id']
                event = eventbrite.get_event(event['id'])
                organizer = eventbrite.get_organizers(event['organizer_id'])
                eventbrite_user = eventbrite.get_user()
                user = self.env['res.users'].search([('email', '=', eventbrite_user['emails'][0]['email'])])
                if not user:
                    user = self.env['res.users'].create({
                        'name': eventbrite_user['name'],
                        'email': eventbrite_user['emails'][0]['email'],
                        'login': eventbrite_user['emails'][0]['email']
                    })
                venues = eventbrite.get_user_venues(eventbrite_user['id'])
                venue = [venue for venue in venues['venues'] if venue['id'] == event['venue_id']]
                partner = user.partner_id
                if venue:
                    venue = venue[0]
                    odoo_country = None
                    if venue['address']['country']:
                        odoo_country = self.env['res.country'].search([('code', '=', venue['address']['country'])])

                    partner.write({
                        'street': venue['address']['address_1'] if venue['address']['address_1'] else '' ,
                        'street2': venue['address']['address_2'] if venue['address']['address_2'] else '',
                        'city': venue['address']['city'] if venue['address']['city'] else '',
                        'zip': venue['address']['postal_code'] if venue['address']['postal_code'] else None,
                        'country_id': odoo_country.id if odoo_country else None
                    })
                odoo_event = self.env['event.event'].search([('eventbrite_id', '=', self.event_id)])
                eventbrite_connector_id = self.env['eventbrite.connector'].search([])[0].id
                start_date = datetime.strptime(event['start']['utc'], "%Y-%m-%dT%H:%M:%SZ")
                end_date = datetime.strptime(event['end']['utc'], "%Y-%m-%dT%H:%M:%SZ")
                if not odoo_event:
                    odoo_event = self.env['event.event'].create({
                        'name': event['name']['text'],
                        'date_begin': start_date,
                        'date_end': end_date,
                        'date_tz': event['end']['timezone'],
                        'seats_max': event['capacity'],
                        'seats_availability': 'limited',
                        'is_online': event.ok,
                        'orgnaizer_id': partner.id,
                        'user_id': user.id,
                        'address_id': partner.id,
                        'eventbrite_id': self.event_id,
                        'eventbrite_connector_id': eventbrite_connector_id,
                        'state': 'confirm' if event['status'] == 'live' else 'done'
                    })
                else:
                    odoo_event.write({
                        'name': event['name']['text'],
                        'date_begin': start_date,
                        'date_end': end_date,
                        'date_tz': event['end']['timezone'],
                        'seats_max': event['capacity'],
                        'seats_availability': 'limited',
                        'is_online': event.ok,
                        'orgnaizer_id': partner.id,
                        'user_id': user.id,
                        'address_id': partner.id,
                        'eventbrite_connector_id': eventbrite_connector_id,
                        'state': 'confirm' if event['status'] == 'live' else 'done'
                    })
                tickets = eventbrite.get_event_ticket_classes(self.event_id)
                for ticket in tickets['ticket_classes']:
                    odoo_ticket = self.env['event.event.ticket'].search(
                        [('eventbrite_id', '=', ticket['id'])]
                    )
                    if not odoo_ticket:
                        product_template = self.env['product.template'].create({
                            'name': odoo_event.name + ' ' +ticket['id'],
                            'list_price': float(ticket['cost']['major_value']) if 'cost' in ticket.keys() else 0,
                            'event_ok': True
                        })
                        odoo_product = self.env['product.product'].create({
                            'product_tmpl_id': product_template.id
                        })
                        odoo_ticket = self.env['event.event.ticket'].create({
                            'name': ticket['name'],
                            'event_id': odoo_event.id,
                            'eventbrite_id': ticket['id'],
                            'seats_max': ticket['quantity_total'],
                            'price': float(ticket['cost']['major_value']) if 'cost' in ticket.keys() else 0,
                            'product_id': odoo_product.id
                        })
                    else:
                        odoo_ticket.write({
                            'name': ticket['name'],
                            'seats_max': ticket['quantity_total'],
                            'price': float(ticket['cost']['major_value']) if 'cost' in ticket.keys() else 0,

                        })

                attendies = eventbrite.get_event_attendees(self.event_id)
                for attendie in attendies['attendees']:
                    attendee = self.env['event.registration'].search([(
                        'eventbrite_id', '=', attendie['id']
                    )])
                    if not attendee:
                        partner = self.env['res.partner'].search([('email', '=', attendie['profile']['email'])])
                        if not partner:
                            partner = self.env['res.partner'].create({
                                'name': attendie['profile']['name'],
                                'email': attendie['profile']['email']
                            })
                        ticket = self.env['event.event.ticket'].search([(
                            'eventbrite_id', '=', attendie['ticket_class_id']
                        )])

                        sale_order = self.env['sale.order'].create({
                            'partner_id': partner.id,
                            "invoice_status": "to invoice",
                            "date_order": attendie['created'].replace('T', ' '),
                        })
                        self.env["sale.order.line"].create({
                                                            'product_id': ticket.product_id.id,
                                                            'order_partner_id': partner.id,
                                                            "order_id": sale_order.id,
                                                            'event_id': odoo_event.id,
                                                            'event_ticket_id': ticket.id
                                                            })
                        sale_order.write({
                            'state': 'sale',
                            "invoice_status": "invoiced",
                        })
                        date = datetime.strptime(attendie['created'], "%Y-%m-%dT%H:%M:%SZ")
                        attendee = self.env['event.registration'].create({
                            'eventbrite_id': attendie['id'],
                            'partner_id': partner.id,
                            'name': partner.name,
                            'email': partner.email,
                            'phone': partner.phone,
                            'event_id': odoo_event.id,
                            'event_ticket_id': ticket.id,
                            'date_open':  date,
                            'sale_order_id': sale_order.id,
                            'state': 'cancel' if attendie['status'] == 'Not Attending' else 'open'
                        })
                        self.env.cr.commit()
                    else:
                        attendee.write({
                            'state': 'cancel' if attendie['status'] == 'Not Attending' else 'open'
                        })
                        self.env.cr.commit()
        except:
            raise ValidationError('Connection Failed >> invalid credentials')


class CustomEvent(models.Model):
    _inherit = 'event.event'

    eventbrite_connector_id = fields.Many2one('eventbrite.connector', string='Partner Reference',  ondelete='cascade',
                              index=True, copy=False)
    eventbrite_id = fields.Char('eventbrite identifier')


class CustomEventTicket(models.Model):
    _inherit = 'event.event.ticket'

    eventbrite_id = fields.Char('eventbrite identifier')


class CustomEventRegistration(models.Model):
    _inherit = 'event.registration'

    eventbrite_id = fields.Char('eventbrite identifier')

