# -*- coding: utf-8 -*-

from odoo import fields, models, api

class ProductFamily(models.Model):
    _name = "product.family"
 
    famille = fields.Char("Famille", size=20, required=True)
    reference_family = fields.Char("Référence", size=50, required=True)
    name = fields.Char("Désignation", size=250)
    
class ProductHeri(models.Model):
    _inherit = "product.product"
    
#     product_family_id = fields.Many2one('product.family', string='Famille')
    family = fields.Char(string='Famille')
    nature_analytique = fields.Char("Nature analytique", size=250)
    stock = fields.Char("Stock HERi")
    security_seuil = fields.Float(string=u'Seuil de securité')
    ref_fournisseur = fields.Char("Référence fournisseur", size=50)
    desc_fournisseur = fields.Char("Description fournisseur", size=100)
    taxe_douane = fields.Float(string=u'Taxe de douane(%)')
    frais_type = fields.Selection([
        ('redevance', 'Redevance fixe pour matériels productifs'),
        ('location', 'Frais de location'),
        ('sans_frais', 'Sans frais')
        ], 'Type de frais',
        default='sans_frais')