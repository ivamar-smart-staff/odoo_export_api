from odoo import http
from odoo.http import request, Response, Controller
import json
import logging

_logger = logging.getLogger(__name__)

class CompanyMediaController(http.Controller):
    @http.route('/api/company-media/', type='http', auth='none', methods=['GET'], csrf=False)
    def get_company_media(self):
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
        
        try:
            page = int(request.params.get('page', 1))
            limit = int(request.params.get('page_size', 100))
        except ValueError:
            return request.make_response(
                json.dumps({"error": "Os parâmetros 'page' e 'limit' devem ser números inteiros."}),
                status=400,
                headers=[('Content-Type', 'application/json')]
            )
        offset = (page - 1) * limit
        companies = request.env['res.company'].sudo().search([], offset=offset, limit=limit)
        total_count = request.env['res.company'].sudo().search_count([])
        
        result = []
        for comp in companies:
            media_records = comp.midia_ids.read([
                'nome_midia', 'cod_midia1', 'cod_midia2',
                'cod_midia3', 'cod_midia4', 'cod_midia5', 'cod_midia6'
            ])
            comp_data = {
                "company_id": comp.id,
                "company_name": comp.name,
                "media": media_records
            }
            result.append(comp_data)
        
        has_next = offset + limit < total_count
        
        response_data = {
            "data": result,
            "page": page,
            "limit": limit,
            "total_count": total_count,
            "has_next": has_next
        }
        
        return request.make_response(
            json.dumps(response_data, ensure_ascii=False),
            headers=[('Content-Type', 'application/json')]
        )
