# -*- coding: utf-8 -*-
{
    'name': 'Sale Commission',
    'summary': 'Commissions for sales',
    'author': 'Angstrom Mena',
    'category': 'sales',
    'depends': ['sale','sales_team', 'account'],
    'data': [
        "security/ir.model.access.csv",
        "views/sale_commission_target_views.xml",
        "views/sale_commission_range_views.xml",
        "views/sale_commission_views.xml",
        "views/sale_commission_item_views.xml",
        "views/menu_items.xml",
    ],
}
