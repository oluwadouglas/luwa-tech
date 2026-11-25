# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class LuwaSubscriptionPlan(models.Model):
    _name = "luwa.subscription.plan"
    _description = "Luwa Subscription Billing Plan"
    _order = "billing_interval, id"

    name = fields.Char(string="Plan Name", required=True, translate=True)
    code = fields.Char(string="Code", required=True)
    billing_interval = fields.Integer(string="Billing Every", default=1, required=True)
    billing_unit = fields.Selection(
        [
            ("day", "Day(s)"),
            ("week", "Week(s)"),
            ("month", "Month(s)"),
            ("year", "Year(s)"),
        ],
        string="Billing Unit",
        default="month",
        required=True,
    )
    active = fields.Boolean(default=True)
    description = fields.Text(string="Description", translate=True)
    subscription_count = fields.Integer(
        string="Subscriptions",
        compute="_compute_subscription_count",
    )

    _code_uniq = models.Constraint("unique (code)", "The subscription plan code must be unique.")

    @api.depends()
    def _compute_subscription_count(self):
        counts = self.env["luwa.subscription"]._read_group(
            [("plan_id", "in", self.ids)],
            ["plan_id"],
            ["__count"],
        )
        mapped = {plan.id: count for plan, count in counts}
        for rec in self:
            rec.subscription_count = mapped.get(rec.id, 0)

    def get_next_billing_date(self, from_date=None):
        """Return the next billing date from `from_date` according to this plan's interval."""
        self.ensure_one()
        base_date = from_date or fields.Date.context_today(self)
        interval = max(self.billing_interval or 1, 1)
        if self.billing_unit == "day":
            return base_date + relativedelta(days=interval)
        if self.billing_unit == "week":
            return base_date + relativedelta(weeks=interval)
        if self.billing_unit == "year":
            return base_date + relativedelta(years=interval)
        return base_date + relativedelta(months=interval)

    def get_period_label(self):
        """Human-readable short suffix such as 'month' or 'year'."""
        self.ensure_one()
        unit_map = {
            "day": "day",
            "week": "week",
            "month": "month",
            "year": "year",
        }
        unit = unit_map.get(self.billing_unit, "month")
        if (self.billing_interval or 1) > 1:
            return f"{self.billing_interval} {unit}s"
        return unit
