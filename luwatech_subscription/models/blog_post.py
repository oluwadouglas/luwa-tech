# -*- coding: utf-8 -*-
import urllib.parse

from odoo import models


class BlogPost(models.Model):
    _inherit = "blog.post"

    def _luwa_public_base_url(self):
        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", "https://luwatech.it")
        )
        return (base_url or "https://luwatech.it").rstrip("/")

    def get_website_meta(self):
        res = super().get_website_meta()
        public_base = self._luwa_public_base_url()
        for section in ("opengraph_meta", "twitter_meta"):
            meta_dict = res.get(section) or {}
            for key in ("og:url", "og:image", "twitter:image"):
                val = meta_dict.get(key)
                if isinstance(val, str) and val.startswith("http://luwa-tech"):
                    meta_dict[key] = public_base + val[len("http://luwa-tech"):]
        return res

    def get_social_share_urls(self):
        self.ensure_one()
        public_base = self._luwa_public_base_url()
        canonical_url = f"{public_base}{self.website_url or ''}"
        title = self.name or "Luwa Tech Blog"
        encoded_url = urllib.parse.quote(canonical_url, safe="")
        encoded_title = urllib.parse.quote(title, safe="")
        encoded_wa = urllib.parse.quote(f"{title} - {canonical_url}", safe="")
        return {
            "canonical_url": canonical_url,
            "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}",
            "x": f"https://twitter.com/intent/tweet?url={encoded_url}&text={encoded_title}",
            "facebook": f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}",
            "whatsapp": f"https://wa.me/?text={encoded_wa}",
        }
