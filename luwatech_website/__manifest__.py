# -*- coding: utf-8 -*-
{
    "name": "Luwa Tech Digital & SaaS Agency Website (Linoor Index-6)",
    "version": "19.0.1.0.0",
    "category": "Website",
    "summary": "Reverse-engineered Linoor Index-6 Corporate & Digital SaaS Agency Website Theme for Luwa Tech",
    "description": """
Luwa Tech Digital & SaaS Agency Website Theme
=============================================
Complete Odoo 19 Website Theme modeled after Linoor Home 06 (Corporate & Digital Agency),
tailored for Luwa Tech (SaaS, Odoo ERP, Custom Software, Web & Mobile Apps, Digital Marketing, IT Training).
    """,
    "author": "Luwa Tech",
    "website": "https://www.luwatech.it",
    "license": "LGPL-3",
    "depends": ["website"],
    "data": [
        "views/website_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "luwatech_website/static/src/css/fontawesome-all.css",
            "luwatech_website/static/src/css/flaticon.css",
            "luwatech_website/static/src/css/linoor-icons-2.css",
            "luwatech_website/static/src/css/luwatech_linoor.css",
            "luwatech_website/static/src/js/luwatech_linoor.js",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
