# -*- coding: utf-8 -*-

from odoo import fields, models, api

class StockPickingHeri(models.Model):
    _inherit = 'stock.picking'   

    date_arrivee_reelle = fields.Datetime(string="Date d'arrivée réelle des matériels")  
    location_id = fields.Many2one(
        'stock.location', "Source Location Zone",
        default=lambda self: self.env['stock.picking.type'].browse(self._context.get('default_picking_type_id')).default_location_src_id,
        readonly=True, required=True,
        states={'draft': [('readonly', False)]})
    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location Zone",
        default=lambda self: self.env['stock.picking.type'].browse(self._context.get('default_picking_type_id')).default_location_dest_id,
        readonly=True, required=True,
        states={'draft': [('readonly', False)],'attente_logistique': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'), ('cancel', 'Cancelled'),
        ('attente_hierarchie','Avis supérieur hierarchique'),
        ('attente_logistique','Avis logistique'),
        ('attente_magasinier','Avis Magasinier'),
        ('attente_call_center','Avis call center'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'),
        ('assigned', 'Available'), ('done', 'Done')], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, track_visibility='onchange',
        help=" * Draft: not confirmed yet and will not be scheduled until confirmed\n"
             " * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n"
             " * Waiting Availability: still waiting for the availability of products\n"
             " * Partially Available: some products are available and reserved\n"
             " * Ready to Transfer: products reserved, simply waiting for confirmation.\n"
             " * Transferred: has been processed, can't be modified or cancelled anymore\n"
             " * Cancelled: has been cancelled, can't be confirmed anymore")

    def aviser_magasinier_tiers(self):
        self.action_confirm()
        self.write({'state':'attente_magasinier'})    
    def aviser_logistique(self):
        self.write({'state':'attente_logistique'})  
    def action_aviser_magasinier_bs(self):
        self.action_assign()
        self.write({'state':'assigned'})
    def action_aviser_call_center_bs(self):
        self.write({'state':'attente_call_center'})
    def action_validation_call_center_bs(self):
        self.write({'state':'assigned'})