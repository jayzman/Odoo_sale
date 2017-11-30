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
from pychart.arrow import default

class ResCalendar(models.Model):
    _name = "res.calendar"
    
    name = fields.Char(u'Entre deux dates')
    last_month = fields.Datetime(string="Date du mois précedent") 
    current_month = fields.Datetime(string="Date du mois en cours") 
    is_initialize = fields.Boolean(string='Est initialisé')
    
    def _compute_date_faturation_redevance(self):
        calendar = self.env.ref('sale_heri.calendrier_facturation_redevance')
        if not calendar.is_initialize:
            calendar.last_month = fields.Datetime.now()
            calendar.current_month = fields.Datetime.now()
            calendar.is_initialize = True
            print 'INITIALISATION'
        else:
            calendar.last_month = calendar.current_month
            calendar.current_month = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            print 'NON NON NON NON NON NON NON NON NON NON'