# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software
# See LICENSE file for full copyright & licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_create_landed_costs(self):
        res = super(AccountMove, self).button_create_landed_costs()
        purchase_id = False
        stock_picking = []
        if self.invoice_origin:
            purchase_id = self.env['purchase.order'].search([
                ('name', '=', self.invoice_origin)])
        if purchase_id and purchase_id.picking_ids:
            for record in purchase_id.picking_ids:
                stock_picking.append(record.id)
        if res.get('res_id'):
            landed_cost_id = self.env['stock.landed.cost'].search([
                ('id', '=', res['res_id'])])
            landed_cost_id.write({
                'picking_ids': [(6, 0, stock_picking)],
                })
            res.update(res_id=landed_cost_id.id)
        return res
