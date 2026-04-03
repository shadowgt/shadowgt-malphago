package com.malphago.app.ui.screen.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@Composable
fun DashboardScreen(
    onRaceClick: (Int) -> Unit = {},
) {
    var selectedTrack by remember { mutableStateOf("S") }
    val tracks = listOf("S" to "서울", "B" to "부산", "J" to "제주")

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        // 헤더
        item {
            Text(
                text = "말파고",
                style = MaterialTheme.typography.headlineLarge,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = "AI 경마 예측",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(modifier = Modifier.height(8.dp))
        }

        // 경마장 선택 칩
        item {
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                tracks.forEach { (code, name) ->
                    FilterChip(
                        selected = selectedTrack == code,
                        onClick = { selectedTrack = code },
                        label = { Text(name) },
                    )
                }
            }
        }

        // 다음 경주 카드
        item {
            NextRaceCard(trackName = tracks.first { it.first == selectedTrack }.second)
        }

        // 오늘 경주 목록 (목업 데이터)
        item {
            Text(
                text = "오늘의 경주",
                style = MaterialTheme.typography.titleLarge,
                modifier = Modifier.padding(top = 8.dp),
            )
        }

        items((1..10).toList()) { raceNo ->
            RaceCardItem(
                raceNumber = raceNo,
                trackCode = selectedTrack,
                onClick = { onRaceClick(raceNo) },
            )
        }
    }
}

@Composable
private fun NextRaceCard(trackName: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer,
        ),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "다음 경주",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onPrimaryContainer,
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "$trackName 3R · 1400m · 국3",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                PredictionChip(rank = 1, horseName = "번개호", score = 87.3)
                PredictionChip(rank = 2, horseName = "질풍이", score = 82.1)
                PredictionChip(rank = 3, horseName = "드림윈", score = 78.9)
            }
        }
    }
}

@Composable
private fun PredictionChip(rank: Int, horseName: String, score: Double) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = "${rank}위",
            style = MaterialTheme.typography.labelLarge,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary,
        )
        Text(text = horseName, style = MaterialTheme.typography.bodyMedium)
        Text(
            text = "$score",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun RaceCardItem(
    raceNumber: Int,
    trackCode: String,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        onClick = onClick,
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column {
                Text(
                    text = "${raceNumber}R",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = "국${(raceNumber % 5) + 1} · ${1000 + raceNumber * 200}m",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = "${8 + raceNumber}두 출주",
                    style = MaterialTheme.typography.bodyMedium,
                )
                Text(
                    text = "14:${String.format("%02d", raceNumber * 5)} 출발",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
