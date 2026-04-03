package com.malphago.app.data.worker

import android.content.Context
import android.util.Log
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.malphago.app.data.repository.RaceRepository
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.time.LocalDate
import java.time.format.DateTimeFormatter

/**
 * 백그라운드 동기화 Worker.
 * 주기적으로 서버에서 경주 데이터를 가져와 Room DB에 캐싱.
 */
@HiltWorker
class SyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val repository: RaceRepository,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            val today = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd"))
            val tracks = listOf("S", "B")

            for (track in tracks) {
                try {
                    repository.syncRaces(track, today)
                    Log.d(TAG, "Synced races for $track $today")
                } catch (e: Exception) {
                    Log.w(TAG, "Failed to sync $track: ${e.message}")
                }
            }

            // 오래된 데이터 삭제 (7일 이전)
            val cutoff = LocalDate.now().minusDays(7).format(DateTimeFormatter.ofPattern("yyyy-MM-dd"))
            repository.deleteOldRaces(cutoff)

            Result.success()
        } catch (e: Exception) {
            Log.e(TAG, "Sync failed", e)
            Result.retry()
        }
    }

    companion object {
        const val TAG = "SyncWorker"
        const val WORK_NAME = "malphago_sync"
    }
}
