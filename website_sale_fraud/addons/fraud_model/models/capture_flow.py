from odoo import api, fields, models


class CaptureFlow(models.Model):
    _name = 'capture.flow'
    _description = 'Capture Flow'

    order_id = fields.Many2one('sale.order', string='Order Number', required=True)
    customer_name = fields.Char(string='Customer Name')
    order_date = fields.Datetime(string='Order Date')
    order_amount = fields.Float(string='Order Amount')
    website_name = fields.Char(string='Website Name')
    sequence = fields.Integer(string='Sequence', default=10)
    expression = fields.Text(string='Expression')
    yes_action = fields.Selection(
        [('capture', 'Capture'),
         ('review', 'For Review')],
        string='Yes Action',
        default='capture')
    no_action = fields.Selection(
        [('capture', 'Capture'),
         ('review', 'For Review')],
        string='No Action',
        default='review')
    action = fields.Selection(
        [('capture', 'Captured'),
         ('for_review', 'For Review')],
        string='Action')

    _is_auto_check_running = False

    @api.model
    def auto_check_and_capture(self):
        if not self._is_auto_check_running:
            self.__class__._is_auto_check_running = True
            try:
                existing_orders = self.search([]).mapped('order_id')
                orders_to_add = self.env['sale.order'].search([
                    ('id', 'not in', existing_orders.ids),
                    ('state', '!=', 'cancel')
                ])

                for order in orders_to_add:
                    expression = self._build_expression(order)
                    order_amount = order.amount_total
                    previous_order_captured = self._check_previous_order_captured(order)

                    action = 'capture' if (
                        eval(expression, {'order_amount': order_amount,
                                          'previous_order_captured': previous_order_captured})) \
                        else 'for_review'

                    self.create({
                        'order_id': order.id,
                        'customer_name': order.partner_id.name,
                        'order_date': order.date_order,
                        'order_amount': order.amount_total,
                        'website_name': order.website_id.name,
                        'expression': expression,
                        'action': action,
                    })
            finally:
                self.__class__._is_auto_check_running = False

    @api.model
    def _build_expression(self, order):
        if order.amount_total < 1000:
            return "order_amount < 1000"
        else:
            previous_orders = self.env['sale.order'].search([
                ('partner_id', '=', order.partner_id.id),
                ('id', '!=', order.id),
                ('state', '!=', 'cancel')
            ])
            if previous_orders:
                for prev_order in previous_orders:
                    capture_flow_record = self.search([('order_id', '=', prev_order.id)])
                    if capture_flow_record and capture_flow_record.action == 'capture':
                        return "order_amount >= 1000 and previous_order_captured"
            return "order_amount >= 1000 and previous_order_captured"

    @api.model
    def _check_previous_order_captured(self, order):
        previous_orders = self.env['sale.order'].search([
            ('partner_id', '=', order.partner_id.id),
            ('id', '!=', order.id),
            ('state', '!=', 'cancel')
        ])
        if previous_orders:
            for prev_order in previous_orders:
                capture_flow_record = self.search([('order_id', '=', prev_order.id)])
                if capture_flow_record and capture_flow_record.action == 'capture':
                    return True
        return False

    @api.model
    def create(self, vals):
        res = super(CaptureFlow, self).create(vals)
        self.auto_check_and_capture()
        return res

    def write(self, vals):
        res = super(CaptureFlow, self).write(vals)
        self.auto_check_and_capture()
        return res

    def unlink(self):
        res = super(CaptureFlow, self).unlink()
        self.auto_check_and_capture()
        return res

    def evaluate_expression(self, order_amount, previous_order_captured):
        return eval(self.expression, {'order_amount': order_amount, 'previous_order_captured': previous_order_captured})


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        self.env['capture.flow'].auto_check_and_capture()
        return res
