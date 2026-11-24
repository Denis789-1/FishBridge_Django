from decimal import Decimal
from django import forms
from django.utils import timezone
from django.db.models import Q
from fishbridge.models import Booking, Sector, Tariff, Pond, RentalItem, CatchRecord, Rental


class SectorSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value:
            sector = getattr(value, 'instance', None)
            if sector is not None:
                option['attrs']['data-pond'] = str(sector.pond_id)
        return option


class BookingForm(forms.ModelForm):
    pond = forms.ModelChoiceField(
        label='Водоём',
        queryset=Pond.objects.filter(is_active=True),
        required=False,
        empty_label='Все водоёмы',
    )

    class Meta:
        model = Booking
        fields = ['sector', 'tariff', 'start_datetime']
        widgets = {
            'sector': SectorSelect(attrs={'id': 'sector', 'required': True}),
            'tariff': forms.Select(attrs={'id': 'tariff', 'required': True}),
            'start_datetime': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'id': 'start_datetime', 'required': True},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pond'].queryset = Pond.objects.filter(is_active=True)
        self.fields['sector'].queryset = Sector.objects.filter(is_active=True).filter(
            Q(is_closed=False) | Q(closed_until__lte=timezone.now())
        ).select_related('pond')
        self.fields['tariff'].queryset = Tariff.objects.filter(is_active=True)
        pond_id = self.data.get('pond') or self.initial.get('pond')
        if pond_id:
            self.fields['sector'].queryset = self.fields['sector'].queryset.filter(pond_id=pond_id)
        self.fields['sector'].empty_label = 'Выберите сектор'
        self.fields['tariff'].empty_label = 'Выберите тариф'
        self.fields['start_datetime'].input_formats = ['%Y-%m-%dT%H:%M']

    def clean_start_datetime(self):
        value = self.cleaned_data['start_datetime']
        if value <= timezone.now():
            raise forms.ValidationError('Дата и время должны быть в будущем.')
        return value

    def clean(self):
        cleaned = super().clean()
        sector = cleaned.get('sector')
        tariff = cleaned.get('tariff')
        start = cleaned.get('start_datetime')
        pond = cleaned.get('pond')
        if pond and sector and sector.pond_id != pond.pk:
            self.add_error('sector', 'Выберите сектор выбранного водоёма.')
        if sector and not sector.is_active:
            self.add_error('sector', 'Этот сектор сейчас недоступен.')
        if sector and sector.is_closed and (sector.closed_until is None or sector.closed_until > timezone.now()):
            self.add_error('sector', sector.closure_reason or 'Этот сектор временно закрыт.')
        if tariff and not tariff.is_active:
            self.add_error('tariff', 'Этот тариф сейчас недоступен.')
        if sector and tariff and start:
            from datetime import timedelta
            end = start + timedelta(hours=tariff.duration_hours)
            conflict = Booking.objects.filter(
                sector=sector,
                status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
                start_datetime__lt=end,
                end_datetime__gt=start,
            ).exists()
            if conflict:
                self.add_error('sector', 'На это время сектор уже забронирован.')
        return cleaned


class RentalForm(forms.ModelForm):
    class Meta:
        model = Rental
        fields = ['rental_item', 'quantity']
        labels = {
            'rental_item': 'Оборудование',
            'quantity': 'Количество',
        }
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': '1', 'step': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rental_item'].queryset = RentalItem.objects.filter(is_active=True)

    def clean_quantity(self):
        value = self.cleaned_data['quantity']
        if value < 1:
            raise forms.ValidationError('Количество должно быть не меньше 1.')
        return value


class CatchRecordForm(forms.ModelForm):
    class Meta:
        model = CatchRecord
        fields = ['booking', 'fish_species', 'quantity', 'total_weight', 'trophy_weight', 'trophy_decision', 'comment']
        labels = {
            'booking': 'Бронирование',
            'fish_species': 'Вид рыбы',
            'quantity': 'Количество рыб',
            'total_weight': 'Общий вес, кг',
            'trophy_weight': 'Вес трофейного экземпляра, кг',
            'trophy_decision': 'Решение по трофейному экземпляру',
            'comment': 'Комментарий',
        }
        widgets = {
            'total_weight': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'quantity': forms.NumberInput(attrs={'min': '1', 'step': '1'}),
            'trophy_weight': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
        }
        help_texts = {
            'trophy_weight': 'Укажите вес одного экземпляра тяжелее 5 кг. Если трофейных рыб несколько, добавьте отдельную запись для каждой.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['booking'].queryset = Booking.objects.filter(
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
            start_datetime__lte=timezone.now(),
        ).select_related('user', 'sector__pond', 'tariff')
        self.fields['trophy_weight'].required = False
        self.fields['trophy_weight'].initial = 0
        self.fields['trophy_decision'].required = False

    def clean_quantity(self):
        value = self.cleaned_data['quantity']
        if value < 1:
            raise forms.ValidationError('Количество рыб должно быть не меньше 1.')
        return value

    def clean_trophy_weight(self):
        return self.cleaned_data.get('trophy_weight') or Decimal('0.00')

    def clean_total_weight(self):
        value = self.cleaned_data['total_weight']
        if value <= 0:
            raise forms.ValidationError('Вес должен быть больше нуля.')
        return value

    def clean(self):
        cleaned = super().clean()
        trophy_weight = cleaned.get('trophy_weight') or 0
        total_weight = cleaned.get('total_weight')
        decision = cleaned.get('trophy_decision')
        if trophy_weight:
            if trophy_weight <= 5:
                self.add_error('trophy_weight', 'Трофейным считается экземпляр весом строго более 5 кг.')
            if total_weight and trophy_weight > total_weight:
                self.add_error('trophy_weight', 'Вес трофейного экземпляра не может превышать общий вес улова.')
            if not decision:
                self.add_error('trophy_decision', 'Выберите: отпустить трофей или оплатить по двойному тарифу.')
        elif decision:
            self.add_error('trophy_decision', 'Сначала укажите вес трофейного экземпляра.')
        return cleaned


class CloseVisitForm(forms.Form):
    booking = forms.ModelChoiceField(
        label='Бронирование для закрытия визита',
        queryset=Booking.objects.none(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['booking'].queryset = Booking.objects.filter(
            catch_records__isnull=False,
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
            start_datetime__lte=timezone.now(),
        ).select_related(
            'user', 'tariff', 'sector__pond'
        ).distinct()
        self.fields['booking'].label_from_instance = lambda booking: (
            f'Бронь №{booking.pk} — {booking.user.username} — {booking.sector} — '
            f'{booking.start_datetime:%d.%m.%Y %H:%M}'
        )
