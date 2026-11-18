from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db import transaction

from fishbridge.models import (
    User, Pond, Sector, FishSpecies, StockingBatch, Tariff, Booking,
    RentalItem, Rental, CatchRecord, ExtraPayment,
)


class Command(BaseCommand):
    help = 'Создаёт демонстрационные данные FishBridge (повторный запуск не дублирует записи).'

    @transaction.atomic
    def handle(self, *args, **options):
        # Пользователи разных ролей
        admin, _ = User.objects.get_or_create(
            username='admin_demo', defaults={'password': make_password('demo12345'), 'email': 'admin@fishbridge.local', 'first_name': 'Анна', 'last_name': 'Администратор', 'role': User.Role.ADMIN}
        )
        ichthyologists = []
        for i in range(1, 3):
            obj, _ = User.objects.get_or_create(
                username=f'ichthyologist{i}', defaults={'password': make_password('demo12345'), 'email': f'ichthyologist{i}@fishbridge.local', 'first_name': f'Ихтиолог{i}', 'role': User.Role.ICHTHYOLOGIST}
            )
            ichthyologists.append(obj)
        rangers = []
        for i in range(1, 4):
            obj, _ = User.objects.get_or_create(
                username=f'ranger{i}', defaults={'password': make_password('demo12345'), 'email': f'ranger{i}@fishbridge.local', 'first_name': f'Егерь{i}', 'role': User.Role.RANGER}
            )
            rangers.append(obj)
        anglers = []
        for i in range(1, 31):
            obj, _ = User.objects.get_or_create(
                username=f'angler{i:02d}', defaults={'password': make_password('demo12345'), 'email': f'angler{i:02d}@fishbridge.local', 'first_name': f'Рыболов{i}', 'last_name': 'Тестовый', 'phone': f'+7999000{i:04d}', 'role': User.Role.ANGLER}
            )
            anglers.append(obj)

        ponds = []
        pond_data = [
    ('Большое озеро', 'Основной водоём клуба', '12.50', '4.50'),
    ('Лесной пруд', 'Пруд в лесной части клуба', '4.20', '2.80'),
    ('Карповое озеро', 'Водоём для карповой рыбалки', '7.80', '3.20'),
    ('Северный пруд', 'Водоём в северной части клуба', '3.50', '2.10'),
    ('Южное озеро', 'Водоём в южной части клуба', '6.20', '3.00'),
    ('Тихий пруд', 'Небольшой спокойный водоём', '2.80', '1.80'),
    ('Сосновое озеро', 'Озеро рядом с сосновым лесом', '8.40', '3.60'),
    ('Малый пруд', 'Небольшой водоём для рыбалки', '1.90', '1.50'),
    ('Западное озеро', 'Водоём в западной части клуба', '5.70', '2.90'),
    ('Восточный пруд', 'Пруд в восточной части клуба', '3.10', '2.00'),
]
        for name, desc, area, depth in pond_data:
            obj, _ = Pond.objects.get_or_create(name=name, defaults={'description': desc, 'area': Decimal(area), 'depth': Decimal(depth), 'address': 'Московская область, загородный клуб FishBridge'})
            ponds.append(obj)

        sectors = []
        for p_index, pond in enumerate(ponds, start=1):
            for n in range(1, 5):
                obj, _ = Sector.objects.get_or_create(pond=pond, name=f'Мостик {n}', defaults={'description': f'Рыболовный мостик {n}', 'capacity': 2 + n % 3, 'price': Decimal(1800 + p_index * 200 + n * 100)})
                sectors.append(obj)

        species = []
        for name, avg in [
    ('Карп', '3.50'),
    ('Карась', '0.80'),
    ('Щука', '2.20'),
    ('Амур', '4.00'),
    ('Окунь', '0.45'),
    ('Лещ', '1.50'),
    ('Сом', '8.00'),
    ('Линь', '1.20'),
    ('Плотва', '0.30'),
    ('Судак', '2.50'),
]:
            obj, _ = FishSpecies.objects.get_or_create(name=name, defaults={'description': f'Пресноводный вид рыбы: {name.lower()}', 'average_weight': Decimal(avg)})
            species.append(obj)

        tariffs = []
        for name, price, duration, limit in [
    ('Стандартный', '3000.00', 24, '5.00'),
    ('Полдня', '1800.00', 12, '3.00'),
    ('Семейный', '4500.00', 24, '8.00'),
    ('Утренний', '1500.00', 6, '2.00'),
    ('Вечерний', '1700.00', 6, '3.00'),
    ('Суточный', '3500.00', 24, '6.00'),
    ('Выходной', '4000.00', 24, '7.00'),
    ('Премиум', '5500.00', 24, '10.00'),
    ('Ночной', '2000.00', 8, '4.00'),
    ('Двухдневный', '6000.00', 48, '12.00'),
]:
            obj, _ = Tariff.objects.get_or_create(name=name, defaults={'description': f'Тариф {name.lower()}', 'price': Decimal(price), 'duration_hours': duration, 'catch_limit': Decimal(limit)})
            tariffs.append(obj)

        items = []
        for name, price, count in [
    ('Удочка', '500.00', 15),
    ('Подсачек', '200.00', 12),
    ('Садок', '150.00', 10),
    ('Кресло', '300.00', 8),
    ('Спиннинг', '650.00', 10),
    ('Катушка', '250.00', 7),
    ('Рыболовный набор', '800.00', 5),
    ('Палатка', '1200.00', 4),
    ('Фонарь', '250.00', 10),
    ('Подставка для удочки', '180.00', 12),
]:
            obj, _ = RentalItem.objects.get_or_create(name=name, defaults={'description': f'{name} для рыбалки', 'price_per_day': Decimal(price), 'quantity_available': count})
            items.append(obj)

        # Не менее 10 партий зарыбления (связь водоём—вид рыбы через явную модель).
        for i in range(10):
            pond = ponds[i % len(ponds)]
            fish = species[i % len(species)]
            stocking_day = date(2026, 5, 1) + timedelta(days=i)
            StockingBatch.objects.get_or_create(
                pond=pond, fish_species=fish, stocking_date=stocking_day,
                defaults={'quantity': 50 + i * 5, 'total_weight': Decimal('100.00') + Decimal(i * 5), 'responsible': ichthyologists[i % len(ichthyologists)]}
            )

        # 30 бронирований в основной таблице и связанные записи.
        base_day = date(2026, 12, 1)
        for i in range(30):
            start_naive = datetime.combine(base_day + timedelta(days=i), time(8, 0))
            start = timezone.make_aware(start_naive)
            end = start + timedelta(hours=24)
            booking, _ = Booking.objects.get_or_create(
                user=anglers[i], sector=sectors[i % len(sectors)], start_datetime=start,
                defaults={'tariff': tariffs[i % len(tariffs)], 'end_datetime': end, 'status': Booking.Status.CONFIRMED if i % 4 else Booking.Status.COMPLETED}
            )
            item = items[i % len(items)]
            Rental.objects.get_or_create(booking=booking, rental_item=item, defaults={'quantity': 1 + i % 2, 'price_at_booking': item.price_per_day, 'status': Rental.Status.RETURNED if i % 3 == 0 else Rental.Status.ISSUED})
            fish = species[i % len(species)]
            CatchRecord.objects.get_or_create(booking=booking, fish_species=fish, ranger=rangers[i % len(rangers)], defaults={'quantity': 1 + i % 3, 'total_weight': Decimal('1.20') + Decimal(i % 7) / Decimal('2'), 'comment': 'Демонстрационная запись улова'})
            if i < 10:
                ExtraPayment.objects.get_or_create(
                    booking=booking,
                    defaults={'catch_weight': tariffs[i % len(tariffs)].catch_limit + Decimal('1.50'), 'allowed_weight': tariffs[i % len(tariffs)].catch_limit, 'excess_weight': Decimal('1.50'), 'amount': Decimal('1200.00'), 'decision': ExtraPayment.Decision.PAY_DOUBLE, 'is_paid': i % 2 == 0}
                )

        counts = {
            'Пользователи': User.objects.count(), 'Водоёмы': Pond.objects.count(),
            'Рыболовные секторы': Sector.objects.count(), 'Виды рыб': FishSpecies.objects.count(),
            'Партии зарыбления': StockingBatch.objects.count(), 'Тарифы': Tariff.objects.count(),
            'Бронирования': Booking.objects.count(), 'Позиции проката': RentalItem.objects.count(),
            'Аренда': Rental.objects.count(), 'Учёт улова': CatchRecord.objects.count(),
            'Доплаты': ExtraPayment.objects.count(),
        }
        for label, count in counts.items():
            self.stdout.write(f'{label}: {count}')
        self.stdout.write(self.style.SUCCESS('Демонстрационные данные FishBridge созданы.'))
