# -*- coding: utf-8 -*-
{
    'name': "Dropbox Connector ODOO",

    'summary': """
        Dropbox is a document management and storage system. Dropbox is a web-based application that integrates
        with Microsoft Office and it is highly configurable and usage varies substantially between
        organizations.
        """,
    'description': """
        ODOO is a fully integrated suite of business modules that encompass the traditional ERP functionality.
        Dropbox is a document management and storage system. Dropbox is a web-based application that integrates
        with Microsoft Office and it is highly configurable and usage varies substantially between
        organizations. ODOO integration with Dropbox enhances operation of organization with legitimate
        documentation.
    """,
    'author': "Techloyce",
    'website': "http://www.techloyce.com",
     'category': 'Document Management',
    'version':'12.0.0.1.0',
    'depends': ['base', 'sale_management'],
    'images': ['static/description/banner.png'],
    'price': 349,
    'currency': 'EUR',
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'installable': True,
    'application': True,
    'license' : 'OPL-1',
}
