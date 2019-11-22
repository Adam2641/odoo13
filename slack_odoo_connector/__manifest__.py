# -*- coding: utf-8 -*-
{
    'name': "Slack Odoo Connector",

    'summary': """Slack Odoo Integration""",

    'description': """Odoo is a fully integrated suite of business modules that encompass the traditional ERP functionality. Odoo Slack allows you to send updates on your Slack.
    """,
    
    'author': "Techloyce",
    'website': "http://www.techloyce.com",
 
   
    'category': 'sale',
    'version': '11.0.1.0.0',
    'price': 349,
    'currency': 'EUR',
     "license": "OPL-1", 


    # any module necessary for this one to work correctly
    'depends': ['base', 'sale_management', 'base_automation', 'crm'],
    # 'depends': ['base', 'sale','base_automation'],
    'images': [
        'static/description/banner1.png',
    ],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_company.xml',
        # 'views/slack_view.xml',
        'data/scheduler.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}
