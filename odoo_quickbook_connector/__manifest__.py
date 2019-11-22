# -*- coding: utf-8 -*-
{
    'name': "QuickBooks ODOO",

    'summary': """
        ODOO integration with Quickbooks""",

    'description': """
        Till now it only add customer to quickbooks from ODOO
    """,

    'author': "Techloyce",
    'website': "http://www.techloyce.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Generic Modules',
    'version': '0.1',
    'images': [
        'static/description/banner.png',
    ],
    'license' : 'OPL-1', 
    'price': 500,
    'currency': 'EUR',

    # any module necessary for this one to work correctly
    'depends': ['sale_management', 'stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'data/schedulers.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
