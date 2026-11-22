from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [
        ('fishbridge', '0003_sector_temporary_closure'),
    ]

    operations = [
        migrations.AddField(
            model_name='fishspecies',
            name='over_limit_price_per_kg',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Цена за кг сверх нормы, руб.'),
        ),
        migrations.AddConstraint(
            model_name='fishspecies',
            constraint=models.CheckConstraint(condition=Q(over_limit_price_per_kg__gte=0), name='fish_over_limit_price_nonnegative'),
        ),
        migrations.AddField(
            model_name='catchrecord',
            name='trophy_weight',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=8, verbose_name='Вес трофейного экземпляра, кг'),
        ),
        migrations.AddField(
            model_name='catchrecord',
            name='trophy_decision',
            field=models.CharField(blank=True, choices=[('release', 'Отпустить обратно в водоём'), ('pay_double', 'Оплатить по двойному тарифу')], max_length=20, verbose_name='Решение по трофейному экземпляру'),
        ),
        migrations.AddConstraint(
            model_name='catchrecord',
            constraint=models.CheckConstraint(condition=Q(trophy_weight__gte=0), name='catch_trophy_weight_nonnegative'),
        ),
        migrations.AddConstraint(
            model_name='catchrecord',
            constraint=models.CheckConstraint(condition=Q(trophy_weight__lte=F('total_weight')), name='catch_trophy_not_over_total'),
        ),
        migrations.AddField(
            model_name='extrapayment',
            name='billable_weight',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name='Вес обычного улова, учитываемый в норме, кг'),
        ),
        migrations.AddField(
            model_name='extrapayment',
            name='released_weight',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name='Вес отпущенных трофеев, кг'),
        ),
        migrations.AddField(
            model_name='extrapayment',
            name='details',
            field=models.JSONField(blank=True, default=dict, verbose_name='Расшифровка расчёта'),
        ),
        migrations.AlterField(
            model_name='extrapayment',
            name='decision',
            field=models.CharField(choices=[('none', 'Без трофейного решения'), ('release', 'Трофейный экземпляр отпущен'), ('pay_double', 'Трофейный экземпляр оплачен по двойному тарифу'), ('mixed', 'Применены оба варианта')], default='none', max_length=20, verbose_name='Решение по трофеям'),
        ),
        migrations.AlterField(
            model_name='extrapayment',
            name='calculated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Дата расчёта'),
        ),
        migrations.AddConstraint(
            model_name='extrapayment',
            constraint=models.CheckConstraint(condition=Q(billable_weight__gte=0), name='extra_billable_weight_nonnegative'),
        ),
        migrations.AddConstraint(
            model_name='extrapayment',
            constraint=models.CheckConstraint(condition=Q(released_weight__gte=0), name='extra_released_weight_nonnegative'),
        ),
    ]
