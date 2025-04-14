from odoo import http
from odoo.http import request, Controller
from odoo.fields import Datetime
from datetime import datetime, time
import pytz
import json
import logging

from ..utils.date_utils import parse_date

_logger = logging.getLogger(__name__)

class ClientsController(Controller):

    @http.route('/api/clients/', type='http', auth='none', methods=['GET'], csrf=False)
    def get_clients(self):
        # 1) Autenticação via Bearer token
        auth_header = request.httprequest.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return request.make_response(
                json.dumps({"error": "Token não fornecido no header de autorização"}),
                status=401,
                headers=[('Content-Type', 'application/json')]
            )
        token = auth_header.split(' ', 1)[1].strip()
        try:
            request.env['auth.model'].sudo().verify_token(token)
        except Exception as e:
            _logger.exception("Token inválido: %s", e)
            return request.make_response(
                json.dumps({"error": "Token inválido"}),
                status=401,
                headers=[('Content-Type', 'application/json')]
            )

        # 2) Parâmetros de paginação (com defaults)
        try:
            page = int(request.params.get('page', 1))
            page_size = int(request.params.get('page_size', 20))
        except ValueError:
            return request.make_response(
                json.dumps({"error": "Os parâmetros 'page' e 'page_size' devem ser inteiros."}),
                status=400,
                headers=[('Content-Type', 'application/json')]
            )

        start_date_str   = request.params.get('start_date')
        end_date_str     = request.params.get('end_date')

        domain = []

        # 3a) Filtro de datas
        if start_date_str and end_date_str:
            try:
                # parse_date suporta YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS e DD/MM/YYYY
                start_date = parse_date(start_date_str)
                end_date   = parse_date(end_date_str)

                local_tz = pytz.timezone("America/Sao_Paulo")
                # início do dia sem microssegundos
                start_dt = local_tz.localize(datetime.combine(start_date, time.min))
                # fim do dia às 23:59:59
                end_dt   = local_tz.localize(datetime.combine(end_date, time(23, 59, 59)))

                # converte para UTC e formata como string que o Odoo entende
                start_utc = start_dt.astimezone(pytz.utc)
                end_utc   = end_dt.astimezone(pytz.utc)

                domain.append(('create_date', '>=', Datetime.to_string(start_utc)))
                domain.append(('create_date', '<=', Datetime.to_string(end_utc)))

                _logger.info("Filtro de datas aplicado: %s", domain)
            except Exception as e:
                _logger.exception("Erro ao converter datas: %s", e)
                return request.make_response(
                    json.dumps({
                        "error": "Erro ao converter as datas. Use um dos formatos: "
                                 "YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS ou DD/MM/YYYY."
                    }),
                    status=400,
                    headers=[("Content-Type", "application/json")]
                )
            

        # 4) Filtros fixos: remove parceiros já ligados a usuários e sem is_company
        users = request.env['res.users'].sudo().search([])
        removed_partner_ids = users.mapped('partner_id').ids
        domain += [
            ('id', 'not in', removed_partner_ids),
            ('is_company', '=', False),
        ]

        _logger.info("Domínio final de busca: %s", domain)

        # 5) Busca com paginação
        offset = (page - 1) * page_size
        Partner = request.env['res.partner'].sudo()
        partners = Partner.search(domain, offset=offset, limit=page_size)

        # 6) Monta resposta JSON
        data = []
        for p in partners:
            street = ' '.join(filter(None, [p.street, p.street2]))
            data.append({
                "id": p.id,
                "name": p.name,
                "birth_date": p.dob.isoformat() if p.dob else None,
                "address": street,
                "address_number": p.building_number,
                "address_city": p.city,
                "address_state": p.state_id.name if p.state_id else None,
                "address_zip_code": p.zip,
                "email": p.email,
                "cpf": p.vat,
                "cel": p.phone,
                "gender": p.gender,
                "changed_when": p.write_date.isoformat() if p.write_date else None,
                "created": p.create_date.isoformat() if p.create_date else None,
                "accept_info": True,
                "corretor_account_id_crm": None,
            })

        total_count = Partner.search_count(domain)
        has_next = offset + page_size < total_count

        return request.make_response(
            json.dumps({
                "data": data,
                "page": page,
                "page_size": page_size,
                "has_next": has_next,
                "total_count": total_count
            }),
            headers=[('Content-Type', 'application/json')]
        )
