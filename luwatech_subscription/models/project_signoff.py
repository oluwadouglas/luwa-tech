# -*- coding: utf-8 -*-
import base64
import logging
import uuid
from collections import OrderedDict
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProjectProjectSignoffExt(models.Model):
    _inherit = "project.project"

    signoff_ids = fields.One2many(
        "luwa.project.signoff",
        "project_id",
        string="Client Sign-Off Dossiers",
    )
    signoff_count = fields.Integer(
        string="Sign-Off Sheets",
        compute="_compute_signoff_count",
    )
    signoff_status_badge = fields.Char(
        string="Sign-Off Status",
        compute="_compute_signoff_count",
    )

    def _compute_signoff_count(self):
        for rec in self:
            rec.signoff_count = len(rec.signoff_ids)
            if not rec.signoff_ids:
                rec.signoff_status_badge = "No Checklist"
            elif any(s.state == "signed_off" for s in rec.signoff_ids):
                rec.signoff_status_badge = "Signed Off"
            elif any(s.state == "partially_signed" for s in rec.signoff_ids):
                rec.signoff_status_badge = "Partially Signed"
            else:
                rec.signoff_status_badge = "In UAT Review"

    def action_view_project_signoffs(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "luwatech_subscription.action_luwa_project_signoffs"
        )
        action["domain"] = [("project_id", "=", self.id)]
        action["context"] = {
            "default_project_id": self.id,
            "default_partner_id": self.partner_id.id if self.partner_id else False,
            "default_name": f"{self.name} - Master Module-by-Module Sign-Off Checklist",
        }
        if len(self.signoff_ids) == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = self.signoff_ids.id
        return action


class LuwaProjectSignoff(models.Model):
    _name = "luwa.project.signoff"
    _description = "Project Module-by-Module Master Sign-Off Checklist"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Sign-Off Dossier Title",
        required=True,
        tracking=True,
        default="Odoo ERP Module-by-Module Master Sign-Off Checklist",
    )
    reference = fields.Char(
        string="Document Ref",
        required=True,
        copy=False,
        default="SIGNOFF/2026/0001",
        tracking=True,
    )
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Client / Organization",
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    erp_version = fields.Char(
        string="Target System / Version",
        default="Odoo 18 Enterprise & Custom Engineering ERP (munigengineering)",
    )
    database_branch = fields.Char(
        string="Database / Instance",
        default="munigengineering (Production)",
    )
    implementation_partner = fields.Char(
        string="Implementation Partner",
        default="Luwa Technologies (U) Limited",
    )
    prepared_by = fields.Char(
        string="Prepared By",
        default="Luwatech System Engineering Team",
    )
    signoff_date = fields.Date(
        string="Checklist Date",
        default=fields.Date.context_today,
        tracking=True,
    )
    warranty_days = fields.Integer(
        string="Hypercare Warranty (Days)",
        default=30,
    )
    warranty_end_date = fields.Date(
        string="Warranty Expiry Date",
    )
    state = fields.Selection(
        [
            ("draft", "Draft / In Preparation"),
            ("shared", "Shared with Client"),
            ("in_review", "In Client UAT Review"),
            ("partially_signed", "Partially Signed Off"),
            ("signed_off", "Fully Signed Off & Accepted"),
        ],
        string="Sign-Off Status",
        default="in_review",
        tracking=True,
    )
    access_token = fields.Char(
        string="Security Token",
        copy=False,
        default=lambda self: uuid.uuid4().hex,
    )
    public_signoff_url = fields.Char(
        string="Client Online Sign-Off Link",
        compute="_compute_public_signoff_url",
    )
    master_pdf_file = fields.Binary(
        string="Signed Master Checklist PDF (Standard Odoo Layout)",
        attachment=True,
    )
    master_pdf_filename = fields.Char(
        string="Master PDF Filename",
        default="Munig_Odoo_Module_By_Module_Master_Checklist.pdf",
    )
    line_ids = fields.One2many(
        "luwa.project.signoff.line",
        "signoff_id",
        string="Module & Submenu Checklist Lines",
        copy=True,
    )

    total_items = fields.Integer(
        string="Total Checklist Items",
        compute="_compute_progress",
        store=True,
    )
    dev_completed_items = fields.Integer(
        string="Dev Completed",
        compute="_compute_progress",
        store=True,
    )
    client_signed_items = fields.Integer(
        string="Client Signed Off Items",
        compute="_compute_progress",
        store=True,
    )
    checked_items = fields.Integer(
        string="Checked Items",
        compute="_compute_progress",
        store=True,
    )
    module_group_count = fields.Integer(
        string="Modules Covered",
        compute="_compute_progress",
        store=True,
    )
    completion_rate = fields.Float(
        string="Client Sign-Off Progress (%)",
        compute="_compute_progress",
        store=True,
    )

    # 5-Pillar Governance Signatories (Including HR & Admin)
    # 1. Luwatech Lead
    luwa_lead_name = fields.Char(
        string="Luwatech Implementation Lead",
        default="Luwatech System Engineering Lead",
        tracking=True,
    )
    luwa_lead_role = fields.Char(
        string="Luwatech Lead Role",
        default="Lead ERP Solutions Architect",
    )
    luwa_lead_signed = fields.Boolean(string="Luwatech Lead Signed", default=True, tracking=True)
    luwa_lead_date = fields.Date(string="Luwatech Sign Date", default=fields.Date.context_today)
    luwa_lead_signed_on = fields.Date(string="Luwatech Signed On", default=fields.Date.context_today)
    luwa_lead_signature = fields.Binary(string="Luwatech Lead Signature", attachment=True)

    # 2. Client Technical & Operations Lead
    client_tech_name = fields.Char(
        string="Munig Technical & Operations Lead",
        tracking=True,
    )
    client_tech_role = fields.Char(
        string="Technical Lead Role",
        default="Technical & Operations Director",
    )
    client_tech_signed = fields.Boolean(string="Technical Lead Signed", default=False, tracking=True)
    client_tech_date = fields.Date(string="Technical Lead Sign Date")
    client_tech_signed_on = fields.Date(string="Technical Lead Signed On")
    client_tech_signature = fields.Binary(string="Technical Lead Signature", attachment=True)

    # 3. Client HR & Administration Lead (NEW)
    client_hr_name = fields.Char(
        string="Munig HR & Administration Lead",
        tracking=True,
    )
    client_hr_role = fields.Char(
        string="HR Lead Role",
        default="Human Resources & Administration Manager",
    )
    client_hr_signed = fields.Boolean(string="HR Lead Signed", default=False, tracking=True)
    client_hr_date = fields.Date(string="HR Lead Sign Date")
    client_hr_signed_on = fields.Date(string="HR Lead Signed On")
    client_hr_signature = fields.Binary(string="HR Lead Signature", attachment=True)

    # 4. Client Finance & Procurement Lead
    client_fin_name = fields.Char(
        string="Munig Finance & Procurement Lead",
        tracking=True,
    )
    client_fin_role = fields.Char(
        string="Finance Lead Role",
        default="Head of Finance & Procurement",
    )
    client_fin_signed = fields.Boolean(string="Finance Lead Signed", default=False, tracking=True)
    client_fin_date = fields.Date(string="Finance Lead Sign Date")
    client_fin_signed_on = fields.Date(string="Finance Lead Signed On")
    client_fin_signature = fields.Binary(string="Finance Lead Signature", attachment=True)

    # 5. Client Managing Director / CEO
    client_ceo_name = fields.Char(
        string="Munig Managing Director / CEO",
        tracking=True,
    )
    client_ceo_role = fields.Char(
        string="CEO Role",
        default="Managing Director / CEO",
    )
    client_ceo_signed = fields.Boolean(string="Managing Director / CEO Signed", default=False, tracking=True)
    client_ceo_date = fields.Date(string="CEO Sign Date")
    client_ceo_signed_on = fields.Date(string="CEO Signed On")
    client_ceo_signature = fields.Binary(string="CEO Signature", attachment=True)

    general_remarks = fields.Text(
        string="Executive UAT Remarks & Handover Notes",
        default=(
            "This Master Checklist covers every active application module, submenu, "
            "and custom workflow installed in the Munig Engineering Solutions Limited "
            "Odoo 18 ERP system (munigengineering). By signing off below, the client "
            "confirms that all checked modules and submenus have been reviewed, tested, "
            "and accepted for production deployment."
        ),
    )

    @api.depends("access_token")
    def _compute_public_signoff_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "https://www.luwatech.it")
        for rec in self:
            if not rec.access_token:
                rec.access_token = uuid.uuid4().hex
            rec.public_signoff_url = f"{base_url}/project/signoff/{rec.id}?token={rec.access_token}"

    @api.depends("line_ids.dev_done", "line_ids.client_signed", "line_ids.client_checked", "line_ids.module_group")
    def _compute_progress(self):
        for rec in self:
            lines = rec.line_ids
            total = len(lines)
            dev_done = len(lines.filtered(lambda l: l.dev_done or l.luwatech_qa == "ready"))
            signed = len(lines.filtered(lambda l: l.client_signed or l.client_checked))
            groups = len(set(lines.mapped("module_group")))
            rec.total_items = total
            rec.dev_completed_items = dev_done
            rec.client_signed_items = signed
            rec.checked_items = signed
            rec.module_group_count = groups
            rec.completion_rate = round((signed / total) * 100.0, 1) if total else 0.0

    def get_grouped_lines(self):
        """Return OrderedDict of {module_group: [line_records]} preserving sequence order."""
        self.ensure_one()
        grouped = OrderedDict()
        for line in self.line_ids.sorted(key=lambda r: (r.sequence, r.id)):
            grp = line.module_group or "General Module"
            if grp not in grouped:
                grouped[grp] = []
            grouped[grp].append(line)
        return grouped

    def action_mark_all_dev_done(self):
        for rec in self:
            rec.line_ids.write({"dev_done": True, "luwatech_qa": "ready"})

    def action_mark_all_client_signed(self):
        for rec in self:
            today = fields.Date.context_today(self)
            rec.line_ids.write({
                "client_signed": True,
                "client_checked": True,
                "signoff_date": today,
                "verified_date": fields.Datetime.now(),
                "signed_by": rec.partner_id.name or "Client Representative",
                "verified_by": rec.partner_id.name or "Client Representative",
            })
            rec.state = "signed_off"
            rec._regenerate_signed_pdf_attachment()

    def action_set_in_review(self):
        self.write({"state": "in_review"})

    def action_set_signed_off(self):
        self.write({"state": "signed_off"})
        for rec in self:
            rec._regenerate_signed_pdf_attachment()

    def action_open_public_signoff(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.public_signoff_url,
            "target": "new",
        }

    def action_print_signoff_pdf(self):
        self.ensure_one()
        return self.env.ref("luwatech_subscription.action_report_project_signoff").report_action(self)

    def _regenerate_signed_pdf_attachment(self):
        """Render the official Odoo Standard-Layout QWeb PDF report and update master_pdf_file."""
        for rec in self:
            try:
                pdf_content, _ = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
                    "luwatech_subscription.action_report_project_signoff",
                    [rec.id],
                )
                if pdf_content:
                    clean_ref = (rec.reference or f"SIGNOFF_{rec.id}").replace("/", "_")
                    rec.sudo().write({
                        "master_pdf_file": base64.b64encode(pdf_content),
                        "master_pdf_filename": f"Munig_Odoo18_Module_SignOff_{clean_ref}.pdf",
                    })
            except Exception as e:
                _logger.warning("Could not auto-regenerate standard Odoo PDF for signoff %s: %s", rec.id, e)


class LuwaProjectSignoffLine(models.Model):
    _name = "luwa.project.signoff.line"
    _description = "Project Sign-Off Module & Submenu Line"
    _order = "sequence asc, id asc"

    signoff_id = fields.Many2one(
        "luwa.project.signoff",
        string="Sign-Off Dossier",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="No.", default=10)
    code = fields.Char(string="Code")
    module_group = fields.Char(
        string="Odoo 18 Application Module",
        required=True,
        help="Root Odoo 18 Application Module (e.g., 01. Requisitions & Approvals)",
    )
    odoo_app = fields.Char(string="App Name")
    technical_module = fields.Char(
        string="Technical Addon / Menu Root",
        help="Technical module or root menu name in Munig Odoo 18",
    )
    submenu_name = fields.Char(
        string="Submenu / Feature Path",
        required=True,
    )
    submenu_feature = fields.Char(string="Submenu / Feature")
    description = fields.Text(
        string="Complete Submenus, Workflows & Acceptance Scope",
        required=True,
    )
    luwatech_qa = fields.Selection(
        [
            ("ready", "Ready / Completed"),
            ("in_progress", "In Progress"),
            ("na", "Not Applicable"),
        ],
        string="Luwatech QA",
        default="ready",
    )
    dev_done = fields.Boolean(
        string="Dev Ready",
        default=True,
    )
    client_signed = fields.Boolean(
        string="Client Sign-Off",
        default=False,
    )
    client_checked = fields.Boolean(
        string="Client Checked",
        default=False,
    )
    signed_by = fields.Char(
        string="Verified By",
    )
    verified_by = fields.Char(
        string="Verified By",
    )
    signoff_date = fields.Date(
        string="Date Signed",
    )
    verified_date = fields.Datetime(
        string="Verified Datetime",
    )
    remarks = fields.Char(
        string="Client Remarks / Observations",
    )
    client_remarks = fields.Text(
        string="Client Remarks",
    )
