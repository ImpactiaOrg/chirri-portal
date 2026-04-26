"""Admin for apps.llm.

PromptAdmin: name/description editable, list of versions read-only,
new-version + set-active + diff actions.
LLMJobAdmin / LLMCallAdmin: read-only audit + status page.
"""
import difflib
import json
import logging

from django.contrib import admin, messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse

from .models import LLMCall, LLMJob, Prompt, PromptVersion

logger = logging.getLogger(__name__)


class PromptVersionInline(admin.TabularInline):
    model = PromptVersion
    extra = 0
    fields = ("version", "model_hint", "response_format", "notes",
              "created_by", "created_at")
    readonly_fields = fields
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "consumer", "active_version_display",
                    "updated_at")
    list_filter = ("consumer",)
    search_fields = ("key", "name", "description", "consumer")
    fieldsets = (
        (None, {"fields": ("key", "name", "description", "consumer",
                           "active_version_display_ro")}),
    )
    readonly_fields = ("active_version_display_ro",)
    inlines = [PromptVersionInline]

    @admin.display(description="Versión activa")
    def active_version_display(self, obj):
        return f"v{obj.active_version.version}" if obj.active_version else "—"

    @admin.display(description="Versión activa")
    def active_version_display_ro(self, obj):
        return self.active_version_display(obj)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("<int:prompt_id>/new-version/",
                 self.admin_site.admin_view(self.new_version_view),
                 name="llm_prompt_new_version"),
            path("<int:prompt_id>/set-active/<int:version_id>/",
                 self.admin_site.admin_view(self.set_active_view),
                 name="llm_prompt_set_active"),
            path("<int:prompt_id>/diff/<int:a_id>/<int:b_id>/",
                 self.admin_site.admin_view(self.diff_view),
                 name="llm_prompt_diff"),
        ]
        return custom + urls

    def new_version_view(self, request, prompt_id: int):
        p = get_object_or_404(Prompt, pk=prompt_id)
        if request.method == "POST":
            schema_raw = request.POST.get("json_schema", "").strip()
            try:
                schema = json.loads(schema_raw) if schema_raw else None
            except json.JSONDecodeError as exc:
                messages.error(request, f"json_schema inválido: {exc}")
                return redirect(reverse(
                    "admin:llm_prompt_change", args=[prompt_id],
                ))
            v = PromptVersion.objects.create(
                prompt=p,
                body=request.POST.get("body", ""),
                notes=request.POST.get("notes", "")[:300],
                model_hint=request.POST.get("model_hint", "")[:100],
                response_format=request.POST.get("response_format", "text"),
                json_schema=schema,
                created_by=request.user,
            )
            messages.success(request,
                             f"Creada {p.key}@v{v.version} (no activada).")
            return redirect(reverse(
                "admin:llm_prompt_change", args=[prompt_id],
            ))
        # GET: render a small form template inline.
        return render(request, "admin/llm/prompt/new_version.html", {
            **self.admin_site.each_context(request),
            "prompt": p,
            "active": p.active_version,
            "opts": self.model._meta,
        })

    def set_active_view(self, request, prompt_id: int, version_id: int):
        p = get_object_or_404(Prompt, pk=prompt_id)
        v = get_object_or_404(PromptVersion, pk=version_id, prompt=p)
        p.active_version = v
        p.save()
        messages.success(request, f"{p.key}@v{v.version} ahora es la versión activa.")
        return redirect(reverse("admin:llm_prompt_change", args=[prompt_id]))

    def diff_view(self, request, prompt_id: int, a_id: int, b_id: int):
        p = get_object_or_404(Prompt, pk=prompt_id)
        a = get_object_or_404(PromptVersion, pk=a_id, prompt=p)
        b = get_object_or_404(PromptVersion, pk=b_id, prompt=p)
        diff_html = difflib.HtmlDiff(wrapcolumn=80).make_table(
            a.body.splitlines(), b.body.splitlines(),
            fromdesc=f"v{a.version}", todesc=f"v{b.version}",
            context=False,
        )
        return render(request, "admin/llm/prompt/diff.html", {
            **self.admin_site.each_context(request),
            "prompt": p, "a": a, "b": b, "diff_html": diff_html,
            "opts": self.model._meta,
        })


@admin.register(PromptVersion)
class PromptVersionAdmin(admin.ModelAdmin):
    list_display = ("prompt", "version", "model_hint", "response_format",
                    "created_by", "created_at")
    list_filter = ("response_format", "prompt__consumer")
    search_fields = ("prompt__key", "notes", "body")
    readonly_fields = ("prompt", "version", "body", "notes", "model_hint",
                       "response_format", "json_schema", "created_by", "created_at")

    def has_add_permission(self, request):
        return False
