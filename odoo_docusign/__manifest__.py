{
    'name': "Docusign",

    'summary': """Electronic Signature""",

    'description': """
        ODOO is a fully integrated suite of business modules that encompass the traditional ERP functionality.
        DocuSign is the Global Standard for eSignature, is the leader in eSignature transaction management.
        Global enterprises, Business departments, individual professionals, and consumers are standardizing on
        DocuSign, with more than 60,000 new users joining the DocuSign Global Network
        every day. DocuSign is used to accelerate transaction times to increase speed to results, reduce costs,
        and delight customers across nearly every industry—from financial services, insurance, technology,
        healthcare, manufacturing, communications, property management and consumer goods, to higher education
        and others. ODOO integration with Docusign enhances operation of organization with legitimate
        documentation.
    """,

    'author': "Techloyce",
    'website': "http://www.techloyce.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sale',
    'version': '12.0.0.1.0',
    # any module necessary for this one to work correctly
    'depends': ['sale_management'],
    'images': [
        'static/description/banner.png',
    ],
    'price': 449,
    'currency': 'EUR',

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/docusign.xml',
        'views/docusign_menu.xml',
    ],
    'installable': 'True',
    'application': 'True',
    'license' : 'OPL-1', 
}
