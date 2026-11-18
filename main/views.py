
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

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
    sectors = Sector.objects.filter(
        is_active=True
    ).select_related('pond')

    tariffs = Tariff.objects.filter(is_active=True)
    selected_sector = request.GET.get('sector', '')

    return render(request, 'main/booking.html', {
        'sectors': sectors,
        'tariffs': tariffs,
        'selected_sector': selected_sector,
    })


def account(request):
    profile = None
    bookings = Booking.objects.none()
    rentals = Rental.objects.none()

    if request.user.is_authenticated:
        profile = FishBridgeUser.objects.filter(
            username=request.user.username,
            is_active=True,
        ).first()

    if profile:
        bookings = Booking.objects.filter(
            user=profile
        ).select_related('sector__pond', 'tariff')

        rentals = Rental.objects.filter(
            booking__user=profile
        ).select_related('rental_item', 'booking')

    return render(request, 'main/account.html', {
        'profile': profile,
        'bookings': bookings,
        'rentals': rentals,
        'rentals_count': rentals.count(),
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


def login_page(request):
    return render(request, 'main/login.html')


def register_page(request):
    return render(request, 'main/register.html')
