# -*- coding: utf-8 -*-
{
    'name': "Box Integration",

    'summary': """
        Box gives you a single platform to accelerate your business processes and increase 
        employee productivity.""",

    'description': """
        ODOO is a fully integrated suite of business modules that encompass the traditional ERP functionality.
        Box is a document management and storage system. Box is a web-based application that integrates with
        Microsoft Office and it is highly configurable and usage varies substantially between organizations.
        ODOO integration with Box enhances operation of organization with legitimate documentation.
    """,

    'author': "Techloyce",
    'website': "http://www.techloyce.com",
    'images': ['static/description/banner.png'],

    'price': 349,
    'currency': 'EUR',
    'category': 'Document Management',
    'version': '13.0.0.0.1',
    'depends': ['base', 'sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'installable': True,
    'application': True,
    'license' : 'OPL-1', 
}
