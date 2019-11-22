# -*- coding: utf-8 -*-
{
    'name': "odoo_hubspot",
    'summary': """
            Odoo Hubspot Connector provides the opportunity to import contacts and companies from Hubspot to ODOO.
            """,
    'description': """
       Odoo is a fully integrated suite of business modules that encompass the traditional ERP functionality.
        Odoo Hubspot Connector provides the opportunity to import contacts and companies from Hubspot to ODOO.
    """,
    'author': "Techloyce",
    'website': "http://www.techloyce.com",
    'category': 'sale',
    'price': 349,
    "license": "OPL-1",
    'currency': 'EUR',
    'version': '12.0.0.1.0',
    'depends': ['base', 'crm'],
    'images': [
        'static/description/banner.png',
    ],
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'data/scheduler.xml',
    ],
}
