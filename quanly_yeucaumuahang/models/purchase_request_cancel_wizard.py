from odoo import models, fields
from odoo.exceptions import UserError


class PurchaseRequestCancelWizard(models.TransientModel):
    _name = "purchase.request.cancel.wizard"
    _description = "Wizard từ chối yêu cầu mua hàng"

    request_id = fields.Many2one(
        "purchase.request",
        string="Yêu cầu mua hàng",
        required=True
    )

    reason = fields.Text(
        "Lý do từ chối",
        required=True
    )

    def action_confirm_cancel(self):
        self.ensure_one()

        request = self.request_id

        if request.state != "wait":
            raise UserError("Chỉ được từ chối yêu cầu ở trạng thái Chờ phê duyệt")

        if request.approver_id != self.env.user:
            raise UserError("Bạn không phải người phê duyệt của yêu cầu này")

        request.write({
            "state": "cancel",
            "reject_reason": self.reason,
        })

        return {
            "type": "ir.actions.act_window_close"
        }