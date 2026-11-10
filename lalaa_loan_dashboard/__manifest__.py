# -*- coding: utf-8 -*-
{
    'name': "Executive Loan Dashboard",
    'summary': "Advanced analytical dashboard for Loan Management",
    'description': """
Executive Loan Dashboard for Lalaa Loan module.
Features:
- Portfolio Quality
- Collections tracking
- Profitability metrics
- Compliance alerts
    """,
    'author': "Munig Engineering",
    'website': "https://munigengineering.com",
    'category': 'Finance/Loans',
    'version': '20.0.1.0.0',
    'depends': ['lalaa_loan', 'account', 'mail', 'web'],
    'data': [
        'security/ir.access.csv',
        'views/dashboard_menuitem.xml',
        'data/cron_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'lalaa_loan_dashboard/static/lib/chartjs/chart.min.js',
            'lalaa_loan_dashboard/static/src/components/**/*.js',
            'lalaa_loan_dashboard/static/src/components/**/*.xml',
            'lalaa_loan_dashboard/static/src/components/**/*.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
