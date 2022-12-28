# -*- coding: utf-8 -*-
{
    'name': 'Cierre de Caja',
    'version': '12.0',
    'category': '',
    'summary': "Cierre de Caja",
    'author': 'Yasmany Castillo <yasmany003@gmail.com>',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/cashbox_data.xml',
        'data/report_paperformat.xml',
        'reports/report_cashbox_cashier.xml',
        # 'reports/report_cashbox_main.xml',
        # 'wizard/wizard_cashbox_view.xml',
        # 'views/cashbox_view.xml',
        'views/cashbox_cashier_view.xml',
        'views/res_config_settings_view.xml',
        'views/journal.xml',
    ],
}



