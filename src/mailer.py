from __future__ import annotations

import logging
import smtplib
from datetime import date
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr

logger = logging.getLogger(__name__)


def build_daily_mail_text(cards: list[dict], site_url: str) -> str:
    lines = []
    lines.append("ArxivFilter Daily Digest")
    lines.append("")

    if not cards:
        lines.append("今日没有新增可展示文章。")
        return "\n".join(lines).strip()

    lines.append(f"今日新增文章：{len(cards)} 篇")
    lines.append(f"已同步至：{site_url}")
    lines.append("")
    for idx, card in enumerate(cards, start=1):
        lines.extend(
            [
                f"{idx}. [{card['tag']}] {card['id']}",
                f"原标题: {card['title_en']}",
                f"中文标题: {card['title_zh']}",
                f"作者: {card['authors_full']}",
                f"AI摘要: {card['ai_abstract']}",
                f"{card['abs_url']}",
                f"{card['abs_url'].replace('abs', 'pdf')}",
                f"{card['abs_url'].replace('abs', 'html')}",
                f"{card['abs_url'].replace('arxiv.org', 'alphaxiv.org')}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def send_plain_email(
    *,
    title: str,
    text: str,
    mail_cfg: dict,
    sender_name: str = "ArxivFilter",
) -> None:
    logger.info("Preparing email: %s", title)

    if mail_cfg.get("dryrun", True):
        logger.info("Mail dryrun enabled. Skip sending.")
        logger.info("Mail content:\n%s", text)
        return

    message = MIMEText(text, "plain", "utf-8")
    message["From"] = formataddr((sender_name, mail_cfg["user"]))
    message["To"] = mail_cfg["receiver"]
    message["Subject"] = Header(title, "utf-8")

    with smtplib.SMTP_SSL(mail_cfg["host"], int(mail_cfg["port"])) as smtp:
        smtp.login(mail_cfg["user"], mail_cfg["password"])
        smtp.sendmail(mail_cfg["user"], [mail_cfg["receiver"]], message.as_string())
    logger.info("Email sent to %s", mail_cfg["receiver"])


def send_daily_digest(cards: list[dict], mail_cfg: dict, site_url: str) -> None:
    title = f"ArxivFilter {date.today().isoformat()} Daily Digest"
    text = build_daily_mail_text(cards, site_url)
    send_plain_email(title=title, text=text, mail_cfg=mail_cfg, sender_name="ArxivFilter")
