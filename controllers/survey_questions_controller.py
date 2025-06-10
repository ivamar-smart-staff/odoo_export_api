from odoo import http
from odoo.http import request, Response, Controller
from datetime import datetime, time, timezone
import json
import logging
import pytz

from ..utils.date_utils import parse_date

_logger = logging.getLogger(__name__)


class SurveyResponsesController(http.Controller):

    @http.route('/api/survey/responses/', type='http', auth='none', methods=['GET'], csrf=False)
    def get_all_survey_responses(self):
        # Validação do token via header "Authorization"
        auth_header = request.httprequest.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return request.make_response(
                json.dumps({"error": "Token não fornecido no header de autorização"}),
                status=401,
                headers=[("Content-Type", "application/json")]
            )
        token = auth_header.split(" ")[1].strip()
        try:
            request.env["auth.model"].sudo().verify_token(token)
        except Exception as e:
            _logger.exception("Token inválido: %s", e)
            return request.make_response(
                json.dumps({"error": "Token inválido"}),
                status=401,
                headers=[("Content-Type", "application/json")]
            )

        # Obtenção e validação dos parâmetros de paginação
        try:
            page = int(request.params.get("page", 1))
            limit = int(request.params.get("limit", 100))
        except ValueError:
            return request.make_response(
                json.dumps({"error": "Os parâmetros 'page' e 'limit' devem ser números inteiros."}),
                status=400,
                headers=[("Content-Type", "application/json")]
            )
        offset = (page - 1) * limit

        # Parâmetro opcional para filtrar pela company (pelo id da company)
        domain = []
        company_id_param = request.params.get("company_id")
        start_date_str = request.params.get("start_date")
        end_date_str = request.params.get("end_date")

        if start_date_str and end_date_str:
            try:
                # Converte para date
                start_dt = parse_date(start_date_str)
                end_dt = parse_date(end_date_str)

                # Define timezone local (BR) e aplica hora mínima e máxima
                local_tz = pytz.timezone("America/Sao_Paulo")
                start_dt = local_tz.localize(datetime.combine(start_dt, time.min))
                end_dt = local_tz.localize(datetime.combine(end_dt, time.max))

                # Converte para UTC (sem precisar do ir.utils)
                start_date = start_dt.astimezone(pytz.utc)
                end_date = end_dt.astimezone(pytz.utc)

                # Aplica no domínio
                domain.append(("create_date", ">=", start_date))
                domain.append(("create_date", "<=", end_date))

                _logger.info("Domínio final: %s", domain)


            except Exception as e:
                _logger.exception("Erro ao converter datas: %s", e)
                return request.make_response(
                    json.dumps({
                        "error": "Erro ao converter as datas. Use um dos formatos: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS ou DD/MM/YYYY."
                    }),
                    status=400,
                    headers=[("Content-Type", "application/json")]
                )

        if company_id_param:
            try:
                company_id = int(company_id_param)
                domain.append(("company_id", "=", company_id))
            except ValueError:
                return request.make_response(
                    json.dumps({"error": "O parâmetro 'company_id' deve ser um número inteiro."}),
                    status=400,
                    headers=[("Content-Type", "application/json")]
                )

        # Lista de campos do crm.lead que fazem parte do survey
        '''Campos retirados: 
        is_filhos
        monthly_income
        search_duration
        change_duration
        tamanho
        buscando
        incorporadora
        aqua
        falta
        interessado
        review1
        review2
        review4
        review5
        attention
        '''
        text_fields = [
            "filhos", "children_living", "profession_list", "monthly_income_new", "age_limit",
            "reason_for_property", "communicao_selection", "tamanho_new", "buscando_new",
            "incorporadora_selection", "aqua_selection_new", "review1_new", "review3_new"
        ]
        options_fields = [
            "free_time", "buy_property_ids", "venture_ids", "displease_venture_ids"
        ]

        total_all = request.env['crm.lead'].sudo().search_count([
            ('company_id', '=', 3)
        ])

        # Busca as leads com paginação, aplicando o domínio (filtragem por company, se fornecido)
        leads = request.env["crm.lead"].sudo().search(domain, offset=offset, limit=limit)
        total_count = request.env["crm.lead"].sudo().search_count(domain)

        lead_model = request.env["crm.lead"]
        results = []
        for lead in leads:
            text_questions = {}
            for field in text_fields:
                label = lead_model._fields[field].string if field in lead_model._fields else field
                value = lead[field]
                field_obj = lead_model._fields.get(field)
                if field_obj:
                    if field_obj.type == "boolean":
                        text_questions[label] = value if value is not None else False
                    elif field_obj.type == "selection":
                        selection_options = field_obj.selection(lead.env) if callable(
                            field_obj.selection) else field_obj.selection
                        selections_dict = dict(selection_options)
                        text_questions[label] = selections_dict.get(value, value)
                    else:
                        text_questions[label] = value if value is not None else ""
                else:
                    text_questions[label] = value if value is not None else ""

            options_questions = {}
            for field in options_fields:
                label = lead_model._fields[field].string if field in lead_model._fields else field
                value = lead[field]
                if hasattr(value, "mapped"):
                    options_questions[label] = value.mapped("name") if value else []
                else:
                    options_questions[label] = value if value is not None else ""

            res = {
                "lead_id": lead.id,
                "user_id": lead.user_id.id if lead.user_id else None,
                "text_questions": text_questions,
                "options_questions": options_questions,
            }
            results.append(res)

        has_next = offset + limit < total_count
        response_data = {
            "data": results,
            "page": page,
            "limit": limit,
            "total_count": total_count,
            "has_next": has_next
        }

        return request.make_response(
            json.dumps(response_data, ensure_ascii=False),
            headers=[("Content-Type", "application/json")]
        )
