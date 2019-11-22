# -*- coding: utf-8 -*-
{
    'name': "Box Integration",

    'summary': """
        Box gives you a single platform to accelerate your business processes and increase 
        employee productivity.""",

    'description': """
        Today’s digital-first world demands you work in an entirely new way. 
        You have to securely collaborate with partners and customers, deliver 
        innovation faster than the rest, and manage the content at the heart of it all. 
        Box gives you a single platform to accelerate your business processes and increase 
        employee productivity, all while protecting your most valuable information. 
        It’s called Cloud Content Management, and it's the ultimate business advantage.
    """,

    'author': "Techloyce",
    'website': "http://www.techloyce.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'images': ['static/description/banner.png'],

    'price': 349,
    'currency': 'EUR',
    'category': 'Document Management',

    'version': '12.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],

    'installable': True,
    'application': True,
    'license' : 'OPL-1', 
}
