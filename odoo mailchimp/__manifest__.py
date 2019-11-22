# -*- coding: utf-8 -*-
{
    'name': "odoo mailchimp",

    'summary': """
        Odoo MailChimp provides functionality to import/export lists and send campaigns.
        """,

    'description': """
        Odoo is a fully integrated suite of business modules that encompass the traditional ERP functionality.
        Use Odoo MailChimp to import / export lists between MailChimp and odoo and send Campaigns.
        Odoo MailChimp provides functionality to import/export lists and send campaigns.
    """,

    'author': "Techloyce",
    'website': "http://www.techloyce.com",
    'category': 'Sale',
    'version': '12.0.0.1.0',
    # any module necessary for this one to work correctly
    'depends': ['base', 'sale_management'],
    'images': [
        'static/description/banner.png',
    ],
    'price': 499,
    'currency': 'EUR',
    "license": "OPL-1",
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
}
