
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.templatetags.static import static
from datetime import timedelta
import logging
import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .forms import BookingForm

logger = logging.getLogger(__name__)

from fishbridge.models import (
    Booking,
    Pond,
    Rental,
    Sector,
    Tariff,
    User as FishBridgeUser,
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

    sectors = pond.sectors.filter(is_active=True)
    fish_species = pond.fish_species.all()
    tariffs = Tariff.objects.filter(is_active=True)

    return render(request, 'main/pond_detail.html', {
        'pond': pond,
        'sectors': sectors,
        'fish_species': fish_species,
        'tariffs': tariffs,
    })


def booking(request):
    user_id = request.session.get('fishbridge_user_id')
    profile = FishBridgeUser.objects.filter(id=user_id, is_active=True).first() if user_id else None
    form = BookingForm(request.POST or None, initial={
        'sector': request.GET.get('sector', '')
    })

    if request.method == 'POST':
        logger.info('Получена отправка формы бронирования')
        if not profile:
            logger.warning('Попытка бронирования без действующего профиля')
            messages.error(request, 'Для бронирования сначала войдите в аккаунт.')
            return redirect('login')
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
                messages.success(request, 'Заявка на бронирование успешно отправлена.')
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
    user_id = request.session.get('fishbridge_user_id')

    profile = FishBridgeUser.objects.filter(
        id=user_id,
        is_active=True,
    ).first() if user_id else None
    if user_id and profile is None:
        logger.warning('В сессии найден несуществующий или неактивный профиль: user_id=%s', user_id)
        request.session.pop('fishbridge_user_id', None)

    bookings = Booking.objects.none()
    rentals = Rental.objects.none()

    favorite_ponds = []

    if profile:
        bookings = Booking.objects.filter(
            user=profile
        ).select_related('sector__pond', 'tariff')

        rentals = Rental.objects.filter(
            booking__user=profile
        ).select_related('rental_item', 'booking')

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
        'rentals_count': rentals.count(),
        'completed_count': bookings.filter(
            status=Booking.Status.COMPLETED
        ).count(),
        'favorite_ponds': favorite_ponds,
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

        if phone and not re.fullmatch(r'[+0-9()\- ]{6,20}', phone):
            errors.append('Введите корректный номер телефона.')

        if len(username) > 150 or len(first_name) > 150 or len(last_name) > 150:
            errors.append('Имя, фамилия и логин не должны превышать 150 символов.')

        if len(password) < 8:
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
