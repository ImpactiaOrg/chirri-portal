"""Widgets — unidades atómicas de contenido dentro de una Section.

Polimórficos vía django-polymorphic. Cada subtipo aporta sus campos.
La base define lo compartido: section FK, order, title (subtítulo
opcional dentro del widget), instructions (AI hint), timestamps.
"""
