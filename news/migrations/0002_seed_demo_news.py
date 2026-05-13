from datetime import date

from django.db import migrations


NEWS_SEED = [
    {
        "slug": "canggu-ubud-ride-guide",
        "published_at": date(2026, 5, 10),
        "sort_order": 30,
        "translations": {
            "en": {
                "title": "Canggu to Ubud: a comfortable route for first-time riders",
                "description": (
                    "Planning your first longer scooter trip in Bali? "
                    "The Canggu to Ubud route is one of the easiest ways to get comfortable with island traffic. "
                    "We recommend starting early, keeping a light rain layer under the seat, and stopping for a short break before central Ubud. "
                    "For new riders, scooters with relaxed seating and phone mounts make the trip noticeably easier."
                ),
            },
            "ru": {
                "title": "Маршрут Чангу - Убуд: удобная поездка для первого выезда",
                "description": (
                    "Если вы только начинаете ездить по Бали на байке, маршрут из Чангу в Убуд отлично подходит для первой более длинной поездки. "
                    "Лучше выезжать утром, брать с собой легкую дождевую куртку и делать короткую остановку перед въездом в центр Убуда. "
                    "Для начинающих особенно удобны скутеры с комфортной посадкой и держателем для телефона."
                ),
            },
        },
    },
    {
        "slug": "weekly-scooter-checks",
        "published_at": date(2026, 5, 6),
        "sort_order": 20,
        "translations": {
            "en": {
                "title": "What our team checks every week before a scooter goes out again",
                "description": (
                    "Every active rental scooter goes through a repeat check before the next booking. "
                    "We inspect brakes, lights, tire condition, mirrors, and basic fluid levels, then verify the helmet set and lock. "
                    "This weekly routine helps us keep the fleet predictable for guests who need a simple, ready-to-ride experience."
                ),
            },
            "ru": {
                "title": "Что мы проверяем каждую неделю перед следующей арендой",
                "description": (
                    "Перед следующей выдачей каждый активный скутер проходит повторную проверку. "
                    "Команда смотрит тормоза, свет, состояние шин, зеркала и базовые жидкости, а затем проверяет комплект шлемов и замок. "
                    "Такой регулярный процесс помогает держать парк в понятном и надежном состоянии для клиентов."
                ),
            },
        },
    },
    {
        "slug": "long-stay-rental-tips",
        "published_at": date(2026, 5, 2),
        "sort_order": 10,
        "translations": {
            "en": {
                "title": "3 simple tips if you are renting a scooter for two weeks or longer",
                "description": (
                    "For longer stays, small habits make the rental much smoother. "
                    "Save your fuel receipts for the first couple of days, keep the bike parked in covered areas when possible, and message support early if you notice anything unusual. "
                    "Long-term guests usually benefit most from a model with extra trunk space and softer suspension for daily island movement."
                ),
            },
            "ru": {
                "title": "3 простых совета, если вы арендуете скутер на две недели и дольше",
                "description": (
                    "При длительной аренде удобнее всего помогают простые привычки. "
                    "Сохраняйте чеки на топливо хотя бы в первые дни, по возможности оставляйте байк на крытой парковке и заранее пишите в поддержку, если заметили что-то необычное. "
                    "Для долгого пребывания чаще всего комфортнее модели с более мягкой подвеской и вместительным багажником."
                ),
            },
        },
    },
]


def seed_demo_news(apps, schema_editor):
    NewsArticle = apps.get_model("news", "NewsArticle")
    NewsArticleTranslation = apps.get_model("news", "NewsArticleTranslation")

    for item in NEWS_SEED:
        article, _ = NewsArticle.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "published_at": item["published_at"],
                "is_active": True,
                "sort_order": item["sort_order"],
            },
        )
        for language, translation in item["translations"].items():
            NewsArticleTranslation.objects.update_or_create(
                article=article,
                language=language,
                defaults={
                    "title": translation["title"],
                    "description": translation["description"],
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ("news", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_demo_news, migrations.RunPython.noop),
    ]
