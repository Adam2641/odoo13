# -*- coding: utf-8 -*-
{
    'name': "SharePoint",

    'summary': """Document Management using SharePoint ODOO Connector""",

    'description': """
        ODOO is a fully integrated suite of business modules that encompass the traditional ERP functionality.
        SharePoint is a document management and storage system.
        SharePoint is a web-based application that integrates with Microsoft Office and
        it is highly configurable and usage varies substantially between organizations.
        ODOO integration with SharePoint enhances operation of organization with legitimate
        documentation.
    """,
    'author': "Techloyce",
    'website': "http://www.techloyce.com",

    'category': 'Document Management',
    'version': '12.0.0.1.0',
    'price':499,
    'currency':'EUR',
    'license' : 'OPL-1',
    'depends': ['sale'],
    'data': [
        'views/templates.xml',
        'security/ir.model.access.csv',
    ],
	'images': [
        'static/description/banner1.png',
    ],

}

