"""Módulo de validación de calidad visual de SVGs generados."""
from AlmaGag.validation.visual_quality import (
    Violation,
    QualityReport,
    validate_svg,
    validate_gag,
)

__all__ = ['Violation', 'QualityReport', 'validate_svg', 'validate_gag']
