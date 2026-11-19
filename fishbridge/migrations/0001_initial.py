                                                                            
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q, F


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='FishSpecies',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('name', models.CharField(max_length=100, unique=True, verbose_name='Название вида')), ('description', models.TextField(blank=True, verbose_name='Описание')), ('average_weight', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name='Средний вес, кг'))],
            options={'verbose_name': 'вид рыбы', 'verbose_name_plural': 'Виды рыб', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Pond',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('name', models.CharField(max_length=100, unique=True, verbose_name='Название')), ('description', models.TextField(blank=True, verbose_name='Описание')), ('area', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='Площадь, га')), ('depth', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='Глубина, м')), ('address', models.CharField(max_length=255, verbose_name='Адрес')), ('is_active', models.BooleanField(default=True, verbose_name='Действует'))],
            options={'verbose_name': 'водоём', 'verbose_name_plural': 'Водоёмы', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='RentalItem',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('name', models.CharField(max_length=150, unique=True, verbose_name='Название оборудования')), ('description', models.TextField(blank=True, verbose_name='Описание')), ('price_per_day', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Цена за день, руб.')), ('quantity_available', models.PositiveIntegerField(verbose_name='Количество в наличии')), ('is_active', models.BooleanField(default=True, verbose_name='Доступно'))],
            options={'verbose_name': 'позиция проката', 'verbose_name_plural': 'Позиции проката', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Tariff',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('name', models.CharField(max_length=100, unique=True, verbose_name='Название тарифа')), ('description', models.TextField(blank=True, verbose_name='Описание')), ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Стоимость, руб.')), ('duration_hours', models.PositiveSmallIntegerField(verbose_name='Продолжительность, часов')), ('catch_limit', models.DecimalField(decimal_places=2, max_digits=6, verbose_name='Норма вылова, кг')), ('is_active', models.BooleanField(default=True, verbose_name='Действует'))],
            options={'verbose_name': 'тариф', 'verbose_name_plural': 'Тарифы', 'ordering': ['price', 'name']},
        ),
        migrations.CreateModel(
            name='User',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('username', models.CharField(max_length=150, unique=True, verbose_name='Логин')), ('password', models.CharField(max_length=128, verbose_name='Хеш пароля')), ('email', models.EmailField(max_length=254, unique=True, verbose_name='Электронная почта')), ('first_name', models.CharField(blank=True, max_length=150, verbose_name='Имя')), ('last_name', models.CharField(blank=True, max_length=150, verbose_name='Фамилия')), ('phone', models.CharField(blank=True, max_length=20, verbose_name='Телефон')), ('role', models.CharField(choices=[('guest', 'Гость'), ('angler', 'Рыболов'), ('ranger', 'Егерь'), ('ichthyologist', 'Ихтиолог'), ('admin', 'Администратор')], default='angler', max_length=20, verbose_name='Роль')), ('is_active', models.BooleanField(default=True, verbose_name='Активен')), ('date_joined', models.DateTimeField(auto_now_add=True, verbose_name='Дата регистрации'))],
            options={'verbose_name': 'пользователь', 'verbose_name_plural': 'Пользователи', 'ordering': ['last_name', 'first_name', 'username']},
        ),
        migrations.CreateModel(
            name='Sector',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('name', models.CharField(max_length=100, verbose_name='Название сектора')), ('description', models.TextField(blank=True, verbose_name='Описание')), ('capacity', models.PositiveSmallIntegerField(verbose_name='Вместимость')), ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Стоимость, руб.')), ('is_active', models.BooleanField(default=True, verbose_name='Доступен')), ('pond', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sectors', to='fishbridge.pond', verbose_name='Водоём'))],
            options={'verbose_name': 'рыболовный сектор', 'verbose_name_plural': 'Рыболовные секторы', 'ordering': ['pond__name', 'name']},
        ),
        migrations.CreateModel(
            name='StockingBatch',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('quantity', models.PositiveIntegerField(verbose_name='Количество рыб')), ('total_weight', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Общий вес, кг')), ('stocking_date', models.DateField(verbose_name='Дата зарыбления')), ('fish_species', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='stocking_batches', to='fishbridge.fishspecies', verbose_name='Вид рыбы')), ('pond', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='stocking_batches', to='fishbridge.pond', verbose_name='Водоём')), ('responsible', models.ForeignKey(limit_choices_to={'role': 'ichthyologist'}, on_delete=django.db.models.deletion.PROTECT, related_name='responsible_stocking_batches', to='fishbridge.user', verbose_name='Ответственный ихтиолог'))],
            options={'verbose_name': 'партия зарыбления', 'verbose_name_plural': 'Партии зарыбления', 'ordering': ['-stocking_date', 'pond__name']},
        ),
        migrations.CreateModel(
            name='Booking',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('start_datetime', models.DateTimeField(verbose_name='Начало бронирования')), ('end_datetime', models.DateTimeField(verbose_name='Окончание бронирования')), ('status', models.CharField(choices=[('pending', 'Ожидает подтверждения'), ('confirmed', 'Подтверждено'), ('cancelled', 'Отменено'), ('completed', 'Завершено')], default='pending', max_length=20, verbose_name='Статус')), ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')), ('sector', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bookings', to='fishbridge.sector', verbose_name='Рыболовный сектор')), ('tariff', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bookings', to='fishbridge.tariff', verbose_name='Тариф')), ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bookings', to='fishbridge.user', verbose_name='Пользователь'))],
            options={'verbose_name': 'бронирование', 'verbose_name_plural': 'Бронирования', 'ordering': ['-start_datetime']},
        ),
        migrations.CreateModel(
            name='CatchRecord',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('quantity', models.PositiveSmallIntegerField(verbose_name='Количество рыб')), ('total_weight', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Общий вес, кг')), ('recorded_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата и время учёта')), ('comment', models.TextField(blank=True, verbose_name='Комментарий')), ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='catch_records', to='fishbridge.booking', verbose_name='Бронирование')), ('fish_species', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='catch_records', to='fishbridge.fishspecies', verbose_name='Вид рыбы')), ('ranger', models.ForeignKey(limit_choices_to={'role': 'ranger'}, on_delete=django.db.models.deletion.PROTECT, related_name='recorded_catches', to='fishbridge.user', verbose_name='Егерь'))],
            options={'verbose_name': 'запись об улове', 'verbose_name_plural': 'Учёт улова', 'ordering': ['-recorded_at']},
        ),
        migrations.CreateModel(
            name='ExtraPayment',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('catch_weight', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Фактический вес улова, кг')), ('allowed_weight', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Разрешённый вес, кг')), ('excess_weight', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Превышение, кг')), ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Сумма доплаты, руб.')), ('decision', models.CharField(choices=[('release', 'Отпустить лишний улов'), ('pay_double', 'Оплатить по двойному тарифу')], max_length=20, verbose_name='Решение')), ('calculated_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата расчёта')), ('is_paid', models.BooleanField(default=False, verbose_name='Оплачено')), ('booking', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='extra_payment', to='fishbridge.booking', verbose_name='Бронирование'))],
            options={'verbose_name': 'доплата', 'verbose_name_plural': 'Доплаты', 'ordering': ['-calculated_at']},
        ),
        migrations.CreateModel(
            name='Rental',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('quantity', models.PositiveSmallIntegerField(verbose_name='Количество')), ('price_at_booking', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Цена на момент бронирования, руб.')), ('status', models.CharField(choices=[('reserved', 'Зарезервировано'), ('issued', 'Выдано'), ('returned', 'Возвращено')], default='reserved', max_length=20, verbose_name='Статус аренды')), ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rentals', to='fishbridge.booking', verbose_name='Бронирование')), ('rental_item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='rentals', to='fishbridge.rentalitem', verbose_name='Позиция проката'))],
            options={'verbose_name': 'аренда', 'verbose_name_plural': 'Аренда', 'ordering': ['booking_id', 'rental_item__name']},
        ),
        migrations.AddConstraint(model_name='user', constraint=models.CheckConstraint(condition=~Q(username=''), name='user_username_not_empty')),
        migrations.AddConstraint(model_name='pond', constraint=models.CheckConstraint(condition=Q(area__isnull=True) | Q(area__gt=0), name='pond_area_positive')),
        migrations.AddConstraint(model_name='pond', constraint=models.CheckConstraint(condition=Q(depth__isnull=True) | Q(depth__gt=0), name='pond_depth_positive')),
        migrations.AddConstraint(model_name='sector', constraint=models.UniqueConstraint(fields=('pond', 'name'), name='unique_sector_name_per_pond')),
        migrations.AddConstraint(model_name='sector', constraint=models.CheckConstraint(condition=Q(capacity__gt=0), name='sector_capacity_positive')),
        migrations.AddConstraint(model_name='sector', constraint=models.CheckConstraint(condition=Q(price__gte=0), name='sector_price_nonnegative')),
        migrations.AddConstraint(model_name='fishspecies', constraint=models.CheckConstraint(condition=Q(average_weight__isnull=True) | Q(average_weight__gt=0), name='fish_average_weight_positive')),
        migrations.AddConstraint(model_name='stockingbatch', constraint=models.UniqueConstraint(fields=('pond', 'fish_species', 'stocking_date'), name='unique_stocking_per_pond_species_date')),
        migrations.AddConstraint(model_name='stockingbatch', constraint=models.CheckConstraint(condition=Q(quantity__gt=0), name='stocking_quantity_positive')),
        migrations.AddConstraint(model_name='stockingbatch', constraint=models.CheckConstraint(condition=Q(total_weight__gt=0), name='stocking_weight_positive')),
        migrations.AddConstraint(model_name='tariff', constraint=models.CheckConstraint(condition=Q(price__gte=0), name='tariff_price_nonnegative')),
        migrations.AddConstraint(model_name='tariff', constraint=models.CheckConstraint(condition=Q(duration_hours__gt=0), name='tariff_duration_positive')),
        migrations.AddConstraint(model_name='tariff', constraint=models.CheckConstraint(condition=Q(catch_limit__gte=0), name='tariff_catch_limit_nonnegative')),
        migrations.AddConstraint(model_name='booking', constraint=models.CheckConstraint(condition=Q(end_datetime__gt=F('start_datetime')), name='booking_end_after_start')),
        migrations.AddIndex(model_name='booking', index=models.Index(fields=['sector', 'start_datetime', 'end_datetime'], name='booking_sector_dates_idx')),
        migrations.AddConstraint(model_name='rentalitem', constraint=models.CheckConstraint(condition=Q(price_per_day__gte=0), name='rental_item_price_nonnegative')),
        migrations.AddConstraint(model_name='rental', constraint=models.UniqueConstraint(fields=('booking', 'rental_item'), name='unique_rental_item_per_booking')),
        migrations.AddConstraint(model_name='rental', constraint=models.CheckConstraint(condition=Q(quantity__gt=0), name='rental_quantity_positive')),
        migrations.AddConstraint(model_name='rental', constraint=models.CheckConstraint(condition=Q(price_at_booking__gte=0), name='rental_price_nonnegative')),
        migrations.AddConstraint(model_name='catchrecord', constraint=models.CheckConstraint(condition=Q(quantity__gt=0), name='catch_quantity_positive')),
        migrations.AddConstraint(model_name='catchrecord', constraint=models.CheckConstraint(condition=Q(total_weight__gt=0), name='catch_weight_positive')),
        migrations.AddConstraint(model_name='extrapayment', constraint=models.CheckConstraint(condition=Q(catch_weight__gte=0), name='extra_catch_weight_nonnegative')),
        migrations.AddConstraint(model_name='extrapayment', constraint=models.CheckConstraint(condition=Q(allowed_weight__gte=0), name='extra_allowed_weight_nonnegative')),
        migrations.AddConstraint(model_name='extrapayment', constraint=models.CheckConstraint(condition=Q(excess_weight__gte=0), name='extra_excess_weight_nonnegative')),
        migrations.AddConstraint(model_name='extrapayment', constraint=models.CheckConstraint(condition=Q(amount__gte=0), name='extra_amount_nonnegative')),
    ]
