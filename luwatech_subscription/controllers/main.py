# -*- coding: utf-8 -*-
import logging
import re
from werkzeug.exceptions import NotFound

_logger = logging.getLogger(__name__)

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


SERVICE_CATALOG = {
    "digital-marketing": {
        "slug": "digital-marketing",
        "title": "Digital Marketing, SEO & Growth (DMaaS)",
        "kicker": "Digital Agency & Performance Growth",
        "summary": "Full-funnel Digital Marketing as a Service — Starter ($115/mo) and Premium ($225/mo) agency retainers covering social media, SEO, and campaign management (ad budgets separate).",
        "image": "/luwatech_website/static/src/images/update-01-10-2021/services/service-1-1.jpg?v=8",
        "icon": "fas fa-bullhorn",
        "accent": "cyan",
        "highlights": [
            "DMaaS Starter ($115/mo, excl. ad spend): Social media, SEO & campaign setup",
            "DMaaS Premium ($225/mo, excl. ad spend): Full-funnel ads, SEO & lead automation",
            "Google Search, YouTube, Meta, Instagram & LinkedIn creative campaigns",
            "Conversion-rate analytics, attribution dashboards & bi-weekly growth reviews",
        ],
        "shop_url": "/subscriptions#marketing-plans",
        "cta_label": "View Marketing Subscriptions",
    },
    "custom-saas": {
        "slug": "custom-saas",
        "title": "Custom SaaS & Digital Platforms",
        "kicker": "Luwa Digital Product Studio",
        "summary": "We design, build, and host purpose-built cloud platforms including Luwa eShule (School Management), Luwa eTari (Hospital Management), Cloud POS, and customer portals.",
        "image": "/luwatech_website/static/src/images/update-01-10-2021/services/service-1-2.jpg?v=8",
        "icon": "fas fa-cloud",
        "accent": "orange",
        "highlights": [
            "Luwa eShule — Complete School Management System (fees, exams, parent portal)",
            "Luwa eTari — End-to-end Hospital & Clinic Management System (EMR, pharmacy, lab)",
            "Multi-branch Cloud POS, Inventory & Ugandan PAYE/NSSF Payroll platforms",
            "Custom web portals & SaaS platforms with Mobile Money & role-based security",
        ],
        "shop_url": "/shop?search=Luwa",
        "cta_label": "Explore Luwa Digital Products",
    },
    "it-training": {
        "slug": "it-training",
        "title": "IT Training & Digital Academy",
        "kicker": "Corporate Upskilling & Bootcamps",
        "summary": "Practical, instructor-led corporate training and career bootcamps in Software Engineering, Digital Marketing, Cloud DevOps, Cybersecurity, and Business Software.",
        "image": "/luwatech_website/static/src/images/update-01-10-2021/services/service-1-3.jpg?v=8",
        "icon": "fas fa-graduation-cap",
        "accent": "cyan",
        "highlights": [
            "Corporate team upskilling in Kampala & live instructor-led online cohorts",
            "Software Engineering, Web Development, Python, JavaScript & Cloud tracks",
            "AI-assisted Digital Marketing, Analytics & Performance Ads workshops",
            "Cybersecurity fundamentals & hands-on enterprise software mastery",
        ],
        "shop_url": "/shop?search=Academy",
        "cta_label": "Enroll / Request Training",
    },
    "enterprise-erp": {
        "slug": "enterprise-erp",
        "title": "SAP, Zoho & Microsoft Dynamics 365 Connectors",
        "kicker": "Business Software & API Connectors",
        "summary": "Seamless digital storefronts, CRM portals, URA EFRIS tax fiscalization, and Mobile Money API connectors integrated with SAP, Zoho, and Microsoft Dynamics 365.",
        "image": "/luwatech_website/static/src/images/update-01-10-2021/services/service-1-4.jpg?v=8",
        "icon": "fas fa-plug",
        "accent": "orange",
        "highlights": [
            "Zoho One, Zoho CRM, Zoho Books & Inventory web and Mobile Money integrations",
            "Microsoft Dynamics 365 Business Central e-commerce & payment sync",
            "SAP Business One & S/4HANA API bridges for web portals and EFRIS",
            "Automated customer notifications via WhatsApp, SMS & email workflows",
        ],
        "shop_url": "/shop?search=Zoho",
        "cta_label": "Explore Software Connectors",
    },
    "web-eshop-mobile": {
        "slug": "web-eshop-mobile",
        "title": "Web, E-Shop & Mobile Apps",
        "kicker": "E-Commerce & Digital Experience",
        "summary": "High-converting brand websites, scalable e-commerce storefronts with invoicing and stock control, and mobile apps built for East African businesses.",
        "image": "/luwatech_website/static/src/images/update-01-10-2021/services/service-1-5.jpg?v=8",
        "icon": "fas fa-shopping-bag",
        "accent": "cyan",
        "highlights": [
            "E-Commerce Starter Subscription (Store, Minimal Invoicing & Stock) — $19/mo",
            "E-Commerce Complete Subscription (With Payment Gateway) — $29/mo",
            "Custom brand websites, landing pages & interactive digital experiences",
            "Android & iOS mobile apps connected directly to your store & inventory",
        ],
        "shop_url": "/subscriptions",
        "cta_label": "View E-Commerce Plans",
    },
    "efris-mobile-money": {
        "slug": "efris-mobile-money",
        "title": "EFRIS & Mobile Money Integrations",
        "kicker": "Tax Fiscalization & Payment APIs",
        "summary": "Automated URA EFRIS fiscal invoicing and real-time MTN MoMo & Airtel Money payment collection/disbursement APIs connected directly to your web store or software.",
        "image": "/luwatech_subscription/static/src/img/efris-momo-integration.png?v=9",
        "icon": "fas fa-money-check-alt",
        "accent": "orange",
        "highlights": [
            "URA EFRIS real-time invoice fiscalization, QR code & credit-note sync",
            "MTN Mobile Money & Airtel Money collection and automated reconciliation",
            "Works seamlessly with e-commerce stores, custom platforms, SAP, Zoho & Dynamics 365",
            "Webhook monitoring, retry queues, and audit-ready financial logs",
        ],
        "shop_url": "/shop?search=EFRIS",
        "cta_label": "Request Integration Quote",
    },
    "whatsapp-integration": {
        "slug": "whatsapp-integration",
        "title": "WhatsApp Integration as a Service",
        "kicker": "WhatsApp Business API",
        "summary": "Managed WhatsApp Business API integration connecting your website, e-commerce checkout, digital campaigns, and CRM directly to your customers on WhatsApp.",
        "image": "/luwatech_subscription/static/src/img/whatsapp-integration.png?v=9",
        "icon": "fab fa-whatsapp",
        "accent": "cyan",
        "highlights": [
            "Instant WhatsApp order confirmations, delivery updates & payment receipts",
            "Automated invoice & payment-link delivery via WhatsApp Business API",
            "Two-way CRM & shared team support inbox synchronization",
            "Lead-capture chatbots, broadcast templates & OTP verification",
        ],
        "shop_url": "/shop?search=WhatsApp",
        "cta_label": "Request WhatsApp Integration",
    },
}

SERVICE_ORDER = [
    "digital-marketing",
    "web-eshop-mobile",
    "efris-mobile-money",
    "whatsapp-integration",
    "custom-saas",
    "enterprise-erp",
    "it-training",
]


class LuwaSubscriptionWebsite(http.Controller):

    @http.route(
        "/luwatech/whatsapp/send_direct",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def whatsapp_send_direct(self, **post):
        _logger.info(">>> WHATSAPP SEND DIRECT ENTRY <<< raw post: %s", post)
        """Dispatches an inquiry message via the background WhatsApp engine (127.0.0.1:3010)
        directly without opening external chat creation links.
        Alerts Luwa Tech desk (+256787819453 Oluwa) and sends an automated confirmation
        to the visitor's WhatsApp number.
        """
        params = {}
        try:
            if request.httprequest.is_json:
                data = request.httprequest.get_json(silent=True) or {}
                params = data.get("params") if "params" in data else data
            else:
                params = post
        except Exception:
            params = post

        raw_phone = (params.get("visitor_phone") or "").strip()
        name = (params.get("visitor_name") or "Website Visitor").strip()
        body = (params.get("message") or "").strip()
        page = (params.get("source_url") or request.httprequest.referrer or "https://www.luwatech.it").strip()

        if not raw_phone:
            return request.make_json_response({"ok": False, "error": "Please provide a valid WhatsApp / contact phone number."})
        if not body:
            return request.make_json_response({"ok": False, "error": "Message body cannot be empty."})

        # Normalize phone
        digits = "".join(ch for ch in raw_phone if ch.isdigit())
        if digits.startswith("00"):
            digits = digits[2:]
        if digits.startswith("0") and len(digits) == 10:
            digits = "256" + digits[1:]
        elif len(digits) == 9 and digits.startswith("7"):
            digits = "256" + digits

        if len(digits) < 7:
            return request.make_json_response({"ok": False, "error": "Please enter a valid phone number with country code."})

        try:
            cfg = request.env["luwa.whatsapp.config"].sudo().get_solo()
            desk_phone = cfg.connected_phone or "256787819453"

            # 1. Alert message to Luwa Tech Internal Desk
            desk_alert = (
                "*LUWA TECH - NEW DIRECT WEBSITE INQUIRY*\n\n"
                f"- *From:* {name}\n"
                f"- *Visitor WhatsApp:* +{digits}\n"
                f"- *Origin Page:* {page}\n\n"
                "*Message:*\n"
                f"{body}\n\n"
                "_Sent directly via Luwa Tech background WhatsApp engine._"
            )
            cfg.send_whatsapp_message(
                phone=desk_phone,
                message=desk_alert,
                trigger_type="manual",
                queue_if_offline=True,
            )

            # 2. Automated Confirmation Message to Visitor's WhatsApp
            visitor_confirm = (
                "*LUWA TECH - KAMPALA DIGITAL STUDIO*\n\n"
                f"Hello *{name}*,\n"
                "Thank you for contacting *Luwa Tech*! Your request has been delivered directly to our solutions desk:\n\n"
                f"\"{body}\"\n\n"
                "A solutions specialist is reviewing your requirements and will follow up with you right here on WhatsApp shortly.\n\n"
                "*Luwa Tech Kampala*\n"
                "Tel: +256 787 819 453 | Web: https://www.luwatech.it"
            )
            cfg.send_whatsapp_message(
                phone=digits,
                message=visitor_confirm,
                trigger_type="manual",
                queue_if_offline=True,
            )

            # 3. Create Lead in CRM
            try:
                request.env["crm.lead"].sudo().create({
                    "name": f"WhatsApp Inquiry: {name} - {body[:40]}...",
                    "contact_name": name,
                    "phone": f"+{digits}",
                    "description": f"Source URL: {page}\n\nVisitor WhatsApp Message:\n{body}",
                    "type": "lead",
                    "priority": "2",
                })
            except Exception as crm_err:
                _logger.warning("Could not create CRM lead for WA inquiry: %s", crm_err)

            return request.make_json_response({
                "ok": True,
                "message": "Your message has been sent directly to the Luwa Tech team via our background engine! Check your WhatsApp for an automated confirmation.",
            })
        except Exception as exc:
            _logger.error("WhatsApp send_direct error: %s", exc)
            return request.make_json_response({"ok": False, "error": f"WhatsApp service error: {str(exc)}"})


    @http.route("/subscriptions", type="http", auth="public", website=True, sitemap=True)
    def subscriptions_page(self, **kwargs):
        all_subs = request.env["product.template"].sudo().search(
            [("is_subscription", "=", True), ("website_published", "=", True)],
            order="list_price asc, id asc",
        )
        ecom_subs = all_subs.filtered(lambda p: p.subscription_category != "marketing")
        marketing_subs = all_subs.filtered(lambda p: p.subscription_category == "marketing")
        return request.render(
            "luwatech_subscription.subscriptions_showcase_page",
            {
                "subscription_products": all_subs,
                "ecom_subscriptions": ecom_subs,
                "marketing_subscriptions": marketing_subs,
                "main_object": request.website,
            },
        )

    @http.route("/services", type="http", auth="public", website=True, sitemap=True)
    def services_overview_page(self, **kwargs):
        services = [SERVICE_CATALOG[key] for key in SERVICE_ORDER]
        return request.render(
            "luwatech_subscription.services_overview_page",
            {
                "services": services,
                "main_object": request.website,
            },
        )

    @http.route("/services/<string:slug>", type="http", auth="public", website=True, sitemap=True)
    def service_detail_page(self, slug, **kwargs):
        service = SERVICE_CATALOG.get(slug)
        if not service:
            raise NotFound()
        other_services = [SERVICE_CATALOG[k] for k in SERVICE_ORDER if k != slug]
        return request.render(
            "luwatech_subscription.service_detail_page",
            {
                "service": service,
                "other_services": other_services,
                "main_object": request.website,
            },
        )

    @http.route(
        "/subscriptions/subscribe/<int:product_tmpl_id>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def subscribe_add_to_cart(self, product_tmpl_id, **kwargs):
        tmpl = request.env["product.template"].sudo().browse(product_tmpl_id).exists()
        if not tmpl or not tmpl.website_published:
            return request.redirect("/subscriptions")
        variant = tmpl.product_variant_id
        if not variant or not variant._is_add_to_cart_allowed():
            return request.redirect(tmpl.website_url or "/shop")
        order_sudo = request.cart or request.website._create_cart()
        order_sudo.with_context(skip_cart_verification=True)._cart_add(
            product_id=variant.id,
            quantity=1,
        )
        return request.redirect("/shop/cart")



    @http.route(["/team", "/our-team"], type="http", auth="public", website=True, sitemap=True)
    def our_team_page(self, **kwargs):
        team_members = (
            request.env["hr.employee"]
            .sudo()
            .search([("is_published_website", "=", True), ("active", "=", True)], order="website_sequence asc, id asc")
        )
        return request.render(
            "luwatech_subscription.our_team_page",
            {
                "team_members": team_members,
                "main_object": request.website,
            },
        )



    @http.route(
        "/luwatech/newsletter/subscribe",
        type="http",
        auth="public",
        methods=["POST", "GET"],
        website=True,
        csrf=False,
        sitemap=False,
    )
    def luwatech_newsletter_subscribe(self, email="", **kwargs):
        from odoo.tools import email_normalize

        wants_json = (
            "application/json" in (request.httprequest.headers.get("Accept") or "")
            or request.httprequest.headers.get("X-Requested-With") == "XMLHttpRequest"
            or kwargs.get("ajax") == "1"
        )
        raw_email = (email or kwargs.get("newsletter_email") or "").strip()
        norm_email = email_normalize(raw_email)

        if not norm_email:
            if wants_json:
                return request.make_json_response(
                    {"ok": False, "message": "Please enter a valid email address."},
                    status=400,
                )
            return request.redirect("/?newsletter_error=invalid_email#subscribe-newsletter")

        MailingList = request.env["mailing.list"].sudo()
        MailingContact = request.env["mailing.contact"].sudo()
        MailingSubscription = request.env["mailing.subscription"].sudo()

        mlist = MailingList.search([("is_public", "=", True), ("active", "=", True)], order="id asc", limit=1)
        if not mlist:
            mlist = MailingList.search([("active", "=", True)], order="id asc", limit=1)
        if not mlist:
            mlist = MailingList.create({
                "name": "Luwa Tech Growth & Updates Newsletter",
                "active": True,
                "is_public": True,
            })

        contact = MailingContact.search([("email_normalized", "=", norm_email)], limit=1)
        if not contact:
            default_name = norm_email.split("@")[0].replace(".", " ").replace("_", " ").title()
            contact = MailingContact.create({
                "name": default_name or norm_email,
                "email": norm_email,
            })

        sub = MailingSubscription.search([
            ("contact_id", "=", contact.id),
            ("list_id", "=", mlist.id),
        ], limit=1)

        already_subscribed = False
        if sub:
            if sub.opt_out:
                sub.write({"opt_out": False, "opt_out_datetime": False})
            else:
                already_subscribed = True
        else:
            MailingSubscription.create({
                "contact_id", contact.id,
            } if False else {
                "contact_id": contact.id,
                "list_id": mlist.id,
                "opt_out": False,
            })

        msg = (
            f"You are already subscribed ({norm_email}) to our {mlist.name} list!"
            if already_subscribed
            else f"Thank you! {norm_email} has been added to our {mlist.name} mailing list."
        )

        if wants_json:
            return request.make_json_response({
                "ok": True,
                "already_subscribed": already_subscribed,
                "email": norm_email,
                "list_name": mlist.name,
                "message": msg,
            })

        return request.redirect("/?newsletter_subscribed=1#subscribe-newsletter")



    @http.route("/project/signoff/<int:signoff_id>", type="http", auth="public", website=True, sitemap=False)
    def project_signoff_portal(self, signoff_id, token="", saved="", submitted="", **kwargs):
        dossier = request.env["luwa.project.signoff"].sudo().browse(signoff_id).exists()
        if not dossier or (dossier.access_token and token != dossier.access_token and not request.env.user._is_internal()):
            raise NotFound()
        return request.render(
            "luwatech_subscription.project_signoff_public_page",
            {
                "dossier": dossier,
                "token": token or dossier.access_token,
                "submitted": bool(submitted or saved),
                "main_object": dossier,
            },
        )

    @http.route("/project/signoff/<int:signoff_id>/pdf", type="http", auth="public", website=True, sitemap=False)
    def project_signoff_download_pdf(self, signoff_id, token="", **kwargs):
        import base64
        dossier = request.env["luwa.project.signoff"].sudo().browse(signoff_id).exists()
        if not dossier or (dossier.access_token and token != dossier.access_token and not request.env.user._is_internal()):
            raise NotFound()
        pdf_bytes = None
        try:
            pdf_bytes, _ = request.env["ir.actions.report"].sudo()._render_qweb_pdf(
                "luwatech_subscription.action_report_project_signoff",
                [dossier.id],
            )
            if pdf_bytes:
                clean_ref = (dossier.reference or f"SIGNOFF_{dossier.id}").replace("/", "_")
                dossier.sudo().write({
                    "master_pdf_file": base64.b64encode(pdf_bytes),
                    "master_pdf_filename": f"Munig_Odoo18_Module_SignOff_{clean_ref}.pdf",
                })
        except Exception:
            if dossier.master_pdf_file:
                pdf_bytes = base64.b64decode(dossier.master_pdf_file)
        if not pdf_bytes:
            raise NotFound()
        filename = dossier.master_pdf_filename or "Munig_Odoo18_Module_SignOff_Checklist.pdf"
        return request.make_response(
            pdf_bytes,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Disposition", f'inline; filename="{filename}"'),
            ],
        )

    @http.route("/project/signoff/<int:signoff_id>/submit", type="http", auth="public", methods=["POST"], website=True, csrf=False, sitemap=False)
    def project_signoff_submit(self, signoff_id, token="", **post_data):
        from odoo import fields
        dossier = request.env["luwa.project.signoff"].sudo().browse(signoff_id).exists()
        if not dossier or (dossier.access_token and token != dossier.access_token and not request.env.user._is_internal()):
            raise NotFound()

        # Combine post_data and request.httprequest.form
        post = dict(request.httprequest.form)
        post.update(post_data)

        today = fields.Date.context_today(dossier)
        signer_name = (
            (post.get("signer_name") or "").strip()
            or (post.get("client_tech_name") or "").strip()
            or (post.get("client_hr_name") or "").strip()
            or (post.get("client_ceo_name") or "").strip()
            or (post.get("client_fin_name") or "").strip()
            or dossier.partner_id.name
            or "Client Representative"
        )

        signed_any = False
        for line in dossier.line_ids:
            is_checked = bool(post.get(f"line_signed_{line.id}") or post.get(f"check_{line.id}"))
            remark_val = (post.get(f"line_remarks_{line.id}") or post.get(f"remark_{line.id}") or "").strip()
            line_vals = {
                "client_signed": is_checked,
                "client_checked": is_checked,
                "remarks": remark_val,
                "client_remarks": remark_val,
            }
            if is_checked:
                signed_any = True
                if not line.signoff_date:
                    line_vals["signoff_date"] = today
                if not line.verified_date:
                    line_vals["verified_date"] = fields.Datetime.now()
                if not line.signed_by:
                    line_vals["signed_by"] = signer_name
                if not line.verified_by:
                    line_vals["verified_by"] = signer_name
            line.write(line_vals)

        header_vals = {}
        if "general_remarks" in post:
            header_vals["general_remarks"] = (post.get("general_remarks") or "").strip()

        signatory_map = [
            ("luwa_lead_name", "luwa_lead_signed", "luwa_lead_date", "luwa_lead_signed_on", "luwa_lead_signature", "luwa_lead_signature_b64"),
            ("client_tech_name", "client_tech_signed", "client_tech_date", "client_tech_signed_on", "client_tech_signature", "client_tech_signature_b64"),
            ("client_hr_name", "client_hr_signed", "client_hr_date", "client_hr_signed_on", "client_hr_signature", "client_hr_signature_b64"),
            ("client_fin_name", "client_fin_signed", "client_fin_date", "client_fin_signed_on", "client_fin_signature", "client_fin_signature_b64"),
            ("client_ceo_name", "client_ceo_signed", "client_ceo_date", "client_ceo_signed_on", "client_ceo_signature", "client_ceo_signature_b64"),
        ]
        for name_f, signed_f, date_f, date_on_f, sig_f, b64_param in signatory_map:
            if name_f in post:
                header_vals[name_f] = (post.get(name_f) or "").strip()
            is_sig_checked = bool(post.get(signed_f))
            raw_b64 = (post.get(b64_param) or "").strip()
            if raw_b64 and "base64," in raw_b64:
                clean_b64 = raw_b64.split("base64,", 1)[1].strip().replace(" ", "+")
                missing_padding = len(clean_b64) % 4
                if missing_padding:
                    clean_b64 += "=" * (4 - missing_padding)
                try:
                    import base64
                    base64.b64decode(clean_b64)
                    header_vals[sig_f] = clean_b64
                    is_sig_checked = True
                except Exception as e:
                    pass
            header_vals[signed_f] = is_sig_checked
            if is_sig_checked:
                if not getattr(dossier, date_f):
                    header_vals[date_f] = today
                if not getattr(dossier, date_on_f):
                    header_vals[date_on_f] = today

        dossier.write(header_vals)

        if dossier.total_items > 0 and dossier.client_signed_items == dossier.total_items:
            dossier.write({"state": "signed_off"})
        elif dossier.client_signed_items > 0 or signed_any or dossier.client_tech_signed or dossier.client_hr_signed or dossier.client_fin_signed or dossier.client_ceo_signed:
            if dossier.state != "signed_off":
                dossier.write({"state": "partially_signed"})

        dossier._regenerate_signed_pdf_attachment()
        dossier.message_post(
            body=(
                f"Client online sign-off updated by {signer_name}: "
                f"{dossier.client_signed_items}/{dossier.total_items} submenus signed off "
                f"({dossier.completion_rate}%)."
            )
        )
        return request.redirect(f"/project/signoff/{dossier.id}?token={dossier.access_token}&submitted=1")


class LuwaSubscriptionPortal(CustomerPortal):

    def _luwa_portal_kpis(self):
        partner = request.env.user.partner_id
        comm_id = partner.commercial_partner_id.id
        Subscription = request.env["luwa.subscription"].sudo()
        SaleOrder = request.env["sale.order"].sudo()
        AccountMove = request.env["account.move"].sudo()
        Wishlist = request.env["product.wishlist"].sudo()

        sub_domain = [("partner_id", "child_of", comm_id)]
        active_subs = Subscription.search_count(sub_domain + [("state", "=", "active")])
        pending_subs = Subscription.search_count(sub_domain + [("state", "=", "draft")])
        total_subs = Subscription.search_count(sub_domain)
        order_count = SaleOrder.search_count([
            ("partner_id", "child_of", comm_id),
            ("state", "in", ["sent", "sale", "done"]),
        ])
        invoice_count = AccountMove.search_count([
            ("partner_id", "child_of", comm_id),
            ("move_type", "in", ["out_invoice", "out_refund"]),
            ("state", "=", "posted"),
        ])
        wish_count = Wishlist.search_count([
            ("partner_id", "=", partner.id),
            ("active", "=", True),
        ])
        return {
            "luwa_sub_active_count": active_subs,
            "luwa_sub_pending_count": pending_subs,
            "luwa_sub_total_count": total_subs,
            "luwa_order_count": order_count,
            "luwa_invoice_count": invoice_count,
            "luwa_wishlist_count": wish_count,
        }

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if "subscription_count" in counters:
            values["subscription_count"] = (
                request.env["luwa.subscription"]
                .sudo()
                .search_count([("partner_id", "child_of", partner.commercial_partner_id.id)])
            )
        return values

    @http.route()
    def home(self, **kw):
        response = super().home(**kw)
        if hasattr(response, "qcontext"):
            response.qcontext.update(self._luwa_portal_kpis())
        return response

    @http.route(["/my/subscriptions", "/my/subscriptions/page/<int:page>"], type="http", auth="user", website=True)
    def portal_my_subscriptions(self, page=1, status="all", **kwargs):
        partner = request.env.user.partner_id
        Subscription = request.env["luwa.subscription"].sudo()
        base_domain = [("partner_id", "child_of", partner.commercial_partner_id.id)]
        domain = list(base_domain)
        if status in ("active", "draft", "paused", "cancelled", "expired"):
            domain.append(("state", "=", status))
        else:
            status = "all"
        subscriptions = Subscription.search(domain, order="id desc")
        return request.render(
            "luwatech_subscription.portal_my_subscriptions",
            {
                "subscriptions": subscriptions,
                "status_filter": status,
                "active_count": Subscription.search_count(base_domain + [("state", "=", "active")]),
                "pending_count": Subscription.search_count(base_domain + [("state", "=", "draft")]),
                "total_count": Subscription.search_count(base_domain),
                "page_name": "subscriptions",
            },
        )
