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
    val weather: String?,
    @SerializedName("total_entries") val totalEntries: Int?,
)

data class RaceEntryDto(
    val id: Int,
    @SerializedName("race_id") val raceId: Int,
    @SerializedName("horse_number") val horseNumber: Int?,
    val ranking: Int?,
    @SerializedName("favor_ranking") val favorRanking: Int?,
    val rating: Int?,
    @SerializedName("horse_weight") val horseWeight: Int?,
)
