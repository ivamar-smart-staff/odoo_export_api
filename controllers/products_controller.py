from odoo import http
from odoo.http import request, Response, Controller
import json
import logging

_logger = logging.getLogger(__name__)

class ProductsController(Controller):
    @http.route('/api/products/', type='http', auth='none', methods=['GET'], csrf=False)
    def get_products(self):
        products = request.env['res.company'].sudo().search([])
        json_return = []
        for product in products:
            if product.partner_id.partner_latitude == 0 and product.partner_id.partner_longitude == 0:
                request.env['products.model'].calculate_coordinates(product.partner_id.id)

            data = {
                "id": product.id,
                "cnpj": None,
                "address": " - ".join(filter(None, [product.street, product.street2])) + f" - {product.city}/{product.state_id.name or ''}",
                "billing_address": None,
                "name": product.name,
                "phone": None,
                "lat": product.partner_id.partner_latitude or None,
                "long": product.partner_id.partner_longitude or None,
                "sap": None,
                "started_when": None,


            }
            json_return.append(data)

        return request.make_response(
            json.dumps(json_return),
            headers=[('Content-Type', 'application/json')]
        )