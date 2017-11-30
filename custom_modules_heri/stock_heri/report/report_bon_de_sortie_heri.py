# -*- coding: utf-8 -*-

from odoo import api, models

class report_bon_de_sortie_template(models.AbstractModel):
    _name = 'report.stock_heri.report_bon_de_sortie_template'
   
    def _set_duplicata(self, obj):
        obj.is_duplicata = True
        return
    
    @api.multi
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'stock.picking',
            'docs': self.env['stock.picking'].browse(docids),
            'set_duplicata': self._set_duplicata,
            'data': data,
        }
        return self.env['report'].render('stock_heri.report_bon_de_sortie_template', docargs)

     

    
    

