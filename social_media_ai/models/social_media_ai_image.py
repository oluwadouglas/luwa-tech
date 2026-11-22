# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SocialMediaAiImage(models.Model):
    _name = "social.media.ai.image"
    _description = "AI Generated & Custom Uploaded Social Media Marketing Image"
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Image Title",
        required=True,
        default="New Marketing Image",
    )
    image_source = fields.Selection(
        [
            ("upload", "Upload My Own Image / Photo"),
            ("ai", "Generate Image with AI"),
        ],
        string="Image Source",
        default="ai",
        required=True,
    )
    custom_image_upload = fields.Binary(
        string="Upload Custom Image File",
        attachment=False,
        help="Upload your own JPG/PNG marketing image from your device.",
    )
    custom_image_filename = fields.Char(string="Uploaded Filename")
    prompt = fields.Text(
        string="Image Description / Prompt",
        help="Describe the marketing visual you want AI to generate.",
    )
    style = fields.Selection(
        [
            ("photorealistic", "Photorealistic Commercial"),
            ("african_business", "African Business & Tech Lifestyle"),
            ("corporate_ad", "Modern Corporate Ad & Brand Graphic"),
            ("digital_illustration", "Vibrant Digital Illustration"),
            ("3d_render", "3D Studio Render"),
            ("minimalist", "Clean Minimalist Showcase"),
        ],
        string="Visual Style",
        default="african_business",
        required=True,
    )
    aspect_ratio = fields.Selection(
        [
            ("1:1", "Square (1:1 • Instagram / Facebook / LinkedIn Feed)"),
            ("16:9", "Landscape (16:9 • X / LinkedIn Banner)"),
            ("4:5", "Portrait (4:5 • Instagram / Facebook Vertical)"),
        ],
        string="Aspect Ratio",
        default="1:1",
        required=True,
    )
    image = fields.Binary(
        string="Marketing Image",
        attachment=True,
    )
    image_filename = fields.Char(
        string="Filename",
        default="ai_marketing_image.jpg",
    )
    attachment_id = fields.Many2one(
        "ir.attachment",
        string="Odoo Attachment",
        readonly=True,
        ondelete="set null",
    )
    post_id = fields.Many2one(
        "social.media.post",
        string="Linked Social Media Post",
        ondelete="set null",
    )
    engine_used = fields.Char(
        string="Image Source / Engine",
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Ready"),
            ("generated", "Saved in Library"),
        ],
        string="Status",
        default="draft",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Created By",
        default=lambda self: self.env.user,
    )
    create_date = fields.Datetime(string="Created On", readonly=True)

    @api.onchange("custom_image_upload")
    def _onchange_custom_image_upload(self):
        for rec in self:
            if rec.custom_image_upload:
                rec.image = rec.custom_image_upload
                rec.image_filename = rec.custom_image_filename or "custom_uploaded_image.jpg"
                rec.image_source = "upload"
                rec.engine_used = "Custom User Upload"
                rec.state = "generated"

    def action_clear_image(self):
        for rec in self:
            rec.write({
                "image": False,
                "custom_image_upload": False,
                "state": "draft",
            })
        return True

    def action_generate_image(self):
        Config = self.env["social.media.ai.config"]
        for rec in self:
            if not (rec.prompt or "").strip():
                raise UserError(_("Please describe the image you want to generate."))
            res = Config.generate_marketing_image(
                image_prompt=rec.prompt,
                aspect_ratio=rec.aspect_ratio or "1:1",
                style=rec.style or "african_business",
                title_overlay=rec.name,
            )
            b64_img = res["image_b64"]
            fname = res.get("filename") or f"ai_image_{rec.id}.jpg"
            if not rec.name or rec.name in ("New AI Marketing Image", "New Marketing Image"):
                rec.name = rec.prompt.strip()[:65]

            attachment = self.env["ir.attachment"].create({
                "name": fname,
                "type": "binary",
                "datas": b64_img,
                "res_model": "social.media.ai.image",
                "res_id": rec.id,
                "mimetype": "image/png" if fname.endswith(".png") else "image/jpeg",
            })
            rec.write({
                "image": b64_img,
                "image_filename": fname,
                "image_source": "ai",
                "attachment_id": attachment.id,
                "engine_used": res.get("engine", "AI Image Engine"),
                "state": "generated",
            })
            if rec.post_id:
                rec.post_id.write({
                    "image": b64_img,
                    "image_filename": fname,
                    "ai_image_id": rec.id,
                    "attachment_ids": [(4, attachment.id)],
                })
        return True

    def action_attach_to_post(self):
        self.ensure_one()
        if not self.image:
            raise UserError(_("Please upload or generate an image first before attaching it to a post."))
        if not self.post_id:
            raise UserError(_("Please select a Linked Social Media Post in the field above, or click 'Create New Post with Image'."))

        vals = {
            "image": self.image,
            "image_filename": self.image_filename or "marketing_image.jpg",
            "ai_image_id": self.id,
        }
        if self.attachment_id:
            vals["attachment_ids"] = [(4, self.attachment_id.id)]
        self.post_id.write(vals)
        return {
            "type": "ir.actions.act_window",
            "name": _("Social Media Post"),
            "res_model": "social.media.post",
            "res_id": self.post_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_create_post_from_image(self):
        self.ensure_one()
        if not self.image and self.prompt:
            self.action_generate_image()
        if not self.image:
            raise UserError(_("Please upload your own image or generate an AI image first."))
        post_vals = {
            "name": self.name or (self.prompt or "New Marketing Post")[:65],
            "ai_prompt": self.prompt or self.name,
            "image_prompt": self.prompt or "",
            "image": self.image,
            "image_filename": self.image_filename,
            "image_source": self.image_source,
            "ai_image_id": self.id,
            "platform": "instagram",
            "state": "draft",
        }
        if self.attachment_id:
            post_vals["attachment_ids"] = [(4, self.attachment_id.id)]
        post = self.env["social.media.post"].create(post_vals)
        self.post_id = post.id
        return {
            "type": "ir.actions.act_window",
            "name": _("Social Media Post"),
            "res_model": "social.media.post",
            "res_id": post.id,
            "view_mode": "form",
            "target": "current",
        }
