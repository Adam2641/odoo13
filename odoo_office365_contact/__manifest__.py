# -*- coding: utf-8 -*-
{
    'name': "Odoo Office365 Contact Sync",

    'summary': """
        Odoo is a fully integrated suite of business modules that encompass the traditional ERP functionality.
                Odoo Office365 Connector provides the opportunity to sync calendar between ODOO and Office365.
            """,

    'description': """
        -
    """,
    'author': "Techloyce",
    'website': "http://www.techloyce.com",
    'category': 'CRM',
	'license' : 'OPL-1',
    'price': 499,
    'currency': 'EUR',
    'version': '0.1',
    'depends': ['base', 'crm'],
    'images': [
        'static/description/banner.png',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'data/scheduler.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
	'installable': True,
    'application': True,
    'license' : 'OPL-1',
}
