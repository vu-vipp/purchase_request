{
    'name': 'Quản lý yêu cầu mua hàng',
    'version': '16.0.1.0.0',
    'depends': ['base', 'purchase', 'hr', 'product', 'mail'],
    'data': [
    'security/security.xml',
    'security/ir.model.access.csv',
    'data/purchase_request_sequence.xml',
    'views/purchase_request_views.xml',
    'views/purchase_request_line_views.xml',
    'views/purchase_request_cancel_wizard_views.xml',
    'views/purchase_request_export_wizard_views.xml',
    'views/menu_views.xml',
],

    'installable': True,
    'application': True,
}