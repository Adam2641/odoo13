# -*- coding: utf-8 -*-
{
    'name': "Alfresco",

   'summary': """Alfresco Odoo Integration""",

    'description': """
Alfresco-odoo-connector connects odoo with alfresco.
It provides mutiple attachments in odoo.
When a file is uploaded in odoo it will also be uploaded at alfresco.
In order to do so we just need alfresco URL,Username and Password.
Thers is an optional directory-name field which tells whether file should be placed in root directory or inside a directory.
    Installation Prcoess
	Windows prerequisites
		Install python if not installed
		Install setuptools and cmislib and iso8601 libraries using pip install <library-name> if not installed
		After installations copy 3 folders setuptools and cmislib and iso8601 from path python27/\Lib/\site-packages  to odoo10/\server path.

	Ubuntu prerequisites
		Install setuptools and cmislib and iso8601 libraries

	Overview
		Add alfresco credential by using Setting under Configuration menu.
		URL,Username,password are alfresco's mandatory fields and they required valid information to upload file at alfresco.
		Add files using Upload File under Document menu.
		Directory name is kept optional if its value is empty then file will be uploaded to root path of alfresco repository otherwise it will create directory with <directory-name>
    """,

    'author': "Techloyce",
    'website': "http://www.techloyce.com",

    'category': 'Document Management',
    'version': '0.1',
    'price':500,
    'currency':'EUR',

    'depends': ['sale_management'],
    'images':[
        'static/description/banner1.png'],

    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',

    ],
    'demo': [],
}

