from django.urls import path
from .views import CapabilityView, XBarRView, HistogramView, ParetoView, HealthView
from .views import (
    ProductionListView, MedicionDetailView, ScrapDetailView, DefectoDetailView
)


urlpatterns = [
    path('health/', HealthView.as_view(), name='health'),
    path('metrics/capability/', CapabilityView.as_view(), name='capability'),
    path('charts/xbar-r/', XBarRView.as_view(), name='xbar_r'),
    path('charts/histogram/', HistogramView.as_view(), name='histogram'),
    path('charts/pareto/', ParetoView.as_view(), name='pareto'),
]

urlpatterns += [
    path('ingreso/produccion/list/', ProductionListView.as_view()),
    path('medicion/<int:pk>/', MedicionDetailView.as_view()),
    path('scrap/<int:pk>/', ScrapDetailView.as_view()),
    path('defecto/<int:pk>/', DefectoDetailView.as_view()),
]