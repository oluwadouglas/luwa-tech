# -*- coding: utf-8 -*-
import uuid
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

PLATFORM_COLORS = {
    "facebook": 4,   # Blue
    "instagram": 9,  # Magenta / Pink
    "linkedin": 11,  # Indigo / Deep Blue
    "x": 1,          # Charcoal / Dark
}


class SocialMediaPost(models.Model):
    _name = "social.media.post"
    _description = "Social Media Post"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "scheduled_date desc, create_date desc, id desc"

    name = fields.Char(
        string="Post Title / Headline",
        required=True,
        tracking=True,
        help="Main post title or headline.",
    )
    caption = fields.Text(
        string="Marketing Caption",
        tracking=True,
        help="Primary social media caption body.",
    )
    hashtags = fields.Char(
        string="Hashtags",
        help="Relevant hashtags separated by spaces (e.g. #DigitalMarketing #Kampala).",
    )
    call_to_action = fields.Char(
        string="Call to Action (CTA)",
        help="Action prompt for readers (e.g. Book a free demo at luwatech.it).",
    )
    platform = fields.Selection(
        [
            ("facebook", "Facebook"),
            ("instagram", "Instagram"),
            ("linkedin", "LinkedIn"),
            ("x", "X (Twitter)"),
        ],
        string="Target Platform",
        required=True,
        default="linkedin",
        tracking=True,
    )
    account_id = fields.Many2one(
        "social.media.account",
        string="Connected Social Account",
        domain="[('platform', '=', platform)]",
        tracking=True,
        help="Select the connected social media account to publish this post directly.",
    )
    account_ids = fields.Many2many(
        "social.media.account",
        "social_media_post_account_rel",
        "post_id",
        "account_id",
        string="Cross-Post to Multiple Accounts",
        help="Optional: select additional connected social accounts to publish to simultaneously.",
    )
    auto_publish = fields.Boolean(
        string="Auto-Publish on Scheduled Date",
        default=True,
        help="When enabled and linked to a Connected Social Account, the scheduled cron job will automatically publish this post at the Scheduled Publishing Date.",
    )
    scheduled_date = fields.Datetime(
        string="Scheduled Publishing Date",
        default=lambda self: fields.Datetime.now() + timedelta(days=1),
        tracking=True,
        index=True,
    )
    published_date = fields.Datetime(
        string="Actual Published Date",
        readonly=True,
        tracking=True,
    )
    external_post_id = fields.Char(
        string="Platform Post ID",
        readonly=True,
        copy=False,
    )
    external_post_url = fields.Char(
        string="Live Post URL",
        readonly=True,
        copy=False,
    )
    publish_error = fields.Text(
        string="Last Publishing Error",
        readonly=True,
        copy=False,
    )
    media_access_token = fields.Char(
        string="Media Access Token",
        default=lambda self: uuid.uuid4().hex,
        copy=False,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending_approval", "Pending Approval"),
            ("approved", "Approved"),
            ("scheduled", "Scheduled"),
            ("published", "Published"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    create_date = fields.Datetime(
        string="Creation Date",
        readonly=True,
    )

    # Image & Custom Upload Management
    image_source = fields.Selection(
        [
            ("upload", "Upload My Own Image / Photo"),
            ("ai", "Generate Image with AI"),
            ("library", "Choose from Saved Media Library"),
        ],
        string="Image Source",
        default="upload",
        required=True,
    )
    image = fields.Binary(
        string="Post Image",
        attachment=True,
    )
    image_filename = fields.Char(
        string="Image Filename",
        default="social_post_image.jpg",
    )
    custom_image_upload = fields.Binary(
        string="Upload Custom Image File",
        attachment=False,
        help="Click here to upload your own image (JPG, PNG, WEBP) from your computer or phone instead of using an AI image.",
    )
    custom_image_filename = fields.Char(string="Uploaded Filename")
    ai_image_id = fields.Many2one(
        "social.media.ai.image",
        string="Saved Media Library Image",
        ondelete="set null",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "social_media_post_ir_attachment_rel",
        "post_id",
        "attachment_id",
        string="Additional Media Attachments",
    )

    # AI Content Generation Controls
    ai_prompt = fields.Text(
        string="AI Content Instruction",
        help="Enter a simple instruction describing the post you want AI to write.",
    )
    tone = fields.Selection(
        [
            ("professional", "Professional & Authoritative"),
            ("engaging", "Engaging & Conversational"),
            ("persuasive", "Bold & Persuasive"),
            ("educational", "Educational & Value-Driven"),
            ("storytelling", "Inspiring & Storytelling"),
            ("promotional", "Urgent & Promotional"),
            ("humorous", "Witty & Lighthearted"),
        ],
        string="Content Tone",
        default="professional",
    )
    target_audience = fields.Char(
        string="Target Audience",
        default="Business Owners, Founders & Marketing Leaders",
    )
    campaign_objective = fields.Selection(
        [
            ("brand_awareness", "Brand Awareness & Reach"),
            ("lead_generation", "Lead Generation & Inquiries"),
            ("product_launch", "Product / Feature Launch"),
            ("website_traffic", "Website & Store Traffic"),
            ("engagement", "Community Engagement & Comments"),
            ("sales_conversion", "Direct Sales & Subscriptions"),
            ("event_promotion", "Event / Webinar / Training Promotion"),
        ],
        string="Campaign Objective",
        default="lead_generation",
    )

    # Platform-Specific Variations Generated by AI
    variation_facebook = fields.Text(string="Facebook Variation")
    variation_instagram = fields.Text(string="Instagram Variation")
    variation_linkedin = fields.Text(string="LinkedIn Variation")
    variation_x = fields.Text(string="X (Twitter) Variation")

    # Inline AI Image Generation Controls
    image_prompt = fields.Text(
        string="AI Image Description",
        help="Describe the marketing visual you want AI to create for this post.",
    )
    image_style = fields.Selection(
        [
            ("photorealistic", "Photorealistic Commercial"),
            ("african_business", "African Business & Tech Lifestyle"),
            ("corporate_ad", "Modern Corporate Ad & Brand Graphic"),
            ("digital_illustration", "Vibrant Digital Illustration"),
            ("3d_render", "3D Studio Render"),
            ("minimalist", "Clean Minimalist Showcase"),
        ],
        string="Image Style",
        default="african_business",
    )
    image_aspect_ratio = fields.Selection(
        [
            ("1:1", "Square (1:1)"),
            ("16:9", "Landscape (16:9)"),
            ("4:5", "Portrait (4:5)"),
        ],
        string="Image Aspect Ratio",
        default="1:1",
    )
    ai_engine_used = fields.Char(string="Last AI Engine Used", readonly=True)

    # Ownership & UI Helpers
    user_id = fields.Many2one(
        "res.users",
        string="Author / Responsible",
        default=lambda self: self.env.user,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    color = fields.Integer(
        string="Color Index",
        compute="_compute_color",
        store=True,
    )
    full_post_preview = fields.Text(
        string="Complete Post Preview",
        compute="_compute_full_post_preview",
    )

    @api.onchange("platform")
    def _onchange_platform_select_account(self):
        for rec in self:
            if rec.platform and (not rec.account_id or rec.account_id.platform != rec.platform):
                acc = self.env["social.media.account"].search(
                    [("platform", "=", rec.platform)],
                    order="state asc, sequence asc, id asc",
                    limit=1,
                )
                rec.account_id = acc.id if acc else False

    @api.onchange("custom_image_upload")
    def _onchange_custom_image_upload(self):
        for rec in self:
            if rec.custom_image_upload:
                rec.image = rec.custom_image_upload
                rec.image_filename = rec.custom_image_filename or "custom_uploaded_image.jpg"
                rec.image_source = "upload"
                rec.ai_engine_used = "Custom User Uploaded Image"

    @api.onchange("ai_image_id")
    def _onchange_ai_image_id(self):
        for rec in self:
            if rec.ai_image_id and rec.ai_image_id.image:
                rec.image = rec.ai_image_id.image
                rec.image_filename = rec.ai_image_id.image_filename or "library_image.jpg"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("custom_image_upload") and not vals.get("image"):
                vals["image"] = vals["custom_image_upload"]
                vals["image_filename"] = vals.get("custom_image_filename") or "custom_uploaded_image.jpg"
            if not vals.get("account_id") and vals.get("platform"):
                acc = self.env["social.media.account"].search(
                    [("platform", "=", vals["platform"])],
                    limit=1,
                )
                if acc:
                    vals["account_id"] = acc.id
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("custom_image_upload"):
            vals["image"] = vals["custom_image_upload"]
            vals["image_filename"] = vals.get("custom_image_filename") or "custom_uploaded_image.jpg"
            vals["ai_engine_used"] = "Custom User Uploaded Image"
        return super().write(vals)

    def action_clear_image(self):
        for rec in self:
            rec.write({
                "image": False,
                "custom_image_upload": False,
                "ai_image_id": False,
                "image_source": "upload",
            })
        return True

    def get_public_image_url(self):
        self.ensure_one()
        if not self.media_access_token:
            self.sudo().media_access_token = uuid.uuid4().hex
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "https://www.luwatech.it").rstrip("/")
        return f"{base_url}/social_media_ai/media/{self.id}/{self.media_access_token}.jpg"

    @api.depends("platform")
    def _compute_color(self):
        for rec in self:
            rec.color = PLATFORM_COLORS.get(rec.platform, 4)

    @api.depends("name", "caption", "call_to_action", "hashtags")
    def _compute_full_post_preview(self):
        for rec in self:
            parts = []
            if rec.name:
                parts.append(rec.name)
            if rec.caption:
                parts.append(rec.caption)
            if rec.call_to_action:
                parts.append(f"👉 {rec.call_to_action}")
            if rec.hashtags:
                parts.append(rec.hashtags)
            rec.full_post_preview = "\n\n".join(parts)

    # -------------------------------------------------------------------------
    # AI GENERATION ACTIONS ON POST
    # -------------------------------------------------------------------------
    def action_generate_ai_content(self):
        Config = self.env["social.media.ai.config"]
        for rec in self:
            instruction = (rec.ai_prompt or rec.name or "").strip()
            if not instruction:
                raise UserError(_("Please enter an AI Content Instruction (or Post Title) first."))
            result = Config.generate_marketing_content(
                prompt=instruction,
                platform=rec.platform or "linkedin",
                tone=rec.tone or "professional",
                target_audience=rec.target_audience or "Business Owners & Customers",
                campaign_objective=rec.campaign_objective or "lead_generation",
            )
            rec.write({
                "name": result["headline"],
                "caption": result["caption"],
                "hashtags": result["hashtags"],
                "call_to_action": result["call_to_action"],
                "variation_facebook": result["variation_facebook"],
                "variation_instagram": result["variation_instagram"],
                "variation_linkedin": result["variation_linkedin"],
                "variation_x": result["variation_x"],
                "image_prompt": rec.image_prompt or result.get("suggested_image_prompt", instruction),
                "ai_engine_used": result.get("engine", "AI Engine"),
            })
            rec.message_post(
                body=_("✨ AI Content generated via <b>%s</b> for <b>%s</b>.")
                % (result.get("engine", "AI Engine"), rec.platform.upper())
            )
        return True

    def action_generate_ai_image(self):
        Config = self.env["social.media.ai.config"]
        AiImage = self.env["social.media.ai.image"]
        for rec in self:
            img_prompt = (rec.image_prompt or rec.ai_prompt or rec.name or "").strip()
            if not img_prompt:
                raise UserError(_("Please enter an AI Image Description (or Content Instruction) first."))
            res = Config.generate_marketing_image(
                image_prompt=img_prompt,
                aspect_ratio=rec.image_aspect_ratio or "1:1",
                style=rec.image_style or "african_business",
                title_overlay=rec.name,
            )
            b64_img = res["image_b64"]
            fname = res.get("filename") or f"post_{rec.id}_ai.jpg"

            ai_img_record = AiImage.create({
                "name": rec.name or img_prompt[:60],
                "prompt": img_prompt,
                "style": rec.image_style or "african_business",
                "aspect_ratio": rec.image_aspect_ratio or "1:1",
                "image": b64_img,
                "image_filename": fname,
                "post_id": rec.id,
                "engine_used": res.get("engine", "AI Image Engine"),
                "state": "generated",
            })
            attachment = self.env["ir.attachment"].create({
                "name": fname,
                "type": "binary",
                "datas": b64_img,
                "res_model": "social.media.post",
                "res_id": rec.id,
                "mimetype": "image/png" if fname.endswith(".png") else "image/jpeg",
            })
            ai_img_record.attachment_id = attachment.id

            rec.write({
                "image": b64_img,
                "image_filename": fname,
                "image_source": "ai",
                "ai_image_id": ai_img_record.id,
                "attachment_ids": [(4, attachment.id)],
                "ai_engine_used": res.get("engine", "AI Image Engine"),
            })
            rec.message_post(
                body=_("🎨 AI Marketing Image generated and attached via <b>%s</b>.")
                % res.get("engine", "AI Image Engine")
            )
        return True

    def action_generate_both_ai(self):
        self.action_generate_ai_content()
        self.action_generate_ai_image()
        return True

    def action_use_facebook_variation(self):
        for rec in self:
            if rec.variation_facebook:
                rec.write({"platform": "facebook", "caption": rec.variation_facebook})
                rec._onchange_platform_select_account()
        return True

    def action_use_instagram_variation(self):
        for rec in self:
            if rec.variation_instagram:
                rec.write({"platform": "instagram", "caption": rec.variation_instagram})
                rec._onchange_platform_select_account()
        return True

    def action_use_linkedin_variation(self):
        for rec in self:
            if rec.variation_linkedin:
                rec.write({"platform": "linkedin", "caption": rec.variation_linkedin})
                rec._onchange_platform_select_account()
        return True

    def action_use_x_variation(self):
        for rec in self:
            if rec.variation_x:
                rec.write({"platform": "x", "caption": rec.variation_x})
                rec._onchange_platform_select_account()
        return True

    # -------------------------------------------------------------------------
    # POST LIFECYCLE & DIRECT SOCIAL PUBLISHING ACTIONS
    # -------------------------------------------------------------------------
    def action_submit_approval(self):
        self.write({"state": "pending_approval"})
        return True

    def action_approve(self):
        self.write({"state": "approved"})
        return True

    def action_schedule(self):
        for rec in self:
            if not rec.scheduled_date:
                rec.scheduled_date = fields.Datetime.now() + timedelta(days=1)
            rec.state = "scheduled"
        return True

    def action_publish_now(self):
        """Publish directly to the connected social media account(s) via API."""
        for rec in self:
            target_accounts = rec.account_ids or rec.account_id
            if not target_accounts:
                acc = self.env["social.media.account"].search(
                    [("platform", "=", rec.platform), ("state", "=", "connected")],
                    limit=1,
                )
                if acc:
                    rec.account_id = acc.id
                    target_accounts = acc
                else:
                    raise UserError(
                        _(
                            "No connected %s account selected!\n\n"
                            "Go to Social Media AI → Social Accounts to connect your %s credentials, "
                            "or click 'Mark as Published (Manual)' if you posted it manually."
                        )
                        % (rec.platform.upper(), rec.platform.upper())
                    )

            published_links = []
            last_ext_id = ""
            last_ext_url = ""
            try:
                for acc in target_accounts:
                    res = acc.publish_post_to_platform(rec)
                    last_ext_id = res.get("external_id", "")
                    last_ext_url = res.get("external_url", "")
                    published_links.append(f"{acc.name} ({last_ext_id or 'OK'})")

                rec.write({
                    "state": "published",
                    "published_date": fields.Datetime.now(),
                    "external_post_id": last_ext_id,
                    "external_post_url": last_ext_url,
                    "publish_error": False,
                })
                rec.message_post(
                    body=_("🚀 Published directly via API to: <b>%s</b>. Live URL: %s")
                    % (", ".join(published_links), last_ext_url or "N/A")
                )
            except Exception as exc:
                rec.write({"publish_error": str(exc)})
                raise

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Published to Social Media!"),
                "message": _("Your post has been published live to your connected account."),
                "type": "success",
                "sticky": False,
            },
        }

    def action_publish(self):
        """Manual status transition to Published."""
        self.write({
            "state": "published",
            "published_date": fields.Datetime.now(),
        })
        for rec in self:
            rec.message_post(body=_("✅ Post marked as Published for %s.") % rec.platform.upper())
        return True

    def action_reset_draft(self):
        self.write({"state": "draft"})
        return True

    @api.model
    def _cron_publish_scheduled_posts(self):
        """Automated scheduled post publisher for connected social accounts."""
        now = fields.Datetime.now()
        due_posts = self.search([
            ("state", "=", "scheduled"),
            ("auto_publish", "=", True),
            ("scheduled_date", "<=", now),
        ])
        for post in due_posts:
            target_accounts = post.account_ids or post.account_id
            connected = target_accounts.filtered(lambda a: a.state == "connected")
            if not connected:
                continue
            try:
                post.action_publish_now()
            except Exception as exc:
                post.sudo().write({"publish_error": str(exc)})

    # -------------------------------------------------------------------------
    # DASHBOARD DATA PROVIDER (OWL DASHBOARD RPC)
    # -------------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self):
        Post = self.sudo()
        AiImage = self.env["social.media.ai.image"].sudo()
        Account = self.env["social.media.account"].sudo()

        total_posts = Post.search_count([])
        draft_posts = Post.search_count([("state", "=", "draft")])
        pending_posts = Post.search_count([("state", "=", "pending_approval")])
        approved_posts = Post.search_count([("state", "=", "approved")])
        scheduled_posts = Post.search_count([("state", "=", "scheduled")])
        published_posts = Post.search_count([("state", "=", "published")])
        total_images = AiImage.search_count([])
        connected_accounts = Account.search_count([("state", "=", "connected")])
        total_accounts = Account.search_count([])

        platform_counts = {
            "facebook": Post.search_count([("platform", "=", "facebook")]),
            "instagram": Post.search_count([("platform", "=", "instagram")]),
            "linkedin": Post.search_count([("platform", "=", "linkedin")]),
            "x": Post.search_count([("platform", "=", "x")]),
        }

        recent_records = Post.search([], order="create_date desc, id desc", limit=6)
        upcoming_records = Post.search(
            [("state", "in", ["scheduled", "approved", "pending_approval"])],
            order="scheduled_date asc, id desc",
            limit=6,
        )

        def _serialize_post(p):
            return {
                "id": p.id,
                "name": p.name or "Untitled Post",
                "caption_snippet": (p.caption or "")[:110] + ("..." if len(p.caption or "") > 110 else ""),
                "platform": p.platform,
                "platform_label": dict(self._fields["platform"].selection).get(p.platform, p.platform),
                "state": p.state,
                "state_label": dict(self._fields["state"].selection).get(p.state, p.state),
                "scheduled_date": fields.Datetime.to_string(p.scheduled_date) if p.scheduled_date else "",
                "create_date": fields.Datetime.to_string(p.create_date) if p.create_date else "",
                "has_image": bool(p.image),
                "image_url": f"/web/image/social.media.post/{p.id}/image" if p.image else "",
                "hashtags": p.hashtags or "",
            }

        cfg = self.env["social.media.ai.config"].get_solo()
        has_openai_key = bool((cfg.openai_api_key or "").strip())

        return {
            "kpis": {
                "total": total_posts,
                "draft": draft_posts,
                "pending_approval": pending_posts,
                "approved": approved_posts,
                "scheduled": scheduled_posts,
                "published": published_posts,
                "ai_images": total_images,
                "connected_accounts": connected_accounts,
                "total_accounts": total_accounts,
            },
            "platforms": platform_counts,
            "recent_posts": [_serialize_post(p) for p in recent_records],
            "upcoming_posts": [_serialize_post(p) for p in upcoming_records],
            "ai_status": {
                "text_engine": "OpenAI API (" + (cfg.openai_model or "gpt-4o-mini") + ")"
                if has_openai_key
                else "Free OpenAI-Compatible AI (Active • Ready)",
                "image_engine": "OpenAI DALL-E (" + (cfg.openai_image_model or "dall-e-3") + ")"
                if has_openai_key
                else "Free Flux AI Image Studio (Active • Ready)",
            },
        }
