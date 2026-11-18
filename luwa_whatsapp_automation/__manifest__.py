# -*- coding: utf-8 -*-
{
    "name": "Luwa Tech WhatsApp Automation",
    "version": "19.0.1.1.0",
    "category": "Sales/CRM",
    "summary": "Isolated QR-linked WhatsApp bridge and automated reminders for CRM, Sales, Invoices, and Subscriptions",
    "author": "Luwa Tech",
    "website": "https://www.luwatech.it",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "crm",
        "sale_management",
        "account",
        "portal",
        "whatsapp_mail_messaging",
        "luwatech_subscription",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/whatsapp_data.xml",
        "views/whatsapp_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
