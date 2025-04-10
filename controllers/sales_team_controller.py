from odoo import http
from odoo.http import request, Response, Controller
import json
import logging

_logger = logging.getLogger(__name__)

class SalesTeamExportController(http.Controller):
    @http.route('/api/sales-teams/', type='http', auth='none', methods=['GET'], csrf=False)
    def get_sales_teams(self):
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
            request.env['auth.model'].sudo().verify_token(token)
        except Exception as e:
            _logger.exception("Token inválido: %s", e)
            return request.make_response(
                json.dumps({"error": "Token inválido"}),
                status=401,
                headers=[('Content-Type', 'application/json')]
            )

        # Obtenção e validação dos parâmetros de paginação
        page = request.params.get('page', 1)
        page_size = request.params.get('page_size', 100)
        try:
            page = int(page)
            page_size = int(page_size)
        except ValueError:
            return request.make_response(
                json.dumps({"error": "Os parâmetros 'page' e 'page_size' devem ser números inteiros."}),
                status=400,
                headers=[('Content-Type', 'application/json')]
            )
        offset = (page - 1) * page_size

        # Busca as equipes de vendas com paginação
        sales_teams = request.env['crm.team'].sudo().search([], offset=offset, limit=page_size)
        total_count = request.env['crm.team'].sudo().search_count([])

        result = []
        for team in sales_teams:
            team_data = {
                "id": team.id,
                "name": team.name,
                "brokers": []
            }
            # Itera sobre os usuários (corretores) da equipe
            for user in team.member_ids:
                broker_data = {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email or ""
                }
                team_data["brokers"].append(broker_data)

            result.append(team_data)

        has_next = offset + page_size < total_count
        response_data = {
            "data": result,
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "has_next": has_next
        }

        return request.make_response(
            json.dumps(response_data, ensure_ascii=False),
            headers=[('Content-Type', 'application/json')]
        )
