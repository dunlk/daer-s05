from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone
from django.utils.text import Truncator

from tienda.grupos import es_agente
from tienda.models import Sugerencia

from .verificador import verificar


class SugerenciaAdmin(admin.ModelAdmin):
    # Parte 2a: bandeja
    list_display = (
        "producto",
        "campo",
        "valor_actual_col",
        "valor_propuesto",
        "verificacion",
        "motivo_corto",
        "origen",
        "estado",
        "creado_por",
    )

    list_filter = ("estado", "origen", "campo")
    search_fields = ("producto__nombre", "motivo")
    list_select_related = ("producto", "creado_por")

    actions = ["aprobar_y_aplicar", "rechazar"]

    # Parte 2b: campos de solo lectura
    def get_readonly_fields(self, request, obj=None):
        campos = (
            "origen",
            "estado",
            "creado_por",
            "valor_anterior",
            "decidido_por",
            "decidido_en",
        )

        if obj is not None:
            return campos + (
                "producto",
                "campo",
                "valor_propuesto",
                "motivo",
            )

        return campos

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="actual")
    def valor_actual_col(self, obj):
        return obj.valor_actual()

    @admin.display(description="verificador")
    def verificacion(self, obj):
        if obj.estado != Sugerencia.PENDIENTE:
            return "—"

        problemas = verificar(obj)

        if problemas:
            return "✘ " + "; ".join(problemas)

        return "✔ pasa"

    @admin.display(description="motivo")
    def motivo_corto(self, obj):
        return Truncator(obj.motivo).chars(60)

    # Parte 2c: aprobar y aplicar
    @admin.action(
        description="Aprobar y aplicar (solo las que pasan el verificador)",
        permissions=["change"],
    )
    def aprobar_y_aplicar(self, request, queryset):
        aplicadas = 0
        decididas = 0

        with transaction.atomic():
            for s in queryset.select_related("producto"):
                if s.estado != Sugerencia.PENDIENTE:
                    decididas += 1
                    continue

                problemas = verificar(s)

                if problemas:
                    self.message_user(
                        request,
                        f"No se aplicó {s}: {'; '.join(problemas)}",
                        messages.WARNING,
                    )
                    continue

                producto = s.producto
                campo = s.campo

                valor_anterior = getattr(producto, campo)

                if campo == "stock":
                    valor_nuevo = int(s.valor_propuesto)
                else:
                    valor_nuevo = s.valor_propuesto

                setattr(producto, campo, valor_nuevo)
                producto.save()

                s.valor_anterior = valor_anterior
                s.estado = Sugerencia.APROBADA
                s.decidido_por = request.user
                s.decidido_en = timezone.now()
                s.save()

                self.log_change(
                    request,
                    producto,
                    f"{campo}: {valor_anterior} → {valor_nuevo}",
                )

                aplicadas += 1

        if decididas:
            self.message_user(
                request,
                f"{decididas} sugerencia(s) ya estaba(n) decidida(s).",
                messages.WARNING,
            )

        self.message_user(
            request,
            f"{aplicadas} sugerencia(s) aplicada(s).",
            messages.SUCCESS,
        )

    # Acción rechazar
    @admin.action(description="Rechazar", permissions=["change"])
    def rechazar(self, request, queryset):
        n = 0

        for s in queryset.filter(estado=Sugerencia.PENDIENTE):
            s.estado = Sugerencia.RECHAZADA
            s.decidido_por = request.user
            s.decidido_en = timezone.now()
            s.save()

            self.log_change(request, s, "Rechazada")
            n += 1

        self.message_user(
            request,
            f"{n} sugerencia(s) rechazada(s).",
            messages.SUCCESS,
        )

    @admin.display(description="verificador")
    def verificacion(self, obj):
        if obj.estado != Sugerencia.PENDIENTE:
            return "—"

        problemas = verificar(obj)

        if problemas:
            return "✘ " + "; ".join(problemas)

        return "✔ pasa"
