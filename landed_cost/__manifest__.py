# -*- coding: utf-8 -*-
{
    'name': "Landed Cost Product Detail",

    'summary': """
        Este modulo agrega un detalle de los productos liquidados.""",

    'description': """
    """,

    'author': "Yasmany Castillo",
    'website': "",

    'category': 'Warehouse',
    'version': '12.0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['stock_landed_costs',],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/landed_cost_view.xml',
    ],
}
