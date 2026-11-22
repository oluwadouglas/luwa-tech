# -*- coding: utf-8 -*-
{
    "name": "Social Media AI Manager",
    "version": "19.0.1.0.0",
    "category": "Marketing/Social Media",
    "summary": "AI Social Media Content Generator, AI Image Studio, Post Manager & Content Calendar",
    "description": """
Social Media AI Content Management (Phase 1)
============================================
Professional AI-powered Social Media Content Creation & Management suite for Odoo 19 Community:
- Modern OWL Executive Dashboard (KPIs, Platform Breakdown, Recent & Upcoming Content)
- AI Content Generator (OpenAI API + Free Zero-Key OpenAI-Compatible AI fallback)
  generating headlines, marketing captions, hashtags, calls to action, and platform variations
  for Facebook, Instagram, LinkedIn, and X (Twitter)
- AI Image Generation Studio (OpenAI DALL-E + Free Flux AI Image API + Local Graphic fallback)
  with preview, library storage, and direct attachment to social media posts
- Full Social Media Post Lifecycle (Draft, Pending Approval, Approved, Scheduled, Published)
- Interactive Content Calendar with drag-and-drop rescheduling and platform/status filters
    """,
    "author": "Luwa Tech",
    "website": "https://www.luwatech.it",
    "license": "LGPL-3",
    "depends": ["base", "web", "mail"],
    "data": [
        "security/social_media_ai_security.xml",
        "security/ir.model.access.csv",
        "views/social_media_account_views.xml",
        "views/social_media_post_views.xml",
        "views/social_media_ai_generator_views.xml",
        "views/social_media_ai_image_views.xml",
        "views/social_media_ai_config_views.xml",
        "views/social_media_ai_menus.xml",
        "data/demo_posts_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "social_media_ai/static/src/components/dashboard.scss",
            "social_media_ai/static/src/components/dashboard.xml",
            "social_media_ai/static/src/components/dashboard.js",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
