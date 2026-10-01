from django.db import models


class FuelStation(models.Model):
    opis_id = models.PositiveIntegerField(
        unique=True,
        db_index=True,
    )
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=150)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.PositiveIntegerField()

    latitude = models.FloatField(
        null=True,
        blank=True,
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["opis_id"]

    def __str__(self) -> str:
        return f"{self.name} ({self.city}, {self.state})"


class FuelPrice(models.Model):
    station = models.ForeignKey(
        FuelStation,
        on_delete=models.CASCADE,
        related_name="prices",
    )
    retail_price = models.DecimalField(
        max_digits=10,
        decimal_places=8,
    )

    class Meta:
        indexes = [
            models.Index(fields=["station", "retail_price"]),
        ]

    def __str__(self) -> str:
        return f"{self.station.opis_id}: ${self.retail_price}"