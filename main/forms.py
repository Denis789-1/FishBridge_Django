from django import forms
from django.utils import timezone
from fishbridge.models import Booking, Sector, Tariff


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['sector', 'tariff', 'start_datetime']
        widgets = {
            'sector': forms.Select(attrs={'id': 'sector', 'required': True}),
            'tariff': forms.Select(attrs={'id': 'tariff', 'required': True}),
            'start_datetime': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'id': 'start_datetime', 'required': True},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sector'].queryset = Sector.objects.filter(is_active=True).select_related('pond')
        self.fields['tariff'].queryset = Tariff.objects.filter(is_active=True)
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
        if sector and not sector.is_active:
            self.add_error('sector', 'Этот сектор сейчас недоступен.')
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
