# -*- coding: utf-8 -*-
# Copyright 2025 ERPGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase
from unittest.mock import patch, MagicMock


class TestFraudDetection(TransactionCase):
    """Unit tests for fraud detection flows in sale orders."""

    def setUp(self):
        """Set up test data before each test case."""
        super().setUp()

        # References to predefined fraud capture flows
        self.flow_capture = self.env.ref('website_sale_fraud.capture_flow_capture_payment')
        self.flow_review = self.env.ref('website_sale_fraud.capture_flow_ask_for_review')
        self.flow_send_email = self.env.ref('website_sale_fraud.capture_flow_send_email')

        # Payment-related setup
        self.payment_method = self.env.ref('payment.payment_method_unknown')
        self.provider = self.env.ref('payment.payment_provider_demo')

        # Create a test partner
        self.partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'email': 'test@example.com'
        })

        # Create a test product
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 9
        })

        # Create a test sale order line
        self.order_line = [[0, 0, {
            'name': 'Test Order Line',
            'product_id': self.product.id,
            'product_uom_qty': 1,
        }]]

        # Create a test sale order
        self.sale_order = self.env['sale.order'].create({
            'name': 'Test SO With Price 9',
            'partner_id': self.partner.id,
            'order_line': self.order_line
        })

        # Create a test payment transaction linked to the sale order
        self.payment_transaction = self.env['payment.transaction'].create({
            'provider_id': self.provider.id,
            'payment_method_id': self.payment_method.id,
            'partner_id': self.sale_order.partner_id.id,
            'reference': self.sale_order.name,
            'amount': self.sale_order.amount_total,
            'state': 'authorized',
            'currency_id': self.env.ref('base.EUR').id,
            'sale_order_ids': [(4, self.sale_order.id)]
        })

        # Define test flows with different fraud detection conditions
        self.test_flow_capture_yes = self.env['capture.flow'].create({
            'name': 'Test Flow - Capture Payment - Yes',
            'action': 'decision',
            'expression': 'object.amount_total>10',
            'yes_id': self.flow_capture.id,
            'no_id': self.flow_review.id
        })

        self.test_flow_capture_no = self.env['capture.flow'].create({
            'name': 'Test Flow - Capture Payment - No',
            'action': 'decision',
            'expression': 'object.amount_total>11',
            'yes_id': self.flow_capture.id,
            'no_id': self.flow_review.id
        })

        self.test_flow_send_email = self.env['capture.flow'].create({
            'name': 'Test Flow - Send Email',
            'action': 'decision',
            'expression': 'object.amount_total>10',
            'yes_id': self.flow_send_email.id,
            'no_id': self.flow_review.id,
            'mail_template_id': self.env.ref('sale.mail_template_sale_confirmation').id
        })

        # Define a chain of seven sequential capture flows for testing multiple conditions
        self.test_flow_7 = self.env['capture.flow'].create({
            'name': 'Test Flow 7',
            'action': 'decision',
            'expression': 'len(object.order_line)>=1',
            'yes_id': self.flow_capture.id,
            'no_id': self.flow_review.id
        })
        self.test_flow_6 = self.env['capture.flow'].create({
            'name': 'Test Flow 6',
            'action': 'decision',
            'expression': 'len(object.order_line)>=1',
            'yes_id': self.test_flow_7.id,
            'no_id': self.flow_review.id
        })
        self.test_flow_5 = self.env['capture.flow'].create({
            'name': 'Test Flow 5',
            'action': 'decision',
            'expression': 'len(object.order_line)>=1',
            'yes_id': self.test_flow_6.id,
            'no_id': self.flow_review.id
        })
        self.test_flow_4 = self.env['capture.flow'].create({
            'name': 'Test Flow 4',
            'action': 'decision',
            'expression': 'len(object.order_line)>=1',
            'yes_id': self.test_flow_5.id,
            'no_id': self.flow_review.id
        })
        self.test_flow_3 = self.env['capture.flow'].create({
            'name': 'Test Flow 3',
            'action': 'decision',
            'expression': 'len(object.order_line)>=1',
            'yes_id': self.test_flow_4.id,
            'no_id': self.flow_review.id
        })
        self.test_flow_2 = self.env['capture.flow'].create({
            'name': 'Test Flow 2',
            'action': 'decision',
            'expression': 'len(object.order_line)>=1',
            'yes_id': self.test_flow_3.id,
            'no_id': self.flow_review.id
        })
        self.test_flow_1 = self.env['capture.flow'].create({
            'name': 'Test Flow 1',
            'action': 'decision',
            'expression': 'len(object.order_line)>=1',
            'yes_id': self.test_flow_2.id,
            'no_id': self.flow_review.id
        })

    @patch('odoo.addons.sale.models.sale_order.SaleOrder.message_post')
    def test_flow_capture_yes_condition(self, mock_message_post):
        """Test the 'test_flow_capture_yes' to verify that the 'yes' condition triggers the expected action."""

        # Execute fraud check on the sale order with the defined test flow
        self.sale_order.check_fraud(self.test_flow_capture_yes)

        # Verify that the fraud check triggered a message post
        mock_message_post.assert_called_once()

        # Ensure that the correct message was logged
        args, kwargs = mock_message_post.call_args
        assert "🔄 Auto-capture will be processed after shipping" in kwargs['body']

    @patch('odoo.addons.sale.models.sale_order.SaleOrder.message_post')
    def test_flow_capture_no_condition(self, mock_message_post):
        """Test the 'test_flow_capture_no' to verify that the 'no' condition triggers the expected action."""

        # Execute fraud check on the sale order with the defined test flow
        self.sale_order.check_fraud(self.test_flow_capture_no)

        # Verify that the fraud check triggered a message post
        mock_message_post.assert_called_once()

        # Ensure that the correct message was logged
        args, kwargs = mock_message_post.call_args
        assert "⚠️ Transaction requires manual review and approval." in kwargs['body']

    def test_flow_email_condition(self):
        """Tests if an email is created and correctly linked to the sale order when the fraud check triggers an email flow."""

        # Execute fraud check that should trigger an email sending flow
        self.sale_order.check_fraud(self.test_flow_send_email)

        # Search for the notification, on the mail.message, linked to the sale order
        notification = self.env['mail.message'].search([
            ('res_id', '=', self.sale_order.id),
            ('model', '=', 'sale.order'),
            ('subtype_id', '=', self.env.ref('mail.mt_note').id)
        ], limit=1)

        self.assertIn("📧 An email notification will be sent to the client.", notification.body)

        # Assert that the notification was created
        self.assertTrue(notification, f"No Message was found linked to sale.order with ID {self.sale_order.id}")

        # Assert that the notification is correctly linked to the sale order
        self.assertEqual(notification.res_id, self.sale_order.id, "Notification res_id does not match the sale order ID")
        self.assertEqual(notification.model, 'sale.order', "notification model is not 'sale.order'")

    @patch('odoo.addons.sale.models.sale_order.SaleOrder.message_post')
    def test_flow_cycle_ends_in_yes(self, mock_message_post):
        """Tests whether the sales order correctly goes through the flow cycle and ends in the 'yes' condition of test_flow_1."""

        # Execute fraud check on the sale order with the defined test flow
        self.sale_order.check_fraud(self.test_flow_1)

        # Verify that the fraud check triggered a message post
        mock_message_post.assert_called_once()

        # Ensure that the correct message was logged
        args, kwargs = mock_message_post.call_args
        assert "🔄 Auto-capture will be processed after shipping" in kwargs['body']
