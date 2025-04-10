from odoo import http
from odoo.http import request, Response, Controller
from werkzeug.exceptions import BadRequest
import json
import logging

_logger = logging.getLogger(__name__)

class VisitsController(Controller):
    @http.route('/api/visits/', type='http', auth='none', methods=['GET'], csrf=False)
    def get_visits(self):
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

        leads = request.env['crm.lead'].sudo().search([],offset=offset,limit=page_size)

        json_return = []
        for lead in leads:
            team_member = request.env['crm.team.member'].sudo().search([('email', '=', lead.user_id.login)],limit=1)

            data = {
                "id": lead.id,
                "third_party_id": None,
                "broker_name": " - ".join([lead.user_id.name, team_member.sales_name]),
                "manager_name": team_member.crm_team_id.user_id.name,
                "superintendent_name": None,
                "indication_broker_name": None,
                "sales_company_id": None, # todo: esse id é do sistema da incorporadora ou posso só colocar o do Odoo aleatório?
                "another": None,
                "product_id": team_member.company_id.unique_id, # todo: perguntar qual id deve ser puxado
                "customer_id": None, # todo: não sei qual id puxar aqui
                "type_of": "FIRSTCONTACT", # todo: FIRSTCONTACT, RECURRENCE, PHONECONTACT - de onde eu puxo isso?
                "out_of_service": "2024-01-02 00:00",  # todo: o que é isso
                "created": "2024-01-02 11:33",
                "justify_id": None, # todo: descobrir esse ID
                "owner": False, # todo: true or false n sei oq é
                "indication": False, # todo: true or false n sei oq é
                "created_by": 2390, # todo: id broker
                "changed_by": 5769, # todo id broker de novo
                "changed_when": "2024-01-03 11:57", # todo: data da mudança
                "main_media_id": 136, #todo: id da media
                "corretor_account_id_crm": 1072, #todo: não sei o que é
                "recebido_crm": False, #todo: talvez uma integração com a tabela de log
                "regra3": False,  #todo: nao sei o que é
                "broker_email": lead.user_id.login,
                "product_type_id": 371 #todo: id do tipo de produto?
            }

            # _logger.info("Data recebido: %s", data)
            json_return.append(data)

        total_count = request.env['crm.lead'].sudo().search_count([])
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