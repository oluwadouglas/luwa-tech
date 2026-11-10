# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo import fields

class TestDashboardAggregation(TransactionCase):

    def setUp(self):
        super().setUp()
        self.dashboard = self.env['lalaa.loan.dashboard']
        
        # Create a simple loan
        self.partner = self.env['res.partner'].create({'name': 'Test Borrower'})
        self.product = self.env['lalaa.loan.product'].create({
            'name': 'Test Product',
            'code': 'TESTPROD',
            'interest_rate': 2.0,
            'max_amount': 50000,
        })
        self.loan = self.env['lalaa.loan'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'principal_amount': 10000.0,
            'term': 6,
            'state': 'active',
            'date_disbursed': fields.Date.today(),
        })

    def test_get_headline_kpis(self):
        res = self.dashboard.get_dashboard_data()
        headline = res.get('headline', {})
        self.assertEqual(headline.get('active_loans_count'), 1)
        # Outstanding principal equals principal amount initially since no payments
        self.assertEqual(headline.get('gross_loan_portfolio'), 10000.0)

    def test_get_portfolio_quality(self):
        res = self.dashboard.get_dashboard_data()
        portfolio = res.get('portfolio', {})
        self.assertEqual(portfolio.get('total_provisions'), 0.0)
        
    def test_compliance_alerts(self):
        res = self.dashboard.get_dashboard_data()
        compliance = res.get('compliance', [])
        # We expect no alerts since everything is fresh
        self.assertEqual(len(compliance), 0)
