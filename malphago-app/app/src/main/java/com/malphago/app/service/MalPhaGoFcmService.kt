package com.malphago.app.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.util.Log
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.malphago.app.MainActivity
import com.malphago.app.R

class MalPhaGoFcmService : FirebaseMessagingService() {

    companion object {
        private const val TAG = "MalPhaGoFCM"
        const val CHANNEL_CHANGES = "race_changes"
        const val CHANNEL_PREDICTIONS = "race_predictions"
    }

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.d(TAG, "FCM token refreshed: $token")
        // TODO: 서버에 토큰 등록 (POST /api/notifications/subscribe)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        Log.d(TAG, "FCM received from: ${message.from}")

        val data = message.data
        val changeType = data["change_type"] ?: ""
        val raceId = data["race_id"]
        val type = data["type"] ?: changeType

        // 알림 채널 결정
        val channelId = when {
            type == "prediction_ready" -> CHANNEL_PREDICTIONS
            else -> CHANNEL_CHANGES
        }

        // 알림 텍스트
        val title = message.notification?.title ?: getDefaultTitle(type)
        val body = message.notification?.body ?: getDefaultBody(data)

        showNotification(channelId, title, body, raceId)
    }

    private fun getDefaultTitle(type: String): String = when (type) {
        "jockey_change" -> "기수 변경"
        "horse_scratch" -> "출전 취소"
        "weight_change" -> "마체중 변경"
        "prediction_ready" -> "예측 업데이트"
        else -> "경주 알림"
    }

    private fun getDefaultBody(data: Map<String, String>): String {
        val horseName = data["horse_name"] ?: ""
        val raceNumber = data["race_number"] ?: ""
        return "$raceNumber R $horseName 변경사항이 있습니다."
    }

    private fun showNotification(
        channelId: String,
        title: String,
        body: String,
        raceId: String?,
    ) {
        createNotificationChannels()

        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            raceId?.let { putExtra("race_id", it) }
        }

        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE,
        )

        val notification = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(pendingIntent)
            .build()

        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(System.currentTimeMillis().toInt(), notification)
    }

    private fun createNotificationChannels() {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        val changesChannel = NotificationChannel(
            CHANNEL_CHANGES,
            "경주 변경 알림",
            NotificationManager.IMPORTANCE_HIGH,
        ).apply {
            description = "기수 변경, 출전 취소 등 경주 변경사항 알림"
        }

        val predictionsChannel = NotificationChannel(
            CHANNEL_PREDICTIONS,
            "예측 업데이트",
            NotificationManager.IMPORTANCE_DEFAULT,
        ).apply {
            description = "경주 예측 결과 업데이트 알림"
        }

        manager.createNotificationChannel(changesChannel)
        manager.createNotificationChannel(predictionsChannel)
    }
}
