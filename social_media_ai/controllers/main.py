# -*- coding: utf-8 -*-
import base64

from odoo import http
from odoo.http import request


class SocialMediaAiMediaController(http.Controller):

    @http.route(
        "/social_media_ai/media/<int:post_id>/<string:token>.jpg",
        type="http",
        auth="public",
        csrf=False,
        sitemap=False,
    )
    def public_post_image(self, post_id, token, **kwargs):
        """Serve post image via a token-verified public URL for Instagram/Meta Graph API."""
        post = request.env["social.media.post"].sudo().browse(post_id).exists()
        if not post or not post.image or not post.media_access_token or post.media_access_token != token:
            return request.not_found()
        image_bytes = base64.b64decode(post.image)
        headers = [
            ("Content-Type", "image/jpeg"),
            ("Content-Length", str(len(image_bytes))),
            ("Cache-Control", "public, max-age=3600"),
        ]
        return request.make_response(image_bytes, headers=headers)
