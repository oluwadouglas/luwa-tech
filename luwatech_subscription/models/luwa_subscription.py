# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LuwaSubscription(models.Model):
    _name = "luwa.subscription"
    _description = "Luwa Tech Customer Subscription"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Subscription Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        tracking=True,
    )
    partner_email = fields.Char(related="partner_id.email", string="Email", readonly=True)
    partner_phone = fields.Char(related="partner_id.phone", string="Phone", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Subscription Package",
        domain="[('is_subscription', '=', True)]",
        required=True,
        tracking=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product Variant",
        compute="_compute_product_id",
        store=True,
        readonly=False,
    )
    plan_id = fields.Many2one(
        "luwa.subscription.plan",
        string="Billing Plan",
        required=True,
        tracking=True,
    )
    recurring_amount = fields.Monetary(
        string="Recurring Price",
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("paused", "Paused"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    start_date = fields.Date(
        string="Start Date",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    next_billing_date = fields.Date(
        string="Next Billing Date",
        tracking=True,
    )
    end_date = fields.Date(string="End Date", tracking=True)
    auto_renew = fields.Boolean(string="Auto-Renew", default=True, tracking=True)
    user_id = fields.Many2one(
        "res.users",
        string="Account Manager",
        default=lambda self: self.env.user,
        tracking=True,
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Origin Sales Order",
        readonly=True,
        copy=False,
    )
    invoice_ids = fields.Many2many(
        "account.move",
        string="Invoices",
        copy=False,
    )
    invoice_count = fields.Integer(
        string="Invoices",
        compute="_compute_invoice_count",
    )
    includes_invoicing = fields.Boolean(related="product_tmpl_id.includes_invoicing", readonly=True)
    includes_stock_management = fields.Boolean(related="product_tmpl_id.includes_stock_management", readonly=True)
    includes_payment_gateway = fields.Boolean(related="product_tmpl_id.includes_payment_gateway", readonly=True)
    notes = fields.Text(string="Internal Notes")

    @api.depends("product_tmpl_id")
    def _compute_product_id(self):
        for rec in self:
            if rec.product_tmpl_id and (
                not rec.product_id or rec.product_id.product_tmpl_id != rec.product_tmpl_id
            ):
                rec.product_id = rec.product_tmpl_id.product_variant_id

    @api.depends("invoice_ids")
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    @api.onchange("product_tmpl_id")
    def _onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            self.recurring_amount = self.product_tmpl_id.list_price
            if self.product_tmpl_id.subscription_plan_id:
                self.plan_id = self.product_tmpl_id.subscription_plan_id
            elif not self.plan_id:
                self.plan_id = self.env["luwa.subscription.plan"].search([], limit=1)
            if self.plan_id and self.start_date and not self.next_billing_date:
                self.next_billing_date = self.plan_id.get_next_billing_date(self.start_date)

    @api.onchange("plan_id", "start_date")
    def _onchange_plan_or_start(self):
        if self.plan_id and self.start_date:
            self.next_billing_date = self.plan_id.get_next_billing_date(self.start_date)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("luwa.subscription") or _("New")
                )
            if not vals.get("next_billing_date") and vals.get("plan_id"):
                plan = self.env["luwa.subscription.plan"].browse(vals["plan_id"])
                start = fields.Date.to_date(vals.get("start_date")) if vals.get("start_date") else fields.Date.context_today(self)
                vals["next_billing_date"] = plan.get_next_billing_date(start)
        return super().create(vals_list)

    def action_activate(self):
        for rec in self:
            if not rec.start_date:
                rec.start_date = fields.Date.context_today(rec)
            if not rec.next_billing_date and rec.plan_id:
                rec.next_billing_date = rec.plan_id.get_next_billing_date(rec.start_date)
            rec.state = "active"

    def action_pause(self):
        for rec in self:
            rec.state = "paused"

    def action_resume(self):
        for rec in self:
            rec.state = "active"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"
            rec.end_date = fields.Date.context_today(rec)

    def action_set_draft(self):
        for rec in self:
            rec.state = "draft"

    def action_create_renewal_invoice(self):
        """Create a draft customer invoice for the next subscription period and advance billing date."""
        for rec in self:
            if rec.state not in ("active", "expired"):
                raise UserError(_("Only Active or Expired subscriptions can generate a renewal invoice."))
            product = rec.product_id or rec.product_tmpl_id.product_variant_id
            if not product:
                raise UserError(_("No product variant found for subscription package %s.") % rec.product_tmpl_id.display_name)
            invoice = self.env["account.move"].create({
                "move_type": "out_invoice",
                "partner_id": rec.partner_id.id,
                "company_id": rec.company_id.id,
                "currency_id": rec.currency_id.id,
                "invoice_origin": rec.name,
                "invoice_line_ids": [
                    (0, 0, {
                        "product_id": product.id,
                        "name": f"{rec.product_tmpl_id.name} ({rec.name} - {rec.plan_id.name})",
                        "quantity": 1.0,
                        "price_unit": rec.recurring_amount,
                    })
                ],
            })
            rec.invoice_ids = [(4, invoice.id)]
            base_date = rec.next_billing_date or fields.Date.context_today(rec)
            rec.next_billing_date = rec.plan_id.get_next_billing_date(base_date)
            if rec.state == "expired":
                rec.state = "active"
            rec.message_post(body=_("Renewal invoice %s generated.") % invoice.name)
        if len(self) == 1 and self.invoice_ids:
            return self.action_view_invoices()
        return True

    def action_view_invoices(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": _("Subscription Invoices"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", self.invoice_ids.ids)],
        }
        if len(self.invoice_ids) == 1:
            action["view_mode"] = "form"
            action["res_id"] = self.invoice_ids.id
        return action

    @api.model
    def _cron_check_subscriptions(self):
        """Daily cron: mark active subscriptions past end_date as expired."""
        today = fields.Date.context_today(self)
        expired = self.search([
            ("state", "=", "active"),
            ("end_date", "!=", False),
            ("end_date", "<", today),
        ])
        if expired:
            expired.write({"state": "expired"})
