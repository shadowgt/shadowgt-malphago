package com.malphago.app.ui.screen.analysis

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AnalysisScreen(modifier: Modifier = Modifier) {
    var selectedTab by remember { mutableIntStateOf(0) }
    val tabs = listOf("말 분석", "기수 분석", "시너지 분석")

    Column(modifier = modifier.fillMaxSize()) {
        // 탭
        TabRow(selectedTabIndex = selectedTab) {
            tabs.forEachIndexed { index, title ->
                Tab(
                    selected = selectedTab == index,
                    onClick = { selectedTab = index },
                    text = { Text(title) },
                )
            }
        }

        when (selectedTab) {
            0 -> HorseAnalysisTab()
            1 -> JockeyAnalysisTab()
            2 -> SynergyAnalysisTab()
        }
    }
}

@Composable
private fun HorseAnalysisTab() {
    val mockHorses = listOf(
        Triple("바람의검", "82-15-12-10", 18.3),
        Triple("천둥번개", "65-8-9-7", 12.3),
        Triple("금빛질주", "45-10-8-5", 22.2),
        Triple("하늘바람", "120-20-15-18", 16.7),
    )

    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        item {
            OutlinedTextField(
                value = "",
                onValueChange = {},
                placeholder = { Text("말 이름 검색") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            Spacer(modifier = Modifier.height(8.dp))
        }

        items(mockHorses.size) { index ->
            val (name, record, winRate) = mockHorses[index]
            StatCard(
                title = name,
                subtitle = "전적: $record",
                value = "${winRate}%",
                valueLabel = "승률",
            )
        }
    }
}

@Composable
private fun JockeyAnalysisTab() {
    val mockJockeys = listOf(
        Triple("문세영", "1500-250-200-180", 16.7),
        Triple("김성현", "1200-180-160-140", 15.0),
        Triple("이찬호", "900-120-110-95", 13.3),
        Triple("김동수", "800-100-90-80", 12.5),
    )

    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        item {
            OutlinedTextField(
                value = "",
                onValueChange = {},
                placeholder = { Text("기수 이름 검색") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            Spacer(modifier = Modifier.height(8.dp))
        }

        items(mockJockeys.size) { index ->
            val (name, record, winRate) = mockJockeys[index]
            StatCard(
                title = name,
                subtitle = "전적: $record",
                value = "${winRate}%",
                valueLabel = "승률",
            )
        }
    }
}

@Composable
private fun SynergyAnalysisTab() {
    val mockSynergies = listOf(
        SynergyItem("바람의검 + 문세영", 85.2, 72.1, 15.3),
        SynergyItem("천둥번개 + 김성현", 78.5, 65.3, 12.8),
        SynergyItem("금빛질주 + 이찬호", 71.0, 58.9, 18.5),
    )

    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        item {
            Text(
                "말-기수 시너지 분석",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            Spacer(modifier = Modifier.height(8.dp))
        }

        items(mockSynergies.size) { index ->
            val synergy = mockSynergies[index]
            SynergyCard(synergy)
        }
    }
}

private data class SynergyItem(
    val combo: String,
    val synergyScore: Double,
    val trainerRate: Double,
    val highDividendRate: Double,
)

@Composable
private fun SynergyCard(synergy: SynergyItem) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = synergy.combo,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
            )
            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                StatItem("시너지", "${synergy.synergyScore}%")
                StatItem("조교사 입상", "${synergy.trainerRate}%")
                StatItem("이변율", "${synergy.highDividendRate}%")
            }
        }
    }
}

@Composable
private fun StatItem(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = value,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary,
        )
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun StatCard(
    title: String,
    subtitle: String,
    value: String,
    valueLabel: String,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = value,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary,
                )
                Text(
                    text = valueLabel,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
