package com.malphago.app.service

import android.util.Log
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.tasks.await

/**
 * FCM 토픽 구독 관리
 *
 * 토픽:
 * - "race_changes": 기수/말 변경 알림
 * - "race_predictions": 예측 결과 업데이트
 */
object FcmManager {

    private const val TAG = "FcmManager"
    const val TOPIC_CHANGES = "race_changes"
    const val TOPIC_PREDICTIONS = "race_predictions"

    suspend fun subscribeToChanges() {
        try {
            FirebaseMessaging.getInstance().subscribeToTopic(TOPIC_CHANGES).await()
            Log.d(TAG, "Subscribed to $TOPIC_CHANGES")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to subscribe to $TOPIC_CHANGES", e)
        }
    }

    suspend fun subscribeToPredictions() {
        try {
            FirebaseMessaging.getInstance().subscribeToTopic(TOPIC_PREDICTIONS).await()
            Log.d(TAG, "Subscribed to $TOPIC_PREDICTIONS")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to subscribe to $TOPIC_PREDICTIONS", e)
        }
    }

    suspend fun unsubscribeFromChanges() {
        try {
            FirebaseMessaging.getInstance().unsubscribeFromTopic(TOPIC_CHANGES).await()
            Log.d(TAG, "Unsubscribed from $TOPIC_CHANGES")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to unsubscribe from $TOPIC_CHANGES", e)
        }
    }

    suspend fun getToken(): String? {
        return try {
            FirebaseMessaging.getInstance().token.await()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get FCM token", e)
            null
        }
    }
}
