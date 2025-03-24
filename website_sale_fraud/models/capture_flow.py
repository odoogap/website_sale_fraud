# -*- coding: utf-8 -*-
# Copyright 2025 ERPGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CaptureFlow(models.Model):
    _name = "capture.flow"
    _description = "Capture Flow"
    _order = 'sequence, id'

    name = fields.Char(string="Name", required=True)
    active = fields.Boolean(string="Active", default=True)
    expression = fields.Text(
        string="Expression",
        default="# object.amount_total>1000\n# len(object.order_line)>1\n"
                "# object.partner_id.country_id.code=='US'\n# return True/False\n")
    sequence = fields.Integer(string="Sequence", default=0, index=True, required=True)
    # Yes Flow
    yes_id = fields.Many2one('capture.flow', string="Yes Flow", domain=['|', ('action', '!=', 'decision'), ('active', '=', True)])
    yes_mail_template_id = fields.Many2one('mail.template', string="Yes - Email Template", domain=[('model', '=', 'sale.order')])
    yes_show_mail_template = fields.Boolean(string="Yes - Show Mail Template", compute='_compute_show_mail_template')
    yes_tag_id = fields.Many2one('crm.tag', string="Yes - Tag")
    yes_message = fields.Html(string="Yes - Log Message")
    # No Flow
    no_id = fields.Many2one('capture.flow', string="No Flow", domain=['|', ('action', '!=', 'decision'), ('active', '=', True)])
    no_mail_template_id = fields.Many2one('mail.template', string="No - Email Template", domain=[('model', '=', 'sale.order')])
    no_show_mail_template = fields.Boolean(string="No - Show Mail Template", compute='_compute_show_mail_template')
    no_tag_id = fields.Many2one('crm.tag', string="No - Tag")
    no_message = fields.Html(string="No - Log Message")

    action = fields.Selection([
        ('decision', 'Decision'),
        ('capture', 'Capture'),
        ('review', 'Review'),
        ('send_email', 'Send Email')
    ], string="Action", required=True, default='decision')

    @api.constrains('yes_id', 'no_id')
    def _check_yes_id_no_id_recursion(self):
        for rec in self:
            if (rec.id and (rec.yes_id or rec.no_id)) and (rec.yes_id.id == rec.id or rec.no_id.id == rec.id):
                raise ValidationError(_("Error ! You cannot create recursive 'Capture Flows'."))

    @api.depends('yes_id', 'no_id')
    def _compute_show_mail_template(self):
        for rec in self:
            yes_show_mail_template = False
            no_show_mail_template = False
            if rec.action == 'decision':
                if rec.yes_id and rec.yes_id.action == 'send_email':
                    yes_show_mail_template = True
                if rec.no_id and rec.no_id.action == 'send_email':
                    no_show_mail_template = True
            rec.write({
                'yes_show_mail_template': yes_show_mail_template,
                'no_show_mail_template': no_show_mail_template
            })

    @api.model
    def evaluate(self):
        return tools

    @api.model_create_multi
    def create(self, values_list):
        # Retrieve the highest existing sequence number
        last_sequence = self.search([('active', 'in', (True, False))], order="sequence desc", limit=1).sequence or 0
        for values in values_list:
            # Increment the sequence only if it is not already provided
            if 'sequence' not in values or values['sequence'] == 0:
                last_sequence += 1
                values['sequence'] = last_sequence
        # Create records with updated sequence values
        return super(CaptureFlow, self).create(values_list)
    
    
    def copy_data(self, default=None):
        default = dict(default or {})
        last_sequence = self.search([('active', 'in', (True, False))], order="sequence desc", limit=1).sequence or 0
        last_sequence += 1
        vals_list = super().copy_data(default=default)
        for flow, vals in zip(self, vals_list):
            if 'name' not in default:
                vals['name'] = _("%s (copy)", flow.name)
            vals['sequence'] = last_sequence
        return vals_list
