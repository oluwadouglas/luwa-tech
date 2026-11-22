/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class SocialMediaAiDashboard extends Component {
    static template = "social_media_ai.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            isLoading: true,
            data: {
                kpis: {
                    total: 0,
                    draft: 0,
                    pending_approval: 0,
                    approved: 0,
                    scheduled: 0,
                    published: 0,
                    ai_images: 0,
                },
                platforms: {
                    facebook: 0,
                    instagram: 0,
                    linkedin: 0,
                    x: 0,
                },
                recent_posts: [],
                upcoming_posts: [],
                ai_status: {
                    text_engine: "Free OpenAI-Compatible AI (Ready)",
                    image_engine: "Free Flux AI Image Studio (Ready)",
                },
            },
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.isLoading = true;
        try {
            const res = await this.orm.call(
                "social.media.post",
                "get_dashboard_data",
                []
            );
            if (res) {
                this.state.data = res;
            }
        } catch (err) {
            console.error("Failed to load Social Media AI dashboard data:", err);
        } finally {
            this.state.isLoading = false;
        }
    }

    openPostsByDomain(title, domain = []) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: title,
            res_model: "social.media.post",
            views: [
                [false, "kanban"],
                [false, "list"],
                [false, "calendar"],
                [false, "form"],
            ],
            domain: domain,
            target: "current",
        });
    }

    openPostRecord(postId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Social Media Post",
            res_model: "social.media.post",
            res_id: postId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    createNewPost() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "New AI Social Media Post",
            res_model: "social.media.post",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAiContentStudio() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "AI Content Studio",
            res_model: "social.media.ai.generator",
            views: [
                [false, "form"],
                [false, "list"],
            ],
            target: "current",
        });
    }

    openAiImageStudio() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "AI Image Studio",
            res_model: "social.media.ai.image",
            views: [
                [false, "form"],
                [false, "kanban"],
                [false, "list"],
            ],
            target: "current",
        });
    }

    openContentCalendar() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Social Media Content Calendar",
            res_model: "social.media.post",
            views: [
                [false, "calendar"],
                [false, "kanban"],
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    openAiConfig() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "AI Providers & API Credentials",
            res_model: "social.media.ai.config",
            res_id: 1,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openSocialAccounts() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Connected Social Media Accounts",
            res_model: "social.media.account",
            views: [
                [false, "kanban"],
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }
}

registry.category("actions").add("social_media_ai.dashboard", SocialMediaAiDashboard);
