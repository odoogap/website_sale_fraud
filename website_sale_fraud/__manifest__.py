# -*- coding: utf-8 -*-
# Copyright 2025 ERPGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    'name': 'eCommerce - Fraud Detection',
    'category': 'Website/Website',
    'sequence': 50,
    'summary': 'Detect fraudulent orders',
    'website': 'https://www.erpgap.com/ecommerce/',
    'version': '1.1',
    'depends': [
        'website_sale',
        'payment',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/capture_flow_data.xml',
        'data/payment_provider_data.xml',
        'views/website_sale_fraud_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
