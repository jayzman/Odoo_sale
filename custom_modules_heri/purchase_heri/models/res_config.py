# -*- coding: utf-8 -*-

from odoo import fields, models, api


class PurchaseConfigSettings(models.TransientModel):
    _inherit = 'purchase.config.settings'
    
    @api.model
    def _default_seuil_prevu(self):
        waiting = self.env.ref('purchase_heri.act_prevu_to_act_attente_validation')
        seuil_prevu = float(waiting.condition.split('>')[1])
        return seuil_prevu
    
    @api.model
    def _default_seuil_non_prevu(self):
        waiting_mode = self.env.ref('purchase_heri.act_attente_validation_to_act_wait_mode2')
        seuil_non_prevu = float(waiting_mode.condition.split('<=')[1])
        return seuil_non_prevu
    
    seuil_prevu = fields.Float("Seuil d'un budget request achat prévu", default=lambda self: self._default_seuil_prevu())
    seuil_non_prevu = fields.Float("Seuil d'un budget request achat non prévu", default=lambda self: self._default_seuil_non_prevu())
    
    def set_seuil_prevu(self):
        waiting = self.env.ref('purchase_heri.act_prevu_to_act_attente_validation')
        waiting.write({'condition': 'amount_untaxed > %s' % self.seuil_prevu})
        waiting_mode = self.env.ref('purchase_heri.act_prevu_to_act_wait_mode')
        waiting_mode.write({'condition': 'amount_untaxed <= %s' % self.seuil_prevu})
    
    def set_seuil_non_prevu(self):
        waiting_mode = self.env.ref('purchase_heri.act_attente_validation_to_act_wait_mode2')
        waiting_mode.write({'condition': 'amount_untaxed <= %s' % self.seuil_non_prevu})