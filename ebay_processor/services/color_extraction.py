# ebay_processor/services/color_extraction.py
"""
Servicio de Extracción de Colores de Producto.

Este servicio se especializa en una tarea compleja: determinar el color de la alfombra
y el color del ribete (trim) a partir del título de un producto de eBay.
La lógica está diseñada para manejar una gran variedad de formatos de títulos,
priorizando contextos explícitos sobre suposiciones.
"""

import logging
import re
from typing import Tuple

# Importamos las constantes para mantener la consistencia
from ..core.constants import ALLOWED_COLORS, Carpet, Embroidery

logger = logging.getLogger(__name__)

def extract_carpet_and_trim_colors(title: str) -> Tuple[str, str]:
    """
    Analiza el título de un producto para extraer el color de la alfombra y del ribete.

    El proceso sigue un orden de prioridad:
    1.  Determina si es una alfombra de goma ('Rubber'). Si es así, el color de la alfombra es 'Rubber'.
    2.  Busca menciones explícitas como "Red Trim" o "Black Carpet". Estas tienen la máxima prioridad.
    3.  Analiza patrones complejos dentro de corchetes, como "[Color with Color Trim]".
    4.  Como último recurso, busca colores en el título y los asigna basándose en su posición.
    5.  Aplica valores por defecto inteligentes si no se encuentra alguno de los colores.

    Args:
        title: El título del producto de eBay.

    Returns:
        Una tupla con (carpet_color, trim_color). Ambos son strings capitalizados.
        Ej: ('Black', 'Red'), ('Grey', 'Grey'), ('Rubber', 'Black').
    """
    # -------------------
    # 1. Inicialización y Limpieza
    # -------------------
    if not isinstance(title, str):
        logger.warning(f"Se recibió un título no válido (tipo: {type(title)}). Usando valores por defecto.")
        return 'Black', 'Black'

    title_lower = title.lower().strip()
    
    # Valores por defecto que se sobreescribirán si se encuentra algo
    carpet_color = 'Black'
    trim_color = 'Black'

    # -------------------
    # 2. Detección de Goma (Rubber)
    # -------------------
    # Esta es la regla más importante y debe ir primero.
    # Si es de goma, el color de la alfombra siempre es 'Rubber'.
    is_rubber = any(rubber_keyword in title_lower for rubber_keyword in ['rubber', 'rubstd', 'rubhd', '5mm'])
    if is_rubber:
        carpet_color = 'Rubber'
        # No salimos aún, porque una alfombra de goma puede tener un ribete de color específico.
        logger.debug(f"Título '{title[:30]}...': Detectado como Goma. Carpet='Rubber'.")

    # -------------------
    # 3. Búsqueda de Contexto Explícito (Máxima Prioridad)
    # -------------------
    # Patrones como "Red Trim" o "Blue Carpet" son los más fiables.
    # Usamos finditer para buscar todas las ocurrencias y nos quedamos con la última,
    # que suele ser la correcta en títulos complejos.
    
    # Buscar "Color Trim" o "Color Edge"
    explicit_trim_match = re.search(r'\b(' + '|'.join(ALLOWED_COLORS) + r')\s+(trim|edge)\b', title_lower)
    if explicit_trim_match:
        trim_color = explicit_trim_match.group(1).capitalize()
        logger.debug(f"Título '{title[:30]}...': Encontrado Trim explícito: '{trim_color}'.")
        
    # Buscar "Color Carpet" (solo si no es de goma)
    if not is_rubber:
        explicit_carpet_match = re.search(r'\b(' + '|'.join(ALLOWED_COLORS) + r')\s+carpet\b', title_lower)
        if explicit_carpet_match:
            carpet_color = explicit_carpet_match.group(1).capitalize()
            logger.debug(f"Título '{title[:30]}...': Encontrado Carpet explícito: '{carpet_color}'.")

    # -------------------
    # 4. Análisis de Patrones Complejos (dentro de corchetes)
    # -------------------
    # Muchos títulos usan corchetes para especificar variaciones.
    # Ej: "[Black with Red Trim,Does Not Apply]"
    bracket_content_match = re.search(r'\[(.*?)\]', title_lower)
    if bracket_content_match:
        content = bracket_content_match.group(1)
        
        # Patrón: "Color1 with Color2 Trim"
        with_trim_pattern = re.search(r'\b(' + '|'.join(ALLOWED_COLORS) + r')\s+with\s+(' + '|'.join(ALLOWED_COLORS) + r')\s+trim\b', content)
        if with_trim_pattern:
            # Si encontramos este patrón, es muy fiable y sobreescribe lo anterior.
            if not is_rubber:
                carpet_color = with_trim_pattern.group(1).capitalize()
            trim_color = with_trim_pattern.group(2).capitalize()
            logger.debug(f"Título '{title[:30]}...': Patrón 'with trim' encontrado. Carpet='{carpet_color}', Trim='{trim_color}'.")

    # -------------------
    # 5. Fallback: Búsqueda de Colores sin Contexto
    # -------------------
    # Si después de todo lo anterior seguimos con los valores por defecto,
    # buscamos cualquier color mencionado y lo asignamos.
    
    # Creamos una lista de todos los colores encontrados en el título.
    found_colors = [color for color in ALLOWED_COLORS if re.search(r'\b' + color + r'\b', title_lower)]
    
    if found_colors:
        # Si la alfombra sigue siendo 'Black' por defecto (y no es de goma),
        # asignamos el primer color encontrado en el título.
        if carpet_color == 'Black' and not is_rubber:
            # Excluimos el color que ya podría estar asignado al trim para evitar duplicados.
            available_colors = [c for c in found_colors if c.capitalize() != trim_color]
            if available_colors:
                carpet_color = available_colors[0].capitalize()
                logger.debug(f"Título '{title[:30]}...': Fallback asignó Carpet='{carpet_color}'.")

    # -------------------
    # 6. Lógica Final de Defectos Inteligentes
    # -------------------
    # Si el trim sigue siendo el 'Black' por defecto pero la alfombra tiene un color,
    # es muy probable que el trim sea del mismo color que la alfombra.
    # Ej: Título "Red Car Mats" -> Carpet='Red', Trim debería ser 'Red', no 'Black'.
    if trim_color == 'Black' and carpet_color not in ['Black', 'Rubber']:
        trim_color = carpet_color
        logger.debug(f"Título '{title[:30]}...': Defaulting inteligente, Trim igual a Carpet: '{trim_color}'.")
        
    logger.info(f"Título: '{title[:50]}...' -> Extraído: Carpet='{carpet_color}', Trim='{trim_color}'.")
    return carpet_color, trim_color


def determine_carpet_type(title: str) -> str:
    """
    Determina el tipo de alfombra (CT65, Velour, Goma) a partir del título.

    Args:
        title: El título del producto de eBay.

    Returns:
        Un string representando el tipo de alfombra (usando constantes de `Carpet`).
    """
    if not isinstance(title, str):
        return Carpet.STANDARD # Valor por defecto

    title_lower = title.lower()
    
    if 'velour' in title_lower:
        return Carpet.VELOUR
    if '5mm' in title_lower or 'heavy duty rubber' in title_lower:
        return Carpet.RUBBER_HD
    if 'rubber' in title_lower:
        return Carpet.RUBBER_STD
        
    return Carpet.STANDARD


def determine_embroidery_type(title: str) -> str:
    """
    Determina el tipo de bordado a partir del título.

    Args:
        title: El título del producto de eBay.

    Returns:
        "Double Stitch" o una cadena vacía (usando constantes de `Embroidery`).
    """
    if not isinstance(title, str):
        return Embroidery.NONE # Valor por defecto

    # Palabras clave que indican "Double Stitch"
    keywords = ["GREYDS", "BLACKDS", "REDS", "BLUEDS", "UPGRADED", "DOUBLE STITCH"]
    
    title_upper = title.upper()
    if any(keyword in title_upper for keyword in keywords):
        return Embroidery.DOUBLE_STITCH
        
    return Embroidery.NONE