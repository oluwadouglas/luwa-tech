# -*- coding: utf-8 -*-
import logging
import random
import re
import time
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

GREETINGS_POOL = [
    "Hello",
    "Hi",
    "Greetings",
    "Good day",
]


def _normalize_ug_phone(raw_phone):
    digits = re.sub(r"[^\d]", "", str(raw_phone or ""))
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 10:
        digits = "256" + digits[1:]
    elif len(digits) == 9 and digits.startswith("7"):
        digits = "256" + digits
    return digits if len(digits) >= 9 else ""


class LuwaWhatsappCampaign(models.Model):
    _name = "luwa.whatsapp.campaign"
    _description = "Luwa Tech Anti-Ban Bulk WhatsApp Campaign"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Campaign Title",
        required=True,
        default="Luwa Tech Digital Growth Campaign",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("ready", "Recipients Queued"),
            ("running", "Running (Safe Anti-Ban Trickle)"),
            ("paused", "Paused"),
            ("done", "Completed"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )
    audience_source = fields.Selection(
        [
            ("mixed", "Selected Contacts + Pasted Phone Numbers"),
            ("crm_leads", "All CRM Leads / Inquiries (with Phone)"),
            ("customers", "All Contacts / Customers (with Phone)"),
            ("custom_numbers", "Pasted Phone Numbers Only"),
        ],
        string="Target Audience Source",
        default="mixed",
        required=True,
    )
    partner_ids = fields.Many2many(
        "res.partner",
        "luwa_wa_campaign_partner_rel",
        "campaign_id",
        "partner_id",
        string="Selected Contacts",
    )
    raw_numbers = fields.Text(
        string="Paste Bulk Phone Numbers",
        help="Enter one per line or comma-separated. You can also enter 'Name, Phone' per line (e.g. 'John Mukasa, 0772123456').",
    )

    # Anti-Ban Safety Settings
    batch_size = fields.Integer(
        string="Messages Per 5-Min Batch",
        default=6,
        help="Safe trickle batch size processed every 5 minutes (recommended: 4 to 8 messages per batch).",
    )
    min_delay_sec = fields.Integer(
        string="Min Delay Between Messages (Sec)",
        default=12,
        help="Minimum randomized human pause between consecutive messages.",
    )
    max_delay_sec = fields.Integer(
        string="Max Delay Between Messages (Sec)",
        default=26,
        help="Maximum randomized human pause between consecutive messages.",
    )
    daily_limit = fields.Integer(
        string="Max Campaign Messages / 24h",
        default=160,
        help="Hard daily cap to protect your WhatsApp reputation (recommended: 120 to 200 per day).",
    )
    use_greeting_variation = fields.Boolean(
        string="Anti-Ban Dynamic Greeting Variation",
        default=True,
        help="Automatically varies {greeting} (Hello / Hi / Greetings / Good day) and personalizes {partner_name} so messages never look identical.",
    )
    skip_unregistered = fields.Boolean(
        string="Skip Numbers Not Registered on WhatsApp",
        default=True,
        help="Checks WhatsApp registration before sending so invalid numbers are skipped safely without hurting account score.",
    )

    # Content & Attachment
    attachment_file = fields.Binary(string="Attach PDF Flyer / Brochure (Optional)")
    attachment_name = fields.Char(string="Attachment Filename")
    message_template = fields.Text(
        string="Campaign Message Template",
        required=True,
        default=(
            "*LUWA TECH - KAMPALA DIGITAL GROWTH STUDIO*\n\n"
            "{greeting} *{partner_name}*,\n"
            "Are you looking to grow your sales with a modern Online Store (MTN MoMo, Airtel Money & URA EFRIS ready), "
            "WhatsApp Business Automation, or a monthly Digital Marketing retainer?\n\n"
            "- *E-Commerce & Custom Web Apps*\n"
            "- *Automated WhatsApp & CRM Systems*\n"
            "- *Performance Digital Marketing*\n\n"
            "Explore our plans at:\n"
            "https://www.luwatech.it/subscriptions\n\n"
            "Reply *\"INFO\"* here on WhatsApp to book a free strategy call with our Kampala team!\n\n"
            "_Reply STOP to opt out of campaign updates._"
        ),
    )

    line_ids = fields.One2many("luwa.whatsapp.campaign.line", "campaign_id", string="Recipients Queue")
    total_count = fields.Integer(compute="_compute_stats", string="Total Recipients")
    pending_count = fields.Integer(compute="_compute_stats", string="Pending")
    sent_count = fields.Integer(compute="_compute_stats", string="Sent")
    skipped_count = fields.Integer(compute="_compute_stats", string="Skipped")
    failed_count = fields.Integer(compute="_compute_stats", string="Failed")
    progress_pct = fields.Float(compute="_compute_stats", string="Progress (%)")
    last_batch_at = fields.Datetime(string="Last Batch Sent At", readonly=True)

    @api.depends("line_ids.state")
    def _compute_stats(self):
        for rec in self:
            lines = rec.line_ids
            total = len(lines)
            pending = len(lines.filtered(lambda l: l.state == "pending"))
            sent = len(lines.filtered(lambda l: l.state == "sent"))
            skipped = len(lines.filtered(lambda l: l.state == "skipped"))
            failed = len(lines.filtered(lambda l: l.state == "failed"))
            rec.total_count = total
            rec.pending_count = pending
            rec.sent_count = sent
            rec.skipped_count = skipped
            rec.failed_count = failed
            done_count = sent + skipped + failed
            rec.progress_pct = round((done_count / total) * 100.0, 1) if total else 0.0

    def action_build_recipient_list(self):
        self.ensure_one()
        existing_by_norm = {l.normalized_phone: l for l in self.line_ids if l.normalized_phone}
        new_lines = []
        seen = set(existing_by_norm.keys())

        def _add_candidate(name, phone_raw, partner=False):
            norm = _normalize_ug_phone(phone_raw)
            if not norm or norm in seen:
                return
            seen.add(norm)
            new_lines.append({
                "campaign_id": self.id,
                "partner_id": partner.id if partner else False,
                "recipient_name": (name or (partner.name if partner else "") or "Valued Client").strip(),
                "phone": str(phone_raw).strip(),
                "normalized_phone": norm,
                "state": "pending",
            })

        if self.audience_source in ("mixed", "customers"):
            partners = (
                self.partner_ids
                if self.audience_source == "mixed"
                else self.env["res.partner"].sudo().search([("phone", "!=", False)], limit=1000)
            )
            for p in partners:
                if p.phone:
                    _add_candidate(p.name, p.phone, partner=p)

        if self.audience_source == "crm_leads":
            leads = self.env["crm.lead"].sudo().search([], limit=1000)
            for lead in leads:
                ph = lead.phone or (lead.partner_id.phone if lead.partner_id else "")
                nm = lead.contact_name or (lead.partner_id.name if lead.partner_id else "") or lead.name
                if ph:
                    _add_candidate(nm, ph, partner=lead.partner_id)

        if self.audience_source in ("mixed", "custom_numbers") and self.raw_numbers:
            for raw_line in (self.raw_numbers or "").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if "," in line and not re.match(r"^[\d+\s,-]+$", line):
                    parts = [p.strip() for p in line.split(",", 1)]
                    _add_candidate(parts[0], parts[1])
                else:
                    for token in re.split(r"[,;]+", line):
                        if token.strip():
                            _add_candidate("Valued Client", token.strip())

        if new_lines:
            self.env["luwa.whatsapp.campaign.line"].sudo().create(new_lines)

        if not self.line_ids:
            raise UserError(_("No valid phone numbers found. Select contacts or paste phone numbers first."))

        if self.state == "draft":
            self.state = "ready"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Audience Ready"),
                "message": _("%s new unique recipient(s) added (%s total in campaign).") % (len(new_lines), len(self.line_ids)),
                "type": "success",
                "sticky": False,
            },
        }

    def action_start_campaign(self):
        self.ensure_one()
        if not self.line_ids:
            self.action_build_recipient_list()
        if not self.line_ids.filtered(lambda l: l.state == "pending"):
            raise UserError(_("All recipients in this campaign have already been processed."))
        cfg = self.env["luwa.whatsapp.config"].get_solo()
        status = cfg._sync_from_bridge()
        if not status.get("connected"):
            raise UserError(_("Your WhatsApp number is not connected. Check QR Pairing & Automation first."))
        self.state = "running"
        # Immediately process a safe initial mini-batch (up to 3 messages) so the user sees instant progress
        sent_now = self._process_batch(max_Override=min(3, max(1, self.batch_size)))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Anti-Ban Campaign Running"),
                "message": _(
                    "Started! %s initial message(s) sent safely. Remaining %s recipient(s) will trickle automatically every 5 minutes."
                )
                % (sent_now, self.pending_count),
                "type": "success",
                "sticky": False,
            },
        }

    def action_send_next_batch_now(self):
        self.ensure_one()
        cfg = self.env["luwa.whatsapp.config"].get_solo()
        status = cfg._sync_from_bridge()
        if not status.get("connected"):
            raise UserError(_("WhatsApp is not connected."))
        count = self._process_batch(max_Override=min(5, max(1, self.batch_size)))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Safe Batch Processed"),
                "message": _("%s recipient(s) processed with anti-ban pacing (%s still pending).") % (count, self.pending_count),
                "type": "success",
                "sticky": False,
            },
        }

    def action_pause_campaign(self):
        self.write({"state": "paused"})

    def action_reset_draft(self):
        for rec in self:
            rec.line_ids.filtered(lambda l: l.state in ("failed", "skipped")).write({"state": "pending", "error_message": False})
            rec.state = "ready" if rec.line_ids else "draft"

    def _render_line_message(self, line, index_offset=0):
        self.ensure_one()
        cfg = self.env["luwa.whatsapp.config"].get_solo()
        greeting = (
            GREETINGS_POOL[index_offset % len(GREETINGS_POOL)]
            if self.use_greeting_variation
            else "Hello"
        )
        return cfg._format_template(
            self.message_template,
            greeting=greeting,
            partner_name=line.recipient_name or "Valued Client",
            record_name=self.name,
            portal_url="https://www.luwatech.it/subscriptions",
        )

    def _process_batch(self, max_Override=None):
        self.ensure_one()
        cfg = self.env["luwa.whatsapp.config"].get_solo()

        # Enforce 24-hour anti-ban daily cap
        day_ago = fields.Datetime.now() - timedelta(hours=24)
        sent_24h = self.env["luwa.whatsapp.message"].sudo().search_count([
            ("trigger_type", "=", "campaign"),
            ("state", "=", "sent"),
            ("create_date", ">=", day_ago),
        ])
        daily_cap = max(10, int(self.daily_limit or 160))
        if sent_24h >= daily_cap:
            _logger.info("Luwa WhatsApp campaign '%s' paused for 24h safety cap (%s/%s).", self.name, sent_24h, daily_cap)
            return 0

        limit = min(
            int(max_Override or self.batch_size or 6),
            max(1, daily_cap - sent_24h),
        )
        pending_lines = self.line_ids.filtered(lambda l: l.state == "pending")[:limit]
        if not pending_lines:
            self.state = "done"
            return 0

        doc_b64 = (
            self.attachment_file.decode("ascii")
            if isinstance(self.attachment_file, bytes)
            else (self.attachment_file or False)
        )
        min_d = max(3, int(self.min_delay_sec or 12))
        max_d = max(min_d + 1, int(self.max_delay_sec or 26))
        # When triggered interactively inside an HTTP request, cap per-step sleep to 4s so request never times out
        is_interactive = bool(max_Override is not None)

        processed = 0
        for idx, line in enumerate(pending_lines):
            if idx > 0:
                pause_sec = random.uniform(2.0, 4.0) if is_interactive else random.uniform(min_d, max_d)
                time.sleep(pause_sec)

            body = self._render_line_message(line, index_offset=self.sent_count + idx)
            res = cfg._bridge_request(
                "POST",
                "/send",
                payload={
                    "phone": line.normalized_phone or line.phone,
                    "message": body,
                    "document_b64": doc_b64 or False,
                    "filename": self.attachment_name or "LuwaTech-Brochure.pdf",
                    "mimetype": "application/pdf",
                    "queue_if_offline": False,
                    "skip_if_unregistered": bool(self.skip_unregistered),
                    "simulate_typing": True,
                },
                timeout=25,
            )

            now = fields.Datetime.now()
            if res.get("ok"):
                line.sudo().write({
                    "state": "sent",
                    "sent_at": now,
                    "error_message": "",
                })
                self.env["luwa.whatsapp.message"].sudo().create({
                    "recipient_phone": line.phone,
                    "normalized_phone": res.get("phone") or line.normalized_phone,
                    "partner_id": line.partner_id.id if line.partner_id else False,
                    "trigger_type": "campaign",
                    "attachment_name": self.attachment_name or "",
                    "body": body,
                    "state": "sent",
                    "res_model": "luwa.whatsapp.campaign",
                    "res_id": self.id,
                })
                processed += 1
            elif res.get("skipped_unregistered"):
                line.sudo().write({
                    "state": "skipped",
                    "sent_at": now,
                    "error_message": "Not registered on WhatsApp",
                })
                processed += 1
            else:
                line.sudo().write({
                    "state": "failed",
                    "sent_at": now,
                    "error_message": res.get("error") or "Send failed",
                })

            self.env.cr.commit()

        self.last_batch_at = fields.Datetime.now()
        if not self.line_ids.filtered(lambda l: l.state == "pending"):
            self.state = "done"
        self.env.cr.commit()
        return processed

    @api.model
    def _cron_process_running_campaigns(self):
        cfg = self.env["luwa.whatsapp.config"].get_solo()
        status = cfg._sync_from_bridge()
        if not status.get("connected"):
            return
        running = self.sudo().search([("state", "=", "running")], order="id asc", limit=2)
        for camp in running:
            camp._process_batch()


class LuwaWhatsappCampaignLine(models.Model):
    _name = "luwa.whatsapp.campaign.line"
    _description = "Luwa Tech WhatsApp Campaign Recipient"
    _order = "id asc"

    campaign_id = fields.Many2one("luwa.whatsapp.campaign", required=True, ondelete="cascade")
    partner_id = fields.Many2one("res.partner", string="Contact")
    recipient_name = fields.Char(string="Recipient Name")
    phone = fields.Char(string="Input Phone", required=True)
    normalized_phone = fields.Char(string="WhatsApp Number", index=True)
    state = fields.Selection(
        [
            ("pending", "Pending in Queue"),
            ("sent", "Sent"),
            ("skipped", "Skipped (Not on WhatsApp)"),
            ("failed", "Failed"),
        ],
        string="Status",
        default="pending",
    )
    sent_at = fields.Datetime(string="Processed At", readonly=True)
    error_message = fields.Char(string="Note / Error", readonly=True)
