from odoo import models, fields, api, exceptions
import logging

_logger = logging.getLogger(__name__)


class ProductsModel(models.Model):
    _name = 'products.model'
    _description = 'Product lat and long calculation'

    def calculate_coordinates(self, contact_id):
        partners = self.env['res.partner'].sudo().search([('id', '=', contact_id)], limit=1)
        for partner in partners:
            street = (partner.street or '') + ' ' + (partner.street2 or '')
            result = partner._geo_localize(
                street,
                partner.zip,
                partner.city,
                partner.state_id.name,
                partner.country_id.name
            )

            if result:
                partner.write({
                    'partner_latitude': result[0],
                    'partner_longitude': result[1],
                    'date_localization': fields.Date.context_today(partner)
                })
            # else:
            #     partners_not_geo_localized |= partner

            # _logger.info(f"Id_company = {contact_id}, Street = {street or ''}, City = {partner.city or ''}, Zip = {partner.zip or ''}, Country = {partner.country_id.name or ''}")
