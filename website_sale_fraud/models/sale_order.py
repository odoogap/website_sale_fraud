# -*- coding: utf-8 -*-
# Copyright 2025 ERPGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        self.check_fraud()
        return res

    fraud_detection_completed = fields.Boolean(string="Fraud Detection", default=False, help="Technical field", copy=False)
    auto_capture_after_shipping = fields.Boolean(string="Auto Capture After Shipping", default=False)

    def check_fraud(self):
        for so in self:
            if so.fraud_detection_completed:
                continue
            start_rule = self.env['capture.flow'].search([('action', '=', 'decision')], order='sequence', limit=1)
            if start_rule:
                so._check_fraude(start_rule, parent_flow=None)
            so.fraud_detection_completed = True

    def _check_fraude(self, flow, parent_flow):
        if flow.action == 'capture':
            self.auto_capture_after_shipping = True
            self.message_post(
                body="Fraud Detection: Auto capture after shipping",
            )
        elif flow.action == 'review':
            self.message_post(
                body="Fraud Detection: Requires Approval for Fraud Detection",
            )
        elif flow.action == 'send_email':
            if parent_flow and parent_flow.mail_template_id:
                self.with_user(SUPERUSER_ID).with_context(force_send=True).message_post_with_source(
                    parent_flow.mail_template_id,
                    email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature',
                    subtype_xmlid='mail.mt_comment',
                )
            self.message_post(
                body="Fraud Detection: The Email will be send to the client",
            )
        else:
            if safe_eval(flow.expression, {'object': self}):
                self._check_fraude(flow.yes_id, flow)
            else:
                self._check_fraude(flow.no_id, flow)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('move_ids.state', 'move_ids.scrapped', 'move_ids.quantity', 'move_ids.product_uom')
    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()
        statuses = set()
        for line in self:  # TODO: maybe one day, this should be done in SQL for performance sake
            if line.qty_delivered_method == 'stock_move':
                outgoing_moves, incoming_moves = line._get_outgoing_incoming_moves()
                statuses.update(outgoing_moves.mapped('state'))
                statuses.update(incoming_moves.mapped('state'))

        if ('done' in statuses and len(statuses)==1 and
                self.order_id.auto_capture_after_shipping and
                self.order_id.website_id and  self.order_id.authorized_transaction_ids):
            self.env['payment.capture.wizard'].with_context(active_ids=self.order_id.authorized_transaction_ids.ids).create({}).action_capture()
