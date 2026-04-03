"""변경 알림 서비스

기수/말 변경 감지 시 FCM 푸시 알림을 발송한다.
FCM HTTP v1 API 사용 (google-auth 기반).
FCM_SERVER_KEY가 없으면 로그 모드로 동작.

알림 흐름:
1. crawl_storage.save_race_card()에서 변경 감지
2. EntryChangeLog에 기록
3. notify_entry_change() 호출 → FCM 발송 (또는 로그)
"""

import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# FCM v1 API endpoint
FCM_V1_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"


@dataclass
class ChangeNotification:
    """변경 알림 데이터"""
    race_id: int
    race_number: int
    track_name: str
    change_type: str  # jockey_change, horse_scratch, weight_change
    horse_name: str
    old_value: str
    new_value: str
    message: str = ""

    def build_message(self) -> str:
        if self.change_type == "jockey_change":
            return (
                f"{self.track_name} {self.race_number}R 기수 변경: "
                f"{self.old_value} → {self.new_value} (말: {self.horse_name})"
            )
        elif self.change_type == "horse_scratch":
            return (
                f"{self.track_name} {self.race_number}R 출전취소: "
                f"{self.horse_name}"
            )
        elif self.change_type == "weight_change":
            return (
                f"{self.track_name} {self.race_number}R 마체중 변경: "
                f"{self.horse_name} {self.old_value}→{self.new_value}kg"
            )
        return f"{self.track_name} {self.race_number}R 변경: {self.horse_name}"


async def notify_entry_change(notification: ChangeNotification) -> bool:
    """변경 알림 발송

    FCM_SERVER_KEY가 설정되면 FCM 푸시 알림 발송.
    미설정 시 로그만 출력.
    """
    msg = notification.build_message()
    notification.message = msg

    if not settings.FCM_SERVER_KEY:
        logger.info(f"[알림-로그] {msg}")
        return True

    return await _send_fcm_topic(
        topic="race_changes",
        title="출전 변경",
        body=msg,
        data={
            "race_id": str(notification.race_id),
            "race_number": str(notification.race_number),
            "change_type": notification.change_type,
            "horse_name": notification.horse_name,
        },
    )


async def notify_prediction_ready(race_id: int, race_number: int, track_name: str) -> bool:
    """예측 완료 알림"""
    msg = f"{track_name} {race_number}R 예측 결과가 업데이트되었습니다."

    if not settings.FCM_SERVER_KEY:
        logger.info(f"[알림-로그] {msg}")
        return True

    return await _send_fcm_topic(
        topic="race_predictions",
        title="예측 업데이트",
        body=msg,
        data={"race_id": str(race_id), "type": "prediction_ready"},
    )


async def _send_fcm_topic(
    topic: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> bool:
    """FCM Legacy HTTP API 토픽 메시지 발송

    FCM_SERVER_KEY = Legacy server key (프로젝트 설정 > Cloud Messaging)
    프로덕션에서는 FCM HTTP v1 API + 서비스 계정으로 전환 권장.
    """
    url = "https://fcm.googleapis.com/fcm/send"
    headers = {
        "Authorization": f"key={settings.FCM_SERVER_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": f"/topics/{topic}",
        "notification": {
            "title": title,
            "body": body,
            "sound": "default",
        },
        "data": data or {},
        "android": {
            "priority": "high",
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                logger.info(f"FCM sent: {topic} — {title}")
                return True
            else:
                logger.error(f"FCM error {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        logger.error(f"FCM send failed: {e}")
        return False


async def notify_batch_changes(notifications: list[ChangeNotification]) -> int:
    """여러 변경 알림 일괄 발송"""
    sent = 0
    for n in notifications:
        if await notify_entry_change(n):
            sent += 1
    return sent
