# -*- coding: utf-8 -*-
{
    'name': 'Stock module for HERi',
    'version': '1.0',
    'category': 'Stock Management',
    'sequence': 0,
    'description': """Module de gestion des stocks pour Heri""",
    'website': 'https://www.ingenosya.mg',
    'depends': ['purchase_heri'],
    'data': [
            'views/budget_request_stock_view.xml',
            'views/stock_view.xml',
            'report/report_bon_de_sortie_template.xml',
            'report/report_bon_de_sortie.xml',
              ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}