# -*- coding: utf-8 -*-

from odoo import fields, models, api


class PurchaseConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'
    
    @api.model
    def _default_seuil_nbr_jour_non_prevu(self):
        waiting_mode = self.env.ref('sale_heri.act_correction_motif_finance_to_observation_dg')
        seuil_non_prevu = float(waiting_mode.condition.split('>')[1])
        return seuil_non_prevu
    
    seuil_nbr_jour = fields.Float("Seuil du montant total de la facturation redevance mensuelle", default=lambda self: self._default_seuil_nbr_jour_non_prevu())
    jour_etab_facture_redevance = fields.Float("Jour du mois pour l'etablissement de la facture redevance", default=25)
    
    def set_seuil_prevu(self):
        waiting_mode = self.env.ref('sale_heri.act_correction_motif_finance_to_observation_dg')
        waiting_mode.write({'condition': 'nbre_jour_detention > %s' % self.seuil_nbr_jour})
        sms_invoice = self.env.ref('sale_heri.act_correction_motif_finance_to_generation_facture_sms')
        sms_invoice.write({'condition': 'nbre_jour_detention <= %s' % self.seuil_nbr_jour})
        
    