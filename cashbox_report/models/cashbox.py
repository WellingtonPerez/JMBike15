import logging
from operator import itemgetter
from odoo import api, fields, models, exceptions

_logger = logging.getLogger(__name__)


class AccountCashbox(models.Model):
    """ Cash Box Details """
    _name = 'account.cashbox'
    _description = 'Cierre de Caja'
    _order = 'date'

    name = fields.Char(string="Referencia", required=True, readonly=True, )
    date = fields.Date(string="Fecha", )
    cashier = fields.Many2one(comodel_name="res.users", string="Usuario", )
    cashbox_coin_ids = fields.One2many(
        comodel_name='cashbox.coin',
        inverse_name='cashbox_id',
        string='Desglose de efectivo',
    )
    cash_amount = fields.Float(string="Total Efectivo", )
    bank_amount = fields.Float(string="Total Banco", )
    check_amount = fields.Float(string="Total Cheque", )
    credit_card_amount = fields.Float(string="Total Tarjeta", )
    note = fields.Text(string="Observaciones", )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.user.company_id,
        required=True,
    )

    @api.multi
    def _get_journal_ids(self, type='sale'):
        journal_domain = [('company_id', '=', self.env.user.company_id.id)]

        if type == 'all':
            journal_domain.append(('type', 'in', ['sale', 'cash', 'bank']))
        else:
            journal_domain.append(('type', '=', 'sale'))
            journal_domain.append(('ncf_control', '=', True))

        journal_ids = self.env['account.journal'].search(journal_domain)
        return journal_ids

    @api.model
    def _check_payment_status(self, invoice):
        if invoice.payment_term_id.id != 1:
            return False
        return True

    @api.multi
    def _prepare_payment_info(self):
        payment_methods = {}
        payment_obj = self.env['account.payment']
        payment_ids, other_payment_details = [], []

        domain = [('payment_date', '=', self.date),
                  ('payment_type', '=', 'inbound'),
                  ('create_uid', '=', self.cashier.id),
                  ('company_id', '=', self.env.user.company_id.id),
                  ('state', 'in', ['posted','reconciled'])]
        for rec in payment_obj.search(domain):
            journal_name = rec.journal_id.name
            amount = 0.0
            if rec.invoice_ids:
                invoices_a = rec.invoice_ids.filtered(
                    lambda invoice: invoice.journal_id.ncf_control == True)
                if invoices_a:
                    amount = rec.amount

                invoices = rec.invoice_ids.filtered(
                    lambda invoice: invoice.date_invoice != self.date)
                for inv in invoices:
                    if inv.type == 'out_refund':
                        continue
                    amount = rec.amount
                    payment_ids.append(rec.id)
            else:
                payment_ids.append(rec.id)
                amount = rec.amount

            if journal_name in payment_methods.keys():
                payment_methods[journal_name] += amount
            else:
                payment_methods[journal_name] = amount

        payment_ids = set(payment_ids)
        payments = sorted(list(payment_ids))

        for p in payment_obj.browse(payments):
            date = p.payment_date
            other_payment_details.append({
                'Fecha': "{}/{}/{}".format(date[8:10], date[5:7], date[:4]),
                'Referencia': p.name,
                'Cliente': p.partner_id.name,
                'Monto': p.amount,
                'Metodo de pago': p.journal_id.name,
            })

        return (payment_methods, other_payment_details)

    @api.multi
    def _prepare_invoice_detail(self, journals):
        payment_obj = self.env['account.payment']
        invoice_details, invoice_headers, credit_notes_issued = {}, [], 0.0
        credit_notes_applied, balance_favor, advance = 0.0, 0.0, 0.0

        for journal in journals:
            journal_name = journal.name
            domain = [
                ('type', 'in', ['out_invoice', 'out_refund']),
                ('date_invoice', '=', self.date),
                ('state', 'in', ['open', 'paid']),
                ('company_id', '=', self.env.user.company_id.id),
                ('user_id', '=', self.cashier.id),
                ('journal_id', '=', journal.id)]

            for inv in self.env['account.invoice'].search(
                domain, order="number asc"):

                payments = inv._get_payments_vals()
                cash_invoice = self._check_payment_status(inv)

                values = {
                    'id': inv.id,
                    'number': inv.number,
                    'partner': inv.partner_id.name,
                    'Credito': 0.0,
                    'Contado': 0.0,
                    'NC Emitidas': 0.0,
                }

                if inv.type == 'out_invoice':
                    if cash_invoice:
                        values['Contado'] = inv.amount_total
                    else:
                        values['Credito'] = inv.amount_total

                if inv.type == 'out_refund' and inv.state in ['open', 'paid']:
                    if not values['number']:
                        values['number'] = inv.number
                    values['NC Emitidas'] = inv.amount_total
                    credit_notes_issued += inv.amount_total

                if inv.type != 'out_refund':
                    for rec in payments:
                        payment_date = rec.get('date')
                        if payment_date > self.date:
                            continue

                        minor_date = True if payment_date < self.date else False
                        header = rec.get('journal_name')

                        amount = rec.get('amount')
                        is_credit_note = True if rec.get('ref')[:3] == 'B04' else False
                        # Check balance in favor
                        if not is_credit_note:
                            payment = payment_obj.browse(
                                rec.get('account_payment_id'))
                            difference = payment.amount - amount
                            if difference:
                                balance_favor += difference

                        if not is_credit_note and minor_date:
                            header = False
                            advance += amount
                            values['Anticipo'] = amount
                            if not cash_invoice:
                                continue

                        if cash_invoice and is_credit_note:
                            header = 'NC Aplicadas'
                            credit_notes_applied += rec.get('amount')
                        elif rec.get('journal_name') == inv.journal_id.name:
                            continue

                        if header:
                            if header in values.keys():
                                values[header] += amount
                            else:
                                values[header] = amount
                            invoice_headers.append(header)

                if journal_name in invoice_details.keys():
                    invoice_details[journal_name].append(values)
                else:
                    invoice_details[journal_name] = [values]

        return (invoice_details, invoice_headers, credit_notes_issued,
                credit_notes_applied, advance, balance_favor)

    @api.model
    def prepare_data(self):
        data = {'info': {}}
        cash_invoice_open = []
        invoice_obj = self.env['account.invoice']
        journals = self._get_journal_ids()

        domain = [
            ('type', '=', 'out_invoice'),
            ('date_invoice', '=', self.date),
            ('state', 'in', ['open', 'paid']),
            ('company_id', '=', self.env.user.company_id.id),
            ('user_id', '=', self.cashier.id),
            ('journal_id', 'in', journals.ids)]
        for inv in invoice_obj.search(domain):
            journal = inv.journal_id.name
            record = data['info']
            cash, credit = 0.0, 0.0

            cash_invoice = self._check_payment_status(inv)
            if inv.type == 'out_invoice':
                if cash_invoice:
                    cash = inv.amount_total
                else:
                    credit = inv.amount_total

            if journal not in data['info'].keys():
                record[journal] = {
                    'Contado': cash,
                    'Credito': credit,
                }
            else:
                record[journal]['Contado'] += cash
                record[journal]['Credito'] += credit

            if inv.payment_term_id.id == 1 and inv.state == 'open':
                cash_invoice_open.append({
                    'number': inv.number,
                    'partner': inv.partner_id.name,
                    'date': inv.date_invoice,
                    'amount': inv.amount_total
                })

        all_journals = self._get_journal_ids(type='all')
        detail_result = self._prepare_invoice_detail(all_journals)
        invoice_details = detail_result[0]
        invoice_headers = detail_result[1]
        credit_notes_issued = detail_result[2]
        credit_notes_applied = detail_result[3]
        advance = detail_result[4]
        balance_favor = detail_result[5]

        payment_info = self._prepare_payment_info()
        data['payment_methods'] = payment_info[0]
        other_payment_details = payment_info[1]

        headers = set(invoice_headers)
        headers = sorted(list(headers))
        headers.insert(0, 'Factura')
        headers.insert(1, 'Cliente')
        headers.insert(2, 'Credito')
        headers.insert(3, 'Contado')
        headers.insert(4, 'Anticipo')
        headers.insert(-1, 'NC Emitidas')

        order_details = {}
        for k, v in invoice_details.items():
            order_details[k] = sorted(v, key=itemgetter('number'))

        return (data, order_details, headers, credit_notes_applied,
                credit_notes_issued, cash_invoice_open, other_payment_details,
                advance, balance_favor)

    def _print_report(self, data):
        return self.env.ref('cashbox_report.action_report_cashbox_manager').report_action(self, data=data)

    @api.multi
    def check_report(self):
        self.ensure_one()
        result = self.prepare_data()

        data = {'form': result[0]}
        data['form']['invoices'] = result[1]
        data['form']['headers'] = result[2]
        data['form']['credit_notes'] = result[3]
        data['form']['credit_notes_issued'] = result[4]
        data['form']['cash_invoice_open'] = result[5]
        data['form']['other_payment_details'] = result[6]
        data['form']['advance'] = result[7]
        data['form']['balance_favor'] = result[8]
        data['form']['ids'] = self.ids
        data['form']['model'] = self._name

        return self._print_report(data)


class AccountCashboxLine(models.Model):
    """ Cash Box Details """
    _name = 'cashbox.coin'
    _description = 'CashBox Coin'
    _order = 'coin_value'

    @api.one
    @api.depends('coin_value', 'number')
    def _sub_total(self):
        """ Calculates Sub total"""
        self.subtotal = self.coin_value * self.number

    coin_value = fields.Float(
        string='Valor Moneda', required=True, readonly=True)
    number = fields.Integer(string='Cantidad')
    subtotal = fields.Float(compute='_sub_total', string='Subtotal', digits=0, readonly=True)
    cashbox_id = fields.Many2one('account.cashbox', string="Cashbox")
