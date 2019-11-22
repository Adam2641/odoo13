# -*- coding: utf-8 -*-
{
    'name': "odoo_eventbrite",

    'summary': """
        Use ODOO Eventbrite to sync events between ODOO and Eventbrite""",

    'description': """
        ODOO is a fully integrated suite of business modules that encompass the traditional ERP
        functionality. ODOO integration with Eventbrite gives us power to manually sync events
        between ODOO and Eventbrite.
    """,

    'author': "Techloyce",
    'website': "http://www.techloyce.com",
    'category': 'sale',
    'version': '0.1',
    'depends': ['base', 'sale_management', 'event'],
    'images': [
        'static/description/banner.png',
    ],
    'price': 449,
    "license": "OPL-1",
    'currency': 'EUR',

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
}
