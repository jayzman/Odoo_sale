# -*- coding: utf-8 -*-
{
    'name': 'Purchase module for HERi',
    'version': '1.0',
    'category': 'Purchase Management',
    'sequence': 0,
    'description': """Module de gestion des achats pour Heri""",
    'website': 'https://www.ingenosya.mg',
    'depends': ['base','purchase','stock', 'hr'],
    'data': [
                #views
                'views/bex_view.xml',
                'views/purchase_view.xml',
                'views/purchase_wkf.xml',
                'views/paiement.xml',
                'views/res_config_views.xml',
                #data
                'data/stock_warehouse_data.xml',
                #security
                'security/security.xml',
                'security/ir.model.access.csv',
             ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}