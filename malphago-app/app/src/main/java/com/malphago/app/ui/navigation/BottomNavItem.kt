package com.malphago.app.ui.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.QueryStats
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.ui.graphics.vector.ImageVector

sealed class BottomNavItem(
    val route: String,
    val label: String,
    val icon: ImageVector,
) {
    data object RaceDay : BottomNavItem("raceday", "경주일", Icons.Default.DateRange)
    data object Analysis : BottomNavItem("analysis", "분석", Icons.Default.QueryStats)
    data object Prediction : BottomNavItem("prediction", "예측", Icons.Default.TrendingUp)
    data object Settings : BottomNavItem("settings", "설정", Icons.Default.Settings)
}
