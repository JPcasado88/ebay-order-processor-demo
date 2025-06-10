# ebay_processor/services/car_details_extractor.py
"""
Servicio de Extracción de Detalles de Vehículos.
...
"""

import logging
import re
from typing import Dict, Optional

# Importamos las utilidades de los módulos correctos.
from ..utils.string_utils import normalize_make, normalize_model
from ..utils.date_utils import normalize_year_range # <<< Importado desde su nuevo hogar.

logger = logging.getLogger(__name__)

class CarDetailsExtractor:
    """
    Encapsula la lógica para extraer marca, modelo y año de un título de producto.
    """

    # Palabras comunes en los títulos que no aportan información sobre el vehículo
    # y que pueden interferir con la extracción.
    NOISE_WORDS = [
        'tailored', 'carpet', 'car mats', 'floor mats', 'set', '4pcs', '5pcs', 'pc',
        'heavy duty', 'rubber', 'solid trim', 'uk made', 'custom', 'fully',
        'black', 'grey', 'blue', 'red', 'beige', 'with', 'trim', 'edge', 'for', 'fits'
    ]
    
    # Patrón de regex principal y más fiable. Busca la estructura:
    # (Marca) (Modelo) (Año)
    # - La marca es una o más palabras.
    # - El modelo es cualquier cosa hasta encontrar el año.
    # - El año tiene varios formatos: 2010-2015, 2020+, 2024, etc.
    VEHICLE_PATTERN = re.compile(
        # Grupo 1: Marca (no codicioso)
        r'([A-Za-z\s\-]+?)\s+'
        # Grupo 2: Modelo (cualquier caracter, no codicioso)
        r'(.*?)\s+'
        # Grupo 3: Año (múltiples formatos)
        r'(\d{4}\s*[-–to]+\s*\d{4}|\d{4}\s*[-–to]+\s*present|\d{4}\s*\+?|\d{4})',
        re.IGNORECASE
    )

    def _clean_title(self, title: str) -> str:
        """
        Pre-procesa el título para eliminar ruido y facilitar la extracción.
        
        Args:
            title: El título original del producto.

        Returns:
            El título limpio.
        """
        # Eliminar contenido dentro de corchetes, ej: [Black with Red Trim]
        clean_title = re.sub(r'\[.*?\]', ' ', title)
        
        # Eliminar las palabras "ruido" definidas en la clase.
        # Se construye un regex para buscar cualquiera de estas palabras completas (\b).
        noise_pattern = r'\b(' + '|'.join(self.NOISE_WORDS) + r')\b'
        clean_title = re.sub(noise_pattern, ' ', clean_title, flags=re.IGNORECASE)
        
        # Normalizar múltiples espacios a uno solo.
        return ' '.join(clean_title.split())

    def extract(self, title: str) -> Optional[Dict[str, str]]:
        """
        Método principal para extraer los detalles del vehículo de un título.

        Args:
            title: El título del producto de eBay.

        Returns:
            Un diccionario con 'make', 'model' y 'year' si se encuentra una coincidencia,
            o None en caso contrario.
        """
        if not isinstance(title, str):
            return None
        
        clean_title = self._clean_title(title)
        
        match = self.VEHICLE_PATTERN.search(clean_title)
        
        if not match:
            logger.debug(f"No se pudieron extraer detalles del título: '{title}' (limpio: '{clean_title}')")
            return None
            
        make_raw, model_raw, year_raw = match.groups()
        
        # Usamos nuestras funciones de utilidad para normalizar los resultados.
        make = normalize_make(make_raw)
        model = normalize_model(model_raw)
        year = normalize_year_range(year_raw)
        
        # Verificación final: asegurarnos de que la marca y el modelo no estén vacíos.
        if not make or not model:
            logger.warning(f"Extracción parcial para '{title}'. Make o Model vacío después de normalizar.")
            return None

        logger.info(f"Título '{title[:50]}...' -> Extraído: Make='{make}', Model='{model}', Year='{year}'")
        return {
            'make': make,
            'model': model,
            'year': year
        }