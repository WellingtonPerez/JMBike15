from odoo import api, fields, models

class AccountJournal(models.Model):   
    _inherit = 'account.journal'

    close_type = fields.Selection(string='Tipo Cierre',
                                  selection =[('cash','Efectivo'),
                                              ('bank','Banco'),
                                              ('card','Tarjetas'),
                                              ('check','Cheque'),
                                              ('transfer','Tranferencias')],
                                            required=False,
                                            copy=False)