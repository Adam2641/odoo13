# -*- coding: utf-8 -*-
{
    'name': "ODOO Shopify",

    'summary': """
        Shopify is one platform with all the ecommerce and point of sale features you need to start, run, and grow your business.
        """,

    'description': """
        Shopify is one platform with all the ecommerce and point of sale features you need to start, run, and grow your business.
        Odoo is a fully integrated suite of business modules that encompass the traditional ERP functionality.
        Odoo Shopify provides functionality to import orders and customers from your Shopify shop.
        It also provides functionality to export products from odoo to your Shopify shop.
    """,

    'author': "Techloyce",
    'website': "http://www.techloyce.com",

    'category': 'Sale',
    'version': '12.0.0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['sale_management', 'stock'],
    'images': [
        'static/description/banner.png',
    ],
    'price': 499,
    'currency': 'EUR',
    'license' : 'OPL-1', 
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/customuser.xml',
        'data/schedulers.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'application': True,
}
