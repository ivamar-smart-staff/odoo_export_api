from datetime import datetime

def parse_date(date_str):
    """Tenta converter uma string em datetime usando vários formatos."""
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        pass
    
    formats = ["%Y-%m-%d", "%d/%m/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Formato de data inválido: {date_str}")