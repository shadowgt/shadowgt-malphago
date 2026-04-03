package com.malphago.app.data.local.entity

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "race",
    indices = [Index(value = ["trackCode", "raceDate", "raceNumber"], unique = true)],
)
data class RaceEntity(
    @PrimaryKey val id: Int,
    val trackCode: String,
    val raceDate: String,
    val raceNumber: Int,
    val raceName: String?,
    val raceLevel: String?,
    val distance: Int?,
    val weather: String?,
    val moisture: String?,
    val totalEntries: Int?,
    val prize1st: Int?,
    val raceTime: String?,
    val lastSyncAt: Long = System.currentTimeMillis(),
)
