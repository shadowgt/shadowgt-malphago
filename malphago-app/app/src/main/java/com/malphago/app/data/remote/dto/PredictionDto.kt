package com.malphago.app.data.remote.dto

import com.google.gson.annotations.SerializedName

data class PredictionDto(
    @SerializedName("entry_id") val entryId: Int,
    @SerializedName("total_score") val totalScore: Double,
    @SerializedName("predicted_rank") val predictedRank: Int,
    val confidence: Double?,
    val factors: String?,
    @SerializedName("model_version") val modelVersion: String?,
    @SerializedName("actual_rank") val actualRank: Int?,
)

data class SynergyDto(
    @SerializedName("jockey_name") val jockeyName: String?,
    @SerializedName("trainer_name") val trainerName: String?,
    @SerializedName("horse_name") val horseName: String?,
    @SerializedName("best_record_rate") val bestRecordRate: Double?,
    @SerializedName("best_record_trainer_rate") val bestRecordTrainerRate: Double?,
    @SerializedName("high_dividend_record_rate") val highDividendRecordRate: Double?,
    @SerializedName("high_dividend_record_trainer_rate") val highDividendRecordTrainerRate: Double?,
    @SerializedName("horse_jockey_synergy_rate") val horseJockeySynergyRate: Double?,
    @SerializedName("horse_jockey_total_runs") val horseJockeyTotalRuns: Int?,
    @SerializedName("trainer_win_rate") val trainerWinRate: Double?,
    @SerializedName("jockey_total_runs") val jockeyTotalRuns: Int?,
)

data class DistanceBreakdownDto(
    val distance: String?,
    val runs: Int?,
    val wins: Int?,
    val top3: Int?,
    @SerializedName("win_rate") val winRate: Double?,
)

data class HorseStatsDto(
    @SerializedName("horse_id") val horseId: Int,
    val name: String?,
    val origin: String?,
    val gender: String?,
    @SerializedName("total_record") val totalRecord: String?,
    @SerializedName("win_rate") val winRate: Double?,
    @SerializedName("top3_rate") val top3Rate: Double?,
    @SerializedName("distance_breakdown") val distanceBreakdown: List<DistanceBreakdownDto>?,
    @SerializedName("recent_races") val recentRaces: List<RecentRaceDto>?,
)

data class RecentRaceDto(
    @SerializedName("race_date") val raceDate: String?,
    @SerializedName("race_number") val raceNumber: Int?,
    val distance: Int?,
    val ranking: Int?,
    @SerializedName("horse_weight") val horseWeight: Int?,
    @SerializedName("odds_win") val oddsWin: Double?,
)

data class TrackBreakdownDto(
    val track: String?,
    val runs: Int?,
    val wins: Int?,
    @SerializedName("win_rate") val winRate: Double?,
)

data class JockeyStatsDto(
    @SerializedName("jockey_id") val jockeyId: Int,
    val name: String?,
    @SerializedName("total_record") val totalRecord: String?,
    @SerializedName("win_rate") val winRate: Double?,
    @SerializedName("top3_rate") val top3Rate: Double?,
    @SerializedName("recent_30_form") val recent30Form: Double?,
    @SerializedName("distance_breakdown") val distanceBreakdown: List<DistanceBreakdownDto>?,
    @SerializedName("track_breakdown") val trackBreakdown: List<TrackBreakdownDto>?,
)
