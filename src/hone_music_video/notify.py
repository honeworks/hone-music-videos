"""Notifications (design §13.4, D-060): hone-flow tells one webhook when the run waits for the owner at a
gate, when a stage fails and when the video is done.

Configured only from the environment, or the `.env` files hone-models reads (`$HONE_ENV_FILE`, then
`./.env`; a variable already set wins): `HONE_MV_NOTIFY_URL`, `HONE_MV_NOTIFY_KIND` and
`HONE_MV_DASHBOARD_URL`. hone-flow reads the URL when it delivers and never records it (hone-flow §4.9)."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from hone_flow.notifications import (
    DiscordWebhook,
    HttpWebhook,
    MattermostWebhook,
    SlackWebhook,
    Webhook,
)

from hone_music_video.errors import InvalidInput
from hone_music_video.project import Project

URL_ENV = "HONE_MV_NOTIFY_URL"
KIND_ENV = "HONE_MV_NOTIFY_KIND"
DASHBOARD_ENV = "HONE_MV_DASHBOARD_URL"
DASHBOARD = "http://localhost:8794"  # `hone-music-video dashboard`'s default port
EVENTS = ("run.awaiting_review", "run.failed", "run.completed")
# Telegram's Bot API `sendMessage` takes Slack's body (`{"text": ...}`) with `chat_id` in the URL (D-060)
KINDS: dict[str, type[Webhook]] = {
    "slack": SlackWebhook,
    "mattermost": MattermostWebhook,
    "telegram": SlackWebhook,
    "discord": DiscordWebhook,
    "http": HttpWebhook,
}


def _value(text: str) -> str:
    """A `.env` value: quoted taken as it is, unquoted up to a ` #` comment (as hone-models reads it)."""
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    return text.split(" #", 1)[0].rstrip()


def load_env_files() -> None:
    """This module's variables from `$HONE_ENV_FILE` and `./.env` when not set already (D-060)."""
    for name in (os.environ.get("HONE_ENV_FILE"), ".env"):
        if not name or not Path(name).is_file():
            continue
        for line in Path(name).read_text(encoding="utf-8").splitlines():
            key, sep, value = line.strip().removeprefix("export ").partition("=")
            if sep and key.strip() in (URL_ENV, KIND_ENV, DASHBOARD_ENV):
                os.environ.setdefault(key.strip(), _value(value.strip()))


def page(project: Project) -> str:
    """The project's page on the dashboard; `{` and `}` doubled, as hone-flow formats it as a template."""
    base = os.environ.get(DASHBOARD_ENV) or DASHBOARD
    link = f"{base.rstrip('/')}/#/p/{quote(project.id)}"
    return link.replace("{", "{{").replace("}", "}}")


def destinations(project: Project) -> list[Webhook]:
    """The webhook the run notifies, or none when `HONE_MV_NOTIFY_URL` is not set."""
    load_env_files()
    if not os.environ.get(URL_ENV):
        return []
    kind = (os.environ.get(KIND_ENV) or "slack").strip().lower()
    if kind not in KINDS:
        raise InvalidInput(f"{KIND_ENV}={kind!r} is not a notification kind; use one of {', '.join(KINDS)}")
    return [KINDS[kind](name="owner", url_env=URL_ENV, events=EVENTS, browse_url=page(project))]
