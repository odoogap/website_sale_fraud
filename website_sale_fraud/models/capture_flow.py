# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _


class CaptureFlow(models.Model):
    _name = "capture.flow"
    _description = "Capture Flow"

    name = fields.Char(string="Name", required=True)
    expression = fields.Text(string="Expression")
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

    fraud_detection = fields.Boolean(string="Fraud Detection", default=True, help="Technical field")

    def check_fraud(self):
        for so in self:
            if so.fraud_detection:
                continue
            # Find the first flow
            flow = self.env['capture.flow'].search([], order='sequence', limit=1).evaluate()
            if flow == 'capture':
                so.payment_action_capture()
            else:
                pass
            so.fraud_detection = True
