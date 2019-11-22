# -*- coding: utf-8 -*-
{
    'name': 'ODOO Xero',
    'version': '12.0.0.1.0',
    'category': 'Sales',
    'summary': 'ODOO Xero',
    'author': 'Techloyce',
    'website': 'http://www.techloyce.com',
    'depends': ['sale','sale_management','contacts'],
    'price': 499,
    'currency': 'EUR', 
    'data': [
          'security/ir.model.access.csv',
          'views/xero_view.xml',

    ],
    'demo': [
        # 'demo/res_partner_demo.xml',
    ],
	
    'installable': True,
    'application': True,
	
	'images': [
        'static/description/banner.png',
    ],
    'license' : 'OPL-1', 
}
