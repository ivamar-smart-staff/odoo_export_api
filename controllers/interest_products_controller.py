from odoo import http
from odoo.http import request, Response, Controller
import json
import logging

_logger = logging.getLogger(__name__)

class LeadsInterestsController(http.Controller):
    @http.route('/api/leads/interests/', type='http', auth='none', methods=['GET'], csrf=False)
    def get_interests(self):
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
        try:
            page = int(request.params.get('page', 1))
            limit = int(request.params.get('limit', 100))
        except ValueError:
            return request.make_response(
                json.dumps({"error": "Os parâmetros 'page' e 'limit' devem ser números inteiros."}),
                status=400,
                headers=[('Content-Type', 'application/json')]
            )
        offset = (page - 1) * limit

        # Utilizando read_group para agrupar os leads pelo campo "interest"
        groups = request.env['crm.lead'].sudo().read_group([], ['interest'], ['interest'])
        interests = []
        for group in groups:
            interest_val = group.get('interest')
            if interest_val:
                interests.append(interest_val)

        # Se nenhum interesse estiver preenchido, utiliza os valores padrão
        if not interests:
            interests = ["residencial", "comercial", "investimento"]

        # Paginação na lista de interesses
        total_count = len(interests)
        paginated_interests = interests[offset:offset+limit]
        has_next = offset + limit < total_count

        response_data = {
            "data": paginated_interests,
            "page": page,
            "limit": limit,
            "total_count": total_count,
            "has_next": has_next
        }

        return request.make_response(
            json.dumps(response_data, ensure_ascii=False),
            headers=[('Content-Type', 'application/json')]
        )
