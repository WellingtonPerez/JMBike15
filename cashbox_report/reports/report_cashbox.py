# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)

class CashboxReportMain(models.AbstractModel):
    _name = 'report.cashbox_report.report_cashbox_main'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Render report template"""

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        return {
            'doc_ids': data['form']['ids'],
            'doc_model': data['form']['model'],
            'docs': docs,
            'data': data['form']['info'],
            'payment_methods': data['form']['payment_methods'],
            'invoices': data['form']['invoices'],
            'headers': data['form']['headers'],
            'credit_notes': data['form']['credit_notes'],
            'credit_notes_issued': data['form']['credit_notes_issued'],
            'cash_invoice_open': data['form']['cash_invoice_open'],
            'other_payment_details': data['form']['other_payment_details'],
            'advance': data['form']['advance'],
            'balance_favor': data['form']['balance_favor'],
        }


class CashboxReportCashier(models.AbstractModel):
    _name = 'report.cashbox_report.report_cashbox_cashier'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Render report template"""
        docs = self.env['cashbox.cashier'].browse(self._context.get(
            'active_id'))
        return {
            'doc_ids': docids,
            'doc_model': data['form']['model'],
            'docs': docs,
            'data': data['form']['info'],
            'payment_methods': data['form']['payment_methods'],
            'invoices': data['form']['invoices'],
            'headers': data['form']['headers'],
            'credit_notes': data['form']['credit_notes'],
            'credit_notes_issued': data['form']['credit_notes_issued'],
            'cash_invoice_open': data['form']['cash_invoice_open'],
            'other_payment_details': data['form']['other_payment_details'],
            'advance': data['form']['advance'],
            'balance_favor': data['form']['balance_favor'],
        }
