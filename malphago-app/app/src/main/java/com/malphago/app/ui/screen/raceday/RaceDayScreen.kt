package com.malphago.app.ui.screen.raceday

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
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RaceDayScreen(
    onRaceClick: (Int) -> Unit = {},
) {
    var selectedTrack by remember { mutableStateOf("S") }
    val tracks = listOf("S" to "서울", "B" to "부산", "J" to "제주")

    // 목업 경주 데이터
    val races = remember {
        (1..10).map { no ->
            RaceItem(
                raceNumber = no,
                level = "국${(no % 5) + 1}",
                distance = 1000 + no * 200,
                entries = 8 + no % 5,
                prizeMoney = "${(no * 500 + 2000)}만원",
            )
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("경주일") },
        )

        // 경마장 선택
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
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

        // 날짜 표시
        Text(
            text = "2026년 4월 4일 (토)",
            style = MaterialTheme.typography.titleMedium,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
        )

        // 경주 목록
        LazyColumn(
            modifier = Modifier.padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(races) { race ->
                RaceListCard(race = race, onClick = { onRaceClick(race.raceNumber) })
            }
            item { Spacer(modifier = Modifier.height(16.dp)) }
        }
    }
}

data class RaceItem(
    val raceNumber: Int,
    val level: String,
    val distance: Int,
    val entries: Int,
    val prizeMoney: String,
)

@Composable
private fun RaceListCard(race: RaceItem, onClick: () -> Unit) {
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
            // 왼쪽: 회차 + 등급/거리
            Row(
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "${race.raceNumber}R",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary,
                )
                Column {
                    Text(
                        text = "${race.level} · ${race.distance}m",
                        style = MaterialTheme.typography.titleMedium,
                    )
                    Text(
                        text = "${race.entries}두 출주",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            // 오른쪽: 상금
            Text(
                text = race.prizeMoney,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.tertiary,
                fontWeight = FontWeight.SemiBold,
            )
        }
    }
}
