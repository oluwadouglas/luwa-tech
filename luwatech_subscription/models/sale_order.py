# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    subscription_ids = fields.One2many(
        "luwa.subscription",
        "sale_order_id",
        string="Subscriptions",
    )
    subscription_count = fields.Integer(
        string="Subscriptions",
        compute="_compute_subscription_count",
    )

    @api.depends("subscription_ids")
    def _compute_subscription_count(self):
        for order in self:
            order.subscription_count = len(order.subscription_ids)

    def _action_confirm(self):
        res = super()._action_confirm()
        self._create_luwa_subscriptions(target_state="active")
        return res

    def _create_luwa_subscriptions(self, target_state="active"):
        """Create or activate subscription records for any subscription line on checkout/confirmation."""
        Subscription = self.env["luwa.subscription"].sudo()
        default_plan = self.env["luwa.subscription.plan"].sudo().search([], limit=1)
        today = fields.Date.context_today(self)
        for order in self:
            existing_by_tmpl = {s.product_tmpl_id.id: s for s in order.subscription_ids}
            for line in order.order_line:
                tmpl = line.product_id.product_tmpl_id
                if not tmpl.is_subscription:
                    continue
                plan = tmpl.subscription_plan_id or default_plan
                if not plan:
                    continue
                existing = existing_by_tmpl.get(tmpl.id)
                if existing:
                    if target_state == "active" and existing.state == "draft":
                        existing.write({
                            "state": "active",
                            "start_date": today,
                            "next_billing_date": plan.get_next_billing_date(today),
                        })
                    continue
                sub = Subscription.create({
                    "partner_id": order.partner_id.id,
                    "company_id": order.company_id.id,
                    "currency_id": order.currency_id.id,
                    "product_tmpl_id": tmpl.id,
                    "product_id": line.product_id.id,
                    "plan_id": plan.id,
                    "recurring_amount": line.price_unit or tmpl.list_price,
                    "state": target_state,
                    "start_date": today,
                    "next_billing_date": plan.get_next_billing_date(today),
                    "sale_order_id": order.id,
                    "user_id": order.user_id.id or self.env.user.id,
                })
                existing_by_tmpl[tmpl.id] = sub

    def action_view_subscriptions(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": "Subscriptions",
            "res_model": "luwa.subscription",
            "view_mode": "list,form",
            "domain": [("sale_order_id", "=", self.id)],
            "context": {
                "default_sale_order_id": self.id,
                "default_partner_id": self.partner_id.id,
            },
        }
        if len(self.subscription_ids) == 1:
            action["view_mode"] = "form"
            action["res_id"] = self.subscription_ids.id
        return action


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _post_process(self):
        res = super()._post_process()
        for tx in self:
            if tx.state in ("pending", "authorized", "done") and tx.sale_order_ids:
                target_state = "active" if tx.state == "done" else "draft"
                tx.sale_order_ids.sudo()._create_luwa_subscriptions(target_state=target_state)
        return res


class ResPartner(models.Model):
    _inherit = "res.partner"

    subscription_ids = fields.One2many(
        "luwa.subscription",
        "partner_id",
        string="Subscriptions",
    )
    subscription_count = fields.Integer(
        string="Subscriptions",
        compute="_compute_subscription_count",
    )

    @api.depends("subscription_ids")
    def _compute_subscription_count(self):
        for partner in self:
            partner.subscription_count = len(partner.subscription_ids)

    def action_view_subscriptions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Subscriptions",
            "res_model": "luwa.subscription",
            "view_mode": "list,kanban,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }
