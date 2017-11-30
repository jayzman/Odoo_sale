# -*- coding: utf-8 -*-

from odoo import fields, models, api

class StockPicking(models.Model):
    _inherit = 'stock.picking' 
    #champ lié à la au budget expense report 
    bex_id = fields.Many2one('budget.expense.report')