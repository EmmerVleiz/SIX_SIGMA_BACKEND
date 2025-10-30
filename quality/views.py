from django.utils import timezone
from django.conf import settings
from django.db import transaction, connection
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from rest_framework import status

from .models import Medicion, Scrap, Defecto, IndicadorProceso, ParametroControl

def resolve_mode(request):
    qmode = (request.GET.get('mode') or '').strip().lower()
    if qmode == 'demo':
        return False
    if qmode == 'real':
        return True
    return str(getattr(settings, 'USE_EXT_SCHEMA', '0')) == '1'

# ====== servicios / demo ======
from .services import capability, xbar_r_groups, histogram_bins, pareto
from .models import Medicion, ParametroControl, Defecto, DefectoTipo, Measurement

FIELD_MAP_REAL = {
    'promedio':     'promedio',
    'thickness_mm': 'th',
    'weight_g':     None,
    'th':           'th',
}

import numpy as np
from .utils_demo import synth_series


class HealthView(APIView):
    def get(self, request):
        detected = str(getattr(settings, 'USE_EXT_SCHEMA', '0')) == '1'
        requested = resolve_mode(request)
        dbinfo = {}
        try:
            db = settings.DATABASES.get('default', {})
            dbinfo['engine'] = db.get('ENGINE')
            dbinfo['name']   = db.get('NAME')
            dbinfo['host']   = db.get('HOST')
            dbinfo['port']   = db.get('PORT')
            rows = Medicion.objects.count()
            last = Medicion.objects.order_by('-fecha').values('fecha').first()
            dbinfo['connected'] = True
            dbinfo['medicion_rows'] = rows
            dbinfo['medicion_last_fecha'] = (last['fecha'].isoformat() if last and last.get('fecha') else None)
        except Exception as e:
            dbinfo['connected'] = False
            dbinfo['error'] = str(e)

        return Response({
            'status': 'ok',
            'now': timezone.now(),
            'use_ext_schema_config': detected,
            'requested_mode': 'real' if requested else 'demo',
            'db': dbinfo
        })


class CapabilityView(APIView):
    def get(self, request):
        try:
            n = int(request.GET.get('n', '200'))
            dim = (request.GET.get('dimension') or 'diameter_mm').strip()
            use_ext = resolve_mode(request)
            lsl = request.GET.get('lsl'); usl = request.GET.get('usl')

            # NUEVO: filtros de fecha y de entidad
            fmin = request.GET.get('from')
            fmax = request.GET.get('to')
            prod = request.GET.get('producto')
            line = request.GET.get('linea')

            if use_ext:
                field = FIELD_MAP_REAL.get(dim)
                if not field:
                    return Response({'detail': f'Dimension {dim} no disponible en modo real'}, status=400)

                # Si no traen LSL/USL intenta leer de parametro_control cuando hay producto/linea
                if (lsl is None or usl is None) and prod and line:
                    pc = (ParametroControl.objects
                          .filter(id_producto=prod, id_linea=line,
                                  nombre__in=['Ciclo promedio (s)', 'Tubos por hora'])
                          .first())
                    if pc:
                        if lsl is None: lsl = str(pc.limite_inferior)
                        if usl is None: usl = str(pc.limite_superior)

                lsl = float(lsl) if lsl is not None else (30.0 if field == 'promedio' else 40.0)
                usl = float(usl) if usl is not None else (90.0 if field == 'promedio' else 80.0)

                # ====== AQUI EL CAMBIO IMPORTANTE: aplicar filtros ======
                qs = Medicion.objects.all()
                if prod:
                    qs = qs.filter(id_producto=prod)
                if line:
                    qs = qs.filter(id_linea=line)
                if fmin:
                    qs = qs.filter(fecha__gte=fmin)
                if fmax:
                    qs = qs.filter(fecha__lte=fmax)

                qs = qs.order_by('-fecha').values_list(field, flat=True)[:n]
                xs = [float(x) for x in qs if x is not None]
                # =========================================================
            else:
                lsl = float(lsl) if lsl is not None else (15.5 if dim == 'diameter_mm' else 2.0)
                usl = float(usl) if usl is not None else (16.5 if dim == 'diameter_mm' else 3.0)
                xs = synth_series(dim, n).tolist()

            if lsl >= usl:
                return Response({'detail': 'LSL debe ser < USL'}, status=400)

            # Si no hay suficientes datos, devolvemos 200 con KPIs nulos (para que el UI no se rompa)
            if len(xs) < 2:
                return Response({
                    'count': len(xs),
                    'dimension': dim,
                    'lsl': lsl,
                    'usl': usl,
                    'mu': None,
                    's_sample': None,
                    'cp': None,
                    'cpk': None,
                    'mode': 'real' if use_ext else 'demo',
                    'detail': 'insufficient_data'
                }, status=200)

            # Cálculo normal
            res = capability(xs, lsl, usl)
            res.update({
                'count': len(xs),
                'dimension': dim,
                'lsl': lsl,
                'usl': usl,
                'mode': 'real' if use_ext else 'demo'
            })
            return Response(res)


        except ValueError:
            return Response({'detail': 'Parámetros numéricos inválidos (lsl/usl/n)'}, status=400)
        except KeyError as e:
            return Response({'detail': str(e)}, status=400)
        except Exception as e:
            return Response({'detail': f'Error interno (capability): {e}'}, status=500)


class XBarRView(APIView):
    def get(self, request):
        try:
            n = int(request.GET.get('n', '200'))
            g = int(request.GET.get('group_size', '5'))
            dim = (request.GET.get('dimension') or 'diameter_mm').strip()
            use_ext = resolve_mode(request)

            if use_ext:
                field = FIELD_MAP_REAL.get(dim)
                if not field:
                    return Response({'detail': f'Dimension {dim} no disponible en modo real'}, status=400)

                # --- NUEVO: filtros por rango/ids ---
                prod = request.GET.get('producto')
                line = request.GET.get('linea')
                fmin = request.GET.get('from')
                fmax = request.GET.get('to')

                qs = Medicion.objects.all()
                if prod:
                    qs = qs.filter(id_producto=prod)
                if line:
                    qs = qs.filter(id_linea=line)
                if fmin:
                    qs = qs.filter(fecha__gte=fmin)
                if fmax:
                    qs = qs.filter(fecha__lte=fmax)

                qs = qs.order_by('fecha').values_list(field, flat=True)
                vals = [float(x) for x in qs if x is not None]
                if n and len(vals) > n:
                    vals = vals[-n:]
                xs = vals  # oldest -> newest
            else:
                xs = synth_series(dim, n).tolist()

            if len(xs) < g:
                return Response({'detail': 'Datos insuficientes para subagrupar'}, status=400)

            data = xbar_r_groups(xs, g)
            data.update({'dimension': dim, 'group_size': g, 'mode': 'real' if use_ext else 'demo'})
            return Response(data)
        except KeyError as e:
            return Response({'detail': str(e)}, status=400)
        except Exception as e:
            return Response({'detail': f'Error interno (xbar-r): {e}'}, status=500)


class HistogramView(APIView):
    def get(self, request):
        try:
            bins = int(request.GET.get('bins', '12'))
            n = int(request.GET.get('n', '500'))
            dim = (request.GET.get('dimension') or 'diameter_mm').strip()
            use_ext = resolve_mode(request)

            if use_ext:
                field = FIELD_MAP_REAL.get(dim)
                if not field:
                    return Response({'detail': f'Dimension {dim} no disponible en modo real'}, status=400)

                # --- NUEVO: filtros por rango/ids ---
                prod = request.GET.get('producto')
                line = request.GET.get('linea')
                fmin = request.GET.get('from')
                fmax = request.GET.get('to')

                qs = Medicion.objects.all()
                if prod:
                    qs = qs.filter(id_producto=prod)
                if line:
                    qs = qs.filter(id_linea=line)
                if fmin:
                    qs = qs.filter(fecha__gte=fmin)
                if fmax:
                    qs = qs.filter(fecha__lte=fmax)

                qs = qs.order_by('fecha').values_list(field, flat=True)
                vals = [float(x) for x in qs if x is not None]
                if n and len(vals) > n:
                    vals = vals[-n:]
                xs = np.array(vals, dtype=float)
            else:
                xs = synth_series(dim, n)

            if xs.size == 0:
                return Response({'detail': 'No hay datos para construir histograma'}, status=400)

            counts, edges = np.histogram(xs, bins=bins)
            centers = ((edges[:-1] + edges[1:]) / 2.0)

            return Response({
                'counts': counts.tolist(),
                'edges': edges.tolist(),
                'centers': centers.tolist(),
                'dimension': dim,
                'bins': bins,
                'count': int(xs.size),
                'mode': 'real' if use_ext else 'demo'
            })
        except KeyError as e:
            return Response({'detail': str(e)}, status=400)
        except Exception as e:
            return Response({'detail': f'Error interno (histogram): {e}'}, status=500)


class ParetoView(APIView):
    def get(self, request):
        try:
            use_ext = resolve_mode(request)
            if use_ext:
                fmin = request.GET.get('from'); fmax = request.GET.get('to')
                qs = Defecto.objects.all()
                if fmin: qs = qs.filter(fecha__gte=fmin)
                if fmax: qs = qs.filter(fecha__lte=fmax)
                agg = (qs.values('id_defecto_tipo')
                         .annotate(total=Sum('cantidad'))
                         .order_by('-total'))
                id_to_name = {t.id_defecto_tipo: t.nombre for t in DefectoTipo.objects.all()}
                buckets = {
                    id_to_name.get(row['id_defecto_tipo'], str(row['id_defecto_tipo'])): int(row['total'] or 0)
                    for row in agg
                }
                series = pareto(buckets)
                total_defects = sum(buckets.values())
                return Response({'series': series, 'total_defects': total_defects, 'mode': 'real'})

            # demo
            try:
                total_defects = Measurement.objects.aggregate(total=Sum('defects'))['total'] or 0
                if total_defects and total_defects > 0:
                    categories = ['Porosidad', 'Diámetro bajo', 'Diámetro alto', 'Ovalidad', 'Espesor bajo']
                    weights    = [0.40,        0.25,            0.15,           0.12,       0.08]
                    buckets = {name: int(total_defects * w) for name, w in zip(categories, weights)}
                else:
                    raise ValueError('sin datos en Measurement.defects')
            except Exception:
                buckets = {'Porosidad': 120, 'Diámetro bajo': 70, 'Diámetro alto': 45, 'Ovalidad': 36, 'Espesor bajo': 24}
            series = pareto(buckets)
            total_defects = sum(buckets.values())
            return Response({'series': series, 'total_defects': total_defects, 'mode': 'demo'})
        except Exception as e:
            return Response({'detail': f'Error interno (pareto): {e}'}, status=500)


class TargetsView(APIView):
    def get(self, request):
        use_ext = resolve_mode(request)
        prod = request.GET.get('producto'); line = request.GET.get('linea')
        result = {
            'promedio': {'target': 60.0, 'lsl': 30.0, 'usl': 90.0},
            'th':       {'target': 60.0, 'lsl': 40.0, 'usl': 80.0},
        }
        if not use_ext or not (prod and line):
            return Response({'mode': 'real' if use_ext else 'demo', 'data': result})
        pcs = ParametroControl.objects.filter(id_producto=prod, id_linea=line)
        for pc in pcs:
            name = (pc.nombre or '').strip().lower()
            if 'ciclo' in name and 'promedio' in name:
                result['promedio'] = {'target': float(pc.valor_objetivo), 'lsl': float(pc.limite_inferior), 'usl': float(pc.limite_superior)}
            elif 'tubo' in name and 'hora' in name:
                result['th'] = {'target': float(pc.valor_objetivo), 'lsl': float(pc.limite_inferior), 'usl': float(pc.limite_superior)}
        return Response({'mode': 'real', 'data': result})


class YieldTrendView(APIView):
    def get(self, request):
        use_ext = resolve_mode(request)
        if not use_ext:
            return Response({'trend': [], 'overall': {'overall_yield': 0, 'overall_sigma': None}})
        fmin = request.GET.get('from'); fmax = request.GET.get('to'); opp = int(request.GET.get('opp', '1'))
        qs = Scrap.objects.all().order_by('fecha').values('fecha', 'total_producido', 'total_defectuoso')
        if fmin: qs = qs.filter(fecha__gte=fmin)
        if fmax: qs = qs.filter(fecha__lte=fmax)
        rows = list(qs)
        from .services import aggregate_scrap
        payload = aggregate_scrap(rows, opportunities_per_unit=opp)
        return Response(payload)

class IndicatorsTrendView(APIView):
    def get(self, request):
        USE_EXT = str(getattr(settings, 'USE_EXT_SCHEMA', '0')) == '1'
        if not USE_EXT:
            return Response({'labels': [], 'cp': [], 'cpk': [], 'sigma': []})
        prod = request.GET.get('producto'); line = request.GET.get('linea')
        fmin = request.GET.get('from'); fmax = request.GET.get('to')
        qs = IndicadorProceso.objects.all()
        if prod: qs = qs.filter(id_producto=prod)
        if line: qs = qs.filter(id_linea=line)
        if fmin: qs = qs.filter(fecha__gte=fmin)
        if fmax: qs = qs.filter(fecha__lte=fmax)
        qs = qs.order_by('fecha').values('fecha','cp','cpk','sigma')
        labels = [r['fecha'].strftime('%Y-%m-%d') for r in qs]
        cp  = [float(r['cp'])    if r['cp']   is not None else None for r in qs]  # noqa: E201
        cpk = [float(r['cpk'])   if r['cpk']  is not None else None for r in qs]
        s   = [float(r['sigma']) if r['sigma'] is not None else None for r in qs]
        return Response({'labels': labels, 'cp': cp, 'cpk': cpk, 'sigma': s})

# =========================
# Helpers de mapeo robusto
# =========================

def _allowed_keys(Model):
    keys = set()
    for f in Model._meta.get_fields():
        att = getattr(f, 'attname', None)
        name = getattr(f, 'name', None)
        if att: keys.add(att)    # 'producto_id', 'linea_id'
        if name: keys.add(name)  # 'producto', 'linea', 'id_producto', 'id_linea'
    return keys

def _choose_key(allowed: set, candidates):
    for c in candidates:
        if c in allowed:
            return c
    return None

def _prod_line_kwargs(Model, id_producto: int, id_linea: int) -> dict:
    """
    Si el modelo no tiene esos fields, devuelve {} (no levanta excepción).
    """
    allowed = _allowed_keys(Model)
    k_prod = _choose_key(allowed, ['id_producto', 'producto_id', 'producto'])
    k_line = _choose_key(allowed, ['id_linea', 'linea_id', 'linea'])
    kw = {}
    if k_prod is not None: kw[k_prod] = id_producto
    if k_line is not None: kw[k_line] = id_linea
    return kw

# --- introspección de columnas reales en SQL Server ---
def _table_has_column(db_table: str, column_name: str) -> bool:
    # db_table puede venir como 'dbo.scrap' o 'scrap'
    parts = db_table.split('.')
    if len(parts) == 2:
        schema, table = parts[0], parts[1]
    else:
        schema, table = 'dbo', parts[0]   # asumimos dbo si no se especifica
    with connection.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
            [schema, table, column_name]
        )
        return cur.fetchone() is not None

def _raw_insert_scrap(fecha, id_producto, id_linea, total_prod, total_def):
    """
    Inserta en tabla scrap con SQL crudo incluyendo sólo las columnas que EXISTEN.
    Evita errores de NULL en id_linea/id_producto cuando el modelo no las expone.
    """
    db_table = Scrap._meta.db_table  # normalmente 'scrap' (en SQL Server = dbo.scrap)
    cols = ['fecha', 'total_producido', 'total_defectuoso']
    params = [fecha, int(total_prod), int(total_def)]

    if _table_has_column(db_table, 'id_producto'):
        cols.append('id_producto'); params.append(int(id_producto))
    if _table_has_column(db_table, 'id_linea'):
        cols.append('id_linea'); params.append(int(id_linea))

    qn = connection.ops.quote_name
    table_sql = '.'.join(qn(p) for p in db_table.split('.'))  # dbo.scrap -> [dbo].[scrap]
    cols_sql  = ', '.join(qn(c) for c in cols)
    placeholders = ', '.join(['%s'] * len(cols))  # mssql-django usa %s

    with connection.cursor() as cur:
        cur.execute(f"INSERT INTO {table_sql} ({cols_sql}) VALUES ({placeholders})", params)

# =========================
# Ingreso de Producción
# =========================

class IngresoProduccionView(APIView):
    def post(self, request):
        data = request.data
        req = ['fecha', 'id_producto', 'id_linea']
        for k in req:
            if k not in data:
                return Response({"detail": f"Falta campo requerido: {k}"}, status=400)

        fecha = data['fecha']
        id_producto = int(data['id_producto'])
        id_linea = int(data['id_linea'])
        dimension = data.get('dimension', 'promedio')   # 'promedio' | 'th'
        muestras = data.get('muestras', [])
        total_producido  = data.get('total_producido')
        total_defectuoso = data.get('total_defectuoso')
        defectos = data.get('defectos', [])

        if dimension not in ('promedio', 'th'):
            return Response({"detail":"dimension debe ser 'promedio' o 'th'."}, status=400)

        try:
            with transaction.atomic():
                # 1) medicion: guardar según estructura real de la tabla
                created_med = 0
                orden = 1

                def _add_prod_line(Model, base):
                    base.update(_prod_line_kwargs(Model, id_producto, id_linea))
                    return base

                allowed_med = _allowed_keys(Medicion)   # lo que REALMENTE tiene el modelo

                if dimension == 'promedio':
                    # tomas ingresadas en el modal
                    vals = [float(x) for x in (muestras or []) if x is not None and str(x) != ""]
                    # empaquetar en grupos de hasta 4 (t1..t4)
                    for i in range(0, len(vals), 4):
                        chunk = vals[i:i+4]  # tamaño 1..4
                        base = {'fecha': fecha, 'orden': orden}

                        # mapear t1..t4 si el modelo los tiene
                        for idx, f in enumerate(['t1','t2','t3','t4']):
                            if f in allowed_med:
                                base[f] = float(chunk[idx]) if idx < len(chunk) else None

                        # promedio del chunk
                        if 'promedio' in allowed_med and len(chunk) > 0:
                            base['promedio'] = sum(chunk)/len(chunk)

                        # codigo opcional
                        if 'codigo' in allowed_med:
                            base['codigo'] = f'P{int(id_producto):03d}'

                        _add_prod_line(Medicion, base)
                        Medicion.objects.create(**base)
                        created_med += 1
                        orden += 1

                else:  # dimension == 'th'
                    for v in (muestras or []):
                        if v is None or str(v) == "": 
                            continue
                        base = {'fecha': fecha, 'orden': orden}
                        if 'th' in allowed_med:
                            base['th'] = float(v)
                        if 'codigo' in allowed_med:
                            base['codigo'] = f'P{int(id_producto):03d}'
                        _add_prod_line(Medicion, base)
                        Medicion.objects.create(**base)
                        created_med += 1
                        orden += 1


                # 2) scrap (si hay totales)
                created_scrap = False
                if total_producido is not None and total_defectuoso is not None:
                    # Si el modelo NO expone producto/línea, hacemos INSERT crudo con columnas reales.
                    allow = _allowed_keys(Scrap)
                    has_any_prod_line = any(k in allow for k in ('id_producto','producto_id','producto',
                                                                 'id_linea','linea_id','linea'))
                    if has_any_prod_line:
                        base = dict(fecha=fecha,
                                    total_producido=int(total_producido),
                                    total_defectuoso=int(total_defectuoso))
                        base.update(_prod_line_kwargs(Scrap, id_producto, id_linea))
                        Scrap.objects.create(**base)
                    else:
                        _raw_insert_scrap(fecha, id_producto, id_linea,
                                          total_producido, total_defectuoso)
                    created_scrap = True

                # 3) defectos
                created_def = 0
                allowed_def = _allowed_keys(Defecto)
                k_def = _choose_key(allowed_def, ['defecto_tipo_id', 'id_defecto_tipo', 'defecto_tipo'])
                for d in (defectos or []):
                    base = dict(fecha=fecha,
                                cantidad=int(d.get('cantidad', 0)),
                                lote=d.get('lote'))
                    if k_def:
                        base[k_def] = int(d['id_defecto_tipo'])
                    base.update(_prod_line_kwargs(Defecto, id_producto, id_linea))
                    Defecto.objects.create(**base)
                    created_def += 1

                # 4) indicador_proceso: cp/cpk/sigma del día si hay LSL/USL
                created_ind = False
                if muestras:
                    pc_name = 'Ciclo promedio (s)' if dimension == 'promedio' else 'Tubos por hora'
                    pc = ParametroControl.objects.filter(
                        id_producto=id_producto, id_linea=id_linea, nombre=pc_name
                    ).values('limite_inferior','limite_superior').first()

                    if pc:
                        lsl = float(pc['limite_inferior']); usl = float(pc['limite_superior'])
                        mu, s = _mean_std_local([float(x) for x in muestras])
                        if s > 0:
                            cp  = (usl - lsl) / (6.0 * s)
                            cpk = min((usl - mu)/(3.0*s), (mu - lsl)/(3.0*s))
                            sigma = (3.0 * cpk) + 1.5
                        else:
                            cp = cpk = sigma = 0.0

                        # Incluir SOLO keys existentes en el modelo real:
                        allowed_ind = _allowed_keys(IndicadorProceso)  # {'fecha','cp','cpk','sigma', ...}
                        base = {}

                        if 'fecha' in allowed_ind:
                            base['fecha'] = fecha
                        if 'cp' in allowed_ind:
                            base['cp'] = cp
                        if 'cpk' in allowed_ind:
                            base['cpk'] = cpk
                        if 'sigma' in allowed_ind:
                            base['sigma'] = sigma
                        # comentarios es opcional y muchas veces NO existe:
                        if 'comentarios' in allowed_ind:
                            base['comentarios'] = f'auto:{dimension}'

                        # Agrega id_producto / id_linea SOLO si esos fields existen en el modelo:
                        base.update(_prod_line_kwargs(IndicadorProceso, id_producto, id_linea))

                        # Solo intentamos crear si al menos hay 'fecha' y alguno de los KPIs:
                        if 'fecha' in base and any(k in base for k in ('cp','cpk','sigma')):
                            IndicadorProceso.objects.create(**base)
                            created_ind = True
                        else:
                            # No hay columnas suficientes en la tabla; lo omitimos sin romper.
                            created_ind = False

            return Response({"ok": True, "created":{
                "medicion": created_med, "scrap": created_scrap,
                "defecto": created_def, "indicador": created_ind
            }}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"ok": False, "error": str(e)}, status=500)


def _mean_std_local(vals):
    n = len(vals)
    if n == 0: return 0.0, 0.0
    mu = sum(vals)/n
    if n == 1: return mu, 0.0
    var = sum((x-mu)**2 for x in vals)/(n-1)
    return mu, var**0.5

# ====== CRUD de revisión/edición ======

class ProductionListView(APIView):
    """
    GET /api/ingreso/produccion/list/?fecha=YYYY-MM-DD&producto=1&linea=1
    Devuelve: { medicion: [...], scrap:[...], defecto:[...] }
    """
    def get(self, request):
        fecha = request.GET.get('fecha')
        prod  = request.GET.get('producto')
        line  = request.GET.get('linea')
        if not (fecha and prod and line):
            return Response({"detail":"fecha, producto y linea son obligatorios"}, status=400)

        med = (Medicion.objects
               .filter(fecha=fecha, id_producto=prod, id_linea=line)
               .values('id_medicion','fecha','id_linea','id_producto','orden',
                       'codigo','t1','t2','t3','t4','promedio','th')
               .order_by('orden','id_medicion'))

        sc = []
        # scrap puede o no tener ids de línea/producto según tu mapeo; usamos filtros flexibles
        qs_scrap = Scrap.objects.filter(fecha=fecha)
        if 'id_producto' in [f.name for f in Scrap._meta.fields]:
            qs_scrap = qs_scrap.filter(id_producto=prod)
        if 'id_linea' in [f.name for f in Scrap._meta.fields]:
            qs_scrap = qs_scrap.filter(id_linea=line)
        sc = list(qs_scrap.values())

        de = (Defecto.objects
              .filter(fecha=fecha, id_producto=prod, id_linea=line)
              .values('id_defecto','fecha','id_linea','id_producto',
                      'id_defecto_tipo','cantidad','lote','turno')
              .order_by('id_defecto'))

        return Response({
            "medicion": list(med),
            "scrap": sc,
            "defecto": list(de)
        })


class MedicionDetailView(APIView):
    """
    PUT /api/medicion/<id>/
    DELETE /api/medicion/<id>/
    """
    def put(self, request, pk):
        try:
            obj = Medicion.objects.get(pk=pk)
        except Medicion.DoesNotExist:
            return Response({"detail":"no existe"}, status=404)

        data = request.data or {}
        # solo campos permitidos
        allow = {'t1','t2','t3','t4','promedio','th','orden','codigo'}
        for k in list(data.keys()):
            if k not in allow:
                data.pop(k)

        for k,v in data.items():
            setattr(obj, k, (None if v in ("", None) else float(v) if k in ('t1','t2','t3','t4','promedio','th') else v))
        obj.save()
        return Response({"ok": True})

    def delete(self, request, pk):
        try:
            Medicion.objects.filter(pk=pk).delete()
            return Response(status=204)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


class ScrapDetailView(APIView):
    """
    PUT /api/scrap/<id>/
    DELETE /api/scrap/<id>/
    """
    def put(self, request, pk):
        try:
            obj = Scrap.objects.get(pk=pk)
        except Scrap.DoesNotExist:
            return Response({"detail":"no existe"}, status=404)

        for k in ('total_producido','total_defectuoso'):
            if k in request.data:
                val = request.data[k]
                setattr(obj, k, None if val in ("", None) else int(val))
        obj.save()
        return Response({"ok": True})

    def delete(self, request, pk):
        try:
            Scrap.objects.filter(pk=pk).delete()
            return Response(status=204)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


class DefectoDetailView(APIView):
    """
    PUT /api/defecto/<id>/
    DELETE /api/defecto/<id>/
    """
    def put(self, request, pk):
        try:
            obj = Defecto.objects.get(pk=pk)
        except Defecto.DoesNotExist:
            return Response({"detail":"no existe"}, status=404)

        for k in ('id_defecto_tipo','cantidad','lote','turno'):
            if k in request.data:
                val = request.data[k]
                if k in ('id_defecto_tipo','cantidad'):
                    val = None if val in ("", None) else int(val)
                obj.__setattr__(k, val)
        obj.save()
        return Response({"ok": True})

    def delete(self, request, pk):
        try:
            Defecto.objects.filter(pk=pk).delete()
            return Response(status=204)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)
