# -*- coding: utf-8 -*-
{
    'name': "ODOO Salesforce Connector",
    'version': '0.1',
    'category': 'Sales',
    'summary': 'ODOO Salesforce',
    'author': 'Techloyce',
    'website': 'http://www.techloyce.com',
    'images': [
        'static/description/banner.png',
    ],
    'depends': ['sale', 'crm', 'sale_crm'],
    'price': 499,
    'currency': 'EUR',
    'license' : 'OPL-1',

    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        # 'data/schedule.xml',
    ],
    'installable': True,
    'application': True,
}
