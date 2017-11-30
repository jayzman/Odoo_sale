# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
import re

class ModePaiement(models.Model):
    _name = "mode.paiement"
    
    mode_paiement = fields.Many2one('account.journal', string="Mode de paiement", domain=[('type','in',('cash','bank'))])
    breq_id = fields.Many2one('purchase.order')
    #mode de paiement
    def valider_mode_paiement(self):
        #self._compute_pump()
        if not self.mode_paiement:
            raise UserError(u'Le mode de paiement ne doit pas être vide.')
        mode_paiement = self.mode_paiement.id
        breq = self.env['purchase.order'].browse(self.breq_id.id)
        breq.write({'journal_id': mode_paiement})
        if self.breq_id.purchase_type != "purchase_import":
            breq.signal_workflow('valider_mode')