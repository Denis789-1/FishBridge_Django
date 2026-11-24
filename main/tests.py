from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .services import calculate_extra_payment
from fishbridge.models import Booking, CatchRecord, ExtraPayment, FishSpecies, Pond, Rental, RentalItem, Sector, Tariff, User
from .forms import BookingForm, CatchRecordForm, CloseVisitForm


class FishBridgeFeatureTests(TestCase):
    def setUp(self):
        self.angler = User.objects.create(
            username='angler_test',
            password='unused',
            email='angler@example.com',
            role=User.Role.ANGLER,
        )
        self.ranger = User.objects.create(
            username='ranger_test',
            password='unused',
            email='ranger@example.com',
            role=User.Role.RANGER,
        )
        self.pond = Pond.objects.create(name='Тестовый водоём', address='Тестовый адрес')
        self.second_pond = Pond.objects.create(name='Другой водоём', address='Другой адрес')
        self.sector = Sector.objects.create(
            pond=self.pond,
            name='Сектор 1',
            capacity=2,
            price=Decimal('1000.00'),
        )
        self.second_sector = Sector.objects.create(
            pond=self.second_pond,
            name='Сектор 2',
            capacity=2,
            price=Decimal('1200.00'),
        )
        self.tariff = Tariff.objects.create(
            name='Суточный',
            price=Decimal('1500.00'),
            duration_hours=24,
            catch_limit=Decimal('5.00'),
        )
        self.fish = FishSpecies.objects.create(name='Карп', over_limit_price_per_kg=Decimal('100.00'))
        self.start = timezone.now() + timedelta(days=3)
        self.booking = Booking.objects.create(
            user=self.angler,
            sector=self.sector,
            tariff=self.tariff,
            start_datetime=self.start,
            end_datetime=self.start + timedelta(hours=24),
        )

    def login_as(self, user):
        session = self.client.session
        session['fishbridge_user_id'] = user.pk
        session.save()

    def test_booking_form_filters_sectors_by_pond(self):
        form = BookingForm(initial={'pond': self.pond.pk})
        self.assertEqual(list(form.fields['sector'].queryset), [self.sector])

    def test_pond_detail_shows_booked_sector_for_selected_date(self):
        response = self.client.get(
            reverse('pond_detail', args=[self.pond.pk]),
            {'date': self.start.date().isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Забронирован на выбранную дату')

    def test_ranger_page_requires_ranger_role(self):
        response = self.client.get(reverse('ranger_catch'))
        self.assertRedirects(response, reverse('login'))
        self.login_as(self.angler)
        response = self.client.get(reverse('ranger_catch'))
        self.assertEqual(response.status_code, 403)
        self.login_as(self.ranger)
        response = self.client.get(reverse('ranger_catch'))
        self.assertEqual(response.status_code, 200)

    def test_catch_form_excludes_expired_bookings(self):
        expired_booking = Booking.objects.create(
            user=self.angler,
            sector=self.sector,
            tariff=self.tariff,
            start_datetime=timezone.now() - timedelta(days=2),
            end_datetime=timezone.now() - timedelta(days=1),
        )
        form = CatchRecordForm()
        self.assertNotIn(expired_booking, form.fields['booking'].queryset)

    def test_ranger_can_register_catch_for_booking(self):
        self.booking.start_datetime = timezone.now() - timedelta(hours=1)
        self.booking.end_datetime = timezone.now() + timedelta(hours=23)
        self.booking.save(update_fields=['start_datetime', 'end_datetime'])
        self.login_as(self.ranger)
        response = self.client.post(reverse('ranger_catch'), {
            'booking': self.booking.pk,
            'fish_species': self.fish.pk,
            'quantity': 2,
            'total_weight': '3.50',
            'comment': 'Проверочная запись',
        })
        self.assertRedirects(response, reverse('ranger_catch'))
        catch = CatchRecord.objects.get()
        self.assertEqual(catch.booking, self.booking)
        self.assertEqual(catch.ranger, self.ranger)
        self.assertEqual(catch.total_weight, Decimal('3.50'))

    def test_completed_booking_has_disabled_rental_button(self):
        self.booking.status = Booking.Status.COMPLETED
        self.booking.save(update_fields=['status'])
        self.login_as(self.angler)
        response = self.client.get(reverse('account'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<button class="btn" type="button" disabled>Добавить прокат</button>', html=True)

    def test_angler_can_add_rental_to_own_booking(self):
        self.login_as(self.angler)
        item = RentalItem.objects.create(
            name='Удочка',
            price_per_day=Decimal('200.00'),
            quantity_available=2,
        )
        response = self.client.post(reverse('rental_add', args=[self.booking.pk]), {
            'rental_item': item.pk,
            'quantity': 1,
        })
        self.assertRedirects(response, reverse('account'))
        rental = Rental.objects.get()
        self.assertEqual(rental.booking, self.booking)
        self.assertEqual(rental.quantity, 1)
        self.assertEqual(rental.price_at_booking, Decimal('200.00'))

    def test_angler_cannot_add_rental_to_another_users_booking(self):
        other_user = User.objects.create(
            username='other_test',
            password='unused',
            email='other@example.com',
            role=User.Role.ANGLER,
        )
        other_booking = Booking.objects.create(
            user=other_user,
            sector=self.second_sector,
            tariff=self.tariff,
            start_datetime=self.start,
            end_datetime=self.start + timedelta(hours=24),
        )
        self.login_as(self.angler)
        response = self.client.get(reverse('rental_add', args=[other_booking.pk]))
        self.assertEqual(response.status_code, 404)
    def test_temporary_sector_closure_hides_sector_from_booking_form(self):
        self.sector.is_closed = True
        self.sector.closure_reason = 'Технические работы'
        self.sector.save(update_fields=['is_closed', 'closure_reason'])
        form = BookingForm()
        self.assertNotIn(self.sector, form.fields['sector'].queryset)
        response = self.client.get(
            reverse('pond_detail', args=[self.pond.pk]),
            {'date': self.start.date().isoformat()},
        )
        self.assertContains(response, 'Технические работы')

    def test_admin_dashboard_is_restricted_to_admin_role(self):
        self.login_as(self.ranger)
        response = self.client.get(reverse('management_dashboard'))
        self.assertEqual(response.status_code, 403)
        admin_user = User.objects.create(
            username='admin_test',
            password='unused',
            email='admin@example.com',
            role=User.Role.ADMIN,
        )
        self.login_as(admin_user)
        response = self.client.get(reverse('management_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Начисления за период')
    def test_ichthyologist_dashboard_requires_ichthyologist_role(self):
        self.login_as(self.ranger)
        response = self.client.get(reverse('ichthyologist_dashboard'))
        self.assertEqual(response.status_code, 403)
        ichthyologist = User.objects.create(
            username='ichthyologist_test',
            password='unused',
            email='ichthyologist@example.com',
            role=User.Role.ICHTHYOLOGIST,
        )
        self.login_as(ichthyologist)
        response = self.client.get(reverse('ichthyologist_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Кабинет ихтиолога')


    def test_extra_payment_calculates_overage_using_each_species_price(self):
        pike = FishSpecies.objects.create(name='Щука', over_limit_price_per_kg=Decimal('200.00'))
        CatchRecord.objects.create(
            booking=self.booking,
            fish_species=self.fish,
            ranger=self.ranger,
            quantity=2,
            total_weight=Decimal('4.00'),
        )
        CatchRecord.objects.create(
            booking=self.booking,
            fish_species=pike,
            ranger=self.ranger,
            quantity=1,
            total_weight=Decimal('3.00'),
        )
        payment = calculate_extra_payment(self.booking)
        self.assertEqual(payment.catch_weight, Decimal('7.00'))
        self.assertEqual(payment.allowed_weight, Decimal('5.00'))
        self.assertEqual(payment.excess_weight, Decimal('2.00'))
        self.assertEqual(payment.amount, Decimal('286.00'))
        self.assertEqual(len(payment.details['species']), 2)

    def test_released_trophy_is_excluded_from_chargeable_catch(self):
        CatchRecord.objects.create(
            booking=self.booking,
            fish_species=self.fish,
            ranger=self.ranger,
            quantity=2,
            total_weight=Decimal('9.00'),
            trophy_weight=Decimal('6.00'),
            trophy_decision=CatchRecord.TrophyDecision.RELEASE,
        )
        payment = calculate_extra_payment(self.booking)
        self.assertEqual(payment.catch_weight, Decimal('9.00'))
        self.assertEqual(payment.billable_weight, Decimal('3.00'))
        self.assertEqual(payment.released_weight, Decimal('6.00'))
        self.assertEqual(payment.excess_weight, Decimal('0.00'))
        self.assertEqual(payment.amount, Decimal('0.00'))

    def test_trophy_paid_at_double_species_rate(self):
        CatchRecord.objects.create(
            booking=self.booking,
            fish_species=self.fish,
            ranger=self.ranger,
            quantity=1,
            total_weight=Decimal('6.50'),
            trophy_weight=Decimal('6.50'),
            trophy_decision=CatchRecord.TrophyDecision.PAY_DOUBLE,
        )
        payment = calculate_extra_payment(self.booking)
        self.assertEqual(payment.billable_weight, Decimal('0.00'))
        self.assertEqual(payment.excess_weight, Decimal('0.00'))
        self.assertEqual(payment.amount, Decimal('1300.00'))
        self.assertEqual(payment.decision, ExtraPayment.Decision.PAY_DOUBLE)

    def test_catch_form_rejects_trophy_weight_not_over_five_kg(self):
        self.booking.start_datetime = timezone.now() - timedelta(hours=1)
        self.booking.end_datetime = timezone.now() + timedelta(hours=23)
        self.booking.save(update_fields=['start_datetime', 'end_datetime'])
        form = CatchRecordForm(data={
            'booking': self.booking.pk,
            'fish_species': self.fish.pk,
            'quantity': 1,
            'total_weight': '5.00',
            'trophy_weight': '5.00',
            'trophy_decision': CatchRecord.TrophyDecision.RELEASE,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('trophy_weight', form.errors)

    def test_catch_form_excludes_future_bookings(self):
        form = CatchRecordForm()
        self.assertNotIn(self.booking, form.fields['booking'].queryset)

    def test_ranger_cannot_close_future_booking(self):
        CatchRecord.objects.create(
            booking=self.booking,
            fish_species=self.fish,
            ranger=self.ranger,
            quantity=1,
            total_weight=Decimal('2.00'),
        )
        form = CloseVisitForm()
        self.assertNotIn(self.booking, form.fields['booking'].queryset)
        self.login_as(self.ranger)
        response = self.client.post(reverse('ranger_catch'), {
            'action': 'close_visit',
            'booking': self.booking.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)
        self.assertFalse(ExtraPayment.objects.filter(booking=self.booking).exists())

    def test_ranger_can_close_visit_and_save_automatic_calculation(self):
        self.booking.start_datetime = timezone.now() - timedelta(hours=1)
        self.booking.end_datetime = timezone.now() + timedelta(hours=23)
        self.booking.save(update_fields=['start_datetime', 'end_datetime'])
        CatchRecord.objects.create(
            booking=self.booking,
            fish_species=self.fish,
            ranger=self.ranger,
            quantity=2,
            total_weight=Decimal('7.00'),
        )
        self.login_as(self.ranger)
        response = self.client.post(reverse('ranger_catch'), {
            'action': 'close_visit',
            'booking': self.booking.pk,
        })
        self.assertRedirects(response, reverse('ranger_catch'))
        payment = ExtraPayment.objects.get(booking=self.booking)
        self.booking.refresh_from_db()
        self.assertEqual(payment.amount, Decimal('200.00'))
        self.assertEqual(self.booking.status, Booking.Status.COMPLETED)

    def test_booking_page_renders_pond_filter(self):
        response = self.client.get(reverse('booking'), {'pond': self.pond.pk, 'sector': self.sector.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Водоём')
        self.assertContains(response, 'Сектор 1')

