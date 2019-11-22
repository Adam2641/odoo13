# -*- coding: utf-8 -*-
{
    'name': "odoo office 365",

    'summary': """
                Odoo Office365 Connector provides the opportunity to sync calendar, contacts, tasks and mails between ODOO and Office365.
            """,

    'description': """
	Odoo is a fully integrated suite of business modules that encompass the traditional ERP functionality. Odoo office 365 Connector 		provides the opportunity to sync calendar, contacts,task and mail between ODOO and office 365.
    """,
    'author': "Techloyce",
    'website': "http://www.techloyce.com",
    'category': 'sale',
    'price': 499,
    'currency': 'EUR',
    'version': '12.0.0.1.2',
    'license' : 'OPL-1', 
    'depends': ['base', 'calendar', 'crm'],
    'images': [
        'static/description/banner.png',
    ],
    'data': [
        #'security/ir.model.access.csv',
        'views/views.xml',
        'data/scheduler.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
