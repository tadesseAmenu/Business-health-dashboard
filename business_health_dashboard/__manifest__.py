{
    'name': 'Business Health Dashboard',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Track expenses and revenue, view business health KPIs and alerts',
    'author': 'Your Name',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/business_health_security.xml',
        'security/ir.model.access.csv',
        'data/dashboard_config.xml',
        'views/expense_entry_views.xml',
        'views/revenue_views.xml',
        'views/business_dashboard_views.xml',
        'report/dashboard_report.xml',
        'report/expense_entry_report.xml',
        'report/revenue_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'business_health_dashboard/static/src/scss/business_dashboard.scss',
        ],
    },
    'application': True,
    'installable': True,
}