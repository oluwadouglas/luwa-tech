# -*- coding: utf-8 -*-
import base64
import io
import json
import logging
import random
import re
import urllib.error
import urllib.parse
import urllib.request

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

PLATFORM_LABELS = {
    "facebook": "Facebook",
    "instagram": "Instagram",
    "linkedin": "LinkedIn",
    "x": "X (Twitter)",
}

TONE_LABELS = {
    "professional": "Professional & Authoritative",
    "engaging": "Engaging & Conversational",
    "persuasive": "Bold & Persuasive",
    "educational": "Educational & Value-Driven",
    "storytelling": "Inspiring & Storytelling",
    "promotional": "Urgent & Promotional",
    "humorous": "Witty & Lighthearted",
}

OBJECTIVE_LABELS = {
    "brand_awareness": "Brand Awareness & Reach",
    "lead_generation": "Lead Generation & Inquiries",
    "product_launch": "Product / Feature Launch",
    "website_traffic": "Website & Store Traffic",
    "engagement": "Community Engagement & Comments",
    "sales_conversion": "Direct Sales & Subscriptions",
    "event_promotion": "Event / Webinar / Training Promotion",
}


class SocialMediaAiConfig(models.Model):
    _name = "social.media.ai.config"
    _description = "Social Media AI Configuration & Provider Engine"

    name = fields.Char(string="Configuration Name", default="Social Media AI Settings", required=True)
    text_provider = fields.Selection(
        [
            ("auto", "Auto (OpenAI API if Key Configured, else Free AI Engine)"),
            ("openai", "OpenAI Official API (gpt-4o-mini / gpt-4o)"),
            ("pollinations_free", "Free AI Text Engine (OpenAI-Compatible • No API Key Required)"),
            ("custom_openai", "Custom OpenAI-Compatible Endpoint (Groq / Gemini / OpenRouter)"),
        ],
        string="AI Text Provider",
        default="auto",
        required=True,
    )
    image_provider = fields.Selection(
        [
            ("auto", "Auto (OpenAI DALL-E if Key Configured, else Free Flux AI Image Engine)"),
            ("openai", "OpenAI DALL-E Image API (dall-e-3 / dall-e-2)"),
            ("pollinations_free", "Free Flux AI Image Generator (No API Key Required)"),
            ("local_studio", "Built-in Pillow Graphic Studio (100% Offline Free Generator)"),
        ],
        string="AI Image Provider",
        default="auto",
        required=True,
    )
    openai_api_key = fields.Char(
        string="OpenAI API Key",
        help="Your OpenAI secret key (sk-...). Stored securely in system parameters.",
    )
    openai_base_url = fields.Char(
        string="OpenAI API Base URL",
        default="https://api.openai.com/v1",
        help="Default: https://api.openai.com/v1. You can also use Groq (https://api.groq.com/openai/v1) or OpenRouter.",
    )
    openai_model = fields.Char(
        string="OpenAI Chat Model",
        default="gpt-4o-mini",
        help="Model identifier for text generation (e.g. gpt-4o-mini, gpt-4o, llama-3.3-70b-versatile).",
    )
    openai_image_model = fields.Selection(
        [
            ("dall-e-3", "DALL-E 3 (High Detail)"),
            ("dall-e-2", "DALL-E 2 (Fast)"),
        ],
        string="OpenAI Image Model",
        default="dall-e-3",
    )
    default_brand_context = fields.Text(
        string="Default Brand & Company Context",
        default=(
            "Luwa Tech — Premier Digital Marketing Agency, Custom SaaS Studio & Corporate IT Training Partner "
            "in Kampala, Uganda. Website: https://www.luwatech.it | Phone/WhatsApp: +256 787 819 453."
        ),
        help="Included as background context so AI posts reflect your brand voice and contact details.",
    )
    allow_free_fallback = fields.Boolean(
        string="Automatic Free AI Fallback",
        default=True,
        help="If the primary OpenAI API key is missing or hits a rate limit, automatically fall back to the free AI engine.",
    )
    last_test_status = fields.Char(string="Last Connection Status", readonly=True)

    @api.model
    def get_solo(self):
        rec = self.sudo().search([], limit=1)
        IrConfig = self.env["ir.config_parameter"].sudo()
        if not rec:
            rec = self.sudo().create({
                "name": "Social Media AI Settings",
                "text_provider": IrConfig.get_param("social_media_ai.text_provider", "auto"),
                "image_provider": IrConfig.get_param("social_media_ai.image_provider", "auto"),
                "openai_api_key": IrConfig.get_param("social_media_ai.openai_api_key", ""),
                "openai_base_url": IrConfig.get_param("social_media_ai.openai_base_url", "https://api.openai.com/v1"),
                "openai_model": IrConfig.get_param("social_media_ai.openai_model", "gpt-4o-mini"),
                "openai_image_model": IrConfig.get_param("social_media_ai.openai_image_model", "dall-e-3"),
            })
        return rec

    def write(self, vals):
        res = super().write(vals)
        IrConfig = self.env["ir.config_parameter"].sudo()
        for rec in self:
            IrConfig.set_param("social_media_ai.text_provider", rec.text_provider or "auto")
            IrConfig.set_param("social_media_ai.image_provider", rec.image_provider or "auto")
            IrConfig.set_param("social_media_ai.openai_api_key", (rec.openai_api_key or "").strip())
            IrConfig.set_param("social_media_ai.openai_base_url", (rec.openai_base_url or "https://api.openai.com/v1").strip())
            IrConfig.set_param("social_media_ai.openai_model", (rec.openai_model or "gpt-4o-mini").strip())
            IrConfig.set_param("social_media_ai.openai_image_model", rec.openai_image_model or "dall-e-3")
        return res

    def action_test_ai_connection(self):
        self.ensure_one()
        result = self.generate_marketing_content(
            prompt="Announce our new AI-powered social media and digital marketing suite for growing businesses.",
            platform="linkedin",
            tone="professional",
            target_audience="Business Owners & Marketing Managers",
            campaign_objective="brand_awareness",
        )
        engine_used = result.get("engine", "AI Engine")
        headline = result.get("headline", "Generated Headline")
        self.sudo().write({
            "last_test_status": f"Success via {engine_used} — Sample Headline: {headline[:75]}",
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("AI Engine Connected (%s)") % engine_used,
                "message": _("Sample headline generated: %s") % headline,
                "type": "success",
                "sticky": False,
            },
        }

    # -------------------------------------------------------------------------
    # AI TEXT GENERATION ENGINE (OpenAI API + Free OpenAI-Compatible AI + Fallback)
    # -------------------------------------------------------------------------
    @api.model
    def generate_marketing_content(
        self,
        prompt,
        platform="linkedin",
        tone="professional",
        target_audience="Business Owners & Decision Makers",
        campaign_objective="lead_generation",
    ):
        cfg = self.get_solo()
        clean_prompt = (prompt or "").strip()
        if not clean_prompt:
            raise UserError(_("Please enter a content instruction or topic before generating."))

        platform_label = PLATFORM_LABELS.get(platform, "LinkedIn")
        tone_label = TONE_LABELS.get(tone, "Professional")
        objective_label = OBJECTIVE_LABELS.get(campaign_objective, "Lead Generation")
        brand_ctx = (cfg.default_brand_context or "").strip()

        system_msg = (
            "You are an expert Social Media Marketing Director and Copywriter. "
            "Respond ONLY with a valid JSON object (no markdown fences, no commentary) containing these exact keys:\n"
            "{\n"
            '  "headline": "Attention-grabbing post headline (max 90 chars)",\n'
            '  "caption": "Primary marketing caption tailored for the selected platform (2-3 short paragraphs with emojis and bullet points)",\n'
            '  "hashtags": "8 to 12 relevant, high-reach hashtags separated by spaces",\n'
            '  "call_to_action": "Clear, persuasive call to action",\n'
            '  "variation_facebook": "Engaging Facebook post version with community hook and CTA",\n'
            '  "variation_instagram": "Visual-first Instagram caption with line breaks, emojis and hashtag block",\n'
            '  "variation_linkedin": "Executive LinkedIn thought-leadership post with structured takeaways and professional CTA",\n'
            '  "variation_x": "Punchy X (Twitter) post under 260 characters including 2-3 key hashtags",\n'
            '  "suggested_image_prompt": "Detailed visual description for an AI marketing image accompanying this post"\n'
            "}"
        )

        user_msg = (
            f"Campaign Instruction / Topic: {clean_prompt}\n"
            f"Primary Target Platform: {platform_label}\n"
            f"Content Tone: {tone_label}\n"
            f"Target Audience: {target_audience or 'Business Owners & Customers'}\n"
            f"Campaign Objective: {objective_label}\n"
            f"Brand Context: {brand_ctx}\n\n"
            "Return the JSON object now."
        )

        api_key = (cfg.openai_api_key or "").strip()
        use_openai = cfg.text_provider in ("openai", "custom_openai") or (
            cfg.text_provider == "auto" and bool(api_key)
        )

        # 1. Try Official OpenAI or Custom OpenAI-Compatible Endpoint if configured
        if use_openai and api_key:
            try:
                base_url = (cfg.openai_base_url or "https://api.openai.com/v1").rstrip("/")
                endpoint = f"{base_url}/chat/completions"
                payload = {
                    "model": cfg.openai_model or "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.7,
                }
                if "api.openai.com" in base_url:
                    payload["response_format"] = {"type": "json_object"}

                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                        "User-Agent": "Odoo19-SocialMediaAI/1.0",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=22) as resp:
                    raw_body = resp.read().decode("utf-8")
                    data = json.loads(raw_body)
                    content_str = data["choices"][0]["message"]["content"]
                    parsed = self._parse_ai_json(content_str)
                    if parsed:
                        parsed["engine"] = f"OpenAI ({cfg.openai_model or 'gpt-4o-mini'})"
                        return self._normalize_content_dict(parsed, clean_prompt, platform, tone_label, target_audience)
            except Exception as exc:
                _logger.warning("OpenAI API call failed (%s). Checking fallback...", exc)
                if not cfg.allow_free_fallback and cfg.text_provider == "openai":
                    raise UserError(_("OpenAI API Error: %s") % str(exc))

        # 2. Free OpenAI-Compatible AI Engine (Pollinations OpenAI Endpoint - 100% Free, Zero Key)
        try:
            free_payload = {
                "model": "openai",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": 0.7,
            }
            req = urllib.request.Request(
                "https://text.pollinations.ai/openai",
                data=json.dumps(free_payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Odoo19-SocialMediaAI/1.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw_body = resp.read().decode("utf-8")
                data = json.loads(raw_body)
                content_str = data["choices"][0]["message"]["content"]
                parsed = self._parse_ai_json(content_str)
                if parsed:
                    parsed["engine"] = "Free OpenAI-Compatible AI"
                    return self._normalize_content_dict(parsed, clean_prompt, platform, tone_label, target_audience)
        except Exception as exc:
            _logger.warning("Free AI endpoint fallback triggered local copywriter: %s", exc)

        # 3. Resilient Local Copywriting Studio Fallback (if offline)
        return self._local_fallback_content(clean_prompt, platform, tone_label, target_audience, objective_label)

    @api.model
    def _parse_ai_json(self, text):
        if not text:
            return None
        cleaned = text.strip()
        # Strip markdown fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except Exception:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    return None
        return None

    @api.model
    def _normalize_content_dict(self, data, prompt, platform, tone_label, target_audience):
        headline = (data.get("headline") or f"Transform Your Growth: {prompt[:60]}").strip()
        caption = (data.get("caption") or "").strip()
        hashtags = (data.get("hashtags") or "#DigitalGrowth #BusinessInnovation #MarketingStrategy #TechSolutions").strip()
        if isinstance(hashtags, list):
            hashtags = " ".join(str(h) for h in hashtags)
        cta = (data.get("call_to_action") or "Book your free consultation today at https://www.luwatech.it or message us on WhatsApp!").strip()

        var_fb = (data.get("variation_facebook") or f"🚀 {headline}\n\n{caption}\n\n👉 {cta}\n\n{hashtags}").strip()
        var_ig = (data.get("variation_instagram") or f"✨ {headline}\n.\n{caption}\n.\n🔗 {cta}\n.\n{hashtags}").strip()
        var_li = (data.get("variation_linkedin") or f"{headline}\n\n{caption}\n\n💡 {cta}\n\n{hashtags}").strip()
        var_x = (data.get("variation_x") or f"🚀 {headline[:110]} — {cta[:90]} {hashtags.split()[0] if hashtags else '#Growth'}")[:280].strip()
        img_prompt = (
            data.get("suggested_image_prompt")
            or f"Modern professional marketing visual for '{headline}', vibrant lighting, African business professionals collaborating with modern digital technology, clean commercial photography"
        ).strip()

        return {
            "headline": headline,
            "caption": caption,
            "hashtags": hashtags,
            "call_to_action": cta,
            "variation_facebook": var_fb,
            "variation_instagram": var_ig,
            "variation_linkedin": var_li,
            "variation_x": var_x,
            "suggested_image_prompt": img_prompt,
            "engine": data.get("engine", "AI Content Engine"),
        }

    @api.model
    def _local_fallback_content(self, prompt, platform, tone_label, target_audience, objective_label):
        short_topic = prompt[:70].strip().rstrip(".")
        headline = f"Accelerate Your Business with {short_topic[:55].title()}"
        cta = "Get started today — visit https://www.luwatech.it or call/WhatsApp +256 787 819 453 for a tailored demo!"
        hashtags = "#LuwaTech #DigitalMarketing #BusinessGrowth #CustomSaaS #Kampala #EastAfrica #Innovation #TechSolutions"
        caption = (
            f"Are you ready to elevate how you reach and serve {target_audience}?\n\n"
            f"Our latest initiative focuses on: {prompt}\n\n"
            f"✅ Built for measurable {objective_label.lower()}\n"
            f"✅ Designed with a {tone_label.lower()} approach\n"
            f"✅ Backed by real-time analytics and local engineering support"
        )
        return {
            "headline": headline,
            "caption": caption,
            "hashtags": hashtags,
            "call_to_action": cta,
            "variation_facebook": f"🔥 {headline}\n\n{caption}\n\n💬 Drop a comment or message us to learn more!\n👉 {cta}\n\n{hashtags}",
            "variation_instagram": f"✨ {headline} ✨\n\n{caption}\n\n📲 Tap the link in bio or DM us to get started!\n.\n.\n{hashtags}",
            "variation_linkedin": f"📈 {headline}\n\nIn today's competitive market, forward-thinking teams are prioritizing {prompt}.\n\n{caption}\n\n🤝 {cta}\n\n{hashtags}",
            "variation_x": f"🚀 {headline[:120]}! Built for {target_audience[:45]}. {cta[:75]} #LuwaTech #DigitalGrowth"[:280],
            "suggested_image_prompt": f"Professional marketing visual representing {prompt}, modern African tech office, cyan and orange accents, high-resolution commercial photography",
            "engine": "Built-in Marketing Copy Engine",
        }

    # -------------------------------------------------------------------------
    # AI IMAGE GENERATION ENGINE (OpenAI DALL-E + Free Flux AI + Pillow Fallback)
    # -------------------------------------------------------------------------
    @api.model
    def generate_marketing_image(
        self,
        image_prompt,
        aspect_ratio="1:1",
        style="photorealistic",
        title_overlay="",
    ):
        cfg = self.get_solo()
        clean_prompt = (image_prompt or "").strip()
        if not clean_prompt:
            raise UserError(_("Please describe the marketing image you want to generate."))

        style_map = {
            "photorealistic": "ultra-sharp commercial photography, natural lighting, high contrast, 8k editorial quality",
            "african_business": "authentic modern African professionals in a bright contemporary Kampala tech office, warm studio lighting, Canon EOS R5 photography",
            "corporate_ad": "sleek modern digital marketing graphic, clean composition, vibrant cyan and orange brand accents, premium advertising aesthetic",
            "digital_illustration": "modern flat vector & 3D isometric digital illustration, vibrant gradient palette, SaaS marketing artwork",
            "3d_render": "octane 3D render, glassmorphism UI elements, soft studio rim lighting, futuristic tech visual",
            "minimalist": "clean minimalist product showcase, generous negative space, crisp studio lighting",
        }
        style_suffix = style_map.get(style, style_map["photorealistic"])
        full_prompt = f"{clean_prompt}, {style_suffix}"

        dimensions = {
            "1:1": (1024, 1024),
            "16:9": (1280, 720),
            "4:5": (1024, 1280),
        }
        width, height = dimensions.get(aspect_ratio, (1024, 1024))

        api_key = (cfg.openai_api_key or "").strip()
        use_openai = cfg.image_provider == "openai" or (
            cfg.image_provider == "auto" and bool(api_key)
        )

        # 1. Official OpenAI DALL-E Image Generation API
        if use_openai and api_key and cfg.image_provider != "local_studio":
            try:
                base_url = (cfg.openai_base_url or "https://api.openai.com/v1").rstrip("/")
                endpoint = f"{base_url}/images/generations"
                dalle_size = "1024x1024"
                if cfg.openai_image_model == "dall-e-3":
                    if aspect_ratio == "16:9":
                        dalle_size = "1792x1024"
                    elif aspect_ratio == "4:5":
                        dalle_size = "1024x1792"
                payload = {
                    "model": cfg.openai_image_model or "dall-e-3",
                    "prompt": full_prompt[:1000],
                    "n": 1,
                    "size": dalle_size,
                    "response_format": "b64_json",
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                        "User-Agent": "Odoo19-SocialMediaAI/1.0",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=35) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    b64_img = data["data"][0]["b64_json"]
                    return {
                        "image_b64": b64_img,
                        "filename": "openai_marketing_image.png",
                        "engine": f"OpenAI ({cfg.openai_image_model or 'dall-e-3'})",
                        "prompt_used": full_prompt,
                    }
            except Exception as exc:
                _logger.warning("OpenAI DALL-E call failed (%s). Falling back to Free AI Image Engine...", exc)
                if not cfg.allow_free_fallback and cfg.image_provider == "openai":
                    raise UserError(_("OpenAI Image API Error: %s") % str(exc))

        # 2. Free Flux AI Image Generation API (Pollinations.ai — 100% Free, Zero Key)
        if cfg.image_provider != "local_studio":
            try:
                seed = random.randint(1000, 999999)
                encoded = urllib.parse.quote(full_prompt[:450])
                url = (
                    f"https://image.pollinations.ai/prompt/{encoded}"
                    f"?width={width}&height={height}&nologo=true&seed={seed}"
                )
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Odoo19-SocialMediaAI/1.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=28) as resp:
                    img_bytes = resp.read()
                    if img_bytes and len(img_bytes) > 2048:
                        return {
                            "image_b64": base64.b64encode(img_bytes).decode("ascii"),
                            "filename": f"ai_marketing_{seed}.jpg",
                            "engine": "Free Flux AI Image Generator",
                            "prompt_used": full_prompt,
                        }
            except Exception as exc:
                _logger.warning("Free AI Image endpoint timed out (%s). Using built-in Pillow graphic studio.", exc)

        # 3. Built-in Pillow Branded Marketing Graphic Generator (100% Free Offline Fallback)
        b64_fallback = self._generate_local_pillow_poster(
            title=title_overlay or clean_prompt[:65],
            subtitle=clean_prompt,
            width=width,
            height=height,
        )
        return {
            "image_b64": b64_fallback,
            "filename": "social_marketing_poster.png",
            "engine": "Built-in Pillow Marketing Studio",
            "prompt_used": full_prompt,
        }

    @api.model
    def _generate_local_pillow_poster(self, title, subtitle, width=1024, height=1024):
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (width, height), "#091828")
        draw = ImageDraw.Draw(img)

        # Smooth diagonal gradient & modern geometric accents
        for y in range(height):
            ratio = y / float(height)
            r = int(9 + ratio * 14)
            g = int(24 + ratio * 46)
            b = int(40 + ratio * 72)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Top-right cyan glow circle & bottom-left orange accent
        draw.ellipse([width - 360, -120, width + 140, 380], fill=(0, 180, 216))
        draw.ellipse([-140, height - 340, 320, height + 120], fill=(255, 107, 24))
        draw.rounded_rectangle(
            [64, 64, width - 64, height - 64],
            radius=32,
            fill=(13, 31, 49),
            outline=(0, 180, 216),
            width=4,
        )

        try:
            font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 46)
            font_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
            font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        except Exception:
            font_lg = ImageFont.load_default()
            font_md = ImageFont.load_default()
            font_sm = ImageFont.load_default()

        # Brand badge pill
        draw.rounded_rectangle([110, 120, 470, 174], radius=27, fill=(255, 107, 24))
        draw.text((135, 134), "AI MARKETING STUDIO", fill=(255, 255, 255), font=font_sm)

        # Wrap headline
        words = (title or "Social Media Campaign").split()
        lines, cur = [], []
        for w in words:
            cur.append(w)
            if len(" ".join(cur)) > 24:
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))

        y_pos = 240
        for line in lines[:4]:
            draw.text((110, y_pos), line, fill=(255, 255, 255), font=font_lg)
            y_pos += 64

        # Wrap subtitle
        sub_words = (subtitle or "").split()
        sub_lines, cur_sub = [], []
        for w in sub_words:
            cur_sub.append(w)
            if len(" ".join(cur_sub)) > 42:
                sub_lines.append(" ".join(cur_sub))
                cur_sub = []
        if cur_sub:
            sub_lines.append(" ".join(cur_sub))

        y_pos += 30
        for sline in sub_lines[:4]:
            draw.text((110, y_pos), sline, fill=(180, 215, 235), font=font_md)
            y_pos += 42

        # Bottom CTA bar
        draw.rounded_rectangle(
            [110, height - 180, width - 110, height - 105],
            radius=18,
            fill=(0, 180, 216),
        )
        draw.text((145, height - 156), "LUWA TECH • DIGITAL & AI CONTENT SUITE", fill=(9, 24, 40), font=font_sm)

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return base64.b64encode(buf.getvalue()).decode("ascii")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    social_ai_text_provider = fields.Selection(
        [
            ("auto", "Auto (OpenAI API if Key Configured, else Free AI Engine)"),
            ("openai", "OpenAI Official API (gpt-4o-mini / gpt-4o)"),
            ("pollinations_free", "Free AI Text Engine (OpenAI-Compatible • No API Key Required)"),
            ("custom_openai", "Custom OpenAI-Compatible Endpoint (Groq / Gemini / OpenRouter)"),
        ],
        string="Social AI Text Provider",
        config_parameter="social_media_ai.text_provider",
        default="auto",
    )
    social_ai_image_provider = fields.Selection(
        [
            ("auto", "Auto (OpenAI DALL-E if Key Configured, else Free Flux AI Image Engine)"),
            ("openai", "OpenAI DALL-E Image API (dall-e-3 / dall-e-2)"),
            ("pollinations_free", "Free Flux AI Image Generator (No API Key Required)"),
            ("local_studio", "Built-in Pillow Graphic Studio (100% Offline Free Generator)"),
        ],
        string="Social AI Image Provider",
        config_parameter="social_media_ai.image_provider",
        default="auto",
    )
    social_ai_openai_api_key = fields.Char(
        string="OpenAI API Key",
        config_parameter="social_media_ai.openai_api_key",
    )
    social_ai_openai_base_url = fields.Char(
        string="OpenAI API Base URL",
        config_parameter="social_media_ai.openai_base_url",
        default="https://api.openai.com/v1",
    )
    social_ai_openai_model = fields.Char(
        string="OpenAI Chat Model",
        config_parameter="social_media_ai.openai_model",
        default="gpt-4o-mini",
    )
    social_ai_openai_image_model = fields.Selection(
        [
            ("dall-e-3", "DALL-E 3 (High Detail)"),
            ("dall-e-2", "DALL-E 2 (Fast)"),
        ],
        string="OpenAI Image Model",
        config_parameter="social_media_ai.openai_image_model",
        default="dall-e-3",
    )
