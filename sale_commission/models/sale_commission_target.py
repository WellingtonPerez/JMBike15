# -*- coding: utf-8 -*-
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


class SaleCommissionTarget(models.Model):
    _name = 'sale.commission.target'
    _inherit = ['mail.thread']

    name = fields.Char(string="Description", compute="compute_name", tracking=True)
    user_id = fields.Many2one('res.users', string="Salesperson", required=True, tracking=True)
    target = fields.Monetary(string="Sale Target", required=True, tracking=True)
    start_date = fields.Date(string="Start Date", required=True, tracking=True)
    end_date = fields.Date(string="End Date", required=True, tracking=True)
    currency_id = fields.Many2one(related="user_id.currency_id", tracking=True)

    _sql_constraints = [('unique_salesperson_target', 'unique(user_id,start_date,end_date)',
                         _('Target must be unique by user and date Range')),
                        ('unique_partner_target', 'unique(partner_id,start_date,end_date)',
                         _('Target must be unique by Third Party and date Range'))]

    def compute_name(self):
        for target in self:
            target.name = "%s - %s (%s - %s)" % (target.user_id.name,
                                                 target.target,
                                                 target.start_date,
                                                 target.end_date)

    @api.constrains('start_date', 'end_date')
    def check_ranges(self):
        if self.end_date <= self.start_date:
            raise ValidationError(_("Target Start Date must be greather than Rage End Date"))
