# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    show_payment_method = fields.Boolean(
        string="Mostrar detalle métodos de pago", )
    show_charge_client = fields.Boolean(
        string="Mostrar Cobros a Clientes", )
    show_balance_favor = fields.Boolean(
        string="Mostrar balance a favor", )
    show_invoice_advance = fields.Boolean(
        string="Mostrar anticipos de facturas", )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    show_payment_method = fields.Boolean(
        related='company_id.show_payment_method', readonly=False, )
    show_charge_client = fields.Boolean(
        related='company_id.show_charge_client', readonly=False, )
    show_balance_favor = fields.Boolean(
        related='company_id.show_balance_favor', readonly=False, )
    show_invoice_advance = fields.Boolean(
        related='company_id.show_invoice_advance', readonly=False, )
