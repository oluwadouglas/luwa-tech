# -*- coding: utf-8 -*-
import re
from odoo import _, api, fields, models
from odoo.exceptions import UserError


def _norm_key(raw_phone):
    digits = re.sub(r"[^\d]", "", str(raw_phone or ""))
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 10:
        digits = "256" + digits[1:]
    elif len(digits) == 9 and digits.startswith("7"):
        digits = "256" + digits
    return digits


def _collect_recipients(phone_str, partner_id=None, partner_ids=None):
    """Return list of (phone_str, res.partner or False) deduplicated by normalized digits."""
    targets = []
    seen = set()

    all_partners = []
    if partner_ids:
        all_partners.extend(list(partner_ids))
    if partner_id and partner_id not in all_partners:
        all_partners.insert(0, partner_id)

    partner_by_key = {}
    for p in all_partners:
        if p.phone:
            k = _norm_key(p.phone)
            if k:
                partner_by_key[k] = p

    for part in re.split(r"[,;\n]+", str(phone_str or "")):
        raw = part.strip()
        if not raw:
            continue
        k = _norm_key(raw)
        if not k or k in seen:
            continue
        seen.add(k)
        targets.append((raw, partner_by_key.get(k, partner_id if len(all_partners) == 1 else False)))

    for p in all_partners:
        if p.phone and p.phone.strip():
            k = _norm_key(p.phone)
            if k and k not in seen:
                seen.add(k)
                targets.append((p.phone.strip(), p))

    return targets


def _deliver_via_luwa_bridge(
    env,
    phone,
    message,
    partner=None,
    partners=None,
    res_model=False,
    res_id=0,
    queue_if_offline=True,
    document_b64=False,
    filename=False,
    auto_pdf=True,
):
    cfg = env["luwa.whatsapp.config"].get_solo()
    targets = _collect_recipients(phone, partner_id=partner, partner_ids=partners)
    if not targets:
        raise UserError(_("Please select at least one recipient with a phone number or enter phone number(s)."))

    # Pre-extract official PDF once if needed so multi-recipient sends don't re-render QWeb PDF repeatedly
    if not document_b64 and auto_pdf and res_model in ("sale.order", "account.move", "luwa.subscription") and res_id:
        doc_info = cfg._extract_record_pdf_and_link(res_model, res_id, include_pdf=True)
        if doc_info.get("document_b64"):
            document_b64 = doc_info["document_b64"]
            filename = doc_info.get("filename") or "LuwaTech-Document.pdf"

    sent_phones = []
    queued_phones = []
    errors = []
    last_att_name = filename or ""

    for target_phone, target_partner in targets:
        log = cfg.send_whatsapp_message(
            phone=target_phone,
            message=message,
            partner=target_partner,
            res_model=res_model,
            res_id=res_id,
            trigger_type="manual",
            queue_if_offline=queue_if_offline,
            document_b64=document_b64,
            filename=filename,
            auto_pdf=False,
        )
        if log.attachment_name:
            last_att_name = log.attachment_name
        if log.state == "sent":
            sent_phones.append(log.normalized_phone or target_phone)
        elif log.state == "queued":
            queued_phones.append(log.normalized_phone or target_phone)
        else:
            errors.append(f"{target_phone}: {log.error_message or 'Failed'}")

    if not sent_phones and not queued_phones:
        raise UserError(_("WhatsApp send failed: %s") % ("; ".join(errors) or "Unknown error"))

    att_label = f" (with {last_att_name})" if last_att_name else ""
    delivered_all = sent_phones + queued_phones
    if queued_phones and not sent_phones:
        note = _("Message%s queued for %s recipient(s): %s") % (
            att_label,
            len(queued_phones),
            ", ".join(queued_phones),
        )
    else:
        note = _("WhatsApp message%s sent directly to %s recipient(s): %s") % (
            att_label,
            len(delivered_all),
            ", ".join(delivered_all),
        )
    return {
        "type": "ir.actions.client",
        "tag": "display_notification",
        "params": {
            "title": _("WhatsApp Engine"),
            "message": note,
            "type": "success",
            "sticky": False,
            "next": {"type": "ir.actions.act_window_close"},
        },
    }


class LuwaWhatsappComposer(models.TransientModel):
    _name = "luwa.whatsapp.composer"
    _description = "Send Direct WhatsApp Message & Document"

    partner_id = fields.Many2one("res.partner", string="Primary Contact")
    partner_ids = fields.Many2many(
        "res.partner",
        "luwa_wa_composer_partner_rel",
        "composer_id",
        "partner_id",
        string="Recipients (Select One or More Contacts)",
    )
    phone = fields.Char(
        string="Phone Number(s) (Comma-Separated)",
        required=True,
        help="Add one or multiple phone numbers separated by commas, e.g. 0754370995, 0787819453",
    )
    attach_pdf = fields.Boolean(
        string="Attach Official PDF (Quote / Order / Invoice)",
        default=True,
    )
    pdf_preview_name = fields.Char(
        string="Document to Attach",
        readonly=True,
    )
    custom_attachment = fields.Binary(string="Or Upload Custom PDF / File")
    custom_attachment_name = fields.Char(string="Custom File Name")
    message = fields.Text(string="Message Preview (Editable Before Sending)", required=True)
    queue_if_offline = fields.Boolean(
        string="Queue If WhatsApp Disconnected",
        default=True,
    )
    res_model = fields.Char(readonly=True)
    res_id = fields.Integer(readonly=True)

    @api.onchange("partner_ids", "partner_id")
    def _onchange_partners_sync_phones(self):
        existing_parts = [
            p.strip()
            for p in re.split(r"[,;\n]+", str(self.phone or ""))
            if p.strip()
        ]
        seen = {_norm_key(p) for p in existing_parts if _norm_key(p)}
        combined = list(existing_parts)

        partners = list(self.partner_ids)
        if self.partner_id and self.partner_id not in partners:
            partners.insert(0, self.partner_id)

        for partner in partners:
            if partner.phone and partner.phone.strip():
                k = _norm_key(partner.phone)
                if k and k not in seen:
                    seen.add(k)
                    combined.append(partner.phone.strip())
        if combined:
            self.phone = ", ".join(combined)

    def action_send(self):
        self.ensure_one()
        doc_b64 = (
            self.custom_attachment.decode("ascii")
            if isinstance(self.custom_attachment, bytes)
            else (self.custom_attachment or False)
        )
        return _deliver_via_luwa_bridge(
            self.env,
            phone=self.phone,
            message=self.message,
            partner=self.partner_id,
            partners=self.partner_ids,
            res_model=self.res_model,
            res_id=self.res_id,
            queue_if_offline=self.queue_if_offline,
            document_b64=doc_b64,
            filename=self.custom_attachment_name or False,
            auto_pdf=self.attach_pdf and not bool(doc_b64),
        )


class WhatsappSendMessageOverride(models.TransientModel):
    """Upgrade top-bar Cybrosys whatsapp.send.message popup with multi-recipient + PDF + preview."""
    _inherit = "whatsapp.send.message"

    partner_ids = fields.Many2many(
        "res.partner",
        "luwa_wa_send_msg_partner_rel",
        "wiz_id",
        "partner_id",
        string="Additional Recipients",
    )
    attach_pdf = fields.Boolean(
        string="Attach Official PDF (When on Quote/Order/Invoice)",
        default=True,
    )
    custom_attachment = fields.Binary(string="Attach PDF / File")
    custom_attachment_name = fields.Char(string="Attachment File Name")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context or {}
        active_model = ctx.get("active_model")
        active_id = ctx.get("active_id")
        cfg = self.env["luwa.whatsapp.config"].get_solo()
        if active_model in ("sale.order", "account.move") and active_id:
            try:
                rec = self.env[active_model].sudo().browse(int(active_id))
                if rec.exists():
                    doc_info = cfg._extract_record_pdf_and_link(active_model, rec.id, include_pdf=False)
                    rec_ref = rec.name if (rec.name and rec.name != "/") else f"DRAFT-{rec.id:04d}"
                    if active_model == "sale.order":
                        tpl = cfg.tpl_quote_reminder if rec.state in ("draft", "sent") else cfg.tpl_order_confirm
                        res["message"] = cfg._format_template(
                            tpl,
                            partner_name=rec.partner_id.name or "Valued Client",
                            record_name=rec_ref,
                            amount=f"{rec.amount_total:,.0f}",
                            currency=rec.currency_id.name or "",
                            due_date=str(rec.validity_date or "Open"),
                            portal_url=doc_info["portal_url"],
                        )
                    elif active_model == "account.move":
                        amt = rec.amount_residual if rec.amount_residual > 0 else rec.amount_total
                        res["message"] = cfg._format_template(
                            cfg.tpl_invoice_reminder,
                            partner_name=rec.partner_id.name or "Valued Client",
                            record_name=rec_ref,
                            amount=f"{amt:,.0f}",
                            currency=rec.currency_id.name or "",
                            due_date=str(rec.invoice_date_due or fields.Date.context_today(self)),
                            portal_url=doc_info["portal_url"],
                        )
            except Exception:
                pass
        elif not res.get("message"):
            res["message"] = (
                "*LUWA TECH - KAMPALA DIGITAL STUDIO*\n\n"
                "Hello,\n"
                "Thank you for partnering with *Luwa Tech*.\n\n"
                "Best regards,\n"
                "*Luwa Tech Team*\n"
                "Tel: +256 787 819 453 | https://www.luwatech.it"
            )
        return res

    @api.onchange("partner_id", "partner_ids")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.image_1920 = self.partner_id.image_1920
        existing_parts = [
            p.strip()
            for p in re.split(r"[,;\n]+", str(self.mobile or ""))
            if p.strip()
        ]
        seen = {_norm_key(p) for p in existing_parts if _norm_key(p)}
        combined = list(existing_parts)

        partners = []
        if self.partner_id:
            partners.append(self.partner_id)
        for p in self.partner_ids:
            if p not in partners:
                partners.append(p)

        for p in partners:
            if p.phone and p.phone.strip():
                k = _norm_key(p.phone)
                if k and k not in seen:
                    seen.add(k)
                    combined.append(p.phone.strip())
        if combined:
            self.mobile = ", ".join(combined)

    def send_message(self):
        self.ensure_one()
        if not self.mobile or not self.message:
            raise UserError(_("Please enter at least one Contact Number and Message."))
        ctx = self.env.context or {}
        res_model = ctx.get("active_model") or ("res.partner" if self.partner_id else False)
        res_id = ctx.get("active_id") or (self.partner_id.id if self.partner_id else 0)
        doc_b64 = (
            self.custom_attachment.decode("ascii")
            if isinstance(self.custom_attachment, bytes)
            else (self.custom_attachment or False)
        )
        return _deliver_via_luwa_bridge(
            self.env,
            phone=self.mobile,
            message=self.message,
            partner=self.partner_id,
            partners=self.partner_ids,
            res_model=res_model,
            res_id=res_id,
            queue_if_offline=True,
            document_b64=doc_b64,
            filename=self.custom_attachment_name or False,
            auto_pdf=self.attach_pdf and not bool(doc_b64),
        )


class PortalShareWhatsappOverride(models.TransientModel):
    """Override Portal Share WhatsApp button to send directly via Luwa QR Bridge with PDF."""
    _inherit = "portal.share"

    def action_send_whatsapp(self):
        self.ensure_one()
        if not self.mobile_number:
            raise UserError(_("Please enter a recipient mobile number."))
        if self.res_model == "sale.order":
            common_message = _("*LUWA TECH - QUOTATION / ORDER ACCESS*")
        elif self.res_model == "account.move":
            common_message = _("*LUWA TECH - INVOICE ACCESS*")
        else:
            common_message = _("*LUWA TECH - DOCUMENT ACCESS*")
        full_text = "\n\n".join(
            part for part in [common_message, self.note or "", f"View / Download Online:\n{self.share_link or ''}"] if part
        )
        return _deliver_via_luwa_bridge(
            self.env,
            phone=self.mobile_number,
            message=full_text,
            partner=self.partner_id,
            res_model=self.res_model,
            res_id=int(self.res_id or 0),
            queue_if_offline=True,
            auto_pdf=True,
        )
