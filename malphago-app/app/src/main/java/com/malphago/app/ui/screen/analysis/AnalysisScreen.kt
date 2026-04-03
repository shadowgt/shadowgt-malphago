package com.malphago.app.ui.screen.analysis

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.malphago.app.data.remote.dto.DistanceBreakdownDto
import com.malphago.app.data.remote.dto.HorseStatsDto
import com.malphago.app.data.remote.dto.JockeyStatsDto
import com.patrykandpatrick.vico.compose.cartesian.CartesianChartHost
import com.patrykandpatrick.vico.compose.cartesian.axis.rememberBottom
import com.patrykandpatrick.vico.compose.cartesian.axis.rememberStart
import com.patrykandpatrick.vico.compose.cartesian.layer.rememberColumnCartesianLayer
import com.patrykandpatrick.vico.compose.cartesian.rememberCartesianChart
import com.patrykandpatrick.vico.core.cartesian.axis.HorizontalAxis
import com.patrykandpatrick.vico.core.cartesian.axis.VerticalAxis
import com.patrykandpatrick.vico.core.cartesian.data.CartesianChartModelProducer
import com.patrykandpatrick.vico.core.cartesian.data.columnSeries

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AnalysisScreen(
    modifier: Modifier = Modifier,
    viewModel: AnalysisViewModel = hiltViewModel(),
) {
    var selectedTab by remember { mutableIntStateOf(0) }
    val tabs = listOf("말 분석", "기수 분석", "시너지 분석")
    val uiState by viewModel.uiState.collectAsState()

    Column(modifier = modifier.fillMaxSize()) {
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
            0 -> HorseAnalysisTab(
                stats = uiState.horseStats,
                isLoading = uiState.isLoading,
                onSearch = { viewModel.loadHorseStats(it) },
            )
            1 -> JockeyAnalysisTab(
                stats = uiState.jockeyStats,
                isLoading = uiState.isLoading,
                onSearch = { viewModel.loadJockeyStats(it) },
            )
            2 -> SynergyAnalysisTab()
        }
    }
}

@Composable
private fun HorseAnalysisTab(
    stats: HorseStatsDto?,
    isLoading: Boolean,
    onSearch: (Int) -> Unit,
) {
    var searchId by remember { mutableStateOf("") }

    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = searchId,
                    onValueChange = { searchId = it },
                    placeholder = { Text("말 ID 입력") },
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                )
                Spacer(modifier = Modifier.width(8.dp))
                Button(onClick = { searchId.toIntOrNull()?.let(onSearch) }) {
                    Text("검색")
                }
            }
        }

        if (isLoading) {
            item {
                Box(
                    modifier = Modifier.fillMaxWidth().padding(32.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator()
                }
            }
        }

        stats?.let { horse ->
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = horse.name ?: "Unknown",
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold,
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                            horse.origin?.let { InfoChip("산지: $it") }
                            horse.gender?.let { InfoChip("성별: $it") }
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceEvenly,
                        ) {
                            StatItem("전적", horse.totalRecord ?: "-")
                            StatItem("승률", "${horse.winRate ?: 0}%")
                            StatItem("입상률", "${horse.top3Rate ?: 0}%")
                        }
                    }
                }
            }

            // 거리별 성적 차트
            horse.distanceBreakdown?.let { breakdown ->
                if (breakdown.isNotEmpty()) {
                    item {
                        Text(
                            "거리별 성적",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(top = 8.dp),
                        )
                    }
                    item {
                        DistanceBarChart(breakdown)
                    }
                }
            }

            // 최근 경주
            horse.recentRaces?.let { races ->
                if (races.isNotEmpty()) {
                    item {
                        Text(
                            "최근 경주",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(top = 8.dp),
                        )
                    }
                    items(races.size) { i ->
                        val race = races[i]
                        Card(modifier = Modifier.fillMaxWidth()) {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(12.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Text(race.raceDate ?: "-", style = MaterialTheme.typography.bodyMedium)
                                Text("${race.distance ?: "-"}m", style = MaterialTheme.typography.bodyMedium)
                                Text(
                                    "${race.ranking ?: "-"}착",
                                    style = MaterialTheme.typography.bodyMedium,
                                    fontWeight = FontWeight.Bold,
                                    color = when (race.ranking) {
                                        1 -> Color(0xFFFFD700)
                                        2 -> Color(0xFFC0C0C0)
                                        3 -> Color(0xFFCD7F32)
                                        else -> MaterialTheme.colorScheme.onSurface
                                    },
                                )
                                Text("${race.oddsWin ?: "-"}배", style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun DistanceBarChart(breakdown: List<DistanceBreakdownDto>) {
    val modelProducer = remember { CartesianChartModelProducer() }

    LaunchedEffect(breakdown) {
        modelProducer.runTransaction {
            columnSeries {
                series(breakdown.map { it.winRate ?: 0.0 })
            }
        }
    }

    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            CartesianChartHost(
                chart = rememberCartesianChart(
                    rememberColumnCartesianLayer(),
                    startAxis = VerticalAxis.rememberStart(),
                    bottomAxis = HorizontalAxis.rememberBottom(),
                ),
                modelProducer = modelProducer,
                modifier = Modifier.fillMaxWidth().height(200.dp),
            )
            Spacer(modifier = Modifier.height(4.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly,
            ) {
                breakdown.forEach { d ->
                    Text(
                        "${d.distance ?: "?"}m",
                        style = MaterialTheme.typography.labelSmall,
                    )
                }
            }
        }
    }
}

@Composable
private fun JockeyAnalysisTab(
    stats: JockeyStatsDto?,
    isLoading: Boolean,
    onSearch: (Int) -> Unit,
) {
    var searchId by remember { mutableStateOf("") }

    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = searchId,
                    onValueChange = { searchId = it },
                    placeholder = { Text("기수 ID 입력") },
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                )
                Spacer(modifier = Modifier.width(8.dp))
                Button(onClick = { searchId.toIntOrNull()?.let(onSearch) }) {
                    Text("검색")
                }
            }
        }

        if (isLoading) {
            item {
                Box(
                    modifier = Modifier.fillMaxWidth().padding(32.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator()
                }
            }
        }

        stats?.let { jockey ->
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = jockey.name ?: "Unknown",
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold,
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceEvenly,
                        ) {
                            StatItem("전적", jockey.totalRecord ?: "-")
                            StatItem("승률", "${jockey.winRate ?: 0}%")
                            StatItem("입상률", "${jockey.top3Rate ?: 0}%")
                            StatItem("최근폼", "${jockey.recent30Form ?: 0}%")
                        }
                    }
                }
            }

            // 거리별 성적 차트
            jockey.distanceBreakdown?.let { breakdown ->
                if (breakdown.isNotEmpty()) {
                    item {
                        Text(
                            "거리별 성적",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(top = 8.dp),
                        )
                    }
                    item {
                        DistanceBarChart(breakdown)
                    }
                }
            }

            // 트랙별 성적
            jockey.trackBreakdown?.let { tracks ->
                if (tracks.isNotEmpty()) {
                    item {
                        Text(
                            "트랙별 성적",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(top = 8.dp),
                        )
                    }
                    items(tracks.size) { i ->
                        val t = tracks[i]
                        Card(modifier = Modifier.fillMaxWidth()) {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(12.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Text("트랙 ${t.track ?: "-"}")
                                Text("${t.runs ?: 0}전 ${t.wins ?: 0}승")
                                Text(
                                    "승률 ${t.winRate ?: 0}%",
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary,
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SynergyAnalysisTab() {
    Box(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            "경주 상세에서 시너지 분석을 확인하세요.",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun InfoChip(text: String) {
    Surface(
        color = MaterialTheme.colorScheme.secondaryContainer,
        shape = MaterialTheme.shapes.small,
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            style = MaterialTheme.typography.labelMedium,
        )
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
