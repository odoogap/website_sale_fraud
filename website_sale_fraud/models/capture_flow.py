# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _


class CaptureFlow(models.Model):
    _name = "capture.flow"
    _description = "Capture Flow"

    name = fields.Char(string="Name", required=True)
    active = fields.Boolean(string="Active", default=True)
    expression = fields.Text(
        string="Expression",
        default="# object.amount_total>1000\n# len(object.order_line)>1\n"
                "# object.partner_id.country_id.code=='US'\n# return True/False\n",)
    sequence = fields.Integer(string="Sequence", default=10)
    yes_id = fields.Many2one('capture.flow', string="Yes Flow", domain=["|", ["active", "=", True], ["active", "=", False]])
    no_id = fields.Many2one('capture.flow', string="No Flow", domain=["|", ["active", "=", True], ["active", "=", False]])
    action = fields.Selection([
        ('decision', 'Decision'),
        ('capture', 'Capture'),
        ('review', 'Review'),
    ], string="Action", required=True, default='decision')

    @api.model
    def evaluate(self):
        return tools
