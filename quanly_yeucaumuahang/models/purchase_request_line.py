from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class PurchaseRequestLine(models.Model):
    _name = "purchase.request.line"
    _description = "Chi tiết yêu cầu mua hàng"

    request_id = fields.Many2one(
        "purchase.request",
        string="Yêu cầu mua hàng",
        ondelete="cascade"
    )

    state = fields.Selection(
        related="request_id.state",
        string="Trạng thái"
    )

    product_id = fields.Many2one(
        "product.template",
        string="Sản phẩm",
        required=True
    )

    uom_id = fields.Many2one(
        "uom.uom",
        string="Đơn vị tính",
        required=True
    )

    qty = fields.Float(
        "Số lượng",
        default=1
    )

    qty_approve = fields.Float(
        "Số lượng phê duyệt"
    )

    price_unit = fields.Float(
        "Đơn giá"
    )

    total = fields.Float(
        "Thành tiền",
        compute="_compute_total",
        store=True
    )

    @api.depends("qty", "price_unit")
    def _compute_total(self):
        for line in self:
            line.total = line.qty * line.price_unit

    @api.onchange("product_id")
    def _onchange_product_id(self):
     if self.product_id:
        self.uom_id = self.product_id.uom_id

        seller = self.product_id.seller_ids.sorted(
            key=lambda s: s.id,
            reverse=True
        )[:1]

        if seller:
            self.price_unit = seller.price
        else:
            self.price_unit = self.product_id.list_price

        if not self.qty_approve:
            self.qty_approve = self.qty
    @api.constrains("qty", "qty_approve", "price_unit")
    def _check_qty_price(self):
       for line in self:
        if line.qty <= 0:
            raise ValidationError("Số lượng yêu cầu phải lớn hơn 0!")

        if line.qty_approve < 0:
            raise ValidationError("Số lượng phê duyệt không được nhỏ hơn 0!")

        if line.qty_approve and line.qty_approve > line.qty:
            raise ValidationError("Số lượng phê duyệt không được lớn hơn số lượng yêu cầu!")

        if line.price_unit < 0:
            raise ValidationError("Đơn giá không được nhỏ hơn 0!")
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            request_id = vals.get("request_id")
            if request_id:
                request = self.env["purchase.request"].browse(request_id)
                if request.state != "draft":
                    raise UserError("Chỉ được thêm chi tiết yêu cầu mua hàng ở trạng thái Dự thảo")

        return super().create(vals_list)

    def write(self, vals):
        allowed_fields_wait = {"qty_approve"}

        for line in self:
            if line.request_id.state == "wait":
                wrong_fields = set(vals.keys()) - allowed_fields_wait
                if wrong_fields:
                    raise UserError("Ở trạng thái Chờ phê duyệt, chỉ được sửa Số lượng phê duyệt")

            elif line.request_id.state not in ["draft"]:
                raise UserError("Không được sửa chi tiết yêu cầu mua hàng ở trạng thái này")

        return super().write(vals)

    def unlink(self):
        for line in self:
            if line.request_id.state != "draft":
                raise UserError("Chỉ được xóa chi tiết yêu cầu mua hàng ở trạng thái Dự thảo")

        return super().unlink()