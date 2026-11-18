
from datetime import datetime, timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone

from fishbridge.models import (
    Booking,
    Pond,
    Sector,
    Tariff,
    User as FishBridgeUser,
)


def home(request):
    featured_ponds = Pond.objects.filter(is_active=True)[:3]

    return render(request, 'main/index.html', {
        'featured_ponds': featured_ponds,
    })


def ponds_list(request):
    query = request.GET.get('q', '').strip()
    ponds = Pond.objects.filter(is_active=True)

    if query:
        ponds = ponds.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(address__icontains=query)
        )

    paginator = Paginator(ponds, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'main/ponds.html', {
        'page_obj': page_obj,
        'query': query,
    })


def pond_detail(request, pk):
    pond = get_object_or_404(Pond, pk=pk, is_active=True)

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
    sectors = Sector.objects.filter(
        is_active=True,
        pond__is_active=True,
    ).select_related('pond')
    tariffs = Tariff.objects.filter(is_active=True)

    selected_sector = request.GET.get('sector', '')
    selected_tariff = ''
    selected_datetime = ''

    if request.method == 'POST':
        selected_sector = request.POST.get('sector', '').strip()
        selected_tariff = request.POST.get('tariff', '').strip()
        selected_datetime = request.POST.get('start_datetime', '').strip()

        user_id = request.session.get('fishbridge_user_id')
        profile = FishBridgeUser.objects.filter(
            id=user_id,
            is_active=True,
        ).first() if user_id else None

        if not profile:
            messages.error(request, 'Чтобы отправить заявку, сначала войдите в аккаунт.')
            return redirect('login')

        try:
            sector = Sector.objects.get(
                pk=selected_sector,
                is_active=True,
                pond__is_active=True,
            )
            tariff = Tariff.objects.get(pk=selected_tariff, is_active=True)
            start_datetime = datetime.fromisoformat(selected_datetime)

            if timezone.is_naive(start_datetime):
                start_datetime = timezone.make_aware(start_datetime)

            if start_datetime <= timezone.now():
                raise ValueError('Выберите дату и время в будущем.')

            new_booking = Booking(
                user=profile,
                sector=sector,
                tariff=tariff,
                start_datetime=start_datetime,
                end_datetime=start_datetime + timedelta(hours=tariff.duration_hours),
            )
            new_booking.full_clean()
            new_booking.save()

            messages.success(request, 'Заявка на бронирование успешно отправлена.')
            return redirect('account')

        except (Sector.DoesNotExist, Tariff.DoesNotExist):
            messages.error(request, 'Выберите доступный сектор и действующий тариф.')
        except ValueError as error:
            messages.error(request, str(error) or 'Проверьте дату и время бронирования.')
        except ValidationError as error:
            for error_message in error.messages:
                messages.error(request, error_message)

    return render(request, 'main/booking.html', {
        'sectors': sectors,
        'tariffs': tariffs,
        'selected_sector': selected_sector,
        'selected_tariff': selected_tariff,
        'selected_datetime': selected_datetime,
    })


def account(request):
    user_id = request.session.get('fishbridge_user_id')

    profile = FishBridgeUser.objects.filter(
        id=user_id,
        is_active=True,
    ).first() if user_id else None

    bookings = Booking.objects.none()

    if profile:
        bookings = Booking.objects.filter(
            user=profile
        ).select_related('sector__pond', 'tariff')

    return render(request, 'main/account.html', {
        'profile': profile,
        'bookings': bookings,
        'completed_count': bookings.filter(
            status=Booking.Status.COMPLETED
        ).count(),
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

    return render(request, 'main/search_results.html', {
        'query': query,
        'ponds': ponds,
    })


def register_page(request):
    if request.session.get('fishbridge_user_id'):
        return redirect('account')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()

        errors = []

        if not username or not email or not password:
            errors.append('Заполните логин, электронную почту и пароль.')

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
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('account')

    return render(request, 'main/register.html')


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
            messages.success(request, 'Вы успешно вошли в аккаунт.')
            return redirect('account')

        messages.error(request, 'Неверный логин или пароль.')

    return render(request, 'main/login.html')


def logout_page(request):
    request.session.flush()
    messages.success(request, 'Вы вышли из аккаунта.')
    return redirect('home')
