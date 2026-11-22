# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SocialMediaAiGenerator(models.Model):
    _name = "social.media.ai.generator"
    _description = "AI Social Media Content & Image Studio"
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Session / Campaign Name",
        default="New AI Content Session",
        required=True,
    )
    prompt = fields.Text(
        string="Content Instruction / Topic",
        required=True,
        help="Describe the marketing post you want AI to create (e.g., 'Promote our E-Commerce & Mobile Money integration for Ugandan retailers').",
    )
    platform = fields.Selection(
        [
            ("facebook", "Facebook"),
            ("instagram", "Instagram"),
            ("linkedin", "LinkedIn"),
            ("x", "X (Twitter)"),
        ],
        string="Primary Platform",
        default="linkedin",
        required=True,
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
        required=True,
    )
    target_audience = fields.Char(
        string="Target Audience",
        default="Business Owners, Founders & Marketing Managers",
        required=True,
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
        required=True,
    )
    scheduled_date = fields.Datetime(
        string="Target Publishing Date",
        default=lambda self: fields.Datetime.now() + timedelta(days=1),
    )

    # Editable Generated Content Fields
    headline = fields.Char(string="Generated Post Headline")
    caption = fields.Text(string="Generated Marketing Caption")
    hashtags = fields.Char(string="Generated Hashtags")
    call_to_action = fields.Char(string="Generated Call to Action")

    variation_facebook = fields.Text(string="Facebook Variation")
    variation_instagram = fields.Text(string="Instagram Variation")
    variation_linkedin = fields.Text(string="LinkedIn Variation")
    variation_x = fields.Text(string="X (Twitter) Variation")

    # AI Image Generation OR Custom Upload inside Studio
    image_source = fields.Selection(
        [
            ("upload", "Upload My Own Image / Photo"),
            ("ai", "Generate Image with AI"),
        ],
        string="Image Source",
        default="upload",
        required=True,
    )
    custom_image_upload = fields.Binary(
        string="Upload Custom Image File",
        attachment=False,
        help="Upload your own image file from your device if you prefer not to use an AI image.",
    )
    custom_image_filename = fields.Char(string="Uploaded Filename")
    image_prompt = fields.Text(string="AI Image Description")
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
        string="Aspect Ratio",
        default="1:1",
    )
    generated_image = fields.Binary(string="Post Image Preview", attachment=True)
    generated_image_filename = fields.Char(string="Image Filename", default="ai_studio_image.jpg")
    ai_image_id = fields.Many2one("social.media.ai.image", string="Saved AI Image", readonly=True)

    engine_used = fields.Char(string="AI Engine Used", readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft Instruction"),
            ("generated", "Content Generated (Editable)"),
            ("saved", "Saved to Posts"),
        ],
        string="Studio Status",
        default="draft",
    )
    created_post_ids = fields.Many2many(
        "social.media.post",
        string="Created Social Media Posts",
        readonly=True,
    )
    created_post_count = fields.Integer(
        string="Created Posts",
        compute="_compute_created_post_count",
    )

    @api.onchange("custom_image_upload")
    def _onchange_custom_image_upload(self):
        for rec in self:
            if rec.custom_image_upload:
                rec.generated_image = rec.custom_image_upload
                rec.generated_image_filename = rec.custom_image_filename or "custom_uploaded_image.jpg"
                rec.image_source = "upload"

    def action_clear_image(self):
        for rec in self:
            rec.write({
                "generated_image": False,
                "custom_image_upload": False,
                "ai_image_id": False,
            })
        return True

    @api.depends("created_post_ids")
    def _compute_created_post_count(self):
        for rec in self:
            rec.created_post_count = len(rec.created_post_ids)

    def action_generate_content(self):
        Config = self.env["social.media.ai.config"]
        for rec in self:
            res = Config.generate_marketing_content(
                prompt=rec.prompt,
                platform=rec.platform,
                tone=rec.tone,
                target_audience=rec.target_audience,
                campaign_objective=rec.campaign_objective,
            )
            rec.write({
                "name": res["headline"][:75],
                "headline": res["headline"],
                "caption": res["caption"],
                "hashtags": res["hashtags"],
                "call_to_action": res["call_to_action"],
                "variation_facebook": res["variation_facebook"],
                "variation_instagram": res["variation_instagram"],
                "variation_linkedin": res["variation_linkedin"],
                "variation_x": res["variation_x"],
                "image_prompt": rec.image_prompt or res.get("suggested_image_prompt", rec.prompt),
                "engine_used": res.get("engine", "AI Engine"),
                "state": "generated",
            })
        return True

    def action_generate_image(self):
        Config = self.env["social.media.ai.config"]
        AiImage = self.env["social.media.ai.image"]
        for rec in self:
            img_prompt = (rec.image_prompt or rec.prompt or "").strip()
            if not img_prompt:
                raise UserError(_("Please enter an AI Image Description or Content Instruction first."))
            res = Config.generate_marketing_image(
                image_prompt=img_prompt,
                aspect_ratio=rec.image_aspect_ratio or "1:1",
                style=rec.image_style or "african_business",
                title_overlay=rec.headline or rec.name,
            )
            b64_img = res["image_b64"]
            fname = res.get("filename") or f"studio_{rec.id}.jpg"
            ai_img = AiImage.create({
                "name": rec.headline or rec.name or img_prompt[:60],
                "prompt": img_prompt,
                "style": rec.image_style or "african_business",
                "aspect_ratio": rec.image_aspect_ratio or "1:1",
                "image": b64_img,
                "image_filename": fname,
                "image_source": "ai",
                "engine_used": res.get("engine", "AI Image Engine"),
                "state": "generated",
            })
            rec.write({
                "generated_image": b64_img,
                "generated_image_filename": fname,
                "image_source": "ai",
                "ai_image_id": ai_img.id,
            })
        return True

    def action_generate_content_and_image(self):
        self.action_generate_content()
        self.action_generate_image()
        return True

    def action_save_as_post(self):
        self.ensure_one()
        if not self.headline and not self.caption:
            self.action_generate_content()

        post_vals = {
            "name": self.headline or self.name,
            "caption": self.caption,
            "hashtags": self.hashtags,
            "call_to_action": self.call_to_action,
            "platform": self.platform,
            "scheduled_date": self.scheduled_date or (fields.Datetime.now() + timedelta(days=1)),
            "state": "draft",
            "ai_prompt": self.prompt,
            "tone": self.tone,
            "target_audience": self.target_audience,
            "campaign_objective": self.campaign_objective,
            "variation_facebook": self.variation_facebook,
            "variation_instagram": self.variation_instagram,
            "variation_linkedin": self.variation_linkedin,
            "variation_x": self.variation_x,
            "image_prompt": self.image_prompt,
            "image_style": self.image_style,
            "image_aspect_ratio": self.image_aspect_ratio,
            "image_source": self.image_source,
            "image": self.generated_image,
            "image_filename": self.generated_image_filename,
            "ai_image_id": self.ai_image_id.id if self.ai_image_id else False,
            "ai_engine_used": self.engine_used,
        }
        post = self.env["social.media.post"].create(post_vals)
        if self.generated_image:
            att = self.env["ir.attachment"].create({
                "name": self.generated_image_filename or "social_post_image.jpg",
                "type": "binary",
                "datas": self.generated_image,
                "res_model": "social.media.post",
                "res_id": post.id,
            })
            post.attachment_ids = [(4, att.id)]
        self.write({
            "state": "saved",
            "created_post_ids": [(4, post.id)],
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Social Media Post"),
            "res_model": "social.media.post",
            "res_id": post.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_save_all_platforms(self):
        self.ensure_one()
        if not self.headline and not self.caption:
            self.action_generate_content()

        platform_map = [
            ("facebook", self.variation_facebook or self.caption),
            ("instagram", self.variation_instagram or self.caption),
            ("linkedin", self.variation_linkedin or self.caption),
            ("x", self.variation_x or self.caption),
        ]
        created_ids = []
        base_date = self.scheduled_date or (fields.Datetime.now() + timedelta(days=1))
        for idx, (plat, body) in enumerate(platform_map):
            post_vals = {
                "name": f"{self.headline or self.name} ({plat.upper()})",
                "caption": body,
                "hashtags": self.hashtags,
                "call_to_action": self.call_to_action,
                "platform": plat,
                "scheduled_date": base_date + timedelta(hours=idx * 2),
                "state": "draft",
                "ai_prompt": self.prompt,
                "tone": self.tone,
                "target_audience": self.target_audience,
                "campaign_objective": self.campaign_objective,
                "variation_facebook": self.variation_facebook,
                "variation_instagram": self.variation_instagram,
                "variation_linkedin": self.variation_linkedin,
                "variation_x": self.variation_x,
                "image_prompt": self.image_prompt,
                "image_source": self.image_source,
                "image": self.generated_image,
                "image_filename": self.generated_image_filename,
                "ai_image_id": self.ai_image_id.id if self.ai_image_id else False,
                "ai_engine_used": self.engine_used,
            }
            post = self.env["social.media.post"].create(post_vals)
            created_ids.append(post.id)

        self.write({
            "state": "saved",
            "created_post_ids": [(4, pid) for pid in created_ids],
        })
        return self.action_view_created_posts()

    def action_view_created_posts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Generated Social Media Posts"),
            "res_model": "social.media.post",
            "view_mode": "kanban,list,calendar,form",
            "domain": [("id", "in", self.created_post_ids.ids)],
            "target": "current",
        }
