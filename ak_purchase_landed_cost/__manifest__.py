# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software
# See LICENSE file for full copyright & licensing details.

# Author: Aktiv Software
# mail:   odoo@aktivsoftware.com
# Copyright (C) 2015-Present Aktiv Software
# Contributions:
#           Aktiv Software:
#              - Sruthy K S
#              - Juhi Upadhyay
#              - Harshil Soni
#              - Tanvi Gajera

{
    'name': 'Purchase Landed Cost',
    'author': 'Aktiv Software PVT. LTD.',
    'website': 'https://aktivsoftware.com',
    'summary': 'Landed cost on single product',
    'description': """This module will allow you to add landed cost on single
            product.""",
    'price': 25.00,
    'currency': "EUR",
    'license': 'OPL-1',
    'category': 'purchase',
    'version': '15.0.1.0.0',
    'depends': [
        'purchase', 'stock', 'stock_landed_costs', 'account'
    ],
    'data': [
        'views/stock_landed_cost_views.xml',
        'views/product_views.xml'
    ],
    'images': ['static/description/Banner.jpg'],
}
