package com.malphago.app.ui.screen.raceday

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.malphago.app.data.local.entity.RaceEntity
import com.malphago.app.data.local.entity.RaceEntryEntity
import com.malphago.app.data.repository.RaceRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import javax.inject.Inject

data class RaceDayUiState(
    val selectedTrack: String = "S",
    val selectedDate: String = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd")),
    val races: List<RaceEntity> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
)

data class RaceDetailUiState(
    val raceNumber: Int = 0,
    val entries: List<RaceEntryEntity> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class RaceDayViewModel @Inject constructor(
    private val repository: RaceRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(RaceDayUiState())
    val uiState: StateFlow<RaceDayUiState> = _uiState.asStateFlow()

    private val _detailState = MutableStateFlow(RaceDetailUiState())
    val detailState: StateFlow<RaceDetailUiState> = _detailState.asStateFlow()

    init {
        loadRaces()
    }

    fun selectTrack(trackCode: String) {
        _uiState.value = _uiState.value.copy(selectedTrack = trackCode)
        loadRaces()
    }

    fun selectDate(date: String) {
        _uiState.value = _uiState.value.copy(selectedDate = date)
        loadRaces()
    }

    fun loadRaces() {
        val state = _uiState.value
        viewModelScope.launch {
            _uiState.value = state.copy(isLoading = true)
            try {
                // 서버에서 동기화
                repository.syncRaces(state.selectedTrack, state.selectedDate)
            } catch (e: Exception) {
                // 오프라인: 로컬 캐시에서 로드
            }

            // Room DB에서 Flow로 관찰
            repository.getRacesByTrackAndDate(state.selectedTrack, state.selectedDate)
                .collect { races ->
                    _uiState.value = _uiState.value.copy(
                        races = races,
                        isLoading = false,
                        error = null,
                    )
                }
        }
    }

    fun loadEntries(raceId: Int, raceNumber: Int) {
        _detailState.value = RaceDetailUiState(raceNumber = raceNumber, isLoading = true)
        viewModelScope.launch {
            try {
                repository.syncEntries(raceId)
            } catch (_: Exception) { }

            repository.getEntriesByRace(raceId).collect { entries ->
                _detailState.value = _detailState.value.copy(
                    entries = entries,
                    isLoading = false,
                )
            }
        }
    }

    fun refresh() {
        loadRaces()
    }
}
