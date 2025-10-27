# -*- coding: utf-8 -*-
# Copyright 2025 ERPGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

from odoo import api, fields, models, tools, _

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    capture_manually = fields.Boolean(
        string="Capture Amount Manually",
        help="Capture the amount from Odoo, when the delivery is completed.\n"
             "Use this if you want to charge your customers cards only when\n"
             "you are sure you can ship the goods to them.",
        readonly=True, default=True
    )

    disable_capture_manually = fields.Boolean(
        string="Disable Capture Manually",
        help="Used to enable/disable manual capture.",
        default=False
    )

    @api.model
    def enable_capture_manually(self):
        """ Enable "capture_manually" on all the Payment Providers where "disable_capture_manually" Is equal to FALSE """
        providers = self.search([('disable_capture_manually', '=', False)])
        if providers:
            providers.write({'capture_manually': True})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'disable_capture_manually' in vals:
                if vals.get('disable_capture_manually') is True:
                    vals['capture_manually'] = False
                else:
                    vals['capture_manually'] = True
        return super(PaymentProvider, self).create(vals_list)

    def write(self, vals):
        if 'disable_capture_manually' in vals:
            for rec in self:
                if vals.get('disable_capture_manually') is True:
                    rec.capture_manually = False
                else:
                    rec.capture_manually = True
        return super(PaymentProvider, self).write(vals)
