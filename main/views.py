
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.urls import reverse
from datetime import timedelta
import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .forms import BookingForm

from fishbridge.models import (
    Booking,
    Pond,
    Rental,
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
    user_id = request.session.get('fishbridge_user_id')
    profile = FishBridgeUser.objects.filter(id=user_id, is_active=True).first() if user_id else None
    form = BookingForm(request.POST or None, initial={
        'sector': request.GET.get('sector', '')
    })

    if request.method == 'POST':
        if not profile:
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
                if hasattr(error, 'message_dict'):
                    for field, errors in error.message_dict.items():
                        form.add_error(field if field in form.fields else None, errors)
                else:
                    form.add_error(None, error.messages)
            else:
                messages.success(request, 'Заявка на бронирование успешно отправлена.')
                return redirect('account')

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
    } for pond in ponds[:20]]
    return JsonResponse({'ponds': data})


def account(request):
    user_id = request.session.get('fishbridge_user_id')

    profile = FishBridgeUser.objects.filter(
        id=user_id,
        is_active=True,
    ).first() if user_id else None

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

        for pond in Pond.objects.filter(is_active=True).prefetch_related('sectors'):
            sector = pond.sectors.filter(is_active=True).first()
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
            messages.success(request, 'Вы успешно вошли в аккаунт.')
            return redirect('account')

        messages.error(request, 'Неверный логин или пароль.')

    return render(request, 'main/login.html')


def logout_page(request):
    request.session.flush()
    messages.success(request, 'Вы вышли из аккаунта.')
    return redirect('home')
