from odoo import http
from odoo.http import request, Response, Controller
from werkzeug.exceptions import BadRequest
import json
import logging

_logger = logging.getLogger(__name__)

class ClientsController(Controller):
    @http.route('/api/clients/', type='http', auth='none', methods=['GET'], csrf=False)
    def get_clients(self):
        page = int(request.params.get('page'))
        page_size = int(request.params.get('page_size'))

        if not page or not page_size:
            raise BadRequest("Os parâmetros 'page' e 'page_size' são obrigatórios na URL.")

        try:
            page = int(page)
            page_size = int(page_size)
        except ValueError:
            raise BadRequest("Os parâmetros 'page' e 'page_size' devem ser números inteiros.")

        offset = (page - 1) * page_size

        users = request.env['res.users'].sudo().search([])
        removed_user_partner_ids = users.mapped('partner_id').ids

        partners = request.env['res.partner'].sudo().search(
            [('id', 'not in', removed_user_partner_ids)],
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
                "address_state": partner.state_id.name,
                "address_zip_code": partner.zip,
                "email": partner.email,
                "cpf": partner.vat,
                "cel": partner.phone,
                "gender": partner.gender,
                "changed_when": partner.write_date.isoformat() if partner.write_date else None,
                # "changed_by": null,
                "created": partner.create_date.isoformat() if partner.create_date else None,
                # "route": null,
                "accept_info": True,
                "corretor_account_id_crm": None,
                # "id_regiao": null,


            }

            # _logger.info("Data recebido: %s", data)
            json_return.append(data)

        total_count = request.env['res.partner'].sudo().search_count(
            [('id', 'not in', removed_user_partner_ids)]
        )
        has_next = offset + page_size < total_count

        return request.make_response(
            json.dumps({
                'data': json_return,
                'page': page,
                'page_size': page_size,
                'has_next': has_next,
                'total_count': total_count,
            }),
            headers=[('Content-Type', 'application/json')]
        )