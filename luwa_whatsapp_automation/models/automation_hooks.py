# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


def _open_composer_action(record, phone, default_message, partner=None, partners=None, attach_pdf=False, pdf_preview_name=""):
    partner_ids = []
    if partners:
        partner_ids = partners.ids
    elif partner:
        partner_ids = [partner.id]
    return {
        "type": "ir.actions.act_window",
        "name": _("Send WhatsApp Message & Document"),
        "res_model": "luwa.whatsapp.composer",
        "view_mode": "form",
        "target": "new",
        "context": {
            "default_partner_id": partner.id if partner else (partner_ids[0] if partner_ids else False),
            "default_partner_ids": [(6, 0, partner_ids)],
            "default_phone": phone or "",
            "default_message": default_message or "",
            "default_attach_pdf": bool(attach_pdf),
            "default_pdf_preview_name": pdf_preview_name or "",
            "default_res_model": record._name if len(record) == 1 else False,
            "default_res_id": record.id if len(record) == 1 else 0,
        },
    }


class CrmLead(models.Model):
    _inherit = "crm.lead"

    luwa_last_wa_date = fields.Datetime(string="Last WhatsApp Auto-Reply", copy=False, readonly=True)

    def action_open_luwa_whatsapp(self):
        self.ensure_one()
        cfg = self.env["luwa.whatsapp.config"].get_solo()
        phone = self.phone or (self.partner_id.phone if self.partner_id else "")
        customer = self.contact_name or (self.partner_id.name if self.partner_id else self.name) or "Valued Client"
        msg = cfg._format_template(
            cfg.tpl_crm_ack,
            partner_name=customer,
            record_name=self.name or "Inquiry",
        )
        return _open_composer_action(
            self,
            phone,
            msg,
            partner=self.partner_id,
            attach_pdf=False,
            pdf_preview_name="No PDF (CRM Inquiry - you may upload a custom PDF/brochure below)",
        )

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        if self.env.context.get("skip_luwa_whatsapp_auto"):
            return leads
        try:
            cfg = self.env["luwa.whatsapp.config"].get_solo()
            if cfg.auto_crm_ack:
                for lead in leads:
                    phone = lead.phone or (lead.partner_id.phone if lead.partner_id else "")
                    if not phone:
                        continue
                    customer = (
                        lead.contact_name
                        or (lead.partner_id.name if lead.partner_id else "")
                        or "Valued Client"
                    )
                    msg = cfg._format_template(
                        cfg.tpl_crm_ack,
                        partner_name=customer,
                        record_name=lead.name or "Website Inquiry",
                    )
                    log = cfg.send_whatsapp_message(
                        phone=phone,
                        message=msg,
                        partner=lead.partner_id,
                        res_model="crm.lead",
                        res_id=lead.id,
                        trigger_type="crm_ack",
                        queue_if_offline=True,
                        auto_pdf=False,
                    )
                    if log.state in ("sent", "queued"):
                        lead.sudo().luwa_last_wa_date = fields.Datetime.now()
        except Exception as exc:
            _logger.warning("Luwa WhatsApp CRM lead auto-reply failed safely: %s", exc)
        return leads


class SaleOrder(models.Model):
    _inherit = "sale.order"

    luwa_last_wa_reminder_date = fields.Date(string="Last WhatsApp Reminder", copy=False, readonly=True)

    def action_open_luwa_whatsapp(self):
        self.ensure_one()
        cfg = self.env["luwa.whatsapp.config"].get_solo()
        phone = self.partner_id.phone or ""
        doc_info = cfg._extract_record_pdf_and_link("sale.order", self.id, include_pdf=False)
        tpl = cfg.tpl_quote_reminder if self.state in ("draft", "sent") else cfg.tpl_order_confirm
        rec_ref = self.name if (self.name and self.name != "/") else f"DRAFT-{self.id:04d}"
        prefix = "Quotation" if self.state in ("draft", "sent") else "Order"
        msg = cfg._format_template(
            tpl,
            partner_name=self.partner_id.name or "Valued Client",
            record_name=rec_ref,
            amount=f"{self.amount_total:,.0f}",
            currency=self.currency_id.name or "",
            due_date=str(self.validity_date or "Open"),
            portal_url=doc_info["portal_url"],
        )
        return _open_composer_action(
            self,
            phone,
            msg,
            partner=self.partner_id,
            attach_pdf=True,
            pdf_preview_name=f"LuwaTech-{prefix}-{rec_ref}.pdf (Official PDF Auto-Attached)",
        )

    def action_send_whatsapp(self):
        """Route Cybrosys Sale Order button to unified Luwa WhatsApp & PDF composer."""
        return self.action_open_luwa_whatsapp()

    def action_whatsapp_multi(self):
        """Route multi-select Sale Order button to unified multi-recipient composer."""
        if len(self) == 1:
            return self.action_open_luwa_whatsapp()
        partners = self.mapped("partner_id")
        phones = ", ".join(dict.fromkeys(p.phone.strip() for p in partners if p.phone and p.phone.strip()))
        first = self[0]
        cfg = self.env["luwa.whatsapp.config"].get_solo()
        doc_info = cfg._extract_record_pdf_and_link("sale.order", first.id, include_pdf=False)
        msg = cfg._format_template(
            cfg.tpl_quote_reminder,
            partner_name="Valued Client",
            record_name=", ".join(self.mapped("name")),
            amount=f"{sum(self.mapped('amount_total')):,.0f}",
            currency=first.currency_id.name or "",
            due_date=str(first.validity_date or "Open"),
            portal_url=doc_info["portal_url"],
        )
        return _open_composer_action(
            self,
            phones,
            msg,
            partners=partners,
            attach_pdf=False,
            pdf_preview_name="Multi-record selection (upload a shared PDF below if needed)",
        )

    def _action_confirm(self):
        res = super()._action_confirm()
        if self.env.context.get("skip_luwa_whatsapp_auto"):
            return res
        try:
            cfg = self.env["luwa.whatsapp.config"].get_solo()
            if cfg.auto_order_confirm:
                for order in self:
                    phone = order.partner_id.phone
                    if not phone:
                        continue
                    doc_info = cfg._extract_record_pdf_and_link("sale.order", order.id, include_pdf=cfg.auto_attach_pdf)
                    rec_ref = order.name if (order.name and order.name != "/") else f"ORDER-{order.id:04d}"
                    msg = cfg._format_template(
                        cfg.tpl_order_confirm,
                        partner_name=order.partner_id.name or "Valued Client",
                        record_name=rec_ref,
                        amount=f"{order.amount_total:,.0f}",
                        currency=order.currency_id.name or "",
                        portal_url=doc_info["portal_url"],
                    )
                    cfg.send_whatsapp_message(
                        phone=phone,
                        message=msg,
                        partner=order.partner_id,
                        res_model="sale.order",
                        res_id=order.id,
                        trigger_type="order_confirm",
                        queue_if_offline=True,
                        document_b64=doc_info["document_b64"],
                        filename=doc_info["filename"],
                        auto_pdf=False,
                    )
        except Exception as exc:
            _logger.warning("Luwa WhatsApp order confirmation failed safely: %s", exc)
        return res


class AccountMove(models.Model):
    _inherit = "account.move"

    luwa_last_wa_reminder_date = fields.Date(string="Last WhatsApp Reminder", copy=False, readonly=True)

    def action_open_luwa_whatsapp(self):
        self.ensure_one()
        cfg = self.env["luwa.whatsapp.config"].get_solo()
        phone = self.partner_id.phone or ""
        amount_val = self.amount_residual if self.amount_residual > 0 else self.amount_total
        doc_info = cfg._extract_record_pdf_and_link("account.move", self.id, include_pdf=False)
        rec_ref = self.name if (self.name and self.name != "/") else f"DRAFT-{self.id:04d}"
        msg = cfg._format_template(
            cfg.tpl_invoice_reminder,
            partner_name=self.partner_id.name or "Valued Client",
            record_name=rec_ref,
            amount=f"{amount_val:,.0f}",
            currency=self.currency_id.name or "",
            due_date=str(self.invoice_date_due or fields.Date.context_today(self)),
            portal_url=doc_info["portal_url"],
        )
        return _open_composer_action(
            self,
            phone,
            msg,
            partner=self.partner_id,
            attach_pdf=True,
            pdf_preview_name=f"LuwaTech-Invoice-{rec_ref}.pdf (Official PDF Auto-Attached)",
        )

    def action_send_whatsapp(self):
        """Route Cybrosys Invoice button to unified Luwa WhatsApp & PDF composer."""
        return self.action_open_luwa_whatsapp()

    def action_whatsapp_multi(self):
        """Route multi-select Invoice button to unified multi-recipient composer."""
        if len(self) == 1:
            return self.action_open_luwa_whatsapp()
        partners = self.mapped("partner_id")
        phones = ", ".join(dict.fromkeys(p.phone.strip() for p in partners if p.phone and p.phone.strip()))
        first = self[0]
        cfg = self.env["luwa.whatsapp.config"].get_solo()
        doc_info = cfg._extract_record_pdf_and_link("account.move", first.id, include_pdf=False)
        msg = cfg._format_template(
            cfg.tpl_invoice_reminder,
            partner_name="Valued Client",
            record_name=", ".join(m.name if (m.name and m.name != "/") else f"DRAFT-{m.id:04d}" for m in self),
            amount=f"{sum(self.mapped('amount_total')):,.0f}",
            currency=first.currency_id.name or "",
            due_date=str(first.invoice_date_due or fields.Date.context_today(self)),
            portal_url=doc_info["portal_url"],
        )
        return _open_composer_action(
            self,
            phones,
            msg,
            partners=partners,
            attach_pdf=False,
            pdf_preview_name="Multi-invoice selection (upload a shared PDF below if needed)",
        )


class LuwaSubscription(models.Model):
    _inherit = "luwa.subscription"

    luwa_last_wa_reminder_date = fields.Date(string="Last WhatsApp Reminder", copy=False, readonly=True)

    def action_open_luwa_whatsapp(self):
        self.ensure_one()
        cfg = self.env["luwa.whatsapp.config"].get_solo()
        phone = self.partner_phone or self.partner_id.phone or ""
        plan_name = self.plan_id.name or self.product_tmpl_id.name or "Subscription"
        doc_info = cfg._extract_record_pdf_and_link("luwa.subscription", self.id, include_pdf=False)
        rec_ref = self.name if (self.name and self.name != "/") else f"SUB-{self.id:04d}"
        msg = cfg._format_template(
            cfg.tpl_subscription_reminder,
            partner_name=self.partner_id.name or "Valued Client",
            record_name=rec_ref,
            plan_name=plan_name,
            amount=f"{self.recurring_amount:,.0f}",
            currency=self.currency_id.name or "",
            due_date=str(self.next_billing_date or ""),
            portal_url=doc_info["portal_url"],
        )
        return _open_composer_action(
            self,
            phone,
            msg,
            partner=self.partner_id,
            attach_pdf=True,
            pdf_preview_name=f"Subscription-{rec_ref}.pdf (Latest Invoice/Order PDF Auto-Attached if available)",
        )
