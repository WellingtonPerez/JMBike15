# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    commission_item_id = fields.Many2one('sale.commission.item', string="Commission Item")
    order_id = fields.Many2one('sale.order', string="Sale Order", compute="compute_order")
    payment_ids = fields.One2many('account.payment', string="Payments", compute="compute_payments")
    sale_commission_item_sale_ids = fields.One2many('sale.commission.item', 'invoice_id', string="Sale Commissions",
                                                  domain=[('commission_type', '=', 'sale')])
    sale_commission_item_third_ids = fields.One2many('sale.commission.item', 'invoice_id',
                                                    string="Third Party Commissions",
                                                    domain=[('commission_type', '=', 'third')])

    def compute_order(self):
        for move in self:
            self.order_id = self.env['sale.order'].search([('invoice_ids', 'in', [move.id])])

    def compute_payments(self):
        for move in self:
            payment_ids = []
            for payment_info in move._get_reconciled_info_JSON_values():
                payment_ids.append(payment_info.get('account_payment_id'))
            move.payment_ids = move.payment_ids.browse(payment_ids)
