# -*- coding: utf-8 -*-

{
    'name': 'eCommerce - Fraud Detection',
    'category': 'Website/Website',
    'sequence': 50,
    'summary': 'Detect fraudulent orders',
    'website': 'https://www.erpgap.com/ecommerce/',
    'version': '1.1',
    'depends': ['website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/website_sale_fraud_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
