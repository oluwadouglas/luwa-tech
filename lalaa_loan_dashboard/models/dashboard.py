# -*- coding: utf-8 -*-
from odoo import models, api, fields
from datetime import timedelta

class LalaaLoanDashboard(models.AbstractModel):
    _name = 'lalaa.loan.dashboard'
    _description = 'Loan Dashboard Backend Service'

    @api.model
    def get_dashboard_data(self, filters=None):
        """
        Main entry point for the OWL dashboard.
        Calculates all required KPIs in one RPC call.
        """
        filters = filters or {}
        
        return {
            'headline': self._get_headline_kpis(filters),
            'portfolio': self._get_portfolio_quality(filters),
            'collections': self._get_collections(filters),
            'profitability': self._get_profitability(filters),
            'liquidity': self._get_liquidity(filters),
            'risk': self._get_risk_concentration(filters),
            'pipeline': self._get_pipeline(filters),
            'compliance': self._get_compliance_alerts(filters),
            'top_borrowers': self._get_top_borrowers(filters),
        }

    def _get_headline_kpis(self, filters):
        # Gross Loan Portfolio = sum of all outstanding principal
        loans = self.env['lalaa.loan'].search([('state', '=', 'active')])
        glp = sum(loans.mapped('outstanding_principal'))
        
        # Total Active Loans
        active_count = len(loans)
        
        # Disbursed YTD
        this_year_start = fields.Date.today().replace(month=1, day=1)
        ytd_loans = self.env['lalaa.loan'].search([
            ('state', 'in', ['active', 'default', 'closed']),
            ('date_disbursed', '>=', this_year_start)
        ])
        disbursed_ytd = sum(ytd_loans.mapped('principal_amount'))
        
        # Month Target Achievement
        this_month_start = fields.Date.today().replace(day=1)
        mtd_loans = self.env['lalaa.loan'].search([
            ('state', 'in', ['active', 'default', 'closed']),
            ('date_disbursed', '>=', this_month_start)
        ])
        disbursed_mtd = sum(mtd_loans.mapped('principal_amount'))
        target = self.env.company.lalaa_monthly_disbursement_target or 0
        target_achievement = (disbursed_mtd / target) * 100 if target > 0 else 0.0

        return {
            'gross_loan_portfolio': glp,
            'active_loans_count': active_count,
            'disbursed_ytd': disbursed_ytd,
            'target_achievement': target_achievement,
        }

    def _get_portfolio_quality(self, filters):
        loans = self.env['lalaa.loan'].search([('state', 'in', ['active', 'default'])])
        par_30 = sum(loans.filtered(lambda l: l.days_past_due > 30).mapped('outstanding_principal'))
        par_90 = sum(loans.filtered(lambda l: l.days_past_due > 90).mapped('outstanding_principal'))
        glp = sum(loans.mapped('outstanding_principal')) or 1

        npl_loans = loans.filtered(lambda l: getattr(l, 'days_past_due', 0) > 90)
        npl_amount = sum(npl_loans.mapped('outstanding_principal'))
        total_provisions = sum(loans.mapped('provision_amount'))

        return {
            'par_30_ratio': (par_30 / glp) * 100,
            'par_90_ratio': (par_90 / glp) * 100,
            'npl_ratio': (npl_amount / glp) * 100,
            'provision_coverage': (total_provisions / npl_amount * 100) if npl_amount else 100.0,
            'total_provisions': total_provisions,
        }

    def _get_collections(self, filters):
        # Calculate collection ratio for the current month
        today = fields.Date.today()
        start_date = today.replace(day=1)
        
        schedules = self.env['lalaa.loan.schedule'].search([
            ('date_due', '>=', start_date),
            ('date_due', '<=', today)
        ])
        total_due = sum(schedules.mapped('total_due'))
        total_collected = sum(schedules.mapped('total_paid'))

        collection_ratio = (total_collected / total_due * 100) if total_due else 0

        # Aging brackets
        late_schedules = self.env['lalaa.loan.schedule'].search([
            ('state', 'in', ['pending', 'partial']),
            ('date_due', '<', today)
        ])
        
        aging = {'1_30': 0, '31_60': 0, '61_90': 0, '90_plus': 0}
        for sch in late_schedules:
            days_late = (today - sch.date_due).days
            if days_late <= 30:
                aging['1_30'] += sch.balance
            elif days_late <= 60:
                aging['31_60'] += sch.balance
            elif days_late <= 90:
                aging['61_90'] += sch.balance
            else:
                aging['90_plus'] += sch.balance

        return {
            'collection_ratio': collection_ratio,
            'collection_target': self.env.company.lalaa_collection_target_percent,
            'aging_brackets': aging
        }

    def _get_profitability(self, filters):
        this_year_start = fields.Date.today().replace(month=1, day=1)
        payments = self.env['lalaa.loan.payment'].search([
            ('state', '=', 'posted'),
            ('date', '>=', this_year_start)
        ])
        
        # Interest + Fees + Penalties = Revenue
        interest_income = sum(payments.mapped('interest'))
        fee_income = sum(payments.mapped('fee'))
        penalty_income = sum(payments.mapped('penalty'))
        total_revenue = interest_income + fee_income + penalty_income
        
        loans = self.env['lalaa.loan'].search([('state', 'in', ['active', 'default', 'closed'])])
        avg_loan_size = sum(loans.mapped('principal_amount')) / len(loans) if loans else 0

        return {
            'interest_income_ytd': interest_income,
            'total_revenue_ytd': total_revenue,
            'avg_loan_size': avg_loan_size
        }

    def _get_liquidity(self, filters):
        # Assuming we just look at expected cashflows vs current
        today = fields.Date.today()
        next_30_days = today + timedelta(days=30)
        
        schedules = self.env['lalaa.loan.schedule'].search([
            ('date_due', '>=', today),
            ('date_due', '<=', next_30_days)
        ])
        expected_inflows = sum(schedules.mapped('total_due'))
        
        return {
            'expected_inflows_30d': expected_inflows
        }

    def _get_risk_concentration(self, filters):
        loans = self.env['lalaa.loan'].search([('state', '=', 'active')])
        
        # By Product
        by_product = {}
        for loan in loans:
            name = loan.product_id.name or 'Unknown'
            by_product[name] = by_product.get(name, 0) + loan.outstanding_principal
            
        # By Branch
        by_branch = {}
        for loan in loans:
            name = loan.branch_id.name or 'Head Office'
            by_branch[name] = by_branch.get(name, 0) + loan.outstanding_principal

        # By Sector
        by_sector = {}
        for loan in loans:
            name = loan.sector_id.name or 'Uncategorized'
            by_sector[name] = by_sector.get(name, 0) + loan.outstanding_principal

        return {
            'by_product': by_product,
            'by_branch': by_branch,
            'by_sector': by_sector
        }

    def _get_pipeline(self, filters):
        apps = self.env['lalaa.loan.application'].search([
            ('state', 'not in', ['approved', 'rejected'])
        ])
        return {
            'pending_applications_count': len(apps),
            'pending_applications_amount': sum(apps.mapped('requested_amount'))
        }

    def _get_compliance_alerts(self, filters):
        company = self.env.company
        alerts = []
        if company.lalaa_umra_licence_expiry_date:
            days_to_expiry = (company.lalaa_umra_licence_expiry_date - fields.Date.today()).days
            if days_to_expiry < 90:
                alerts.append({
                    'type': 'warning',
                    'message': f'UMRA Licence expires in {days_to_expiry} days.'
                })
        
        # Check if PAR>30 exceeds target
        loans = self.env['lalaa.loan'].search([('state', 'in', ['active', 'default'])])
        par_30 = sum(loans.filtered(lambda l: getattr(l, 'days_past_due', 0) > 30).mapped('outstanding_principal'))
        glp = sum(loans.mapped('outstanding_principal')) or 1
        par_30_ratio = (par_30 / glp) * 100
        
        if par_30_ratio > company.lalaa_par_target_percent:
            alerts.append({
                'type': 'danger',
                'message': f'PAR>30 ({par_30_ratio:.1f}%) exceeds target ({company.lalaa_par_target_percent:.1f}%)'
            })
            
        return alerts

    def _get_top_borrowers(self, filters):
        # Top 5 Borrowers by outstanding principal
        loans = self.env['lalaa.loan'].search(
            [('state', 'in', ['active', 'default'])],
            order='outstanding_principal desc',
            limit=5
        )
        top = []
        for loan in loans:
            top.append({
                'name': loan.partner_id.name or 'Unknown',
                'balance': loan.outstanding_principal
            })
        return top

    @api.model
    def _send_weekly_digest(self):
        """
        Triggered by cron to send a weekly summary to the Loan Manager group.
        """
        data = self.get_dashboard_data()
        
        # Format values for email
        glp = f"UGX {data['headline']['gross_loan_portfolio']:,.0f}"
        active = data['headline']['active_loans_count']
        disbursed = f"UGX {data['headline']['disbursed_ytd']:,.0f}"
        par30 = f"{data['portfolio']['par_30_ratio']:.1f}%"
        
        # Get users in Loan Manager group
        group = self.env.ref('lalaa_loan.group_loan_manager', raise_if_not_found=False)
        if not group or not group.user_ids:
            return
            
        emails = [u.email for u in group.user_ids if u.email]
        if not emails:
            return
            
        body_html = f"""
        <div style="font-family: sans-serif; color: #333;">
            <h2>Weekly Executive Loan Digest</h2>
            <p>Here is your weekly summary of the portfolio:</p>
            <ul>
                <li><strong>Gross Loan Portfolio:</strong> {glp}</li>
                <li><strong>Active Loans:</strong> {active}</li>
                <li><strong>Disbursed YTD:</strong> {disbursed}</li>
                <li><strong>PAR>30:</strong> {par30}</li>
            </ul>
            <p>Please log in to the system to view full details.</p>
        </div>
        """
        
        mail_values = {
            'subject': 'Weekly Executive Loan Digest',
            'body_html': body_html,
            'email_to': ','.join(emails),
            'email_from': self.env.company.email or self.env.user.email,
        }
        
        self.env['mail.mail'].create(mail_values).send()
