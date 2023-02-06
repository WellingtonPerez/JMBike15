# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SaleCommissionRange(models.Model):
    _name = 'sale.commission.range'
    _inherit = ['mail.thread']

    name = fields.Char(string="Description", required=True, tracking=True)
    min = fields.Integer(string="Min Target", required=False, tracking=True)
    max = fields.Integer(string="Max Target", required=False, tracking=True)
    no_limit = fields.Boolean(string="Unlimited", tracking=True)
    partner_id = fields.Many2one('res.partner', string="Third Party", tracking=True)

    commission_percent = fields.Float(string="Commission Percent", required=True, tracking=True)
    commission_type = fields.Selection([('sale', 'Sale'),
                                        ('payment', 'Payment'),
                                        ('third', 'Third Party')], string="Commission Type", required=True,
                                       tracking=True)

    _sql_constraints = [('unique_partner_id', 'unique(partner_id)', 'Thirt Party range must be unique')]

    @api.constrains('min', 'max')
    def check_tops(self):
        if self.commission_type != 'third':
            if self.min < 0:
                raise ValidationError(_("Min Target Top must be greather than 0"))
            if self.max <= self.min and not self.no_limit:
                raise ValidationError(_("Max Target Top must be greather than Min Target Top"))
            intercepted_commissions = self.search([('min', '<=', self.min),
                                                   ('max', '>=', self.min),
                                                   ('id', '!=', self.id),
                                                   ('commission_type', '=', self.commission_type)])
            if intercepted_commissions:
                raise ValidationError(
                    _("Target Ranges interception with %s" % ','.join(intercepted_commissions.mapped('name'))))
