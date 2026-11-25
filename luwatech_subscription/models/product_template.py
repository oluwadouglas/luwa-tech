# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_subscription = fields.Boolean(
        string="Subscription Module",
        default=False,
        help="Check if this product is a recurring subscription package displayed in Subscriptions & Shop.",
    )
    subscription_category = fields.Selection(
        [
            ("ecommerce", "E-Commerce"),
            ("marketing", "Digital Marketing"),
            ("saas", "SaaS / Other"),
        ],
        string="Subscription Category",
        default="ecommerce",
    )
    subscription_plan_id = fields.Many2one(
        "luwa.subscription.plan",
        string="Billing Plan",
        help="Default billing cycle for this subscription product.",
    )
    subscription_tier = fields.Selection(
        [
            ("starter", "Starter"),
            ("complete", "Complete"),
            ("enterprise", "Enterprise"),
        ],
        string="Subscription Tier",
        default="starter",
    )
    subscription_badge = fields.Char(
        string="Website Badge",
        translate=True,
        help="Short highlight badge displayed on the website card.",
    )
    subscription_note = fields.Char(
        string="Pricing / Scope Note",
        translate=True,
        help="Short note shown below the price on website cards (e.g. 'Excludes paid ad spend budgets').",
    )
    subscription_features = fields.Text(
        string="Included Features (one per line)",
        translate=True,
        help="Enter one feature per line to display as a checklist on the website and product page.",
    )
    includes_ecommerce = fields.Boolean(string="Includes E-Commerce Store", default=True)
    includes_invoicing = fields.Boolean(string="Includes Minimal Invoicing", default=False)
    includes_stock_management = fields.Boolean(string="Includes Stock Management", default=False)
    includes_payment_gateway = fields.Boolean(string="Includes Payment Gateway", default=False)
    subscription_count = fields.Integer(
        string="Subscriptions",
        compute="_compute_subscription_count",
    )

    def _compute_subscription_count(self):
        counts = self.env["luwa.subscription"]._read_group(
            [("product_tmpl_id", "in", self.ids)],
            ["product_tmpl_id"],
            ["__count"],
        )
        mapped = {tmpl.id: count for tmpl, count in counts}
        for rec in self:
            rec.subscription_count = mapped.get(rec.id, 0)

    def get_subscription_feature_list(self):
        """Return cleaned feature bullet lines for website rendering."""
        self.ensure_one()
        if not self.subscription_features:
            return []
        return [
            line.strip()
            for line in self.subscription_features.splitlines()
            if line.strip()
        ]

    def action_view_subscriptions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Subscriptions",
            "res_model": "luwa.subscription",
            "view_mode": "list,kanban,form",
            "domain": [("product_tmpl_id", "=", self.id)],
            "context": {
                "default_product_tmpl_id": self.id,
                "default_plan_id": self.subscription_plan_id.id,
                "default_recurring_amount": self.list_price,
            },
        }
