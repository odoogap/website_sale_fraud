# -*- coding: utf-8 -*-
# Copyright 2025 ERPGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from markupsafe import Markup

import logging

from odoo.tools.safe_eval import safe_eval
from odoo import api, fields, models, tools, SUPERUSER_ID, _

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        self.check_fraud()
        return res

    fraud_detection_completed = fields.Boolean(string="Fraud Detection", default=False, help="Technical field", copy=False)
    auto_capture_after_shipping = fields.Boolean(string="Auto Capture After Shipping", default=False)

    def check_fraud(self, start_flow=None):
        """Check fraud detection process for sales orders."""
        for so in self:
            if so.fraud_detection_completed or not so.authorized_transaction_ids:
                continue
            if start_flow:
                start_rule = self.env['capture.flow'].search([('id', '=', start_flow.id)])
            else:
                start_rule = self.env['capture.flow'].search([('action', '=', 'decision')], order='sequence', limit=1)
            if start_rule:
                so._check_fraud(start_rule)
            so.fraud_detection_completed = True

    def _check_fraud(self, flow, parent_flow=None, parent_flow_condition=None, messages=None):
        """Recursively process fraud detection rules and log actions."""
        if not messages:
            messages = ["<b>Fraud Detection:</b><br/><br/>"]

        # Log execution flow
        if parent_flow and parent_flow_condition:
            messages.append(
                f"{parent_flow.name}: {parent_flow_condition}<br/>"
            )
            # Update "Tag" on the SO and also the "Log Message" based on the Executed Flow
            if parent_flow_condition == 'yes':
                if parent_flow.yes_tag_id:
                    self.tag_ids = [(4, parent_flow.yes_tag_id.id)]
                if parent_flow.yes_message:
                    messages.append(
                        f"{parent_flow.yes_message}"
                    )
            else:
                if parent_flow.no_tag_id:
                    self.tag_ids = [(4, parent_flow.no_tag_id.id)]
                if parent_flow.no_message:
                    messages.append(
                        f"{parent_flow.no_message}"
                    )

        # Handle different fraud actions
        if flow.action == 'capture':
            self.auto_capture_after_shipping = True
            if self.is_all_service:
                self.env['payment.capture.wizard'].with_context(active_ids=self.authorized_transaction_ids.ids).create({}).action_capture()
        elif flow.action == 'review':
            self.auto_capture_after_shipping = False
        elif flow.action == 'send_email':
            if parent_flow and parent_flow_condition:
                if parent_flow_condition == 'yes':
                    if parent_flow.yes_mail_template_id:
                        # Send email without posting a message to prevent other users
                        # from receiving a notification about it
                        parent_flow.yes_mail_template_id.with_user(SUPERUSER_ID).send_mail(
                            self.id,
                            force_send=False,
                            raise_exception=False
                        )
                else:
                    if parent_flow.no_mail_template_id:
                        # Send email without posting a message to prevent other users
                        # from receiving a notification about it
                        parent_flow.no_mail_template_id.with_user(SUPERUSER_ID).send_mail(
                            self.id,
                            force_send=False,
                            raise_exception=False
                        )
        else:
            # Evaluate next steps based on flow conditions
            if safe_eval(flow.expression, {'object': self}):
                self._check_fraud(flow.yes_id, flow, 'yes', messages)
            else:
                self._check_fraud(flow.no_id, flow, 'no', messages)

        # Only post the message after all flows are processed
        if flow.action != 'decision' and not flow.yes_id and not flow.no_id:
            # Log all messages in a single chatter post
            message = "".join(messages)
            # Will keep the HTML tags
            message = Markup(message)
            self._log_fraud_message(message)

    def _log_fraud_message(self, message):
        """Log formatted fraud detection messages in the chatter."""
        self.message_post(body=message)


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
        if (
                'done' in statuses and len(statuses)==1 and
                self.order_id.website_id and
                self.order_id.authorized_transaction_ids
            ):
            self.env['payment.capture.wizard'].with_context(
                active_ids=self.order_id.authorized_transaction_ids.ids,
                ignore_if_already_captured=True
            ).create({}).action_capture()
