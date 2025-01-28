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

    @api.model
    def enable_capture_manually(self):
        """ Enable "capture_manually" on all the Payment Providers """
        providers = self.search([('capture_manually', '=', False)])
        if providers:
            providers.write({'capture_manually': True})
