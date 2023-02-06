# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleCommissionItem(models.Model):
    _name = 'sale.commission.item'

    name = fields.Many2one('sale.commission', string="Commission")
    order_id = fields.Many2one('sale.order', string="Sale Order")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    payment_id = fields.Many2one('account.payment', string="Payment")
    partner_id = fields.Many2one('res.partner', string="Third Party")
    user_id = fields.Many2one('res.users', string="Salesperson")
    comission_range_id = fields.Many2one('sale.commission.range', string="Commission Range")
    amount = fields.Monetary(string="Amount")
    currency_id = fields.Many2one(related="user_id.company_id.currency_id")
    invoiced_amount = fields.Monetary(string='Invoiced Amount', related='invoice_id.amount_untaxed')
    paid_amount = fields.Monetary(string="Paid Amount", related='payment_id.amount')
    commission_percent = fields.Float(related="comission_range_id.commission_percent")
    commission_type = fields.Selection(related="comission_range_id.commission_type")
    state = fields.Selection(related="name.state")