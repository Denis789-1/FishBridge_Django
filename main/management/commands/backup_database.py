import sqlite3
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Создаёт резервную копию базы данных SQLite.'

    def handle(self, *args, **options):
        database = settings.DATABASES['default']
        if database['ENGINE'] != 'django.db.backends.sqlite3':
            raise CommandError('Команда поддерживает только SQLite.')

        source_path = Path(database['NAME'])
        if not source_path.exists():
            raise CommandError('Файл базы данных не найден.')

        backup_dir = settings.BASE_DIR / 'backups'
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_path = backup_dir / f'db_{timestamp}.sqlite3'

        try:
            with sqlite3.connect(source_path) as source:
                with sqlite3.connect(backup_path) as destination:
                    source.backup(destination)
        except sqlite3.Error as error:
            if backup_path.exists():
                backup_path.unlink()
            raise CommandError(f'Не удалось создать резервную копию: {error}') from error

        self.stdout.write(self.style.SUCCESS(f'Резервная копия создана: {backup_path}'))
