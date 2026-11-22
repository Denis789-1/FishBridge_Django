from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from fishbridge.models import CatchRecord, ExtraPayment

CENT = Decimal('0.01')
ZERO = Decimal('0.00')


def money(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@transaction.atomic
def calculate_extra_payment(booking):
    records = list(
        CatchRecord.objects.filter(booking=booking)
        .select_related('fish_species')
        .order_by('fish_species_id', 'pk')
    )
    if not records:
        raise ValueError('Нельзя закрыть визит без зарегистрированного улова.')

    species_data = {}
    total_weight = ZERO
    released_weight = ZERO
    double_trophy_weight = ZERO
    decisions = set()

    for record in records:
        species_id = record.fish_species_id
        if species_id not in species_data:
            species_data[species_id] = {
                'name': record.fish_species.name,
                'rate': record.fish_species.over_limit_price_per_kg,
                'normal_weight': ZERO,
                'released_weight': ZERO,
                'double_trophy_weight': ZERO,
                'excess_weight': ZERO,
                'excess_amount': ZERO,
                'trophy_amount': ZERO,
            }
        item = species_data[species_id]
        trophy_weight = record.trophy_weight or ZERO
        normal_weight = record.total_weight - trophy_weight
        total_weight += record.total_weight
        item['normal_weight'] += normal_weight

        if trophy_weight:
            decisions.add(record.trophy_decision)
            if record.trophy_decision == CatchRecord.TrophyDecision.RELEASE:
                item['released_weight'] += trophy_weight
                released_weight += trophy_weight
            elif record.trophy_decision == CatchRecord.TrophyDecision.PAY_DOUBLE:
                item['double_trophy_weight'] += trophy_weight
                double_trophy_weight += trophy_weight

    normal_total = sum((item['normal_weight'] for item in species_data.values()), ZERO)
    allowed_weight = booking.tariff.catch_limit
    excess_weight = max(normal_total - allowed_weight, ZERO)
    amount = ZERO

    if excess_weight > ZERO and normal_total > ZERO:
        remaining = excess_weight
        species_items = list(species_data.values())
        for index, item in enumerate(species_items):
            if index == len(species_items) - 1:
                share = remaining
            else:
                share = (excess_weight * item['normal_weight'] / normal_total).quantize(CENT, rounding=ROUND_HALF_UP)
                share = min(share, remaining)
            item['excess_weight'] = share
            remaining -= share
            item['excess_amount'] = money(share * item['rate'])
            amount += item['excess_amount']

    for item in species_data.values():
        item['trophy_amount'] = money(item['double_trophy_weight'] * item['rate'] * Decimal('2'))
        amount += item['trophy_amount']

    if not decisions:
        decision = ExtraPayment.Decision.NONE
    elif decisions == {CatchRecord.TrophyDecision.RELEASE}:
        decision = ExtraPayment.Decision.RELEASE
    elif decisions == {CatchRecord.TrophyDecision.PAY_DOUBLE}:
        decision = ExtraPayment.Decision.PAY_DOUBLE
    else:
        decision = ExtraPayment.Decision.MIXED

    details = {
        'normal_catch_weight': str(normal_total),
        'double_trophy_weight': str(double_trophy_weight),
        'species': [
            {
                'name': item['name'],
                'price_per_kg': str(item['rate']),
                'normal_weight': str(item['normal_weight']),
                'released_trophy_weight': str(item['released_weight']),
                'double_trophy_weight': str(item['double_trophy_weight']),
                'excess_weight': str(item['excess_weight']),
                'excess_amount': str(item['excess_amount']),
                'trophy_amount': str(item['trophy_amount']),
                'total_amount': str(money(item['excess_amount'] + item['trophy_amount'])),
            }
            for item in species_data.values()
        ],
    }

    payment, created = ExtraPayment.objects.get_or_create(
        booking=booking,
        defaults={
            'catch_weight': total_weight,
            'allowed_weight': allowed_weight,
            'billable_weight': normal_total,
            'released_weight': released_weight,
            'excess_weight': excess_weight,
            'amount': money(amount),
            'decision': decision,
            'details': details,
        },
    )
    if not created:
        payment.catch_weight = total_weight
        payment.allowed_weight = allowed_weight
        payment.billable_weight = normal_total
        payment.released_weight = released_weight
        payment.excess_weight = excess_weight
        payment.amount = money(amount)
        payment.decision = decision
        payment.details = details
        payment.save()

    return payment
