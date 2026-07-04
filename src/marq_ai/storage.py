import json
import os


MARQ_HISTORY_FILE = (
    "data/marq_ai/history.json"
)


def ensure_storage():
    os.makedirs(
        "data/marq_ai",
        exist_ok=True,
    )

    if not os.path.exists(
        MARQ_HISTORY_FILE
    ):
        with open(
            MARQ_HISTORY_FILE,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                [],
                file,
                ensure_ascii=False,
                indent=2,
            )


def load_history():
    ensure_storage()

    with open(
        MARQ_HISTORY_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def append_history(
    record: dict
):
    history = load_history()

    history.append(
        record
    )

    with open(
        MARQ_HISTORY_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            history,
            file,
            ensure_ascii=False,
            indent=2,
        )
