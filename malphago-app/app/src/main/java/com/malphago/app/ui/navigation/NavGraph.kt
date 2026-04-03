package com.malphago.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.malphago.app.ui.screen.analysis.AnalysisScreen
import com.malphago.app.ui.screen.prediction.PredictionScreen
import com.malphago.app.ui.screen.raceday.RaceDayScreen
import com.malphago.app.ui.screen.settings.SettingsScreen

@Composable
fun NavGraph(navController: NavHostController, modifier: Modifier = Modifier) {
    NavHost(navController = navController, startDestination = BottomNavItem.RaceDay.route, modifier = modifier) {
        composable(BottomNavItem.RaceDay.route) { RaceDayScreen() }
        composable(BottomNavItem.Analysis.route) { AnalysisScreen() }
        composable(BottomNavItem.Prediction.route) { PredictionScreen() }
        composable(BottomNavItem.Settings.route) { SettingsScreen() }
    }
}
