# -*- coding: utf-8 -*-
from odoo import http

# class SalesforceConnector(http.Controller):
#     @http.route('/salesforce_connector/salesforce_connector/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/salesforce_connector/salesforce_connector/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('salesforce_connector.listing', {
#             'root': '/salesforce_connector/salesforce_connector',
#             'objects': http.request.env['salesforce_connector.salesforce_connector'].search([]),
#         })

#     @http.route('/salesforce_connector/salesforce_connector/objects/<model("salesforce_connector.salesforce_connector"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('salesforce_connector.object', {
#             'object': obj
#         })


