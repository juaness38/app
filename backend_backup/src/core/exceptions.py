# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - EXCEPCIONES PERSONALIZADAS
LUIS: Manejo de errores limpio y estructurado.
"""

class AstrofloraException(Exception):
    """LUIS: Clase base para todas nuestras excepciones."""
    pass

class ConfigurationError(AstrofloraException):
    """LUIS: Para errores fatales de configuración que deben detener la app."""
    pass

class ServiceUnavailableException(AstrofloraException):
    """LUIS: Cuando una dependencia externa no está disponible."""
    pass

class AnalysisNotFoundException(AstrofloraException):
    """LUIS: Cuando se solicita un análisis que no existe."""
    pass

class DriverIAException(AstrofloraException):
    """LUIS: Errores específicos del Driver IA."""
    pass

class ToolGatewayException(AstrofloraException):
    """LUIS: Errores en la comunicación con herramientas externas."""
    pass

class CircuitBreakerOpenException(AstrofloraException):
    """LUIS: Cuando un Circuit Breaker está abierto."""
    pass

class CapacityExceededException(AstrofloraException):
    """LUIS: Cuando se excede la capacidad del sistema."""
    pass