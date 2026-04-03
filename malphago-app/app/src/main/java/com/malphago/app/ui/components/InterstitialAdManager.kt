package com.malphago.app.ui.components

import android.app.Activity
import android.content.Context
import android.util.Log
import com.google.android.gms.ads.AdError
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.FullScreenContentCallback
import com.google.android.gms.ads.LoadAdError
import com.google.android.gms.ads.interstitial.InterstitialAd
import com.google.android.gms.ads.interstitial.InterstitialAdLoadCallback

/**
 * 인터스티셜 광고 관리자
 *
 * 사용 시나리오: 경주 예측 결과 조회 후 표시
 * 테스트 광고 단위 ID 사용 중.
 */
object InterstitialAdManager {

    private const val TAG = "InterstitialAd"
    // 테스트 인터스티셜 ID — 프로덕션에서 실제 ID로 교체
    private const val TEST_AD_UNIT_ID = "ca-app-pub-3940256099942544/1033173712"

    private var interstitialAd: InterstitialAd? = null
    private var isLoading = false

    fun load(context: Context, adUnitId: String = TEST_AD_UNIT_ID) {
        if (isLoading || interstitialAd != null) return
        isLoading = true

        InterstitialAd.load(
            context,
            adUnitId,
            AdRequest.Builder().build(),
            object : InterstitialAdLoadCallback() {
                override fun onAdLoaded(ad: InterstitialAd) {
                    interstitialAd = ad
                    isLoading = false
                    Log.d(TAG, "Interstitial loaded")
                }

                override fun onAdFailedToLoad(error: LoadAdError) {
                    interstitialAd = null
                    isLoading = false
                    Log.e(TAG, "Interstitial failed: ${error.message}")
                }
            },
        )
    }

    fun show(activity: Activity, onDismissed: () -> Unit = {}) {
        val ad = interstitialAd
        if (ad == null) {
            onDismissed()
            return
        }

        ad.fullScreenContentCallback = object : FullScreenContentCallback() {
            override fun onAdDismissedFullScreenContent() {
                interstitialAd = null
                onDismissed()
                // 다음 광고 미리 로드
                load(activity)
            }

            override fun onAdFailedToShowFullScreenContent(error: AdError) {
                interstitialAd = null
                onDismissed()
            }
        }

        ad.show(activity)
    }

    fun isReady(): Boolean = interstitialAd != null
}
