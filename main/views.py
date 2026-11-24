
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch, Sum
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse
from django.templatetags.static import static
from datetime import timedelta, datetime, time
import logging
import re
from functools import wraps
from django.utils import timezone
from django.utils.dateparse import parse_date
from decimal import Decimal
from django.db import transaction
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .forms import BookingForm, RentalForm, CatchRecordForm, CloseVisitForm

logger = logging.getLogger(__name__)

from .services import calculate_extra_payment

from fishbridge.models import (
    Booking,
    Pond,
    Rental,
    Sector,
    Tariff,
    User as FishBridgeUser,
    FishSpecies,
    StockingBatch,
    RentalItem,
    CatchRecord,
    ExtraPayment,
)



POND_IMAGES = {
    1: ('images/ozero-bolshoe-2.webp', 1023, 707),
    2: ('images/lesnoy-prud.webp', 1280, 960),
    3: ('images/carpovoe-ozero.webp', 596, 335),
    4: ('images/severny-prud.webp', 447, 447),
    5: ('images/south-ozero.webp', 678, 452),
    6: ('images/prud-tihiy.webp', 1000, 750),
    7: ('images/sosnovoe-ozero.webp', 528, 378),
    8: ('images/maly-prud.webp', 1333, 1000),
    9: ('images/west-ozero.webp', 1024, 768),
    10: ('images/vostochny-prud.webp', 1400, 933),
}


def add_pond_image(pond):
    image = POND_IMAGES.get(pond.pk)
    if image:
        pond.image_url = static(image[0])
        pond.image_width = image[1]
        pond.image_height = image[2]
    return pond


def get_profile(request):
    user_id = request.session.get('fishbridge_user_id')
    if not user_id:
        return None
    profile = FishBridgeUser.objects.filter(id=user_id, is_active=True).first()
    if profile is None:
        request.session.pop('fishbridge_user_id', None)
    return profile


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            profile = get_profile(request)
            if profile is None:
                messages.error(request, 'Для доступа к этой странице войдите в аккаунт.')
                return redirect('login')
            if profile.role not in roles:
                return HttpResponseForbidden('Недостаточно прав для просмотра этой страницы.')
            request.fishbridge_profile = profile
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def home(request):
    featured_ponds = Pond.objects.filter(is_active=True)[:3]
    for pond in featured_ponds:
        add_pond_image(pond)

    return render(request, 'main/index.html', {
        'featured_ponds': featured_ponds,
    })


def ponds_list(request):
    query = request.GET.get('q', '').strip()
    ponds = Pond.objects.filter(is_active=True).annotate(
        sectors_count=Count('sectors', filter=Q(sectors__is_active=True))
    )

    if query:
        ponds = ponds.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(address__icontains=query)
        )

    paginator = Paginator(ponds, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    for pond in page_obj:
        add_pond_image(pond)

    return render(request, 'main/ponds.html', {
        'page_obj': page_obj,
        'query': query,
    })


def pond_detail(request, pk):
    pond = get_object_or_404(Pond, pk=pk, is_active=True)
    add_pond_image(pond)
    selected_date_value = request.GET.get('date', '').strip()
    try:
        selected_date = datetime.strptime(selected_date_value, '%Y-%m-%d').date() if selected_date_value else timezone.localdate()
    except ValueError:
        selected_date = timezone.localdate()
    day_start = timezone.make_aware(datetime.combine(selected_date, time.min))
    day_end = day_start + timedelta(days=1)
    sectors = list(pond.sectors.all().select_related('pond'))
    occupied_sector_ids = set(Booking.objects.filter(
        sector__pond=pond,
        status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
        start_datetime__lt=day_end,
        end_datetime__gt=day_start,
    ).values_list('sector_id', flat=True))
    for sector in sectors:
        is_temporarily_closed = sector.is_closed and (sector.closed_until is None or sector.closed_until > timezone.now())
        if not sector.is_active or is_temporarily_closed:
            sector.status_label = sector.closure_reason or 'Временно недоступен'
            sector.is_booked_on_date = True
        elif sector.pk in occupied_sector_ids:
            sector.status_label = 'Забронирован на выбранную дату'
            sector.is_booked_on_date = True
        else:
            sector.status_label = 'Свободен на выбранную дату'
            sector.is_booked_on_date = False
    sectors.sort(key=lambda sector: (sector.is_booked_on_date, sector.name))
    fish_species = pond.fish_species.all()
    tariffs = Tariff.objects.filter(is_active=True)

    return render(request, 'main/pond_detail.html', {
        'pond': pond,
        'sectors': sectors,
        'fish_species': fish_species,
        'tariffs': tariffs,
        'selected_date': selected_date.isoformat(),
    })


def booking(request):
    profile = get_profile(request)
    form = BookingForm(request.POST or None, initial={
        'sector': request.GET.get('sector', ''),
        'pond': request.GET.get('pond', ''),
        'start_datetime': request.GET.get('start_datetime', ''),
    })

    if request.method == 'POST':
        logger.info('Получена отправка формы бронирования')
        if not profile:
            logger.warning('Попытка бронирования без действующего профиля')
            messages.error(request, 'Для бронирования сначала войдите в аккаунт.')
            return redirect('login')
        if profile.role != FishBridgeUser.Role.ANGLER:
            return HttpResponseForbidden('Бронировать сектор может только рыболов.')
        if form.is_valid():
            booking_item = form.save(commit=False)
            booking_item.user = profile
            booking_item.end_datetime = booking_item.start_datetime + timedelta(
                hours=booking_item.tariff.duration_hours
            )
            try:
                booking_item.full_clean()
                booking_item.save()
            except ValidationError as error:
                logger.error('Ошибка проверки данных бронирования: %s', error)
                if hasattr(error, 'message_dict'):
                    for field, errors in error.message_dict.items():
                        form.add_error(field if field in form.fields else None, errors)
                else:
                    form.add_error(None, error.messages)
            except Exception:
                logger.exception('Не удалось сохранить бронирование')
                raise
            else:
                logger.info('Бронирование успешно сохранено: booking_id=%s', booking_item.pk)
                messages.success(request, 'Заявка на бронирование успешно отправлена!')
                return redirect('account')
        else:
            logger.warning('Форма бронирования не прошла проверку: %s', form.errors.as_json())

    return render(request, 'main/booking.html', {'form': form})


def ponds_api(request):
    query = request.GET.get('q', '').strip()
    ponds = Pond.objects.filter(is_active=True)
    if query:
        ponds = ponds.filter(
            Q(name__icontains=query) | Q(description__icontains=query) | Q(address__icontains=query)
        )
    data = [{
        'id': pond.pk,
        'name': pond.name,
        'description': pond.description or 'Описание пока не добавлено.',
        'address': pond.address,
        'url': reverse('pond_detail', args=[pond.pk]),
        'image_url': static(POND_IMAGES[pond.pk][0]) if pond.pk in POND_IMAGES else '',
        'image_width': POND_IMAGES[pond.pk][1] if pond.pk in POND_IMAGES else 0,
        'image_height': POND_IMAGES[pond.pk][2] if pond.pk in POND_IMAGES else 0,
    } for pond in ponds[:20]]
    logger.debug('API поиска водоёмов: query=%r, results=%s', query, len(data))
    return JsonResponse({'ponds': data})


def account(request):
    profile = get_profile(request)

    bookings = Booking.objects.none()
    rentals = Rental.objects.none()
    extra_payments = ExtraPayment.objects.none()

    favorite_ponds = []

    if profile:
        bookings = Booking.objects.filter(
            user=profile
        ).select_related('sector__pond', 'tariff')

        rentals = Rental.objects.filter(
            booking__user=profile
        ).select_related('rental_item', 'booking')
        extra_payments = ExtraPayment.objects.filter(
            booking__user=profile
        ).select_related('booking__sector__pond')

        ponds = Pond.objects.filter(is_active=True).prefetch_related(
            Prefetch(
                'sectors',
                queryset=Sector.objects.filter(is_active=True).order_by('pk'),
                to_attr='active_sectors',
            )
        )
        for pond in ponds:
            sector = pond.active_sectors[0] if pond.active_sectors else None
            favorite_ponds.append({
                'id': pond.pk,
                'name': pond.name,
                'description': pond.description or 'Описание пока не добавлено.',
                'address': pond.address or '',
                'detail_url': reverse('pond_detail', args=[pond.pk]),
                'booking_url': reverse('booking') + (f'?sector={sector.pk}' if sector else ''),
                'has_sector': bool(sector),
            })

    return render(request, 'main/account.html', {
        'profile': profile,
        'bookings': bookings,
        'rentals': rentals,
        'extra_payments': extra_payments,
        'rentals_count': rentals.count(),
        'completed_count': bookings.filter(
            status=Booking.Status.COMPLETED
        ).count(),
        'favorite_ponds': favorite_ponds,
    })



@role_required(FishBridgeUser.Role.ANGLER)
def rental_add(request, booking_id):
    profile = request.fishbridge_profile
    booking_item = get_object_or_404(Booking, pk=booking_id, user=profile)
    if booking_item.status not in [Booking.Status.PENDING, Booking.Status.CONFIRMED]:
        messages.error(request, 'Прокат можно добавить только к активному бронированию.')
        return redirect('account')
    form = RentalForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        rental_item = form.cleaned_data['rental_item']
        quantity = form.cleaned_data['quantity']
        days = max(1, (booking_item.tariff.duration_hours + 23) // 24)
        with transaction.atomic():
            item = RentalItem.objects.select_for_update().get(pk=rental_item.pk)
            reserved = Rental.objects.filter(
                rental_item=item,
                status__in=[Rental.Status.RESERVED, Rental.Status.ISSUED],
                booking__status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
                booking__start_datetime__lt=booking_item.end_datetime,
                booking__end_datetime__gt=booking_item.start_datetime,
            ).exclude(booking=booking_item).aggregate(total=Sum('quantity'))['total'] or 0
            already_in_booking = Rental.objects.filter(
                booking=booking_item,
                rental_item=item,
                status__in=[Rental.Status.RESERVED, Rental.Status.ISSUED],
            ).aggregate(total=Sum('quantity'))['total'] or 0
            if reserved + already_in_booking + quantity > item.quantity_available:
                form.add_error('quantity', 'Недостаточно оборудования на выбранный период.')
            else:
                rental, created = Rental.objects.get_or_create(
                    booking=booking_item,
                    rental_item=item,
                    defaults={
                        'quantity': quantity,
                        'price_at_booking': item.price_per_day * days * quantity,
                    },
                )
                if not created:
                    rental.quantity += quantity
                    rental.price_at_booking += item.price_per_day * days * quantity
                    rental.status = Rental.Status.RESERVED
                    rental.save(update_fields=['quantity', 'price_at_booking', 'status'])
                messages.success(request, 'Оборудование добавлено к бронированию.')
                return redirect('account')
    return render(request, 'main/rental_add.html', {
        'booking': booking_item,
        'form': form,
    })


@role_required(FishBridgeUser.Role.RANGER)
def ranger_catch(request):
    form = CatchRecordForm()
    close_form = CloseVisitForm()
    if request.method == 'POST' and request.POST.get('action') == 'close_visit':
        close_form = CloseVisitForm(request.POST)
        if close_form.is_valid():
            booking_item = close_form.cleaned_data['booking']
            try:
                payment = calculate_extra_payment(booking_item)
            except ValueError as error:
                messages.error(request, str(error))
            else:
                booking_item.status = Booking.Status.COMPLETED
                booking_item.save(update_fields=['status'])
                logger.info('Визит закрыт: booking_id=%s extra_payment=%s', booking_item.pk, payment.amount)
                messages.success(request, f'Визит закрыт. Доплата рассчитана автоматически: {payment.amount:.2f} руб.')
                return redirect('ranger_catch')
    elif request.method == 'POST':
        form = CatchRecordForm(request.POST)
        if form.is_valid():
            catch = form.save(commit=False)
            catch.ranger = request.fishbridge_profile
            catch.save()
            logger.info('Егерь зарегистрировал улов: catch_id=%s booking_id=%s', catch.pk, catch.booking_id)
            messages.success(request, 'Данные об улове сохранены. После внесения всех видов рыбы закройте визит для расчёта доплаты.')
            return redirect('ranger_catch')
    recent_catches = CatchRecord.objects.select_related(
        'booking__user', 'booking__tariff', 'booking__sector__pond', 'fish_species', 'ranger'
    )[:30]
    recent_payments = ExtraPayment.objects.select_related('booking__user', 'booking__sector__pond')[:20]
    return render(request, 'main/ranger_catch.html', {
        'form': form,
        'close_form': close_form,
        'recent_catches': recent_catches,
        'recent_payments': recent_payments,
    })


@role_required(FishBridgeUser.Role.ICHTHYOLOGIST)
def ichthyologist_dashboard(request):
    batches = StockingBatch.objects.select_related(
        'pond', 'fish_species', 'responsible'
    )
    species = FishSpecies.objects.all()
    return render(request, 'main/ichthyologist.html', {
        'batches': batches,
        'species': species,
    })


@role_required(FishBridgeUser.Role.ADMIN)
def management_dashboard(request):
    date_from = parse_date(request.GET.get('date_from', ''))
    date_to = parse_date(request.GET.get('date_to', ''))
    bookings = Booking.objects.exclude(status=Booking.Status.CANCELLED)
    if date_from:
        bookings = bookings.filter(start_datetime__date__gte=date_from)
    if date_to:
        bookings = bookings.filter(start_datetime__date__lte=date_to)
    booking_total = bookings.aggregate(total=Sum('tariff__price'))['total'] or Decimal('0.00')
    rental_total = Rental.objects.filter(booking__in=bookings).aggregate(
        total=Sum('price_at_booking')
    )['total'] or Decimal('0.00')
    extra_total = ExtraPayment.objects.filter(booking__in=bookings).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    return render(request, 'main/management.html', {
        'ponds_count': Pond.objects.count(),
        'sectors_count': Sector.objects.count(),
        'bookings_count': bookings.count(),
        'rentals_count': Rental.objects.filter(booking__in=bookings).count(),
        'catches_count': CatchRecord.objects.filter(booking__in=bookings).count(),
        'booking_total': booking_total,
        'rental_total': rental_total,
        'extra_total': extra_total,
        'accrual_total': booking_total + rental_total + extra_total,
        'date_from': date_from.isoformat() if date_from else '',
        'date_to': date_to.isoformat() if date_to else '',
        'admin_url': '/admin/',
    })


def about(request):
    return render(request, 'main/about.html')


def search_results(request):
    query = request.GET.get('q', '').strip()
    ponds = Pond.objects.none()

    if query:
        ponds = Pond.objects.filter(
            is_active=True
        ).filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(address__icontains=query)
        )

    for pond in ponds:
        add_pond_image(pond)

    return render(request, 'main/search_results.html', {
        'query': query,
        'ponds': ponds,
    })


def register_page(request):
    if request.session.get('fishbridge_user_id'):
        return redirect('account')

    values = {}
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        values = {'first_name': first_name, 'last_name': last_name, 'username': username, 'email': email, 'phone': phone}

        errors = []

        if not username or not email or not password:
            errors.append('Заполните логин, электронную почту и пароль.')

        try:
            validate_email(email)
        except ValidationError:
            errors.append('Введите корректный адрес электронной почты.')

        if phone and (not re.fullmatch(r'[+0-9()\- ]{6,20}', phone) or len(re.sub(r'\D', '', phone)) < 6):
            errors.append('Введите корректный номер телефона.')

        if len(username) > 150 or len(first_name) > 150 or len(last_name) > 150:
            errors.append('Имя, фамилия и логин не должны превышать 150 символов.')

        if len(password) < 8:
            errors.append('Пароль должен содержать минимум 8 символов.')

        if len(password.strip()) < 8:
            errors.append('Пароль должен содержать минимум 8 символов.')

        if FishBridgeUser.objects.filter(username=username).exists():
            errors.append('Пользователь с таким логином уже существует.')

        if FishBridgeUser.objects.filter(email=email).exists():
            errors.append('Пользователь с такой почтой уже существует.')

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            user = FishBridgeUser.objects.create(
                username=username,
                email=email,
                password=make_password(password),
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=FishBridgeUser.Role.ANGLER,
            )

            request.session['fishbridge_user_id'] = user.id
            logger.info('Зарегистрирован пользователь: user_id=%s', user.pk)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('account')

    return render(request, 'main/register.html', {'values': values})


def login_page(request):
    if request.session.get('fishbridge_user_id'):
        return redirect('account')

    if request.method == 'POST':
        login_value = request.POST.get('username', '').strip()
        if not login_value:
            login_value = request.POST.get('email', '').strip()

        password = request.POST.get('password', '')

        user = FishBridgeUser.objects.filter(
            Q(username=login_value) | Q(email=login_value.lower()),
            is_active=True,
        ).first()

        if user and check_password(password, user.password):
            request.session.cycle_key()
            request.session['fishbridge_user_id'] = user.id
            logger.info('Успешный вход пользователя: user_id=%s', user.pk)
            messages.success(request, 'Вы успешно вошли в аккаунт.')
            return redirect('account')

        logger.warning('Неудачная попытка входа')
        messages.error(request, 'Неверный логин или пароль.')

    return render(request, 'main/login.html')


def logout_page(request):
    request.session.flush()
    messages.success(request, 'Вы вышли из аккаунта.')
    return redirect('home')
