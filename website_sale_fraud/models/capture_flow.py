# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.tools.safe_eval import safe_eval

class CaptureFlow(models.Model):
    _name = "capture.flow"
    _description = "Capture Flow"

    name = fields.Char(string="Name", required=True)
    expression = fields.Text(
        string="Expression",
        default="# object.amount_total>1000\n# len(object.order_line)>1\n"
                "# object.partner_id.country_id.code=='US'\n# return True/False\n",)
    sequence = fields.Integer(string="Sequence", default=10)
    yes_id = fields.Many2one('capture.flow', string="Yes Flow")
    no_id = fields.Many2one('capture.flow', string="No Flow")
    action = fields.Selection([
        ('decision', 'Decision'),
        ('capture', 'Capture'),
        ('review', 'Review'),
    ], string="Action", required=True, default='capture')

    @api.model
    def evaluate(self):
        return tools


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        self.check_fraud()
        return res

    authorized_transaction_ids = fields.Many2many(store=True)
    fraud_detection = fields.Boolean(string="Fraud Detection", default=False, help="Technical field", copy=False)

    def check_fraud(self):
        for so in self:
            if so.fraud_detection:
                continue
            start_rule = self.env['capture.flow'].search([], order='sequence', limit=1)
            so._check_fraude(start_rule)
            so.fraud_detection = True

    def _check_fraude(self, flow):
        print("action_confirm 4")
        if flow.action == 'capture':
            self.payment_action_capture()
        elif flow.action == 'review':
            self.message_post(
                body="Requires Approval for Fraud Detection #general",
            )
        else:
            if safe_eval(flow.expression, {'object': self}):
                self._check_fraude(flow.yes_id)
            else:
                self._check_fraude(flow.no_id)
