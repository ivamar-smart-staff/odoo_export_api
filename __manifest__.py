{
    'name': 'JWT Authentication API',
    'version': '1.0',
    'summary': 'Provides JWT authentication endpoints for Odoo API',
    'description': """
        This module adds JWT authentication capabilities to Odoo
        with a single endpoint to generate tokens.
    """,
    'author': 'Rony Amorim',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/jwt_token_views.xml',
        'data/default_config.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}