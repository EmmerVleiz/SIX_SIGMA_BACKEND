from rest_framework import serializers
from .models import Measurement, ProductionBatch

class MeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = ['id','batch','timestamp','diameter_mm','thickness_mm','weight_g','speed_mpm','defects']

class ProductionBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionBatch
        fields = ['id','code','start_time','end_time','product','line','notes']
