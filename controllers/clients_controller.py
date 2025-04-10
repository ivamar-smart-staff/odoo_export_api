from odoo import http
from odoo.http import request, Response, Controller
from werkzeug.exceptions import BadRequest
import json
import logging

_logger = logging.getLogger(__name__)

class ClientsController(Controller):
    @http.route('/api/clients/', type='http', auth='none', methods=['GET'], csrf=False)
    def get_clients(self):
        # Validação do token via parâmetros (query string)
        token = request.params.get('token')
        if not token:
            return request.make_response(
                json.dumps({"error": "Token não fornecido"}),
                status=401,
                headers=[('Content-Type', 'application/json')]
            )
        try:
            # Verifica o token usando o modelo de autenticação
            request.env['auth.model'].sudo().verify_token(token)
        except Exception as e:
            _logger.exception("Token inválido: %s", e)
            return request.make_response(
                json.dumps({"error": "Token inválido"}),
                status=401,
                headers=[('Content-Type', 'application/json')]
            )

        # Obtenção e validação dos parâmetros de paginação
        page = request.params.get('page')
        page_size = request.params.get('page_size')
        if not page or not page_size:
            return request.make_response(
                json.dumps({"error": "Os parâmetros 'page' e 'page_size' são obrigatórios na URL."}),
                status=400,
                headers=[('Content-Type', 'application/json')]
            )
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

        # Busca os usuários para identificar quais parceiros foram removidos (por exemplo, parceiros já ligados a usuários)
        users = request.env['res.users'].sudo().search([])
        removed_user_partner_ids = users.mapped('partner_id').ids

        # Domínio atualizado: além de filtrar os parceiros removidos, filtra apenas os que não são empresas (is_company=False)
        domain = [
            ('id', 'not in', removed_user_partner_ids),
            ('is_company', '=', False)
        ]
        
        # Consulta otimizada com paginação
        partners = request.env['res.partner'].sudo().search(
            domain,
            offset=offset,
            limit=page_size
        )

        json_return = []
        for partner in partners:
            street = (partner.street or '') + ' ' + (partner.street2 or '')
            data = {
                "id": partner.id,
                "name": partner.name,
                "birth_date": partner.dob.isoformat() if partner.dob else None,
                "address": street,
                "address_number": partner.building_number,
                "address_adjunct": "resid",
                "address_district": "Tamboré",
                "address_city": partner.city,
                "address_state": partner.state_id.name if partner.state_id else None,
                "address_zip_code": partner.zip,
                "email": partner.email,
                "cpf": partner.vat,
                "cel": partner.phone,
                "gender": partner.gender,
                "changed_when": partner.write_date.isoformat() if partner.write_date else None,
                "created": partner.create_date.isoformat() if partner.create_date else None,
                "accept_info": True,
                "corretor_account_id_crm": None,
            }
            json_return.append(data)

        total_count = request.env['res.partner'].sudo().search_count(domain)
        has_next = offset + page_size < total_count

        return request.make_response(
            json.dumps({
                "data": json_return,
                "page": page,
                "page_size": page_size,
                "has_next": has_next,
                "total_count": total_count
            }),
            headers=[('Content-Type', 'application/json')]
        )
