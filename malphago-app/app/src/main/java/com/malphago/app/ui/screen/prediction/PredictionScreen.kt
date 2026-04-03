package com.malphago.app.ui.screen.prediction

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.malphago.app.data.remote.dto.PredictionDto

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PredictionScreen(
    uiState: PredictionUiState = PredictionUiState(),
    onRunPrediction: (Int) -> Unit = {},
    onLoadPredictions: (Int) -> Unit = {},
    modifier: Modifier = Modifier,
) {
    var selectedRaceIndex by remember { mutableIntStateOf(0) }
    val raceLabels = (1..10).map { "${it}R" }

    Column(modifier = modifier.fillMaxSize()) {
        // 헤더
        Surface(tonalElevation = 2.dp) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "경주 예측",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                )
                FilledTonalButton(
                    onClick = { onRunPrediction(selectedRaceIndex + 1) },
                    enabled = !uiState.isLoading,
                ) {
                    if (uiState.isLoading) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(18.dp),
                            strokeWidth = 2.dp,
                        )
                    } else {
                        Icon(Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(18.dp))
                    }
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("예측 실행")
                }
            }
        }

        // 경주 선택 칩
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            raceLabels.take(5).forEachIndexed { index, label ->
                FilterChip(
                    selected = selectedRaceIndex == index,
                    onClick = {
                        selectedRaceIndex = index
                        onLoadPredictions(index + 1)
                    },
                    label = { Text(label) },
                )
            }
        }

        // 에러 표시
        uiState.error?.let { error ->
            Text(
                text = error,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        }

        // 예측 결과 리스트
        if (uiState.predictions.isEmpty() && !uiState.isLoading) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = "예측 실행 버튼을 눌러주세요",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        } else {
            LazyColumn(
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(uiState.predictions) { prediction ->
                    PredictionCard(prediction)
                }
            }
        }
    }
}

@Composable
private fun PredictionCard(prediction: PredictionDto) {
    val rankColor = when (prediction.predictedRank) {
        1 -> MaterialTheme.colorScheme.primary
        2 -> MaterialTheme.colorScheme.secondary
        3 -> MaterialTheme.colorScheme.tertiary
        else -> MaterialTheme.colorScheme.outline
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (prediction.predictedRank <= 3)
                MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f)
            else MaterialTheme.colorScheme.surface,
        ),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // 순위 뱃지
            Surface(
                shape = MaterialTheme.shapes.small,
                color = rankColor,
                modifier = Modifier.size(40.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(
                        text = "${prediction.predictedRank}",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimary,
                    )
                }
            }

            Spacer(modifier = Modifier.width(12.dp))

            // 정보
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "출주마 #${prediction.entryId}",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = "모델: ${prediction.modelVersion ?: "-"}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            // 점수
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = "${"%.1f".format(prediction.totalScore)}점",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = rankColor,
                )
                prediction.confidence?.let {
                    Text(
                        text = "신뢰도 ${it.toInt()}%",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }

        // 점수 바
        LinearProgressIndicator(
            progress = { (prediction.totalScore / 100).toFloat().coerceIn(0f, 1f) },
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .padding(bottom = 12.dp),
            color = rankColor,
            trackColor = MaterialTheme.colorScheme.surfaceVariant,
        )
    }
}
