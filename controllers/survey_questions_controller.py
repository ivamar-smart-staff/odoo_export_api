from odoo import http
from odoo.http import request, Response, Controller
import json
import logging

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
        text_fields = [
            "filhos", "is_filhos", "profession_list", "monthly_income", "reason_for_property",
            "search_duration", "change_duration", "tamanho", "buscando", "incorporadora",
            "aqua", "interessado", "falta", "review1", "review2", "review3", "review4", "review5",
            "attention"
        ]
        options_fields = [
            "free_time", "buy_property_ids", "venture_ids", "displease_venture_ids"
        ]
        
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
                        selection_options = field_obj.selection(lead.env) if callable(field_obj.selection) else field_obj.selection
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
