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
    'category': 'Customer Relationship Management',
    'version': '13.0.0.0.1',
    # 'price': ,
    'currency': 'EUR',
    'license': 'OPL-1',
    'depends': ['base','mail','sale_management'],
    'images': [
            'static/description/banner.png',
        ],
    'data': [
        'security/ir.model.access.csv',
        'views/configuration.xml',
        'views/tickets.xml',
        'data/schedulers.xml',
    ],
    'installable': True,
    'application': True,
}
