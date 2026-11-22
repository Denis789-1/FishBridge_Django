
from django.contrib import admin
from .models import (
    User, Pond, Sector, FishSpecies, StockingBatch,
    Tariff, Booking, RentalItem, Rental,
    CatchRecord, ExtraPayment
)

admin.site.register(User)
admin.site.register(Pond)
@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'pond', 'is_active', 'is_closed', 'closed_until')
    list_filter = ('pond', 'is_active', 'is_closed')
    search_fields = ('name', 'pond__name', 'closure_reason')

@admin.register(FishSpecies)
class FishSpeciesAdmin(admin.ModelAdmin):
    list_display = ('name', 'average_weight', 'over_limit_price_per_kg')
    search_fields = ('name',)

admin.site.register(StockingBatch)
admin.site.register(Tariff)
admin.site.register(Booking)
admin.site.register(RentalItem)
admin.site.register(Rental)
@admin.register(CatchRecord)
class CatchRecordAdmin(admin.ModelAdmin):
    list_display = ('booking', 'fish_species', 'quantity', 'total_weight', 'trophy_weight', 'trophy_decision', 'ranger')
    list_filter = ('fish_species', 'trophy_decision', 'recorded_at')
    search_fields = ('booking__user__username', 'fish_species__name')

@admin.register(ExtraPayment)
class ExtraPaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'catch_weight', 'allowed_weight', 'excess_weight', 'amount', 'decision', 'is_paid', 'calculated_at')
    list_filter = ('decision', 'is_paid', 'calculated_at')
    search_fields = ('booking__user__username',)
