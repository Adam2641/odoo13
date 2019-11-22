# -*- coding: utf-8 -*-
{
    'name': "Odoo Zendesk Integration",

    'summary': """
        Zendesk Support puts all your customer support interactions in one place.""",

    'description': """
        Odoo Zendesk Support puts all your customer support interactions in one place, 
        so communication is seamless, personal, and efficient–which means more 
        productive agents and satisfied customers.
    """,

    'author': "Techloyce",
    'website': "http://www.techloyce.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customer Relationship Management',
    'version': '12.0.1.0.0',
    # 'price': ,
    'currency': 'EUR',
    'license': 'OPL-1',

    # any module necessary for this one to work correctly
    'depends': ['base','mail','contacts'],
    'images': [
            'static/description/banner.png',
        ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/configuration.xml',
        'views/tickets.xml',
        'data/schedulers.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}