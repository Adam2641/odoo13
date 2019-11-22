# -*- coding: utf-8 -*-
from odoo import http

# class ZendeskIntegration(http.Controller):
#     @http.route('/zendesk_integration/zendesk_integration/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/zendesk_integration/zendesk_integration/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('zendesk_integration.listing', {
#             'root': '/zendesk_integration/zendesk_integration',
#             'objects': http.request.env['zendesk_integration.zendesk_integration'].search([]),
#         })

#     @http.route('/zendesk_integration/zendesk_integration/objects/<model("zendesk_integration.zendesk_integration"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('zendesk_integration.object', {
#             'object': obj
#         })