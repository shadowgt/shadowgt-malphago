package com.malphago.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.malphago.app.ui.screen.analysis.AnalysisScreen
import com.malphago.app.ui.screen.prediction.PredictionScreen
import com.malphago.app.ui.screen.prediction.PredictionViewModel
import com.malphago.app.ui.screen.raceday.RaceDayScreen
import com.malphago.app.ui.screen.raceday.RaceDayViewModel
import com.malphago.app.ui.screen.raceday.RaceDetailScreen
import com.malphago.app.ui.screen.settings.SettingsScreen

@Composable
fun NavGraph(navController: NavHostController, modifier: Modifier = Modifier) {
    NavHost(
        navController = navController,
        startDestination = BottomNavItem.RaceDay.route,
        modifier = modifier,
    ) {
        composable(BottomNavItem.RaceDay.route) {
            val viewModel: RaceDayViewModel = hiltViewModel()
            val uiState by viewModel.uiState.collectAsState()

            RaceDayScreen(
                uiState = uiState,
                onTrackSelect = viewModel::selectTrack,
                onRaceClick = { raceNo ->
                    navController.navigate("race_detail/$raceNo")
                },
                onRefresh = viewModel::refresh,
            )
        }

        composable(
            route = "race_detail/{raceNumber}",
            arguments = listOf(navArgument("raceNumber") { type = NavType.IntType }),
        ) { backStackEntry ->
            val raceNumber = backStackEntry.arguments?.getInt("raceNumber") ?: 1
            val viewModel: RaceDayViewModel = hiltViewModel(
                navController.getBackStackEntry(BottomNavItem.RaceDay.route),
            )
            val detailState by viewModel.detailState.collectAsState()

            RaceDetailScreen(
                raceNumber = raceNumber,
                detailState = detailState,
                onBack = { navController.popBackStack() },
            )
        }

        composable(BottomNavItem.Analysis.route) { AnalysisScreen() }

        composable(BottomNavItem.Prediction.route) {
            val viewModel: PredictionViewModel = hiltViewModel()
            val uiState by viewModel.uiState.collectAsState()

            PredictionScreen(
                uiState = uiState,
                onRunPrediction = viewModel::runPrediction,
                onLoadPredictions = viewModel::loadPredictions,
            )
        }

        composable(BottomNavItem.Settings.route) { SettingsScreen() }
    }
}
