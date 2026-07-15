from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


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
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        "Mã yêu cầu",
        default=lambda self: preview_purchase_request_sequence(self.env),
        readonly=True,
        required=True,
        copy=False)

    department_id = fields.Many2one(
    "hr.department",
    string="Phòng ban",
    default=lambda self: self._default_department_id(),
    required=True,
    tracking=True
)

    request_id = fields.Many2one(
    "res.users",
    string="Người yêu cầu",
    default=lambda self: self.env.user,
    required=True)

    approver_id = fields.Many2one(
    "res.users",
    string="Người phê duyệt",
    required=True,
    tracking=True
)

    date = fields.Date(
    "Ngày tạo",
    default=fields.Date.context_today,
    required=True)

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
    default="draft",
    tracking=True
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
    @api.constrains("request_id", "approver_id")
    def _check_requester_approver(self):
     for request in self:
        if request.request_id and request.approver_id and request.request_id == request.approver_id:
            raise ValidationError("Người phê duyệt không được trùng với người yêu cầu!")
    def _default_department_id(self):
        employee = self.env.user.employee_id
        if employee and employee.department_id:
            return employee.department_id.id
        return False
    @api.onchange("department_id")
    def _onchange_department_id(self):
        if self.department_id and self.department_id.manager_id:
            manager_user = self.department_id.manager_id.user_id
            if manager_user:
                self.approver_id = manager_user
    @api.onchange("request_id")
    def _onchange_request_id(self):
        if self.request_id and self.request_id.employee_id:
            employee = self.request_id.employee_id
            if employee.department_id:
                self.department_id = employee.department_id            
    @api.depends("request_line_ids.qty", "request_line_ids.total")
    def _compute_totals(self):
        for request in self:
            request.total_qty = sum(request.request_line_ids.mapped("qty"))
            request.total_amount = sum(request.request_line_ids.mapped("total"))

    def action_submit(self):
     for request in self:
        if request.state != "draft":
            raise UserError("Chỉ yêu cầu ở trạng thái Dự thảo mới được gửi phê duyệt")

        if not request.department_id:
            raise UserError("Vui lòng chọn Phòng ban")

        if not request.request_id:
            raise UserError("Vui lòng chọn Người yêu cầu")

        if not request.approver_id:
            raise UserError("Vui lòng chọn Người phê duyệt")

        if request.request_id == request.approver_id:
            raise UserError("Người phê duyệt không được trùng với người yêu cầu")

        if not request.request_line_ids:
            raise UserError("Vui lòng thêm ít nhất một sản phẩm yêu cầu mua hàng")

        for line in request.request_line_ids:
            if line.qty <= 0:
                raise UserError("Số lượng yêu cầu phải lớn hơn 0")

            if line.price_unit < 0:
                raise UserError("Đơn giá không được nhỏ hơn 0")

            if not line.qty_approve:
                line.qty_approve = line.qty

            if line.qty_approve > line.qty:
                raise UserError("Số lượng phê duyệt không được lớn hơn số lượng yêu cầu")

        request.state = "wait"
    def action_back_to_draft(self):
     for request in self:
        if request.state not in ["wait", "cancel"]:
            raise UserError("Chỉ được quay lại dự thảo từ trạng thái Chờ phê duyệt hoặc Đã hủy")

        request.state = "draft"
        request.date_approve = False
        request.reject_reason = False
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

  