# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.http import request


class ProductWishlist(models.Model):
    _inherit = "product.wishlist"

    @api.model
    def current(self):
        """Return active wishlisted items for the current session/partner without hiding Custom Pricing items."""
        if not request:
            return self
        if request.website.is_public_user():
            wish = self.sudo().search([("id", "in", request.session.get("wishlist_ids", []))])
        else:
            wish = self.search([
                ("partner_id", "=", self.env.user.partner_id.id),
                ("website_id", "=", request.website.id),
            ])
        return wish.filtered(lambda w: w.sudo().product_id.product_tmpl_id.website_published)

    @api.model
    def _add_to_wishlist(self, pricelist_id, currency_id, website_id, price, product_id, partner_id=False):
        """Idempotently add/reactivate wishlist item to prevent UNIQUE(product_id, partner_id) errors."""
        if partner_id:
            existing = self.with_context(active_test=False).sudo().search(
                [("partner_id", "=", partner_id), ("product_id", "=", product_id)],
                limit=1,
            )
            if existing:
                existing.write({
                    "pricelist_id": pricelist_id,
                    "currency_id": currency_id,
                    "website_id": website_id,
                    "price": price,
                    "active": True,
                })
                return existing
        return super()._add_to_wishlist(
            pricelist_id=pricelist_id,
            currency_id=currency_id,
            website_id=website_id,
            price=price,
            product_id=product_id,
            partner_id=partner_id,
        )

    @api.model
    def _check_wishlist_from_session(self):
        """Safely merge session wishlist into logged-in partner without duplicate or inactive collisions."""
        session_ids = request.session.get("wishlist_ids", []) if request else []
        if not session_ids:
            return
        session_wishes = self.sudo().search([("id", "in", session_ids)])
        partner = self.env.user.partner_id
        partner_wishes = self.with_context(active_test=False).sudo().search([
            ("partner_id", "=", partner.id)
        ])
        partner_by_prod = {w.product_id.id: w for w in partner_wishes}
        to_unlink = self.env["product.wishlist"].sudo()
        to_assign = self.env["product.wishlist"].sudo()
        for wish in session_wishes:
            existing = partner_by_prod.get(wish.product_id.id)
            if existing:
                if not existing.active:
                    existing.write({"active": True, "website_id": wish.website_id.id})
                to_unlink |= wish
            else:
                to_assign |= wish
        if to_unlink:
            to_unlink.unlink()
        if to_assign:
            to_assign.write({"partner_id": partner.id})
        request.session.pop("wishlist_ids", None)
