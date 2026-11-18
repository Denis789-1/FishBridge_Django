
from django.contrib import admin
from .models import (
    User, Pond, Sector, FishSpecies, StockingBatch,
    Tariff, Booking, RentalItem, Rental,
    CatchRecord, ExtraPayment
)

admin.site.register(User)
admin.site.register(Pond)
admin.site.register(Sector)
admin.site.register(FishSpecies)
admin.site.register(StockingBatch)
admin.site.register(Tariff)
admin.site.register(Booking)
admin.site.register(RentalItem)
admin.site.register(Rental)
admin.site.register(CatchRecord)
admin.site.register(ExtraPayment)
