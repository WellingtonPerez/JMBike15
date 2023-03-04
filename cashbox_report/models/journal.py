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

class PosPaymentMethod(models.Model):   
    _inherit = 'pos.payment.method'

    close_type = fields.Selection([('cash','Efectivo'),
                                              ('bank','Banco'),
                                              ('card','Tarjetas'),
                                              ('check','Cheque'),
                                              ('transfer','Tranferencias')], related='journal_id.close_type')