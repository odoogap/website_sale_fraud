# -*- coding: utf-8 -*-
# Copyright 2025 ERPGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestFraudGiftCard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'GC Buyer', 'email': 'gc.buyer@example.com'})
        cls.product = cls.env['product.product'].create({
            'name': 'GC Test Product',
            'detailed_type': 'consu',
            'list_price': 50.0,
            'taxes_id': [Command.clear()],
        })
        cls.program = cls.env['loyalty.program'].create({
            'name': 'GC Test Program',
            'program_type': 'gift_card',
            'company_id': cls.env.company.id,
        })
        cls.program._compute_from_program_type()  # rules/rewards are only set by onchange
        cls.review_tag = cls.env['crm.tag'].create({'name': 'GC Fraud Review'})
        review = cls.env['capture.flow'].create({'name': 'GC Review', 'action': 'review'})
        cls.capture = cls.env['capture.flow'].create({'name': 'GC Capture', 'action': 'capture'})
        cls.start_rule = cls.env['capture.flow'].create({
            'name': 'GC Decision',
            'action': 'decision',
            'expression': 'object._is_paid_by_gift_card_only()',
            'yes_id': review.id,
            'yes_tag_id': cls.review_tag.id,
            'no_id': cls.capture.id,
        })

    def _create_order(self, price=50.0):
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': price,
                'tax_id': [Command.clear()],
            })],
        })

    def _pay_with_gift_card(self, order, points):
        card = self.env['loyalty.card'].with_context(loyalty_no_mail=True).create({
            'program_id': self.program.id,
            'points': points,
        })
        status = order._try_apply_code(card.code)
        self.assertNotIn('error', status)
        order._update_programs_and_rewards()
        order._auto_apply_rewards()
        return card

    def _fraud_logged(self, order):
        return any('Fraud Detection' in (m.body or '') for m in order.message_ids)

    def test_fully_gift_card_paid_order_is_checked(self):
        order = self._create_order()
        self._pay_with_gift_card(order, 100)
        self.assertFalse(order.amount_total)
        self.assertFalse(order.authorized_transaction_ids)

        order.check_fraud(start_flow=self.start_rule)

        self.assertTrue(order.fraud_detection_completed)
        self.assertIn(self.review_tag, order.tag_ids)
        self.assertTrue(self._fraud_logged(order))

    def test_partially_gift_card_paid_order_without_payment_is_skipped(self):
        order = self._create_order()
        self._pay_with_gift_card(order, 20)
        self.assertTrue(order.amount_total)

        order.check_fraud(start_flow=self.start_rule)

        self.assertFalse(order.fraud_detection_completed)
        self.assertFalse(self._fraud_logged(order))

    def test_zero_total_order_without_gift_card_is_skipped(self):
        order = self._create_order(price=0.0)

        order.check_fraud(start_flow=self.start_rule)

        self.assertFalse(order.fraud_detection_completed)
        self.assertFalse(self._fraud_logged(order))

    def test_service_only_gift_card_paid_order_reaching_capture(self):
        """A digital order paid by gift card has no transaction for the Capture rule to capture."""
        self.product.detailed_type = 'service'
        order = self._create_order()
        self._pay_with_gift_card(order, 100)
        self.assertTrue(order.is_all_service)
        trusted_rule = self.env['capture.flow'].create({
            'name': 'GC Trusted',
            'action': 'decision',
            'expression': 'True',
            'yes_id': self.capture.id,
            'no_id': self.capture.id,
        })

        order.check_fraud(start_flow=trusted_rule)

        self.assertTrue(order.fraud_detection_completed)
        self.assertTrue(order.auto_capture_after_shipping)
        self.assertTrue(self._fraud_logged(order))
