from django.apps import AppConfig


class LlmConfig(AppConfig):
    name = "apps.llm"
    label = "llm"
    verbose_name = "LLM"
    default_auto_field = "django.db.models.BigAutoField"
