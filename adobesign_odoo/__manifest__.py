# -*- coding: utf-8 -*-
{
    'name': "Adobe Sign ODOO",

    'summary': """Connect Adobe Sign with ODOO""",

    # 'description': """
    #     Long description of module's purpose
    # """,

    'author': "Techloyce",
    'website': "http://www.techloyce.com",
    'category': 'Document Management',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['sale_management'],
    'license' : 'OPL-1', 
    'price': 499,
    'currency': 'EUR',

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    'images': [
        'static/description/banner.png',
    ],

    'installable': True,
    'application': True,
    'license' : 'OPL-1', 

}
