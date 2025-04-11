from odoo import models, fields, api, exceptions
import logging

_logger = logging.getLogger(__name__)


class VisitsModel(models.Model):
    _name = 'visits.model'
    _description = 'Some lead information to the endpont'




    # _logger.info(f"Id_company = {contact_id}, Street = {street or ''}, City = {partner.city or ''}, Zip = {partner.zip or ''}, Country = {partner.country_id.name or ''}")
