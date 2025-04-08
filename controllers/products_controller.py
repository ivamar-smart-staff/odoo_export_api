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
            latlong = {product.partner_id.partner_latitude, product.partner_id.partner_longitude} if product.partner_id.partner_latitude != 0 and product.partner_id.partner_longitude != 0 else get_product_latlong()
            object = {
                "id": product.id,
                "cnpj": None,
                "address": f"{product.street} - {product.street2} - {product.city}/{product.state_id}" or None,
                "billing_address": None,
                "name": product.name,
                "phone": None,
                "lat": product.partner.id

            }
            json_return.append(object)

        return request.make_response(
            json.dumps(json_return),
            headers=[('Content-Type', 'application/json')]
        )