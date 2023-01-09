# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software
# See LICENSE file for full copyright & licensing details.

from odoo import models, api, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        product_ids = []
        if self._context.get("cost_id"):
            landed_cost_id = self.env["stock.landed.cost"].browse(self._context["cost_id"])
            picking_ids = landed_cost_id.mapped('picking_ids')
            move_ids = picking_ids.mapped('move_ids_without_package')
            product_ids += move_ids.mapped('product_id').ids
            return set(product_ids)
        return super()._search(args, offset, limit, order, count, access_rights_uid)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    split_method_landed_cost = fields.Selection(selection_add=[('duty', 'Duty')])

    duty_ok = fields.Boolean(string='Have Duty')
    duty_pecent = fields.Float(string="Duty Percent")

    insurance_product_id = fields.Many2one('product.product', string="Insurance")
    freight_product_id = fields.Many2one('product.product', string="Freight")
