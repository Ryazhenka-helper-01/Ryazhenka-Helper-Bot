import os

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8248993284:AAH1xH0bq2Dup1XwU9X6IGrJ4L-OWjIA4Aw"  # токен бота от BotFather или из переменной окружения

DATA_FILE = "data.json"

XP_PER_MESSAGE = 1
XP_COOLDOWN_SECONDS = 0

DEFAULT_RANKS = [
    {"xp_min": 0, "name": "F"},
    {"xp_min": 100, "name": "D"},
    {"xp_min": 200, "name": "C"},
    {"xp_min": 300, "name": "B"},
    {"xp_min": 400, "name": "A"},
    {"xp_min": 500, "name": "S"},
    {"xp_min": 600, "name": "S+"},
    {"xp_min": 700, "name": "S++"},
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
    "switch_hekate_backup": (
        "Hekate (https://github.com/CTCaer/hekate):\n"
        "1) Скачай последний релиз hekate_ctcaer.bin и папку /bootloader.\n"
        "2) Скопируй файлы в корень microSD, отформатированной в FAT32.\n"
        "3) Запусти Hekate через RCM и перейди в 'Tools → Backup eMMC'.\n"
        "4) Сохрани BOOT0/1 и eMMC RAW GPP на ПК, проверь хэши и храни в безопасном месте.\n"
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
}
