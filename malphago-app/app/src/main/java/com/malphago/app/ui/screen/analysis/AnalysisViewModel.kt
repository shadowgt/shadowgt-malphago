package com.malphago.app.ui.screen.analysis

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.malphago.app.data.remote.api.MalPhaGoApi
import com.malphago.app.data.remote.dto.HorseStatsDto
import com.malphago.app.data.remote.dto.JockeyStatsDto
import com.malphago.app.data.remote.dto.SynergyDto
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AnalysisUiState(
    val horseStats: HorseStatsDto? = null,
    val jockeyStats: JockeyStatsDto? = null,
    val synergies: List<SynergyDto> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class AnalysisViewModel @Inject constructor(
    private val api: MalPhaGoApi,
) : ViewModel() {

    private val _uiState = MutableStateFlow(AnalysisUiState())
    val uiState: StateFlow<AnalysisUiState> = _uiState.asStateFlow()

    fun loadHorseStats(horseId: Int) {
        _uiState.value = _uiState.value.copy(isLoading = true, error = null)
        viewModelScope.launch {
            try {
                val stats = api.getHorseStats(horseId)
                _uiState.value = _uiState.value.copy(
                    horseStats = stats,
                    isLoading = false,
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message,
                )
            }
        }
    }

    fun loadJockeyStats(jockeyId: Int) {
        _uiState.value = _uiState.value.copy(isLoading = true, error = null)
        viewModelScope.launch {
            try {
                val stats = api.getJockeyStats(jockeyId)
                _uiState.value = _uiState.value.copy(
                    jockeyStats = stats,
                    isLoading = false,
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message,
                )
            }
        }
    }

    fun loadRaceSynergies(raceId: Int) {
        _uiState.value = _uiState.value.copy(isLoading = true, error = null)
        viewModelScope.launch {
            try {
                val synergies = api.getRaceSynergies(raceId)
                _uiState.value = _uiState.value.copy(
                    synergies = synergies,
                    isLoading = false,
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message,
                )
            }
        }
    }
}
