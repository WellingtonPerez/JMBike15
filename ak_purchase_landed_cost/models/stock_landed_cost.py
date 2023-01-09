# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software
# See LICENSE file for full copyright & licensing details.

from collections import defaultdict
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero

SPLIT_METHOD = [
    ('equal', 'Equal'),
    ('by_quantity', 'By Quantity'),
    ('by_current_cost_price', 'By Current Cost'),
    ('by_weight', 'By Weight'),
    ('by_volume', 'By Volume'),
    ('by_product', 'By Product'),
    ('duty', 'Duty')
]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    split_method_landed_cost = fields.Selection(SPLIT_METHOD,
                                                string="Default Split Method",
                                                help="Default Split Method \
                                                when used for Landed Cost")


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def button_validate(self):
        self._check_can_validate()
        cost_without_adjusment_lines = self.filtered(
            lambda c: not c.valuation_adjustment_lines)
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(_(
                'Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

        for cost in self:
            cost = cost.with_company(cost.company_id)
            move = self.env['account.move']
            move_vals = {
                'journal_id': cost.account_journal_id.id,
                'date': cost.date,
                'ref': cost.name,
                'line_ids': [],
                'move_type': 'entry',
            }
            valuation_layer_ids = []
            cost_to_add_byproduct = defaultdict(lambda: 0.0)
            for line in cost.valuation_adjustment_lines.filtered(
                    lambda line: line.move_id):
                remaining_qty = sum(
                    line.move_id.stock_valuation_layer_ids.mapped(
                        'remaining_qty'))
                linked_layer = line.move_id.stock_valuation_layer_ids[:1]

                # Prorate the value at what's still in stock
                cost_to_add = (
                                      remaining_qty / line.move_id.product_qty) * \
                              line.additional_landed_cost
                if not cost.company_id.currency_id.is_zero(cost_to_add):
                    values = {
                        'value': cost_to_add,
                        'unit_cost': 0,
                        'quantity': 0,
                        'remaining_qty': 0,
                        'stock_valuation_layer_id': linked_layer.id,
                        'description': cost.name,
                        'stock_move_id': line.move_id.id,
                        'product_id': line.move_id.product_id.id,
                        'stock_landed_cost_id': cost.id,
                        'company_id': cost.company_id.id,
                    }
                    if line.cost_line_id.split_method == "by_product":
                        values.update({
                            'product_id': line.cost_line_id.by_product_id.id,
                        })
                    valuation_layer = self.env[
                        'stock.valuation.layer'].create(values)
                    linked_layer.remaining_value += cost_to_add
                    valuation_layer_ids.append(valuation_layer.id)
                # Update the AVCO
                product = line.move_id.product_id
                if product.cost_method == 'average':
                    cost_to_add_byproduct[product] += cost_to_add
                qty_out = 0
                if line.move_id._is_in():
                    qty_out = line.move_id.product_qty - remaining_qty
                elif line.move_id._is_out():
                    qty_out = line.move_id.product_qty
                move_vals['line_ids'] += line._create_accounting_entries(
                    move, qty_out)

            products = self.env['product.product'].browse(
                p.id for p in cost_to_add_byproduct.keys())
            for product in products:
                if not float_is_zero(
                        product.quantity_svl,
                        precision_rounding=product.uom_id.rounding):
                    product.with_company(cost.company_id).sudo().with_context(
                        disable_auto_svl=True).standard_price += \
                        cost_to_add_byproduct[product] / product.quantity_svl

            move_vals['stock_valuation_layer_ids'] = [
                (6, None, valuation_layer_ids)]
            move = move.create(move_vals)
            cost.write({'state': 'done', 'account_move_id': move.id})
            move._post()

            if cost.vendor_bill_id and cost.vendor_bill_id.state == 'posted' \
                    and cost.company_id.anglo_saxon_accounting:
                all_amls = cost.vendor_bill_id.line_ids | \
                           cost.account_move_id.line_ids
                for product in cost.cost_lines.product_id:
                    accounts = product.product_tmpl_id.get_product_accounts()
                    input_account = accounts['stock_input']
                    all_amls.filtered(
                        lambda aml: aml.account_id == input_account and not
                        aml.full_reconcile_id).reconcile()

        return True

    def compute_landed_cost(self):
        AdjustementLines = self.env['stock.valuation.adjustment.lines']
        AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()

        digits = self.env['decimal.precision'].precision_get('Product Price')
        towrite_dict = {}
        for cost in self.filtered(lambda cost: cost._get_targeted_move_ids()):
            total_qty = 0.0
            total_cost = 0.0
            total_weight = 0.0
            total_volume = 0.0
            total_line = 0.0
            all_val_line_values = cost.get_valuation_lines()
            for val_line_values in all_val_line_values:
                for cost_line in cost.cost_lines.filtered(
                        lambda x: x.product_id.product_tmpl_id.split_method_landed_cost != 'duty'):
                    val_line_values.update({'cost_id': cost.id, 'cost_line_id': cost_line.id})
                    self.env['stock.valuation.adjustment.lines'].create(val_line_values)
                for cost_line in cost.cost_lines.filtered(
                        lambda x: x.product_id.product_tmpl_id.split_method_landed_cost == 'duty'):
                    val_line_values.update({'cost_id': cost.id, 'cost_line_id': cost_line.id})
                    self.env['stock.valuation.adjustment.lines'].create(val_line_values)

                total_qty += val_line_values.get('quantity', 0.0)
                total_weight += val_line_values.get('weight', 0.0)
                total_volume += val_line_values.get('volume', 0.0)

                former_cost = val_line_values.get('former_cost', 0.0)
                total_cost += tools.float_round(
                    former_cost, precision_digits=digits) if digits else former_cost

                total_line += 1

            for line in cost.cost_lines.filtered(lambda x:x.split_method != 'duty'):
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines:
                    value = 0.0
                    if valuation.cost_line_id and \
                            valuation.cost_line_id.id == line.id:
                        if line.split_method == 'by_quantity' and total_qty:
                            per_unit = (line.price_unit / total_qty)
                            value = valuation.quantity * per_unit
                        elif line.split_method == 'by_weight' and total_weight:
                            per_unit = (line.price_unit / total_weight)
                            value = valuation.weight * per_unit
                        elif line.split_method == 'by_volume' and total_volume:
                            per_unit = (line.price_unit / total_volume)
                            value = valuation.volume * per_unit
                        elif line.split_method == 'equal':
                            value = (line.price_unit / total_line)
                        elif line.split_method == 'by_current_cost_price' and \
                                total_cost:
                            per_unit = (line.price_unit / total_cost)
                            value = valuation.former_cost * per_unit
                        elif line.split_method == 'by_product':
                            per_unit = (line.price_unit / total_qty)
                            value = valuation.former_cost * per_unit
                        elif line.split_method == 'duty':
                            if valuation.product_id.duty_ok:
                                print(valuation)
                                insurance_product_id = valuation.cost_line_id.product_id.insurance_product_id
                                freight_product_id = valuation.cost_line_id.product_id.freight_product_id
                                print(valuation.product_id)
                                print(valuation.product_id.name)
                                aditional_landed_cost = cost.valuation_adjustment_lines.filtered(lambda
                                                                             x: x.product_id == valuation.product_id and x.cost_line_id != valuation.cost_line_id)
                                print(aditional_landed_cost)
                                print(towrite_dict)

                            value = 0
                        else:
                            value = (line.price_unit / total_line)

                        if digits:
                            value = tools.float_round(
                                value, precision_digits=digits,
                                rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value
            for line in cost.cost_lines.filtered(lambda x:x.split_method == 'duty'):
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines:
                    value = 0.0
                    product_cost = valuation.former_cost
                    if valuation.cost_line_id and \
                            valuation.cost_line_id.id == line.id:
                        if valuation.product_id.duty_ok:
                            insurance_product_id = valuation.cost_line_id.product_id.insurance_product_id
                            freight_product_id = valuation.cost_line_id.product_id.freight_product_id
                            aditional_landed_cost = cost.valuation_adjustment_lines.filtered(lambda
                                                                                                     x: x.product_id == valuation.product_id and x.cost_line_id.product_id in [insurance_product_id,freight_product_id])
                            for landed_cost in aditional_landed_cost:
                                product_cost += towrite_dict[landed_cost.id]

                            value = (product_cost * valuation.product_id.duty_pecent) / 100
                        else:
                            value = (line.price_unit / total_line)

                        if digits:
                            value = tools.float_round(
                                value, precision_digits=digits,
                                rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value
        for key, value in towrite_dict.items():
            AdjustementLines.browse(key).write(
                {'additional_landed_cost': value})
        return True


class StockLandedCostLine(models.Model):
    _inherit = 'stock.landed.cost.lines'

    split_method = fields.Selection(
        SPLIT_METHOD,
        string='Split Method',
        required=True,
        help="Equal : Cost will be equally divided.\n" "By Quantity : Cost\
            will be divided according to product's \
            quantity.\n" "By Current cost : Cost will be divided according to \
            product's current cost.\n" "By Weight : Cost will be divided \
            depending on its weight.\n" "By Volume : Cost will be divided \
            depending on its volume. \n" "By Product : Cost will be divided \
            according product.")

    by_product_id = fields.Many2one('product.product', string="BY Product")

    @api.onchange('split_method')
    def onchange_split_method(self):
        if self.split_method == 'by_product':
            picking_ids = self.cost_id.mapped('picking_ids').ids
            move_ids = self.env['stock.picking'].search([
                ('id', 'in', picking_ids)]).mapped('move_ids_without_package')
            product_ids = move_ids.mapped('product_id').ids
            return {'domain': {'by_product_id': [('id', 'in', product_ids)]}}
