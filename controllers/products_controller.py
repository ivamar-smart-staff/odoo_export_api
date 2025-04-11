from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class ProductsController(http.Controller):
    @http.route('/api/products/', type='http', auth='none', methods=['GET'], csrf=False)
    @auto_authenticate
    def get_products(self):
        # Validação do token via header "Authorization"
        auth_header = request.httprequest.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return request.make_response(
                json.dumps({"error": "Token não fornecido no header de autorização"}),
                status=401,
                headers=[('Content-Type', 'application/json')]
            )
        token = auth_header.split(' ')[1].strip()
        try:
            # Verifica o token utilizando o modelo de autenticação
            request.env['auth.model'].sudo().verify_token(token)
        except Exception as e:
            _logger.exception("Token inválido: %s", e)
            return request.make_response(
                json.dumps({"error": "Token inválido"}),
                status=401,
                headers=[('Content-Type', 'application/json')]
            )

        # Parâmetros de paginação (opcional)
        page = int(request.params.get('page', 1))
        limit = int(request.params.get('limit', 100))
        offset = (page - 1) * limit

        # Busca apenas os campos necessários do modelo res.company
        companies = request.env['res.company'].sudo().search_read(
            [],
            ['id', 'name', 'street', 'street2', 'city', 'state_id', 'partner_id'],
            offset=offset, limit=limit
        )
        
        json_return = []
        for comp in companies:
            # Obter o partner_id do campo Many2one
            partner_field = comp.get('partner_id')
            lat = None
            lon = None
            if partner_field:
                partner_id = partner_field[0]
                partner = request.env['res.partner'].sudo().browse(partner_id)
                # Supomos que o modelo res.partner possui os campos partner_latitude e partner_longitude
                lat = partner.partner_latitude or 0
                lon = partner.partner_longitude or 0
                # Se as coordenadas estiverem zeradas, executa o cálculo (atenção: pode ser processamento pesado)
                if lat == 0 and lon == 0:
                    request.env['products.model'].calculate_coordinates(partner_id)
                    # Invalida o cache para forçar a nova leitura
                    #partner.invalidate_cache()
                    lat = partner.partner_latitude or 0
                    lon = partner.partner_longitude or 0

            # Monta o endereço com os campos disponíveis
            state_name = comp.get('state_id')[1] if comp.get('state_id') else ''
            address = " - ".join(filter(None, [comp.get('street'), comp.get('street2')])) + f" - {comp.get('city')}/{state_name}"

            data = {
                "id": comp.get('id'),
                "cnpj": None,
                "address": address,
                "billing_address": None,
                "name": comp.get('name'),
                "phone": None,
                "lat": lat if lat else None,
                "long": lon if lon else None,
                "sap": None,
                "started_when": None,
            }
            json_return.append(data)

        return request.make_response(
            json.dumps(json_return),
            headers=[('Content-Type', 'application/json')]
        )
