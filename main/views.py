from django.shortcuts import render
from django.core.paginator import Paginator
from fishbridge.models import Pond


def home(request):
    return render(request, 'main/index.html')


def ponds_list(request):
    ponds = Pond.objects.filter(is_active=True)

    query = request.GET.get('q', '')

    if query:
        ponds = ponds.filter(
            name__icontains=query
        ) | ponds.filter(
            description__icontains=query
        ) | ponds.filter(
            address__icontains=query
        )

    paginator = Paginator(ponds, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'main/ponds.html', {
        'page_obj': page_obj,
        'query': query
    })