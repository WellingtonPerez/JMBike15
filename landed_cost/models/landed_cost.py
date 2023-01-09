# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    product_detail_ids = fields.One2many(
        comodel_name='stock.product.detail',
        inverse_name='landed_cost_id',
        string='Detalle por producto',
        copy=False)

    # @api.multi
    def compute_landed_cost(self):
        result = super(StockLandedCost, self).compute_landed_cost()

        detail_lines = self.env['stock.product.detail']
        detail_lines.search([('landed_cost_id', 'in', self.ids)]).unlink()

        products = {}
        for line in self.valuation_adjustment_lines:

            if line.product_id.type != 'product':
                continue
            additional_cost = line.additional_landed_cost / line.quantity
            value = line.former_cost / line.quantity

            # last_id = self.env['stock.product.detail'].search([('product_id','=',line.product_id.id)])[-1].new_cost

            if line.product_id.id not in products.keys():
                products[line.product_id.id] = {
                    'name': self.name,
                    'landed_cost_id': self.id,
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'actual_cost': value,
                    'additional_cost': additional_cost,
                    'new_cost': value + additional_cost,
                    'list_price': line.product_id.list_price,
                    'old_price': line.product_id.list_price,
                    'old_cost': line.product_id.standard_price,
                    'change_price': False
                }
            else:
                products[line.product_id.id]['additional_cost'] += additional_cost
                products[line.product_id.id]['new_cost'] += additional_cost

            margen = 0
            estimado = 0
            if line.product_id.list_price > 0:
                margen = (line.product_id.list_price - line.product_id.standard_price) / line.product_id.list_price
                if margen > 0 and (1 - margen) > 0:
                    estimado = products[line.product_id.id]['new_cost'] / (1 - margen)
                    products[line.product_id.id]['list_price'] = estimado
                else:
                    margen = (line.product_id.list_price - products[line.product_id.id][
                        'new_cost']) / line.product_id.list_price

        for key, value in products.items():
            self.env['stock.product.detail'].create(value)

        return result

    # @api.multi
    def button_validate(self):
        res = super(StockLandedCost, self).button_validate()
        if res:
            for item in self.product_detail_ids:
                # Si el usuario desactiva el cotejo para cambiar el precio, no se actualiza
                if not item.change_price:
                    continue

                new_price = item.list_price
                if new_price != item.product_tmpl_id.list_price:
                    item.product_tmpl_id.write({'list_price': new_price})

        return res


class StockProductDetail(models.Model):
    _name = 'stock.product.detail'
    _description = 'Stock Landed Cost Product Details'

    name = fields.Char(u'Descripción', required=True)
    landed_cost_id = fields.Many2one(
        comodel_name='stock.landed.cost',
        string=u'Liquidación',
        ondelete='cascade',
        required=True)
    product_id = fields.Many2one('product.product', 'Producto', required=True)
    product_tmpl_id = fields.Many2one(
        related='product_id.product_tmpl_id',
        string='Plantilla Producto',
    )

    list_price = fields.Float(string='Precio de venta', )
    old_price = fields.Float(string='Precio de Anterior', )
    old_cost = fields.Float(string='Costo Anterior', )
    change_price = fields.Boolean(string="Modificar Precio", default=True)
    margin = fields.Float(string="Margin")

    quantity = fields.Float(
        string='Cantidad',
        default=1.0,
        digits=dp.get_precision('Product Unit of Measure'),
        required=True)
    actual_cost = fields.Float(
        'Costo actual unitario',
        digits=dp.get_precision('Product Price'),
        readonly=True)
    additional_cost = fields.Float(
        string=u'Costo de Importación',
        digits=dp.get_precision('Product Price'),
        readonly=True)
    new_cost = fields.Float(
        string=u'Nuevo Costo',
        digits=dp.get_precision('Product Price'),
        readonly=True)

    @api.onchange('margin')
    def recompute_list_price(self):
        self.list_price = self.new_cost + ((self.new_cost * self.margin) / 100)
