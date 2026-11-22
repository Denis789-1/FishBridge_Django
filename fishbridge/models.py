from django.db import models
from django.db.models import Q, F
from django.core.exceptions import ValidationError


class User(models.Model):
    class Role(models.TextChoices):
        GUEST = 'guest', 'Гость'
        ANGLER = 'angler', 'Рыболов'
        RANGER = 'ranger', 'Егерь'
        ICHTHYOLOGIST = 'ichthyologist', 'Ихтиолог'
        ADMIN = 'admin', 'Администратор'

    username = models.CharField('Логин', max_length=150, unique=True)
    password = models.CharField('Хеш пароля', max_length=128)
    email = models.EmailField('Электронная почта', max_length=254, unique=True)
    first_name = models.CharField('Имя', max_length=150, blank=True)
    last_name = models.CharField('Фамилия', max_length=150, blank=True)
    phone = models.CharField('Телефон', max_length=20, blank=True)
    role = models.CharField('Роль', max_length=20, choices=Role.choices, default=Role.ANGLER)
    is_active = models.BooleanField('Активен', default=True)
    date_joined = models.DateTimeField('Дата регистрации', auto_now_add=True)

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['last_name', 'first_name', 'username']
        constraints = [
            models.CheckConstraint(condition=~Q(username=''), name='user_username_not_empty'),
        ]

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()


class Pond(models.Model):
    name = models.CharField('Название', max_length=100, unique=True)
    description = models.TextField('Описание', blank=True)
    area = models.DecimalField('Площадь, га', max_digits=8, decimal_places=2, null=True, blank=True)
    depth = models.DecimalField('Глубина, м', max_digits=5, decimal_places=2, null=True, blank=True)
    address = models.CharField('Адрес', max_length=255)
    is_active = models.BooleanField('Действует', default=True)

    fish_species = models.ManyToManyField(
    'FishSpecies',
    through='StockingBatch',
    related_name='ponds',
    verbose_name='Виды рыб',
    blank=True
)

    class Meta:
        verbose_name = 'водоём'
        verbose_name_plural = 'Водоёмы'
        ordering = ['name']
        constraints = [
            models.CheckConstraint(condition=Q(area__isnull=True) | Q(area__gt=0), name='pond_area_positive'),
            models.CheckConstraint(condition=Q(depth__isnull=True) | Q(depth__gt=0), name='pond_depth_positive'),
        ]

    def __str__(self):
        return self.name


class Sector(models.Model):
    pond = models.ForeignKey(Pond, on_delete=models.PROTECT, related_name='sectors', verbose_name='Водоём')
    name = models.CharField('Название сектора', max_length=100)
    description = models.TextField('Описание', blank=True)
    capacity = models.PositiveSmallIntegerField('Вместимость')
    price = models.DecimalField('Стоимость, руб.', max_digits=10, decimal_places=2)
    is_active = models.BooleanField('Доступен', default=True)
    is_closed = models.BooleanField('Временно закрыт', default=False)
    closure_reason = models.CharField('Причина закрытия', max_length=255, blank=True)
    closed_until = models.DateTimeField('Закрыт до', null=True, blank=True)

    class Meta:
        verbose_name = 'рыболовный сектор'
        verbose_name_plural = 'Рыболовные секторы'
        ordering = ['pond__name', 'name']
        constraints = [
            models.UniqueConstraint(fields=['pond', 'name'], name='unique_sector_name_per_pond'),
            models.CheckConstraint(condition=Q(capacity__gt=0), name='sector_capacity_positive'),
            models.CheckConstraint(condition=Q(price__gte=0), name='sector_price_nonnegative'),
        ]

    def __str__(self):
        return f'{self.pond}: {self.name}'


class FishSpecies(models.Model):
    name = models.CharField('Название вида', max_length=100, unique=True)
    description = models.TextField('Описание', blank=True)
    average_weight = models.DecimalField('Средний вес, кг', max_digits=6, decimal_places=2, null=True, blank=True)
    over_limit_price_per_kg = models.DecimalField('Цена за кг сверх нормы, руб.', max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'вид рыбы'
        verbose_name_plural = 'Виды рыб'
        ordering = ['name']
        constraints = [
            models.CheckConstraint(condition=Q(average_weight__isnull=True) | Q(average_weight__gt=0), name='fish_average_weight_positive'),
            models.CheckConstraint(condition=Q(over_limit_price_per_kg__gte=0), name='fish_over_limit_price_nonnegative'),
        ]

    def __str__(self):
        return self.name


class StockingBatch(models.Model):
    pond = models.ForeignKey(Pond, on_delete=models.PROTECT, related_name='stocking_batches', verbose_name='Водоём')
    fish_species = models.ForeignKey(FishSpecies, on_delete=models.PROTECT, related_name='stocking_batches', verbose_name='Вид рыбы')
    quantity = models.PositiveIntegerField('Количество рыб')
    total_weight = models.DecimalField('Общий вес, кг', max_digits=10, decimal_places=2)
    stocking_date = models.DateField('Дата зарыбления')
    responsible = models.ForeignKey(User, on_delete=models.PROTECT, related_name='responsible_stocking_batches', verbose_name='Ответственный ихтиолог', limit_choices_to={'role': User.Role.ICHTHYOLOGIST})

    class Meta:
        verbose_name = 'партия зарыбления'
        verbose_name_plural = 'Партии зарыбления'
        ordering = ['-stocking_date', 'pond__name']
        constraints = [
            models.UniqueConstraint(fields=['pond', 'fish_species', 'stocking_date'], name='unique_stocking_per_pond_species_date'),
            models.CheckConstraint(condition=Q(quantity__gt=0), name='stocking_quantity_positive'),
            models.CheckConstraint(condition=Q(total_weight__gt=0), name='stocking_weight_positive'),
        ]

    def __str__(self):
        return f'{self.fish_species} — {self.pond} ({self.stocking_date})'


class Tariff(models.Model):
    name = models.CharField('Название тарифа', max_length=100, unique=True)
    description = models.TextField('Описание', blank=True)
    price = models.DecimalField('Стоимость, руб.', max_digits=10, decimal_places=2)
    duration_hours = models.PositiveSmallIntegerField('Продолжительность, часов')
    catch_limit = models.DecimalField('Норма вылова, кг', max_digits=6, decimal_places=2)
    is_active = models.BooleanField('Действует', default=True)

    class Meta:
        verbose_name = 'тариф'
        verbose_name_plural = 'Тарифы'
        ordering = ['price', 'name']
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name='tariff_price_nonnegative'),
            models.CheckConstraint(condition=Q(duration_hours__gt=0), name='tariff_duration_positive'),
            models.CheckConstraint(condition=Q(catch_limit__gte=0), name='tariff_catch_limit_nonnegative'),
        ]

    def __str__(self):
        return f'{self.name} — {self.price} руб.'


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает подтверждения'
        CONFIRMED = 'confirmed', 'Подтверждено'
        CANCELLED = 'cancelled', 'Отменено'
        COMPLETED = 'completed', 'Завершено'

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='bookings', verbose_name='Пользователь')
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name='bookings', verbose_name='Рыболовный сектор')
    tariff = models.ForeignKey(Tariff, on_delete=models.PROTECT, related_name='bookings', verbose_name='Тариф')
    start_datetime = models.DateTimeField('Начало бронирования')
    end_datetime = models.DateTimeField('Окончание бронирования')
    status = models.CharField('Статус', max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-start_datetime']
        indexes = [models.Index(fields=['sector', 'start_datetime', 'end_datetime'], name='booking_sector_dates_idx')]
        constraints = [
            models.CheckConstraint(condition=Q(end_datetime__gt=F('start_datetime')), name='booking_end_after_start'),
        ]

    def clean(self):
        super().clean()
        if self.sector_id and self.start_datetime and self.end_datetime and self.status != self.Status.CANCELLED:
            overlapping = Booking.objects.filter(
                sector_id=self.sector_id,
                status__in=[self.Status.PENDING, self.Status.CONFIRMED],
                start_datetime__lt=self.end_datetime,
                end_datetime__gt=self.start_datetime,
            ).exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError({'sector': 'На это время сектор уже забронирован.'})

    def __str__(self):
        return f'Бронь №{self.pk}: {self.sector}, {self.start_datetime:%d.%m.%Y %H:%M}'


class RentalItem(models.Model):
    name = models.CharField('Название оборудования', max_length=150, unique=True)
    description = models.TextField('Описание', blank=True)
    price_per_day = models.DecimalField('Цена за день, руб.', max_digits=10, decimal_places=2)
    quantity_available = models.PositiveIntegerField('Количество в наличии')
    is_active = models.BooleanField('Доступно', default=True)

    class Meta:
        verbose_name = 'позиция проката'
        verbose_name_plural = 'Позиции проката'
        ordering = ['name']
        constraints = [
            models.CheckConstraint(condition=Q(price_per_day__gte=0), name='rental_item_price_nonnegative'),
        ]

    def __str__(self):
        return self.name


class Rental(models.Model):
    class Status(models.TextChoices):
        RESERVED = 'reserved', 'Зарезервировано'
        ISSUED = 'issued', 'Выдано'
        RETURNED = 'returned', 'Возвращено'

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='rentals', verbose_name='Бронирование')
    rental_item = models.ForeignKey(RentalItem, on_delete=models.PROTECT, related_name='rentals', verbose_name='Позиция проката')
    quantity = models.PositiveSmallIntegerField('Количество')
    price_at_booking = models.DecimalField('Цена на момент бронирования, руб.', max_digits=10, decimal_places=2)
    status = models.CharField('Статус аренды', max_length=20, choices=Status.choices, default=Status.RESERVED)

    class Meta:
        verbose_name = 'аренда'
        verbose_name_plural = 'Аренда'
        ordering = ['booking_id', 'rental_item__name']
        constraints = [
            models.UniqueConstraint(fields=['booking', 'rental_item'], name='unique_rental_item_per_booking'),
            models.CheckConstraint(condition=Q(quantity__gt=0), name='rental_quantity_positive'),
            models.CheckConstraint(condition=Q(price_at_booking__gte=0), name='rental_price_nonnegative'),
        ]

    def __str__(self):
        return f'{self.rental_item} × {self.quantity} (бронь №{self.booking_id})'


class CatchRecord(models.Model):
    class TrophyDecision(models.TextChoices):
        RELEASE = 'release', 'Отпустить обратно в водоём'
        PAY_DOUBLE = 'pay_double', 'Оплатить по двойному тарифу'

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='catch_records', verbose_name='Бронирование')
    fish_species = models.ForeignKey(FishSpecies, on_delete=models.PROTECT, related_name='catch_records', verbose_name='Вид рыбы')
    ranger = models.ForeignKey(User, on_delete=models.PROTECT, related_name='recorded_catches', verbose_name='Егерь', limit_choices_to={'role': User.Role.RANGER})
    quantity = models.PositiveSmallIntegerField('Количество рыб')
    total_weight = models.DecimalField('Общий вес, кг', max_digits=8, decimal_places=2)
    trophy_weight = models.DecimalField('Вес трофейного экземпляра, кг', max_digits=8, decimal_places=2, default=0, blank=True)
    trophy_decision = models.CharField('Решение по трофейному экземпляру', max_length=20, choices=TrophyDecision.choices, blank=True)
    recorded_at = models.DateTimeField('Дата и время учёта', auto_now_add=True)
    comment = models.TextField('Комментарий', blank=True)

    class Meta:
        verbose_name = 'запись об улове'
        verbose_name_plural = 'Учёт улова'
        ordering = ['-recorded_at']
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name='catch_quantity_positive'),
            models.CheckConstraint(condition=Q(total_weight__gt=0), name='catch_weight_positive'),
            models.CheckConstraint(condition=Q(trophy_weight__gte=0), name='catch_trophy_weight_nonnegative'),
            models.CheckConstraint(condition=Q(trophy_weight__lte=F('total_weight')), name='catch_trophy_not_over_total'),
        ]

    def clean(self):
        super().clean()
        if self.trophy_weight and self.trophy_weight <= 5:
            raise ValidationError({'trophy_weight': 'Трофейным считается экземпляр весом строго более 5 кг.'})
        if self.trophy_weight and not self.trophy_decision:
            raise ValidationError({'trophy_decision': 'Выберите решение по трофейному экземпляру.'})
        if not self.trophy_weight and self.trophy_decision:
            raise ValidationError({'trophy_decision': 'Решение можно выбрать только для трофейного экземпляра.'})

    def __str__(self):
        return f'{self.fish_species}: {self.total_weight} кг (бронь №{self.booking_id})'


class ExtraPayment(models.Model):
    class Decision(models.TextChoices):
        NONE = 'none', 'Без трофейного решения'
        RELEASE = 'release', 'Трофейный экземпляр отпущен'
        PAY_DOUBLE = 'pay_double', 'Трофейный экземпляр оплачен по двойному тарифу'
        MIXED = 'mixed', 'Применены оба варианта'

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='extra_payment', verbose_name='Бронирование')
    catch_weight = models.DecimalField('Общий вес зарегистрированного улова, кг', max_digits=8, decimal_places=2)
    allowed_weight = models.DecimalField('Норма вылова по тарифу, кг', max_digits=8, decimal_places=2)
    billable_weight = models.DecimalField('Вес обычного улова, учитываемый в норме, кг', max_digits=8, decimal_places=2, default=0)
    released_weight = models.DecimalField('Вес отпущенных трофеев, кг', max_digits=8, decimal_places=2, default=0)
    excess_weight = models.DecimalField('Превышение нормы обычного улова, кг', max_digits=8, decimal_places=2)
    amount = models.DecimalField('Сумма доплаты, руб.', max_digits=10, decimal_places=2, default=0)
    decision = models.CharField('Решение по трофеям', max_length=20, choices=Decision.choices, default=Decision.NONE)
    details = models.JSONField('Расшифровка расчёта', default=dict, blank=True)
    calculated_at = models.DateTimeField('Дата расчёта', auto_now=True)
    is_paid = models.BooleanField('Оплачено', default=False)

    class Meta:
        verbose_name = 'доплата'
        verbose_name_plural = 'Доплаты'
        ordering = ['-calculated_at']
        constraints = [
            models.CheckConstraint(condition=Q(catch_weight__gte=0), name='extra_catch_weight_nonnegative'),
            models.CheckConstraint(condition=Q(allowed_weight__gte=0), name='extra_allowed_weight_nonnegative'),
            models.CheckConstraint(condition=Q(billable_weight__gte=0), name='extra_billable_weight_nonnegative'),
            models.CheckConstraint(condition=Q(released_weight__gte=0), name='extra_released_weight_nonnegative'),
            models.CheckConstraint(condition=Q(excess_weight__gte=0), name='extra_excess_weight_nonnegative'),
            models.CheckConstraint(condition=Q(amount__gte=0), name='extra_amount_nonnegative'),
        ]

    def __str__(self):
        return f'Доплата по брони №{self.booking_id}: {self.amount} руб.'

