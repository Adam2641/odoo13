# -*- coding: utf-8 -*-
from odoo import http

# class GoogleIntegration(http.Controller):
#     @http.route('/google_integration/google_integration/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/google_integration/google_integration/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('google_integration.listing', {
#             'root': '/google_integration/google_integration',
#             'objects': http.request.env['google_integration.google_integration'].search([]),
#         })

#     @http.route('/google_integration/google_integration/objects/<model("google_integration.google_integration"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('google_integration.object', {
#             'object': obj
#         })
