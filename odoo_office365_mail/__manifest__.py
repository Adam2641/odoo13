# -*- coding: utf-8 -*-
{
    'name': "Odoo Office365 Mail Sync",

    'summary': """
            Odoo Office365 Mail Connector provides the opportunity to sync email between ODOO and Office365.
        """,

    'description':  """
        Odoo is a fully integrated suite of business modules that encompass the traditional ERP functionality.
                Odoo Office365 Mail Connector provides the opportunity to sync email between ODOO and Office365.
            """,
    'author': "Techloyce",
    'website': "http://www.techloyce.com",
    'category': 'CRM',
	
    'price': 499,
    'currency': 'EUR',
    'version': '13.0.0.1.0',
    'depends': ['base', 'crm'],
    'images': [
        'static/description/banner.png',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'data/scheduler.xml',
    ],
    'installable': True,
    'application': True,
    'license' : 'OPL-1',
}
