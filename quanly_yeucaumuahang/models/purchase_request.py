from odoo import models, fields, api
from odoo.exceptions import UserError


def preview_purchase_request_sequence(env):
    seq = env["ir.sequence"].sudo().search(
        [("code", "=", "purchase.request")],
        limit=1
    )

    if not seq:
        return "New"

    prefix = seq.prefix or ""
    suffix = seq.suffix or ""
    padding = seq.padding or 0
    number = seq.number_next_actual

    return f"{prefix}{str(number).zfill(padding)}{suffix}"


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _description = "Yêu cầu mua hàng"

    name = fields.Char(
        "Mã yêu cầu",
        default=lambda self: preview_purchase_request_sequence(self.env),
        readonly=True,
        required=True,
        copy=False
    )

    department_id = fields.Many2one(
        "hr.department",
        string="Phòng ban"
    )

    request_id = fields.Many2one(
        "res.users",
        string="Người yêu cầu",
        default=lambda self: self.env.user
    )

    approver_id = fields.Many2one(
        "res.users",
        string="Người phê duyệt"
    )

    date = fields.Date(
        "Ngày tạo",
        default=fields.Date.context_today
    )

    date_approve = fields.Date(
        "Ngày phê duyệt",
        readonly=True
    )

    request_line_ids = fields.One2many(
        "purchase.request.line",
        "request_id",
        string="Chi tiết yêu cầu mua hàng"
    )

    description = fields.Text("Mô tả")
    reject_reason = fields.Text(
    "Lý do từ chối",
    readonly=True
)
    state = fields.Selection(
        [
            ("draft", "Dự thảo"),
            ("wait", "Chờ phê duyệt"),
            ("approved", "Đã phê duyệt"),
            ("cancel", "Đã hủy"),
        ],
        string="Trạng thái",
        default="draft"
    )

    total_qty = fields.Float(
        "Tổng số lượng",
        compute="_compute_totals",
        store=True
    )

    total_amount = fields.Float(
        "Tổng tiền",
        compute="_compute_totals",
        store=True
    )

    @api.depends("request_line_ids.qty", "request_line_ids.total")
    def _compute_totals(self):
        for request in self:
            request.total_qty = sum(request.request_line_ids.mapped("qty"))
            request.total_amount = sum(request.request_line_ids.mapped("total"))

    def action_submit(self):
        for request in self:
            if not request.department_id:
                raise UserError("Vui lòng chọn Phòng ban")

            if not request.request_id:
                raise UserError("Vui lòng chọn Người yêu cầu")

            if not request.approver_id:
                raise UserError("Vui lòng chọn Người phê duyệt")

            if not request.request_line_ids:
                raise UserError("Vui lòng thêm ít nhất một sản phẩm yêu cầu mua hàng")

            request.state = "wait"
    def action_back_to_draft(self):
        self.state = "draft"
    def action_approve(self):
        for request in self:
            if request.state != "wait":
                raise UserError("Chỉ được phê duyệt yêu cầu ở trạng thái Chờ phê duyệt")

            if request.approver_id != self.env.user:
                raise UserError("Bạn không phải người phê duyệt của yêu cầu này")

            request.state = "approved"
            request.date_approve = fields.Date.today()

    def action_cancel(self):
        self.ensure_one()

        if self.state != "wait":
            raise UserError("Chỉ được từ chối yêu cầu ở trạng thái Chờ phê duyệt")

        if self.approver_id != self.env.user:
            raise UserError("Bạn không phải người phê duyệt của yêu cầu này")

        return {
            "name": "Lý do từ chối",
            "type": "ir.actions.act_window",
            "res_model": "purchase.request.cancel.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_request_id": self.id,
            },
        }
    def action_export_excel(self):
        self.ensure_one()

        if self.state != "approved":
            raise UserError("Chỉ được xuất Excel khi yêu cầu đã được phê duyệt")

        wizard = self.env["purchase.request.export.wizard"].create({
            "request_id": self.id,
        })

        return {
            "name": "Xuất Excel",
            "type": "ir.actions.act_window",
            "res_model": "purchase.request.export.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["name"] = self.env["ir.sequence"].next_by_code("purchase.request") or "New"
        return super().create(vals_list)

    def unlink(self):
        for request in self:
            if request.state != "draft":
                raise UserError("Bạn không được phép xóa ở trạng thái khác dự thảo")
        return super().unlink()