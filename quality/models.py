from django.db import models

class ProductionBatch(models.Model):
    code = models.CharField(max_length=50, unique=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    product = models.CharField(max_length=100, default='Tubo PVC 1/2" SDR 315 PSI')
    line = models.CharField(max_length=30, default='Línea #3')
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.code} ({self.product})"

class Measurement(models.Model):
    batch = models.ForeignKey(ProductionBatch, on_delete=models.CASCADE, related_name='measurements')
    timestamp = models.DateTimeField()
    diameter_mm = models.FloatField(help_text="Diámetro exterior (mm)")
    thickness_mm = models.FloatField(help_text="Espesor (mm)")
    weight_g = models.FloatField(help_text="Peso (g)")
    speed_mpm = models.FloatField(help_text="Velocidad (m/min)")
    defects = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['batch', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.batch.code} @ {self.timestamp:%Y-%m-%d %H:%M}"

# === MODELOS UNMANAGED PARA LA BD EXTERNA ===
from django.db import models

class LineaProduccion(models.Model):
    id_linea = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=255, null=True)
    class Meta:
        managed = False
        db_table = 'linea_produccion'

class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    dimension = models.CharField(max_length=50, null=True)
    sdr = models.CharField(max_length=20, null=True)
    descripcion = models.CharField(max_length=255, null=True)
    class Meta:
        managed = False
        db_table = 'producto'

class ParametroControl(models.Model):
    id_parametro = models.AutoField(primary_key=True)
    id_producto = models.IntegerField()
    id_linea = models.IntegerField()
    nombre = models.CharField(max_length=100)
    valor_objetivo = models.FloatField()
    limite_superior = models.FloatField()
    limite_inferior = models.FloatField()
    class Meta:
        managed = False
        db_table = 'parametro_control'

class Medicion(models.Model):
    id_medicion = models.AutoField(primary_key=True)
    fecha = models.DateField()
    id_linea = models.IntegerField()
    id_producto = models.IntegerField()
    orden = models.CharField(max_length=50, null=True)
    codigo = models.CharField(max_length=50, null=True)
    t1 = models.FloatField(null=True)
    t2 = models.FloatField(null=True)
    t3 = models.FloatField(null=True)
    t4 = models.FloatField(null=True)
    promedio = models.FloatField(null=True)  # "ciclo promedio (s)" en tu script
    th = models.FloatField(null=True)        # "tubos por hora"
    class Meta:
        managed = False
        db_table = 'medicion'

class DefectoTipo(models.Model):
    id_defecto_tipo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255, null=True)
    class Meta:
        managed = False
        db_table = 'defecto_tipo'

class Defecto(models.Model):
    id_defecto = models.AutoField(primary_key=True)
    fecha = models.DateField()
    id_linea = models.IntegerField()
    id_producto = models.IntegerField()
    id_defecto_tipo = models.IntegerField()
    cantidad = models.IntegerField()
    lote = models.CharField(max_length=50, null=True)
    turno = models.CharField(max_length=50, null=True)
    class Meta:
        managed = False
        db_table = 'defecto'


# === MODELOS UNMANAGED ADICIONALES ===
from django.db import models

class Scrap(models.Model):
    id_scrap = models.AutoField(primary_key=True, db_column='id_scrap')
    fecha = models.DateField(db_column='fecha')
    # ⇩⇩⇩ Agrega estos dos si existen en la tabla real ⇩⇩⇩
    id_linea = models.IntegerField(db_column='id_linea')        # <- requerido por tu SQL
    id_producto = models.IntegerField(db_column='id_producto')  # <- requerido por tu SQL
    # ⇧⇧⇧
    total_producido = models.IntegerField(db_column='total_producido', null=True)
    total_defectuoso = models.IntegerField(db_column='total_defectuoso', null=True)

    class Meta:
        managed = False
        db_table = 'scrap'


class IndicadorProceso(models.Model):
    # Tabla: indicador_proceso  (tendencia de capacidad)
    id_indicador = models.AutoField(primary_key=True)
    fecha = models.DateField()
    id_producto = models.IntegerField()
    id_linea = models.IntegerField()
    cp = models.FloatField(null=True)
    cpk = models.FloatField(null=True)
    sigma = models.FloatField(null=True)

    class Meta:
        managed = False
        db_table = 'indicador_proceso'
