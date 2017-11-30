# -*- coding: utf-8 -*-
{
    'name': 'Product module for HERi',
    'version': '1.0',
    'category': 'Product',
    'sequence': 0,
    'description': """Module de references articles pour Heri""",
    'website': 'https://www.ingenosya.mg',
    'depends': ['purchase','stock', 'hr'],
    'data': [
                'views/product_view.xml',
                'views/res_partner_view.xml',
             ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}