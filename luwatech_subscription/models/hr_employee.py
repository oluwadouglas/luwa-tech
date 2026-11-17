# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployeeWebsiteTeam(models.Model):
    _inherit = "hr.employee"

    is_published_website = fields.Boolean(
        string="Publish on Website (Our Team)",
        default=False,
        help="Enable this to showcase this team member on the Luwa Tech homepage and /team page.",
    )
    website_role = fields.Char(
        string="Website Role / Title",
        help="Public role displayed on the website (e.g. Founder & CEO, Lead Cloud Architect).",
    )
    website_department_tag = fields.Char(
        string="Specialty Badge",
        default="Kampala Studio",
        help="Short badge shown on the team card (e.g. Executive Leadership, Cloud & SaaS, Digital Growth).",
    )
    website_bio = fields.Text(
        string="Website Bio",
        help="Short 1-2 sentence public bio displayed on the homepage and Our Team page.",
    )
    website_sequence = fields.Integer(
        string="Website Display Order",
        default=10,
    )
    social_linkedin = fields.Char(string="LinkedIn URL", placeholder="https://www.linkedin.com/in/...")
    social_twitter = fields.Char(string="X (Twitter) URL", placeholder="https://x.com/...")
    social_github = fields.Char(string="GitHub / Portfolio URL", placeholder="https://github.com/...")
    social_instagram = fields.Char(string="Instagram URL", placeholder="https://www.instagram.com/...")
    social_whatsapp = fields.Char(string="WhatsApp Link or Number", placeholder="https://wa.me/256787819453")

    def action_toggle_website_publish(self):
        for rec in self:
            rec.is_published_website = not rec.is_published_website

    def get_public_whatsapp_url(self):
        self.ensure_one()
        raw = (self.social_whatsapp or self.work_phone or "").strip()
        if not raw:
            return ""
        if raw.startswith("http://") or raw.startswith("https://"):
            return raw
        digits = "".join(ch for ch in raw if ch.isdigit())
        if digits.startswith("0") and len(digits) == 10:
            digits = "256" + digits[1:]
        return f"https://wa.me/{digits}" if digits else ""
