# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SocialMediaAccount(models.Model):
    _name = "social.media.account"
    _description = "Connected Social Media Account (Facebook, Instagram, LinkedIn, X)"
    _inherit = ["mail.thread"]
    _order = "sequence asc, id asc"

    name = fields.Char(
        string="Account Label",
        required=True,
        tracking=True,
        help="e.g. Luwa Tech Facebook Page, Luwa Tech LinkedIn, @luwatech on X",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    platform = fields.Selection(
        [
            ("facebook", "Facebook Page"),
            ("instagram", "Instagram Business"),
            ("linkedin", "LinkedIn (Profile or Company Page)"),
            ("x", "X (Twitter)"),
        ],
        string="Platform",
        required=True,
        default="facebook",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("unconfigured", "Not Connected"),
            ("connected", "Connected & Verified"),
            ("error", "Connection Error"),
        ],
        string="Connection Status",
        default="unconfigured",
        tracking=True,
    )
    account_handle = fields.Char(
        string="Connected Handle / Page Name",
        readonly=True,
    )
    external_account_id = fields.Char(
        string="Verified Platform ID",
        readonly=True,
    )
    last_verified_at = fields.Datetime(string="Last Verified", readonly=True)
    last_error = fields.Text(string="Last API Response / Error", readonly=True)

    # 1. Shared / Meta (Facebook & Instagram) & LinkedIn OAuth Access Token
    access_token = fields.Char(
        string="Access Token / Bearer Token",
        help="Page Access Token (Facebook/Instagram), OAuth 2.0 Access Token (LinkedIn), or OAuth 2.0 User Token (X).",
    )

    # 2. Facebook & Instagram Specific Fields
    facebook_page_id = fields.Char(
        string="Facebook Page ID",
        help="Numeric ID of your Facebook Page (e.g. 102938475610293).",
    )
    instagram_account_id = fields.Char(
        string="Instagram Business Account ID",
        help="Numeric ID of your Instagram Business / Creator account linked to your Facebook Page.",
    )
    meta_app_id = fields.Char(string="Meta App ID (Optional)")
    meta_app_secret = fields.Char(string="Meta App Secret (Optional)")

    # 3. LinkedIn Specific Fields
    linkedin_account_type = fields.Selection(
        [
            ("person", "Personal Profile (urn:li:person)"),
            ("organization", "Company Page (urn:li:organization)"),
        ],
        string="LinkedIn Target Type",
        default="person",
    )
    linkedin_author_id = fields.Char(
        string="LinkedIn Member / Organization ID",
        help="Your LinkedIn Member sub/ID (auto-detected on click of 'Test & Connect') or Company Page numeric ID.",
    )

    # 4. X (Twitter) Specific Fields (Free Tier OAuth 1.0a & OAuth 2.0)
    x_auth_mode = fields.Selection(
        [
            ("oauth1", "OAuth 1.0a Keys (Recommended • Works on X Free Tier + Image Upload)"),
            ("oauth2", "OAuth 2.0 User Access Token"),
        ],
        string="X Authentication Mode",
        default="oauth1",
    )
    x_api_key = fields.Char(string="X API Key (Consumer Key)")
    x_api_secret = fields.Char(string="X API Key Secret (Consumer Secret)")
    x_access_token = fields.Char(string="X Access Token")
    x_access_token_secret = fields.Char(string="X Access Token Secret")

    post_ids = fields.One2many("social.media.post", "account_id", string="Posts")
    published_count = fields.Integer(
        string="Published Posts",
        compute="_compute_published_count",
    )

    @api.depends("post_ids", "post_ids.state")
    def _compute_published_count(self):
        for rec in self:
            rec.published_count = len(rec.post_ids.filtered(lambda p: p.state == "published"))

    def action_view_account_posts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Posts for %s") % self.name,
            "res_model": "social.media.post",
            "view_mode": "kanban,list,calendar,form",
            "domain": [("account_id", "=", self.id)],
            "context": {"default_account_id": self.id, "default_platform": self.platform},
        }

    # -------------------------------------------------------------------------
    # OAUTH 1.0A SIGNER FOR X (TWITTER) FREE TIER
    # -------------------------------------------------------------------------
    def _build_x_oauth1_header(self, method, url, extra_params=None):
        self.ensure_one()
        consumer_key = (self.x_api_key or "").strip()
        consumer_secret = (self.x_api_secret or "").strip()
        token = (self.x_access_token or "").strip()
        token_secret = (self.x_access_token_secret or "").strip()
        if not (consumer_key and consumer_secret and token and token_secret):
            raise UserError(
                _("Please fill in all 4 X OAuth 1.0a keys: API Key, API Key Secret, Access Token, and Access Token Secret.")
            )

        oauth_params = {
            "oauth_consumer_key": consumer_key,
            "oauth_nonce": uuid.uuid4().hex,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": token,
            "oauth_version": "1.0",
        }
        all_params = dict(oauth_params)
        if extra_params:
            all_params.update(extra_params)

        def _pct(val):
            return urllib.parse.quote(str(val), safe="")

        sorted_items = sorted((_pct(k), _pct(v)) for k, v in all_params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_items)
        base_url = url.split("?")[0]
        base_str = "&".join([method.upper(), _pct(base_url), _pct(param_str)])
        signing_key = f"{_pct(consumer_secret)}&{_pct(token_secret)}"
        signature = base64.b64encode(
            hmac.new(signing_key.encode("utf-8"), base_str.encode("utf-8"), hashlib.sha1).digest()
        ).decode("ascii")
        oauth_params["oauth_signature"] = signature

        auth_header = "OAuth " + ", ".join(
            f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(oauth_params.items())
        )
        return auth_header

    # -------------------------------------------------------------------------
    # CONNECTION VERIFICATION ("Test & Connect Account")
    # -------------------------------------------------------------------------
    def action_verify_connection(self):
        self.ensure_one()
        try:
            if self.platform == "facebook":
                token = (self.access_token or "").strip()
                page_id = (self.facebook_page_id or "me").strip()
                if not token:
                    raise UserError(_("Please enter your Facebook Page Access Token."))
                url = (
                    f"https://graph.facebook.com/v21.0/{urllib.parse.quote(page_id)}"
                    f"?fields=id,name,access_token&access_token={urllib.parse.quote(token)}"
                )
                req = urllib.request.Request(url, headers={"User-Agent": "Odoo19-SocialMediaAI/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                vals = {
                    "state": "connected",
                    "external_account_id": data.get("id", page_id),
                    "account_handle": data.get("name", "Facebook Page"),
                    "facebook_page_id": data.get("id", page_id),
                    "last_verified_at": fields.Datetime.now(),
                    "last_error": False,
                }
                if data.get("access_token"):
                    vals["access_token"] = data["access_token"]
                self.write(vals)

            elif self.platform == "instagram":
                token = (self.access_token or "").strip()
                ig_id = (self.instagram_account_id or "").strip()
                if not token or not ig_id:
                    raise UserError(_("Please enter both your Instagram Business Account ID and Meta Page Access Token."))
                url = (
                    f"https://graph.facebook.com/v21.0/{urllib.parse.quote(ig_id)}"
                    f"?fields=id,username,name&access_token={urllib.parse.quote(token)}"
                )
                req = urllib.request.Request(url, headers={"User-Agent": "Odoo19-SocialMediaAI/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                handle = data.get("username") or data.get("name") or ig_id
                self.write({
                    "state": "connected",
                    "external_account_id": data.get("id", ig_id),
                    "account_handle": f"@{handle}" if not str(handle).startswith("@") else handle,
                    "last_verified_at": fields.Datetime.now(),
                    "last_error": False,
                })

            elif self.platform == "linkedin":
                token = (self.access_token or "").strip()
                if not token:
                    raise UserError(_("Please enter your LinkedIn OAuth 2.0 Access Token."))
                headers = {
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "Odoo19-SocialMediaAI/1.0",
                }
                member_id = (self.linkedin_author_id or "").strip()
                member_name = "LinkedIn Account"
                try:
                    req = urllib.request.Request("https://api.linkedin.com/v2/userinfo", headers=headers)
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        member_id = member_id or data.get("sub", "")
                        member_name = data.get("name") or data.get("email") or "LinkedIn Profile"
                except Exception:
                    req = urllib.request.Request("https://api.linkedin.com/v2/me", headers=headers)
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        member_id = member_id or data.get("id", "")
                        fname = data.get("localizedFirstName", "")
                        lname = data.get("localizedLastName", "")
                        member_name = f"{fname} {lname}".strip() or "LinkedIn Profile"

                self.write({
                    "state": "connected",
                    "linkedin_author_id": member_id,
                    "external_account_id": member_id,
                    "account_handle": member_name,
                    "last_verified_at": fields.Datetime.now(),
                    "last_error": False,
                })

            elif self.platform == "x":
                url = "https://api.twitter.com/2/users/me"
                if self.x_auth_mode == "oauth1":
                    auth_header = self._build_x_oauth1_header("GET", url)
                else:
                    token = (self.access_token or "").strip()
                    if not token:
                        raise UserError(_("Please enter your X OAuth 2.0 Bearer/Access Token."))
                    auth_header = f"Bearer {token}"

                req = urllib.request.Request(
                    url,
                    headers={
                        "Authorization": auth_header,
                        "User-Agent": "Odoo19-SocialMediaAI/1.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8")).get("data", {})
                username = data.get("username") or data.get("name") or "X Account"
                self.write({
                    "state": "connected",
                    "external_account_id": data.get("id", ""),
                    "account_handle": f"@{username}" if not str(username).startswith("@") else username,
                    "last_verified_at": fields.Datetime.now(),
                    "last_error": False,
                })

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Account Connected!"),
                    "message": _("%s (%s) is verified and ready for direct publishing.")
                    % (self.name, self.account_handle or self.platform),
                    "type": "success",
                    "sticky": False,
                },
            }
        except urllib.error.HTTPError as http_err:
            err_body = ""
            try:
                err_body = http_err.read().decode("utf-8")
            except Exception:
                err_body = str(http_err)
            self.write({
                "state": "error",
                "last_error": f"HTTP {http_err.code}: {err_body}",
            })
            raise UserError(_("Platform API Error (HTTP %s):\n%s") % (http_err.code, err_body))
        except Exception as exc:
            self.write({
                "state": "error",
                "last_error": str(exc),
            })
            raise UserError(_("Connection Verification Failed:\n%s") % str(exc))

    # -------------------------------------------------------------------------
    # DIRECT PUBLISHING ENGINE (Facebook, Instagram, LinkedIn, X)
    # -------------------------------------------------------------------------
    def publish_post_to_platform(self, post):
        """Publish a social.media.post record (with user-uploaded or AI image) directly to this account."""
        self.ensure_one()
        body_parts = []
        if post.caption:
            body_parts.append(post.caption.strip())
        elif post.name:
            body_parts.append(post.name.strip())
        if post.call_to_action:
            body_parts.append(f"👉 {post.call_to_action.strip()}")
        if post.hashtags:
            body_parts.append(post.hashtags.strip())
        full_message = "\n\n".join(body_parts)

        try:
            if self.platform == "facebook":
                return self._publish_to_facebook(post, full_message)
            elif self.platform == "instagram":
                return self._publish_to_instagram(post, full_message)
            elif self.platform == "linkedin":
                return self._publish_to_linkedin(post, full_message)
            elif self.platform == "x":
                return self._publish_to_x(post, full_message)
            else:
                raise UserError(_("Unsupported platform: %s") % self.platform)
        except urllib.error.HTTPError as http_err:
            err_body = ""
            try:
                err_body = http_err.read().decode("utf-8")
            except Exception:
                err_body = str(http_err)
            self.sudo().write({"last_error": f"HTTP {http_err.code}: {err_body}"})
            raise UserError(_("%s Publishing Error (HTTP %s):\n%s") % (self.name, http_err.code, err_body))

    def _publish_to_facebook(self, post, full_message):
        token = (self.access_token or "").strip()
        page_id = (self.facebook_page_id or "").strip()
        if not token or not page_id:
            raise UserError(_("Please configure Facebook Page ID and Page Access Token on account '%s'.") % self.name)

        if post.image:
            # Multipart upload to /{page_id}/photos so custom uploaded or AI images post natively
            boundary = f"----OdooSocialBoundary{uuid.uuid4().hex}"
            img_bytes = base64.b64decode(post.image)
            fname = post.image_filename or "post_image.jpg"

            parts = []
            for k, v in [("caption", full_message), ("access_token", token), ("published", "true")]:
                parts.append(f"--{boundary}\r\n".encode("utf-8"))
                parts.append(f'Content-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8"))

            parts.append(f"--{boundary}\r\n".encode("utf-8"))
            parts.append(
                f'Content-Disposition: form-data; name="source"; filename="{fname}"\r\n'
                f"Content-Type: image/jpeg\r\n\r\n".encode("utf-8")
            )
            parts.append(img_bytes)
            parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
            body = b"".join(parts)

            url = f"https://graph.facebook.com/v21.0/{urllib.parse.quote(page_id)}/photos"
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "User-Agent": "Odoo19-SocialMediaAI/1.0",
                },
                method="POST",
            )
        else:
            url = f"https://graph.facebook.com/v21.0/{urllib.parse.quote(page_id)}/feed"
            payload = urllib.parse.urlencode({
                "message": full_message,
                "access_token": token,
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, method="POST")

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        ext_id = data.get("post_id") or data.get("id") or ""
        return {
            "external_id": ext_id,
            "external_url": f"https://www.facebook.com/{ext_id}" if ext_id else "https://www.facebook.com",
        }

    def _publish_to_instagram(self, post, full_message):
        token = (self.access_token or "").strip()
        ig_id = (self.instagram_account_id or "").strip()
        if not token or not ig_id:
            raise UserError(
                _("Please configure Instagram Business Account ID and Access Token on account '%s'.") % self.name
            )
        if not post.image:
            raise UserError(_("Instagram requires an image! Please upload your own image or generate one with AI first."))

        image_url = post.get_public_image_url()
        # Step 1: Create media container
        container_url = f"https://graph.facebook.com/v21.0/{urllib.parse.quote(ig_id)}/media"
        container_payload = urllib.parse.urlencode({
            "image_url": image_url,
            "caption": full_message[:2200],
            "access_token": token,
        }).encode("utf-8")
        req1 = urllib.request.Request(container_url, data=container_payload, method="POST")
        with urllib.request.urlopen(req1, timeout=30) as resp1:
            c_data = json.loads(resp1.read().decode("utf-8"))
        creation_id = c_data.get("id")
        if not creation_id:
            raise UserError(_("Instagram did not return a media container ID: %s") % json.dumps(c_data))

        # Step 2: Publish media container
        pub_url = f"https://graph.facebook.com/v21.0/{urllib.parse.quote(ig_id)}/media_publish"
        pub_payload = urllib.parse.urlencode({
            "creation_id": creation_id,
            "access_token": token,
        }).encode("utf-8")
        req2 = urllib.request.Request(pub_url, data=pub_payload, method="POST")
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            p_data = json.loads(resp2.read().decode("utf-8"))
        ext_id = p_data.get("id", creation_id)
        return {
            "external_id": ext_id,
            "external_url": "https://www.instagram.com",
        }

    def _publish_to_linkedin(self, post, full_message):
        token = (self.access_token or "").strip()
        author_id = (self.linkedin_author_id or "").strip()
        if not token:
            raise UserError(_("Please enter your LinkedIn OAuth 2.0 Access Token on account '%s'.") % self.name)
        if not author_id:
            self.action_verify_connection()
            author_id = (self.linkedin_author_id or "").strip()
        author_urn = (
            author_id
            if author_id.startswith("urn:li:")
            else f"urn:li:{self.linkedin_account_type or 'person'}:{author_id}"
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "User-Agent": "Odoo19-SocialMediaAI/1.0",
        }

        asset_urn = None
        if post.image:
            # Step 1: Register image upload with LinkedIn Assets API
            reg_payload = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": author_urn,
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent",
                        }
                    ],
                }
            }
            reg_req = urllib.request.Request(
                "https://api.linkedin.com/v2/assets?action=registerUpload",
                data=json.dumps(reg_payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(reg_req, timeout=25) as reg_resp:
                reg_data = json.loads(reg_resp.read().decode("utf-8")).get("value", {})
            upload_url = (
                reg_data.get("uploadMechanism", {})
                .get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {})
                .get("uploadUrl")
            )
            asset_urn = reg_data.get("asset")
            if upload_url and asset_urn:
                img_bytes = base64.b64decode(post.image)
                up_req = urllib.request.Request(
                    upload_url,
                    data=img_bytes,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/octet-stream",
                    },
                    method="PUT",
                )
                with urllib.request.urlopen(up_req, timeout=35):
                    pass

        share_content = {
            "shareCommentary": {"text": full_message[:2900]},
            "shareMediaCategory": "IMAGE" if asset_urn else "NONE",
        }
        if asset_urn:
            share_content["media"] = [
                {
                    "status": "READY",
                    "media": asset_urn,
                    "title": {"text": (post.name or "Social Post")[:190]},
                }
            ]

        ugc_payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {"com.linkedin.ugc.ShareContent": share_content},
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        ugc_req = urllib.request.Request(
            "https://api.linkedin.com/v2/ugcPosts",
            data=json.dumps(ugc_payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(ugc_req, timeout=25) as ugc_resp:
            ugc_data = json.loads(ugc_resp.read().decode("utf-8"))
        ext_id = ugc_data.get("id", "")
        return {
            "external_id": ext_id,
            "external_url": f"https://www.linkedin.com/feed/update/{ext_id}" if ext_id else "https://www.linkedin.com",
        }

    def _publish_to_x(self, post, full_message):
        tweet_text = (post.variation_x or full_message or post.name or "").strip()[:280]
        media_id = None

        # Optional image upload to X v1.1 media endpoint when using OAuth 1.0a
        if post.image and self.x_auth_mode == "oauth1":
            try:
                upload_url = "https://upload.twitter.com/1.1/media/upload.json"
                b64_str = post.image.decode("ascii") if isinstance(post.image, bytes) else str(post.image)
                body_params = {"media_data": b64_str}
                auth_header = self._build_x_oauth1_header("POST", upload_url, extra_params=body_params)
                up_req = urllib.request.Request(
                    upload_url,
                    data=urllib.parse.urlencode(body_params).encode("utf-8"),
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/x-www-form-urlencoded",
                        "User-Agent": "Odoo19-SocialMediaAI/1.0",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(up_req, timeout=30) as up_resp:
                    up_data = json.loads(up_resp.read().decode("utf-8"))
                    media_id = up_data.get("media_id_string")
            except Exception as exc:
                _logger.warning("X image upload skipped, posting text tweet: %s", exc)

        tweet_url = "https://api.twitter.com/2/tweets"
        payload = {"text": tweet_text}
        if media_id:
            payload["media"] = {"media_ids": [media_id]}

        if self.x_auth_mode == "oauth1":
            auth_header = self._build_x_oauth1_header("POST", tweet_url)
        else:
            token = (self.access_token or "").strip()
            if not token:
                raise UserError(_("Please configure X OAuth credentials on account '%s'.") % self.name)
            auth_header = f"Bearer {token}"

        req = urllib.request.Request(
            tweet_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json",
                "User-Agent": "Odoo19-SocialMediaAI/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8")).get("data", {})
        ext_id = data.get("id", "")
        return {
            "external_id": ext_id,
            "external_url": f"https://x.com/i/web/status/{ext_id}" if ext_id else "https://x.com",
        }
