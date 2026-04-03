"""SMS 예측 전송 서비스

경주일 예측 결과를 구독자에게 자동 문자 발송.
지원 프로바이더: 알리고 (aligo.in) SMS API.

사용 흐름:
1. 예측 실행 완료 후 호출
2. 구독자 목록 조회 (DB)
3. 예측 상위 3두 메시지 포맷팅
4. SMS API로 발송

환경변수:
- SMS_API_KEY: 알리고 API 키
- SMS_USER_ID: 알리고 사용자 ID
- SMS_SENDER: 발신번호
"""

import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

ALIGO_API_URL = "https://apis.aligo.in/send/"


@dataclass
class PredictionSms:
    """SMS 전송용 예측 결과"""
    track_name: str
    race_number: int
    predictions: list[dict]  # [{"rank": 1, "horse_name": "...", "score": 75.2}, ...]

    def format_message(self) -> str:
        """SMS 메시지 포맷 (90자 제한 고려)"""
        header = f"[말파고] {self.track_name} {self.race_number}R"
        lines = []
        for p in self.predictions[:3]:
            lines.append(f"{p['rank']}위 {p['horse_name']}({p['score']:.0f})")
        body = " / ".join(lines)
        return f"{header}\n{body}"


async def send_sms(phone: str, message: str) -> bool:
    """알리고 SMS API로 문자 발송

    Args:
        phone: 수신번호 (010-XXXX-XXXX 또는 01012345678)
        message: 메시지 내용

    Returns:
        성공 여부
    """
    if not settings.SMS_API_KEY or not settings.SMS_USER_ID:
        logger.info(f"[SMS-로그] → {phone}: {message}")
        return True

    payload = {
        "key": settings.SMS_API_KEY,
        "user_id": settings.SMS_USER_ID,
        "sender": settings.SMS_SENDER,
        "receiver": phone.replace("-", ""),
        "msg": message,
        "msg_type": "SMS" if len(message) <= 90 else "LMS",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(ALIGO_API_URL, data=payload, timeout=10.0)
            data = resp.json()
            if data.get("result_code") == "1":
                logger.info(f"SMS sent to {phone}")
                return True
            else:
                logger.error(f"SMS failed: {data.get('message')}")
                return False
    except Exception as e:
        logger.error(f"SMS send error: {e}")
        return False


async def send_prediction_sms(
    subscribers: list[str],
    prediction: PredictionSms,
) -> int:
    """구독자 전체에게 예측 SMS 발송

    Args:
        subscribers: 수신번호 리스트
        prediction: 예측 결과

    Returns:
        발송 성공 건수
    """
    message = prediction.format_message()
    sent = 0
    for phone in subscribers:
        if await send_sms(phone, message):
            sent += 1
    logger.info(f"SMS prediction sent: {sent}/{len(subscribers)}")
    return sent
