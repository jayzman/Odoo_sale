# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import namedtuple
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
from odoo.tools import float_compare, float_round
import re
import time
from docutils.nodes import Invisible
from odoo.api import onchange
from odoo.tools import float_is_zero

class BreqStockHeri(models.Model):
    _inherit = "purchase.order"
    
    @api.model
    def create(self, values):
        order = super(BreqStockHeri,self).create(values)
        if not values['is_breq_id_sale']:
            if not values['order_line']:
                    raise UserError('Veuillez renseigner les lignes de la commande.')
        
                #A executer dans un breq stock uniquement
            if order.is_breq_stock:
                order._create_picking2()
        return order 
    
    breq_id_sale = fields.Many2one("sale.order")
    is_facture_comptabilise = fields.Boolean('Est comptabilise',compute="_compute_all_comptabilise")
    kiosque_id = fields.Many2one('stock.location', string='Kiosque Client') 
    facturation_type = fields.Selection([
            ('facturation_redevance','Redevance mensuelle'),
            ('materiel_loue', 'Materiel Loué'),
            ('facturation_tiers', 'Tiers'),
            ('facturation_entrepreneurs', 'Entrepreneurs'),
            ('facturation_heri_entrepreneurs', 'Entrepreneurs Heri'),
        ], string='Type de Facturation')
    #creation bon de sortie (budget request stock) loué
    @api.multi
    def _create_picking_sale(self):
        StockPickingHeri = self.env['stock.picking']
        for order in self:
            if order.facturation_type == 'materiel_loue' :
                vals = {
    
                        'picking_type_id': order.env.ref('purchase_heri.type_preparation_heri').id,
                        'partner_id': order.partner_id.id,
                        'date': order.date_order,
                        'origin': order.breq_id_sale.name,
                        'location_dest_id': order.kiosque_id.id,
                        'location_id': order.location_id.id,
                        'company_id': order.company_id.id,
                        'move_type': 'direct',
                        'state':'attente_magasinier',
                        'employee_id': order.employee_id.id,
                        'breq_id' : order.id,
                        'section' : order.section,
                        'amount_untaxed' : order.amount_untaxed,
                        'is_bs': True,
                        'mouvement_type' : order.mouvement_type,
                        }
            if order.facturation_type == 'facturation_tiers' :
                vals = {
                        'picking_type_id': order.env.ref('purchase_heri.type_preparation_heri').id,
                        'partner_id': order.partner_id.id,
                        'date': order.date_order,
                        'origin': order.breq_id_sale.name,
                        'location_dest_id': order.env.ref('purchase_heri.stock_location_virtual_heri').id,
                        'location_id': order.location_id.id,
                        'company_id': order.company_id.id,
                        'move_type': 'direct',
                        'state':'attente_magasinier',
                        'employee_id': order.employee_id.id,
                        'breq_id' : order.id,
                        'section' : order.section,
                        'amount_untaxed' : order.amount_untaxed,
                        'is_bs': True,
                        'mouvement_type' : order.mouvement_type,
                        }
            if order.facturation_type == 'facturation_heri_entrepreneurs' or order.facturation_type == 'facturation_entrepreneurs' :
                vals = {
                        'picking_type_id': order.env.ref('purchase_heri.type_preparation_heri').id,
                        'partner_id': order.partner_id.id,
                        'date': order.date_order,
                        'origin': order.breq_id_sale.name,
                        'location_dest_id':  order.kiosque_id.id,
                        'location_id': order.location_id.id,
                        'company_id': order.company_id.id,
                        'move_type': 'direct',
                        'employee_id': order.employee_id.id,
                        'breq_id' : order.id,
                        'section' : order.section,
                        'amount_untaxed' : order.amount_untaxed,
                        'mouvement_type' :'bci',
                        }
            vals1 = {
         
                    'picking_type_id': order.env.ref('purchase_heri.type_preparation_heri').id,
                    'partner_id': order.partner_id.id,
                    'date': order.date_order,
                    'origin': order.breq_id_sale.name,
                    'location_dest_id': order.kiosque_id.id,
                    'location_id': order.location_id.id,
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'state':'attente_magasinier',
                    'employee_id': order.employee_id.id,
                    'breq_id' : order.id,
                    'section' : order.section,
                    'amount_untaxed' : order.amount_untaxed,
                    'is_bs': True,
                    'mouvement_type' : order.mouvement_type,
                    }
            picking_type_id = order.env.ref('purchase_heri.type_preparation_heri').id
            move = StockPickingHeri.create(vals)
            if order.facturation_type == 'facturation_entrepreneurs' :
                move1 = StockPickingHeri.create(vals1)
                move_lines1 = order.order_line._create_stock_moves(move1)
                move_lines1 = move_lines1.filtered(lambda x: x.state not in ('done', 'cancel')).action_confirm()
                move_lines1.action_assign()
                move1.aviser_magasinier_tiers()
            if order.facturation_type == 'facturation_heri_entrepreneurs' or order.facturation_type == 'facturation_entrepreneurs' :
                res = re.findall("\d+", move.name)
                longeur_res = len(res)
                res_final = res[longeur_res-1]
                bci_name = "BCI" + "".join(res_final)
                move.update({'name': bci_name})
            move_lines = order.order_line._create_stock_moves(move)
            move_lines = move_lines.filtered(lambda x: x.state not in ('done', 'cancel')).action_confirm()
            move_lines.action_assign()           
            if order.facturation_type != 'materiel_loue' :
                move.aviser_magasinier_tiers()
                
        picking_type = self.env['stock.picking.type'].search([('id','=',picking_type_id)])
        if  order.facturation_type != 'facturation_tiers' :
            picking_type.default_location_dest_id = self.kiosque_id.id
        return True
    #test
    state = fields.Selection([
        ('nouveau', 'Nouveau'),
        ('confirmation_dg', 'En attente validation DG'),
        ('a_approuver', 'Avis supérieur hiérarchique'),
        ('preparation_materiel', 'préparation des matériels'),
        ('test', 'Test des matériels'),
        ('etab_facture', 'Etablissement Facture'),
        ('comptabilise', 'Comptabilise'),
        ('aviser_finance', 'Etablissement OV'),
        ('ov_to_bank', 'OV envoyé à la banque'),
        ('br_lie', 'Prix de revient'),
        ('calcul_pr', 'Prix de revient calculé'),
        ('non_prevue', 'En vérification compta'),
        ('attente_validation', 'En attente validation DG'),
        ('wait_mode', 'En attente paiement finance'),
        ('purchase', 'BEX'),
        ('refuse', 'Refusé'),
        ('done', 'Terminé'),
        ('bs', 'Bon de sortie'),
        ('bci', 'Bon de cession interne'),
        ('bonci_et_bons', 'Bon de cession interne et bon de sortie'),
        ('cancel', 'Annulé'),
        ], string='Etat BReq', readonly=True, default='nouveau', track_visibility='onchange')
    
    statut_facture = fields.Selection(compute="_get_statut_facture", string='Etat Facture',
                      selection=[
                             ('draft', 'Nouveau'), ('cancel', 'Cancelled'),
                             ('open','Ouvert'),
                             ('paid','Comptabilise'),
                             ])
    @api.one
    def _get_statut_facture(self):  
        facture_lie = self.env['account.invoice'].search([('breq_stock_id','=',self.id)], limit=1)
        if facture_lie:
            self.statut_facture = facture_lie.state     
    
    @api.depends('state')
    def _compute_all_comptabilise(self):
        for order in self:
            current_brq_stock_id = self.env['account.invoice'].search([('breq_stock_id','=',order.id)])
            if current_brq_stock_id and all([x.state == 'paid' for x in current_brq_stock_id]):
                order.is_facture_comptabilise = True
            else :
                order.is_facture_comptabilise = False 

    def envoyer_pour_tester(self):
        self._create_picking_sale()
        self.write({'state':'test'})  
    def generer_bci_et_bs(self):
        self._create_picking_sale()
        self.write({'state':'bonci_et_bons'}) 
    def envoyer_pour_la_preparation(self):
        self.write({'state':'preparation_materiel'}) 
    def annule_test(self):
        self.write({'state':'nouveau'})
    def envoyer_pour_facturation(self):
        self.write({'state':'etab_facture'}) 
        self.action_invoice_create()
    def annule_facturation(self):
        self.write({'state':'nouveau'})  
    def comptabiliser_sale(self):
        if self.facturation_type == 'facturation_heri_entrepreneurs' :
            self.write({'state':'bci'})
        if self.facturation_type == 'facturation_tiers' :
            self.write({'state':'bs'})

    breq_facture_stock_ids = fields.One2many('account.invoice', string="Breq facture ids", compute='_compute_breq_stock_facture_lie')
    breq_facture_stock_count = fields.Integer(compute='_compute_breq_stock_facture_lie') 
    
    #facture lié count 
    @api.multi
    def _compute_breq_stock_facture_lie(self):
        for order in self:
            breq_stock_facture_child= order.env['account.invoice'].search([('breq_stock_id','=',order.id)],limit=1)
            if breq_stock_facture_child:
                order.breq_facture_stock_ids = breq_stock_facture_child
                order.breq_facture_stock_count = len(breq_stock_facture_child)
                
    #facture lié vue
    @api.multi
    def action_breq_stock_lie_facture(self):
        action = self.env.ref('sale_heri.action_budget_request_stock_heri_lie_facture')
        result = action.read()[0]
        return result
    
    #création facture
    @api.multi
    def _create_facture_breq_stock(self):
        for order in self:
            invoice_vals = {
                    'name': order.breq_id_sale.client_order_ref or order.breq_id_sale.name,
                    'origin': order.breq_id_sale.name,
                    'type': 'out_invoice',
                    'TYPE2JOURNAL':'out_invoice',
                    'reference': False,
                    'account_id': order.partner_id.property_account_receivable_id.id,
                    'partner_id': order.breq_id_sale.partner_invoice_id.id,
                    'payment_term_id': order.payment_term_id.id,
                    'fiscal_position_id': order.fiscal_position_id.id or order.partner_id.property_account_position_id.id,
                    'breq_stock_id': order.id, 
                    'breq_id_sale': order.breq_id_sale.id,
                    'parent_id':order.breq_id_sale.id,
                    'user_id': order.breq_id_sale.user_id.id,                 
                    'amount_untaxed': order.amount_untaxed,
                    'amount_tax': order.amount_tax,
                    'amount_total': order.amount_total,
                    'date_invoice':fields.Datetime.now(),
                    'team_id':order.breq_id_sale.team_id.id,
                    'partner_shipping_id': order.breq_id_sale.partner_shipping_id.id,
                    'currency_id': order.breq_id_sale.pricelist_id.currency_id.id,
                    'payment_term_id': order.breq_id_sale.payment_term_id.id,
                    'fiscal_position_id': order.breq_id_sale.fiscal_position_id.id or order.partner_id.property_account_position_id.id,
                    'comment': order.notes,
                    }       
        return invoice_vals
    
    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        inv_obj = self.env['account.invoice']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        invoices = {}
        references = {}
        for order in self:
            group_key = order.breq_id_sale.id if grouped else (order.breq_id_sale.partner_invoice_id.id, order.breq_id_sale.currency_id.id)
            for line in order.breq_id_sale.order_line.sorted(key=lambda l: l.qty_to_invoice < 0):
                if float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    continue
                if group_key not in invoices:
                    inv_data = order._create_facture_breq_stock()
                    invoice = inv_obj.create(inv_data)
                    references[invoice] = order
                    invoices[group_key] = invoice
                elif group_key in invoices:
                    vals = {}
                    if order.breq_id_sale.name not in invoices[group_key].origin.split(', '):
                        vals['origin'] = invoices[group_key].origin + ', ' + order.breq_id_sale.name
                    if order.breq_id_sale.client_order_ref and order.breq_id_sale.client_order_ref not in invoices[group_key].name.split(', '):
                        vals['name'] = invoices[group_key].name + ', ' + order.breq_id_sale.client_order_ref
                    invoices[group_key].write(vals)
                if line.qty_to_invoice > 0:
                    line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)
                elif line.qty_to_invoice < 0 and final:
                    line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)

            if references.get(invoices.get(group_key)):
                if order not in references[invoices[group_key]]:
                    references[invoice] = references[invoice] | order

        if not invoices:
            raise UserError('There is no invoicable line.')

        for invoice in invoices.values():
            if not invoice.invoice_line_ids:
                raise UserError('There is no invoicable line.')
            # If invoice is negative, do a refund invoice instead
            if invoice.amount_untaxed < 0:
                invoice.type = 'out_refund'
                for line in invoice.invoice_line_ids:
                    line.quantity = -line.quantity
            # Use additional field helper function (for account extensions)
            for line in invoice.invoice_line_ids:
                line._set_additional_fields(invoice)
            # Necessary to force computation of taxes. In account_invoice, they are triggered
            # by onchanges, which are not triggered when doing a create.
            invoice.compute_taxes()
            invoice.message_post_with_view('mail.message_origin_link',
                values={'self': invoice, 'origin': references[invoice]},
                subtype_id=self.env.ref('mail.mt_note').id)
        return [inv.id for inv in invoices.values()]
    
    picking_bci_ids = fields.One2many('stock.picking', string="picking_ids", compute='_compute_bci_lie')
    bci_lie_count = fields.Integer(compute='_compute_bci_lie')
    bci_id = fields.Many2one('stock.picking', string="picking_id", compute='_compute_bci_lie')
    @api.multi
    def _compute_bci_lie(self):
        for order in self:
            bci_child_purchase = self.env['stock.picking'].search([('breq_id','=',order.id),('mouvement_type','=','bci')],limit=1)
            if bci_child_purchase:
                order.picking_bci_ids = bci_child_purchase
                order.bci_lie_count = len(bci_child_purchase)
                order.bci_id = bci_child_purchase.id
    
    bci_bs_lie_count = fields.Integer(compute='_compute_bci_bs_lie')
#     bci_bs_id = fields.Many2one('stock.picking', string="picking_id", compute='_compute_bci_bs_lie')
    @api.multi
    def _compute_bci_bs_lie(self):
        for order in self:
            bci_bs_child_purchase = self.env['stock.picking'].search([('breq_id','=',order.id)],limit=2)
            if bci_bs_child_purchase:
#                 order.bci_bs_id = bci_bs_child_purchase
                order.bci_bs_lie_count = len(bci_bs_child_purchase)
    
    #action form bon de sortie facturation aux tiers
    @api.multi
    def action_bs_lie_facturation_tiers(self):
        action = self.env.ref('sale_heri.action_bon_de_sortie_lie_facture_tiers')
        result = action.read()[0]
        return result
    #action form bon de cession interne facturation aux entrepreneurs
    @api.multi
    def action_bci_lie_facturation_entrepreneurs(self):
        action = self.env.ref('sale_heri.action_bon_de_cession_lie_facture_entrepreneurs')
        result = action.read()[0]
        return result   
    #action form bon de cession interne facturation par entrepreneurs
    @api.multi
    def action_bci_et_bs_lie_facturation_entrepreneurs_1(self):
        action = self.env.ref('sale_heri.action_bon_de_cession_lie_facture_entrepreneurs_1')
        result = action.read()[0]
        return result  
