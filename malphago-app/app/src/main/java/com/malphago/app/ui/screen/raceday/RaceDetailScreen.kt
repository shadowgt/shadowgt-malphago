package com.malphago.app.ui.screen.raceday

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RaceDetailScreen(
    raceNumber: Int,
    onBack: () -> Unit = {},
    onEntryClick: (Int) -> Unit = {},
) {
    // 목업 출주표 데이터
    val entries = remember {
        listOf(
            EntryMock(1, "번개호", "김동수", "이영호", 72, 452, 2, 87.3),
            EntryMock(2, "질풍이", "박재현", "김수일", 68, 468, 1, 82.1),
            EntryMock(3, "드림윈", "이상현", "박종태", 65, 445, 5, 78.9),
            EntryMock(4, "스피드킹", "김성현", "최영식", 70, 460, 3, 76.5),
            EntryMock(5, "바람의검", "문세영", "이영호", 63, 440, 4, 74.2),
            EntryMock(6, "천둥이", "김용근", "정성우", 60, 455, 6, 71.8),
            EntryMock(7, "골든스타", "유현명", "박종태", 58, 448, 7, 68.4),
            EntryMock(8, "파워런", "이호성", "김수일", 55, 470, 8, 65.1),
        )
    }

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("${raceNumber}R 경주 상세") },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, "뒤로")
                }
            },
        )

        LazyColumn(
            modifier = Modifier.padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            // 경주 정보 헤더
            item {
                RaceInfoHeader(raceNumber = raceNumber)
            }

            // 예측 실행 + 기수 변경 버튼
            item {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    FilledTonalButton(
                        onClick = { /* 예측 실행 */ },
                        modifier = Modifier.weight(1f),
                    ) {
                        Icon(Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("예측 실행")
                    }
                    OutlinedButton(
                        onClick = { /* 기수 변경 시뮬레이션 */ },
                        modifier = Modifier.weight(1f),
                    ) {
                        Icon(Icons.Default.SwapHoriz, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("기수 변경")
                    }
                }
            }

            // 출주표 헤더
            item {
                Text(
                    text = "출주표",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(top = 8.dp),
                )
            }

            // 출주마 목록
            items(entries) { entry ->
                EntryCard(entry = entry, onClick = { onEntryClick(entry.horseNumber) })
            }

            item { Spacer(modifier = Modifier.height(16.dp)) }
        }
    }
}

data class EntryMock(
    val horseNumber: Int,
    val horseName: String,
    val jockeyName: String,
    val trainerName: String,
    val rating: Int,
    val horseWeight: Int,
    val favorRanking: Int,
    val predictionScore: Double,
)

@Composable
private fun RaceInfoHeader(raceNumber: Int) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "${raceNumber}R · 국3 · 1400m",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
            )
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                InfoLabel(label = "날씨", value = "맑음")
                InfoLabel(label = "주로", value = "건조")
                InfoLabel(label = "출주", value = "8두")
                InfoLabel(label = "상금", value = "4500만원")
            }
        }
    }
}

@Composable
private fun InfoLabel(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

@Composable
private fun EntryCard(entry: EntryMock, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        onClick = onClick,
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // 마번
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.primary),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = "${entry.horseNumber}",
                    color = MaterialTheme.colorScheme.onPrimary,
                    fontWeight = FontWeight.Bold,
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            // 마명 + 기수/조교사
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = entry.horseName,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = "${entry.jockeyName} / ${entry.trainerName}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        text = "R${entry.rating}",
                        style = MaterialTheme.typography.bodySmall,
                    )
                    Text(
                        text = "${entry.horseWeight}kg",
                        style = MaterialTheme.typography.bodySmall,
                    )
                    Text(
                        text = "인기${entry.favorRanking}",
                        style = MaterialTheme.typography.bodySmall,
                        color = if (entry.favorRanking <= 3) {
                            MaterialTheme.colorScheme.tertiary
                        } else {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        },
                    )
                }
            }

            // 예측 점수
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = "${entry.predictionScore}",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary,
                )
                Text(
                    text = "예측점수",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
