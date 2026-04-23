"""Choices compartidos por los bloques tipados (DEV-116).

Extraído de ReportMetric para que los bloques puedan referenciarlos sin
depender de un modelo que está siendo eliminado.
"""
from django.db import models


class Network(models.TextChoices):
    INSTAGRAM = "INSTAGRAM", "Instagram"
    TIKTOK = "TIKTOK", "TikTok"
    X = "X", "X/Twitter"


class SourceType(models.TextChoices):
    ORGANIC = "ORGANIC", "Orgánico"
    INFLUENCER = "INFLUENCER", "Influencer"
    PAID = "PAID", "Pauta"
