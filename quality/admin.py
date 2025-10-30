from django.contrib import admin
from django.conf import settings
from .models import (
    ProductionBatch, Measurement,  # demo
    LineaProduccion, Producto, ParametroControl, Medicion, DefectoTipo, Defecto  # reales (unmanaged)
)

USE_EXT = str(getattr(settings, 'USE_EXT_SCHEMA', '0')) == '1'

# --- Mixins de solo lectura ---
class ReadOnlyAdmin(admin.ModelAdmin):
    actions = None
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

# --- Registro condicional ---
if USE_EXT:
    # 1) Mostrar SOLO tus tablas reales (en modo consulta/solo-lectura)
    @admin.register(LineaProduccion)
    class LineaProduccionAdmin(ReadOnlyAdmin):
        list_display = ('id_linea', 'nombre', 'descripcion')
        search_fields = ('nombre',)

    @admin.register(Producto)
    class ProductoAdmin(ReadOnlyAdmin):
        list_display = ('id_producto', 'nombre', 'dimension', 'sdr')
        search_fields = ('nombre', 'dimension', 'sdr')

    @admin.register(ParametroControl)
    class ParametroControlAdmin(ReadOnlyAdmin):
        list_display = ('id_parametro', 'id_producto', 'id_linea', 'nombre', 'valor_objetivo', 'limite_inferior', 'limite_superior')
        list_filter = ('id_producto', 'id_linea', 'nombre')
        search_fields = ('nombre',)

    @admin.register(Medicion)
    class MedicionAdmin(ReadOnlyAdmin):
        list_display = ('id_medicion', 'fecha', 'id_linea', 'id_producto', 'promedio', 'th')
        list_filter = ('id_linea', 'id_producto', 'fecha')
        search_fields = ('orden', 'codigo')

    @admin.register(DefectoTipo)
    class DefectoTipoAdmin(ReadOnlyAdmin):
        list_display = ('id_defecto_tipo', 'nombre')
        search_fields = ('nombre',)

    @admin.register(Defecto)
    class DefectoAdmin(ReadOnlyAdmin):
        list_display = ('id_defecto', 'fecha', 'id_linea', 'id_producto', 'id_defecto_tipo', 'cantidad', 'lote', 'turno')
        list_filter = ('id_linea', 'id_producto', 'id_defecto_tipo', 'fecha', 'turno')
        search_fields = ('lote',)
else:
    # 2) Mostrar SOLO los modelos demo (si usas modo demo)
    @admin.register(ProductionBatch)
    class ProductionBatchAdmin(admin.ModelAdmin):
        list_display = ('code', 'product', 'line', 'start_time', 'end_time')

    @admin.register(Measurement)
    class MeasurementAdmin(admin.ModelAdmin):
        list_display = ('batch','timestamp','diameter_mm','thickness_mm','weight_g','speed_mpm','defects')
        list_filter = ('batch','timestamp')
