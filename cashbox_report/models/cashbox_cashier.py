from datetime import date, datetime as dt
from operator import itemgetter
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, RedirectWarning
from odoo.addons import decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


class CashboxCoin(models.Model):
    """ Cash Box Details """
    _name = 'cashbox.coin'
    _order = 'coin_value'

    #@api.one
    #@api.depends('coin_value', 'number')
    def _sub_total(self):
        """ Calculate Sub total"""
        #self.ensure_one()
        #self.subtotal = self.coin_value * self.number
        for rec in self:
            rec.subtotal = rec.coin_value * rec.number

    coin_value = fields.Float(
        string='Valor Moneda', readonly=True)
    number = fields.Integer(string='Cantidad')
    subtotal = fields.Float(compute='_sub_total', string='Subtotal',
                            digits=dp.get_precision('Product Price'), readonly=True)
    cashbox_cashier_id = fields.Many2one('cashbox.cashier', string="Cashbox")
    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.user.company_id,
        required=True)


class CashboxCashier(models.Model):
    _name = 'cashbox.cashier'
    _order = 'date'

    
    def _set_cashbox_line_values(self):
        coin_values = [1, 5, 10, 25, 50, 100, 200, 500, 1000, 2000]
        for record in self.cashbox_lines_ids.search([]):
            record.unlink()

        for coin in coin_values:
            self.env['cashbox.coin'].create({'coin_value': coin, 'number': 0})
        line_ids = self.cashbox_lines_ids.search([])
        return line_ids

    name = fields.Char(
        string="Referencia",
        required=True,
        readonly=True,
        copy=False,
        default=_('Nuevo'),
    )
    date = fields.Date(string="Fecha", default=fields.Date.context_today)
   
    cashbox_lines_ids = fields.One2many(
        comodel_name='cashbox.coin',
        inverse_name="cashbox_cashier_id",
        string='Desglose de efectivo',
        default=_set_cashbox_line_values,
        copy=False,
    )

    bank_amount = fields.Float(
        string="Total Banco",
        digits=dp.get_precision('Product Price'),
        copy=False,
    )
    cash_amount = fields.Float(
        string="Total Efectivo",
        digits=dp.get_precision('Product Price'),
        copy=False,
    )

    check_amount = fields.Float(
        string="Total Cheque",
        digits=dp.get_precision('Product Price'),
        copy=False,
    )
    credit_card_amount = fields.Float(
        string="Total Tarjeta",
        digits=dp.get_precision('Product Price'),
        copy=False,
    )

    transfer_amount = fields.Float(
        string="Total Transferencias",
        digits=dp.get_precision('Product Price'),
        copy=False,
    )
    
    cashbox_id = fields.Many2one(
        comodel_name="account.cashbox",
        string="Cierre",
        copy=False,
    )
    note = fields.Text(string="Observaciones", copy=False, )
    company_id = fields.Many2one(
        'res.company',
        string='Compañia',
        default=lambda self: self.env.user.company_id,
        required=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Usuario ID',
        #default=lambda self: self.env.user,
        #required=True,
    )
    state = fields.Selection(
        string="Estado",
        selection=[
            ('draft', 'Borrador'),
            ('confirmed', 'Confirmado'),
            ('accepted', 'Aceptado'),
            ('denied', 'Rechazado'),
            ('cancel', 'Cancelado'),
        ],
        required=False,
        default='draft',
        copy=False,
    )

    @api.model
    def create(self, values):
        if not values.get('name', False) or values['name'] == _('New'):
            values['name'] = self.env['ir.sequence'].next_by_code(
                'cashbox.cashier') or _('New')
        return super(CashboxCashier, self).create(values)

    #@api.multi
    def action_confirmed(self):
        self.write({'state': 'confirmed'})

    #@api.multi
    def action_accepted(self):
        self.write({'state': 'accepted'})

    #@api.multi
    def action_denied(self):
        self.write({'state': 'denied'})

    #@api.multi
    def action_cancel(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError("No puede cancelar un registro sino "
                                      "esta borrador.")
        self.write({'state': 'cancel'})

    #@api.multi
    def action_to_draft(self):
        self.write({'state': 'draft'})

    #@api.multi
    def _get_journal_ids(self, type='sale'):
        journal_domain = [('company_id', '=', self.env.user.company_id.id)]

        if type == 'all':
            journal_domain.append(('type', 'in', ['sale', 'cash', 'bank']))
        else:
            journal_domain.append(('type', '=', 'sale'))
            #journal_domain.append(('ncf_control', '=', True))

        journal_ids = self.env['account.journal'].search(journal_domain)
        return journal_ids

    def _check_cash_invoice(self, invoice):
        if invoice.invoice_date == self.date and (invoice.payment_state == 'paid' or invoice.payment_state == 'in_payment'):
           return True
        
        if invoice.invoice_date == self.date and invoice.payment_state != 'paid':
            return False

        if not invoice.invoice_payment_term_id or invoice.invoice_payment_term_id.id != 1:
            return False
        
        return True

    @api.onchange('user_id')
    def _sum_values(self):
        pass
        #self.bank_amount =  99999
        #self.check_amount = 8999
        #self.credit_card_amount = 77777
        #msg = "ON CHANGE"
            # action = self.env.ref('cashbox_report.action_cashbox_cashier')
            # action['domain'] = [('id', 'in', report_exists.ids)]
        #raise ValidationError(msg)

    #@api.multi
    def _prepare_payment_info(self):
        self.bank_amount = 0
        self.check_amount = 0
        self.credit_card_amount = 0
        self.cash_amount = 0
        self.transfer_amount = 0
        
        payment_methods = {}
        payment_obj = self.env['account.payment']
        payment_ids, other_payment_details = [], []

        domain = [('date', '=', self.date),
                  ('payment_type', '=', 'inbound'),
                  ('company_id', '=', self.env.user.company_id.id),
                  ('state', 'in',['posted','reconciled'])]
        
        for rec in payment_obj.search(domain):
            journal_name = rec.journal_id.name           
            if rec.journal_id.close_type =='bank':
                self.bank_amount += rec.amount
            elif rec.journal_id.close_type =='check':
                self.check_amount += rec.amount
            elif rec.journal_id.close_type =='card':
                self.credit_card_amount += rec.amount
            elif rec.journal_id.close_type =='cash':
                self.cash_amount += rec.amount
            elif rec.journal_id.close_type =='transfer':
                self.transfer_amount += rec.amount

            amount = 0.0
            if rec.reconciled_invoice_ids:
                #invoices_a = rec.invoice_ids.filtered(
                #    lambda invoice: invoice.journal_id.ncf_control == True)
                #if invoices_a:
                #    amount = rec.amount

                invoices = rec.reconciled_invoice_ids.filtered(
                    lambda invoice: invoice.invoice_date != self.date)
                for inv in invoices:
                    if inv.move_type == 'out_refund':
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
            p_date = date.strftime(pdate, '%Y-%m-%d')
            print(p_date)
            other_payment_details.append({
                'Fecha': "{}/{}/{}".format(p_date[8:10], p_date[5:7], p_date[:4]),
                'Referencia': p.name,
                'Cliente': p.partner_id.name,
                'Monto': p.amount,
                'Metodo de pago': p.journal_id.name,
            })

        return (payment_methods, other_payment_details)

    #@api.multi
    def _prepare_invoice_detail(self, journals):
        payment_obj = self.env['account.payment']
        invoice_details, invoice_headers, credit_notes_issued = {}, [], 0.0
        credit_notes_applied, balance_favor, advance = 0.0, 0.0, 0.0

        for journal in journals:
            journal_name = journal.name
            domain = [
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('invoice_date', '=', self.date),
                ('payment_state', 'in', ['not_paid', 'paid','in_payment']),
                ('company_id', '=', self.env.user.company_id.id),
                ('user_id', '=', self.user_id.id),
                ('journal_id', '=', journal.id)]

            for inv in self.env['account.move'].search(
                domain, order="name asc"):

                payments = inv._get_reconciled_info_JSON_values() # _get_payments_vals()
                cash_invoice = self._check_cash_invoice(inv)

                values = {
                    'id': inv.id,
                    'number': inv.name,
                    'partner': inv.partner_id.name,
                    'Credito': 0.0,
                    'Contado': 0.0,
                    'NC Emitidas': 0.0,
                }
                if inv.move_type == 'out_invoice':
                    if cash_invoice:
                        values['Contado'] = inv.amount_total
                    else:
                        values['Credito'] = inv.amount_total

                if inv.move_type == 'out_refund' and inv.payment_state in ['not_paid', 'paid','in_payment']:
                    if not values['number']:
                        values['number'] = inv.name
                    values['NC Emitidas'] = inv.amount_total
                    credit_notes_issued += inv.amount_total

                if inv.move_type != 'out_refund':
                    for rec in payments:
                        payment_date = rec.get('date')
                        if payment_date > self.date:
                            continue

                        minor_date = True if payment_date < self.date else False
                        header = rec.get('journal_name')

                        amount = rec.get('amount')
                        is_credit_note = True if rec.get('ref')[
                                                 :3] == 'B04' else False
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
        invoice_obj = self.env['account.move']
        journals = self._get_journal_ids()

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '=', self.date),
            ('payment_state', 'in', ['not_paid', 'paid','in_payment']),
            ('company_id', '=', self.env.user.company_id.id),
            ('user_id', '=', self.user_id.id),
            ('journal_id', 'in', journals.ids)]
        for inv in invoice_obj.search(domain):
            journal = inv.journal_id.name
            record = data['info']
            cash, credit,  = 0.0, 0.0
            cash_invoice = self._check_cash_invoice(inv)

            if inv.move_type == 'out_invoice':
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

            if inv.move_type == 'out_invoice' and inv.payment_state == 'not_paid' \
                    and inv.invoice_payment_term_id.id == 1:
                cash_invoice_open.append({
                    'number': inv.name,
                    'partner': inv.partner_id.name,
                    'date': inv.invoice_date,
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
        report_name = 'cashbox_report.action_report_cashbox_cashier'
        return self.env.ref(report_name).report_action(self, data=data)

    # @api.multi
    # def create_cashbox_log(self):
    #     Cashbox = self.env['account.cashbox']
    #     name = "Reporte generado por {} en fecha {}".format(
    #         self.user_id.name, self.date)
    #
    #     #Prevent duplicate reports
    #     last_today_reports = [
    #         ('date', '=', self.date),
    #         ('cashier', '=', self.user_id.id)]
    #     for rec in Cashbox.search(last_today_reports):
    #         rec.sudo().unlink()
    #
    #     values = {
    #         'name': name,
    #         'date': self.date,
    #         'cashier': self.user_id.id,
    #         'bank_amount': self.bank_amount,
    #         'check_amount': self.check_amount,
    #         'credit_card_amount': self.credit_card_amount,
    #         'note': self.note,
    #         'company_id': self.env.user.company_id.id,
    #     }
    #     cashbox_id = Cashbox.create(values)
    #
    #     cashbox_coins = []
    #     cash_amount = 0.0
    #     for line in self.cashbox_lines_ids.search([]):
    #         cash_amount += line.coin_value * line.number
    #         cashbox_coins.append((0, 0, {
    #             'coin_value': line.coin_value,
    #             'number': line.number,
    #             'cashbox_id': cashbox_id.id,
    #         }))
    #
    #     cashbox_id.write({'cash_amount': cash_amount})
    #     self.cashbox_id = cashbox_id.id
    #     cashbox_id.write({'cashbox_coin_ids': cashbox_coins})
    #     return cashbox_id.ids

    #@api.multi
    def check_report(self):
        self.ensure_one()
        # Before prepare report, check is user have been
        # created a report for this date.
        report_exists = self.search([
            ('id', '!=', self.id),
            ('create_uid', '=', self.user_id.id),
            ('date', '=', self.date),
        ])
        if report_exists:
            msg = "Usted ya ha creado un reporte el día de hoy " \
                  "por favor revise el reporte ya creado. \nReferencia: %s" % \
                  report_exists.name
            # action = self.env.ref('cashbox_report.action_cashbox_cashier')
            # action['domain'] = [('id', 'in', report_exists.ids)]
            raise ValidationError(msg)

        result = self.prepare_data()
        # self.create_cashbox_log()

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
