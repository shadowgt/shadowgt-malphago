package com.malphago.app.ui.components

import android.content.Context
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.AdSize
import com.google.android.gms.ads.AdView

/**
 * AdMob 배너 광고 Composable
 *
 * 테스트 배너 ID 사용 중. 프로덕션에서 실제 광고 단위 ID로 교체 필요.
 */
@Composable
fun AdBanner(
    modifier: Modifier = Modifier,
    adUnitId: String = "ca-app-pub-3940256099942544/6300978111", // 테스트 배너 ID
) {
    AndroidView(
        modifier = modifier.fillMaxWidth(),
        factory = { context: Context ->
            AdView(context).apply {
                setAdSize(AdSize.BANNER)
                this.adUnitId = adUnitId
                loadAd(AdRequest.Builder().build())
            }
        },
    )
}
