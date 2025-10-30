from django.contrib import admin
from django.urls import path, include
from quality.views import IngresoProduccionView

# Si ya los usas, mantenlos
from quality.views import TargetsView, YieldTrendView, IndicatorsTrendView

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- NUEVO: rutas de seguridad ---
      path('api/seguridad/', include('seguridad.urls')),
      
    path('api/ingreso/produccion/', IngresoProduccionView.as_view()),


    # --- tus rutas existentes ---
    path('api/', include('quality.urls')),
    path('api/targets/', TargetsView.as_view()),
    path('api/yield/trend/', YieldTrendView.as_view()),
    path('api/indicators/trend/', IndicatorsTrendView.as_view()),
    
]
