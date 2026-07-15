from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import io


class PurchaseRequestExportWizard(models.TransientModel):
    _name = "purchase.request.export.wizard"
    _description = "Wizard xuất Excel yêu cầu mua hàng"

    request_id = fields.Many2one(
        "purchase.request",
        string="Yêu cầu mua hàng",
        required=True
    )

    file_data = fields.Binary(
        "File Excel",
        readonly=True
    )

    file_name = fields.Char(
        "Tên file",
        readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            request_id = vals.get("request_id")
            if request_id:
                request = self.env["purchase.request"].browse(request_id)
                file_data, file_name = self._create_excel_file(request)

                vals["file_data"] = file_data
                vals["file_name"] = file_name

        return super().create(vals_list)

    def _create_excel_file(self, request):
        if request.state != "approved":
            raise UserError("Chỉ được xuất Excel khi yêu cầu đã được phê duyệt")

        try:
            import xlsxwriter
        except ImportError:
            raise UserError("Chưa có thư viện xlsxwriter. Hãy cài bằng lệnh: pip install XlsxWriter")

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Chi tiết yêu cầu")

        title_format = workbook.add_format({
            "bold": True,
            "font_size": 14,
        })

        header_format = workbook.add_format({
            "bold": True,
            "border": 1,
        })

        cell_format = workbook.add_format({
            "border": 1,
        })

        number_format = workbook.add_format({
            "border": 1,
            "num_format": "#,##0.00",
        })

        sheet.write(0, 0, "CHI TIẾT YÊU CẦU MUA HÀNG", title_format)

        sheet.write(2, 0, "Mã yêu cầu")
        sheet.write(2, 1, request.name or "")

        sheet.write(3, 0, "Phòng ban")
        sheet.write(3, 1, request.department_id.display_name or "")

        sheet.write(4, 0, "Người yêu cầu")
        sheet.write(4, 1, request.request_id.display_name or "")

        sheet.write(5, 0, "Người phê duyệt")
        sheet.write(5, 1, request.approver_id.display_name or "")

        sheet.write(6, 0, "Ngày tạo")
        sheet.write(6, 1, str(request.date or ""))

        sheet.write(7, 0, "Ngày phê duyệt")
        sheet.write(7, 1, str(request.date_approve or ""))

        row = 9

        headers = [
            "STT",
            "Sản phẩm",
            "Đơn vị tính",
            "Số lượng",
            "Số lượng phê duyệt",
            "Đơn giá",
            "Thành tiền",
        ]

        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)

        row += 1

        stt = 1
        for line in request.request_line_ids:
            sheet.write(row, 0, stt, cell_format)
            sheet.write(row, 1, line.product_id.display_name or "", cell_format)
            sheet.write(row, 2, line.uom_id.display_name or "", cell_format)
            sheet.write(row, 3, line.qty, number_format)
            sheet.write(row, 4, line.qty_approve, number_format)
            sheet.write(row, 5, line.price_unit, number_format)
            sheet.write(row, 6, line.total, number_format)

            row += 1
            stt += 1

        sheet.write(row + 1, 5, "Tổng tiền", header_format)
        sheet.write(row + 1, 6, request.total_amount, number_format)

        sheet.set_column(0, 0, 8)
        sheet.set_column(1, 1, 35)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 6, 18)

        workbook.close()
        output.seek(0)

        file_data = base64.b64encode(output.read())
        file_name = f"{request.name}_chi_tiet_yeu_cau_mua_hang.xlsx"

        return file_data, file_name