package com.malphago.app.data.remote.dto

import com.google.gson.annotations.SerializedName

data class RaceDto(
    val id: Int,
    @SerializedName("track_id") val trackId: Int,
    @SerializedName("race_date") val raceDate: String,
    @SerializedName("race_number") val raceNumber: Int,
    @SerializedName("race_name") val raceName: String?,
    @SerializedName("race_level") val raceLevel: String?,
    val distance: Int?,
    val surface: String?,
    val weather: String?,
    val moisture: String?,
    @SerializedName("total_entries") val totalEntries: Int?,
    @SerializedName("prize_1st") val prize1st: Int?,
    @SerializedName("prize_2nd") val prize2nd: Int?,
    @SerializedName("prize_3rd") val prize3rd: Int?,
    @SerializedName("race_time") val raceTime: String?,
)

data class RaceEntryDto(
    val id: Int,
    @SerializedName("race_id") val raceId: Int,
    @SerializedName("horse_id") val horseId: Int?,
    @SerializedName("jockey_id") val jockeyId: Int?,
    @SerializedName("trainer_id") val trainerId: Int?,
    @SerializedName("horse_number") val horseNumber: Int?,
    val ranking: Int?,
    @SerializedName("favor_ranking") val favorRanking: Int?,
    val rating: Int?,
    val weight: String?,
    @SerializedName("horse_weight") val horseWeight: Int?,
    @SerializedName("horse_weight_change") val horseWeightChange: Int?,
    @SerializedName("race_interval") val raceInterval: Int?,
    @SerializedName("finish_margin") val finishMargin: String?,
    @SerializedName("odds_win") val oddsWin: Double?,
    @SerializedName("odds_place") val oddsPlace: Double?,
    val equipment: String?,
)
