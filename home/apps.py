import logging
import threading

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class HomeConfig(AppConfig):
    name = 'home'

    def ready(self):
        # Safety net: if the shop was never seeded (e.g. deploys where the
        # pre-deploy command didn't run), fill it on first startup.
        threading.Thread(target=self._seed_if_empty, daemon=True).start()

    def _seed_if_empty(self):
        try:
            from django.core.management import call_command
            from home.models import ShopItem
            if not ShopItem.objects.exists():
                call_command('seed_shop', verbosity=0)
                call_command('seed_achievements', verbosity=0)
                logger.info('Shop was empty — seeded items, raffle and achievements on startup.')
        except Exception:
            # Tables may not exist yet (first migrate) or DB unreachable;
            # never let startup seeding crash the app.
            pass
