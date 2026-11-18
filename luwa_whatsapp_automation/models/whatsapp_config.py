# -*- coding: utf-8 -*-
import base64
import json
import logging
import re
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


DEFAULT_TPL_CRM_ACK = (
    "*LUWA TECH - KAMPALA DIGITAL STUDIO*\n\n"
    "Hello *{partner_name}*,\n"
    "Thank you for contacting *Luwa Tech*! Your inquiry has been received and assigned to our solutions team:\n\n"
    "- *Reference:* {record_name}\n"
    "- *Client:* {partner_name}\n\n"
    "A specialist is reviewing your request and will reach out shortly. You can also reply directly to this WhatsApp chat at any time.\n\n"
    "*Luwa Tech Kampala*\n"
    "Tel: +256 787 819 453\n"
    "Web: https://www.luwatech.it"
)

DEFAULT_TPL_ORDER_CONFIRM = (
    "*ORDER CONFIRMED - LUWA TECH*\n\n"
    "Hello *{partner_name}*,\n"
    "Thank you for choosing *Luwa Tech*! Your order has been confirmed and your official PDF document is attached directly to this message.\n\n"
    "- *Order Ref:* {record_name}\n"
    "- *Total Amount:* {currency} {amount}\n"
    "- *Attachment:* Official Order PDF\n\n"
    "*View / Download Online:*\n"
    "{portal_url}\n\n"
    "Reply directly to this message if you need any assistance from our team.\n\n"
    "*Luwa Tech - Digital Agency & Software Studio*\n"
    "https://www.luwatech.it"
)

DEFAULT_TPL_QUOTE_REMINDER = (
    "*QUOTATION & PROPOSAL - LUWA TECH*\n\n"
    "Hello *{partner_name}*,\n"
    "Please find attached your official quotation from *Luwa Tech* for your review:\n\n"
    "- *Quotation Ref:* {record_name}\n"
    "- *Total Amount:* {currency} {amount}\n"
    "- *Valid Until:* {due_date}\n"
    "- *Attachment:* Official Quotation PDF\n\n"
    "*Review & Download Online:*\n"
    "{portal_url}\n\n"
    "Simply reply *\"APPROVE\"* here on WhatsApp to proceed, or let us know if you would like any adjustments.\n\n"
    "*Luwa Tech Kampala*\n"
    "Tel: +256 787 819 453 | https://www.luwatech.it"
)

DEFAULT_TPL_INVOICE_REMINDER = (
    "*INVOICE & PAYMENT REMINDER - LUWA TECH*\n\n"
    "Hello *{partner_name}*,\n"
    "Kindly find attached your official invoice from *Luwa Tech*:\n\n"
    "- *Invoice Ref:* {record_name}\n"
    "- *Balance Due:* {currency} {amount}\n"
    "- *Due Date:* {due_date}\n"
    "- *Attachment:* Official Invoice PDF\n\n"
    "*View / Download PDF Online:*\n"
    "{portal_url}\n\n"
    "*Payment Options:*\n"
    "- *Mobile Money (MTN / Airtel):* +256 787 819 453 _(Ref: {record_name})_\n"
    "- *Client Portal:* Use the secure link above\n\n"
    "Please share your payment confirmation here once settled. Thank you for partnering with *Luwa Tech*!"
)

DEFAULT_TPL_SUBSCRIPTION_REMINDER = (
    "*SUBSCRIPTION RENEWAL NOTICE - LUWA TECH*\n\n"
    "Hello *{partner_name}*,\n"
    "Your active *Luwa Tech* subscription is scheduled for renewal so your service continues seamlessly:\n\n"
    "- *Package / Plan:* {plan_name}\n"
    "- *Subscription Ref:* {record_name}\n"
    "- *Renewal Amount:* {currency} {amount}\n"
    "- *Renewal Date:* {due_date}\n\n"
    "*Manage Subscription & Invoices:*\n"
    "{portal_url}\n\n"
    "Reply here on WhatsApp if you would like to renew via Mobile Money or upgrade your package.\n\n"
    "*Luwa Tech Customer Success*\n"
    "Tel: +256 787 819 453 | https://www.luwatech.it"
)


class SafeFormatDict(dict):
    def __missing__(self, key):
        return ""


class LuwaWhatsappConfig(models.Model):
    _name = "luwa.whatsapp.config"
    _description = "Luwa Tech WhatsApp Engine Configuration"

    name = fields.Char(default="Luwa Tech WhatsApp Engine", required=True)
    bridge_url = fields.Char(
        string="Bridge Service URL",
        default="http://127.0.0.1:3010",
        required=True,
        help="Dedicated isolated Luwa Tech Baileys service on loopback port 3010 (separate from Munig on 3000).",
    )
    api_token = fields.Char(
        string="Bridge Auth Token",
        default="luwa-wa-local-2026",
        required=True,
    )
    connection_state = fields.Selection(
        [
            ("disconnected", "Disconnected"),
            ("qr_pending", "Waiting for QR Scan"),
            ("connected", "Connected"),
        ],
        string="Connection Status",
        default="disconnected",
        readonly=True,
    )
    connected_phone = fields.Char(string="Linked WhatsApp Number", readonly=True)
    connected_name = fields.Char(string="WhatsApp Account Name", readonly=True)
    queue_len = fields.Integer(string="Queued in Bridge", readonly=True)
    last_error = fields.Char(string="Last Bridge Error", readonly=True)
    last_sync_at = fields.Datetime(string="Last Synced", readonly=True)
    qr_image = fields.Binary(string="WhatsApp QR Code", attachment=False, readonly=True)

    # Automation rules
    auto_attach_pdf = fields.Boolean(
        string="Attach Official PDF Document (Quotes, Orders & Invoices)",
        default=True,
        help="Automatically renders and attaches the official Odoo PDF document directly in WhatsApp along with a secure download link.",
    )
    auto_crm_ack = fields.Boolean(
        string="Auto-Reply to New Website CRM Leads",
        default=True,
    )
    auto_order_confirm = fields.Boolean(
        string="Auto-Send Sale Order Confirmations",
        default=True,
    )
    auto_quote_reminder = fields.Boolean(
        string="Auto-Remind Open Quotations",
        default=True,
    )
    quote_reminder_days = fields.Integer(
        string="Quote Reminder Delay (Days)",
        default=2,
    )
    auto_invoice_reminder = fields.Boolean(
        string="Auto-Send Unpaid Invoice Payment Reminders",
        default=True,
    )
    invoice_reminder_days = fields.Integer(
        string="Invoice Reminder Interval (Days)",
        default=3,
    )
    auto_subscription_reminder = fields.Boolean(
        string="Auto-Send Subscription Renewal Reminders",
        default=True,
    )
    subscription_reminder_days = fields.Integer(
        string="Remind Before Renewal (Days)",
        default=3,
    )

    # Templates
    tpl_crm_ack = fields.Text(
        string="CRM Lead Auto-Reply Template",
        default=DEFAULT_TPL_CRM_ACK,
    )
    tpl_order_confirm = fields.Text(
        string="Order Confirmation Template",
        default=DEFAULT_TPL_ORDER_CONFIRM,
    )
    tpl_quote_reminder = fields.Text(
        string="Quotation Follow-up Template",
        default=DEFAULT_TPL_QUOTE_REMINDER,
    )
    tpl_invoice_reminder = fields.Text(
        string="Payment Reminder Template",
        default=DEFAULT_TPL_INVOICE_REMINDER,
    )
    tpl_subscription_reminder = fields.Text(
        string="Subscription Renewal Template",
        default=DEFAULT_TPL_SUBSCRIPTION_REMINDER,
    )

    # Quick Test
    test_phone = fields.Char(string="Test Recipient Phone")
    test_message = fields.Text(
        string="Test Message",
        default=(
            "*LUWA TECH WHATSAPP ENGINE*\n\n"
            "Your QR-linked WhatsApp automation is connected and ready to send direct messages and PDF documents!"
        ),
    )
    message_count = fields.Integer(string="Total Messages", compute="_compute_message_count")
    campaign_count = fields.Integer(string="Campaigns", compute="_compute_message_count")
    campaign_ids = fields.Many2many("luwa.whatsapp.campaign", compute="_compute_message_count", string="Marketing Campaigns")
    sent_last_minute = fields.Integer(string="Sent (Last 1 Min)", readonly=True)
    sent_last_hour = fields.Integer(string="Sent (Last 1 Hour)", readonly=True)
    sent_last_24h = fields.Integer(string="Sent (Last 24 Hours)", readonly=True)

    def _compute_message_count(self):
        count = self.env["luwa.whatsapp.message"].sudo().search_count([])
        camps = self.env["luwa.whatsapp.campaign"].sudo().search([], order="id desc", limit=25)
        for rec in self:
            rec.message_count = count
            rec.campaign_count = len(camps)
            rec.campaign_ids = camps

    @api.model
    def get_solo(self):
        cfg = self.sudo().search([], limit=1)
        if not cfg:
            cfg = self.sudo().create({"name": "Luwa Tech WhatsApp Engine"})
        return cfg

    def action_reset_premium_templates(self):
        self.ensure_one()
        self.sudo().write({
            "tpl_crm_ack": DEFAULT_TPL_CRM_ACK,
            "tpl_order_confirm": DEFAULT_TPL_ORDER_CONFIRM,
            "tpl_quote_reminder": DEFAULT_TPL_QUOTE_REMINDER,
            "tpl_invoice_reminder": DEFAULT_TPL_INVOICE_REMINDER,
            "tpl_subscription_reminder": DEFAULT_TPL_SUBSCRIPTION_REMINDER,
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Templates Updated"),
                "message": _("Executive WhatsApp templates with PDF & portal links have been loaded."),
                "type": "success",
                "sticky": False,
            },
        }

    def _get_public_base_url(self):
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url") or "https://www.luwatech.it"
        if "localhost" in base or "127.0.0.1" in base:
            base = "https://www.luwatech.it"
        return base.rstrip("/")

    def _extract_record_pdf_and_link(self, res_model, res_id, include_pdf=True):
        """Return dict with portal_url, document_b64, filename, mimetype for sale.order, account.move, or luwa.subscription."""
        base_url = self._get_public_base_url()
        info = {
            "portal_url": f"{base_url}/my/home",
            "document_b64": False,
            "filename": False,
            "mimetype": "application/pdf",
        }
        if not res_model or not res_id:
            return info
        try:
            rec = self.env[res_model].sudo().browse(int(res_id))
            if not rec.exists():
                return info

            pdf_target_model = None
            pdf_target_rec = None

            if res_model == "sale.order":
                try:
                    rec._portal_ensure_token()
                    info["portal_url"] = f"{base_url}{rec.get_portal_url(report_type='pdf', download=True)}"
                except Exception:
                    info["portal_url"] = f"{base_url}/my/orders/{rec.id}"
                pdf_target_model = "sale.order"
                pdf_target_rec = rec

            elif res_model == "account.move" and rec.move_type in ("out_invoice", "out_refund"):
                try:
                    rec._portal_ensure_token()
                    info["portal_url"] = f"{base_url}{rec.get_portal_url(report_type='pdf', download=True)}"
                except Exception:
                    info["portal_url"] = f"{base_url}/my/invoices/{rec.id}"
                pdf_target_model = "account.move"
                pdf_target_rec = rec

            elif res_model == "luwa.subscription":
                info["portal_url"] = f"{base_url}/my/home"
                if getattr(rec, "invoice_ids", False):
                    posted_invs = rec.invoice_ids.filtered(lambda m: m.state == "posted")
                    if posted_invs:
                        latest_inv = posted_invs.sorted("id", reverse=True)[0]
                        try:
                            latest_inv._portal_ensure_token()
                            info["portal_url"] = f"{base_url}{latest_inv.get_portal_url(report_type='pdf', download=True)}"
                        except Exception:
                            pass
                        pdf_target_model = "account.move"
                        pdf_target_rec = latest_inv
                if not pdf_target_rec and getattr(rec, "sale_order_id", False):
                    so = rec.sale_order_id
                    try:
                        so._portal_ensure_token()
                        info["portal_url"] = f"{base_url}{so.get_portal_url(report_type='pdf', download=True)}"
                    except Exception:
                        pass
                    pdf_target_model = "sale.order"
                    pdf_target_rec = so

            if include_pdf and pdf_target_rec:
                report_ref = (
                    "sale.action_report_saleorder"
                    if pdf_target_model == "sale.order"
                    else "account.account_invoices"
                )
                pdf_bytes, _ = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
                    report_ref, [pdf_target_rec.id]
                )
                if pdf_bytes:
                    raw_ref = pdf_target_rec.name if (pdf_target_rec.name and pdf_target_rec.name != "/") else f"DRAFT-{pdf_target_rec.id:04d}"
                    safe_ref = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_ref).strip("-")
                    prefix = (
                        "Quotation"
                        if pdf_target_model == "sale.order" and pdf_target_rec.state in ("draft", "sent")
                        else ("Order" if pdf_target_model == "sale.order" else "Invoice")
                    )
                    info["document_b64"] = base64.b64encode(pdf_bytes).decode("ascii")
                    info["filename"] = f"LuwaTech-{prefix}-{safe_ref}.pdf"
        except Exception as exc:
            _logger.warning("Could not generate PDF/portal link for %s,%s: %s", res_model, res_id, exc)
        return info

    def _bridge_request(self, method, path, payload=None, timeout=18):
        self.ensure_one()
        base = (self.bridge_url or "http://127.0.0.1:3010").rstrip("/")
        url = f"{base}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "X-Luwa-Token": self.api_token or "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        req = Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8") or "{}"
                return json.loads(raw)
        except HTTPError as err:
            raw = err.read().decode("utf-8", errors="replace")
            try:
                return json.loads(raw)
            except Exception:
                return {"ok": False, "error": f"HTTP {err.code}: {raw[:200]}"}
        except (URLError, TimeoutError, OSError) as err:
            return {"ok": False, "error": str(err)}

    def _sync_from_bridge(self):
        self.ensure_one()
        status = self._bridge_request("GET", "/status", timeout=8)
        now = fields.Datetime.now()
        if not status.get("ok"):
            self.sudo().write({
                "connection_state": "disconnected",
                "last_error": status.get("error") or "Bridge unreachable",
                "last_sync_at": now,
            })
            return status

        connected = bool(status.get("connected"))
        qr_pending = bool(status.get("qr_pending"))
        vals = {
            "connection_state": "connected" if connected else ("qr_pending" if qr_pending else "disconnected"),
            "connected_phone": status.get("phone") or "",
            "connected_name": status.get("name") or "",
            "queue_len": int(status.get("queue_len") or 0),
            "last_error": status.get("last_error") or "",
            "last_sync_at": now,
            "sent_last_minute": int((status.get("anti_ban") or {}).get("sent_last_minute") or 0),
            "sent_last_hour": int((status.get("anti_ban") or {}).get("sent_last_hour") or 0),
            "sent_last_24h": int((status.get("anti_ban") or {}).get("sent_last_24h") or 0),
        }
        if connected:
            vals["qr_image"] = False
        elif qr_pending:
            qr_res = self._bridge_request("GET", "/qr-data", timeout=8)
            if qr_res.get("qr_png_b64"):
                vals["qr_image"] = qr_res["qr_png_b64"]
        self.sudo().write(vals)
        return status

    def action_refresh_status(self):
        for rec in self:
            rec._sync_from_bridge()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_force_new_qr(self):
        for rec in self:
            res = rec._bridge_request("POST", "/refresh-qr", payload={}, timeout=10)
            if not res.get("ok"):
                raise UserError(_("Could not refresh QR code: %s") % (res.get("error") or "Unknown error"))
            rec._sync_from_bridge()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_logout_whatsapp(self):
        for rec in self:
            res = rec._bridge_request("POST", "/logout", payload={}, timeout=10)
            if not res.get("ok"):
                raise UserError(_("Could not disconnect WhatsApp: %s") % (res.get("error") or "Unknown error"))
            rec._sync_from_bridge()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_open_campaigns(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("WhatsApp Marketing Campaigns (Anti-Ban)"),
            "res_model": "luwa.whatsapp.campaign",
            "view_mode": "list,form",
            "target": "current",
        }

    def action_new_campaign(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("New Anti-Ban WhatsApp Campaign"),
            "res_model": "luwa.whatsapp.campaign",
            "view_mode": "form",
            "target": "current",
        }

    def action_view_messages(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("WhatsApp Message Logs"),
            "res_model": "luwa.whatsapp.message",
            "view_mode": "list,form",
            "target": "current",
        }

    def action_send_test_message(self):
        self.ensure_one()
        if not self.test_phone or not self.test_message:
            raise UserError(_("Please fill in both Test Recipient Phone and Test Message."))
        log = self.send_whatsapp_message(
            phone=self.test_phone,
            message=self.test_message,
            trigger_type="test",
            queue_if_offline=False,
        )
        if log.state == "failed":
            raise UserError(_("Failed to send test WhatsApp message: %s") % (log.error_message or "Unknown error"))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WhatsApp Sent"),
                "message": _("Message delivered to %s") % (log.normalized_phone or self.test_phone),
                "type": "success",
                "sticky": False,
            },
        }

    def action_run_automations_now(self):
        self.ensure_one()
        status = self._sync_from_bridge()
        if not status.get("connected"):
            raise UserError(_("WhatsApp is not connected yet. Scan the QR code first, then run automations."))
        sent_count = self._run_automated_reminders()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Automations Completed"),
                "message": _("%s automated WhatsApp reminder(s) processed.") % sent_count,
                "type": "success",
                "sticky": False,
            },
        }

    def _format_template(self, template_text, **kwargs):
        data = SafeFormatDict({k: ("" if v is False or v is None else v) for k, v in kwargs.items()})
        try:
            return (template_text or "").format_map(data).strip()
        except Exception as exc:
            _logger.warning("Template formatting fallback (%s): %s", exc, template_text)
            return (template_text or "").strip()

    def send_whatsapp_message(
        self,
        phone,
        message,
        partner=None,
        res_model=False,
        res_id=0,
        trigger_type="manual",
        queue_if_offline=True,
        document_b64=False,
        filename=False,
        mimetype="application/pdf",
        auto_pdf=None,
        skip_if_unregistered=False,
    ):
        self.ensure_one()
        clean_phone = (phone or "").strip()
        body = (message or "").replace("\u00e2\u20ac\u201d", "-").replace("\u00e2\u20ac\u00a2", "-").replace("\u2014", "-").replace("\u2022", "-").strip()

        should_auto_pdf = self.auto_attach_pdf if auto_pdf is None else bool(auto_pdf)
        if not document_b64 and should_auto_pdf and res_model in ("sale.order", "account.move", "luwa.subscription") and res_id:
            doc_info = self._extract_record_pdf_and_link(res_model, res_id, include_pdf=True)
            if doc_info.get("document_b64"):
                document_b64 = doc_info["document_b64"]
                filename = doc_info.get("filename") or "LuwaTech-Document.pdf"
                mimetype = doc_info.get("mimetype") or "application/pdf"

        log_vals = {
            "recipient_phone": clean_phone,
            "partner_id": partner.id if partner else False,
            "trigger_type": trigger_type,
            "body": body,
            "attachment_name": filename or "",
            "res_model": res_model or False,
            "res_id": int(res_id or 0),
        }

        if not clean_phone or (not body and not document_b64):
            log_vals.update({
                "state": "failed",
                "error_message": "Missing recipient phone or message body.",
            })
            return self.env["luwa.whatsapp.message"].sudo().create(log_vals)

        payload = {
            "phone": clean_phone,
            "message": body,
            "queue_if_offline": bool(queue_if_offline),
            "skip_if_unregistered": bool(skip_if_unregistered),
        }
        if document_b64:
            payload.update({
                "document_b64": document_b64,
                "filename": filename or "LuwaTech-Document.pdf",
                "mimetype": mimetype or "application/pdf",
            })

        res = self._bridge_request(
            "POST",
            "/send",
            payload=payload,
            timeout=20,
        )
        if res.get("ok"):
            state = "queued" if res.get("queued") else "sent"
            log_vals.update({
                "state": state,
                "normalized_phone": res.get("phone") or clean_phone,
                "error_message": "",
            })
        else:
            log_vals.update({
                "state": "failed",
                "error_message": res.get("error") or "Unknown bridge error",
            })

        log = self.env["luwa.whatsapp.message"].sudo().create(log_vals)

        if res_model and res_id and log.state in ("sent", "queued"):
            try:
                rec = self.env[res_model].sudo().browse(int(res_id))
                if rec.exists() and hasattr(rec, "message_post"):
                    status_label = _("queued") if log.state == "queued" else _("sent")
                    att_note = f" [Attached: {filename}]" if filename else ""
                    rec.message_post(
                        body=_("WhatsApp (%s)%s to %s:\n%s")
                        % (status_label, att_note, log.normalized_phone or clean_phone, body)
                    )
            except Exception as exc:
                _logger.warning("Failed to post WhatsApp chatter note on %s,%s: %s", res_model, res_id, exc)
        return log

    @api.model
    def _cron_run_whatsapp_automations(self):
        cfg = self.get_solo()
        status = cfg._sync_from_bridge()
        if not status.get("connected"):
            _logger.info("Luwa WhatsApp cron skipped: WhatsApp number not connected yet.")
            return
        cfg._run_automated_reminders()

    def _run_automated_reminders(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        now = fields.Datetime.now()
        sent_count = 0

        # 1. Open Quotations Follow-up (with PDF attachment + online portal link)
        if self.auto_quote_reminder:
            delay_days = max(1, int(self.quote_reminder_days or 2))
            cutoff_created = now - timedelta(days=delay_days)
            window_start = now - timedelta(days=60)
            remind_cutoff = today - timedelta(days=delay_days)
            quotes = self.env["sale.order"].sudo().search([
                ("state", "in", ["draft", "sent"]),
                ("create_date", "<=", cutoff_created),
                ("create_date", ">=", window_start),
                "|",
                ("luwa_last_wa_reminder_date", "=", False),
                ("luwa_last_wa_reminder_date", "<=", remind_cutoff),
            ], limit=15)
            for quote in quotes:
                phone = quote.partner_id.phone
                if not phone:
                    continue
                doc_info = self._extract_record_pdf_and_link("sale.order", quote.id, include_pdf=self.auto_attach_pdf)
                msg = self._format_template(
                    self.tpl_quote_reminder,
                    partner_name=quote.partner_id.name or "Valued Client",
                    record_name=quote.name,
                    amount=f"{quote.amount_total:,.0f}",
                    currency=quote.currency_id.name or "",
                    due_date=str(quote.validity_date or "Open"),
                    portal_url=doc_info["portal_url"],
                )
                log = self.send_whatsapp_message(
                    phone=phone,
                    message=msg,
                    partner=quote.partner_id,
                    res_model="sale.order",
                    res_id=quote.id,
                    trigger_type="quote_reminder",
                    queue_if_offline=False,
                    document_b64=doc_info["document_b64"],
                    filename=doc_info["filename"],
                    auto_pdf=False,
                )
                if log.state == "sent":
                    quote.luwa_last_wa_reminder_date = today
                    sent_count += 1

        # 2. Unpaid / Overdue Customer Invoices (with PDF attachment + online portal link)
        if self.auto_invoice_reminder:
            interval_days = max(1, int(self.invoice_reminder_days or 3))
            remind_cutoff = today - timedelta(days=interval_days)
            min_due_date = today - timedelta(days=90)
            invoices = self.env["account.move"].sudo().search([
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "in", ["not_paid", "partial"]),
                ("amount_residual", ">", 0),
                ("invoice_date_due", "<=", today),
                ("invoice_date_due", ">=", min_due_date),
                "|",
                ("luwa_last_wa_reminder_date", "=", False),
                ("luwa_last_wa_reminder_date", "<=", remind_cutoff),
            ], limit=20)
            for inv in invoices:
                phone = inv.partner_id.phone
                if not phone:
                    continue
                doc_info = self._extract_record_pdf_and_link("account.move", inv.id, include_pdf=self.auto_attach_pdf)
                msg = self._format_template(
                    self.tpl_invoice_reminder,
                    partner_name=inv.partner_id.name or "Valued Client",
                    record_name=(inv.name if (inv.name and inv.name != "/") else f"DRAFT-INV-{inv.id:04d}"),
                    amount=f"{inv.amount_residual:,.0f}",
                    currency=inv.currency_id.name or "",
                    due_date=str(inv.invoice_date_due or today),
                    portal_url=doc_info["portal_url"],
                )
                log = self.send_whatsapp_message(
                    phone=phone,
                    message=msg,
                    partner=inv.partner_id,
                    res_model="account.move",
                    res_id=inv.id,
                    trigger_type="invoice_reminder",
                    queue_if_offline=False,
                    document_b64=doc_info["document_b64"],
                    filename=doc_info["filename"],
                    auto_pdf=False,
                )
                if log.state == "sent":
                    inv.luwa_last_wa_reminder_date = today
                    sent_count += 1

        # 3. Subscription Renewals (with latest Invoice/Order PDF + portal link)
        if self.auto_subscription_reminder:
            lead_days = max(1, int(self.subscription_reminder_days or 3))
            due_horizon = today + timedelta(days=lead_days)
            remind_cutoff = today - timedelta(days=lead_days)
            subs = self.env["luwa.subscription"].sudo().search([
                ("state", "=", "active"),
                ("next_billing_date", "!=", False),
                ("next_billing_date", "<=", due_horizon),
                "|",
                ("luwa_last_wa_reminder_date", "=", False),
                ("luwa_last_wa_reminder_date", "<=", remind_cutoff),
            ], limit=20)
            for sub in subs:
                phone = sub.partner_phone or sub.partner_id.phone
                if not phone:
                    continue
                doc_info = self._extract_record_pdf_and_link("luwa.subscription", sub.id, include_pdf=self.auto_attach_pdf)
                msg = self._format_template(
                    self.tpl_subscription_reminder,
                    partner_name=sub.partner_id.name or "Valued Client",
                    record_name=sub.name,
                    plan_name=sub.plan_id.name or sub.product_tmpl_id.name or "Subscription",
                    amount=f"{sub.recurring_amount:,.0f}",
                    currency=sub.currency_id.name or "",
                    due_date=str(sub.next_billing_date or ""),
                    portal_url=doc_info["portal_url"],
                )
                log = self.send_whatsapp_message(
                    phone=phone,
                    message=msg,
                    partner=sub.partner_id,
                    res_model="luwa.subscription",
                    res_id=sub.id,
                    trigger_type="subscription_reminder",
                    queue_if_offline=False,
                    document_b64=doc_info["document_b64"],
                    filename=doc_info["filename"],
                    auto_pdf=False,
                )
                if log.state == "sent":
                    sub.luwa_last_wa_reminder_date = today
                    sent_count += 1

        return sent_count


class LuwaWhatsappMessage(models.Model):
    _name = "luwa.whatsapp.message"
    _description = "Luwa Tech WhatsApp Message Log"
    _order = "id desc"

    recipient_phone = fields.Char(string="Input Phone", readonly=True)
    normalized_phone = fields.Char(string="WhatsApp Number", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Customer", readonly=True)
    trigger_type = fields.Selection(
        [
            ("manual", "Manual Send"),
            ("test", "Test Message"),
            ("campaign", "Marketing Campaign"),
            ("crm_ack", "CRM Lead Auto-Reply"),
            ("order_confirm", "Order Confirmation"),
            ("quote_reminder", "Quotation Reminder"),
            ("invoice_reminder", "Payment Reminder"),
            ("subscription_reminder", "Subscription Renewal"),
        ],
        string="Trigger",
        default="manual",
        readonly=True,
    )
    attachment_name = fields.Char(string="Attached PDF / File", readonly=True)
    body = fields.Text(string="Message", readonly=True)
    state = fields.Selection(
        [
            ("sent", "Sent"),
            ("queued", "Queued (Waiting for QR)"),
            ("failed", "Failed"),
        ],
        string="Status",
        default="queued",
        readonly=True,
    )
    error_message = fields.Char(string="Error", readonly=True)
    res_model = fields.Char(string="Related Model", readonly=True)
    res_id = fields.Integer(string="Related Record ID", readonly=True)
    record_ref = fields.Char(string="Record Reference", compute="_compute_record_ref")

    @api.depends("res_model", "res_id")
    def _compute_record_ref(self):
        for rec in self:
            if rec.res_model and rec.res_id:
                try:
                    target = self.env[rec.res_model].sudo().browse(rec.res_id)
                    rec.record_ref = target.display_name if target.exists() else f"{rec.res_model},{rec.res_id}"
                except Exception:
                    rec.record_ref = f"{rec.res_model},{rec.res_id}"
            else:
                rec.record_ref = ""
