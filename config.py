import os

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8248993284:AAH1xH0bq2Dup1XwU9X6IGrJ4L-OWjIA4Aw"  # токен бота от BotFather или из переменной окружения

DATA_FILE = "data.json"

XP_PER_MESSAGE = 1
XP_COOLDOWN_SECONDS = 0

GITHUB_REPO = "Dimasick-git/Ryzhenka"
RELEASE_CHECK_INTERVAL_SECONDS = 3600
RELEASE_DIFF_LIMIT = 15

HELP_KEYWORDS = [
    "нужна помощь",
    "помогите",
    "помоги",
    "что делать",
    "не работает",
    "как исправить",
    "help",
]

DEFAULT_RANKS = [
    {"xp_min": 0, "name": "F"},
    {"xp_min": 10, "name": "D"},
    {"xp_min": 20, "name": "C"},
    {"xp_min": 30, "name": "B"},
    {"xp_min": 40, "name": "A"},
    {"xp_min": 50, "name": "S"},
    {"xp_min": 60, "name": "S+"},
    {"xp_min": 70, "name": "S++"},
]

DEFAULT_GUIDES = {
    "switch_nh_server": (
        "NH Switch Guide (https://github.com/nh-server/switch-guide):\n"
        "1) Определи ревизию приставки и возможность входа в RCM.\n"
        "2) Скачай актуальный архив guide.zip из репозитория.\n"
        "3) Следуй чек-листу из папки 'getting-started' (подготовка карты, драйверы, TegraRcmGUI).\n"
        "4) Выполни пункты из раздела 'USER GUIDE' строго по порядку.\n"
    ),
    "switch_atmosphere": (
        "Atmosphere (https://github.com/Atmosphere-NX/Atmosphere):\n"
        "1) На странице релизов скачай последний atmosphere-*.zip и соответствующий fusee.bin.\n"
        "2) Распакуй содержимое архива в корень microSD, сохрани структуру /atmosphere.\n"
        "3) Скопируй fusee.bin для загрузчика (Hekate или напрямую через TegraRcmGUI).\n"
        "4) Загрузи приставку в RCM и запусти fusee.bin, затем следуй инструкциям Atmosphere.\n"
    ),
    "ryazhenka_hekate_backup": (
        "Ryazhenka Hekate Backup (Ryazhenka):\n"
        "1) Ryazhahand >>> Packages >>> Ryazhenkabestcfw Tuner >>> Настроить частоты (CPU,GPU,RAM).\n"
        "2) Управление Бэкапами >>>  Создаём Бэкап.\n"
        "3) Войди в Homebrew >>> All-in-One Switch Updater >>> Сторонние загрузки >>> Ryazhenka Best CFW >>> Подтвердить >>> Да/Нет — по ситуации (подробнее в видео ниже).\n"
        "4) Управление Бэкапами >>>  Restore Backup >>> выбери нужный по дате.\n"
        "5) Для наглядности используй видео-гайд: https://youtube.com/watch?v=x09UY5gCssw&si=BnNAQQ_K9KBXWOEd\n"
    ),
    "switch_sigpatch": (
        "Sigpatches (https://github.com/ITotalJustice/patches):\n"
        "1) Открой релиз Sigpatches for Atmosphere и скачай архив под свою версию FW.\n"
        "2) Распакуй содержимое (atmosphere/ и bootloader/) в корень microSD, согласись на замену.\n"
        "3) После каждой установки обновления firmware/Atmosphere повторяй шаги для актуальных патчей.\n"
        "4) Перезагрузи консоль через Hekate или через системное меню Atmosphere.\n"
    ),
    "switch_emummc": (
        "emuMMC с Hekate (https://github.com/CTCaer/hekate/blob/master/docs/emummc.md):\n"
        "1) Сделай полную резервную копию eMMC по гайду выше.\n"
        "2) В Hekate открой 'emuMMC → Create emuMMC' и выбери раздел или файл.\n"
        "3) После создания пропиши путь в 'emuMMC → Change emuMMC'.\n"
        "4) Загружайся через профиль emuMMC, не забывая обновлять Atmosphere и патчи.\n"
    ),
    "switch_switchroot": (
        "Android от switchroot (https://github.com/switchroot/android):\n"
        "1) Найди в релизах образ LineageOS/Android для своей модели Switch.\n"
        "2) Подготовь microSD по инструкции в README (разметка карт, копирование bootloader).\n"
        "3) Загрузись в Hekate и выбери профиль switchroot Android.\n"
        "4) После первого запуска настрой Google Apps/Aurora Store согласно гайду репозитория.\n"
    ),
    "ryazhenka_quick_install": (
        "Быстрая установка Ryazhenka (Ryazhenka):\n"
        "1) Скачай последний релиз: https://github.com/Dimasick-git/Ryzhenka/releases/latest\n"
        "2) Распакуй архив в корень microSD (FAT32).\n"
        "3) Вставь карту в Switch и войди в RCM.\n"
        "4) Запусти Hekate и выбери \"Ryazhenka CFW\".\n"
        "5) Готово — прошивка установлена.\n"
    ),
    "ryazhenka_support": (
        "Где искать помощь по Ryazhenka (Ryazhenka):\n"
        "1) Проверь FAQ проекта — часто задаваемые вопросы уже там.\n"
        "2) Просмотри Issues на GitHub: https://github.com/Dimasick-git/Ryzhenka/issues\n"
        "3) Создай новый Issue с подробным описанием проблемы.\n"
        "4) Подключись к Telegram-сообществу Ryazhenka для быстрой поддержки.\n"
    ),
    "ryazhenka_battery_fix": (
        "Ryazhenka Battery Fix (Ryazhenka):\n"
        "1) Полностью зарядите Switch до 100% в доке, не прерывая процесс.\n"
        "2) Включите Ryazhenka и запустите встроенный скрипт Battery Fix (раздел Tools → Maintenance).\n"
        "3) Дождитесь окончания калибровки — консоль автоматически перезагрузится.\n"
        "4) Разрядите консоль до 1-5%, затем снова зарядите до 100% для закрепления результата.\n"
        "5) При повторных проблемах проверьте FAQ/Issues: https://github.com/Dimasick-git/Ryzhenka/issues\n"
    ),
}
