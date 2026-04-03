package com.malphago.app.data.remote.dto

import com.google.gson.annotations.SerializedName

data class EntryChangeDto(
    val id: Int,
    @SerializedName("race_id") val raceId: Int,
    @SerializedName("race_number") val raceNumber: Int,
    @SerializedName("race_date") val raceDate: String,
    val track: String,
    @SerializedName("track_name") val trackName: String?,
    @SerializedName("change_type") val changeType: String,
    @SerializedName("field_name") val fieldName: String?,
    @SerializedName("old_value") val oldValue: String?,
    @SerializedName("new_value") val newValue: String?,
    val source: String?,
    @SerializedName("detected_at") val detectedAt: String?,
)

data class RunningStyleDto(
    @SerializedName("horse_id") val horseId: Int,
    val style: String,
    @SerializedName("avg_corner_position") val avgCornerPosition: Double?,
    @SerializedName("early_speed_score") val earlySpeedScore: Double?,
    @SerializedName("late_kick_score") val lateKickScore: Double?,
    @SerializedName("acceleration_ratio") val accelerationRatio: Double?,
    val consistency: Double?,
    @SerializedName("sample_count") val sampleCount: Int?,
)
