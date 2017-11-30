# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import fields, models, api
from collections import namedtuple
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools.translate import _
import re
from odoo.exceptions import UserError
import logging

class StockPicking(models.Model):
    _inherit = 'stock.picking' 
    _order = 'create_date desc'
    
    @api.model
    def create(self, vals):
        context = (self._context or {})
        mouvement_type = context.get('default_mouvement_type', False)
        if mouvement_type and mouvement_type == 'bci':
            vals['name'] = self.env['ir.sequence'].next_by_code('bon.cession.interne')
            if not vals['move_lines']:
                raise UserError('Veuillez insérer les articles à transférer.')
        return super(StockPicking, self).create(vals)
        
            
    breq_id = fields.Many2one('purchase.order')
    section = fields.Char("Section analytique d’imputation")
    amount_untaxed = fields.Float("Total")
    currency_id = fields.Many2one(related='breq_id.currency_id', store=True, string='Currency', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Demandeur', readonly=True)
    is_creator = fields.Boolean(compute="_get_is_creator", string='Est le demandeur')
    is_manager = fields.Boolean(compute="_get_is_manager", string='Est le Superieur')
    is_bs = fields.Boolean('Est un bon de sortie')
    is_duplicata = fields.Boolean('Est un duplicata')
    is_returned = fields.Boolean('dejà retourner')
    bs_id = fields.Many2one('stock.picking', string="Bon de sortie d\'origine")
    magasinier_id = fields.Many2one('hr.employee')
    date_arrivee_reelle = fields.Datetime(string="Date d'arrivée réelle des matériels")  
    
    picking_ids_bret = fields.One2many('stock.picking', string="stock_ids_bret", compute='_compute_bret_lie')
    picking_count_bret = fields.Integer(compute='_compute_bret_lie') 
    
    @api.multi
    def action_bret_lie(self):
        action = self.env.ref('stock_heri.action_bon_de_retour_lie')
        result = action.read()[0]
        return result
    
    @api.multi
    def _compute_bret_lie(self):
        for br in self:
            br_child_stock = self.env['stock.picking'].search(['&', ('breq_id','=',br.origin),('mouvement_type','=','br')])
            if br_child_stock:
                br.picking_ids_bret = br_child_stock
                br.picking_count_bret = len(br_child_stock)
    
    
    mouvement_type = fields.Selection([
        ('bs', 'bon de sortie'),
        ('be', 'bon d entree'),
        ('bci', 'Bon de cession Interne'),
        ('br', 'Bon de Retour'),
        ], string='Type de Mouvement', readonly=True, track_visibility='onchange')
    
    state = fields.Selection([
        ('draft', 'Draft'), ('cancel', 'Cancelled'),
        ('attente_hierarchie','Avis supérieur hierarchique'),
        ('attente_logistique','Avis logistique'),
        ('attente_magasinier','Avis Magasinier'),
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
    def approuver_br(self):
        self.action_assign()
        self.write({'state':'attente_magasinier'})
    
    def action_aviser(self):
        self.action_confirm()
        self.write({'state':'attente_hierarchie'})
        
    def action_aviser_logistique(self):
#         for pick in self:
#             dict = {}
#             product_list = []
#             location_src_id = pick.location_id.id
#             #Verifier la liste de produit dans move_lines si la quantite en stock est insuffisante lors de la demande sauf pour le bon d'entree qui n'a pas besoin de zone d'emplacement source
#             for line in pick.move_lines:
#                 if line.product_id not in product_list:
#                     product_list.append(line.product_id)
#                 if dict.get(line.product_id,False):
#                     dict[line.product_id] += line.product_uom_qty
#                 else: dict[line.product_id] = line.product_uom_qty  
#             product_list_name = []   
#             for product in product_list:
#                 total_qty = 0.0
#                 total_reserved = 0.0
#                 liste_picking_ids = []
#                 bci_ids = self.env['stock.move'].search([('picking_id.mouvement_type','=', 'bci'), \
#                                                                    ('picking_id.state','not in', ('done','cancel')), \
#                                                                    ('product_id','=', product.id)
#                                                                    ])  
#                 line_ids = self.env['purchase.order.line'].search([('order_id.is_breq_stock','=', True), ('order_id.state','!=', 'cancel'), \
#                                                                ('order_id.bs_id.state','not in', ('done','cancel')), \
#                                                                ('product_id','=', product.id), ('location_id','=', location_src_id)
#                                                                ])      
#                 total_bci_reserved = sum(x.product_uom_qty for x in bci_ids)
#                 total_breq_reserved = sum(x.product_qty for x in line_ids)
#                 stock_quant_ids = self.env['stock.quant'].search(['&', ('product_id','=',product.id), ('location_id','=',location_src_id)])
#                 for quant in stock_quant_ids:
#                     total_qty += quant.qty
#                 total_qty = total_qty - total_bci_reserved - total_breq_reserved
#                 #recuperer tous les noms de produits qui sont insuffisants par rapport au quantite en stock disponible
#                 if total_qty < dict[product]:
#                     product_list_name.append(product.name)
#             
#             if product_list_name:
#                 product_name = ''
#                 product_name = "\n".join(product_list_name)
#                 message = "La quantité en stock de l\'emplacement  source est insuffisante pour les articles ci-après: \n"+str(product_name)
#                 raise UserError(message)
#             elif not pick.move_lines:
#                 raise UserError('Veuillez insérer les articles à transférer.')
#             else:
#                 for line in pick.move_lines:
#                     if line.product_uom_qty <= 0.0:
#                         raise UserError('La quantité à transférer ne devrait pas être inférieure ou égale à 0.0.')
#                     else:
#                         self.write({'state':'attente_logistique'})
        
        
        for pick in self:
            if not pick.move_lines:
                raise UserError('Veuillez insérer les articles à transférer.')
            else:
                for line in pick.move_lines:
                    if line.product_uom_qty > line.qte_prevu:
                        raise UserError("La quantité en stock du magasin d\'origine est insuffisante pour l'article "+str(line.product_id.name))
                    if line.product_uom_qty <= 0.0:
                        raise UserError('La quantité à transférer ne devrait pas être inférieure ou égale à 0.0.')
                    
            pick.write({'state':'attente_logistique'})
        
    def action_aviser_magasinier(self):
        self.write({'state':'attente_magasinier'})    
    
    def action_cancel_magasinier(self):
        self.action_confirm()
        self.write({'state':'attente_hierarchie'})
        
    def action_cancel_sup(self):
        self.write({'state':'draft'})
        
    def action_valider_magasinier(self):
        return self.do_new_transfer()
        
    @api.multi
    def do_print_BS(self):
        employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        if employee_id:
            self.magasinier_id = employee_id[0].id
        self.do_new_transfer()
        return self.do_print()   
    
    @api.multi
    def do_print(self):
        return self.env["report"].get_action(self, 'stock_heri.report_bon_de_sortie_template')   
    
    def _prepare_pack_ops(self, quants, forced_qties):
        """ Prepare pack_operations, returns a list of dict to give at create """
        # TDE CLEANME: oh dear ...
        valid_quants = quants.filtered(lambda quant: quant.qty > 0)
        _Mapping = namedtuple('Mapping', ('product', 'package', 'owner', 'location', 'location_dst_id'))

        all_products = valid_quants.mapped('product_id') | self.env['product.product'].browse(p.id for p in forced_qties.keys()) | self.move_lines.mapped('product_id')
        computed_putaway_locations = dict(
            (product, self.location_dest_id.get_putaway_strategy(product) or self.location_dest_id.id) for product in all_products)

        product_to_uom = dict((product.id, product.uom_id) for product in all_products)
        picking_moves = self.move_lines.filtered(lambda move: move.state not in ('done', 'cancel'))
        for move in picking_moves:
            # If we encounter an UoM that is smaller than the default UoM or the one already chosen, use the new one instead.
            if move.product_uom != product_to_uom[move.product_id.id] and move.product_uom.factor > product_to_uom[move.product_id.id].factor:
                product_to_uom[move.product_id.id] = move.product_uom
        if len(picking_moves.mapped('location_id')) > 1:
            raise UserError(_('The source location must be the same for all the moves of the picking.'))
        if len(picking_moves.mapped('location_dest_id')) > 1:
            raise UserError(_('The destination location must be the same for all the moves of the picking.'))

        pack_operation_values = []
        # find the packages we can move as a whole, create pack operations and mark related quants as done
        top_lvl_packages = valid_quants._get_top_level_packages(computed_putaway_locations)
        for pack in top_lvl_packages:
            pack_quants = pack.get_content()
            pack_operation_values.append({
                'picking_id': self.id,
                'package_id': pack.id,
                'product_qty': 1.0,
                'location_id': pack.location_id.id,
                'location_dest_id': computed_putaway_locations[pack_quants[0].product_id],
                'owner_id': pack.owner_id.id,
            })
            valid_quants -= pack_quants

        # Go through all remaining reserved quants and group by product, package, owner, source location and dest location
        # Lots will go into pack operation lot object
        qtys_grouped = {}
        lots_grouped = {}
        for quant in valid_quants:
            key = _Mapping(quant.product_id, quant.package_id, quant.owner_id, quant.location_id, computed_putaway_locations[quant.product_id])
            qtys_grouped.setdefault(key, 0.0)
            qtys_grouped[key] += quant.qty
            if quant.product_id.tracking != 'none' and quant.lot_id:
                lots_grouped.setdefault(key, dict()).setdefault(quant.lot_id.id, 0.0)
                lots_grouped[key][quant.lot_id.id] += quant.qty
        # Do the same for the forced quantities (in cases of force_assign or incomming shipment for example)
        for product, qty in forced_qties.items():
            if qty <= 0.0:
                continue
            key = _Mapping(product, self.env['stock.quant.package'], self.owner_id, self.location_id, computed_putaway_locations[product])
            qtys_grouped.setdefault(key, 0.0)
            qtys_grouped[key] += qty

        # Create the necessary operations for the grouped quants and remaining qtys
        Uom = self.env['product.uom']
        product_id_to_vals = {}  # use it to create operations using the same order as the picking stock moves
        for mapping, qty in qtys_grouped.items():
            uom = product_to_uom[mapping.product.id]
            val_dict = {
                'picking_id': self.id,
                'product_qty': mapping.product.uom_id._compute_quantity(qty, uom),
                'product_id': mapping.product.id,
                'package_id': mapping.package.id,
                'owner_id': mapping.owner.id,
                'location_id': mapping.location.id,
                'location_dest_id': mapping.location_dst_id,
                'product_uom_id': uom.id,
                'pack_lot_ids': [
                    (0, 0, {'lot_id': lot, 'qty': 0.0, 'qty_todo': lots_grouped[mapping][lot]})
                    for lot in lots_grouped.get(mapping, {}).keys()],
            }
            product_id_to_vals.setdefault(mapping.product.id, list()).append(val_dict)

        for move in self.move_lines.filtered(lambda move: move.state not in ('done', 'cancel')):
            values = product_id_to_vals.pop(move.product_id.id, [])
            #insertion de prix unitaire et prix subtotal
            if self.mouvement_type == 'bs':
                for val in values:
                    val.update({
                                'price_unit': move.purchase_line_id.price_unit,
                                'price_subtotal': move.purchase_line_id.price_subtotal,
                                'qty_done': move.purchase_line_id.product_qty,
                               }) 
            elif self.mouvement_type == 'be':
                for val in values:
                    val.update({
                                    'price_unit': move.purchase_line_id.price_unit,
                                    'price_subtotal': move.purchase_line_id.price_subtotal,
                                    'qty_done': move.product_uom_qty,
                                   })
            ################################################
            pack_operation_values += values
        return pack_operation_values
     
    @api.one
    def _get_is_creator(self):
        self.is_creator = False
        current_employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)], limit=1).id
        employee_id = self.employee_id.id
        if current_employee_id == employee_id:
            self.is_creator = True
            
    @api.one
    def _get_is_manager(self):
        self.is_manager = False
        current_employee_id = self.env['hr.employee'].search([('user_id','=',self.env.uid)]).id
        manager_id = self.employee_id.coach_id.id
        if current_employee_id == manager_id:
            self.is_manager = True
    
     
    @api.multi
    def do_new_transfer(self):
        for pick in self:
            pack_operations_delete = self.env['stock.pack.operation']
            if not pick.move_lines and not pick.pack_operation_ids:
                raise UserError('Please create some Initial Demand or Mark as Todo and create some Operations. ')
            # In draft or with no pack operations edited yet, ask if we can just do everything
            if pick.state == 'draft' or all([x.qty_done == 0.0 for x in pick.pack_operation_ids]):
                # If no lots when needed, raise error
                picking_type = pick.picking_type_id
                if (picking_type.use_create_lots or picking_type.use_existing_lots):
                    for pack in pick.pack_operation_ids:
                        if pack.product_id and pack.product_id.tracking != 'none':
                            raise UserError('Some products require lots/serial numbers, so you need to specify those first!')
                view = self.env.ref('stock.view_immediate_transfer')
                wiz = self.env['stock.immediate.transfer'].create({'pick_id': pick.id})
                # TDE FIXME: a return in a loop, what a good idea. Really.
                return {
                    'name': 'Immediate Transfer?',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.immediate.transfer',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'res_id': wiz.id,
                    'context': self.env.context,
                }

            # Check backorder should check for other barcodes
            if pick.check_backorder():
                view = self.env.ref('stock.view_backorder_confirmation')
                wiz = self.env['stock.backorder.confirmation'].create({'pick_id': pick.id})
                # TDE FIXME: same reamrk as above actually
                return {
                    'name': 'Create Backorder?',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.backorder.confirmation',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'res_id': wiz.id,
                    'context': self.env.context,
                }
            for operation in pick.pack_operation_ids:
                if operation.qty_done < 0:
                    raise UserError(_('No negative quantities allowed'))
                if operation.qty_done > 0:
                    operation.write({'product_qty': operation.qty_done})
                else:
                    pack_operations_delete |= operation
            if pack_operations_delete:
                pack_operations_delete.unlink()
        self.do_transfer()
        if self.mouvement_type == 'bs' :
            return  self.env["report"].get_action(self, 'stock_heri.report_bon_de_sortie_template')
        else :
            return
    
    @api.multi
    def do_stock_transfer(self):
        for pick in self:
            dict = {}
            product_list = []
            location_src_id = pick.location_id.id
            #Verifier la liste de produit dans move_lines si la quantite en stock est insuffisante lors de la demande sauf pour le bon d'entree qui n'a pas besoin de zone d'emplacement source
            if self.mouvement_type != 'be':
                for line in pick.move_lines:
                    if line.product_id not in product_list:
                        product_list.append(line.product_id)
                    if dict.get(line.product_id,False):
                        dict[line.product_id] += line.product_uom_qty
                    else: dict[line.product_id] = line.product_uom_qty  
                product_list_name = []   
                for product in product_list:
                    total_qty = 0.0
                    stock_quant_ids = self.env['stock.quant'].search(['&', ('product_id','=',product.id), ('location_id','=',location_src_id)])
                    for quant in stock_quant_ids:
                        total_qty += quant.qty
                    #recuperer tous les noms de produits qui sont insuffisants par rapport au quantite en stock disponible
                    if total_qty < dict[product]:
                        product_list_name.append(product.name)
                
                if product_list_name:
                    product_name = ''
                    product_name = "\n".join(product_list_name)
                    message = "La quantité en stock de l\'emplacement  source est insuffisante pour les articles ci-après: \n"+str(product_name)
                    raise UserError(message)
            
            pack_operations_delete = self.env['stock.pack.operation']
            if not pick.move_lines and not pick.pack_operation_ids:
                raise UserError('Veuillez créer la liste d\'article à transférer. ')
            #In draft or with no pack operations edited yet, ask if we can just do everything
            if pick.state == 'draft' or all([x.qty_done == 0.0 for x in pick.pack_operation_ids]):
                # If no lots when needed, raise error
                picking_type = pick.picking_type_id
                if (picking_type.use_create_lots or picking_type.use_existing_lots):
                    for pack in pick.pack_operation_ids:
                        if pack.product_id and pack.product_id.tracking != 'none':
                            raise UserError('Some products require lots/serial numbers, so you need to specify those first!')
                view = self.env.ref('stock.view_immediate_transfer')
                wiz = self.env['stock.immediate.transfer'].create({'pick_id': pick.id})
                # TDE FIXME: a return in a loop, what a good idea. Really.
                return {
                    'name':'Immediate Transfer?',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.immediate.transfer',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'res_id': wiz.id,
                    'context': self.env.context,
                }
                                    
            # Check backorder should check for other barcodes
            if pick.check_backorder():
                view = self.env.ref('stock.view_backorder_confirmation')
                wiz = self.env['stock.backorder.confirmation'].create({'pick_id': pick.id})
                # TDE FIXME: same reamrk as above actually
                return {
                    'name': 'Create Backorder?',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.backorder.confirmation',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'res_id': wiz.id,
                    'context': self.env.context,
                }
            for operation in pick.pack_operation_ids:
                if operation.qty_done < 0:
                    raise UserError('No negative quantities allowed')
                if operation.qty_done > 0:
                    operation.write({'product_qty': operation.qty_done})
                else:
                    pack_operations_delete |= operation
            if pack_operations_delete:
                pack_operations_delete.unlink()
        self.do_transfer()
        #Calcul PUMP pour le bon d'entree
        if self.mouvement_type == 'be':
            #calculer pump si le type de mouvement est bon d'entree
            for line in self.bex_id.bex_lines:
                qte_recu = line.qty_done
                prix_unit = line.prix_unitaire
                product_id = self.env['product.product'].search([('id','=',line.product_id.id)])
                #Ici la quantite disponible prend en compte la quantite reservee en entree (d'ou on devrait soustraire par la quantite recue)
                qte_total = product_id.qty_available-qte_recu
                ancien_strd_price = product_id.standard_price
                pump = ((qte_recu*prix_unit)+(qte_total*ancien_strd_price))/(qte_recu+qte_total)
                product_id.standard_price = pump
            return
        else:
            return

    def check_backorder(self):
        need_rereserve, all_op_processed = self.picking_recompute_remaining_quantities(done_qtys=True)
        for move in self.move_lines:
            if float_compare(move.remaining_qty, 0, precision_rounding=move.product_id.uom_id.rounding) != 0:
                return True
        return False
    
    @api.onchange('location_dest_id')
    def onchange_location_dest_id(self):
        for pick in self:
            if pick.mouvement_type == 'bs':
                after_vals = {}
                if pick.location_dest_id:
                    after_vals['location_dest_id'] = pick.location_dest_id.id
                if after_vals:
                    pick.pack_operation_product_ids.write(after_vals)
                    
    
class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    @api.model
    def _quant_create_from_move(self, qty, move, lot_id=False, owner_id=False,
                                src_package_id=False, dest_package_id=False,
                                force_location_from=False, force_location_to=False):
        '''Create a quant in the destination location and create a negative
        quant in the source location if it's an internal location. '''
        price_unit = move.get_price_unit()
        location = force_location_to or move.location_dest_id
        rounding = move.product_id.uom_id.rounding
        vals = {
            'product_id': move.product_id.id,
            'location_id': location.id,
            'qty': float_round(qty, precision_rounding=rounding),
            'cost': price_unit,
            'history_ids': [(4, move.id)],
            'in_date': move.date_arrivee_reelle or datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'company_id': move.company_id.id,
            'lot_id': lot_id,
            'owner_id': owner_id,
            'package_id': dest_package_id,
        }
        if move.location_id.usage == 'internal':
            # if we were trying to move something from an internal location and reach here (quant creation),
            # it means that a negative quant has to be created as well.
            negative_vals = vals.copy()
            negative_vals['location_id'] = force_location_from and force_location_from.id or move.location_id.id
            negative_vals['qty'] = float_round(-qty, precision_rounding=rounding)
            negative_vals['cost'] = price_unit
            negative_vals['negative_move_id'] = move.id
            negative_vals['package_id'] = src_package_id
            negative_quant_id = self.sudo().create(negative_vals)
            vals.update({'propagated_from_id': negative_quant_id.id})

        picking_type = move.picking_id and move.picking_id.picking_type_id or False
        if lot_id and move.product_id.tracking == 'serial' and (not picking_type or (picking_type.use_create_lots or picking_type.use_existing_lots)):
            if qty != 1.0:
                raise UserError(_('You should only receive by the piece with the same serial number'))

        # create the quant as superuser, because we want to restrict the creation of quant manually: we should always use this method to create quants
        return self.sudo().create(vals)
    
class StockMove(models.Model):
    _inherit = 'stock.move'
     
    qte_prevu = fields.Float(compute='_compute_qte_prevu', string='Quantité disponible')
    product_uom_qty = fields.Float('Quantity', default=0.0, required=True, states={'done': [('readonly', True)]})
    date_arrivee_reelle = fields.Datetime(string="Date d'arrivée réelle des matériels", related='picking_id.date_arrivee_reelle', store=True) 
       
    @api.depends('product_id')
    def _compute_qte_prevu(self):
        for line in self:
            if line.picking_id.mouvement_type == 'bci':
                if not line.location_id:
                    raise UserError("La zone d'emplacement source ne doit pas être vide")
                
                location_src_id = line.location_id
                total_qty_available = 0.0
                total_reserved = 0.0
                liste_picking_ids = []
                
                stock_quant_ids = line.env['stock.quant'].search(['&', ('product_id','=',line.product_id.id), ('location_id','=', location_src_id.id)])
                line_ids = line.env['purchase.order.line'].search([('order_id.is_breq_stock','=', True), ('order_id.state','!=', 'cancel'), \
                                                                   ('product_id','=', line.product_id.id), ('location_id','=', location_src_id.id), \
                                                                   ])
                #recuperer tous les articles reserves dans bci
                bci_ids = line.env['stock.move'].search([('picking_id.mouvement_type','=', 'bci'), \
                                                                       ('picking_id.state','not in', ('done','cancel')), \
                                                                       ('product_id','=', line.product_id.id)
                                                                       ])  
                total_bci_reserved = sum(x.product_uom_qty for x in bci_ids)                                                
                total_reserved = sum(x.product_qty for x in line_ids if x.order_id.bs_id.state not in ('done','cancel'))
                for quant in stock_quant_ids:
                    total_qty_available += quant.qty
                line.qte_prevu = total_qty_available - total_reserved - total_bci_reserved
        
        return True

    @api.onchange('product_uom_qty')
    def onchange_product_uom_qty(self):
        for line in self:
            if line.picking_id.mouvement_type == 'bci':
                if line.product_uom_qty > 0.0 and line.product_id:  
                    product_seuil_id = self.env['product.product'].search([('id','=',line.product_id.id)])
                    product_seuil = product_seuil_id.security_seuil
                    qte_restant = line.qte_prevu - line.product_uom_qty
                    uom_qty = line.product_uom_qty
                    prevu = line.qte_prevu
                    if line.qte_prevu < line.product_uom_qty:
        #                 self.product_qty = self.qte_prevu
                        return {
                                'warning': {
                                            'title': 'Avertissement!', 'message': 'La quantité demandée réduite au disponible dans le magasin: '+str(self.qte_prevu)
                                        },
                                'value': {
                                        'product_uom_qty': self.qte_prevu,
                                        }
                                }
                    elif line.qte_prevu >= line.product_uom_qty and qte_restant < product_seuil:
                        return {
                                'warning': {
                                            'title': 'Avertissement - Seuil de sécurité!', 'message': 'Le seuil de securité pour cet article est "'+str(product_seuil)+'". Ce seuil est atteint pour cette demande. La quantité restante serait "'+str(qte_restant)+'" qui est en-dessous de seuil de sécurité.'
                                        },
                                'value': {
                                        'product_uom_qty': line.product_uom_qty,
                                        }
                                }
    
class PackOperationLine(models.Model):
    _inherit = 'stock.pack.operation'
    
    price_unit = fields.Float(string='PU')
    price_subtotal = fields.Float(string='PSub')
      
class StockImmediateTransferHeri(models.Model):
    _name = 'stock.immediate.transfer.heri' 
    _inherit = 'stock.immediate.transfer' 
    
    current_product = fields.Text('')
       
class ReturnPickingLineHeri(models.TransientModel):
    _inherit= "stock.return.picking.line"
    _rec_name = 'product_id'

    quantity = fields.Float("Quantité",required=True, readonly=False)
    
class ReturnPickingHeri(models.TransientModel):
    _inherit = 'stock.return.picking'
    _description = 'Return Picking Heri'

    location_id = fields.Many2one(
        'stock.location', 'Return Location',
        domain="['|', ('id', '=', original_location_id), '&', ('return_location', '=', True), ('id', 'child_of', parent_location_id)]",readonly=True)
    
    @api.multi
    def _create_returns(self):
        # TDE FIXME: store it in the wizard, stupid
        picking = self.env['stock.picking'].browse(self.env.context['active_id'])
        picking.is_returned = True
        return_moves = self.product_return_moves.mapped('move_id')
        unreserve_moves = self.env['stock.move']
        for move in return_moves:
            to_check_moves = self.env['stock.move'] | move.move_dest_id
            while to_check_moves:
                current_move = to_check_moves[-1]
                to_check_moves = to_check_moves[:-1]
                if current_move.state not in ('done', 'cancel') and current_move.reserved_quant_ids:
                    unreserve_moves |= current_move
                split_move_ids = self.env['stock.move'].search([('split_from', '=', current_move.id)])
                to_check_moves |= split_move_ids

        if unreserve_moves:
            unreserve_moves.do_unreserve()
            # break the link between moves in order to be able to fix them later if needed
            unreserve_moves.write({'move_orig_ids': False})

        # create new picking for returned products
        
        picking_type_id = picking.picking_type_id.return_picking_type_id.id or picking.picking_type_id.id
        res = re.findall("\d+", picking.name)
        longeur_res = len(res)
        res_final = res[longeur_res-1]
        br_name = "BR" + "".join(res_final)
        new_picking = picking.copy({
            'move_lines': [],
            'picking_type_id': picking_type_id,
            'name' : br_name,
            'state': 'draft',
            'mouvement_type': 'br',
            'bs_id' : picking.id,
            'origin': picking.name,
            'location_id': picking.location_dest_id.id,
            'location_dest_id': self.location_id.id})
        new_picking.message_post_with_view('mail.message_origin_link',
            values={'self': new_picking, 'origin': picking},
            subtype_id=self.env.ref('mail.mt_note').id)

        returned_lines = 0
        for return_line in self.product_return_moves:
            if not return_line.move_id:
                raise UserError("You have manually created product lines, please delete them to proceed")
            new_qty = return_line.quantity
            if new_qty:
                # The return of a return should be linked with the original's destination move if it was not cancelled
                if return_line.move_id.origin_returned_move_id.move_dest_id.id and return_line.move_id.origin_returned_move_id.move_dest_id.state != 'cancel':
                    move_dest_id = return_line.move_id.origin_returned_move_id.move_dest_id.id
                else:
                    move_dest_id = False

                returned_lines += 1
                return_line.move_id.copy({
                    'product_id': return_line.product_id.id,
                    'product_uom_qty': new_qty,
                    'qty_done': new_qty,
                    'picking_id': new_picking.id,
                    'state': 'draft',
                    'location_id': return_line.move_id.location_dest_id.id,
                    'location_dest_id': self.location_id.id or return_line.move_id.location_id.id,
                    'picking_type_id': picking_type_id,
                    'warehouse_id': picking.picking_type_id.warehouse_id.id,
                    'origin_returned_move_id': return_line.move_id.id,
                    'procure_method': 'make_to_stock',
                    'move_dest_id': move_dest_id,
                })
            if  return_line.move_id.product_uom_qty < new_qty:
                raise UserError(u'La quantité à retourner ne doit pas être au dessus de la quantité de l\' article dans le bon de sortie')
        if not returned_lines:
            raise UserError("Please specify at least one non-zero quantity.")           
        
        new_picking.action_aviser()
        return new_picking.id, picking_type_id
    
    @api.multi
    def create_returns(self):
        for wizard in self:
            new_picking_id, pick_type_id = wizard._create_returns()
        # Override the context to disable all the potential filters that could have been set previously
        ctx = dict(self.env.context)
        ctx.update({
            'search_default_picking_type_id': pick_type_id,
            'search_default_draft': False,
            'search_default_assigned': False,
            'search_default_confirmed': False,
            'search_default_ready': False,
            'search_default_late': False,
            'search_default_available': False,
        })
        res = self.env.ref('stock_heri.view_picking_form_advanced2', False)
        return {
            'name': 'Returned Picking',
            'view_type': 'form',
            'view_mode': 'form,tree,calendar',
            'res_model': 'stock.picking',
            'res_id': new_picking_id,
            'type': 'ir.actions.act_window',
            'context': ctx,
            'views' : [(res and res.id or False, 'form')]
        }