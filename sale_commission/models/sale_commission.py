# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleCommission(models.Model):
    _name = 'sale.commission'
    _inherit = ['mail.thread']

    name = fields.Char(string='Description', required=True, tracking=True)
    user_ids = fields.Many2many('res.users', string="Salesperson", tracking=True)
    partner_ids = fields.Many2many('res.partner', string="Third Party", tracking=True)
    start_date = fields.Date(string="Start Date", required=True, tracking=True)
    end_date = fields.Date(string="End Date", required=True)
    commission_sale_ids = fields.One2many('sale.commission.item', 'name', string="Commission Items",
                                          domain=[('commission_type', '=', 'sale')], tracking=True)
    commission_payment_ids = fields.One2many('sale.commission.item', 'name', string="Commission Items",
                                             domain=[('commission_type', '=', 'payment')], tracking=True)
    commission_third_ids = fields.One2many('sale.commission.item', 'name', string="Commission Items",
                                           domain=[('commission_type', '=', 'third')], tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('processed', 'Processed')], string="State",
                             default="draft", tracking=True)
    commission_item_ids = fields.One2many('sale.commission.item', 'name', string="Commission Items")
    commission_payment_amount_ids = fields.One2many('sale.commission.payment.amount', string="Payment Totals",
                                                    store=False,
                                                    compute="compute_payment_amounts")

    def compute_commissions(self):
        self.commission_sale_ids.unlink()
        self.commission_payment_ids.unlink()
        self.commission_third_ids.unlink()
        commission_items = []
        for user_id in self.user_ids:
            move_ids = self.env['account.move'].search([('invoice_user_id', '=', user_id.id),
                                                        ('state', '=', 'posted'),
                                                        ('move_type', '=', 'out_invoice'),
                                                        ('invoice_date', '>=', self.start_date),
                                                        ('invoice_date', '<=', self.end_date)])
            invoiced_total = sum(move_ids.mapped('amount_untaxed'))
            sale_target_ids = self.env['sale.commission.target'].search([('user_id', '=', user_id.id),
                                                                         ('start_date', '>=', self.start_date),
                                                                         ('end_date', '<=', self.end_date)])
            for sale_target_id in sale_target_ids:
                invoiced_percent = (invoiced_total / sale_target_id.target) * 100
                sale_range_ids = self.env['sale.commission.range'].search([('min', '<=', invoiced_percent),
                                                                           ('max', '>=', invoiced_percent),
                                                                           ('commission_type', '=', 'sale')])
                if not sale_range_ids:
                    sale_range_ids = self.env['sale.commission.range'].search([('min', '<', invoiced_percent),
                                                                               ('max', '<', invoiced_percent),
                                                                               ('no_limit', '=', True),
                                                                               ('commission_type', '=', 'sale')])
                for sale_range_id in sale_range_ids:
                    for move_id in move_ids.filtered(lambda x: not x.sale_commission_item_sale_ids):
                        commission_items.append({'name': self.id,
                                                 'order_id': move_id.order_id.id,
                                                 'invoice_id': move_id.id,
                                                 'user_id': user_id.id,
                                                 'comission_range_id': sale_range_id.id,
                                                 'amount': (
                                                                   move_id.amount_untaxed * sale_range_id.commission_percent) / 100})
                for move_id in move_ids:
                    for payment_id in move_id.payment_ids.filtered(
                            lambda x: x.date >= self.start_date and x.date <= self.end_date and not x.sale_commission_item_payment_id):
                        current_days = payment_id.date - move_id.invoice_date
                        sale_range_ids = self.env['sale.commission.range'].search([('min', '<=', current_days.days),
                                                                                   ('max', '>=', current_days.days),
                                                                                   ('commission_type', '=', 'payment')])
                        if not sale_range_ids:
                            sale_range_ids = self.env['sale.commission.range'].search([('min', '<', current_days.days),
                                                                                       ('max', '<', current_days.days),
                                                                                       ('no_limit', '=', True),
                                                                                       ('commission_type', '=',
                                                                                        'payment')])
                        for sale_range_id in sale_range_ids:
                            commission_items.append({'name': self.id,
                                                     'order_id': move_id.order_id.id,
                                                     'invoice_id': move_id.id,
                                                     'payment_id': payment_id.id,
                                                     'user_id': user_id.id,
                                                     'comission_range_id': sale_range_id.id,
                                                     'amount': (
                                                                       payment_id.amount * sale_range_id.commission_percent) / 100})

        for partner_id in self.partner_ids:
            move_ids = self.env['account.move'].search([('partner_id', '=', partner_id.parent_id.id),
                                                        ('state', '=', 'posted'),
                                                        ('move_type', '=', 'out_invoice'),
                                                        ('invoice_date', '>=', self.start_date),
                                                        ('invoice_date', '<=', self.end_date)])
            sale_range_ids = self.env['sale.commission.range'].search([('partner_id', '=', partner_id.id)])
            for sale_range_id in sale_range_ids:
                for move_id in move_ids.filtered(lambda x: not x.sale_commission_item_third_ids):
                    commission_items.append({'name': self.id,
                                             'order_id': move_id.order_id.id,
                                             'invoice_id': move_id.id,
                                             'partner_id': partner_id.id,
                                             'comission_range_id': sale_range_id.id,
                                             'amount': (
                                                               move_id.amount_untaxed * sale_range_id.commission_percent) / 100})

        self.env['sale.commission.item'].create(commission_items)

    def compute_payment_amounts(self):
        commission_payment_amount = self.env['sale.commission.payment.amount']
        commission_payment_amount_ids = commission_payment_amount
        for user_id in self.user_ids:
            amount = sum(self.commission_item_ids.filtered(lambda x: x.user_id == user_id).mapped('amount'))
            commission_payment_amount_ids += commission_payment_amount.create({'paid_to': user_id.name,
                                                                               'amount': amount,
                                                                               'currency_id': user_id.company_id.currency_id.id})
        for partner_id in self.partner_ids:
            amount = sum(self.commission_item_ids.filtered(lambda x: x.partner_id == partner_id).mapped('amount'))
            commission_payment_amount_ids += commission_payment_amount.create({'paid_to': partner_id.name,
                                                                               'amount': amount,
                                                                               'currency_id': partner_id.currency_id.id})
        self.commission_payment_amount_ids = commission_payment_amount_ids

    def validate(self):
        self.state = 'pending'

    def process(self):
        self.state = 'processed'

    def reset_draft(self):
        self.state = 'draft'


class SaleCommissionPaymentAmount(models.TransientModel):
    _name = "sale.commission.payment.amount"

    paid_to = fields.Char(string="Salesperson/Third Party")
    amount = fields.Monetary(string="Amount")
    currency_id = fields.Many2one('res.currency', string="Currency")
