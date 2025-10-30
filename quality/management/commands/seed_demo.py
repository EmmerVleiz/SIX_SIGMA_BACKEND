from django.core.management.base import BaseCommand
from django.utils import timezone
from quality.models import ProductionBatch, Measurement
import random
from datetime import timedelta


class Command(BaseCommand):
    help = "Crea datos de demostración para el dashboard Six Sigma"

    def handle(self, *args, **kwargs):
        # Limpia datos previos
        Measurement.objects.all().delete()
        ProductionBatch.objects.all().delete()

        now = timezone.now()
        batch = ProductionBatch.objects.create(
            code="BATCH-" + now.strftime("%Y%m%d%H%M"),
            start_time=now - timedelta(hours=8),
            end_time=now,
            product='Tubo PVC 1/2" SDR 315 PSI',
            line='Línea #3'
        )

        # Parámetros de simulación
        mu_d, sigma_d = 16.0, 0.12
        mu_t, sigma_t = 2.5, 0.09
        mu_w, sigma_w = 120.0, 4.0

        ts = now - timedelta(hours=8)
        for _ in range(500):
            ts += timedelta(minutes=1)
            Measurement.objects.create(
                batch=batch,
                timestamp=ts,
                diameter_mm=random.gauss(mu_d, sigma_d),
                thickness_mm=random.gauss(mu_t, sigma_t),
                weight_g=max(0.0, random.gauss(mu_w, sigma_w)),
                speed_mpm=max(0.0, random.gauss(10, 1.2)),
                defects=0 if random.random() > 0.06 else random.randint(1, 3)
            )

        self.stdout.write(self.style.SUCCESS("Datos de demostración creados."))
