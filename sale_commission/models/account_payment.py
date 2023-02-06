# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    commission_item_id = fields.Many2one('sale.commission.item', string="Commission Item")
    sale_commission_item_payment_id = fields.One2many('sale.commission.item', 'payment_id', string="Commissions",
                                                    domain=[('commission_type', '=', 'payment')])