package com.malphago.app.ui.screen.prediction

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.malphago.app.data.remote.dto.PredictionDto
import com.malphago.app.data.repository.RaceRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class PredictionUiState(
    val predictions: List<PredictionDto> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
    val selectedRaceId: Int? = null,
)

@HiltViewModel
class PredictionViewModel @Inject constructor(
    private val repository: RaceRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(PredictionUiState())
    val uiState: StateFlow<PredictionUiState> = _uiState.asStateFlow()

    fun loadPredictions(raceId: Int) {
        _uiState.value = _uiState.value.copy(isLoading = true, selectedRaceId = raceId)
        viewModelScope.launch {
            try {
                val predictions = repository.getPredictions(raceId)
                _uiState.value = _uiState.value.copy(
                    predictions = predictions,
                    isLoading = false,
                    error = null,
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message,
                )
            }
        }
    }

    fun runPrediction(raceId: Int) {
        _uiState.value = _uiState.value.copy(isLoading = true)
        viewModelScope.launch {
            try {
                repository.runPrediction(raceId)
                loadPredictions(raceId)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message,
                )
            }
        }
    }
}
