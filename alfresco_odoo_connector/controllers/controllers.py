# -*- coding: utf-8 -*-
from odoo import http

# class Alfodoo(http.Controller):
#     @http.route('/alfodoo/alfodoo/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/alfodoo/alfodoo/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('alfodoo.listing', {
#             'root': '/alfodoo/alfodoo',
#             'objects': http.request.env['alfodoo.alfodoo'].search([]),
#         })

#     @http.route('/alfodoo/alfodoo/objects/<model("alfodoo.alfodoo"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('alfodoo.object', {
#             'object': obj
#         })